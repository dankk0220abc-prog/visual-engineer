from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.git_ops import (
    GitOperationError,
    GitOperations,
    GitStatusEntry,
    RepositoryMetadata,
)
from visual_engineer_runner.ownership import (
    OwnershipError,
    WorkspaceDiscardProof,
    WorkspaceOwnershipManifest,
    WorkspaceOwnershipStore,
)
from visual_engineer_runner.safe_fs import SafeFilesystemError, SafeWorkspaceFilesystem
from visual_engineer_runner.validation_executor import (
    ValidationExecutionError,
    ValidationExecutor,
)
from visual_engineer_runner_protocol import (
    FailureCode,
    RepositoryRegistrationRequest,
    ResultPayload,
    SideEffectPermit,
    ValidationExecuteJobSpec,
    WorkspaceCheckpointPayload,
    WorkspaceDiffJobSpec,
    WorkspaceDiffResult,
    WorkspaceDiscardJobSpec,
    WorkspaceDiscardResult,
    WorkspaceJobSpec,
    WorkspaceListJobSpec,
    WorkspaceListResult,
    WorkspaceOperation,
    WorkspacePrepareJobSpec,
    WorkspacePrepareResult,
    WorkspaceReadTextJobSpec,
    WorkspaceReadTextResult,
    WorkspaceRollbackJobSpec,
    WorkspaceRollbackResult,
    WorkspaceStatusCode,
    WorkspaceStatusEntry,
    WorkspaceStatusJobSpec,
    WorkspaceStatusResult,
    WorkspaceWriteTextJobSpec,
    WorkspaceWriteTextResult,
    compute_side_effect_job_digest,
    execution_grant_policy_hash_matches,
    side_effect_job_binding,
    side_effect_permit_digest_matches,
)

_RESULT_ADAPTER: TypeAdapter[ResultPayload] = TypeAdapter(ResultPayload)
_MAX_REGISTRY_BYTES = 1024 * 1024
_MAX_COMPLETED_OPERATIONS = 128
_SENSITIVE_CONTENT = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|"
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:(?:token|secret|password|authorization)\s*[:=]\s*\S{8,}))"
)


class WorkspaceExecutionError(Exception):
    def __init__(self, code: FailureCode) -> None:
        super().__init__(code.value)
        self.code = code


class WorkspaceRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[2] = 2
    workspace_id: uuid.UUID
    runner_id: uuid.UUID
    grant_id: uuid.UUID
    repository_handle_id: uuid.UUID
    repository_opaque_handle: str
    policy_hash: str
    source_revision: str
    source_fingerprint: str
    workspace_fingerprint: str
    initial_tree_hash: str
    current_tree_hash: str
    workspace_device: int
    workspace_inode: int
    creation_nonce: str = Field(pattern=r"^[0-9a-f]{32}$")
    created_paths: list[str] = Field(default_factory=list)
    total_written_bytes: int = 0
    local_state: Literal["ready", "rolled_back", "discarded"] = "ready"
    completed_operations: dict[str, dict[str, Any]] = Field(default_factory=dict)
    pending_operation: dict[str, Any] | None = None
    pending_permit_id: uuid.UUID | None = None
    signature: str = Field(default="0" * 64, pattern=r"^[0-9a-f]{64}$")


class WorkspaceManager:
    def __init__(self, settings: RunnerSettings) -> None:
        self._settings = settings
        self._git = GitOperations(settings)
        self._ownership = WorkspaceOwnershipStore(settings)
        self._validation = ValidationExecutor(settings)
        self._lock = threading.RLock()

    def registration_requests(self, runner_id: uuid.UUID) -> list[RepositoryRegistrationRequest]:
        requests: list[RepositoryRegistrationRequest] = []
        for opaque_handle, repository in sorted(self._settings.repository_handles.items()):
            try:
                metadata = self._git.inspect_source(repository)
            except GitOperationError as exc:
                raise WorkspaceExecutionError(exc.code) from exc
            requests.append(
                RepositoryRegistrationRequest(
                    runner_id=runner_id,
                    opaque_handle=opaque_handle,
                    display_name=repository.display_name,
                    capabilities=["committed_head_read", "isolated_workspace"],
                    current_revision=metadata.current_revision,
                    current_branch=metadata.current_branch,
                    source_status=metadata.source_status,
                    source_is_dirty=metadata.source_is_dirty,
                    dirty_path_count=metadata.dirty_path_count,
                )
            )
        return requests

    def execute(
        self,
        spec: WorkspaceJobSpec,
        *,
        operation_id: uuid.UUID,
        cancel_event: threading.Event,
        side_effect_permit: SideEffectPermit | None = None,
    ) -> ResultPayload:
        with self._lock:
            try:
                return self._execute(
                    spec,
                    operation_id=operation_id,
                    cancel_event=cancel_event,
                    side_effect_permit=side_effect_permit,
                )
            except (
                GitOperationError,
                OwnershipError,
                SafeFilesystemError,
                ValidationExecutionError,
            ) as exc:
                raise WorkspaceExecutionError(exc.code) from exc

    def _execute(
        self,
        spec: WorkspaceJobSpec,
        *,
        operation_id: uuid.UUID,
        cancel_event: threading.Event,
        side_effect_permit: SideEffectPermit | None,
    ) -> ResultPayload:
        operation = _operation_for_spec(spec)
        self._validate_grant(spec, operation)
        if isinstance(spec, WorkspacePrepareJobSpec):
            prepare_permit = self._require_side_effect_permit(
                spec,
                operation_id=operation_id,
                permit=side_effect_permit,
                registry=None,
            )
            return self._prepare(
                spec,
                operation_id=operation_id,
                cancel_event=cancel_event,
                permit=prepare_permit,
            )
        registry = self._load_registry(spec.workspace_id)
        if registry is None:
            workspace = self._git.workspace_path(spec.workspace_id)
            if workspace.exists() or workspace.is_symlink():
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)
            if isinstance(spec, WorkspaceDiscardJobSpec):
                missing_registry_permit = self._require_side_effect_permit(
                    spec,
                    operation_id=operation_id,
                    permit=side_effect_permit,
                    registry=None,
                )
                return self._discard_without_registry(
                    spec,
                    operation_id=operation_id,
                    permit=missing_registry_permit,
                )
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_NOT_FOUND)
        self._validate_registry(spec, registry)
        if registry.local_state == "discarded":
            if isinstance(spec, WorkspaceDiscardJobSpec):
                replay_permit = self._require_side_effect_permit(
                    spec,
                    operation_id=operation_id,
                    permit=side_effect_permit,
                    registry=registry,
                )
                workspace = self._git.workspace_path(spec.workspace_id)
                if workspace.exists() or workspace.is_symlink():
                    raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)
                proof = self._validate_discard_proof(
                    spec,
                    registry=registry,
                    operation_id=operation_id,
                    permit=replay_permit,
                )
                if proof.state != "completed":
                    raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
                discard_result = WorkspaceDiscardResult(
                    workspace_id=spec.workspace_id,
                    discarded=True,
                    idempotent=True,
                    side_effect_permit_id=replay_permit.id,
                )
                self._cache_result(registry, operation_id, discard_result)
                return discard_result
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_NOT_FOUND)
        permit: SideEffectPermit | None = None
        if isinstance(
            spec,
            (
                WorkspaceWriteTextJobSpec,
                WorkspaceRollbackJobSpec,
                WorkspaceDiscardJobSpec,
                ValidationExecuteJobSpec,
            ),
        ):
            permit = self._require_side_effect_permit(
                spec,
                operation_id=operation_id,
                permit=side_effect_permit,
                registry=registry,
            )
        elif side_effect_permit is not None:
            raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_INVALID)
        cached = registry.completed_operations.get(str(operation_id))
        if cached is not None:
            try:
                cached_result = _RESULT_ADAPTER.validate_python(cached)
            except ValidationError as exc:
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID) from exc
            return _rebind_cached_permit(cached_result, permit)

        workspace = self._git.workspace_path(spec.workspace_id)
        if (
            isinstance(spec, WorkspaceDiscardJobSpec)
            and permit is not None
            and registry.pending_operation
            == {
                "operation_id": str(operation_id),
                "kind": "discard",
            }
            and not workspace.exists()
            and not workspace.is_symlink()
        ):
            proof = self._validate_discard_proof(
                spec,
                registry=registry,
                operation_id=operation_id,
                permit=permit,
            )
            if proof.state == "pending":
                self._complete_discard_proof(proof, permit)
            registry.local_state = "discarded"
            registry.pending_operation = None
            registry.pending_permit_id = None
            result = WorkspaceDiscardResult(
                workspace_id=spec.workspace_id,
                discarded=True,
                idempotent=True,
                side_effect_permit_id=permit.id,
            )
            self._cache_result(registry, operation_id, result)
            return result
        if workspace.is_symlink():
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
        if not workspace.exists():
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)

        repository = self._repository_for(spec)
        source_metadata = self._git.inspect_source(repository)
        if (
            source_metadata.current_revision != spec.execution_grant.source_revision
            or _source_fingerprint(source_metadata) != registry.source_fingerprint
        ):
            raise WorkspaceExecutionError(FailureCode.SOURCE_REVISION_MISMATCH)
        filesystem = SafeWorkspaceFilesystem(
            workspace,
            spec.execution_grant,
            cancel_event=cancel_event,
            commit_delay_ms=self._settings.workspace_write_commit_delay_ms,
        )
        filesystem.verify_root_identity(
            registry.workspace_device,
            registry.workspace_inode,
        )
        self._validate_ownership_manifest(spec, registry, filesystem)
        if isinstance(spec, ValidationExecuteJobSpec):
            if permit is None:
                raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_REQUIRED)
            status = self._authorized_status(spec, filesystem)
            current_tree_hash = _tree_fingerprint(
                spec.execution_grant.source_revision,
                status,
                filesystem,
            )
            if (
                registry.current_tree_hash != spec.checkpoint_fingerprint
                or current_tree_hash != spec.checkpoint_fingerprint
            ):
                raise WorkspaceExecutionError(FailureCode.VALIDATION_CHECKPOINT_MISMATCH)
            return self._validation.execute(
                spec,
                cancel_event=cancel_event,
                side_effect_permit=permit,
                filesystem=filesystem,
                canonical_workspace=workspace,
            )
        if isinstance(spec, WorkspaceListJobSpec):
            return self._list(spec, filesystem)
        if isinstance(spec, WorkspaceReadTextJobSpec):
            return self._read(spec, filesystem)
        if isinstance(spec, WorkspaceWriteTextJobSpec):
            if permit is None:
                raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_REQUIRED)
            return self._write(
                spec,
                registry,
                filesystem,
                operation_id=operation_id,
                permit=permit,
                cancel_event=cancel_event,
            )
        if isinstance(spec, WorkspaceStatusJobSpec):
            return self._status(spec, registry, filesystem)
        if isinstance(spec, WorkspaceDiffJobSpec):
            return self._diff(spec, registry, filesystem)
        if isinstance(spec, WorkspaceRollbackJobSpec):
            if permit is None:
                raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_REQUIRED)
            return self._rollback(
                spec,
                registry,
                filesystem,
                operation_id=operation_id,
                permit=permit,
            )
        if isinstance(spec, WorkspaceDiscardJobSpec):
            if permit is None:
                raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_REQUIRED)
            return self._discard(
                spec,
                registry,
                filesystem,
                operation_id=operation_id,
                permit=permit,
            )
        raise WorkspaceExecutionError(FailureCode.UNSUPPORTED_CAPABILITY)

    def _prepare(
        self,
        spec: WorkspacePrepareJobSpec,
        *,
        operation_id: uuid.UUID,
        cancel_event: threading.Event,
        permit: SideEffectPermit,
    ) -> WorkspacePrepareResult:
        existing = self._load_registry(spec.workspace_id)
        if existing is not None:
            self._validate_registry(spec, existing)
            if existing.local_state == "discarded":
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
            cached = existing.completed_operations.get(str(operation_id))
            if cached is not None:
                result = _RESULT_ADAPTER.validate_python(cached)
                if isinstance(result, WorkspacePrepareResult):
                    rebound = _rebind_cached_permit(result, permit)
                    if isinstance(rebound, WorkspacePrepareResult):
                        return rebound
            workspace = self._git.workspace_path(spec.workspace_id)
            if workspace.is_symlink():
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
            if not workspace.exists():
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)
            filesystem = SafeWorkspaceFilesystem(
                workspace,
                spec.execution_grant,
            )
            filesystem.verify_root_identity(
                existing.workspace_device,
                existing.workspace_inode,
            )
            self._validate_ownership_manifest(spec, existing, filesystem)
            return WorkspacePrepareResult(
                workspace_id=spec.workspace_id,
                repository_handle_id=spec.execution_grant.repository_handle_id,
                source_revision=spec.execution_grant.source_revision,
                workspace_fingerprint=existing.workspace_fingerprint,
                initial_tree_hash=existing.initial_tree_hash,
                current_tree_hash=existing.current_tree_hash,
                side_effect_permit_id=permit.id,
            )
        if (
            self._ownership.path(spec.workspace_id).exists()
            or self._ownership.path(spec.workspace_id).is_symlink()
            or self._ownership.discard_proof_path(spec.workspace_id).exists()
            or self._ownership.discard_proof_path(spec.workspace_id).is_symlink()
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)

        if self._settings.workspace_prepare_delay_ms and cancel_event.wait(
            self._settings.workspace_prepare_delay_ms / 1000
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_CANCELLED)
        repository = self._repository_for(spec)
        metadata = self._git.inspect_source(repository)
        if metadata.current_revision != spec.execution_grant.source_revision:
            raise WorkspaceExecutionError(FailureCode.SOURCE_REVISION_MISMATCH)
        mirror = self._git.prepare_mirror(
            spec.execution_grant.repository_opaque_handle,
            repository,
            spec.execution_grant.source_revision,
            permit_expires_at=permit.expires_at,
        )
        workspace = self._git.workspace_path(spec.workspace_id)
        if workspace.exists():
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)
        self._ensure_permit_fresh(permit)
        checkout = self._git.create_detached_worktree(
            mirror,
            spec.workspace_id,
            spec.execution_grant.source_revision,
            permit_expires_at=permit.expires_at,
        )
        workspace = checkout.workspace
        filesystem = SafeWorkspaceFilesystem(workspace, spec.execution_grant)
        status = self._authorized_status(spec, filesystem)
        if status:
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
        initial_tree_hash = _tree_fingerprint(spec.execution_grant.source_revision, [], filesystem)
        workspace_fingerprint = hashlib.sha256(
            (
                f"{spec.workspace_id}:{spec.execution_grant.repository_handle_id}:"
                f"{spec.execution_grant.source_revision}:{filesystem.root_device}:"
                f"{filesystem.root_inode}"
            ).encode()
        ).hexdigest()
        creation_nonce = uuid.uuid4().hex
        self._ensure_permit_fresh(permit)
        self._ownership.create(
            workspace_id=spec.workspace_id,
            runner_id=permit.runner_id,
            grant_id=spec.execution_grant.id,
            repository_handle_id=spec.execution_grant.repository_handle_id,
            repository_opaque_handle=spec.execution_grant.repository_opaque_handle,
            source_revision=spec.execution_grant.source_revision,
            policy_hash=spec.execution_grant.policy_hash,
            creation_nonce=creation_nonce,
            workspace_device=filesystem.root_device,
            workspace_inode=filesystem.root_inode,
        )
        registry = WorkspaceRegistry(
            workspace_id=spec.workspace_id,
            runner_id=permit.runner_id,
            grant_id=spec.execution_grant.id,
            repository_handle_id=spec.execution_grant.repository_handle_id,
            repository_opaque_handle=spec.execution_grant.repository_opaque_handle,
            policy_hash=spec.execution_grant.policy_hash,
            source_revision=spec.execution_grant.source_revision,
            source_fingerprint=_source_fingerprint(metadata),
            workspace_fingerprint=workspace_fingerprint,
            initial_tree_hash=initial_tree_hash,
            current_tree_hash=initial_tree_hash,
            workspace_device=filesystem.root_device,
            workspace_inode=filesystem.root_inode,
            creation_nonce=creation_nonce,
        )
        result = WorkspacePrepareResult(
            workspace_id=spec.workspace_id,
            repository_handle_id=spec.execution_grant.repository_handle_id,
            source_revision=spec.execution_grant.source_revision,
            workspace_fingerprint=workspace_fingerprint,
            initial_tree_hash=initial_tree_hash,
            current_tree_hash=initial_tree_hash,
            side_effect_permit_id=permit.id,
        )
        self._cache_result(registry, operation_id, result)
        return result

    def _list(
        self,
        spec: WorkspaceListJobSpec,
        filesystem: SafeWorkspaceFilesystem,
    ) -> WorkspaceListResult:
        entries, truncated = filesystem.list_directory(
            spec.relative_directory,
            depth=spec.depth,
            max_entries=spec.max_entries,
        )
        return WorkspaceListResult(
            workspace_id=spec.workspace_id,
            relative_directory=spec.relative_directory,
            entries=entries,
            truncated=truncated,
        )

    def _read(
        self,
        spec: WorkspaceReadTextJobSpec,
        filesystem: SafeWorkspaceFilesystem,
    ) -> WorkspaceReadTextResult:
        value = filesystem.read_text(spec.relative_path, spec.max_bytes)
        if _SENSITIVE_CONTENT.search(value.content):
            raise WorkspaceExecutionError(FailureCode.POLICY_DENIED)
        return WorkspaceReadTextResult(
            workspace_id=spec.workspace_id,
            relative_path=spec.relative_path,
            content=value.content,
            sha256=value.sha256,
            size=value.size,
        )

    def _write(
        self,
        spec: WorkspaceWriteTextJobSpec,
        registry: WorkspaceRegistry,
        filesystem: SafeWorkspaceFilesystem,
        *,
        operation_id: uuid.UUID,
        permit: SideEffectPermit,
        cancel_event: threading.Event,
    ) -> WorkspaceWriteTextResult:
        if _SENSITIVE_CONTENT.search(spec.content):
            raise WorkspaceExecutionError(FailureCode.POLICY_DENIED)
        encoded = spec.content.encode("utf-8")
        if registry.total_written_bytes + len(encoded) > spec.execution_grant.max_total_write_bytes:
            raise WorkspaceExecutionError(FailureCode.TOTAL_WRITE_BUDGET_EXCEEDED)
        before = self._authorized_status(spec, filesystem)
        changed_before = {entry.relative_path for entry in before}
        if (
            spec.relative_path not in changed_before
            and len(changed_before) >= spec.execution_grant.max_files_changed
        ):
            raise WorkspaceExecutionError(FailureCode.FILE_COUNT_BUDGET_EXCEEDED)

        desired_sha256 = hashlib.sha256(encoded).hexdigest()
        pending_operation = {
            "operation_id": str(operation_id),
            "relative_path": spec.relative_path,
            "mode": spec.mode.value,
            "desired_sha256": desired_sha256,
            "size": len(encoded),
        }
        recover_interrupted = registry.pending_operation is not None
        if recover_interrupted:
            if registry.pending_operation != pending_operation:
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
            registry.pending_permit_id = permit.id
            self._ensure_permit_fresh(permit)
            self._save_registry(registry)
        else:
            registry.pending_operation = pending_operation
            registry.pending_permit_id = permit.id
            self._ensure_permit_fresh(permit)
            self._save_registry(registry)
        outcome = None
        try:
            outcome = filesystem.write_text(
                spec.relative_path,
                spec.content,
                mode=spec.mode,
                expected_sha256=spec.expected_sha256,
                operation_id=operation_id,
                recover_interrupted=recover_interrupted,
                before_commit=lambda: self._ensure_permit_fresh(permit),
            )
            if self._settings.workspace_write_post_commit_delay_ms and cancel_event.wait(
                self._settings.workspace_write_post_commit_delay_ms / 1000
            ):
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_CANCELLED)
            self._ensure_permit_fresh(permit)
            status = self._authorized_status(spec, filesystem)
            if len(status) > spec.execution_grant.max_files_changed:
                raise WorkspaceExecutionError(FailureCode.FILE_COUNT_BUDGET_EXCEEDED)
            if outcome.created and outcome.relative_path not in registry.created_paths:
                registry.created_paths = sorted([*registry.created_paths, outcome.relative_path])
            registry.total_written_bytes += outcome.size
            checkpoint = self._checkpoint(
                spec,
                filesystem,
                status,
                side_effect_permit_id=permit.id,
            )
            registry.current_tree_hash = checkpoint.tree_fingerprint
            registry.pending_operation = None
            registry.pending_permit_id = None
            result = WorkspaceWriteTextResult(
                workspace_id=spec.workspace_id,
                relative_path=outcome.relative_path,
                operation=outcome.operation,
                sha256=outcome.sha256,
                size=outcome.size,
                current_tree_hash=checkpoint.tree_fingerprint,
                changed_file_count=len(status),
                total_written_bytes=registry.total_written_bytes,
                checkpoint=checkpoint,
                side_effect_permit_id=permit.id,
            )
            self._cache_result(registry, operation_id, result)
            return result
        except Exception:
            if outcome is None:
                registry.pending_operation = None
                registry.pending_permit_id = None
            self._save_registry(registry)
            raise

    def _status(
        self,
        spec: WorkspaceStatusJobSpec,
        registry: WorkspaceRegistry,
        filesystem: SafeWorkspaceFilesystem,
    ) -> WorkspaceStatusResult:
        status = self._authorized_status(spec, filesystem)
        current_tree_hash = _tree_fingerprint(
            spec.execution_grant.source_revision,
            status,
            filesystem,
        )
        return WorkspaceStatusResult(
            workspace_id=spec.workspace_id,
            entries=[
                WorkspaceStatusEntry(
                    relative_path=entry.relative_path,
                    status=entry.status,
                )
                for entry in status
            ],
            changed_file_count=len(status),
            current_tree_hash=current_tree_hash,
        )

    def _diff(
        self,
        spec: WorkspaceDiffJobSpec,
        registry: WorkspaceRegistry,
        filesystem: SafeWorkspaceFilesystem,
    ) -> WorkspaceDiffResult:
        status = self._authorized_status(spec, filesystem)
        checkpoint = self._checkpoint(spec, filesystem, status)
        if _SENSITIVE_CONTENT.search(checkpoint.diff):
            raise WorkspaceExecutionError(FailureCode.POLICY_DENIED)
        return WorkspaceDiffResult(
            workspace_id=spec.workspace_id,
            diff=checkpoint.diff,
            diff_hash=checkpoint.diff_hash,
            changed_paths=checkpoint.changed_paths,
            total_diff_bytes=checkpoint.total_diff_bytes,
            current_tree_hash=checkpoint.tree_fingerprint,
            checkpoint=checkpoint,
        )

    def _checkpoint(
        self,
        spec: WorkspaceJobSpec,
        filesystem: SafeWorkspaceFilesystem,
        status: list[GitStatusEntry],
        *,
        side_effect_permit_id: uuid.UUID | None = None,
    ) -> WorkspaceCheckpointPayload:
        workspace = self._git.workspace_path(spec.workspace_id)
        diff = self._git.diff(
            workspace,
            spec.execution_grant.source_revision,
            status,
            read_untracked_text=lambda path: (
                filesystem.read_text(
                    path,
                    spec.execution_grant.max_single_file_bytes,
                ).content
            ),
            max_bytes=spec.execution_grant.max_diff_bytes,
        )
        tree_fingerprint = _tree_fingerprint(
            spec.execution_grant.source_revision,
            status,
            filesystem,
        )
        changed_paths = [entry.relative_path for entry in status]
        return WorkspaceCheckpointPayload(
            source_revision=spec.execution_grant.source_revision,
            tree_fingerprint=tree_fingerprint,
            diff_hash=hashlib.sha256(diff.encode("utf-8")).hexdigest(),
            changed_paths=changed_paths,
            changed_file_count=len(changed_paths),
            total_diff_bytes=len(diff.encode("utf-8")),
            diff=diff,
            side_effect_permit_id=side_effect_permit_id,
        )

    def _rollback(
        self,
        spec: WorkspaceRollbackJobSpec,
        registry: WorkspaceRegistry,
        filesystem: SafeWorkspaceFilesystem,
        *,
        operation_id: uuid.UUID,
        permit: SideEffectPermit,
    ) -> WorkspaceRollbackResult:
        status = self._authorized_status(spec, filesystem)
        tracked = [
            entry.relative_path
            for entry in status
            if entry.relative_path not in registry.created_paths
        ]
        pending_operation = {
            "operation_id": str(operation_id),
            "kind": "rollback",
            "target": "initial",
        }
        if (
            registry.pending_operation is not None
            and registry.pending_operation != pending_operation
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
        registry.pending_operation = pending_operation
        registry.pending_permit_id = permit.id
        self._ensure_permit_fresh(permit)
        self._save_registry(registry)
        self._git.restore_tracked(
            self._git.workspace_path(spec.workspace_id),
            spec.execution_grant.source_revision,
            tracked,
            permit_expires_at=permit.expires_at,
        )
        removed: list[str] = []
        for relative_path in registry.created_paths:
            if filesystem.remove_created_file(
                relative_path,
                before_remove=lambda: self._ensure_permit_fresh(permit),
            ):
                removed.append(relative_path)
        remaining = self._authorized_status(spec, filesystem)
        if remaining:
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
        current_tree_hash = _tree_fingerprint(
            spec.execution_grant.source_revision,
            [],
            filesystem,
        )
        if current_tree_hash != registry.initial_tree_hash:
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
        registry.current_tree_hash = current_tree_hash
        registry.created_paths = []
        registry.total_written_bytes = 0
        registry.local_state = "rolled_back"
        registry.pending_operation = None
        registry.pending_permit_id = None
        result = WorkspaceRollbackResult(
            workspace_id=spec.workspace_id,
            clean=True,
            current_tree_hash=current_tree_hash,
            removed_created_paths=removed,
            side_effect_permit_id=permit.id,
        )
        self._cache_result(registry, operation_id, result)
        return result

    def _discard(
        self,
        spec: WorkspaceDiscardJobSpec,
        registry: WorkspaceRegistry,
        filesystem: SafeWorkspaceFilesystem,
        *,
        operation_id: uuid.UUID,
        permit: SideEffectPermit,
    ) -> WorkspaceDiscardResult:
        filesystem.verify_root_identity(
            registry.workspace_device,
            registry.workspace_inode,
        )
        mirror = self._git.mirror_path(registry.repository_opaque_handle)
        workspace = self._git.workspace_path(spec.workspace_id)
        inventory = self._git.discard_inventory(
            workspace,
            spec.execution_grant.source_revision,
        )
        for entry in inventory:
            if entry.status == WorkspaceStatusCode.IGNORED:
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
            filesystem.authorize(entry.relative_path)
            if (
                entry.status == WorkspaceStatusCode.UNTRACKED
                and entry.relative_path not in registry.created_paths
            ):
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
        pending_operation = {
            "operation_id": str(operation_id),
            "kind": "discard",
        }
        if (
            registry.pending_operation is not None
            and registry.pending_operation != pending_operation
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
        registry.pending_operation = pending_operation
        registry.pending_permit_id = permit.id
        self._ensure_permit_fresh(permit)
        proof = self._create_discard_proof(
            spec,
            registry,
            operation_id=operation_id,
            permit=permit,
        )
        self._save_registry(registry)
        self._git.discard_worktree(
            mirror,
            workspace,
            permit_expires_at=permit.expires_at,
        )
        self._complete_discard_proof(proof, permit)
        registry.local_state = "discarded"
        registry.pending_operation = None
        registry.pending_permit_id = None
        result = WorkspaceDiscardResult(
            workspace_id=spec.workspace_id,
            discarded=True,
            idempotent=False,
            side_effect_permit_id=permit.id,
        )
        self._cache_result(registry, operation_id, result)
        return result

    def _discard_without_registry(
        self,
        spec: WorkspaceDiscardJobSpec,
        *,
        operation_id: uuid.UUID,
        permit: SideEffectPermit,
    ) -> WorkspaceDiscardResult:
        workspace = self._git.workspace_path(spec.workspace_id)
        if workspace.exists() or workspace.is_symlink():
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)
        proof = self._validate_discard_proof(
            spec,
            registry=None,
            operation_id=operation_id,
            permit=permit,
        )
        if proof.state == "pending":
            self._complete_discard_proof(proof, permit)
        return WorkspaceDiscardResult(
            workspace_id=spec.workspace_id,
            discarded=True,
            idempotent=True,
            side_effect_permit_id=permit.id,
        )

    def _authorized_status(
        self,
        spec: WorkspaceJobSpec,
        filesystem: SafeWorkspaceFilesystem,
    ) -> list[GitStatusEntry]:
        status = self._git.status(
            self._git.workspace_path(spec.workspace_id),
            spec.execution_grant.source_revision,
        )
        for entry in status:
            filesystem.authorize(entry.relative_path)
        if len(status) > spec.execution_grant.max_files_changed:
            raise WorkspaceExecutionError(FailureCode.FILE_COUNT_BUDGET_EXCEEDED)
        return status

    def _validate_grant(
        self,
        spec: WorkspaceJobSpec,
        operation: WorkspaceOperation,
    ) -> None:
        grant = spec.execution_grant
        if not execution_grant_policy_hash_matches(grant, grant.policy_hash):
            raise WorkspaceExecutionError(FailureCode.ENVELOPE_HASH_MISMATCH)
        if grant.expires_at <= datetime.now(UTC):
            raise WorkspaceExecutionError(FailureCode.ENVELOPE_EXPIRED)
        if operation not in grant.allowed_operations:
            raise WorkspaceExecutionError(FailureCode.POLICY_DENIED)
        if (
            grant.network_policy != "none"
            or grant.shell_access
            or grant.git_delivery_access
            or grant.source_repository_write_access
        ):
            raise WorkspaceExecutionError(FailureCode.POLICY_DENIED)

    def _validate_registry(
        self,
        spec: WorkspaceJobSpec,
        registry: WorkspaceRegistry,
    ) -> None:
        grant = spec.execution_grant
        if isinstance(spec, ValidationExecuteJobSpec):
            if (
                registry.workspace_id != spec.workspace_id
                or grant.validation_workspace_id != registry.workspace_id
                or grant.validation_checkpoint_id != spec.checkpoint_id
                or registry.current_tree_hash != spec.checkpoint_fingerprint
                or registry.repository_handle_id != grant.repository_handle_id
                or registry.repository_opaque_handle != grant.repository_opaque_handle
                or registry.source_revision != grant.source_revision
            ):
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
            return
        if (
            registry.workspace_id != spec.workspace_id
            or registry.grant_id != grant.id
            or registry.repository_handle_id != grant.repository_handle_id
            or registry.repository_opaque_handle != grant.repository_opaque_handle
            or registry.policy_hash != grant.policy_hash
            or registry.source_revision != grant.source_revision
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)

    def _require_side_effect_permit(
        self,
        spec: WorkspaceJobSpec,
        *,
        operation_id: uuid.UUID,
        permit: SideEffectPermit | None,
        registry: WorkspaceRegistry | None,
    ) -> SideEffectPermit:
        if permit is None:
            raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_REQUIRED)
        binding = side_effect_job_binding(spec)
        job_digest = compute_side_effect_job_digest(spec)
        expected_current = binding["expected_current"]
        if expected_current is None and registry is not None:
            expected_current = registry.current_tree_hash
        if (
            permit.job_id != operation_id
            or permit.grant_id != spec.execution_grant.id
            or permit.workspace_id != spec.workspace_id
            or permit.repository_handle_id != spec.execution_grant.repository_handle_id
            or permit.policy_hash != spec.execution_grant.policy_hash
            or permit.source_revision != spec.execution_grant.source_revision
            or permit.operation.value != binding["operation"]
            or permit.relative_path != binding["relative_path"]
            or permit.proposed_digest != binding["proposed_digest"]
            or permit.job_digest != job_digest
            or (expected_current is not None and permit.expected_current != expected_current)
            or (registry is not None and permit.runner_id != registry.runner_id)
            or not side_effect_permit_digest_matches(permit, permit.operation_digest)
        ):
            raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_INVALID)
        self._ensure_permit_fresh(permit)
        return permit

    @staticmethod
    def _ensure_permit_fresh(permit: SideEffectPermit) -> None:
        if permit.expires_at <= datetime.now(UTC):
            raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_EXPIRED)

    def _validate_ownership_manifest(
        self,
        spec: WorkspaceJobSpec,
        registry: WorkspaceRegistry,
        filesystem: SafeWorkspaceFilesystem,
    ) -> WorkspaceOwnershipManifest:
        manifest = self._validate_ownership_record(spec, registry)
        if (
            manifest.workspace_device != filesystem.root_device
            or manifest.workspace_inode != filesystem.root_inode
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
        return manifest

    def _create_discard_proof(
        self,
        spec: WorkspaceDiscardJobSpec,
        registry: WorkspaceRegistry,
        *,
        operation_id: uuid.UUID,
        permit: SideEffectPermit,
    ) -> WorkspaceDiscardProof:
        manifest = self._validate_ownership_record(spec, registry)
        self._ensure_permit_fresh(permit)
        existing = self._ownership.load_discard_proof(spec.workspace_id)
        if existing is not None:
            if existing.state != "pending" or not self._discard_proof_binding_matches(
                existing,
                spec,
                registry=registry,
                operation_id=operation_id,
                permit=permit,
            ):
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
            return existing
        recorded_at = datetime.now(UTC)
        if recorded_at > permit.expires_at:
            raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_EXPIRED)
        proof = WorkspaceDiscardProof(
            state="pending",
            workspace_id=registry.workspace_id,
            runner_id=registry.runner_id,
            grant_id=registry.grant_id,
            repository_handle_id=registry.repository_handle_id,
            repository_opaque_handle=registry.repository_opaque_handle,
            source_revision=registry.source_revision,
            policy_hash=registry.policy_hash,
            creation_nonce=manifest.creation_nonce,
            workspace_device=manifest.workspace_device,
            workspace_inode=manifest.workspace_inode,
            operation_id=operation_id,
            permit_id=permit.id,
            permit_sequence=permit.sequence,
            attempt_id=permit.attempt_id,
            lease_id=permit.lease_id,
            job_digest=permit.job_digest,
            operation_digest=permit.operation_digest,
            expected_current=permit.expected_current,
            proposed_digest=permit.proposed_digest,
            issued_at=permit.issued_at,
            consumed_at=permit.consumed_at,
            expires_at=permit.expires_at,
            recorded_at=recorded_at,
            completed_at=None,
            proof_nonce=uuid.uuid4().hex,
        )
        return self._ownership.save_discard_proof(proof)

    def _complete_discard_proof(
        self,
        proof: WorkspaceDiscardProof,
        permit: SideEffectPermit,
    ) -> WorkspaceDiscardProof:
        self._ensure_permit_fresh(permit)
        completed_at = datetime.now(UTC)
        if completed_at > proof.expires_at:
            raise WorkspaceExecutionError(FailureCode.SIDE_EFFECT_PERMIT_EXPIRED)
        completed = proof.model_copy(
            update={
                "state": "completed",
                "completed_at": completed_at,
            }
        )
        return self._ownership.save_discard_proof(completed)

    def _validate_discard_proof(
        self,
        spec: WorkspaceDiscardJobSpec,
        *,
        registry: WorkspaceRegistry | None,
        operation_id: uuid.UUID,
        permit: SideEffectPermit,
    ) -> WorkspaceDiscardProof:
        proof = self._ownership.load_discard_proof(spec.workspace_id)
        if proof is None:
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)
        if not self._discard_proof_binding_matches(
            proof,
            spec,
            registry=registry,
            operation_id=operation_id,
            permit=permit,
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
        self._ensure_permit_fresh(permit)
        manifest = self._ownership.load(spec.workspace_id)
        if (
            manifest.workspace_id != proof.workspace_id
            or manifest.runner_id != proof.runner_id
            or manifest.grant_id != proof.grant_id
            or manifest.repository_handle_id != proof.repository_handle_id
            or manifest.repository_opaque_handle != proof.repository_opaque_handle
            or manifest.source_revision != proof.source_revision
            or manifest.policy_hash != proof.policy_hash
            or manifest.creation_nonce != proof.creation_nonce
            or manifest.workspace_device != proof.workspace_device
            or manifest.workspace_inode != proof.workspace_inode
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
        self._require_discarded_inode_absent(proof)
        return proof

    @staticmethod
    def _discard_proof_binding_matches(
        proof: WorkspaceDiscardProof,
        spec: WorkspaceDiscardJobSpec,
        *,
        registry: WorkspaceRegistry | None,
        operation_id: uuid.UUID,
        permit: SideEffectPermit,
    ) -> bool:
        grant = spec.execution_grant
        return not (
            proof.workspace_id != spec.workspace_id
            or proof.runner_id != permit.runner_id
            or proof.grant_id != grant.id
            or proof.repository_handle_id != grant.repository_handle_id
            or proof.repository_opaque_handle != grant.repository_opaque_handle
            or proof.source_revision != grant.source_revision
            or proof.policy_hash != grant.policy_hash
            or proof.operation_id != operation_id
            or proof.permit_id != permit.id
            or proof.permit_sequence != permit.sequence
            or proof.attempt_id != permit.attempt_id
            or proof.lease_id != permit.lease_id
            or proof.job_digest != permit.job_digest
            or proof.operation_digest != permit.operation_digest
            or proof.expected_current != permit.expected_current
            or proof.proposed_digest != permit.proposed_digest
            or proof.issued_at != permit.issued_at
            or proof.consumed_at != permit.consumed_at
            or proof.expires_at != permit.expires_at
            or (
                registry is not None
                and (
                    registry.workspace_id != proof.workspace_id
                    or registry.runner_id != proof.runner_id
                    or registry.grant_id != proof.grant_id
                    or registry.repository_handle_id != proof.repository_handle_id
                    or registry.repository_opaque_handle != proof.repository_opaque_handle
                    or registry.source_revision != proof.source_revision
                    or registry.policy_hash != proof.policy_hash
                    or registry.creation_nonce != proof.creation_nonce
                    or registry.workspace_device != proof.workspace_device
                    or registry.workspace_inode != proof.workspace_inode
                    or not WorkspaceManager._registry_discard_binding_matches(
                        registry,
                        proof,
                        operation_id=operation_id,
                        permit=permit,
                    )
                )
            )
        )

    @staticmethod
    def _registry_discard_binding_matches(
        registry: WorkspaceRegistry,
        proof: WorkspaceDiscardProof,
        *,
        operation_id: uuid.UUID,
        permit: SideEffectPermit,
    ) -> bool:
        pending_matches = (
            registry.pending_operation
            == {
                "operation_id": str(operation_id),
                "kind": "discard",
            }
            and registry.pending_permit_id == permit.id
        )
        if proof.state == "pending":
            return pending_matches and registry.local_state != "discarded"
        completed_payload = registry.completed_operations.get(str(operation_id))
        if completed_payload is None:
            return pending_matches
        try:
            completed = _RESULT_ADAPTER.validate_python(completed_payload)
        except ValidationError:
            return False
        return (
            registry.local_state == "discarded"
            and registry.pending_operation is None
            and registry.pending_permit_id is None
            and isinstance(completed, WorkspaceDiscardResult)
            and completed.workspace_id == proof.workspace_id
            and completed.side_effect_permit_id == permit.id
        )

    def _require_discarded_inode_absent(self, proof: WorkspaceDiscardProof) -> None:
        expected = self._git.workspace_path(proof.workspace_id)
        if expected.exists() or expected.is_symlink():
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)
        pending_directories = [self._settings.workspace_root]
        seen_directories: set[tuple[int, int]] = set()
        entries_checked = 0
        while pending_directories:
            directory = pending_directories.pop()
            descriptor: int | None = None
            try:
                descriptor = os.open(
                    directory,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                )
                directory_metadata = os.fstat(descriptor)
                if not stat.S_ISDIR(directory_metadata.st_mode):
                    raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
                key = (directory_metadata.st_dev, directory_metadata.st_ino)
                if key in seen_directories:
                    continue
                seen_directories.add(key)
                child_directories: list[Path] = []
                with os.scandir(descriptor) as entries:
                    for entry in entries:
                        entries_checked += 1
                        if entries_checked > 200_000:
                            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
                        metadata = entry.stat(follow_symlinks=False)
                        if (
                            metadata.st_dev == proof.workspace_device
                            and metadata.st_ino == proof.workspace_inode
                        ):
                            raise WorkspaceExecutionError(FailureCode.WORKSPACE_RECOVERY_REQUIRED)
                        if (
                            stat.S_ISDIR(metadata.st_mode)
                            and not stat.S_ISLNK(metadata.st_mode)
                            and metadata.st_dev == proof.workspace_device
                        ):
                            child_directories.append(directory / entry.name)
                pending_directories.extend(child_directories)
            except WorkspaceExecutionError:
                raise
            except OSError as exc:
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED) from exc
            finally:
                if descriptor is not None:
                    os.close(descriptor)

    def _validate_ownership_record(
        self,
        spec: WorkspaceJobSpec,
        registry: WorkspaceRegistry,
    ) -> WorkspaceOwnershipManifest:
        manifest = self._ownership.load(spec.workspace_id)
        if (
            manifest.workspace_id != registry.workspace_id
            or manifest.runner_id != registry.runner_id
            or manifest.grant_id != registry.grant_id
            or manifest.repository_handle_id != registry.repository_handle_id
            or manifest.repository_opaque_handle != registry.repository_opaque_handle
            or manifest.source_revision != registry.source_revision
            or manifest.policy_hash != registry.policy_hash
            or manifest.creation_nonce != registry.creation_nonce
            or manifest.workspace_device != registry.workspace_device
            or manifest.workspace_inode != registry.workspace_inode
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
        return manifest

    def _repository_for(self, spec: WorkspaceJobSpec) -> Any:
        repository = self._settings.repository_handles.get(
            spec.execution_grant.repository_opaque_handle
        )
        if repository is None:
            raise WorkspaceExecutionError(FailureCode.REPOSITORY_UNAVAILABLE)
        return repository

    def _registry_path(self, workspace_id: uuid.UUID) -> Path:
        return self._settings.registry_root / f"workspace-{workspace_id.hex}.json"

    def _load_registry(self, workspace_id: uuid.UUID) -> WorkspaceRegistry | None:
        path = self._registry_path(workspace_id)
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED) from exc
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_size > _MAX_REGISTRY_BYTES
            ):
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
            payload = os.read(descriptor, metadata.st_size + 1)
        finally:
            os.close(descriptor)
        try:
            registry = WorkspaceRegistry.model_validate_json(payload)
        except ValidationError as exc:
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED) from exc
        unsigned = registry.model_dump(mode="json", exclude={"signature"})
        if not self._ownership.registry_signature_matches(unsigned, registry.signature):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_QUARANTINED)
        return registry

    def _save_registry(self, registry: WorkspaceRegistry) -> None:
        unsigned = registry.model_dump(mode="json", exclude={"signature"})
        registry.signature = self._ownership.sign_registry(unsigned)
        root = self._settings.registry_root
        root_descriptor = os.open(
            root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        )
        filename = self._registry_path(registry.workspace_id).name
        temporary = f".{filename}.{uuid.uuid4().hex}.tmp"
        descriptor: int | None = None
        temporary_exists = False
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=root_descriptor,
            )
            temporary_exists = True
            payload = _registry_payload(registry)
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.rename(
                temporary,
                filename,
                src_dir_fd=root_descriptor,
                dst_dir_fd=root_descriptor,
            )
            temporary_exists = False
            os.fsync(root_descriptor)
        except OSError as exc:
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_exists:
                try:
                    os.unlink(temporary, dir_fd=root_descriptor)
                except FileNotFoundError:
                    pass
            os.close(root_descriptor)

    def _cache_result(
        self,
        registry: WorkspaceRegistry,
        operation_id: uuid.UUID,
        result: ResultPayload,
    ) -> None:
        if len(registry.completed_operations) >= _MAX_COMPLETED_OPERATIONS:
            oldest = next(iter(registry.completed_operations))
            del registry.completed_operations[oldest]
        registry.completed_operations[str(operation_id)] = result.model_dump(mode="json")
        while (
            len(registry.completed_operations) > 1
            and len(registry.model_dump_json().encode("utf-8")) > _MAX_REGISTRY_BYTES
        ):
            oldest = next(iter(registry.completed_operations))
            del registry.completed_operations[oldest]
        self._save_registry(registry)


def _operation_for_spec(spec: WorkspaceJobSpec) -> WorkspaceOperation:
    if isinstance(spec, WorkspacePrepareJobSpec):
        return WorkspaceOperation.PREPARE
    if isinstance(spec, WorkspaceListJobSpec):
        return WorkspaceOperation.LIST
    if isinstance(spec, WorkspaceReadTextJobSpec):
        return WorkspaceOperation.READ_TEXT
    if isinstance(spec, WorkspaceWriteTextJobSpec):
        return WorkspaceOperation.WRITE_TEXT
    if isinstance(spec, WorkspaceStatusJobSpec):
        return WorkspaceOperation.STATUS
    if isinstance(spec, WorkspaceDiffJobSpec):
        return WorkspaceOperation.DIFF
    if isinstance(spec, WorkspaceRollbackJobSpec):
        return WorkspaceOperation.ROLLBACK
    if isinstance(spec, WorkspaceDiscardJobSpec):
        return WorkspaceOperation.DISCARD
    if isinstance(spec, ValidationExecuteJobSpec):
        return WorkspaceOperation.VALIDATE
    raise WorkspaceExecutionError(FailureCode.UNSUPPORTED_CAPABILITY)


def _registry_payload(registry: WorkspaceRegistry) -> bytes:
    payload = registry.model_dump_json().encode("utf-8")
    if len(payload) > _MAX_REGISTRY_BYTES:
        raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
    return payload


def _source_fingerprint(metadata: RepositoryMetadata) -> str:
    payload = json.dumps(
        {
            "branch": metadata.current_branch,
            "dirty_path_count": metadata.dirty_path_count,
            "revision": metadata.current_revision,
            "source_status": metadata.source_status.value,
            "source_is_dirty": metadata.source_is_dirty,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _rebind_cached_permit(
    result: ResultPayload,
    permit: SideEffectPermit | None,
) -> ResultPayload:
    if permit is None or not isinstance(
        result,
        (
            WorkspacePrepareResult,
            WorkspaceWriteTextResult,
            WorkspaceRollbackResult,
            WorkspaceDiscardResult,
        ),
    ):
        return result
    payload = result.model_dump(mode="json")
    payload["side_effect_permit_id"] = str(permit.id)
    checkpoint = payload.get("checkpoint")
    if isinstance(checkpoint, dict):
        checkpoint["side_effect_permit_id"] = str(permit.id)
    try:
        return _RESULT_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID) from exc


def _tree_fingerprint(
    source_revision: str,
    status: list[GitStatusEntry],
    filesystem: SafeWorkspaceFilesystem,
) -> str:
    digest = hashlib.sha256()
    digest.update(f"source:{source_revision}\n".encode())
    for entry in status:
        digest.update(f"{entry.status.value}:{entry.relative_path}:".encode())
        if entry.status.value != "deleted":
            value = filesystem.read_text(entry.relative_path, 32 * 1024)
            digest.update(value.sha256.encode())
        digest.update(b"\n")
    return digest.hexdigest()
