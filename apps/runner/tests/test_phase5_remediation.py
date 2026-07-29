from __future__ import annotations

import asyncio
import hashlib
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import SecretStr

import visual_engineer_runner.lifecycle as lifecycle_module
from visual_engineer_runner.client import ControlPlaneClient
from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.credentials import CredentialStore, RunnerCredential
from visual_engineer_runner.lifecycle import RunnerLifecycle
from visual_engineer_runner.validation_executor import _TIMEOUT_EXIT, ValidationExecutor
from visual_engineer_runner.workspace_manager import (
    WorkspaceExecutionError,
    WorkspaceManager,
)
from visual_engineer_runner_protocol import (
    Capability,
    ExecutionGrantPolicy,
    JobAssignment,
    JobState,
    LeaseMutationResponse,
    NetworkPolicy,
    PermissionEnvelope,
    RepositoryAccess,
    SideEffectPermit,
    SideEffectPermitState,
    ValidationExecuteJobSpec,
    WorkspaceOperation,
    compute_execution_grant_policy_hash,
    compute_permission_policy_hash,
    compute_side_effect_job_digest,
    compute_side_effect_permit_digest,
    side_effect_job_binding,
)

_CHECKPOINT_FINGERPRINT = hashlib.sha256(b"phase5-remediation-checkpoint").hexdigest()
_SOURCE_REVISION = "a" * 40


def _validation_grant(
    workspace_id: uuid.UUID,
    checkpoint_id: uuid.UUID,
) -> ExecutionGrantPolicy:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "run_id": uuid.uuid4(),
        "plan_id": uuid.uuid4(),
        "repository_handle_id": uuid.uuid4(),
        "repository_opaque_handle": "phase5-remediation-fixture",
        "source_revision": _SOURCE_REVISION,
        "snapshot_fingerprint": hashlib.sha256(b"phase5-remediation-snapshot").hexdigest(),
        "allowed_operations": [WorkspaceOperation.VALIDATE],
        "allowed_paths": ["sandbox/**"],
        "denied_paths": [".git", ".git/**", ".env", "**/.env", "**/*secret*"],
        "max_files_changed": 1,
        "max_total_write_bytes": 4096,
        "max_single_file_bytes": 4096,
        "max_diff_bytes": 1,
        "workspace_ttl_seconds": 1200,
        "network_policy": "none",
        "shell_access": False,
        "git_delivery_access": False,
        "source_repository_write_access": False,
        "validation_workspace_id": workspace_id,
        "validation_checkpoint_id": checkpoint_id,
        "allowed_validation_profiles": ["fixture-python-stdlib-v1:v1"],
        "max_validation_runs": 1,
        "validation_timeout_seconds": 10,
        "validation_cpu_seconds": 5,
        "validation_memory_bytes": 128 * 1024 * 1024,
        "validation_pid_limit": 8,
        "validation_fd_limit": 64,
        "validation_output_bytes": 8192,
        "validation_artifact_bytes": 0,
        "validation_artifact_count": 0,
        "expires_at": datetime.now(UTC) + timedelta(minutes=5),
        "policy_hash": "0" * 64,
    }
    draft = ExecutionGrantPolicy.model_validate(values)
    values["policy_hash"] = compute_execution_grant_policy_hash(draft)
    return ExecutionGrantPolicy.model_validate(values)


def _validation_assignment() -> JobAssignment:
    workspace_id = uuid.uuid4()
    checkpoint_id = uuid.uuid4()
    spec = ValidationExecuteJobSpec(
        validation_run_id=uuid.uuid4(),
        workspace_id=workspace_id,
        execution_grant=_validation_grant(workspace_id, checkpoint_id),
        checkpoint_id=checkpoint_id,
        checkpoint_fingerprint=_CHECKPOINT_FINGERPRINT,
        timeout_seconds=10,
        max_output_bytes=8192,
        max_artifact_bytes=0,
        max_artifact_count=0,
    )
    job_id = uuid.uuid4()
    now = datetime.now(UTC)
    envelope_values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "job_id": job_id,
        "authorization_source": "execution_grant",
        "allowed_capabilities": [Capability.VALIDATION_EXECUTE_V1],
        "repository_access": RepositoryAccess.ISOLATED_WORKSPACE,
        "shell_access": False,
        "network_policy": NetworkPolicy.CONTROL_PLANE_ONLY,
        "max_runtime_seconds": 20,
        "lease_seconds": 2,
        "max_attempts": 2,
        "max_result_bytes": 64 * 1024,
        "issued_at": now,
        "expires_at": now + timedelta(minutes=5),
        "policy_hash": "0" * 64,
    }
    draft = PermissionEnvelope.model_validate(envelope_values)
    envelope_values["policy_hash"] = compute_permission_policy_hash(draft)
    return JobAssignment(
        job_id=job_id,
        attempt_id=uuid.uuid4(),
        lease_id=uuid.uuid4(),
        attempt_number=1,
        job=spec,
        permission_envelope=PermissionEnvelope.model_validate(envelope_values),
        leased_until=now + timedelta(seconds=2),
    )


def _validation_permit(
    assignment: JobAssignment,
    runner_id: uuid.UUID,
) -> SideEffectPermit:
    assert isinstance(assignment.job, ValidationExecuteJobSpec)
    spec = assignment.job
    binding = side_effect_job_binding(spec)
    now = datetime.now(UTC)
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "sequence": 1,
        "runner_id": runner_id,
        "job_id": assignment.job_id,
        "attempt_id": assignment.attempt_id,
        "lease_id": assignment.lease_id,
        "grant_id": spec.execution_grant.id,
        "workspace_id": spec.workspace_id,
        "repository_handle_id": spec.execution_grant.repository_handle_id,
        "operation": WorkspaceOperation.VALIDATE,
        "relative_path": None,
        "expected_current": binding["expected_current"],
        "proposed_digest": binding["proposed_digest"],
        "job_digest": compute_side_effect_job_digest(spec),
        "operation_digest": "0" * 64,
        "policy_hash": spec.execution_grant.policy_hash,
        "source_revision": spec.execution_grant.source_revision,
        "issued_at": now,
        "consumed_at": now,
        "expires_at": now + timedelta(seconds=2),
        "state": SideEffectPermitState.CONSUMED,
    }
    draft = SideEffectPermit.model_validate(values)
    values["operation_digest"] = compute_side_effect_permit_digest(draft)
    return SideEffectPermit.model_validate(values)


class _CancelCleanupClient:
    def __init__(self, assignment: JobAssignment, permit: SideEffectPermit) -> None:
        self.assignment = assignment
        self.permit = permit
        self.cancelled_calls = 0
        self.failure_codes: list[str] = []

    def _response(self, *, cancel_requested: bool) -> LeaseMutationResponse:
        return LeaseMutationResponse(
            job_id=self.assignment.job_id,
            attempt_id=self.assignment.attempt_id,
            state=(JobState.CANCEL_REQUESTED if cancel_requested else JobState.RUNNING),
            leased_until=datetime.now(UTC) + timedelta(seconds=2),
            cancel_requested=cancel_requested,
        )

    async def start(self, *_: object, **__: object) -> LeaseMutationResponse:
        return self._response(cancel_requested=False)

    async def acquire_side_effect_permit(self, *_: object, **__: object) -> SideEffectPermit:
        return self.permit

    async def renew(self, *_: object, **__: object) -> LeaseMutationResponse:
        return self._response(cancel_requested=True)

    async def cancelled(self, *_: object, **__: object) -> LeaseMutationResponse:
        self.cancelled_calls += 1
        return self._response(cancel_requested=True)

    async def fail(self, _: object, payload: object, *__: object) -> LeaseMutationResponse:
        self.failure_codes.append(cast(Any, payload).error_code.value)
        return self._response(cancel_requested=False)

    async def complete(self, *_: object, **__: object) -> LeaseMutationResponse:
        raise AssertionError("cleanup failure must not complete")


def test_timeout_reaps_term_ignoring_descendant_after_leader_exit(tmp_path: Path) -> None:
    """VE-P5-FSR-001: leader exit cannot bypass bounded group termination."""

    child_ready = tmp_path / "descendant-ready"
    marker = tmp_path / "descendant-survived"
    child_code = (
        "import pathlib,signal,time;"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN);"
        f"pathlib.Path({str(child_ready)!r}).touch();"
        "time.sleep(2);"
        f"pathlib.Path({str(marker)!r}).touch()"
    )
    parent_code = (
        "import pathlib,subprocess,sys,time\n"
        f"subprocess.Popen([sys.executable,'-I','-S','-c',{child_code!r}])\n"
        f"p=pathlib.Path({str(child_ready)!r})\n"
        "deadline=time.monotonic()+1\n"
        "while not p.exists() and time.monotonic()<deadline:\n"
        "    time.sleep(0.01)\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", parent_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
    )
    started = time.monotonic()
    try:
        result = ValidationExecutor._collect(
            process,
            timeout_seconds=0.1,
            output_limit=1024,
            cancel_event=threading.Event(),
        )
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)

    assert time.monotonic() - started < 1.25
    assert result[0] == _TIMEOUT_EXIT
    assert result[5] is True
    time.sleep(0.85)
    assert not marker.exists()


def test_cancel_cleanup_failure_is_reported_instead_of_acknowledged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VE-P5-FSR-002: typed cleanup failure wins the cancel race."""

    assignment = _validation_assignment()
    runner_id = uuid.uuid4()
    permit = _validation_permit(assignment, runner_id)
    fake = _CancelCleanupClient(assignment, permit)

    async def cleanup_failure(*_: object, **kwargs: object) -> object:
        cancel_event = cast(threading.Event, kwargs["cancel_event"])
        await asyncio.to_thread(cancel_event.wait)
        raise WorkspaceExecutionError(lifecycle_module.FailureCode.VALIDATION_CLEANUP_FAILED)

    monkeypatch.setattr(lifecycle_module, "execute_job", cleanup_failure)
    settings = RunnerSettings(
        control_plane_url="http://control-plane.test",
        credential_path=tmp_path / "credentials" / "credentials.json",
        ownership_key_path=tmp_path / "credentials" / "ownership.key",
        mirror_root=tmp_path / "mirrors",
        workspace_root=tmp_path / "workspaces",
        registry_root=tmp_path / "registry",
        validation_root=tmp_path / "validations",
        repository_handles={},
    )
    lifecycle = RunnerLifecycle(
        settings,
        cast(ControlPlaneClient, fake),
        CredentialStore(settings.credential_path),
        workspace_manager=cast(WorkspaceManager, object()),
    )
    credential = RunnerCredential(
        runner_id=runner_id,
        token=SecretStr("phase5-remediation-runner-token-" + "x" * 32),
        protocol_version=1,
    )

    asyncio.run(lifecycle._execute_assignment(credential, assignment))

    assert fake.cancelled_calls == 0
    assert fake.failure_codes == ["validation_cleanup_failed"]
