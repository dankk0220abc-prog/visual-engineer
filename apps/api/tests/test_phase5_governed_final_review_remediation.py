from __future__ import annotations

import uuid
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_governed_final_review import _create_package, _successful_suite
from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewBlockerFinding,
    ReviewDecision,
    ReviewPackage,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.validation import ValidationEvidence
from visual_engineer_api.models.workspace import ExecutionGrant
from visual_engineer_api.services.review import ReviewService


def _approve_and_ready(client: TestClient, package: dict[str, Any]) -> None:
    decision = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": f"remediation-decision-{uuid.uuid4()}"},
        json={
            "decision": "approve",
            "reason": "Exact generation and frozen zero-blocker summary reviewed.",
            "expected_generation": package["freshness_generation"],
        },
    )
    assert decision.status_code == 200, decision.text
    readiness = client.post(f"/api/v1/review-packages/{package['id']}/readiness")
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["readiness"]["effective_verdict"] == "ready"


def _insert_blocker(
    db_session: Session,
    package: ReviewPackage,
    *,
    severity: str,
    blocking: bool,
) -> None:
    payload = {
        "plan_id": str(package.plan_id),
        "workspace_id": str(package.workspace_id),
        "checkpoint_id": str(package.checkpoint_id),
        "finding_key": f"remediation-{severity}-{uuid.uuid4()}",
        "finding_version": 1,
        "severity": severity,
        "blocking": blocking,
        "status": "open",
        "source": "governed-review-security-findings",
        "source_version": 1,
        "evidence_digest": package.evidence_manifest_digest,
        "policy_digest": package.suite_policy_digest,
    }
    finding = ReviewBlockerFinding(
        id=uuid.uuid4(),
        plan_id=package.plan_id,
        workspace_id=package.workspace_id,
        checkpoint_id=package.checkpoint_id,
        finding_key=cast(str, payload["finding_key"]),
        finding_version=1,
        severity=severity,
        blocking=blocking,
        status="open",
        source="governed-review-security-findings",
        source_version=1,
        evidence_digest=package.evidence_manifest_digest,
        policy_digest=package.suite_policy_digest,
        finding_digest=ReviewService(db_session)._trusted_digest(payload),
    )
    db_session.add(finding)
    db_session.commit()


@pytest.mark.parametrize(
    ("severity", "blocking", "count_field"),
    (
        ("critical", True, "critical_count"),
        ("high", True, "high_count"),
        ("medium", True, "blocking_medium_count"),
    ),
)
def test_blocker_fact_stales_ready_and_new_generation_cannot_approve(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    severity: str,
    blocking: bool,
    count_field: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    _approve_and_ready(client, package)
    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None

    _insert_blocker(db_session, stored, severity=severity, blocking=blocking)

    observed = client.get(f"/api/v1/review-packages/{package['id']}")
    assert observed.status_code == 200, observed.text
    assert observed.json()["freshness"] == "stale"
    assert observed.json()["readiness"]["effective_verdict"] == "stale"
    assert observed.json()["invalidation"]["reason_code"] == "blocker_summary_changed"

    next_package = client.post(
        "/api/v1/review-packages",
        headers={"Idempotency-Key": f"remediation-next-package-{uuid.uuid4()}"},
        json={"suite_run_id": completed["id"]},
    )
    assert next_package.status_code == 201, next_package.text
    next_payload = cast(dict[str, Any], next_package.json())
    assert next_payload["freshness_generation"] > package["freshness_generation"]
    assert next_payload[count_field] == 1
    assert next_payload["decision"] is None
    assert next_payload["readiness"] is None

    denied = client.post(
        f"/api/v1/review-packages/{next_payload['id']}/decisions",
        headers={"Idempotency-Key": f"remediation-blocked-decision-{uuid.uuid4()}"},
        json={
            "decision": "approve",
            "reason": "Blocking findings must fail closed.",
            "expected_generation": next_payload["freshness_generation"],
        },
    )
    assert denied.status_code == 409, denied.text
    assert denied.json()["error"]["code"] == "review_blockers_present"
    assert (
        db_session.scalar(
            select(ReviewDecision).where(
                ReviewDecision.review_package_id == uuid.UUID(cast(str, next_payload["id"]))
            )
        )
        is None
    )
    assert (
        db_session.scalar(
            select(ReleaseReadinessVerdict).where(
                ReleaseReadinessVerdict.review_package_id
                == uuid.UUID(cast(str, next_payload["id"]))
            )
        )
        is None
    )
    assert all(
        grant.git_delivery_access is False for grant in db_session.scalars(select(ExecutionGrant))
    )

    old_events = list(
        db_session.scalars(
            select(AuditEvent)
            .where(AuditEvent.review_package_id == stored.id)
            .order_by(AuditEvent.review_sequence)
        )
    )
    assert [event.review_sequence for event in old_events] == [1, 2, 3, 4]
    next_events = list(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.review_package_id == uuid.UUID(cast(str, next_payload["id"]))
            )
        )
    )
    assert [event.review_sequence for event in next_events] == [1]


@pytest.mark.parametrize("summary_digest", (None, "f" * 64))
def test_database_rejects_missing_or_mismatched_blocker_summary_readiness(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    summary_digest: str | None,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    decision = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": f"remediation-ready-decision-{uuid.uuid4()}"},
        json={
            "decision": "approve",
            "reason": "Canonical blocker proof reviewed.",
            "expected_generation": package["freshness_generation"],
        },
    )
    assert decision.status_code == 200, decision.text
    decision_payload = cast(dict[str, Any], decision.json()["decision"])
    decision_count = len(list(db_session.scalars(select(ReviewDecision))))
    evidence_digests = list(
        db_session.scalars(
            select(ValidationEvidence.evidence_digest).order_by(ValidationEvidence.id)
        )
    )

    accepted = False
    try:
        db_session.execute(
            text(
                """
                INSERT INTO release_readiness_verdicts (
                    id, review_package_id, review_decision_id,
                    package_version, freshness_generation,
                    package_digest, decision_digest, evidence_manifest_digest,
                    suite_result_digest, policy_digest, blocker_summary_digest,
                    critical_count, high_count, blocking_medium_count,
                    verdict, reason_codes, verdict_digest,
                    git_authorization, deployment_authorization
                ) VALUES (
                    :id, :package_id, :decision_id,
                    :package_version, :generation,
                    :package_digest, :decision_digest, :manifest_digest,
                    :result_digest, :policy_digest, :summary_digest,
                    0, 0, 0, 'ready',
                    '["all_required_evidence_verified"]'::jsonb,
                    :forged_verdict_digest, false, false
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "package_id": package["id"],
                "decision_id": decision_payload["id"],
                "package_version": package["package_version"],
                "generation": package["freshness_generation"],
                "package_digest": package["package_digest"],
                "decision_digest": decision_payload["decision_digest"],
                "manifest_digest": package["evidence_manifest_digest"],
                "result_digest": package["suite_result_digest"],
                "policy_digest": package["suite_policy_digest"],
                "summary_digest": summary_digest,
                "forged_verdict_digest": "e" * 64,
            },
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        accepted = True

    assert accepted is False
    assert db_session.scalar(select(ReleaseReadinessVerdict)) is None
    assert len(list(db_session.scalars(select(ReviewDecision)))) == decision_count
    assert (
        list(
            db_session.scalars(
                select(ValidationEvidence.evidence_digest).order_by(ValidationEvidence.id)
            )
        )
        == evidence_digests
    )
    assert (
        db_session.scalar(
            select(AuditEvent).where(
                AuditEvent.review_package_id == uuid.UUID(cast(str, package["id"])),
                AuditEvent.event_type == "release_readiness_evaluated",
            )
        )
        is None
    )
    assert all(
        grant.git_delivery_access is False for grant in db_session.scalars(select(ExecutionGrant))
    )


def test_grant_lineage_change_stales_ready_in_the_same_database_transaction(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    _approve_and_ready(client, package)
    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None

    db_session.execute(
        text("UPDATE execution_grants SET status = 'expired' WHERE id = :id"),
        {"id": str(stored.execution_grant_id)},
    )
    db_session.commit()

    observed = client.get(f"/api/v1/review-packages/{package['id']}")
    assert observed.status_code == 200, observed.text
    payload = cast(dict[str, Any], observed.json())
    assert payload["freshness"] == "stale"
    assert payload["stale_reason_code"] == "grant_lineage_changed"
    assert payload["readiness"]["effective_verdict"] == "stale"
    assert payload["invalidation"]["reason_code"] == "grant_lineage_changed"

    invalidation_events = list(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.review_package_id == stored.id,
                AuditEvent.event_type == "review_package_invalidated",
            )
        )
    )
    assert len(invalidation_events) == 1


def test_evidence_policy_and_terminal_decision_are_database_immutable(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None
    decided = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": f"remediation-terminal-{uuid.uuid4()}"},
        json={
            "decision": "reject",
            "reason": "Immutable terminal rejection.",
            "expected_generation": package["freshness_generation"],
        },
    )
    assert decided.status_code == 200, decided.text
    evidence = db_session.scalar(select(ValidationEvidence))
    assert evidence is not None

    for statement, values in (
        (
            "UPDATE validation_evidence SET evidence_digest = :digest WHERE id = :id",
            {"digest": "0" * 64, "id": str(evidence.id)},
        ),
        (
            "UPDATE validation_suite_runs SET policy_digest = :digest WHERE id = :id",
            {"digest": "1" * 64, "id": str(stored.suite_run_id)},
        ),
        (
            "UPDATE review_decisions SET decision = 'approve' WHERE review_package_id = :id",
            {"id": package["id"]},
        ),
    ):
        accepted = False
        try:
            db_session.execute(text(statement), values)
            db_session.commit()
        except DBAPIError:
            db_session.rollback()
        else:
            accepted = True
        assert accepted is False

    replay = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={
            "Idempotency-Key": decided.json()["decision"]["idempotency_key"],
        },
        json={
            "decision": "reject",
            "reason": "Immutable terminal rejection.",
            "expected_generation": package["freshness_generation"],
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["decision"]["id"] == decided.json()["decision"]["id"]
    event_count = len(
        list(
            db_session.scalars(
                select(AuditEvent).where(
                    AuditEvent.review_package_id == uuid.UUID(cast(str, package["id"])),
                    AuditEvent.event_type == "review_decision_recorded",
                )
            )
        )
    )
    assert event_count == 1
