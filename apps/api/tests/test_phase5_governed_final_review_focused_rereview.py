from __future__ import annotations

import uuid
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_governed_final_review import _create_package, _successful_suite
from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewDecision,
    ReviewFreshnessState,
    ReviewPackage,
    ReviewPackageInvalidation,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.validation import ValidationEvidence
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    RepositoryHandle,
    Workspace,
)
from visual_engineer_api.services.review import ReviewService


def test_p5_review_rereview_001_repository_revision_change_rejects_database_ready_chain(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package_payload = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package_payload["id"]))
    package = db_session.get(ReviewPackage, package_id)
    assert package is not None
    scope = db_session.get(ReviewFreshnessState, package.freshness_state_id)
    handle = db_session.get(RepositoryHandle, package.repository_handle_id)
    workspace = db_session.get(Workspace, package.workspace_id)
    assert scope is not None
    assert handle is not None
    assert workspace is not None

    original_generation = scope.generation
    original_workspace_state = (
        workspace.source_revision,
        workspace.current_tree_hash,
    )
    original_evidence = list(
        db_session.scalars(
            select(ValidationEvidence.evidence_digest).order_by(ValidationEvidence.id)
        )
    )

    handle.current_revision = "d" * 40
    db_session.commit()
    db_session.refresh(scope)
    assert scope.generation == original_generation
    assert (
        db_session.scalar(
            select(ReviewPackageInvalidation).where(
                ReviewPackageInvalidation.review_package_id == package_id
            )
        )
        is None
    )

    observed = client.get(f"/api/v1/review-packages/{package_id}")
    assert observed.status_code == 200, observed.text
    observed_payload = cast(dict[str, Any], observed.json())
    assert observed_payload["freshness"] == "stale"
    assert observed_payload["stale_reason_code"] == "source_revision_changed"
    assert observed_payload["current_freshness_generation"] == original_generation
    assert observed_payload["invalidation"] is None

    service = ReviewService(db_session)
    reason = "Independent stale-revision database denial."
    decision_id = uuid.uuid4()
    decision_key = f"focused-rereview-stale-revision-{uuid.uuid4()}"
    decision_request = {
        "review_package_id": str(package.id),
        "package_version": package.package_version,
        "expected_generation": package.freshness_generation,
        "package_digest": package.package_digest,
        "policy_digest": package.suite_policy_digest,
        "decision": "approve",
        "reason": reason,
        "actor_type": "local_user",
    }
    request_hash = service._trusted_digest(decision_request)
    decision_proof = {
        "review_decision_id": str(decision_id),
        **decision_request,
        "idempotency_key": decision_key,
        "idempotency_request_hash": request_hash,
        "git_authorization": False,
        "deployment_authorization": False,
    }
    decision = ReviewDecision(
        id=decision_id,
        review_package_id=package.id,
        package_version=package.package_version,
        expected_generation=package.freshness_generation,
        package_digest=package.package_digest,
        policy_digest=package.suite_policy_digest,
        decision="approve",
        reason=reason,
        actor_type="local_user",
        request_id=str(uuid.uuid4()),
        idempotency_key=decision_key,
        idempotency_request_hash=request_hash,
        decision_digest=service._trusted_digest(decision_proof),
        git_authorization=False,
        deployment_authorization=False,
    )
    db_session.add(decision)
    decision_accepted = False
    try:
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        decision_accepted = True

    readiness_accepted = False
    if decision_accepted:
        verdict_proof = {
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
        db_session.add(
            ReleaseReadinessVerdict(
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
                verdict_digest=service._trusted_digest(verdict_proof),
                git_authorization=False,
                deployment_authorization=False,
            )
        )
        try:
            db_session.commit()
        except DBAPIError:
            db_session.rollback()
        else:
            readiness_accepted = True

    approved_decisions = list(
        db_session.scalars(
            select(ReviewDecision).where(
                ReviewDecision.review_package_id == package_id,
                ReviewDecision.decision == "approve",
            )
        )
    )
    ready_rows = list(
        db_session.scalars(
            select(ReleaseReadinessVerdict).where(
                ReleaseReadinessVerdict.review_package_id == package_id,
                ReleaseReadinessVerdict.verdict == "ready",
            )
        )
    )
    readiness_events = list(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.review_package_id == package_id,
                AuditEvent.event_type == "release_readiness_evaluated",
            )
        )
    )
    assert (workspace.source_revision, workspace.current_tree_hash) == original_workspace_state
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
    assert (
        decision_accepted,
        readiness_accepted,
        len(approved_decisions),
        len(ready_rows),
        len(readiness_events),
    ) == (False, False, 0, 0, 0)
