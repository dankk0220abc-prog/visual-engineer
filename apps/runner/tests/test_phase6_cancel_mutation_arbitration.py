from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest
from pydantic import SecretStr

import visual_engineer_runner.lifecycle as lifecycle_module
from visual_engineer_runner.client import ControlPlaneClient, ControlPlaneError
from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.credentials import CredentialStore, RunnerCredential
from visual_engineer_runner.lifecycle import RunnerLifecycle
from visual_engineer_runner_protocol import (
    Capability,
    DeliveryAuthorizationPolicy,
    ExecutionGrantPolicy,
    JobAssignment,
    JobState,
    LeaseMutationResponse,
    LocalDeliveryManifest,
    PermissionEnvelope,
    RepositoryAccess,
    WorkspaceGitCommitJobSpec,
    WorkspaceOperation,
    compute_delivery_authorization_policy_hash,
    compute_execution_grant_policy_hash,
    compute_local_delivery_manifest_digest,
    compute_permission_policy_hash,
)


def _delivery_assignment() -> JobAssignment:
    now = datetime.now(UTC)
    workspace_id = uuid.uuid4()
    checkpoint_id = uuid.uuid4()
    checkpoint_fingerprint = "1" * 64
    checkpoint_diff_hash = "2" * 64
    grant_values: dict[str, object] = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "run_id": uuid.uuid4(),
        "plan_id": uuid.uuid4(),
        "repository_handle_id": uuid.uuid4(),
        "repository_opaque_handle": "fixture-repository-v1",
        "source_revision": "a" * 40,
        "snapshot_fingerprint": "b" * 64,
        "allowed_operations": list(WorkspaceOperation),
        "allowed_paths": ["sandbox/**"],
        "denied_paths": [".git", ".git/**"],
        "max_files_changed": 8,
        "max_total_write_bytes": 128 * 1024,
        "max_single_file_bytes": 32 * 1024,
        "max_diff_bytes": 32 * 1024,
        "workspace_ttl_seconds": 20 * 60,
        "expires_at": now + timedelta(minutes=30),
        "policy_hash": "0" * 64,
    }
    grant_draft = ExecutionGrantPolicy.model_validate(grant_values)
    grant_values["policy_hash"] = compute_execution_grant_policy_hash(grant_draft)
    grant = ExecutionGrantPolicy.model_validate(grant_values)
    authorization_id = uuid.uuid4()
    authorization_values: dict[str, object] = {
        "id": authorization_id,
        "review_package_id": uuid.uuid4(),
        "review_decision_id": uuid.uuid4(),
        "readiness_verdict_id": uuid.uuid4(),
        "freshness_generation": 1,
        "package_digest": "1" * 64,
        "decision_digest": "2" * 64,
        "readiness_digest": "3" * 64,
        "workspace_id": workspace_id,
        "checkpoint_id": checkpoint_id,
        "checkpoint_fingerprint": checkpoint_fingerprint,
        "checkpoint_diff_hash": checkpoint_diff_hash,
        "repository_handle_id": grant.repository_handle_id,
        "source_revision": grant.source_revision,
        "branch_ref": f"refs/heads/visual-engineer/{workspace_id.hex}",
        "commit_message": (f"VisualEngineer: governed local delivery {authorization_id.hex[:8]}"),
        "commit_timestamp": now,
        "expires_at": now + timedelta(minutes=5),
        "policy_hash": "0" * 64,
    }
    authorization_draft = DeliveryAuthorizationPolicy.model_validate(authorization_values)
    authorization_values["policy_hash"] = compute_delivery_authorization_policy_hash(
        authorization_draft
    )
    authorization = DeliveryAuthorizationPolicy.model_validate(authorization_values)
    manifest = LocalDeliveryManifest(
        delivery_authorization_id=authorization.id,
        workspace_id=workspace_id,
        checkpoint_id=checkpoint_id,
        checkpoint_fingerprint=checkpoint_fingerprint,
        checkpoint_diff_hash=checkpoint_diff_hash,
        source_revision=grant.source_revision,
        branch_ref=authorization.branch_ref,
        commit_message=authorization.commit_message,
        changed_paths=["sandbox/tracked.txt"],
        changed_file_count=1,
        total_diff_bytes=1,
        manifest_digest="0" * 64,
    )
    manifest.manifest_digest = compute_local_delivery_manifest_digest(manifest)
    job = WorkspaceGitCommitJobSpec(
        workspace_id=workspace_id,
        execution_grant=grant,
        delivery_authorization=authorization,
        delivery_dispatch_id=uuid.uuid4(),
        delivery_attempt_number=1,
        delivery_manifest=manifest,
        checkpoint_id=checkpoint_id,
        checkpoint_fingerprint=checkpoint_fingerprint,
        checkpoint_diff_hash=checkpoint_diff_hash,
    )
    job_id = uuid.uuid4()
    values = {
        "id": uuid.uuid4(),
        "job_id": job_id,
        "authorization_source": "execution_grant_and_delivery_authorization",
        "allowed_capabilities": [Capability.WORKSPACE_GIT_COMMIT_V1],
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
    return JobAssignment(
        job_id=job_id,
        attempt_id=uuid.uuid4(),
        lease_id=uuid.uuid4(),
        attempt_number=1,
        job=job,
        permission_envelope=PermissionEnvelope.model_validate(values),
        leased_until=now + timedelta(seconds=6),
    )


class CancelBeforePermitClient:
    def __init__(self, assignment: JobAssignment) -> None:
        self.assignment = assignment
        self.acquire_calls = 0
        self.renew_calls = 0
        self.cancelled_calls = 0

    def _response(self, state: JobState, *, cancel_requested: bool) -> LeaseMutationResponse:
        return LeaseMutationResponse(
            job_id=self.assignment.job_id,
            attempt_id=self.assignment.attempt_id,
            state=state,
            leased_until=datetime.now(UTC) + timedelta(seconds=5),
            cancel_requested=cancel_requested,
        )

    async def start(self, *_: object, **__: object) -> LeaseMutationResponse:
        return self._response(JobState.RUNNING, cancel_requested=False)

    async def acquire_side_effect_permit(self, *_: object, **__: object) -> None:
        self.acquire_calls += 1
        raise ControlPlaneError(409, "stale_lease")

    async def renew(self, *_: object, **__: object) -> LeaseMutationResponse:
        self.renew_calls += 1
        return self._response(JobState.CANCEL_REQUESTED, cancel_requested=True)

    async def cancelled(self, *_: object, **__: object) -> LeaseMutationResponse:
        self.cancelled_calls += 1
        return self._response(JobState.CANCELLED, cancel_requested=True)


def test_cancel_winner_is_acknowledged_before_git_executor_or_temp_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assignment = _delivery_assignment()
    credential = RunnerCredential(
        runner_id=uuid.uuid4(),
        token=SecretStr("dynamic-" + "c" * 48),
        protocol_version=1,
    )
    client = CancelBeforePermitClient(assignment)
    executed = threading.Event()

    async def forbidden_execute(*_: object, **__: object) -> object:
        executed.set()
        raise AssertionError("Git executor must not start after cancellation wins")

    monkeypatch.setattr(lifecycle_module, "execute_job", forbidden_execute)
    settings = RunnerSettings(
        credential_path=tmp_path / "credential.json",
        mirror_root=tmp_path / "mirrors",
        workspace_root=tmp_path / "workspaces",
        registry_root=tmp_path / "registry",
    )
    lifecycle = RunnerLifecycle(
        settings,
        cast(ControlPlaneClient, client),
        CredentialStore(settings.credential_path),
    )

    asyncio.run(lifecycle._execute_assignment(credential, assignment))

    assert client.acquire_calls == 1
    assert client.renew_calls == 1
    assert client.cancelled_calls == 1
    assert not executed.is_set()
    assert not settings.mirror_root.exists()
    assert not settings.workspace_root.exists()
    assert not settings.registry_root.exists()
