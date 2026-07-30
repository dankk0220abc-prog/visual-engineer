from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
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
    ReviewBlockerFinding,
    ReviewDecision,
    ReviewFreshnessState,
    ReviewPackage,
    ReviewPackageInvalidation,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.runner import Runner
from visual_engineer_api.models.validation import ValidationEvidence
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    RepositoryHandle,
    Workspace,
)
from visual_engineer_api.schemas.review import ReviewDecisionCreate
from visual_engineer_api.services.review import ReviewService, ReviewServiceError
from visual_engineer_api.services.workspace import WorkspaceService
from visual_engineer_runner_protocol import RepositoryRegistrationRequest

CHANGED_REVISION = "d" * 40


def _successful_context(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> tuple[SuiteContext, dict[str, Any]]:
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
            "reason": "Exact revision freshness generation reviewed.",
            "expected_generation": package["freshness_generation"],
        },
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


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


def test_trusted_revision_registration_atomically_advances_and_invalidates_once(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context, completed = _successful_context(
        client,
        db_session,
        runner_bootstrap_token,
    )
    package = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package["id"]))
    stored = db_session.get(ReviewPackage, package_id)
    assert stored is not None
    scope = db_session.get(ReviewFreshnessState, stored.freshness_state_id)
    workspace = db_session.get(Workspace, stored.workspace_id)
    assert scope is not None
    assert workspace is not None
    original_generation = scope.generation
    original_workspace = (workspace.source_revision, workspace.current_tree_hash)
    original_evidence = list(
        db_session.scalars(
            select(ValidationEvidence.evidence_digest).order_by(ValidationEvidence.id)
        )
    )

    _reregister(client, context, CHANGED_REVISION)
    db_session.expire_all()

    scope = db_session.get(ReviewFreshnessState, stored.freshness_state_id)
    assert scope is not None
    assert scope.generation == original_generation + 1
    assert scope.last_change_kind == "repository_handles:trusted_registration"
    invalidations = list(
        db_session.scalars(
            select(ReviewPackageInvalidation).where(
                ReviewPackageInvalidation.review_package_id == package_id
            )
        )
    )
    assert len(invalidations) == 1
    assert invalidations[0].reason_code == "source_revision_changed"
    assert len(_invalidation_events(db_session, package_id)) == 1

    observed = client.get(f"/api/v1/review-packages/{package_id}")
    assert observed.status_code == 200, observed.text
    observed_payload = cast(dict[str, Any], observed.json())
    assert observed_payload["freshness"] == "stale"
    assert observed_payload["current_freshness_generation"] == original_generation + 1
    assert observed_payload["invalidation"]["reason_code"] == "source_revision_changed"

    _reregister(client, context, CHANGED_REVISION)
    db_session.expire_all()
    scope = db_session.get(ReviewFreshnessState, stored.freshness_state_id)
    assert scope is not None
    assert scope.generation == original_generation + 1
    assert len(_invalidation_events(db_session, package_id)) == 1
    assert (
        len(
            list(
                db_session.scalars(
                    select(ReviewPackageInvalidation).where(
                        ReviewPackageInvalidation.review_package_id == package_id
                    )
                )
            )
        )
        == 1
    )

    workspace = db_session.get(Workspace, stored.workspace_id)
    assert workspace is not None
    assert (workspace.source_revision, workspace.current_tree_hash) == original_workspace
    assert (
        list(
            db_session.scalars(
                select(ValidationEvidence.evidence_digest).order_by(ValidationEvidence.id)
            )
        )
        == original_evidence
    )
    assert all(
        grant.git_delivery_access is False for grant in db_session.scalars(select(ExecutionGrant))
    )


def test_unchanged_revision_registration_does_not_advance_generation(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context, completed = _successful_context(
        client,
        db_session,
        runner_bootstrap_token,
    )
    package = _create_package(client, cast(str, completed["id"]))
    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None
    scope = db_session.get(ReviewFreshnessState, stored.freshness_state_id)
    assert scope is not None
    original_generation = scope.generation

    _reregister(client, context, REVISION)
    db_session.expire_all()

    scope = db_session.get(ReviewFreshnessState, stored.freshness_state_id)
    assert scope is not None
    assert scope.generation == original_generation
    assert (
        db_session.scalar(
            select(ReviewPackageInvalidation).where(
                ReviewPackageInvalidation.review_package_id == stored.id
            )
        )
        is None
    )
    assert _invalidation_events(db_session, stored.id) == []

    unsupported = client.post(
        f"/api/v1/review-packages/{stored.id}/decisions",
        json={
            "decision": "changes_requested",
            "reason": "The Third Slice terminal domain is closed.",
            "expected_generation": original_generation,
        },
    )
    assert unsupported.status_code == 422
    assert (
        db_session.scalar(
            select(ReviewDecision).where(ReviewDecision.review_package_id == stored.id)
        )
        is None
    )


def test_old_generation_keyed_replay_and_direct_readiness_fail_closed(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context, completed = _successful_context(
        client,
        db_session,
        runner_bootstrap_token,
    )
    package = _create_package(client, cast(str, completed["id"]))
    decision_key = f"revision-replay-{uuid.uuid4()}"
    decided = _approve(client, package, key=decision_key)
    decision = cast(dict[str, Any], decided["decision"])
    decision_count = len(list(db_session.scalars(select(ReviewDecision))))

    _reregister(client, context, CHANGED_REVISION)
    db_session.expire_all()

    replay = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": decision_key},
        json={
            "decision": "approve",
            "reason": "Exact revision freshness generation reviewed.",
            "expected_generation": package["freshness_generation"],
        },
    )
    assert replay.status_code == 409, replay.text
    assert replay.json()["error"]["code"] == "review_generation_mismatch"

    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None
    verdict_proof = {
        "review_package_id": str(stored.id),
        "review_decision_id": decision["id"],
        "package_version": stored.package_version,
        "freshness_generation": stored.freshness_generation,
        "package_digest": stored.package_digest,
        "decision_digest": decision["decision_digest"],
        "evidence_manifest_digest": stored.evidence_manifest_digest,
        "suite_result_digest": stored.suite_result_digest,
        "policy_digest": stored.suite_policy_digest,
        "blocker_summary_digest": stored.blocker_summary_digest,
        "critical_count": stored.critical_count,
        "high_count": stored.high_count,
        "blocking_medium_count": stored.blocking_medium_count,
        "verdict": "ready",
        "reason_codes": ["all_required_evidence_verified"],
        "git_authorization": False,
        "deployment_authorization": False,
    }
    db_session.add(
        ReleaseReadinessVerdict(
            review_package_id=stored.id,
            review_decision_id=uuid.UUID(cast(str, decision["id"])),
            package_version=stored.package_version,
            freshness_generation=stored.freshness_generation,
            package_digest=stored.package_digest,
            decision_digest=cast(str, decision["decision_digest"]),
            evidence_manifest_digest=stored.evidence_manifest_digest,
            suite_result_digest=stored.suite_result_digest,
            policy_digest=stored.suite_policy_digest,
            blocker_summary_digest=stored.blocker_summary_digest,
            critical_count=stored.critical_count,
            high_count=stored.high_count,
            blocking_medium_count=stored.blocking_medium_count,
            verdict="ready",
            reason_codes=["all_required_evidence_verified"],
            verdict_digest=ReviewService(db_session)._trusted_digest(verdict_proof),
            git_authorization=False,
            deployment_authorization=False,
        )
    )
    with pytest.raises(DBAPIError):
        db_session.commit()
    db_session.rollback()

    assert len(list(db_session.scalars(select(ReviewDecision)))) == decision_count
    assert db_session.scalar(select(ReleaseReadinessVerdict)) is None
    assert (
        db_session.scalar(
            select(AuditEvent).where(
                AuditEvent.review_package_id == stored.id,
                AuditEvent.event_type == "release_readiness_evaluated",
            )
        )
        is None
    )
    assert len(_invalidation_events(db_session, stored.id)) == 1


@pytest.mark.parametrize("decision_value", ("approve", "reject"))
def test_database_rejects_terminal_decision_after_direct_revision_write(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    decision_value: str,
) -> None:
    _context, completed = _successful_context(
        client,
        db_session,
        runner_bootstrap_token,
    )
    package = _create_package(client, cast(str, completed["id"]))
    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None
    handle = db_session.get(RepositoryHandle, stored.repository_handle_id)
    assert handle is not None
    handle.current_revision = CHANGED_REVISION
    db_session.commit()

    reason = "Direct stale terminal Decision must fail closed."
    decision_id = uuid.uuid4()
    decision_key = f"direct-revision-{decision_value}-{uuid.uuid4()}"
    request_payload = {
        "review_package_id": str(stored.id),
        "package_version": stored.package_version,
        "expected_generation": stored.freshness_generation,
        "package_digest": stored.package_digest,
        "policy_digest": stored.suite_policy_digest,
        "decision": decision_value,
        "reason": reason,
        "actor_type": "local_user",
    }
    service = ReviewService(db_session)
    request_hash = service._trusted_digest(request_payload)
    decision_proof = {
        "review_decision_id": str(decision_id),
        **request_payload,
        "idempotency_key": decision_key,
        "idempotency_request_hash": request_hash,
        "git_authorization": False,
        "deployment_authorization": False,
    }
    db_session.add(
        ReviewDecision(
            id=decision_id,
            review_package_id=stored.id,
            package_version=stored.package_version,
            expected_generation=stored.freshness_generation,
            package_digest=stored.package_digest,
            policy_digest=stored.suite_policy_digest,
            decision=decision_value,
            reason=reason,
            actor_type="local_user",
            request_id=str(uuid.uuid4()),
            idempotency_key=decision_key,
            idempotency_request_hash=request_hash,
            decision_digest=service._trusted_digest(decision_proof),
            git_authorization=False,
            deployment_authorization=False,
        )
    )
    with pytest.raises(DBAPIError):
        db_session.commit()
    db_session.rollback()

    assert (
        db_session.scalar(
            select(ReviewDecision).where(ReviewDecision.review_package_id == stored.id)
        )
        is None
    )
    assert db_session.scalar(select(ReleaseReadinessVerdict)) is None
    assert (
        db_session.scalar(
            select(AuditEvent).where(
                AuditEvent.review_package_id == stored.id,
                AuditEvent.event_type.in_(
                    ("review_decision_recorded", "release_readiness_evaluated")
                ),
            )
        )
        is None
    )


def test_concurrent_revision_change_and_approve_is_order_consistent(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
) -> None:
    context, completed = _successful_context(
        client,
        db_session,
        runner_bootstrap_token,
    )
    package = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package["id"]))
    original_generation = cast(int, package["freshness_generation"])
    barrier = threading.Barrier(2)
    db_session.close()

    def revise() -> str:
        engine = create_engine(database_url)
        try:
            with Session(engine) as session:
                runner = session.get(
                    Runner,
                    uuid.UUID(cast(str, context.runner["runner_id"])),
                )
                assert runner is not None
                barrier.wait()
                WorkspaceService(session).register_repository(
                    runner,
                    RepositoryRegistrationRequest.model_validate(
                        _registration_payload(context, CHANGED_REVISION)
                    ),
                    request_id=str(uuid.uuid4()),
                )
                return "revision_changed"
        finally:
            engine.dispose()

    def approve() -> str:
        engine = create_engine(database_url)
        try:
            with Session(engine) as session:
                barrier.wait()
                try:
                    response = ReviewService(session).decide(
                        package_id,
                        ReviewDecisionCreate(
                            decision="approve",
                            reason="Concurrent exact-generation approval.",
                            expected_generation=original_generation,
                        ),
                        request_id=str(uuid.uuid4()),
                        idempotency_key=f"concurrent-revision-{uuid.uuid4()}",
                    )
                except ReviewServiceError as exc:
                    return exc.code
                assert response.decision is not None
                return response.decision.decision
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        revision_future = executor.submit(revise)
        decision_future = executor.submit(approve)
        outcomes = {revision_future.result(), decision_future.result()}
    assert "revision_changed" in outcomes
    assert outcomes <= {
        "revision_changed",
        "approve",
        "review_generation_mismatch",
        "stale_review_package",
    }

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            stored = session.get(ReviewPackage, package_id)
            assert stored is not None
            scope = session.get(ReviewFreshnessState, stored.freshness_state_id)
            assert scope is not None
            assert scope.generation == original_generation + 1
            assert (
                session.scalar(
                    select(ReviewPackageInvalidation).where(
                        ReviewPackageInvalidation.review_package_id == package_id
                    )
                )
                is not None
            )
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
                <= 1
            )
            assert session.scalar(select(ReleaseReadinessVerdict)) is None
    finally:
        engine.dispose()


def test_nonblocking_new_generation_uses_a_new_package_and_decision(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    _context, completed = _successful_context(
        client,
        db_session,
        runner_bootstrap_token,
    )
    first = _create_package(client, cast(str, completed["id"]))
    first_decided = _approve(
        client,
        first,
        key=f"first-generation-{uuid.uuid4()}",
    )
    first_readiness = client.post(f"/api/v1/review-packages/{first['id']}/readiness")
    assert first_readiness.status_code == 200, first_readiness.text
    assert first_readiness.json()["readiness"]["effective_verdict"] == "ready"

    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, first["id"])))
    assert stored is not None
    finding_payload = {
        "plan_id": str(stored.plan_id),
        "workspace_id": str(stored.workspace_id),
        "checkpoint_id": str(stored.checkpoint_id),
        "finding_key": f"nonblocking-low-{uuid.uuid4()}",
        "finding_version": 1,
        "severity": "low",
        "blocking": False,
        "status": "open",
        "source": "governed-review-security-findings",
        "source_version": 1,
        "evidence_digest": stored.evidence_manifest_digest,
        "policy_digest": stored.suite_policy_digest,
    }
    db_session.add(
        ReviewBlockerFinding(
            plan_id=stored.plan_id,
            workspace_id=stored.workspace_id,
            checkpoint_id=stored.checkpoint_id,
            finding_key=cast(str, finding_payload["finding_key"]),
            finding_version=1,
            severity="low",
            blocking=False,
            status="open",
            source="governed-review-security-findings",
            source_version=1,
            evidence_digest=stored.evidence_manifest_digest,
            policy_digest=stored.suite_policy_digest,
            finding_digest=ReviewService(db_session)._trusted_digest(finding_payload),
        )
    )
    db_session.commit()

    second = _create_package(client, cast(str, completed["id"]))
    assert second["id"] != first["id"]
    assert second["freshness_generation"] == first["freshness_generation"] + 1
    assert second["decision"] is None
    assert second["readiness"] is None
    second_decided = _approve(
        client,
        second,
        key=f"second-generation-{uuid.uuid4()}",
    )
    assert second_decided["decision"]["id"] != first_decided["decision"]["id"]
    second_readiness = client.post(f"/api/v1/review-packages/{second['id']}/readiness")
    assert second_readiness.status_code == 200, second_readiness.text
    assert second_readiness.json()["readiness"]["effective_verdict"] == "ready"

    old_observed = client.get(f"/api/v1/review-packages/{first['id']}")
    assert old_observed.status_code == 200, old_observed.text
    assert old_observed.json()["freshness"] == "stale"
    assert old_observed.json()["readiness"]["effective_verdict"] == "stale"
