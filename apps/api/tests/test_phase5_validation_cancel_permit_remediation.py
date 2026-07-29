from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_phase5_control_plane_remediation import _governed_result
from test_phase5_focused_security_review import _post_completion, _prepare_validation_job
from test_workspace_api import runner_headers
from visual_engineer_api.models.runner import RunnerJob, RunnerJobAttempt, RunnerJobEvent
from visual_engineer_api.models.validation import (
    ValidationEvidence,
    ValidationRun,
    ValidationStepRun,
)
from visual_engineer_api.models.workspace import ExecutionGrant, SideEffectPermit, Workspace


def _event_count(db_session: Session, job_id: str, event_type: str) -> int:
    return int(
        db_session.scalar(
            select(func.count(RunnerJobEvent.id)).where(
                RunnerJobEvent.job_id == uuid.UUID(job_id),
                RunnerJobEvent.event_type == event_type,
            )
        )
        or 0
    )


def test_validation_cancel_atomically_terminalizes_exact_permit_and_replays_once(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    target = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    unrelated = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    late_result = _governed_result(db_session, target)
    target_run = db_session.get(ValidationRun, uuid.UUID(target.validation_run_id))
    assert target_run is not None

    revoked = client.post(f"/api/v1/execution-grants/{target_run.execution_grant_id}/revoke")
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoke_requested"
    requested = client.post(
        f"/api/v1/validation-runs/{target.validation_run_id}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert requested.status_code == 200, requested.text
    assert requested.json()["state"] == "cancel_requested"
    acknowledged = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{target.job_id}/cancelled",
        headers=runner_headers(target.token),
        json=target.identity,
    )
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["state"] == "cancelled"

    db_session.expire_all()
    job = db_session.get(RunnerJob, uuid.UUID(target.job_id))
    attempt = db_session.get(RunnerJobAttempt, uuid.UUID(target.identity["attempt_id"]))
    permit = db_session.get(SideEffectPermit, uuid.UUID(target.permit_id))
    unrelated_permit = db_session.get(SideEffectPermit, uuid.UUID(unrelated.permit_id))
    validation_run = db_session.get(ValidationRun, uuid.UUID(target.validation_run_id))
    step = db_session.scalar(
        select(ValidationStepRun).where(
            ValidationStepRun.validation_run_id == uuid.UUID(target.validation_run_id)
        )
    )
    workspace = db_session.get(Workspace, uuid.UUID(target.workspace_id))
    grant = (
        db_session.get(ExecutionGrant, validation_run.execution_grant_id)
        if validation_run is not None
        else None
    )
    assert job is not None and job.state == "cancelled" and job.result is None
    assert attempt is not None and attempt.state == "cancelled"
    assert permit is not None and permit.state == "cancelled" and permit.terminal_at is not None
    assert unrelated_permit is not None and unrelated_permit.state == "consumed"
    assert validation_run is not None and validation_run.state == "cancelled"
    assert validation_run.completed_at is not None
    assert step is not None and step.state == "cancelled" and step.completed_at is not None
    assert workspace is not None
    assert workspace.current_tree_hash == target.checkpoint_fingerprint
    assert grant is not None and grant.status == "revoked" and grant.revoked_at is not None
    terminal_at = permit.terminal_at
    validation_version = validation_run.version

    replay = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{target.job_id}/cancelled",
        headers=runner_headers(target.token),
        json=target.identity,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True
    rejected_completion = _post_completion(client, target, result=late_result)
    assert rejected_completion.status_code == 409, rejected_completion.text

    db_session.expire_all()
    replayed_permit = db_session.get(SideEffectPermit, uuid.UUID(target.permit_id))
    replayed_run = db_session.get(ValidationRun, uuid.UUID(target.validation_run_id))
    assert replayed_permit is not None and replayed_permit.terminal_at == terminal_at
    assert replayed_run is not None and replayed_run.version == validation_version
    assert _event_count(db_session, target.job_id, "cancel_acknowledged") == 1
    assert _event_count(db_session, target.job_id, "job_succeeded") == 0
    assert _event_count(db_session, target.job_id, "side_effect_permit_completed") == 0
    assert (
        db_session.scalar(
            select(func.count(ValidationEvidence.id)).where(
                ValidationEvidence.validation_run_id == uuid.UUID(target.validation_run_id)
            )
        )
        == 0
    )


def test_stale_identity_and_mismatched_run_cannot_terminalize_validation_permit(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    target = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    unrelated = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    requested = client.post(
        f"/api/v1/validation-runs/{target.validation_run_id}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert requested.status_code == 200, requested.text

    rejected_identities = [
        (
            {**target.identity, "attempt_id": str(uuid.uuid4())},
            409,
            "stale_lease",
        ),
        (
            {**target.identity, "lease_id": str(uuid.uuid4())},
            409,
            "stale_lease",
        ),
        (unrelated.identity, 403, "runner_identity_mismatch"),
    ]
    for identity, expected_status, expected_code in rejected_identities:
        rejected = client.post(
            f"/api/v1/runner-protocol/v1/jobs/{target.job_id}/cancelled",
            headers=runner_headers(target.token),
            json=identity,
        )
        assert rejected.status_code == expected_status, rejected.text
        assert rejected.json()["error"]["code"] == expected_code

    job = db_session.get(RunnerJob, uuid.UUID(target.job_id))
    assert job is not None
    job.parameters = {
        **job.parameters,
        "validation_run_id": str(uuid.uuid4()),
    }
    db_session.commit()
    mismatched_run = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{target.job_id}/cancelled",
        headers=runner_headers(target.token),
        json=target.identity,
    )
    assert mismatched_run.status_code == 409, mismatched_run.text
    assert mismatched_run.json()["error"]["code"] == "validation_result_binding_mismatch"

    db_session.expire_all()
    target_job = db_session.get(RunnerJob, uuid.UUID(target.job_id))
    target_attempt = db_session.get(
        RunnerJobAttempt,
        uuid.UUID(target.identity["attempt_id"]),
    )
    target_permit = db_session.get(SideEffectPermit, uuid.UUID(target.permit_id))
    unrelated_permit = db_session.get(SideEffectPermit, uuid.UUID(unrelated.permit_id))
    validation_run = db_session.get(ValidationRun, uuid.UUID(target.validation_run_id))
    assert target_job is not None and target_job.state == "cancel_requested"
    assert target_attempt is not None and target_attempt.state == "running"
    assert target_permit is not None and target_permit.state == "consumed"
    assert target_permit.terminal_at is None
    assert unrelated_permit is not None and unrelated_permit.state == "consumed"
    assert validation_run is not None and validation_run.state == "cancel_requested"
    assert _event_count(db_session, target.job_id, "cancel_acknowledged") == 0
