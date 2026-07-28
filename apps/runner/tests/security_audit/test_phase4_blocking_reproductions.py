"""Closed regression tests for the remediated Phase 4 audit findings.

These tests use only temporary repositories and harmless marker files. They
prove the formerly blocking observations now fail closed without reaching any
external repository, account, service, or network.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import SecretStr

from visual_engineer_runner.client import ControlPlaneClient, ControlPlaneError
from visual_engineer_runner.config import LocalRepositoryConfig, RunnerSettings
from visual_engineer_runner.credentials import CredentialStore, RunnerCredential
from visual_engineer_runner.git_ops import GitOperationError, GitOperations
from visual_engineer_runner.lifecycle import RunnerLifecycle
from visual_engineer_runner.workspace_manager import WorkspaceExecutionError, WorkspaceManager
from visual_engineer_runner_protocol import (
    Capability,
    CompleteRequest,
    ExecutionGrantPolicy,
    FailureCode,
    JobAssignment,
    JobState,
    LeaseMutationResponse,
    PermissionEnvelope,
    RenewRequest,
    RepositoryAccess,
    SideEffectPermit,
    SideEffectPermitAcquireRequest,
    StartRequest,
    WorkspaceDiscardJobSpec,
    WorkspaceOperation,
    WorkspacePrepareJobSpec,
    WorkspaceWriteMode,
    WorkspaceWriteTextJobSpec,
    compute_execution_grant_policy_hash,
    compute_permission_policy_hash,
    compute_side_effect_job_digest,
    compute_side_effect_permit_digest,
    side_effect_job_binding,
)

HANDLE = "audit-fixture-repository-v1"
RUNNER_ID = uuid.UUID("470122aa-6ab7-5b22-8e2c-183367f363ee")


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _source_repository(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.name", "Audit Fixture")
    _git(source, "config", "user.email", "audit@example.invalid")
    (source / ".gitignore").write_text("ignored-runtime\n", encoding="utf-8")
    sandbox = source / "sandbox"
    sandbox.mkdir()
    (sandbox / "tracked.txt").write_text("original\n", encoding="utf-8")
    _git(source, "add", ".gitignore", "sandbox/tracked.txt")
    _git(source, "commit", "-m", "synthetic audit fixture")
    return source, _git(source, "rev-parse", "HEAD")


def _settings(
    tmp_path: Path,
    source: Path,
    *,
    write_commit_delay_ms: int = 0,
) -> RunnerSettings:
    return RunnerSettings(
        credential_path=tmp_path / "runner-state" / "credential.json",
        repository_handles={
            HANDLE: LocalRepositoryConfig(path=source, display_name="Synthetic Audit Fixture")
        },
        mirror_root=tmp_path / "runner-state" / "mirrors",
        workspace_root=tmp_path / "runner-state" / "workspaces",
        registry_root=tmp_path / "runner-state" / "registry",
        require_source_read_only=False,
        workspace_write_commit_delay_ms=write_commit_delay_ms,
    )


def _grant(revision: str) -> ExecutionGrantPolicy:
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "run_id": uuid.uuid4(),
        "plan_id": uuid.uuid4(),
        "repository_handle_id": uuid.uuid4(),
        "repository_opaque_handle": HANDLE,
        "source_revision": revision,
        "snapshot_fingerprint": hashlib.sha256(b"synthetic-audit-snapshot").hexdigest(),
        "allowed_operations": list(WorkspaceOperation),
        "allowed_paths": ["sandbox/**"],
        "denied_paths": [
            ".git",
            ".git/**",
            ".env",
            ".env.*",
            "**/.env",
            "**/.env.*",
            "**/*credential*",
            "**/*secret*",
            "**/*token*",
            "**/*.key",
            "**/*.pem",
        ],
        "max_files_changed": 8,
        "max_total_write_bytes": 128 * 1024,
        "max_single_file_bytes": 32 * 1024,
        "max_diff_bytes": 32 * 1024,
        "workspace_ttl_seconds": 20 * 60,
        "expires_at": datetime.now(UTC) + timedelta(minutes=30),
        "policy_hash": "0" * 64,
    }
    draft = ExecutionGrantPolicy.model_validate(values)
    values["policy_hash"] = compute_execution_grant_policy_hash(draft)
    return ExecutionGrantPolicy.model_validate(values)


def _execute_prepare(
    manager: WorkspaceManager,
    workspace_id: uuid.UUID,
    grant: ExecutionGrantPolicy,
) -> None:
    operation_id = uuid.uuid4()
    spec = WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant)
    manager.execute(
        spec,
        operation_id=operation_id,
        cancel_event=threading.Event(),
        side_effect_permit=_permit(spec, operation_id=operation_id),
    )


def _permit(
    spec: WorkspacePrepareJobSpec | WorkspaceDiscardJobSpec | WorkspaceWriteTextJobSpec,
    *,
    operation_id: uuid.UUID,
    expected_current: str | None = None,
) -> SideEffectPermit:
    binding = side_effect_job_binding(spec)
    resolved_expected = expected_current or binding["expected_current"]
    assert resolved_expected is not None
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "id": uuid.uuid5(operation_id, "side-effect-permit"),
        "sequence": 1,
        "runner_id": RUNNER_ID,
        "job_id": operation_id,
        "attempt_id": uuid.uuid5(operation_id, "attempt"),
        "lease_id": uuid.uuid5(operation_id, "lease"),
        "grant_id": spec.execution_grant.id,
        "workspace_id": spec.workspace_id,
        "repository_handle_id": spec.execution_grant.repository_handle_id,
        "operation": binding["operation"],
        "relative_path": binding["relative_path"],
        "expected_current": resolved_expected,
        "proposed_digest": binding["proposed_digest"],
        "job_digest": compute_side_effect_job_digest(spec),
        "operation_digest": "0" * 64,
        "policy_hash": spec.execution_grant.policy_hash,
        "source_revision": spec.execution_grant.source_revision,
        "issued_at": now,
        "consumed_at": now,
        "expires_at": now + timedelta(minutes=1),
        "state": "consumed",
    }
    values["operation_digest"] = compute_side_effect_permit_digest(values)
    return SideEffectPermit.model_validate(values)


def _permission_envelope(job_id: uuid.UUID) -> PermissionEnvelope:
    now = datetime.now(UTC)
    values: dict[str, object] = {
        "id": uuid.uuid4(),
        "job_id": job_id,
        "authorization_source": "execution_grant",
        "allowed_capabilities": [Capability.WORKSPACE_WRITE_TEXT_V1],
        "repository_access": RepositoryAccess.ISOLATED_WORKSPACE,
        "max_runtime_seconds": 30,
        "lease_seconds": 6,
        "max_attempts": 2,
        "max_result_bytes": 64 * 1024,
        "issued_at": now,
        "expires_at": now + timedelta(minutes=5),
        "policy_hash": "0" * 64,
    }
    draft = PermissionEnvelope.model_validate(values)
    values["policy_hash"] = compute_permission_policy_hash(draft)
    return PermissionEnvelope.model_validate(values)


class _RevokingControlPlane(ControlPlaneClient):
    """Minimal in-process authority simulator; it performs no network I/O."""

    def __init__(self) -> None:
        self.revoked = False
        self.renew_calls = 0
        self.complete_calls = 0

    async def start(
        self,
        job_id: uuid.UUID,
        payload: StartRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        del token
        self.revoked = True
        return LeaseMutationResponse(
            job_id=job_id,
            attempt_id=payload.attempt_id,
            state=JobState.RUNNING,
            leased_until=datetime.now(UTC) + timedelta(seconds=6),
            cancel_requested=False,
        )

    async def renew(
        self,
        job_id: uuid.UUID,
        payload: RenewRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        del token
        self.renew_calls += 1
        return LeaseMutationResponse(
            job_id=job_id,
            attempt_id=payload.attempt_id,
            state=JobState.CANCEL_REQUESTED,
            leased_until=datetime.now(UTC) + timedelta(seconds=6),
            cancel_requested=True,
        )

    async def acquire_side_effect_permit(
        self,
        job_id: uuid.UUID,
        payload: SideEffectPermitAcquireRequest,
        token: SecretStr,
    ) -> SideEffectPermit:
        del job_id, payload, token
        if self.revoked:
            raise ControlPlaneError(409, "execution_grant_inactive")
        raise AssertionError("the synthetic authority must be revoked")

    async def complete(
        self,
        job_id: uuid.UUID,
        payload: CompleteRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        del job_id, payload, token
        self.complete_calls += 1
        if self.revoked:
            raise ControlPlaneError(409, "execution_grant_inactive")
        raise AssertionError("the synthetic authority must be revoked")


def test_source_local_fsmonitor_is_not_executed_by_git_adapter(tmp_path: Path) -> None:
    source, _ = _source_repository(tmp_path)
    marker = tmp_path / "fsmonitor-marker"
    helper = tmp_path / "fsmonitor-helper"
    helper.write_text(
        f"#!/bin/sh\n: > {shlex.quote(str(marker))}\nprintf '0\\n'\n",
        encoding="utf-8",
    )
    helper.chmod(0o700)
    _git(source, "config", "core.fsmonitor", str(helper))

    settings = _settings(tmp_path, source)
    GitOperations(settings).inspect_source(settings.repository_handles[HANDLE])

    assert not marker.exists()


def test_source_local_clean_filter_is_not_executed_by_git_adapter(tmp_path: Path) -> None:
    source, _ = _source_repository(tmp_path)
    marker = tmp_path / "filter-marker"
    helper = tmp_path / "filter-helper"
    helper.write_text(
        f"#!/bin/sh\n: > {shlex.quote(str(marker))}\nexec /bin/cat\n",
        encoding="utf-8",
    )
    helper.chmod(0o700)
    (source / ".gitattributes").write_text("sandbox/tracked.txt filter=audit\n", encoding="utf-8")
    _git(source, "add", ".gitattributes")
    _git(source, "commit", "-m", "add synthetic clean-filter declaration")
    _git(source, "config", "filter.audit.clean", str(helper))
    _git(source, "config", "filter.audit.required", "true")
    tracked = source / "sandbox" / "tracked.txt"
    tracked.write_text(tracked.read_text(encoding="utf-8"), encoding="utf-8")

    settings = _settings(tmp_path, source)
    GitOperations(settings).inspect_source(settings.repository_handles[HANDLE])

    assert not marker.exists()


def test_revocation_between_start_and_permit_denies_file_side_effect(
    tmp_path: Path,
) -> None:
    source, revision = _source_repository(tmp_path)
    settings = _settings(tmp_path, source, write_commit_delay_ms=100)
    manager = WorkspaceManager(settings)
    grant = _grant(revision)
    workspace_id = uuid.uuid4()
    _execute_prepare(manager, workspace_id, grant)
    workspace = settings.workspace_root / f"workspace-{workspace_id.hex}"
    target = workspace / "sandbox" / "tracked.txt"

    job_id = uuid.uuid4()
    now = datetime.now(UTC)
    assignment = JobAssignment(
        job_id=job_id,
        attempt_id=uuid.uuid4(),
        lease_id=uuid.uuid4(),
        attempt_number=1,
        job=WorkspaceWriteTextJobSpec(
            workspace_id=workspace_id,
            execution_grant=grant,
            mode=WorkspaceWriteMode.REPLACE,
            relative_path="sandbox/tracked.txt",
            content="changed after revocation\n",
            expected_sha256=hashlib.sha256(b"original\n").hexdigest(),
        ),
        permission_envelope=_permission_envelope(job_id),
        leased_until=now + timedelta(seconds=6),
    )
    control_plane = _RevokingControlPlane()
    lifecycle = RunnerLifecycle(
        settings,
        control_plane,
        CredentialStore(settings.credential_path),
        workspace_manager=manager,
    )
    credential = RunnerCredential(
        runner_id=RUNNER_ID,
        token=SecretStr("synthetic-runner-token-" + "x" * 32),
        protocol_version=1,
    )

    with pytest.raises(ControlPlaneError, match="execution_grant_inactive"):
        asyncio.run(lifecycle._execute_assignment(credential, assignment))

    assert control_plane.revoked is True
    assert control_plane.renew_calls == 0
    assert control_plane.complete_calls == 0
    assert target.read_text(encoding="utf-8") == "original\n"


def test_registry_missing_discard_requires_recovery_and_preserves_unknown_file(
    tmp_path: Path,
) -> None:
    source, revision = _source_repository(tmp_path)
    settings = _settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = _grant(revision)
    workspace_id = uuid.uuid4()
    _execute_prepare(manager, workspace_id, grant)
    workspace = settings.workspace_root / f"workspace-{workspace_id.hex}"
    unknown = workspace / "sandbox" / "ignored-runtime"
    unknown.write_text("unknown audit-owned content\n", encoding="utf-8")
    assert _git(workspace, "status", "--porcelain=v1") == ""

    registry = settings.registry_root / f"workspace-{workspace_id.hex}.json"
    os.unlink(registry)
    operation_id = uuid.uuid4()
    spec = WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant)
    with pytest.raises(WorkspaceExecutionError) as error:
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=_permit(
                spec,
                operation_id=operation_id,
                expected_current="0" * 64,
            ),
        )

    assert error.value.code == FailureCode.WORKSPACE_RECOVERY_REQUIRED
    assert workspace.is_dir()
    assert unknown.read_text(encoding="utf-8") == "unknown audit-owned content\n"


def test_reaudit_unreachable_uncommitted_object_is_not_imported_into_mirror(
    tmp_path: Path,
) -> None:
    """VE-P4-AUD-001: import only the approved revision's reachable closure."""

    source, revision = _source_repository(tmp_path)
    uncommitted = source / "sandbox" / "uncommitted-object.txt"
    uncommitted.write_text("unapproved object payload\n", encoding="utf-8")
    object_id = _git(source, "hash-object", "-w", "sandbox/uncommitted-object.txt")
    assert _git(source, "status", "--porcelain=v1") == "?? sandbox/uncommitted-object.txt"

    settings = _settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    workspace_id = uuid.uuid4()
    _execute_prepare(manager, workspace_id, _grant(revision))

    mirror_object = manager._git.mirror_path(HANDLE) / "objects" / object_id[:2] / object_id[2:]
    workspace = manager._git.workspace_path(workspace_id)
    assert not (workspace / "sandbox" / "uncommitted-object.txt").exists()
    assert not mirror_object.exists()


def test_reaudit_registry_loss_and_absent_root_requires_signed_recovery_proof(
    tmp_path: Path,
) -> None:
    """VE-P4-AUD-003: absence alone is not authenticated discard completion."""

    source, revision = _source_repository(tmp_path)
    settings = _settings(tmp_path, source)
    manager = WorkspaceManager(settings)
    grant = _grant(revision)
    workspace_id = uuid.uuid4()
    _execute_prepare(manager, workspace_id, grant)
    registry = manager._load_registry(workspace_id)
    assert registry is not None

    workspace = manager._git.workspace_path(workspace_id)
    preserved = workspace.with_name(f"{workspace.name}-preserved-by-reaudit")
    workspace.rename(preserved)
    manager._registry_path(workspace_id).unlink()

    operation_id = uuid.uuid4()
    spec = WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant)
    with pytest.raises(WorkspaceExecutionError) as error:
        manager.execute(
            spec,
            operation_id=operation_id,
            cancel_event=threading.Event(),
            side_effect_permit=_permit(
                spec,
                operation_id=operation_id,
                expected_current=registry.current_tree_hash,
            ),
        )

    assert error.value.code == FailureCode.WORKSPACE_RECOVERY_REQUIRED
    assert preserved.is_dir()


def test_reaudit_timeout_kills_process_group_after_leader_exits(tmp_path: Path) -> None:
    """VE-P4-AUD-005: a timed-out subprocess group must leave no orphan."""

    source, _ = _source_repository(tmp_path)
    operations = GitOperations(_settings(tmp_path, source))
    marker = tmp_path / "orphan-child-marker"
    child_code = f"import pathlib,time;time.sleep(0.4);pathlib.Path({str(marker)!r}).touch()"
    parent_code = f"import subprocess,sys;subprocess.Popen([sys.executable, '-c', {child_code!r}])"
    process = subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        with pytest.raises(GitOperationError) as error:
            operations._collect_bounded_output(
                process,
                timeout_seconds=0.05,
                timeout_failure=FailureCode.WORKSPACE_STATE_INVALID,
            )
        assert error.value.code == FailureCode.WORKSPACE_STATE_INVALID
        time.sleep(0.6)
        assert not marker.exists()
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=1)
