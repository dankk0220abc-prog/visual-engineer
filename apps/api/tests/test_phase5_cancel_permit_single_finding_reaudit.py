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
from visual_engineer_api.models.workspace import SideEffectPermit, Workspace


def test_single_finding_cancelled_permit_rejects_terminal_attempt_replay(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """VE-P5-FREAUD-001: a terminal Attempt cannot reopen or complete its Permit."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    late_result = _governed_result(db_session, context)
    old_identity = dict(context.identity)

    requested = client.post(
        f"/api/v1/validation-runs/{context.validation_run_id}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert requested.status_code == 200, requested.text
    assert requested.json()["state"] == "cancel_requested"
    acknowledged = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/cancelled",
        headers=runner_headers(context.token),
        json=old_identity,
    )
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["state"] == "cancelled"

    db_session.expire_all()
    permit = db_session.get(SideEffectPermit, uuid.UUID(context.permit_id))
    validation_run = db_session.get(ValidationRun, uuid.UUID(context.validation_run_id))
    assert permit is not None
    assert validation_run is not None
    assert (permit.state, permit.terminal_at is not None) == ("cancelled", True)
    assert validation_run.state == "cancelled"
    terminal_at = permit.terminal_at
    validation_version = validation_run.version
    event_count = int(
        db_session.scalar(
            select(func.count(RunnerJobEvent.id)).where(
                RunnerJobEvent.job_id == uuid.UUID(context.job_id)
            )
        )
        or 0
    )

    cancellation_replay = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/cancelled",
        headers=runner_headers(context.token),
        json=old_identity,
    )
    assert cancellation_replay.status_code == 200, cancellation_replay.text
    assert cancellation_replay.json()["idempotent_replay"] is True

    stale_lease_replay = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/cancelled",
        headers=runner_headers(context.token),
        json={**old_identity, "lease_id": str(uuid.uuid4())},
    )
    assert stale_lease_replay.status_code == 409, stale_lease_replay.text
    assert stale_lease_replay.json()["error"]["code"] == "stale_lease"

    late_completion = _post_completion(
        client,
        context,
        identity=old_identity,
        result=late_result,
    )
    assert late_completion.status_code == 409, late_completion.text
    assert late_completion.json()["error"]["code"] == "stale_lease"

    db_session.expire_all()
    job = db_session.get(RunnerJob, uuid.UUID(context.job_id))
    attempt = db_session.get(RunnerJobAttempt, uuid.UUID(old_identity["attempt_id"]))
    replayed_permit = db_session.get(SideEffectPermit, uuid.UUID(context.permit_id))
    replayed_run = db_session.get(ValidationRun, uuid.UUID(context.validation_run_id))
    step = db_session.scalar(
        select(ValidationStepRun).where(
            ValidationStepRun.validation_run_id == uuid.UUID(context.validation_run_id)
        )
    )
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert job is not None and job.state == "cancelled" and job.result is None
    assert attempt is not None and attempt.state == "cancelled"
    assert str(attempt.lease_id) == old_identity["lease_id"]
    assert replayed_permit is not None
    assert (replayed_permit.state, replayed_permit.terminal_at) == ("cancelled", terminal_at)
    assert replayed_run is not None
    assert (replayed_run.state, replayed_run.version) == ("cancelled", validation_version)
    assert step is not None and step.state == "cancelled"
    assert workspace is not None
    assert workspace.current_tree_hash == context.checkpoint_fingerprint
    assert (
        db_session.scalar(
            select(func.count(ValidationEvidence.id)).where(
                ValidationEvidence.validation_run_id == uuid.UUID(context.validation_run_id)
            )
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count(RunnerJobEvent.id)).where(
                RunnerJobEvent.job_id == uuid.UUID(context.job_id)
            )
        )
        == event_count
    )
    for event_type, expected in (
        ("cancel_acknowledged", 1),
        ("job_succeeded", 0),
        ("side_effect_permit_completed", 0),
    ):
        assert (
            db_session.scalar(
                select(func.count(RunnerJobEvent.id)).where(
                    RunnerJobEvent.job_id == uuid.UUID(context.job_id),
                    RunnerJobEvent.event_type == event_type,
                )
            )
            == expected
        )
