from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_governed_final_review import _create_package
from test_phase5_validation_suites import (
    SuiteContext,
    _complete_step,
    _prepare_suite,
)
from test_workspace_api import REVISION, runner_headers
from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewDecision,
    ReviewFreshnessState,
    ReviewPackage,
    ReviewPackageInvalidation,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.runner import Runner
from visual_engineer_api.repositories.review import ReviewRepository
from visual_engineer_api.repositories.workspace import WorkspaceRepository
from visual_engineer_api.schemas.review import ReviewDecisionCreate
from visual_engineer_api.services.review import ReviewService, ReviewServiceError
from visual_engineer_api.services.workspace import WorkspaceService
from visual_engineer_runner_protocol import RepositoryRegistrationRequest

CHANGED_REVISION = "e" * 40


class ForcedCommitFailure(RuntimeError):
    pass


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _successful_context(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> tuple[SuiteContext, dict[str, Any]]:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    first = _complete_step(
        client,
        context,
        context.suite_run,
        sequence=1,
        exit_code=0,
    )
    completed = _complete_step(
        client,
        context,
        first,
        sequence=2,
        exit_code=0,
    )
    assert completed["state"] == "succeeded"
    return context, completed


def _registration_payload(
    context: SuiteContext,
    revision: str,
) -> dict[str, object]:
    return {
        "runner_id": context.runner["runner_id"],
        "opaque_handle": "fixture-repository-v1",
        "display_name": "Phase 4 Adversarial Fixture",
        "vcs_kind": "git",
        "capabilities": ["committed_head_read", "isolated_workspace"],
        "current_revision": revision,
        "current_branch": "main",
        "source_is_dirty": True,
        "dirty_path_count": 2,
        "metadata_version": 1,
    }


def _reregister(
    client: TestClient,
    context: SuiteContext,
    revision: str,
) -> None:
    response = client.post(
        "/api/v1/runner-protocol/v1/repositories/register",
        headers=runner_headers(context.token),
        json=_registration_payload(context, revision),
    )
    assert response.status_code == 200, response.text
    assert response.json()["current_revision"] == revision


def _approve(
    client: TestClient,
    package: dict[str, Any],
    *,
    key: str,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": key},
        json={
            "decision": "approve",
            "reason": "Independent exact-generation approval.",
            "expected_generation": package["freshness_generation"],
        },
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _decision_row(
    package: ReviewPackage,
    *,
    decision_value: str,
    reason: str,
    key: str,
) -> ReviewDecision:
    decision_id = uuid.uuid4()
    request_payload = {
        "review_package_id": str(package.id),
        "package_version": package.package_version,
        "expected_generation": package.freshness_generation,
        "package_digest": package.package_digest,
        "policy_digest": package.suite_policy_digest,
        "decision": decision_value,
        "reason": reason,
        "actor_type": "local_user",
    }
    request_hash = _canonical_digest(request_payload)
    proof = {
        "review_decision_id": str(decision_id),
        **request_payload,
        "idempotency_key": key,
        "idempotency_request_hash": request_hash,
        "git_authorization": False,
        "deployment_authorization": False,
    }
    return ReviewDecision(
        id=decision_id,
        review_package_id=package.id,
        package_version=package.package_version,
        expected_generation=package.freshness_generation,
        package_digest=package.package_digest,
        policy_digest=package.suite_policy_digest,
        decision=decision_value,
        reason=reason,
        actor_type="local_user",
        request_id=str(uuid.uuid4()),
        idempotency_key=key,
        idempotency_request_hash=request_hash,
        decision_digest=_canonical_digest(proof),
        git_authorization=False,
        deployment_authorization=False,
    )


def _ready_row(
    package: ReviewPackage,
    decision: ReviewDecision,
) -> ReleaseReadinessVerdict:
    proof = {
        "review_package_id": str(package.id),
        "review_decision_id": str(decision.id),
        "package_version": package.package_version,
        "freshness_generation": package.freshness_generation,
        "package_digest": package.package_digest,
        "decision_digest": decision.decision_digest,
        "evidence_manifest_digest": package.evidence_manifest_digest,
        "suite_result_digest": package.suite_result_digest,
        "policy_digest": package.suite_policy_digest,
        "blocker_summary_digest": package.blocker_summary_digest,
        "critical_count": package.critical_count,
        "high_count": package.high_count,
        "blocking_medium_count": package.blocking_medium_count,
        "verdict": "ready",
        "reason_codes": ["all_required_evidence_verified"],
        "git_authorization": False,
        "deployment_authorization": False,
    }
    return ReleaseReadinessVerdict(
        review_package_id=package.id,
        review_decision_id=decision.id,
        package_version=package.package_version,
        freshness_generation=package.freshness_generation,
        package_digest=package.package_digest,
        decision_digest=decision.decision_digest,
        evidence_manifest_digest=package.evidence_manifest_digest,
        suite_result_digest=package.suite_result_digest,
        policy_digest=package.suite_policy_digest,
        blocker_summary_digest=package.blocker_summary_digest,
        critical_count=package.critical_count,
        high_count=package.high_count,
        blocking_medium_count=package.blocking_medium_count,
        verdict="ready",
        reason_codes=["all_required_evidence_verified"],
        verdict_digest=_canonical_digest(proof),
        git_authorization=False,
        deployment_authorization=False,
    )


def _sqlstate(error: DBAPIError) -> str | None:
    return cast(str | None, getattr(error.orig, "sqlstate", None))


def _wait_for_lock(
    database_url: str,
    application_name: str,
    *,
    timeout_seconds: float = 5.0,
) -> tuple[str, str]:
    engine = create_engine(database_url)
    deadline = time.monotonic() + timeout_seconds
    try:
        while time.monotonic() < deadline:
            with engine.connect() as connection:
                row = connection.execute(
                    text(
                        """
                        SELECT wait_event_type, wait_event
                        FROM pg_stat_activity
                        WHERE application_name = :application_name
                        ORDER BY backend_start DESC
                        LIMIT 1
                        """
                    ),
                    {"application_name": application_name},
                ).one_or_none()
            if row is not None and row.wait_event_type == "Lock":
                return cast(str, row.wait_event_type), cast(str, row.wait_event)
            time.sleep(0.02)
    finally:
        engine.dispose()
    raise AssertionError(f"{application_name} did not reach a PostgreSQL lock wait")


def _invalidation_events(
    session: Session,
    package_id: uuid.UUID,
) -> list[AuditEvent]:
    return list(
        session.scalars(
            select(AuditEvent).where(
                AuditEvent.review_package_id == package_id,
                AuditEvent.event_type == "review_package_invalidated",
            )
        )
    )


def _invalidation(
    session: Session,
    package_id: uuid.UUID,
) -> ReviewPackageInvalidation | None:
    return session.scalar(
        select(ReviewPackageInvalidation).where(
            ReviewPackageInvalidation.review_package_id == package_id
        )
    )


def test_audit_trusted_revision_change_atomically_invalidates_ready_and_replay_is_idempotent(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    decision_key = f"audit-ready-{uuid.uuid4()}"
    decided = _approve(client, package_payload, key=decision_key)
    ready = client.post(f"/api/v1/review-packages/{package_id}/readiness")
    assert ready.status_code == 200, ready.text
    assert ready.json()["readiness"]["effective_verdict"] == "ready"

    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    scope = db_session.get(ReviewFreshnessState, package.freshness_state_id)
    assert scope is not None
    initial_generation = scope.generation
    initial_decision_id = cast(dict[str, Any], decided["decision"])["id"]

    _reregister(client, context, CHANGED_REVISION)
    _reregister(client, context, CHANGED_REVISION)
    db_session.expire_all()

    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    scope = db_session.get(ReviewFreshnessState, package.freshness_state_id)
    invalidation = db_session.scalar(
        select(ReviewPackageInvalidation).where(
            ReviewPackageInvalidation.review_package_id == package_id
        )
    )
    historical_ready = db_session.scalar(
        select(ReleaseReadinessVerdict).where(
            ReleaseReadinessVerdict.review_package_id == package_id
        )
    )
    assert scope is not None
    assert invalidation is not None
    assert historical_ready is not None
    assert scope.generation == initial_generation + 1
    assert invalidation.reason_code == "source_revision_changed"
    assert historical_ready.verdict == "ready"
    assert len(_invalidation_events(db_session, package_id)) == 1

    observed = client.get(f"/api/v1/review-packages/{package_id}")
    assert observed.status_code == 200, observed.text
    observed_payload = cast(dict[str, Any], observed.json())
    assert observed_payload["freshness"] == "stale"
    assert observed_payload["readiness"]["effective_verdict"] == "stale"
    assert observed_payload["current_freshness_generation"] == initial_generation + 1

    replay = client.post(
        f"/api/v1/review-packages/{package_id}/decisions",
        headers={"Idempotency-Key": decision_key},
        json={
            "decision": "approve",
            "reason": "Independent exact-generation approval.",
            "expected_generation": initial_generation,
        },
    )
    assert replay.status_code == 409, replay.text
    assert replay.json()["error"]["code"] == "review_generation_mismatch"
    assert len(list(db_session.scalars(select(ReviewDecision)))) == 1

    print(
        "AUDIT_LEDGER trusted_revision_change "
        + json.dumps(
            {
                "initial_revision": REVISION,
                "initial_generation": initial_generation,
                "revision_change": CHANGED_REVISION,
                "current_generation": scope.generation,
                "generation_delta": scope.generation - initial_generation,
                "historical_decision_id": initial_decision_id,
                "historical_ready_row": historical_ready.verdict,
                "effective_ready": observed_payload["readiness"]["effective_verdict"],
                "invalidation_reason": invalidation.reason_code,
                "invalidation_rows": 1,
                "invalidation_events": 1,
                "replay_status": replay.status_code,
                "transaction_outcome": "committed",
            },
            sort_keys=True,
        )
    )


def test_audit_failed_commit_rolls_back_revision_generation_invalidation_and_event(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    scope_id = package.freshness_state_id
    handle_id = package.repository_handle_id
    original_generation = package.freshness_generation
    runner_id = uuid.UUID(cast(str, context.runner["runner_id"]))
    db_session.close()

    engine = create_engine(database_url)
    tentative_generation: int | None = None
    try:
        with Session(engine) as session:
            runner = session.get(Runner, runner_id)
            assert runner is not None

            def fail_commit() -> None:
                raise ForcedCommitFailure("independent forced pre-commit rollback")

            monkeypatch.setattr(session, "commit", fail_commit)
            with pytest.raises(ForcedCommitFailure):
                WorkspaceService(session).register_repository(
                    runner,
                    RepositoryRegistrationRequest.model_validate(
                        _registration_payload(context, CHANGED_REVISION)
                    ),
                    request_id=str(uuid.uuid4()),
                )
            tentative_scope = session.get(ReviewFreshnessState, scope_id)
            assert tentative_scope is not None
            tentative_generation = tentative_scope.generation
            assert tentative_generation == original_generation + 1
            assert _invalidation(session, package_id) is not None
            assert len(_invalidation_events(session, package_id)) == 1
            session.rollback()

        with Session(engine) as session:
            scope = session.get(ReviewFreshnessState, scope_id)
            handle = session.execute(
                text("SELECT current_revision FROM repository_handles WHERE id = :id"),
                {"id": handle_id},
            ).scalar_one()
            assert scope is not None
            assert scope.generation == original_generation
            assert handle == REVISION
            assert _invalidation(session, package_id) is None
            assert _invalidation_events(session, package_id) == []
            print(
                "AUDIT_LEDGER forced_rollback "
                + json.dumps(
                    {
                        "initial_generation": original_generation,
                        "tentative_generation": tentative_generation,
                        "final_generation": scope.generation,
                        "final_revision": handle,
                        "invalidation_rows": 0,
                        "invalidation_events": 0,
                        "transaction_outcome": "rolled_back",
                    },
                    sort_keys=True,
                )
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize("decision_value", ("approve", "reject", "changes_requested"))
def test_audit_old_generation_repository_write_rejects_every_decision_value(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    decision_value: str,
) -> None:
    _context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package = db_session.get(
        ReviewPackage,
        uuid.UUID(cast(str, package_payload["id"])),
    )
    assert package is not None
    db_session.execute(
        text(
            """
            UPDATE repository_handles
            SET current_revision = :revision
            WHERE id = :handle_id
            """
        ),
        {
            "revision": CHANGED_REVISION,
            "handle_id": package.repository_handle_id,
        },
    )
    db_session.commit()

    decision = _decision_row(
        package,
        decision_value=decision_value,
        reason="Independent old-generation repository write denial.",
        key=f"audit-stale-{decision_value}-{uuid.uuid4()}",
    )
    ReviewRepository(db_session).add(decision)
    with pytest.raises(DBAPIError) as captured:
        db_session.commit()
    expected_sqlstate = "22001" if decision_value == "changes_requested" else "55000"
    assert _sqlstate(captured.value) == expected_sqlstate
    db_session.rollback()

    assert (
        db_session.scalar(
            select(ReviewDecision).where(ReviewDecision.review_package_id == package.id)
        )
        is None
    )
    assert db_session.scalar(select(ReleaseReadinessVerdict)) is None
    print(
        "AUDIT_LEDGER stale_repository_write "
        + json.dumps(
            {
                "decision": decision_value,
                "expected_generation": package.freshness_generation,
                "revision": CHANGED_REVISION,
                "sqlstate": expected_sqlstate,
                "decision_rows": 0,
                "ready_rows": 0,
                "transaction_outcome": "rolled_back",
            },
            sort_keys=True,
        )
    )


def test_audit_changes_requested_is_closed_at_api_and_fresh_database_domain(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    _context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package = db_session.get(
        ReviewPackage,
        uuid.UUID(cast(str, package_payload["id"])),
    )
    assert package is not None

    api_response = client.post(
        f"/api/v1/review-packages/{package.id}/decisions",
        json={
            "decision": "changes_requested",
            "reason": "Unsupported terminal domain probe.",
            "expected_generation": package.freshness_generation,
        },
    )
    assert api_response.status_code == 422

    decision = _decision_row(
        package,
        decision_value="changes_requested",
        reason="Unsupported terminal domain probe.",
        key=f"audit-fresh-changes-requested-{uuid.uuid4()}",
    )
    ReviewRepository(db_session).add(decision)
    with pytest.raises(DBAPIError) as captured:
        db_session.commit()
    assert _sqlstate(captured.value) == "22001"
    db_session.rollback()
    assert db_session.scalar(select(ReviewDecision)) is None


def test_audit_direct_ready_write_after_out_of_band_revision_drift_is_rejected(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    _context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    decided = _approve(
        client,
        package_payload,
        key=f"audit-direct-ready-{uuid.uuid4()}",
    )
    package = db_session.get(
        ReviewPackage,
        uuid.UUID(cast(str, package_payload["id"])),
    )
    decision = db_session.get(
        ReviewDecision,
        uuid.UUID(cast(str, cast(dict[str, Any], decided["decision"])["id"])),
    )
    assert package is not None
    assert decision is not None

    db_session.execute(
        text(
            """
            UPDATE repository_handles
            SET current_revision = :revision
            WHERE id = :handle_id
            """
        ),
        {
            "revision": CHANGED_REVISION,
            "handle_id": package.repository_handle_id,
        },
    )
    db_session.commit()
    scope = db_session.get(ReviewFreshnessState, package.freshness_state_id)
    assert scope is not None
    assert scope.generation == package.freshness_generation
    assert db_session.get(ReviewPackageInvalidation, package.id) is None

    ReviewRepository(db_session).add(_ready_row(package, decision))
    with pytest.raises(DBAPIError) as captured:
        db_session.commit()
    assert _sqlstate(captured.value) == "55000"
    db_session.rollback()
    assert db_session.scalar(select(ReleaseReadinessVerdict)) is None


def test_audit_approve_lock_first_then_revision_invalidates_historical_decision(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
) -> None:
    context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    generation = cast(int, package_payload["freshness_generation"])
    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    handle_id = package.repository_handle_id
    runner_id = uuid.UUID(cast(str, context.runner["runner_id"]))
    db_session.close()

    revision_application = f"ve-audit-revision-wait-{uuid.uuid4()}"

    def revise() -> str:
        engine = create_engine(
            database_url,
            connect_args={"application_name": revision_application},
        )
        try:
            with Session(engine) as session:
                runner = session.get(Runner, runner_id)
                assert runner is not None
                WorkspaceService(session).register_repository(
                    runner,
                    RepositoryRegistrationRequest.model_validate(
                        _registration_payload(context, CHANGED_REVISION)
                    ),
                    request_id=str(uuid.uuid4()),
                )
                return "revision_committed"
        finally:
            engine.dispose()

    approval_engine = create_engine(database_url)
    try:
        with Session(approval_engine) as approval_session:
            service = ReviewService(approval_session)
            locked = service._required_package_with_revision_authority(package_id)
            assert locked.repository_handle_id == handle_id
            with ThreadPoolExecutor(max_workers=1) as executor:
                revision_future = executor.submit(revise)
                wait_type, wait_event = _wait_for_lock(
                    database_url,
                    revision_application,
                )
                decided = service.decide(
                    package_id,
                    ReviewDecisionCreate(
                        decision="approve",
                        reason="Approval acquired the revision lock first.",
                        expected_generation=generation,
                    ),
                    request_id=str(uuid.uuid4()),
                    idempotency_key=f"audit-approve-first-{uuid.uuid4()}",
                )
                assert decided.decision is not None
                assert decided.decision.decision == "approve"
                assert revision_future.result() == "revision_committed"

        with Session(approval_engine) as session:
            scope = session.get(ReviewFreshnessState, locked.freshness_state_id)
            assert scope is not None
            assert scope.generation == generation + 1
            assert _invalidation(session, package_id) is not None
            assert len(_invalidation_events(session, package_id)) == 1
            assert (
                len(
                    list(
                        session.scalars(
                            select(ReviewDecision).where(
                                ReviewDecision.review_package_id == package_id
                            )
                        )
                    )
                )
                == 1
            )
            assert session.scalar(select(ReleaseReadinessVerdict)) is None
            print(
                "AUDIT_LEDGER approve_lock_first "
                + json.dumps(
                    {
                        "approve": "committed_before_revision",
                        "revision": "committed_after_approve",
                        "generation": scope.generation,
                        "invalidation_rows": 1,
                        "invalidation_events": 1,
                        "ready_rows": 0,
                        "wait_event": wait_event,
                        "wait_event_type": wait_type,
                    },
                    sort_keys=True,
                )
            )
    finally:
        approval_engine.dispose()


def test_audit_revision_lock_first_rejects_waiting_approve(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
) -> None:
    context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    generation = cast(int, package_payload["freshness_generation"])
    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    handle_id = package.repository_handle_id
    runner_id = uuid.UUID(cast(str, context.runner["runner_id"]))
    scope_id = package.freshness_state_id
    db_session.close()

    approval_application = f"ve-audit-approve-wait-{uuid.uuid4()}"

    def approve() -> str:
        engine = create_engine(
            database_url,
            connect_args={"application_name": approval_application},
        )
        try:
            with Session(engine) as session:
                try:
                    ReviewService(session).decide(
                        package_id,
                        ReviewDecisionCreate(
                            decision="approve",
                            reason="Revision acquired the authority lock first.",
                            expected_generation=generation,
                        ),
                        request_id=str(uuid.uuid4()),
                        idempotency_key=f"audit-revision-first-{uuid.uuid4()}",
                    )
                except ReviewServiceError as exc:
                    return exc.code
                return "approve"
        finally:
            engine.dispose()

    revision_engine = create_engine(database_url)
    try:
        with Session(revision_engine) as revision_session:
            repository = ReviewRepository(revision_session)
            repository.lock_revision_authority(handle_id)
            assert repository.revision_authority(handle_id, lock=True) is not None
            runner = revision_session.get(Runner, runner_id)
            assert runner is not None
            with ThreadPoolExecutor(max_workers=1) as executor:
                approval_future = executor.submit(approve)
                wait_type, wait_event = _wait_for_lock(
                    database_url,
                    approval_application,
                )
                WorkspaceService(revision_session).register_repository(
                    runner,
                    RepositoryRegistrationRequest.model_validate(
                        _registration_payload(context, CHANGED_REVISION)
                    ),
                    request_id=str(uuid.uuid4()),
                )
                approval_outcome = approval_future.result()
            assert approval_outcome in {
                "review_generation_mismatch",
                "stale_review_package",
            }

        with Session(revision_engine) as session:
            scope = session.get(ReviewFreshnessState, scope_id)
            assert scope is not None
            assert scope.generation == generation + 1
            assert _invalidation(session, package_id) is not None
            assert session.scalar(select(ReviewDecision)) is None
            assert session.scalar(select(ReleaseReadinessVerdict)) is None
            print(
                "AUDIT_LEDGER revision_lock_first "
                + json.dumps(
                    {
                        "approve": approval_outcome,
                        "revision": "committed_before_approve",
                        "generation": scope.generation,
                        "decision_rows": 0,
                        "ready_rows": 0,
                        "wait_event": wait_event,
                        "wait_event_type": wait_type,
                    },
                    sort_keys=True,
                )
            )
    finally:
        revision_engine.dispose()


def test_audit_concurrent_duplicate_revision_replay_advances_once(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    scope_id = package.freshness_state_id
    original_generation = package.freshness_generation
    runner_id = uuid.UUID(cast(str, context.runner["runner_id"]))
    db_session.close()
    barrier = threading.Barrier(2)
    original_lookup = WorkspaceRepository.get_repository_handle_by_opaque

    def synchronized_lookup(
        repository: WorkspaceRepository,
        lookup_runner_id: uuid.UUID,
        opaque_handle: str,
        *,
        lock: bool = False,
    ) -> Any:
        result = original_lookup(
            repository,
            lookup_runner_id,
            opaque_handle,
            lock=lock,
        )
        if not lock:
            barrier.wait(timeout=5)
        return result

    monkeypatch.setattr(
        WorkspaceRepository,
        "get_repository_handle_by_opaque",
        synchronized_lookup,
    )

    def revise(application_name: str) -> str:
        engine = create_engine(
            database_url,
            connect_args={"application_name": application_name},
        )
        try:
            with Session(engine) as session:
                runner = session.get(Runner, runner_id)
                assert runner is not None
                response = WorkspaceService(session).register_repository(
                    runner,
                    RepositoryRegistrationRequest.model_validate(
                        _registration_payload(context, CHANGED_REVISION)
                    ),
                    request_id=str(uuid.uuid4()),
                )
                return response.current_revision
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                revise,
                (
                    f"ve-audit-duplicate-a-{uuid.uuid4()}",
                    f"ve-audit-duplicate-b-{uuid.uuid4()}",
                ),
            )
        )
    assert outcomes == [CHANGED_REVISION, CHANGED_REVISION]

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            scope = session.get(ReviewFreshnessState, scope_id)
            assert scope is not None
            invalidation = _invalidation(session, package_id)
            events = _invalidation_events(session, package_id)
            current_revision = session.execute(
                text("SELECT current_revision FROM repository_handles WHERE id = :id"),
                {"id": package.repository_handle_id},
            ).scalar_one()
            print(
                "AUDIT_LEDGER concurrent_duplicate_revision "
                + json.dumps(
                    {
                        "initial_generation": original_generation,
                        "current_generation": scope.generation,
                        "generation_delta": scope.generation - original_generation,
                        "current_revision": current_revision,
                        "registration_outcomes": outcomes,
                        "invalidation_rows": int(invalidation is not None),
                        "invalidation_events": len(events),
                        "decision_rows": len(list(session.scalars(select(ReviewDecision)))),
                        "ready_rows": len(list(session.scalars(select(ReleaseReadinessVerdict)))),
                    },
                    sort_keys=True,
                )
            )
            assert scope.generation == original_generation + 1
            assert invalidation is not None
            assert len(events) == 1
            assert session.scalar(select(ReviewDecision)) is None
            assert session.scalar(select(ReleaseReadinessVerdict)) is None
    finally:
        engine.dispose()


def test_audit_invalidation_audit_event_is_append_only(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context, completed = _successful_context(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    _reregister(client, context, CHANGED_REVISION)
    db_session.expire_all()
    events = _invalidation_events(db_session, package_id)
    assert len(events) == 1
    event_id = events[0].id
    original_type = events[0].event_type

    with pytest.raises(DBAPIError) as update_error:
        db_session.execute(
            text("UPDATE audit_events SET event_type = 'tampered' WHERE id = :id"),
            {"id": event_id},
        )
    assert _sqlstate(update_error.value) == "55000"
    db_session.rollback()

    with pytest.raises(DBAPIError) as delete_error:
        db_session.execute(
            text("DELETE FROM audit_events WHERE id = :id"),
            {"id": event_id},
        )
    assert _sqlstate(delete_error.value) == "55000"
    db_session.rollback()

    persisted = db_session.get(AuditEvent, event_id)
    assert persisted is not None
    assert persisted.event_type == original_type
    assert len(_invalidation_events(db_session, package_id)) == 1
