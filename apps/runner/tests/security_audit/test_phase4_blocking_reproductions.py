"""Closed, synthetic reproductions for Phase 4 independent audit findings.

These tests use only temporary repositories and harmless marker files. They
record current unsafe observations so the audit evidence is reproducible
without reaching any external repository, account, service, or network.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shlex
import subprocess
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import SecretStr

from visual_engineer_runner.client import ControlPlaneClient, ControlPlaneError
from visual_engineer_runner.config import LocalRepositoryConfig, RunnerSettings
from visual_engineer_runner.credentials import CredentialStore, RunnerCredential
from visual_engineer_runner.git_ops import GitOperations
from visual_engineer_runner.lifecycle import RunnerLifecycle
from visual_engineer_runner.workspace_manager import WorkspaceManager
from visual_engineer_runner_protocol import (
    Capability,
    CompleteRequest,
    ExecutionGrantPolicy,
    JobAssignment,
    JobState,
    LeaseMutationResponse,
    PermissionEnvelope,
    RenewRequest,
    RepositoryAccess,
    StartRequest,
    WorkspaceDiscardJobSpec,
    WorkspaceOperation,
    WorkspacePrepareJobSpec,
    WorkspaceWriteMode,
    WorkspaceWriteTextJobSpec,
    compute_execution_grant_policy_hash,
    compute_permission_policy_hash,
)

HANDLE = "audit-fixture-repository-v1"


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
    manager.execute(
        WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
        operation_id=uuid.uuid4(),
        cancel_event=threading.Event(),
    )


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


def test_source_local_fsmonitor_is_executed_by_current_git_adapter(tmp_path: Path) -> None:
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

    assert marker.is_file(), "current adapter unexpectedly blocked the synthetic fsmonitor marker"


def test_source_local_clean_filter_is_executed_by_current_git_adapter(tmp_path: Path) -> None:
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

    assert marker.is_file(), "current adapter unexpectedly blocked the synthetic filter marker"


def test_revocation_between_start_and_first_renew_allows_file_side_effect(
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
        runner_id=uuid.uuid4(),
        token=SecretStr("synthetic-runner-token-" + "x" * 32),
        protocol_version=1,
    )

    with pytest.raises(ControlPlaneError, match="execution_grant_inactive"):
        asyncio.run(lifecycle._execute_assignment(credential, assignment))

    assert control_plane.revoked is True
    assert control_plane.renew_calls == 0
    assert control_plane.complete_calls == 1
    assert target.read_text(encoding="utf-8") == "changed after revocation\n"


def test_registry_missing_discard_deletes_unknown_ignored_file(tmp_path: Path) -> None:
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
    manager.execute(
        WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant),
        operation_id=uuid.uuid4(),
        cancel_event=threading.Event(),
    )

    assert not workspace.exists()
    assert not unknown.exists()
