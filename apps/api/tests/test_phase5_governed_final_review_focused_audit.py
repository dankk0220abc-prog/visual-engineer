from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_validation_suites import SuiteContext, _complete_step, _prepare_suite
from test_workspace_api import (
    acquire_side_effect_permit,
    claim_start,
    governed_validation_result,
    runner_headers,
)
from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewDecision,
    ReviewPackage,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.workspace import RepositoryHandle, Workspace
from visual_engineer_api.schemas.review import ReviewDecisionCreate
from visual_engineer_api.services.review import ReviewService, ReviewServiceError
from visual_engineer_api.services.validation_suite import ValidationSuiteService


def _successful_suite(
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
    assert completed["result"]["verdict"] == "succeeded"
    return context, completed


def _create_package(client: TestClient, suite_run_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/review-packages",
        headers={"Idempotency-Key": f"focused-audit-package-{uuid.uuid4()}"},
        json={"suite_run_id": suite_run_id},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def _approve_and_ready(client: TestClient, package_id: str) -> dict[str, Any]:
    decision = client.post(
        f"/api/v1/review-packages/{package_id}/decisions",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={
            "decision": "approve",
            "reason": "Independent exact-Evidence review.",
        },
    )
    assert decision.status_code == 200, decision.text
    readiness = client.post(
        f"/api/v1/review-packages/{package_id}/readiness",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert readiness.status_code == 200, readiness.text
    payload = cast(dict[str, Any], readiness.json())
    assert payload["readiness"]["effective_verdict"] == "ready"
    return payload


def test_p5_review_aud_001_later_failed_validation_revokes_existing_ready(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context, completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    _approve_and_ready(client, cast(str, package["id"]))

    pending_grant = client.post(
        "/api/v1/execution-grants",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={
            "plan_id": context.plan_id,
            "repository_handle_id": context.repository["repository_handle_id"],
            "validation_checkpoint_id": context.checkpoint_id,
            "validation_profile_id": "fixture-python-stdlib-v1",
        },
    )
    assert pending_grant.status_code == 201, pending_grant.text
    later_grant = cast(dict[str, Any], pending_grant.json())
    approved = client.post(
        f"/api/v1/execution-grants/{later_grant['id']}/decisions",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={
            "decision": "approve",
            "reason": "Fresh authority for an exact validation rerun.",
        },
    )
    assert approved.status_code == 200, approved.text
    created_rerun_response = client.post(
        "/api/v1/validation-runs",
        headers={"Idempotency-Key": f"focused-audit-validation-rerun-{uuid.uuid4()}"},
        json={
            "execution_grant_id": later_grant["id"],
            "profile_id": "fixture-python-stdlib-v1",
        },
    )
    assert created_rerun_response.status_code == 201, created_rerun_response.text
    created_rerun = cast(dict[str, Any], created_rerun_response.json())
    assignment, identity = claim_start(
        client,
        context.runner,
        context.token,
        cast(str, created_rerun["runner_job_id"]),
    )
    permit = acquire_side_effect_permit(
        client,
        context.token,
        assignment,
        identity,
    )
    failed_completion = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{created_rerun['runner_job_id']}/complete",
        headers=runner_headers(context.token),
        json={
            **identity,
            "result": governed_validation_result(
                assignment,
                permit,
                {
                    "kind": "validation_execute_v1",
                    "validation_run_id": created_rerun["id"],
                    "workspace_id": context.workspace_id,
                    "checkpoint_id": context.checkpoint_id,
                    "checkpoint_fingerprint": context.checkpoint_fingerprint,
                    "profile_id": "fixture-python-stdlib-v1",
                    "profile_version": 1,
                    "fixed_argv": [
                        "python",
                        "-I",
                        "-S",
                        "<system-owned-fixture-validator>",
                    ],
                    "started_at": "2026-07-30T02:00:00Z",
                    "completed_at": "2026-07-30T02:00:01Z",
                    "duration_ms": 50,
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": "VE_VALIDATION_PROFILE_FAILED\n",
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
            ),
        },
    )
    assert failed_completion.status_code == 200, failed_completion.text
    assert failed_completion.json()["state"] == "failed"
    failed_rerun_response = client.get(f"/api/v1/validation-runs/{created_rerun['id']}")
    assert failed_rerun_response.status_code == 200, failed_rerun_response.text
    assert failed_rerun_response.json()["state"] == "failed"

    observed = client.get(f"/api/v1/review-packages/{package['id']}")
    assert observed.status_code == 200, observed.text
    observed_payload = cast(dict[str, Any], observed.json())
    assert observed_payload["freshness"] == "stale"
    assert observed_payload["readiness"]["effective_verdict"] == "stale"


def test_p5_review_aud_002_database_rejects_forged_digest_ready_chain(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    _context, completed = _successful_suite(client, db_session, runner_bootstrap_token)
    suite_run, suite_result, entries = ValidationSuiteService(db_session).trusted_success_manifest(
        uuid.UUID(cast(str, completed["id"]))
    )
    workspace = db_session.get(Workspace, suite_run.workspace_id)
    assert workspace is not None
    handle = db_session.get(RepositoryHandle, workspace.repository_handle_id)
    assert handle is not None

    forged_package_id = uuid.uuid4()
    forged_package_digest = "a" * 64
    forged_manifest_digest = "b" * 64
    forged_package = ReviewPackage(
        id=forged_package_id,
        schema_version=1,
        run_id=suite_run.run_id,
        plan_id=suite_run.plan_id,
        repository_handle_id=handle.id,
        source_revision=suite_run.source_revision,
        workspace_id=suite_run.workspace_id,
        checkpoint_id=suite_run.checkpoint_id,
        checkpoint_fingerprint=suite_run.checkpoint_fingerprint,
        suite_run_id=suite_run.id,
        suite_result_id=suite_result.id,
        suite_result_digest=suite_result.aggregate_digest,
        evidence_manifest=ReviewService._manifest(suite_run, suite_result, entries),
        evidence_manifest_digest=forged_manifest_digest,
        package_digest=forged_package_digest,
        idempotency_key=f"focused-audit-forged-package-{uuid.uuid4()}",
        idempotency_request_hash="c" * 64,
        git_authorization=False,
        deployment_authorization=False,
    )
    db_session.add(forged_package)
    package_accepted = False
    try:
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        package_accepted = True

    decision_accepted = False
    readiness_accepted = False
    if package_accepted:
        forged_decision = ReviewDecision(
            review_package_id=forged_package_id,
            package_digest=forged_package_digest,
            decision="approve",
            reason="Forged database-only approval.",
            actor_type="local_user",
            request_id=str(uuid.uuid4()),
            git_authorization=False,
            deployment_authorization=False,
        )
        db_session.add(forged_decision)
        try:
            db_session.commit()
        except DBAPIError:
            db_session.rollback()
        else:
            decision_accepted = True
            db_session.refresh(forged_decision)

        if decision_accepted:
            db_session.add(
                ReleaseReadinessVerdict(
                    review_package_id=forged_package_id,
                    review_decision_id=forged_decision.id,
                    package_digest=forged_package_digest,
                    decision_digest="d" * 64,
                    evidence_manifest_digest=forged_manifest_digest,
                    verdict="ready",
                    reason_codes=["all_required_evidence_verified"],
                    verdict_digest="e" * 64,
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

    assert (package_accepted, decision_accepted, readiness_accepted) == (
        False,
        False,
        False,
    )


def test_p5_review_aud_003_review_audit_events_reject_update_and_delete(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    _context, completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    _approve_and_ready(client, cast(str, package["id"]))
    events = list(
        db_session.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.event_type.in_(
                    (
                        "review_package_created",
                        "review_decision_recorded",
                        "release_readiness_evaluated",
                    )
                )
            )
            .order_by(AuditEvent.created_at, AuditEvent.id)
        )
    )
    assert len(events) == 3

    update_accepted = False
    try:
        db_session.execute(
            text(
                """
                UPDATE audit_events
                SET event_type = 'review_package_invalidated',
                    metadata = '{"reason_code":"forged"}'::jsonb
                WHERE id = :event_id
                """
            ),
            {"event_id": str(events[0].id)},
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        update_accepted = True

    delete_accepted = False
    try:
        db_session.execute(
            text("DELETE FROM audit_events WHERE id = :event_id"),
            {"event_id": str(events[1].id)},
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        delete_accepted = True

    assert (update_accepted, delete_accepted) == (False, False)


def test_p5_review_aud_004_concurrent_approve_reject_has_one_winner_and_one_event(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
) -> None:
    _context, completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package["id"]))
    db_session.close()

    reasons = {
        "approve": "Independent concurrent approval.",
        "reject": "Independent concurrent rejection.",
    }

    def decide(decision: str) -> str:
        engine = create_engine(database_url)
        try:
            with Session(engine) as session:
                try:
                    response = ReviewService(session).decide(
                        package_id,
                        ReviewDecisionCreate(
                            decision=cast(Any, decision),
                            reason=reasons[decision],
                        ),
                        request_id=str(uuid.uuid4()),
                    )
                except ReviewServiceError as exc:
                    return exc.code
                assert response.decision is not None
                return response.decision.decision
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(decide, ("approve", "reject")))
    assert outcomes in (
        ["approve", "review_decision_conflict"],
        ["reject", "review_decision_conflict"],
    )

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            decisions = list(
                session.scalars(
                    select(ReviewDecision).where(ReviewDecision.review_package_id == package_id)
                )
            )
            assert len(decisions) == 1
            winner = decisions[0]
            replay = ReviewService(session).decide(
                package_id,
                ReviewDecisionCreate(
                    decision=cast(Any, winner.decision),
                    reason=winner.reason,
                ),
                request_id=str(uuid.uuid4()),
            )
            assert replay.decision is not None
            assert replay.decision.id == winner.id
            event_count = len(
                list(
                    session.scalars(
                        select(AuditEvent).where(
                            AuditEvent.run_id == replay.run_id,
                            AuditEvent.event_type == "review_decision_recorded",
                        )
                    )
                )
            )
            assert event_count == 1
    finally:
        engine.dispose()


def test_p5_review_aud_005_review_api_rejects_git_pr_delivery_injection(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    _context, completed = _successful_suite(client, db_session, runner_bootstrap_token)
    injected_package = client.post(
        "/api/v1/review-packages",
        headers={"Idempotency-Key": f"focused-audit-injection-{uuid.uuid4()}"},
        json={
            "suite_run_id": completed["id"],
            "git_authorization": True,
            "deployment_authorization": True,
            "branch": "main",
            "commit": True,
            "push": True,
            "pull_request": True,
            "tag": "release",
        },
    )
    assert injected_package.status_code == 422, injected_package.text
    assert db_session.scalar(select(ReviewPackage)) is None

    package = _create_package(client, cast(str, completed["id"]))
    injected_decision = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        json={
            "decision": "approve",
            "reason": "Attempted authority expansion.",
            "git_authorization": True,
            "deployment_authorization": True,
            "branch": "main",
            "push": True,
            "pull_request": True,
        },
    )
    assert injected_decision.status_code == 422, injected_decision.text
    assert db_session.scalar(select(ReviewDecision)) is None
    assert db_session.scalar(select(ReleaseReadinessVerdict)) is None


def test_p5_review_aud_006_decision_requires_generation_and_keyed_idempotency(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    _context, completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    generation = package.get("freshness_generation")
    assert isinstance(generation, int) and generation >= 1

    mismatched = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": f"focused-audit-decision-stale-{uuid.uuid4()}"},
        json={
            "decision": "approve",
            "reason": "Stale generation must not decide.",
            "expected_generation": generation + 1,
        },
    )
    assert mismatched.status_code == 409, mismatched.text
    assert db_session.scalar(select(ReviewDecision)) is None

    decision_key = f"focused-audit-decision-{uuid.uuid4()}"
    decision_payload = {
        "decision": "approve",
        "reason": "Exact generation and exact idempotency payload.",
        "expected_generation": generation,
    }
    decided = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": decision_key},
        json=decision_payload,
    )
    assert decided.status_code == 200, decided.text
    replay = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": decision_key},
        json=decision_payload,
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["decision"]["id"] == decided.json()["decision"]["id"]

    conflict = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": decision_key},
        json={
            **decision_payload,
            "reason": "Same key with a different payload must conflict.",
        },
    )
    assert conflict.status_code == 409, conflict.text
