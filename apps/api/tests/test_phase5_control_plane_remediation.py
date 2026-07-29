from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from test_phase5_focused_security_review import (
    _post_completion,
    _prepare_validation_job,
    _valid_result,
    _ValidationJobContext,
)
from test_workspace_api import runner_headers
from visual_engineer_api.models.runner import RunnerJob, RunnerJobEvent
from visual_engineer_api.models.validation import ValidationEvidence, ValidationRun
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    SideEffectPermit,
    Workspace,
)
from visual_engineer_runner_protocol import (
    SideEffectPermit as ProtocolSideEffectPermit,
)
from visual_engineer_runner_protocol import (
    ValidationExecuteJobSpec,
    ValidationExecutionResult,
    compute_validation_artifact_manifest_digest,
    compute_validation_evidence_digest,
    validation_result_binding,
)


def _protocol_permit(permit: SideEffectPermit) -> ProtocolSideEffectPermit:
    return ProtocolSideEffectPermit(
        id=permit.id,
        sequence=permit.sequence,
        runner_id=permit.runner_id,
        job_id=permit.job_id,
        attempt_id=permit.attempt_id,
        lease_id=permit.lease_id,
        grant_id=permit.grant_id,
        workspace_id=permit.workspace_id,
        repository_handle_id=permit.repository_handle_id,
        operation=permit.operation,
        relative_path=permit.relative_path,
        expected_current=permit.expected_current,
        proposed_digest=permit.proposed_digest,
        job_digest=permit.job_digest,
        operation_digest=permit.operation_digest,
        policy_hash=permit.policy_hash,
        source_revision=permit.source_revision,
        issued_at=permit.issued_at,
        consumed_at=permit.consumed_at,
        expires_at=permit.expires_at,
        state=permit.state,
    )


def _governed_result(
    db_session: Session,
    context: _ValidationJobContext,
    **overrides: Any,
) -> dict[str, Any]:
    job = db_session.get(RunnerJob, uuid.UUID(context.job_id))
    permit = db_session.get(SideEffectPermit, uuid.UUID(context.permit_id))
    assert job is not None
    assert permit is not None
    spec = ValidationExecuteJobSpec.model_validate({"kind": job.kind, **job.parameters})
    artifacts = overrides.pop("artifacts", [])
    payload = {
        **_valid_result(context),
        **validation_result_binding(spec, _protocol_permit(permit)),
        "artifacts": artifacts,
        "artifact_manifest_digest": compute_validation_artifact_manifest_digest(artifacts),
        **overrides,
    }
    result = ValidationExecutionResult.model_validate(payload)
    result.evidence_digest = compute_validation_evidence_digest(result)
    return result.model_dump(mode="json")


def _assert_zero_success_side_effects(
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
    assert job.state in {"running", "cancel_requested"}
    assert job.result is None
    assert permit.state == "consumed"
    assert validation_run.completed_at is None
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
                RunnerJobEvent.job_id == uuid.UUID(context.job_id),
                RunnerJobEvent.event_type.in_(("job_succeeded", "side_effect_permit_completed")),
            )
        )
        == 0
    )


def _wrong_digest() -> str:
    return hashlib.sha256(b"wrong-phase5-result-binding").hexdigest()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda result: result.update(validation_run_id=str(uuid.uuid4())),
        lambda result: result.update(validation_step_id="wrong-step"),
        lambda result: result.update(workspace_id=str(uuid.uuid4())),
        lambda result: result.update(checkpoint_id=str(uuid.uuid4())),
        lambda result: result.update(profile_id="fixture-python-stdlib-v2"),
        lambda result: result.update(profile_version=2),
        lambda result: result.update(source_revision="b" * 40),
        lambda result: result.update(policy_digest=_wrong_digest()),
        lambda result: result.update(
            fixed_argv=[
                "python",
                "-S",
                "-I",
                "<system-owned-fixture-validator>",
            ]
        ),
        lambda result: result.update(fixed_cwd="<wrong-validation-root>"),
        lambda result: result.update(fixed_environment_digest=_wrong_digest()),
        lambda result: result.update(result_schema_version=2),
        lambda result: result.update(side_effect_permit_sequence=99),
        lambda result: result.update(side_effect_permit_id=str(uuid.uuid4())),
        lambda result: result.update(fencing_token=_wrong_digest()),
    ],
    ids=[
        "validation-run",
        "validation-step",
        "workspace",
        "checkpoint",
        "profile-id",
        "profile-version",
        "source-revision",
        "policy-digest",
        "fixed-argv",
        "fixed-cwd",
        "fixed-environment",
        "result-schema",
        "permit-sequence",
        "permit-id",
        "fencing-token",
    ],
)
def test_validation_result_envelope_mismatch_has_zero_success_side_effects(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context)
    mutate(result)
    typed = ValidationExecutionResult.model_validate(result)
    typed.evidence_digest = compute_validation_evidence_digest(typed)
    forged = typed.model_dump(mode="json")

    assert _post_completion(client, context, result=forged).status_code == 409
    assert _post_completion(client, context, result=forged).status_code == 409
    _assert_zero_success_side_effects(db_session, context)


@pytest.mark.parametrize("field", ["runner_id", "attempt_id", "lease_id"])
def test_outer_completion_identity_mismatch_is_side_effect_free(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    field: str,
) -> None:
    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context)
    identity = {**context.identity, field: str(uuid.uuid4())}

    rejected = _post_completion(client, context, identity=identity, result=result)
    assert rejected.status_code in {403, 409}
    _assert_zero_success_side_effects(db_session, context)


def test_completion_for_wrong_job_is_side_effect_free(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context)
    rejected = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{uuid.uuid4()}/complete",
        headers=runner_headers(context.token),
        json={**context.identity, "result": result},
    )
    assert rejected.status_code in {404, 409}
    _assert_zero_success_side_effects(db_session, context)


@pytest.mark.parametrize(
    "overrides",
    [
        {"stdout": "x" * 8193},
        {"stderr": "x" * 8193},
        {"stdout": "x" * 4097, "stderr": "y" * 4096},
        {"artifact_count": 1, "artifact_bytes": 1},
        {"stdout": "short", "stdout_truncated": True},
        {"artifact_manifest_digest": _wrong_digest()},
        {"evidence_digest": _wrong_digest()},
    ],
    ids=[
        "stdout-over",
        "stderr-over",
        "combined-over",
        "artifact-over",
        "truncation-mismatch",
        "manifest-mismatch",
        "evidence-digest-mismatch",
    ],
)
def test_validation_result_budget_or_evidence_rejection_is_side_effect_free(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    overrides: dict[str, Any],
) -> None:
    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context)
    result.update(overrides)
    if "evidence_digest" not in overrides:
        typed = ValidationExecutionResult.model_validate(result)
        typed.evidence_digest = compute_validation_evidence_digest(typed)
        result = typed.model_dump(mode="json")

    assert _post_completion(client, context, result=result).status_code == 409
    assert _post_completion(client, context, result=result).status_code == 409
    _assert_zero_success_side_effects(db_session, context)


@pytest.mark.parametrize(
    "artifact",
    [
        {
            "relative_path": "../escape",
            "file_type": "regular_file",
            "size_bytes": 1,
            "sha256": _wrong_digest(),
        },
        {
            "relative_path": "artifact.bin",
            "file_type": "symlink",
            "size_bytes": 1,
            "sha256": _wrong_digest(),
        },
    ],
    ids=["path-traversal", "special-file"],
)
def test_validation_artifact_metadata_fails_closed_at_protocol_boundary(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    artifact: dict[str, Any],
) -> None:
    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context)
    result.update(
        artifacts=[artifact],
        artifact_count=1,
        artifact_bytes=1,
        artifact_manifest_digest=compute_validation_artifact_manifest_digest([artifact]),
    )

    assert _post_completion(client, context, result=result).status_code == 422
    _assert_zero_success_side_effects(db_session, context)


def test_exact_output_limit_and_identical_replay_persist_once(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context, stdout="x" * 8192)

    completed = _post_completion(client, context, result=result)
    assert completed.status_code == 200, completed.text
    assert completed.json()["state"] == "succeeded"
    replay = _post_completion(client, context, result=result)
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True

    synchronized = client.get(f"/api/v1/validation-runs/{context.validation_run_id}")
    assert synchronized.status_code == 200, synchronized.text
    assert synchronized.json()["state"] == "succeeded"
    assert synchronized.json()["evidence"]["evidence_digest"] == result["evidence_digest"]
    db_session.expire_all()
    assert (
        db_session.scalar(
            select(func.count(ValidationEvidence.id)).where(
                ValidationEvidence.validation_run_id == uuid.UUID(context.validation_run_id)
            )
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count(RunnerJobEvent.id)).where(
                RunnerJobEvent.job_id == uuid.UUID(context.job_id),
                RunnerJobEvent.event_type == "job_succeeded",
            )
        )
        == 1
    )


def test_cancel_requested_cleanup_failure_persists_recovery_once(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    before = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert before is not None
    before_fingerprint = before.current_tree_hash
    cancelled = client.post(
        f"/api/v1/validation-runs/{context.validation_run_id}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["state"] == "cancel_requested"
    failure_payload = {
        **context.identity,
        "error_code": "validation_cleanup_failed",
        "error_message": None,
        "side_effect_permit_id": context.permit_id,
    }
    failed = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/fail",
        headers=runner_headers(context.token),
        json=failure_payload,
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["state"] == "failed"
    replay = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/fail",
        headers=runner_headers(context.token),
        json=failure_payload,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True

    recovered = client.get(f"/api/v1/validation-runs/{context.validation_run_id}")
    assert recovered.status_code == 200, recovered.text
    payload = recovered.json()
    assert payload["state"] == "recovery_required"
    assert payload["error_code"] == "validation_cleanup_failed"
    assert payload["evidence"] is None

    db_session.expire_all()
    job = db_session.get(RunnerJob, uuid.UUID(context.job_id))
    permit = db_session.get(SideEffectPermit, uuid.UUID(context.permit_id))
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert job is not None and job.result is None and job.state == "failed"
    assert permit is not None and permit.state == "failed"
    assert workspace is not None and workspace.current_tree_hash == before_fingerprint
    event_counts: dict[str, int] = {
        event_type: count
        for event_type, count in db_session.execute(
            select(RunnerJobEvent.event_type, func.count(RunnerJobEvent.id))
            .where(RunnerJobEvent.job_id == uuid.UUID(context.job_id))
            .group_by(RunnerJobEvent.event_type)
        ).all()
    }
    assert event_counts.get("job_failed") == 1
    assert event_counts.get("cancel_acknowledged", 0) == 0
    assert event_counts.get("job_succeeded", 0) == 0
    assert event_counts.get("side_effect_permit_completed", 0) == 0


def test_revoked_validation_grant_rejects_completion_without_success(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    result = _governed_result(db_session, context)
    validation_run = db_session.get(ValidationRun, uuid.UUID(context.validation_run_id))
    assert validation_run is not None
    grant = db_session.get(ExecutionGrant, validation_run.execution_grant_id)
    assert grant is not None
    revoked = client.post(f"/api/v1/execution-grants/{grant.id}/revoke")
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoke_requested"

    assert _post_completion(client, context, result=result).status_code == 409
    _assert_zero_success_side_effects(db_session, context)
