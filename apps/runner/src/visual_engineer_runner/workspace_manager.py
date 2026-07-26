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
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.git_ops import (
    GitOperationError,
    GitOperations,
    GitStatusEntry,
    RepositoryMetadata,
)
from visual_engineer_runner.safe_fs import SafeFilesystemError, SafeWorkspaceFilesystem
from visual_engineer_runner_protocol import (
    FailureCode,
    RepositoryRegistrationRequest,
    ResultPayload,
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
    WorkspaceStatusEntry,
    WorkspaceStatusJobSpec,
    WorkspaceStatusResult,
    WorkspaceWriteTextJobSpec,
    WorkspaceWriteTextResult,
    execution_grant_policy_hash_matches,
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

    version: int = 1
    workspace_id: uuid.UUID
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
    created_paths: list[str] = Field(default_factory=list)
    total_written_bytes: int = 0
    local_state: str = "ready"
    completed_operations: dict[str, dict[str, Any]] = Field(default_factory=dict)
    pending_operation: dict[str, Any] | None = None


class WorkspaceManager:
    def __init__(self, settings: RunnerSettings) -> None:
        self._settings = settings
        self._git = GitOperations(settings)
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
    ) -> ResultPayload:
        with self._lock:
            try:
                return self._execute(spec, operation_id=operation_id, cancel_event=cancel_event)
            except (GitOperationError, SafeFilesystemError) as exc:
                raise WorkspaceExecutionError(exc.code) from exc

    def _execute(
        self,
        spec: WorkspaceJobSpec,
        *,
        operation_id: uuid.UUID,
        cancel_event: threading.Event,
    ) -> ResultPayload:
        operation = _operation_for_spec(spec)
        self._validate_grant(spec, operation)
        if isinstance(spec, WorkspacePrepareJobSpec):
            return self._prepare(
                spec,
                operation_id=operation_id,
                cancel_event=cancel_event,
            )
        registry = self._load_registry(spec.workspace_id)
        if registry is None:
            if isinstance(spec, WorkspaceDiscardJobSpec):
                return self._discard_without_registry(spec, operation_id=operation_id)
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_NOT_FOUND)
        self._validate_registry(spec, registry)
        cached = registry.completed_operations.get(str(operation_id))
        if cached is not None:
            try:
                return _RESULT_ADAPTER.validate_python(cached)
            except ValidationError as exc:
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        if registry.local_state == "discarded":
            if isinstance(spec, WorkspaceDiscardJobSpec):
                result = WorkspaceDiscardResult(
                    workspace_id=spec.workspace_id,
                    discarded=True,
                    idempotent=True,
                )
                self._cache_result(registry, operation_id, result)
                return result
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_NOT_FOUND)

        repository = self._repository_for(spec)
        source_metadata = self._git.inspect_source(repository)
        if (
            source_metadata.current_revision != spec.execution_grant.source_revision
            or _source_fingerprint(source_metadata) != registry.source_fingerprint
        ):
            raise WorkspaceExecutionError(FailureCode.SOURCE_REVISION_MISMATCH)
        workspace = self._git.workspace_path(spec.workspace_id)
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
        if isinstance(spec, WorkspaceListJobSpec):
            return self._list(spec, filesystem)
        if isinstance(spec, WorkspaceReadTextJobSpec):
            return self._read(spec, filesystem)
        if isinstance(spec, WorkspaceWriteTextJobSpec):
            return self._write(
                spec,
                registry,
                filesystem,
                operation_id=operation_id,
            )
        if isinstance(spec, WorkspaceStatusJobSpec):
            return self._status(spec, registry, filesystem)
        if isinstance(spec, WorkspaceDiffJobSpec):
            diff_result = self._diff(spec, registry, filesystem)
            registry.local_state = "sealed"
            self._cache_result(registry, operation_id, diff_result)
            return diff_result
        if isinstance(spec, WorkspaceRollbackJobSpec):
            return self._rollback(
                spec,
                registry,
                filesystem,
                operation_id=operation_id,
            )
        if isinstance(spec, WorkspaceDiscardJobSpec):
            return self._discard(spec, registry, filesystem, operation_id=operation_id)
        raise WorkspaceExecutionError(FailureCode.UNSUPPORTED_CAPABILITY)

    def _prepare(
        self,
        spec: WorkspacePrepareJobSpec,
        *,
        operation_id: uuid.UUID,
        cancel_event: threading.Event,
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
                    return result
            filesystem = SafeWorkspaceFilesystem(
                self._git.workspace_path(spec.workspace_id),
                spec.execution_grant,
            )
            filesystem.verify_root_identity(
                existing.workspace_device,
                existing.workspace_inode,
            )
            return WorkspacePrepareResult(
                workspace_id=spec.workspace_id,
                repository_handle_id=spec.execution_grant.repository_handle_id,
                source_revision=spec.execution_grant.source_revision,
                workspace_fingerprint=existing.workspace_fingerprint,
                initial_tree_hash=existing.initial_tree_hash,
                current_tree_hash=existing.current_tree_hash,
            )

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
        )
        workspace = self._git.workspace_path(spec.workspace_id)
        if workspace.exists():
            status = self._git.status(workspace, spec.execution_grant.source_revision)
            if status:
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
        else:
            workspace = self._git.create_detached_worktree(
                mirror,
                spec.workspace_id,
                spec.execution_grant.source_revision,
            )
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
        registry = WorkspaceRegistry(
            workspace_id=spec.workspace_id,
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
        )
        result = WorkspacePrepareResult(
            workspace_id=spec.workspace_id,
            repository_handle_id=spec.execution_grant.repository_handle_id,
            source_revision=spec.execution_grant.source_revision,
            workspace_fingerprint=workspace_fingerprint,
            initial_tree_hash=initial_tree_hash,
            current_tree_hash=initial_tree_hash,
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
        else:
            registry.pending_operation = pending_operation
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
            )
            status = self._authorized_status(spec, filesystem)
            if len(status) > spec.execution_grant.max_files_changed:
                raise WorkspaceExecutionError(FailureCode.FILE_COUNT_BUDGET_EXCEEDED)
            if outcome.created and outcome.relative_path not in registry.created_paths:
                registry.created_paths = sorted([*registry.created_paths, outcome.relative_path])
            registry.total_written_bytes += outcome.size
            checkpoint = self._checkpoint(spec, filesystem, status)
            registry.current_tree_hash = checkpoint.tree_fingerprint
            registry.pending_operation = None
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
            )
            self._cache_result(registry, operation_id, result)
            return result
        except Exception:
            if outcome is None:
                registry.pending_operation = None
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
        registry.current_tree_hash = current_tree_hash
        self._save_registry(registry)
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
        registry.current_tree_hash = checkpoint.tree_fingerprint
        self._save_registry(registry)
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
        )

    def _rollback(
        self,
        spec: WorkspaceRollbackJobSpec,
        registry: WorkspaceRegistry,
        filesystem: SafeWorkspaceFilesystem,
        *,
        operation_id: uuid.UUID,
    ) -> WorkspaceRollbackResult:
        status = self._authorized_status(spec, filesystem)
        tracked = [
            entry.relative_path
            for entry in status
            if entry.relative_path not in registry.created_paths
        ]
        self._git.restore_tracked(
            self._git.workspace_path(spec.workspace_id),
            spec.execution_grant.source_revision,
            tracked,
        )
        removed: list[str] = []
        for relative_path in registry.created_paths:
            if filesystem.remove_created_file(relative_path):
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
        result = WorkspaceRollbackResult(
            workspace_id=spec.workspace_id,
            clean=True,
            current_tree_hash=current_tree_hash,
            removed_created_paths=removed,
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
    ) -> WorkspaceDiscardResult:
        filesystem.verify_root_identity(
            registry.workspace_device,
            registry.workspace_inode,
        )
        mirror = self._git.mirror_path(registry.repository_opaque_handle)
        workspace = self._git.workspace_path(spec.workspace_id)
        self._git.discard_worktree(mirror, workspace)
        registry.local_state = "discarded"
        registry.pending_operation = None
        result = WorkspaceDiscardResult(
            workspace_id=spec.workspace_id,
            discarded=True,
            idempotent=False,
        )
        self._cache_result(registry, operation_id, result)
        return result

    def _discard_without_registry(
        self,
        spec: WorkspaceDiscardJobSpec,
        *,
        operation_id: uuid.UUID,
    ) -> WorkspaceDiscardResult:
        del operation_id
        workspace = self._git.workspace_path(spec.workspace_id)
        if workspace.exists():
            repository = self._repository_for(spec)
            mirror = self._git.prepare_mirror(
                spec.execution_grant.repository_opaque_handle,
                repository,
                spec.execution_grant.source_revision,
            )
            status = self._git.status(workspace, spec.execution_grant.source_revision)
            if status:
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
            self._git.discard_worktree(mirror, workspace)
        return WorkspaceDiscardResult(
            workspace_id=spec.workspace_id,
            discarded=True,
            idempotent=True,
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
        if (
            registry.workspace_id != spec.workspace_id
            or registry.grant_id != grant.id
            or registry.repository_handle_id != grant.repository_handle_id
            or registry.repository_opaque_handle != grant.repository_opaque_handle
            or registry.policy_hash != grant.policy_hash
            or registry.source_revision != grant.source_revision
        ):
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)

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
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_size > _MAX_REGISTRY_BYTES
            ):
                raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID)
            payload = os.read(descriptor, metadata.st_size + 1)
        finally:
            os.close(descriptor)
        try:
            return WorkspaceRegistry.model_validate_json(payload)
        except ValidationError as exc:
            raise WorkspaceExecutionError(FailureCode.WORKSPACE_STATE_INVALID) from exc

    def _save_registry(self, registry: WorkspaceRegistry) -> None:
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
            "source_is_dirty": metadata.source_is_dirty,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
