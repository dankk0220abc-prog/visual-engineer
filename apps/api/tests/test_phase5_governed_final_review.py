from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_validation_suites import _complete_step, _prepare_suite
from visual_engineer_api.models.review import ReviewDecision, ReviewPackage
from visual_engineer_api.models.workspace import (
    RepositoryHandle,
    Workspace,
    WorkspaceCheckpoint,
)
from visual_engineer_api.schemas.review import ReviewDecisionCreate
from visual_engineer_api.services.review import ReviewService, ReviewServiceError


def _successful_suite(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> dict[str, Any]:
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
    return completed


def _create_package(client: TestClient, suite_run_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/review-packages",
        headers={"Idempotency-Key": f"review-package-{uuid.uuid4()}"},
        json={"suite_run_id": suite_run_id},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def test_review_package_decision_and_readiness_happy_path(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    key = f"review-package-{uuid.uuid4()}"
    created = client.post(
        "/api/v1/review-packages",
        headers={"Idempotency-Key": key},
        json={"suite_run_id": completed["id"]},
    )
    assert created.status_code == 201, created.text
    package = cast(dict[str, Any], created.json())
    assert package["freshness"] == "fresh"
    assert package["git_authorization"] is False
    assert package["deployment_authorization"] is False
    manifest = cast(dict[str, Any], package["evidence_manifest"])
    entries = cast(list[dict[str, Any]], manifest["entries"])
    assert [entry["sequence"] for entry in entries] == [1, 2]
    assert all(entry["side_effect_permit_id"] for entry in entries)
    assert all(entry["side_effect_permit_digest"] for entry in entries)
    assert all(entry["execution_envelope_digest"] for entry in entries)
    assert manifest["artifact_count"] == 0

    replay = client.post(
        "/api/v1/review-packages",
        headers={"Idempotency-Key": key},
        json={"suite_run_id": completed["id"]},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == package["id"]
    conflict = client.post(
        "/api/v1/review-packages",
        headers={"Idempotency-Key": key},
        json={"suite_run_id": str(uuid.uuid4())},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "review_package_idempotency_conflict"

    injection = client.post(
        "/api/v1/review-packages",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={"suite_run_id": completed["id"], "command": "git push"},
    )
    assert injection.status_code == 422

    decided = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={"decision": "approve", "reason": "Exact evidence reviewed."},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["decision"]["decision"] == "approve"
    assert decided.json()["decision"]["git_authorization"] is False

    readiness = client.post(
        f"/api/v1/review-packages/{package['id']}/readiness",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert readiness.status_code == 200, readiness.text
    verdict = readiness.json()["readiness"]
    assert verdict["verdict"] == "ready"
    assert verdict["effective_verdict"] == "ready"
    assert verdict["reason_codes"] == ["all_required_evidence_verified"]
    assert verdict["git_authorization"] is False
    assert verdict["deployment_authorization"] is False

    replay_decision = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        json={"decision": "approve", "reason": "Exact evidence reviewed."},
    )
    assert replay_decision.status_code == 200
    assert replay_decision.json()["decision"]["id"] == decided.json()["decision"]["id"]
    conflicting_decision = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        json={"decision": "reject", "reason": "Changed mind."},
    )
    assert conflicting_decision.status_code == 409
    assert conflicting_decision.json()["error"]["code"] == "review_decision_conflict"


def test_stale_revision_invalidates_and_fences_approval(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None
    handle = db_session.get(RepositoryHandle, stored.repository_handle_id)
    assert handle is not None
    handle.current_revision = "b" * 40
    db_session.commit()

    refreshed = client.post(
        f"/api/v1/review-packages/{package['id']}/freshness",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["freshness"] == "stale"
    assert refreshed.json()["stale_reason_code"] == "source_revision_changed"
    assert refreshed.json()["invalidation"]["reason_code"] == "source_revision_changed"

    denied = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        json={"decision": "approve", "reason": "Must not bypass stale fencing."},
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "stale_review_package"
    assert (
        db_session.scalar(
            select(ReviewDecision).where(
                ReviewDecision.review_package_id == uuid.UUID(cast(str, package["id"]))
            )
        )
        is None
    )


def test_ready_verdict_becomes_effectively_stale_after_revision_change(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    decided = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        json={"decision": "approve", "reason": "Fresh exact Evidence approved."},
    )
    assert decided.status_code == 200, decided.text
    readiness = client.post(f"/api/v1/review-packages/{package['id']}/readiness")
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["readiness"]["effective_verdict"] == "ready"

    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None
    handle = db_session.get(RepositoryHandle, stored.repository_handle_id)
    assert handle is not None
    handle.current_revision = "c" * 40
    db_session.commit()

    stale = client.get(f"/api/v1/review-packages/{package['id']}")
    assert stale.status_code == 200, stale.text
    assert stale.json()["freshness"] == "stale"
    assert stale.json()["readiness"]["verdict"] == "ready"
    assert stale.json()["readiness"]["effective_verdict"] == "stale"
    fenced = client.post(f"/api/v1/review-packages/{package['id']}/freshness")
    assert fenced.status_code == 200
    assert fenced.json()["invalidation"]["reason_code"] == "source_revision_changed"


def test_checkpoint_supersession_blocks_service_and_database_ready(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    decided = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        json={"decision": "approve", "reason": "Fresh exact Evidence approved."},
    )
    assert decided.status_code == 200, decided.text
    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None
    workspace = db_session.get(Workspace, stored.workspace_id)
    assert workspace is not None
    newer = WorkspaceCheckpoint(
        workspace_id=workspace.id,
        sequence=2,
        source_revision=stored.source_revision,
        tree_fingerprint=stored.checkpoint_fingerprint,
        diff_hash="9" * 64,
        changed_paths=["sandbox/original.txt"],
        changed_file_count=1,
        total_diff_bytes=0,
        diff_artifact="",
    )
    db_session.add(newer)
    db_session.commit()

    try:
        db_session.execute(
            text(
                """
                INSERT INTO release_readiness_verdicts (
                    id, review_package_id, review_decision_id,
                    package_digest, decision_digest,
                    evidence_manifest_digest, verdict, reason_codes,
                    verdict_digest, git_authorization,
                    deployment_authorization
                )
                SELECT
                    :verdict_id, package.id, decision.id,
                    package.package_digest, :decision_digest,
                    package.evidence_manifest_digest, 'ready',
                    '["all_required_evidence_verified"]'::jsonb,
                    :verdict_digest, false, false
                FROM review_packages AS package
                JOIN review_decisions AS decision
                    ON decision.review_package_id = package.id
                WHERE package.id = :package_id
                """
            ),
            {
                "verdict_id": str(uuid.uuid4()),
                "decision_digest": "7" * 64,
                "verdict_digest": "8" * 64,
                "package_id": package["id"],
            },
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        raise AssertionError("database accepted ready after Checkpoint supersession")

    readiness = client.post(f"/api/v1/review-packages/{package['id']}/readiness")
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["freshness"] == "stale"
    assert readiness.json()["stale_reason_code"] == "checkpoint_superseded"
    assert readiness.json()["readiness"]["verdict"] == "not_ready"
    assert readiness.json()["readiness"]["reason_codes"] == ["stale:checkpoint_superseded"]


def test_review_records_are_database_immutable_and_delivery_false(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    decided = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        json={"decision": "reject", "reason": "Evidence is complete but not accepted."},
    )
    assert decided.status_code == 200, decided.text
    readiness = client.post(f"/api/v1/review-packages/{package['id']}/readiness")
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["readiness"]["verdict"] == "not_ready"
    assert readiness.json()["readiness"]["reason_codes"] == ["review_rejected"]

    try:
        db_session.execute(
            text(
                """
                INSERT INTO review_packages (
                    id, schema_version, run_id, plan_id, repository_handle_id,
                    source_revision, workspace_id, checkpoint_id,
                    checkpoint_fingerprint, suite_run_id, suite_result_id,
                    suite_result_digest, evidence_manifest,
                    evidence_manifest_digest, package_digest, idempotency_key,
                    idempotency_request_hash, git_authorization,
                    deployment_authorization
                )
                SELECT
                    :new_id, schema_version, run_id, plan_id,
                    repository_handle_id, source_revision, workspace_id,
                    checkpoint_id, checkpoint_fingerprint, suite_run_id,
                    suite_result_id, suite_result_digest,
                    evidence_manifest #- '{entries,0,side_effect_permit_id}',
                    evidence_manifest_digest, package_digest, :new_key,
                    idempotency_request_hash, false, false
                FROM review_packages WHERE id = :package_id
                """
            ),
            {
                "new_id": str(uuid.uuid4()),
                "new_key": f"tampered-manifest-{uuid.uuid4()}",
                "package_id": package["id"],
            },
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        raise AssertionError("database accepted an incomplete Evidence Manifest")

    for statement in (
        "UPDATE review_packages SET git_authorization = true WHERE id = :id",
        "UPDATE review_decisions SET decision = 'approve' WHERE review_package_id = :id",
        "UPDATE release_readiness_verdicts SET verdict = 'ready' WHERE review_package_id = :id",
        "DELETE FROM review_packages WHERE id = :id",
    ):
        try:
            db_session.execute(text(statement), {"id": package["id"]})
            db_session.commit()
        except DBAPIError:
            db_session.rollback()
        else:
            raise AssertionError("immutable review record mutation unexpectedly succeeded")


def test_database_rejects_null_reason_and_null_workspace_freshness(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    decision_insert = text(
        """
        INSERT INTO review_decisions (
            id, review_package_id, package_digest, decision, reason,
            actor_type, request_id, git_authorization, deployment_authorization
        )
        SELECT
            :decision_id, id, package_digest, :decision, :reason,
            'local_user', :request_id, false, false
        FROM review_packages
        WHERE id = :package_id
        """
    )

    try:
        db_session.execute(
            decision_insert,
            {
                "decision_id": str(uuid.uuid4()),
                "decision": "reject",
                "reason": None,
                "request_id": str(uuid.uuid4()),
                "package_id": package["id"],
            },
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        raise AssertionError("database accepted a rejection without a reason")

    stored = db_session.get(ReviewPackage, uuid.UUID(cast(str, package["id"])))
    assert stored is not None
    workspace = db_session.get(Workspace, stored.workspace_id)
    assert workspace is not None
    workspace.current_tree_hash = None
    db_session.commit()

    try:
        db_session.execute(
            decision_insert,
            {
                "decision_id": str(uuid.uuid4()),
                "decision": "approve",
                "reason": "Must not bypass NULL stale fencing.",
                "request_id": str(uuid.uuid4()),
                "package_id": package["id"],
            },
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        raise AssertionError("database accepted approval with NULL workspace freshness")


def test_concurrent_review_decision_has_one_winner(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
) -> None:
    completed = _successful_suite(client, db_session, runner_bootstrap_token)
    package = _create_package(client, cast(str, completed["id"]))
    package_id = uuid.UUID(cast(str, package["id"]))
    db_session.close()

    def decide(decision: str) -> str:
        engine = create_engine(database_url)
        try:
            with Session(engine) as session:
                try:
                    result = ReviewService(session).decide(
                        package_id,
                        ReviewDecisionCreate(
                            decision=cast(Any, decision),
                            reason=(
                                "Concurrent rejection."
                                if decision == "reject"
                                else "Concurrent approval."
                            ),
                        ),
                        request_id=str(uuid.uuid4()),
                    )
                except ReviewServiceError as exc:
                    return exc.code
                return result.decision.decision if result.decision else "missing"
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(decide, ["approve", "reject"]))
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
            assert decisions[0].git_authorization is False
            assert decisions[0].deployment_authorization is False
    finally:
        engine.dispose()
