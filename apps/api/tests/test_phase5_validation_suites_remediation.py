from __future__ import annotations

import copy
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_validation_suites import (
    SuiteContext,
    _complete_step,
    _prepare_suite,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.runner import RunnerJob, RunnerJobAttempt
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
)
from visual_engineer_api.schemas.validation import ValidationSuiteRunCreate
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError
from visual_engineer_api.services.validation import ValidationService
from visual_engineer_api.services.validation_suite import (
    ValidationSuiteService,
    ValidationSuiteServiceError,
)


def _durable_counts(session: Session) -> tuple[int, ...]:
    return tuple(
        int(session.scalar(select(func.count()).select_from(model)) or 0)
        for model in (
            ValidationSuiteRun,
            ValidationSuiteStepRun,
            ValidationRun,
            RunnerJob,
            RunnerJobAttempt,
            SideEffectPermit,
            ValidationSuiteResult,
            ValidationEvidence,
            AuditEvent,
        )
    )


def _assert_concurrent_suite_create(
    context: SuiteContext,
    *,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    same_idempotency_key: bool,
    submission_order: tuple[int, int],
) -> None:
    engine = create_engine(database_url)
    grant_lock_barrier = threading.Barrier(2)
    first_grant_locked = threading.Event()
    worker_state = threading.local()
    shared_key = f"suite-race-{uuid.uuid4()}"
    original_required_grant = ValidationSuiteService._required_suite_grant

    def synchronize_before_grant_lock(
        service: ValidationSuiteService,
        grant_id: uuid.UUID,
        suite_reference: str,
        *,
        expected_attempt_number: int,
        expected_root_suite_run_id: uuid.UUID | None,
        expected_retry_of_suite_run_id: uuid.UUID | None,
    ) -> tuple[Any, ...]:
        if not getattr(worker_state, "grant_barrier_passed", False):
            worker_state.grant_barrier_passed = True
            grant_lock_barrier.wait(timeout=10)
        if worker_state.worker != submission_order[0]:
            if not first_grant_locked.wait(timeout=10):
                raise TimeoutError("timed out waiting for the ordered Suite Grant lock")
            return original_required_grant(
                service,
                grant_id,
                suite_reference,
                expected_attempt_number=expected_attempt_number,
                expected_root_suite_run_id=expected_root_suite_run_id,
                expected_retry_of_suite_run_id=expected_retry_of_suite_run_id,
            )
        result = original_required_grant(
            service,
            grant_id,
            suite_reference,
            expected_attempt_number=expected_attempt_number,
            expected_root_suite_run_id=expected_root_suite_run_id,
            expected_retry_of_suite_run_id=expected_retry_of_suite_run_id,
        )
        first_grant_locked.set()
        return result

    monkeypatch.setattr(
        ValidationSuiteService,
        "_required_suite_grant",
        synchronize_before_grant_lock,
    )

    def create_once(worker: int) -> tuple[str, str]:
        worker_state.worker = worker
        key = shared_key if same_idempotency_key else f"{shared_key}-{worker}"
        with Session(engine) as session:
            try:
                response = ValidationSuiteService(session).create(
                    ValidationSuiteRunCreate(
                        execution_grant_id=uuid.UUID(context.grant_id),
                        suite_id="fixture-integrity-suite-v1",
                        suite_version=1,
                    ),
                    idempotency_key=key,
                    request_id=f"suite-race-{worker}",
                )
                return "created", str(response.id)
            except ValidationSuiteServiceError as exc:
                return "denied", exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            future.result(timeout=30)
            for future in [executor.submit(create_once, worker) for worker in submission_order]
        ]

    with Session(engine) as verification:
        suite_ids = list(
            verification.scalars(
                select(ValidationSuiteRun.id).where(
                    ValidationSuiteRun.execution_grant_id == uuid.UUID(context.grant_id)
                )
            )
        )
        child_count = int(
            verification.scalar(
                select(func.count(ValidationRun.id)).where(
                    ValidationRun.execution_grant_id == uuid.UUID(context.grant_id)
                )
            )
            or 0
        )
        child_job_count = int(
            verification.scalar(
                select(func.count(RunnerJob.id)).where(
                    RunnerJob.execution_grant_id == uuid.UUID(context.grant_id)
                )
            )
            or 0
        )
        unbound_child_count = int(
            verification.scalar(
                select(func.count(ValidationRun.id)).where(
                    ValidationRun.execution_grant_id == uuid.UUID(context.grant_id),
                    ValidationRun.runner_job_id.is_(None),
                )
            )
            or 0
        )
    engine.dispose()

    assert len(suite_ids) == 1
    assert child_count == 1
    assert child_job_count == 1
    assert unbound_child_count == 0
    if same_idempotency_key:
        assert [result[0] for result in results] == ["created", "created"]
        assert {result[1] for result in results} == {str(suite_ids[0])}
    else:
        assert [result[0] for result in results] == ["created", "denied"]
        assert results[1][1] == ("validation_suite_grant_already_consumed")


@pytest.mark.parametrize("same_idempotency_key", [True, False])
def test_concurrent_suite_create_consumes_one_grant_exactly_once(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    same_idempotency_key: bool,
) -> None:
    context = _prepare_suite(
        client,
        db_session,
        runner_bootstrap_token,
        start_suite=False,
    )
    db_session.commit()
    _assert_concurrent_suite_create(
        context,
        database_url=database_url,
        monkeypatch=monkeypatch,
        same_idempotency_key=same_idempotency_key,
        submission_order=(1, 2),
    )


@pytest.mark.parametrize("same_idempotency_key", [True, False])
def test_concurrent_suite_create_reverse_submission_order(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    same_idempotency_key: bool,
) -> None:
    context = _prepare_suite(
        client,
        db_session,
        runner_bootstrap_token,
        start_suite=False,
    )
    db_session.commit()
    _assert_concurrent_suite_create(
        context,
        database_url=database_url,
        monkeypatch=monkeypatch,
        same_idempotency_key=same_idempotency_key,
        submission_order=(2, 1),
    )


def test_suite_child_dispatch_rollback_has_no_partial_rows(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _prepare_suite(
        client,
        db_session,
        runner_bootstrap_token,
        start_suite=False,
    )
    db_session.commit()
    engine = create_engine(database_url)
    original_create_workspace_job = RunnerService.create_workspace_job
    independent_observations: list[tuple[int, int]] = []

    def fail_after_non_committing_flush(
        service: RunnerService,
        spec: Any,
        *,
        request_id: str,
        commit: bool = True,
    ) -> Any:
        assert commit is False
        original_create_workspace_job(
            service,
            spec,
            request_id=request_id,
            commit=commit,
        )
        with Session(engine) as observer:
            independent_observations.append(
                (
                    int(
                        observer.scalar(
                            select(func.count(ValidationRun.id)).where(
                                ValidationRun.execution_grant_id == uuid.UUID(context.grant_id)
                            )
                        )
                        or 0
                    ),
                    int(
                        observer.scalar(
                            select(func.count(RunnerJob.id)).where(
                                RunnerJob.execution_grant_id == uuid.UUID(context.grant_id)
                            )
                        )
                        or 0
                    ),
                )
            )
        raise RunnerServiceError(
            "injected_validation_dispatch_failure",
            "Injected Validation dispatch failure",
            category="internal",
        )

    monkeypatch.setattr(
        RunnerService,
        "create_workspace_job",
        fail_after_non_committing_flush,
    )
    shared_key = f"suite-dispatch-rollback-{uuid.uuid4()}"
    with Session(engine) as session:
        created = ValidationSuiteService(session).create(
            ValidationSuiteRunCreate(
                execution_grant_id=uuid.UUID(context.grant_id),
                suite_id="fixture-integrity-suite-v1",
                suite_version=1,
            ),
            idempotency_key=shared_key,
            request_id="suite-dispatch-rollback",
        )

    assert independent_observations == [(0, 0)]
    assert created.state == "recovery_required"
    assert created.error_code == "injected_validation_dispatch_failure"
    assert created.execution_grant_id == uuid.UUID(context.grant_id)
    assert created.steps[0].state == "recovery_required"
    assert created.steps[0].validation_run_id is None
    assert created.steps[0].runner_job_id is None

    with Session(engine) as verification:
        assert (
            verification.scalar(
                select(func.count(ValidationSuiteRun.id)).where(
                    ValidationSuiteRun.execution_grant_id == uuid.UUID(context.grant_id)
                )
            )
            == 1
        )
        assert (
            verification.scalar(
                select(func.count(ValidationRun.id)).where(
                    ValidationRun.execution_grant_id == uuid.UUID(context.grant_id)
                )
            )
            == 0
        )
        assert (
            verification.scalar(
                select(func.count(RunnerJob.id)).where(
                    RunnerJob.execution_grant_id == uuid.UUID(context.grant_id)
                )
            )
            == 0
        )
        replay = ValidationSuiteService(verification).create(
            ValidationSuiteRunCreate(
                execution_grant_id=uuid.UUID(context.grant_id),
                suite_id="fixture-integrity-suite-v1",
                suite_version=1,
            ),
            idempotency_key=shared_key,
            request_id="suite-dispatch-rollback-replay",
        )
        assert replay.id == created.id
        with pytest.raises(
            ValidationSuiteServiceError,
            match="Suite-scoped Execution Grant already authorizes a Suite lineage",
        ) as denied:
            ValidationSuiteService(verification).create(
                ValidationSuiteRunCreate(
                    execution_grant_id=uuid.UUID(context.grant_id),
                    suite_id="fixture-integrity-suite-v1",
                    suite_version=1,
                ),
                idempotency_key=f"{shared_key}-different",
                request_id="suite-dispatch-rollback-different-key",
            )
        assert denied.value.code == "validation_suite_grant_already_consumed"
    engine.dispose()


def test_disjoint_suite_grants_do_not_share_a_global_lock(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _prepare_suite(client, db_session, runner_bootstrap_token, start_suite=False)
    second = _prepare_suite(client, db_session, runner_bootstrap_token, start_suite=False)
    db_session.commit()
    engine = create_engine(database_url)
    first_grant_locked = threading.Event()
    release_first_grant = threading.Event()
    original_required_grant = ValidationSuiteService._required_suite_grant

    def hold_first_exact_grant(
        service: ValidationSuiteService,
        grant_id: uuid.UUID,
        suite_reference: str,
        *,
        expected_attempt_number: int,
        expected_root_suite_run_id: uuid.UUID | None,
        expected_retry_of_suite_run_id: uuid.UUID | None,
    ) -> tuple[Any, ...]:
        result = original_required_grant(
            service,
            grant_id,
            suite_reference,
            expected_attempt_number=expected_attempt_number,
            expected_root_suite_run_id=expected_root_suite_run_id,
            expected_retry_of_suite_run_id=expected_retry_of_suite_run_id,
        )
        if grant_id == uuid.UUID(first.grant_id) and not first_grant_locked.is_set():
            first_grant_locked.set()
            if not release_first_grant.wait(timeout=10):
                raise TimeoutError("timed out holding the first exact Suite Grant lock")
        return result

    monkeypatch.setattr(
        ValidationSuiteService,
        "_required_suite_grant",
        hold_first_exact_grant,
    )

    def create_for(context: SuiteContext, worker: str) -> uuid.UUID:
        with Session(engine) as session:
            response = ValidationSuiteService(session).create(
                ValidationSuiteRunCreate(
                    execution_grant_id=uuid.UUID(context.grant_id),
                    suite_id="fixture-integrity-suite-v1",
                    suite_version=1,
                ),
                idempotency_key=f"disjoint-suite-{worker}-{uuid.uuid4()}",
                request_id=f"disjoint-suite-{worker}",
            )
            return response.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(create_for, first, "first")
        assert first_grant_locked.wait(timeout=10)
        second_future = executor.submit(create_for, second, "second")
        try:
            second_id = second_future.result(timeout=10)
        finally:
            release_first_grant.set()
        first_id = first_future.result(timeout=10)

    assert first_id != second_id
    with Session(engine) as verification:
        assert (
            verification.scalar(
                select(func.count(ValidationSuiteRun.id)).where(
                    ValidationSuiteRun.execution_grant_id.in_(
                        (uuid.UUID(first.grant_id), uuid.UUID(second.grant_id))
                    )
                )
            )
            == 2
        )
    engine.dispose()


@pytest.mark.parametrize("authority_failure", ["revoked", "expired", "stale"])
def test_inactive_or_stale_suite_grant_has_zero_success_side_effects(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    monkeypatch: pytest.MonkeyPatch,
    authority_failure: str,
) -> None:
    context = _prepare_suite(
        client,
        db_session,
        runner_bootstrap_token,
        start_suite=False,
    )
    grant = db_session.get(ExecutionGrant, uuid.UUID(context.grant_id))
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert grant is not None
    assert workspace is not None

    if authority_failure == "revoked":
        revoked = client.post(
            f"/api/v1/execution-grants/{context.grant_id}/revoke",
            headers={"X-Request-ID": str(uuid.uuid4())},
        )
        assert revoked.status_code == 200, revoked.text
    elif authority_failure == "expired":
        expired_now = grant.expires_at + timedelta(seconds=1)
        monkeypatch.setattr(
            "visual_engineer_api.services.validation_suite.utc_now",
            lambda: expired_now,
        )
    else:
        workspace.current_tree_hash = "f" * 64
        db_session.commit()

    db_session.expire_all()
    before = _durable_counts(db_session)
    baseline_before = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert baseline_before is not None
    baseline_hash = baseline_before.current_tree_hash
    denied = client.post(
        "/api/v1/validation-suite-runs",
        headers={"Idempotency-Key": f"denied-suite-{uuid.uuid4()}"},
        json={
            "execution_grant_id": context.grant_id,
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
        },
    )
    assert denied.status_code == 409, denied.text
    expected_code = (
        "stale_validation_baseline" if authority_failure == "stale" else "validation_grant_inactive"
    )
    assert denied.json()["error"]["code"] == expected_code

    db_session.expire_all()
    after = _durable_counts(db_session)
    baseline_after = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert baseline_after is not None
    assert after == before
    assert baseline_after.current_tree_hash == baseline_hash


def _completed_child_binding(
    db_session: Session,
    context: SuiteContext,
    *,
    sequence: int = 1,
) -> dict[str, Any]:
    db_session.expire_all()
    suite_step = db_session.scalar(
        select(ValidationSuiteStepRun).where(
            ValidationSuiteStepRun.suite_run_id == uuid.UUID(context.suite_run["id"]),
            ValidationSuiteStepRun.sequence == sequence,
        )
    )
    assert suite_step is not None
    assert suite_step.validation_run_id is not None
    ValidationService(db_session).get(suite_step.validation_run_id)
    db_session.expire_all()
    suite_step = db_session.get(ValidationSuiteStepRun, suite_step.id)
    assert suite_step is not None
    assert suite_step.validation_run_id is not None
    child = db_session.get(ValidationRun, suite_step.validation_run_id)
    evidence = db_session.scalar(
        select(ValidationEvidence).where(
            ValidationEvidence.validation_run_id == suite_step.validation_run_id
        )
    )
    assert child is not None
    assert evidence is not None
    assert child.runner_job_id is not None
    assert child.runner_id is not None
    assert child.attempt_id is not None
    assert child.lease_id is not None
    return {
        "validation_run_id": child.id,
        "runner_job_id": child.runner_job_id,
        "runner_id": child.runner_id,
        "attempt_id": child.attempt_id,
        "lease_id": child.lease_id,
        "evidence_id": evidence.id,
        "started_at": evidence.started_at,
        "completed_at": evidence.completed_at,
        "duration_ms": evidence.duration_ms,
        "output_bytes": len(evidence.stdout.encode("utf-8")) + len(evidence.stderr.encode("utf-8")),
        "redaction_count": evidence.redaction_count,
        "output_truncated": evidence.stdout_truncated or evidence.stderr_truncated,
    }


def _persist_step_success(
    db_session: Session,
    *,
    step_id: str,
    binding: dict[str, Any],
) -> None:
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
        {**binding, "step_id": step_id},
    )


def test_database_rejects_foreign_or_mismatched_success_proof_bindings(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    primary = _prepare_suite(client, db_session, runner_bootstrap_token)
    foreign = _prepare_suite(client, db_session, runner_bootstrap_token)
    _complete_step(
        client,
        primary,
        primary.suite_run,
        sequence=1,
        exit_code=0,
        synchronize_suite=False,
    )
    _complete_step(
        client,
        foreign,
        foreign.suite_run,
        sequence=1,
        exit_code=0,
        synchronize_suite=False,
    )
    primary_binding = _completed_child_binding(db_session, primary)
    foreign_binding = _completed_child_binding(db_session, foreign)
    primary_step = next(step for step in primary.suite_run["steps"] if step["sequence"] == 1)
    before = _durable_counts(db_session)

    mutations: list[dict[str, Any]] = [
        {**primary_binding, "evidence_id": foreign_binding["evidence_id"]},
        {**primary_binding, "attempt_id": foreign_binding["attempt_id"]},
        {**primary_binding, "lease_id": foreign_binding["lease_id"]},
        {**primary_binding, "runner_job_id": foreign_binding["runner_job_id"]},
        {**primary_binding, "validation_run_id": foreign_binding["validation_run_id"]},
        dict(foreign_binding),
    ]
    for mutation in mutations:
        with pytest.raises(DBAPIError):
            with db_session.begin_nested():
                _persist_step_success(
                    db_session,
                    step_id=primary_step["id"],
                    binding=mutation,
                )
        db_session.expire_all()
        assert _durable_counts(db_session) == before

    for injected_definition in (
        "UPDATE validation_suite_step_runs SET sequence = 2 WHERE id = :step_id",
        "UPDATE validation_suite_step_runs SET step_id = 'fixture-manifest' WHERE id = :step_id",
        "UPDATE validation_suite_step_runs SET profile_version = 2 WHERE id = :step_id",
    ):
        with pytest.raises(DBAPIError):
            with db_session.begin_nested():
                db_session.execute(text(injected_definition), {"step_id": primary_step["id"]})
        db_session.expire_all()
        assert _durable_counts(db_session) == before

    _persist_step_success(
        db_session,
        step_id=primary_step["id"],
        binding=primary_binding,
    )
    db_session.commit()


def test_database_rejects_missing_duplicate_reordered_or_stale_aggregate_evidence(
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
    _complete_step(
        client,
        context,
        after_first,
        sequence=2,
        exit_code=0,
        synchronize_suite=False,
    )
    db_session.expire_all()
    suite_run = db_session.get(ValidationSuiteRun, uuid.UUID(context.suite_run["id"]))
    assert suite_run is not None
    second_step = db_session.scalar(
        select(ValidationSuiteStepRun).where(
            ValidationSuiteStepRun.suite_run_id == suite_run.id,
            ValidationSuiteStepRun.sequence == 2,
        )
    )
    assert second_step is not None
    second_binding = _completed_child_binding(db_session, context, sequence=2)
    _persist_step_success(
        db_session,
        step_id=str(second_step.id),
        binding=second_binding,
    )
    db_session.flush()
    db_session.expire_all()
    steps = list(
        db_session.scalars(
            select(ValidationSuiteStepRun)
            .where(ValidationSuiteStepRun.suite_run_id == suite_run.id)
            .order_by(ValidationSuiteStepRun.sequence)
        )
    )
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
                "evidence_digest": evidence.evidence_digest,
                "reused": False,
            }
        )
        runners.append(str(step.runner_id))
    profiles = [f"{step.profile_id}:v{step.profile_version}" for step in steps]
    completed_at = max(step.completed_at for step in steps if step.completed_at is not None)
    suite_run.state = "succeeded"
    suite_run.completed_step_count = 2
    suite_run.combined_output_bytes = sum(step.output_bytes for step in steps)
    suite_run.completed_at = completed_at
    suite_run.version += 1
    db_session.commit()

    malformed: list[list[dict[str, object]]] = [
        references[:1],
        [copy.deepcopy(references[0]), copy.deepcopy(references[0])],
        list(reversed(copy.deepcopy(references))),
    ]
    for key, value in (
        ("sequence", 2),
        ("step_id", "fixture-manifest"),
        ("profile", "fixture-python-manifest-v1:v1"),
        ("attempt_id", str(uuid.uuid4())),
        ("lease_id", str(uuid.uuid4())),
        ("grant_id", str(uuid.uuid4())),
        ("evidence_id", str(uuid.uuid4())),
        ("evidence_digest", "0" * 64),
    ):
        altered = copy.deepcopy(references)
        altered[0][key] = value
        malformed.append(altered)

    before = _durable_counts(db_session)
    for evidence_references in malformed:
        rejected = ValidationSuiteResult(
            suite_run_id=suite_run.id,
            root_suite_run_id=suite_run.root_suite_run_id,
            run_id=suite_run.run_id,
            execution_grant_id=suite_run.execution_grant_id,
            suite_id=suite_run.suite_id,
            suite_version=suite_run.suite_version,
            source_revision=suite_run.source_revision,
            checkpoint_id=suite_run.checkpoint_id,
            policy_digest=suite_run.policy_digest,
            attempt_number=suite_run.attempt_number,
            total_timeout_seconds=suite_run.total_timeout_seconds,
            total_output_bytes=suite_run.total_output_bytes,
            max_attempts=suite_run.max_attempts,
            verdict="succeeded",
            profile_references=profiles,
            evidence_references=evidence_references,
            runner_references=runners,
            audit_event_references=[],
            started_at=suite_run.started_at or suite_run.requested_at,
            completed_at=completed_at,
            duration_ms=0,
            combined_output_bytes=suite_run.combined_output_bytes,
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
                    ValidationSuiteResult.suite_run_id == suite_run.id,
                    ValidationSuiteResult.verdict == "succeeded",
                )
            )
            == 0
        )
