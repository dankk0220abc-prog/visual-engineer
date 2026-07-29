from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_phase5_control_plane_remediation import _governed_result
from test_phase5_focused_security_review import (
    _post_completion,
    _prepare_validation_job,
    _ValidationJobContext,
)
from test_workspace_api import runner_headers
from visual_engineer_api.models.runner import RunnerJob, RunnerJobAttempt, RunnerJobEvent
from visual_engineer_api.models.validation import (
    ValidationEvidence,
    ValidationRun,
    ValidationStepRun,
)
from visual_engineer_api.models.workspace import SideEffectPermit, Workspace
from visual_engineer_runner_protocol import (
    ValidationExecutionResult,
    compute_validation_artifact_manifest_digest,
    compute_validation_evidence_digest,
)


def _event_count(
    db_session: Session,
    context: _ValidationJobContext,
    event_type: str,
) -> int:
    return int(
        db_session.scalar(
            select(func.count(RunnerJobEvent.id)).where(
                RunnerJobEvent.job_id == uuid.UUID(context.job_id),
                RunnerJobEvent.event_type == event_type,
            )
        )
        or 0
    )


def _assert_rejection_has_zero_success_side_effects(
    db_session: Session,
    context: _ValidationJobContext,
) -> None:
    db_session.expire_all()
    job = db_session.get(RunnerJob, uuid.UUID(context.job_id))
    permit = db_session.get(SideEffectPermit, uuid.UUID(context.permit_id))
    validation_run = db_session.get(ValidationRun, uuid.UUID(context.validation_run_id))
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert job is not None
    assert permit is not None
    assert validation_run is not None
    assert workspace is not None
    assert job.state == "running"
    assert job.result is None
    assert permit.state == "consumed"
    assert validation_run.completed_at is None
    assert workspace.current_tree_hash == context.checkpoint_fingerprint
    assert (
        db_session.scalar(
            select(func.count(ValidationRun.id)).where(
                ValidationRun.execution_grant_id == validation_run.execution_grant_id
            )
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count(ValidationEvidence.id)).where(
                ValidationEvidence.validation_run_id == validation_run.id
            )
        )
        == 0
    )
    assert _event_count(db_session, context, "job_succeeded") == 0
    assert _event_count(db_session, context, "side_effect_permit_completed") == 0


def _recompute_evidence_digest(result: dict[str, Any]) -> dict[str, Any]:
    typed = ValidationExecutionResult.model_validate(result)
    typed.evidence_digest = compute_validation_evidence_digest(typed)
    return typed.model_dump(mode="json")


def test_reaudit_execution_envelope_digest_mismatch_is_rejected_twice(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """P5-AUD-005: a self-consistent evidence digest cannot bless a wrong envelope."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context)
    result["execution_envelope_digest"] = hashlib.sha256(
        b"independent-wrong-execution-envelope"
    ).hexdigest()
    forged = _recompute_evidence_digest(result)

    for _ in range(2):
        rejected = _post_completion(client, context, result=forged)
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["error"]["code"] == "validation_result_evidence_invalid"
    _assert_rejection_has_zero_success_side_effects(db_session, context)


def test_reaudit_duplicate_artifact_path_is_rejected_twice(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """P5-AUD-006: duplicate paths cannot hide behind zero reported totals."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    duplicate = {
        "relative_path": "reports/result.txt",
        "file_type": "regular_file",
        "size_bytes": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
    }
    result = _governed_result(db_session, context)
    result.update(
        artifacts=[duplicate, duplicate],
        artifact_count=0,
        artifact_bytes=0,
        artifact_manifest_digest=compute_validation_artifact_manifest_digest(
            [duplicate, duplicate]
        ),
    )
    forged = _recompute_evidence_digest(result)

    for _ in range(2):
        rejected = _post_completion(client, context, result=forged)
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["error"]["code"] == "validation_result_artifact_invalid"
    _assert_rejection_has_zero_success_side_effects(db_session, context)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda result: result.update(artifact_count=-1),
        lambda result: result.update(artifact_bytes=2**63),
    ],
    ids=["negative-count", "overflow-sized-total"],
)
def test_reaudit_invalid_artifact_arithmetic_fails_at_protocol_boundary(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    """P5-AUD-006: negative and overflow-sized accounting fail closed."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context)
    mutate(result)

    rejected = _post_completion(client, context, result=result)
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["error"]["code"] == "validation_error"
    _assert_rejection_has_zero_success_side_effects(db_session, context)


def test_reaudit_utf8_output_exact_limit_and_plus_one(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """P5-AUD-006: Control Plane budgets UTF-8 bytes rather than characters."""

    rejected_context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    over_limit = _governed_result(
        db_session,
        rejected_context,
        stdout=("界" * 2731),
    )
    rejected = _post_completion(client, rejected_context, result=over_limit)
    assert len(over_limit["stdout"]) == 2731
    assert len(over_limit["stdout"].encode("utf-8")) == 8193
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"]["code"] == "validation_result_budget_exceeded"
    _assert_rejection_has_zero_success_side_effects(db_session, rejected_context)

    accepted_context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    exact_limit = _governed_result(
        db_session,
        accepted_context,
        stdout=("界" * 2730) + "xx",
    )
    assert len(exact_limit["stdout"].encode("utf-8")) == 8192
    completed = _post_completion(client, accepted_context, result=exact_limit)
    assert completed.status_code == 200, completed.text
    assert completed.json()["state"] == "succeeded"
    replay = _post_completion(client, accepted_context, result=exact_limit)
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True

    synchronized = client.get(f"/api/v1/validation-runs/{accepted_context.validation_run_id}")
    assert synchronized.status_code == 200, synchronized.text
    db_session.expire_all()
    permit = db_session.get(SideEffectPermit, uuid.UUID(accepted_context.permit_id))
    assert permit is not None and permit.state == "completed"
    assert (
        db_session.scalar(
            select(func.count(ValidationEvidence.id)).where(
                ValidationEvidence.validation_run_id
                == uuid.UUID(accepted_context.validation_run_id)
            )
        )
        == 1
    )
    assert _event_count(db_session, accepted_context, "job_succeeded") == 1
    assert _event_count(db_session, accepted_context, "side_effect_permit_completed") == 1


def test_reaudit_process_remained_failure_persists_recovery_once(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """VE-P5-FSR-002: another typed cleanup failure atomically enters recovery."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    before = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert before is not None
    before_fingerprint = before.current_tree_hash
    requested = client.post(
        f"/api/v1/validation-runs/{context.validation_run_id}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert requested.status_code == 200, requested.text
    assert requested.json()["state"] == "cancel_requested"
    payload = {
        **context.identity,
        "error_code": "validation_process_remained",
        "error_message": None,
        "side_effect_permit_id": context.permit_id,
    }

    failed = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/fail",
        headers=runner_headers(context.token),
        json=payload,
    )
    assert failed.status_code == 200, failed.text
    replay = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/fail",
        headers=runner_headers(context.token),
        json=payload,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True

    db_session.expire_all()
    job = db_session.get(RunnerJob, uuid.UUID(context.job_id))
    attempt = db_session.get(RunnerJobAttempt, uuid.UUID(context.identity["attempt_id"]))
    permit = db_session.get(SideEffectPermit, uuid.UUID(context.permit_id))
    validation_run = db_session.get(ValidationRun, uuid.UUID(context.validation_run_id))
    step = db_session.scalar(
        select(ValidationStepRun).where(
            ValidationStepRun.validation_run_id == uuid.UUID(context.validation_run_id)
        )
    )
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert job is not None and job.state == "failed" and job.result is None
    assert attempt is not None and attempt.state == "failed"
    assert permit is not None and permit.state == "failed"
    assert validation_run is not None and validation_run.state == "recovery_required"
    assert validation_run.error_code == "validation_process_remained"
    assert step is not None and step.state == "recovery_required"
    assert workspace is not None and workspace.current_tree_hash == before_fingerprint
    assert _event_count(db_session, context, "job_failed") == 1
    assert _event_count(db_session, context, "cancel_acknowledged") == 0
    assert _event_count(db_session, context, "job_succeeded") == 0
    assert _event_count(db_session, context, "side_effect_permit_completed") == 0
    assert (
        db_session.scalar(
            select(func.count(ValidationEvidence.id)).where(
                ValidationEvidence.validation_run_id == validation_run.id
            )
        )
        == 0
    )


def test_reaudit_successful_active_cancel_terminalizes_consumed_permit(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """VE-P5-FSR-002 control: proven cleanup must close every durable fence."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    requested = client.post(
        f"/api/v1/validation-runs/{context.validation_run_id}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert requested.status_code == 200, requested.text
    assert requested.json()["state"] == "cancel_requested"
    acknowledged = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/cancelled",
        headers=runner_headers(context.token),
        json=context.identity,
    )
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["state"] == "cancelled"

    synchronized = client.get(f"/api/v1/validation-runs/{context.validation_run_id}")
    assert synchronized.status_code == 200, synchronized.text
    assert synchronized.json()["state"] == "cancelled"
    assert synchronized.json()["evidence"] is None

    db_session.expire_all()
    job = db_session.get(RunnerJob, uuid.UUID(context.job_id))
    attempt = db_session.get(RunnerJobAttempt, uuid.UUID(context.identity["attempt_id"]))
    permit = db_session.get(SideEffectPermit, uuid.UUID(context.permit_id))
    validation_run = db_session.get(ValidationRun, uuid.UUID(context.validation_run_id))
    step = db_session.scalar(
        select(ValidationStepRun).where(
            ValidationStepRun.validation_run_id == uuid.UUID(context.validation_run_id)
        )
    )
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert job is not None and job.state == "cancelled" and job.result is None
    assert attempt is not None and attempt.state == "cancelled"
    assert validation_run is not None and validation_run.state == "cancelled"
    assert step is not None and step.state == "cancelled"
    assert workspace is not None and workspace.current_tree_hash == context.checkpoint_fingerprint
    assert _event_count(db_session, context, "cancel_acknowledged") == 1
    assert _event_count(db_session, context, "job_succeeded") == 0
    assert _event_count(db_session, context, "side_effect_permit_completed") == 0
    assert (
        db_session.scalar(
            select(func.count(ValidationEvidence.id)).where(
                ValidationEvidence.validation_run_id == validation_run.id
            )
        )
        == 0
    )
    assert permit is not None
    assert (permit.state, permit.terminal_at is not None) == ("cancelled", True)
