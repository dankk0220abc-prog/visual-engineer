from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_validation_suites import (
    SuiteContext,
    _complete_step,
    _new_suite_grant,
    _prepare_suite,
)
from test_workspace_api import (
    acquire_side_effect_permit,
    claim_start,
    governed_validation_result,
    runner_headers,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.runner import (
    Runner,
    RunnerJob,
    RunnerJobAttempt,
    RunnerJobEvent,
)
from visual_engineer_api.models.validation import (
    ValidationEvidence,
    ValidationRun,
    ValidationSuiteResult,
    ValidationSuiteRun,
    ValidationSuiteStepRun,
)
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    SideEffectPermit,
    Workspace,
    WorkspaceEvent,
)
from visual_engineer_api.schemas.validation import ValidationSuiteRetryCreate
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError
from visual_engineer_api.services.validation import ValidationService
from visual_engineer_api.services.validation_suite import (
    ValidationSuiteService,
    ValidationSuiteServiceError,
)
from visual_engineer_runner_protocol import (
    CompleteRequest,
    compute_validation_policy_digest,
)

_COUNTED_MODELS = (
    ExecutionGrant,
    ValidationSuiteRun,
    ValidationSuiteStepRun,
    ValidationRun,
    RunnerJob,
    RunnerJobAttempt,
    SideEffectPermit,
    ValidationSuiteResult,
    ValidationEvidence,
    AuditEvent,
    RunnerJobEvent,
    WorkspaceEvent,
)


def _durable_counts(session: Session) -> tuple[int, ...]:
    session.expire_all()
    return tuple(
        int(session.scalar(select(func.count()).select_from(model)) or 0)
        for model in _COUNTED_MODELS
    )


def _validation_success_result(
    context: SuiteContext,
    assignment: dict[str, Any],
    permit: dict[str, Any],
    *,
    sequence: int,
) -> dict[str, Any]:
    is_manifest = sequence == 2
    return governed_validation_result(
        assignment,
        permit,
        {
            "kind": "validation_execute_v1",
            "validation_run_id": next(
                step["validation_run_id"]
                for step in context.suite_run["steps"]
                if step["sequence"] == sequence
            ),
            "workspace_id": context.workspace_id,
            "checkpoint_id": context.checkpoint_id,
            "checkpoint_fingerprint": context.checkpoint_fingerprint,
            "profile_id": (
                "fixture-python-manifest-v1" if is_manifest else "fixture-python-stdlib-v1"
            ),
            "profile_version": 1,
            "fixed_argv": [
                "python",
                "-I",
                "-S",
                "<system-owned-fixture-validator>",
                *(["<system-owned-profile-mode>"] if is_manifest else []),
            ],
            "started_at": "2026-07-30T02:00:00Z",
            "completed_at": "2026-07-30T02:00:01Z",
            "duration_ms": 50,
            "exit_code": 0,
            "stdout": (
                "VE_VALIDATION_PROFILE_MANIFEST_PASS\n"
                if is_manifest
                else "VE_VALIDATION_PROFILE_PASS\n"
            ),
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
            "redaction_count": 0,
            "timed_out": False,
            "cancelled": False,
            "network_isolated": True,
            "filesystem_isolated": True,
            "sandbox_cleaned": True,
            "artifact_count": 0,
            "artifact_bytes": 0,
            "side_effect_permit_id": permit["id"],
        },
    )


def _materialize_completed_step(
    db_session: Session,
    context: SuiteContext,
    *,
    sequence: int,
) -> ValidationSuiteStepRun:
    db_session.expire_all()
    step = db_session.scalar(
        select(ValidationSuiteStepRun).where(
            ValidationSuiteStepRun.suite_run_id == uuid.UUID(context.suite_run["id"]),
            ValidationSuiteStepRun.sequence == sequence,
        )
    )
    assert step is not None
    assert step.validation_run_id is not None
    ValidationService(db_session).get(step.validation_run_id)
    db_session.expire_all()
    step = db_session.get(ValidationSuiteStepRun, step.id)
    assert step is not None
    assert step.validation_run_id is not None
    child = db_session.get(ValidationRun, step.validation_run_id)
    evidence = db_session.scalar(
        select(ValidationEvidence).where(
            ValidationEvidence.validation_run_id == step.validation_run_id
        )
    )
    assert child is not None
    assert evidence is not None
    assert child.runner_job_id is not None
    assert child.runner_id is not None
    assert child.attempt_id is not None
    assert child.lease_id is not None
    db_session.execute(
        text(
            """
            UPDATE validation_suite_step_runs
            SET state = 'succeeded',
                validation_run_id = :validation_run_id,
                runner_job_id = :runner_job_id,
                runner_id = :runner_id,
                attempt_id = :attempt_id,
                lease_id = :lease_id,
                evidence_id = :evidence_id,
                started_at = :started_at,
                completed_at = :completed_at,
                duration_ms = :duration_ms,
                exit_code = 0,
                output_bytes = :output_bytes,
                redaction_count = :redaction_count,
                output_truncated = :output_truncated,
                cleanup_succeeded = true
            WHERE id = :step_id
            """
        ),
        {
            "step_id": step.id,
            "validation_run_id": child.id,
            "runner_job_id": child.runner_job_id,
            "runner_id": child.runner_id,
            "attempt_id": child.attempt_id,
            "lease_id": child.lease_id,
            "evidence_id": evidence.id,
            "started_at": evidence.started_at,
            "completed_at": evidence.completed_at,
            "duration_ms": evidence.duration_ms,
            "output_bytes": len(evidence.stdout.encode("utf-8"))
            + len(evidence.stderr.encode("utf-8")),
            "redaction_count": evidence.redaction_count,
            "output_truncated": (evidence.stdout_truncated or evidence.stderr_truncated),
        },
    )
    db_session.commit()
    db_session.expire_all()
    persisted = db_session.get(ValidationSuiteStepRun, step.id)
    assert persisted is not None
    return persisted


def _complete_two_steps_without_suite_result(
    client: TestClient,
    db_session: Session,
    context: SuiteContext,
) -> list[ValidationSuiteStepRun]:
    after_first = _complete_step(
        client,
        context,
        context.suite_run,
        sequence=1,
        exit_code=0,
    )
    _complete_step(
        client,
        context,
        after_first,
        sequence=2,
        exit_code=0,
        synchronize_suite=False,
    )
    _materialize_completed_step(db_session, context, sequence=2)
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(ValidationSuiteStepRun)
            .where(ValidationSuiteStepRun.suite_run_id == uuid.UUID(context.suite_run["id"]))
            .order_by(ValidationSuiteStepRun.sequence)
        )
    )


def _evidence_references(
    db_session: Session,
    steps: list[ValidationSuiteStepRun],
) -> tuple[list[dict[str, object]], list[str]]:
    references: list[dict[str, object]] = []
    runners: list[str] = []
    for step in steps:
        assert step.validation_run_id is not None
        assert step.runner_job_id is not None
        assert step.runner_id is not None
        assert step.attempt_id is not None
        assert step.lease_id is not None
        assert step.evidence_id is not None
        child = db_session.get(ValidationRun, step.validation_run_id)
        evidence = db_session.get(ValidationEvidence, step.evidence_id)
        assert child is not None
        assert evidence is not None
        references.append(
            {
                "sequence": step.sequence,
                "step_id": step.step_id,
                "profile": f"{step.profile_id}:v{step.profile_version}",
                "validation_run_id": str(step.validation_run_id),
                "runner_job_id": str(step.runner_job_id),
                "runner_id": str(step.runner_id),
                "attempt_id": str(step.attempt_id),
                "lease_id": str(step.lease_id),
                "grant_id": str(child.execution_grant_id),
                "evidence_id": str(step.evidence_id),
                "evidence_digest": evidence.evidence_digest or "",
                "reused": False,
            }
        )
        runners.append(str(step.runner_id))
    return references, runners


def test_reaudit_retry_and_late_old_completion_race_preserves_one_lineage(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    first_step = context.suite_run["steps"][0]
    assignment, identity = claim_start(
        client,
        context.runner,
        context.token,
        first_step["runner_job_id"],
    )
    permit = acquire_side_effect_permit(
        client,
        context.token,
        assignment,
        identity,
    )
    late_result = _validation_success_result(
        context,
        assignment,
        permit,
        sequence=1,
    )

    cancel_requested = client.post(
        f"/api/v1/validation-suite-runs/{context.suite_run['id']}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert cancel_requested.status_code == 200, cancel_requested.text
    acknowledged = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{first_step['runner_job_id']}/cancelled",
        headers=runner_headers(context.token),
        json=identity,
    )
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["state"] == "cancelled"
    terminal = client.get(f"/api/v1/validation-suite-runs/{context.suite_run['id']}")
    assert terminal.status_code == 200, terminal.text
    assert terminal.json()["state"] == "cancelled"

    retry_grant = _new_suite_grant(
        client,
        context,
        retry_of_suite_run_id=context.suite_run["id"],
    )
    assert retry_grant["validation_suite_root_run_id"] == context.suite_run["id"]
    assert retry_grant["validation_suite_retry_of_run_id"] == context.suite_run["id"]
    assert retry_grant["validation_suite_attempt_number"] == 2
    assert retry_grant["validation_suite_allowed_run_count"] == 1
    db_session.commit()
    before = _durable_counts(db_session)

    engine = create_engine(database_url)
    barrier = threading.Barrier(2)
    retry_key = f"reaudit-retry-race-{uuid.uuid4()}"
    completion_payload = CompleteRequest.model_validate({**identity, "result": late_result})

    def retry_once() -> tuple[str, str]:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            try:
                response = ValidationSuiteService(session).retry(
                    uuid.UUID(context.suite_run["id"]),
                    ValidationSuiteRetryCreate(execution_grant_id=uuid.UUID(retry_grant["id"])),
                    idempotency_key=retry_key,
                    request_id="reaudit-retry-race",
                )
                return "created", str(response.id)
            except ValidationSuiteServiceError as exc:
                return "denied", exc.code

    def complete_old_attempt() -> tuple[str, str]:
        with Session(engine) as session:
            runner = session.get(Runner, uuid.UUID(identity["runner_id"]))
            assert runner is not None
            barrier.wait(timeout=10)
            try:
                RunnerService(session).complete(
                    runner,
                    uuid.UUID(first_step["runner_job_id"]),
                    completion_payload,
                    request_id="reaudit-late-old-completion",
                )
                return "accepted", "unexpected"
            except RunnerServiceError as exc:
                return "denied", exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        retry_future = executor.submit(retry_once)
        completion_future = executor.submit(complete_old_attempt)
        retry_outcome = retry_future.result(timeout=30)
        completion_outcome = completion_future.result(timeout=30)

    assert retry_outcome[0] == "created"
    assert completion_outcome == ("denied", "stale_lease")
    retry_id = uuid.UUID(retry_outcome[1])

    with Session(engine) as verification:
        retry_runs = list(
            verification.scalars(
                select(ValidationSuiteRun).where(
                    ValidationSuiteRun.root_suite_run_id == uuid.UUID(context.suite_run["id"]),
                    ValidationSuiteRun.attempt_number == 2,
                )
            )
        )
        assert [item.id for item in retry_runs] == [retry_id]
        assert retry_runs[0].retry_of_suite_run_id == uuid.UUID(context.suite_run["id"])
        assert retry_runs[0].execution_grant_id == uuid.UUID(retry_grant["id"])
        retry_steps = list(
            verification.scalars(
                select(ValidationSuiteStepRun)
                .where(ValidationSuiteStepRun.suite_run_id == retry_id)
                .order_by(ValidationSuiteStepRun.sequence)
            )
        )
        assert [item.state for item in retry_steps] == ["queued", "pending"]
        assert sum(item.validation_run_id is not None for item in retry_steps) == 1
        assert (
            verification.scalar(
                select(func.count(ValidationEvidence.id)).where(
                    ValidationEvidence.validation_run_id
                    == uuid.UUID(first_step["validation_run_id"])
                )
            )
            == 0
        )
        old_permit = verification.get(
            SideEffectPermit,
            uuid.UUID(permit["id"]),
        )
        assert old_permit is not None
        assert old_permit.state == "cancelled"

        replay_before = _durable_counts(verification)
        replayed = ValidationSuiteService(verification).retry(
            uuid.UUID(context.suite_run["id"]),
            ValidationSuiteRetryCreate(execution_grant_id=uuid.UUID(retry_grant["id"])),
            idempotency_key=retry_key,
            request_id="reaudit-retry-race-replay",
        )
        assert replayed.id == retry_id
        replay_after = _durable_counts(verification)
        assert replay_after == replay_before

    engine.dispose()
    after = _durable_counts(db_session)
    deltas = tuple(
        after_value - before_value for before_value, after_value in zip(before, after, strict=True)
    )
    assert deltas[1:9] == (1, 2, 1, 1, 0, 0, 0, 0)


def test_reaudit_foreign_retry_grant_has_zero_success_side_effects(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    primary = _prepare_suite(client, db_session, runner_bootstrap_token)
    foreign = _prepare_suite(client, db_session, runner_bootstrap_token)
    for context in (primary, foreign):
        cancelled = client.post(
            f"/api/v1/validation-suite-runs/{context.suite_run['id']}/cancel",
            headers={"X-Request-ID": str(uuid.uuid4())},
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["state"] == "cancelled"

    foreign_retry_grant = _new_suite_grant(
        client,
        foreign,
        retry_of_suite_run_id=foreign.suite_run["id"],
    )
    db_session.expire_all()
    workspace = db_session.get(Workspace, uuid.UUID(primary.workspace_id))
    assert workspace is not None
    canonical_before = workspace.current_tree_hash
    before = _durable_counts(db_session)

    denied = client.post(
        f"/api/v1/validation-suite-runs/{primary.suite_run['id']}/retry",
        headers={"Idempotency-Key": f"reaudit-foreign-retry-{uuid.uuid4()}"},
        json={"execution_grant_id": foreign_retry_grant["id"]},
    )
    assert denied.status_code in {409, 422}, denied.text
    assert denied.json()["error"]["code"] in {
        "validation_suite_grant_denied",
        "validation_suite_retry_binding_mismatch",
    }

    assert _durable_counts(db_session) == before
    db_session.expire_all()
    workspace = db_session.get(Workspace, uuid.UUID(primary.workspace_id))
    assert workspace is not None
    assert workspace.current_tree_hash == canonical_before


def test_reaudit_coherent_foreign_ordered_evidence_cannot_authorize_result(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    target = _prepare_suite(client, db_session, runner_bootstrap_token)
    foreign = _prepare_suite(client, db_session, runner_bootstrap_token)
    target_steps = _complete_two_steps_without_suite_result(
        client,
        db_session,
        target,
    )
    foreign_steps = _complete_two_steps_without_suite_result(
        client,
        db_session,
        foreign,
    )
    foreign_references, foreign_runners = _evidence_references(
        db_session,
        foreign_steps,
    )
    db_session.expire_all()
    target_run = db_session.get(
        ValidationSuiteRun,
        uuid.UUID(target.suite_run["id"]),
    )
    assert target_run is not None
    completed_at = max(step.completed_at for step in target_steps if step.completed_at is not None)
    target_run.state = "succeeded"
    target_run.completed_step_count = len(target_steps)
    target_run.combined_output_bytes = sum(step.output_bytes for step in target_steps)
    target_run.completed_at = completed_at
    target_run.version += 1
    db_session.commit()

    db_session.expire_all()
    target_run = db_session.get(ValidationSuiteRun, target_run.id)
    workspace = db_session.get(Workspace, uuid.UUID(target.workspace_id))
    assert target_run is not None
    assert workspace is not None
    canonical_before = workspace.current_tree_hash
    before = _durable_counts(db_session)
    rejected = ValidationSuiteResult(
        suite_run_id=target_run.id,
        root_suite_run_id=target_run.root_suite_run_id,
        run_id=target_run.run_id,
        execution_grant_id=target_run.execution_grant_id,
        suite_id=target_run.suite_id,
        suite_version=target_run.suite_version,
        source_revision=target_run.source_revision,
        checkpoint_id=target_run.checkpoint_id,
        policy_digest=target_run.policy_digest,
        attempt_number=target_run.attempt_number,
        total_timeout_seconds=target_run.total_timeout_seconds,
        total_output_bytes=target_run.total_output_bytes,
        max_attempts=target_run.max_attempts,
        verdict="succeeded",
        profile_references=[f"{step.profile_id}:v{step.profile_version}" for step in target_steps],
        evidence_references=foreign_references,
        runner_references=foreign_runners,
        audit_event_references=[],
        started_at=target_run.started_at or target_run.requested_at,
        completed_at=completed_at,
        duration_ms=0,
        combined_output_bytes=target_run.combined_output_bytes,
        redaction_count=0,
        output_truncated=False,
        timed_out=False,
        cancelled=False,
        recovery_required=False,
        cleanup_succeeded=True,
        source_invariant=True,
        canonical_workspace_invariant=True,
        artifact_count=0,
        artifact_bytes=0,
        aggregate_digest="0" * 64,
    )
    with pytest.raises(DBAPIError):
        with db_session.begin_nested():
            db_session.add(rejected)
            db_session.flush()
    db_session.expire_all()

    assert _durable_counts(db_session) == before
    assert (
        db_session.scalar(
            select(func.count(ValidationSuiteResult.id)).where(
                ValidationSuiteResult.suite_run_id == target_run.id,
                ValidationSuiteResult.verdict == "succeeded",
            )
        )
        == 0
    )
    workspace = db_session.get(Workspace, uuid.UUID(target.workspace_id))
    assert workspace is not None
    assert workspace.current_tree_hash == canonical_before


def test_reaudit_trusted_aggregate_digest_terminal_fence_and_replay(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    after_first = _complete_step(
        client,
        context,
        context.suite_run,
        sequence=1,
        exit_code=0,
    )
    completed = _complete_step(
        client,
        context,
        after_first,
        sequence=2,
        exit_code=0,
    )
    assert completed["state"] == "succeeded"
    result = completed["result"]
    assert result is not None
    assert result["suite_run_id"] == completed["id"]
    assert result["root_suite_run_id"] == completed["root_suite_run_id"]
    assert result["run_id"] == completed["run_id"]
    assert result["execution_grant_id"] == completed["execution_grant_id"]
    assert result["suite_id"] == completed["suite_id"]
    assert result["suite_version"] == completed["suite_version"]
    assert result["source_revision"] == completed["source_revision"]
    assert result["checkpoint_id"] == completed["checkpoint_id"]
    assert result["policy_digest"] == completed["policy_digest"]
    assert result["attempt_number"] == completed["attempt_number"]
    assert result["total_timeout_seconds"] == completed["total_timeout_seconds"]
    assert result["total_output_bytes"] == completed["total_output_bytes"]
    assert result["max_attempts"] == completed["max_attempts"]
    assert [item["sequence"] for item in result["evidence_references"]] == [1, 2]

    aggregate_payload = {
        "suite_run_id": completed["id"],
        "suite": f"{completed['suite_id']}:v{completed['suite_version']}",
        "policy_digest": completed["policy_digest"],
        "source_revision": completed["source_revision"],
        "checkpoint_id": completed["checkpoint_id"],
        "checkpoint_fingerprint": completed["checkpoint_fingerprint"],
        "attempt_number": completed["attempt_number"],
        "root_suite_run_id": completed["root_suite_run_id"],
        "execution_grant_id": completed["execution_grant_id"],
        "verdict": result["verdict"],
        "profiles": result["profile_references"],
        "evidence": result["evidence_references"],
        "runners": result["runner_references"],
        "combined_output_bytes": result["combined_output_bytes"],
        "redaction_count": result["redaction_count"],
        "output_truncated": result["output_truncated"],
        "cleanup_succeeded": result["cleanup_succeeded"],
        "source_invariant": result["source_invariant"],
        "canonical_workspace_invariant": result["canonical_workspace_invariant"],
        "artifact_count": result["artifact_count"],
        "artifact_bytes": result["artifact_bytes"],
        "budgets": {
            "total_timeout_seconds": completed["total_timeout_seconds"],
            "total_output_bytes": completed["total_output_bytes"],
            "max_attempts": completed["max_attempts"],
        },
    }
    assert result["aggregate_digest"] == compute_validation_policy_digest(aggregate_payload)

    db_session.expire_all()
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert workspace is not None
    canonical_before = workspace.current_tree_hash
    before = _durable_counts(db_session)
    for _ in range(2):
        replay = client.get(f"/api/v1/validation-suite-runs/{completed['id']}/result")
        assert replay.status_code == 200, replay.text
        assert replay.json()["result"]["aggregate_digest"] == result["aggregate_digest"]

    with pytest.raises(DBAPIError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    "UPDATE validation_suite_step_runs SET evidence_id = NULL "
                    "WHERE suite_run_id = :suite_run_id AND sequence = 1"
                ),
                {"suite_run_id": completed["id"]},
            )
    with pytest.raises(DBAPIError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    "UPDATE validation_suite_results "
                    "SET evidence_references = '[]'::jsonb "
                    "WHERE suite_run_id = :suite_run_id"
                ),
                {"suite_run_id": completed["id"]},
            )
    db_session.expire_all()

    assert _durable_counts(db_session) == before
    assert (
        db_session.scalar(
            select(func.count(ValidationSuiteResult.id)).where(
                ValidationSuiteResult.suite_run_id == uuid.UUID(completed["id"]),
                ValidationSuiteResult.verdict == "succeeded",
            )
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.event_type == "validation_suite_terminal",
                AuditEvent.details["suite_run_id"].astext == completed["id"],
            )
        )
        == 1
    )
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert workspace is not None
    assert workspace.current_tree_hash == canonical_before
