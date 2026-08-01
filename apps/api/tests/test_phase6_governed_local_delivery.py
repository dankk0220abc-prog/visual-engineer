from __future__ import annotations

import uuid
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_governed_final_review import _create_package
from test_phase5_validation_suites import (
    SuiteContext,
    _complete_step,
    _prepare_suite,
)
from test_workspace_api import (
    WORKSPACE_CAPABILITIES,
    acquire_side_effect_permit,
    claim_start,
    complete,
    runner_headers,
)
from visual_engineer_api.models.delivery import (
    DeliveryAuthorization,
    LocalDelivery,
)
from visual_engineer_api.models.runner import RunnerJob
from visual_engineer_api.models.workspace import RepositoryHandle, SideEffectPermit
from visual_engineer_runner_protocol import (
    JobAssignment,
    WorkspaceGitCommitJobSpec,
    WorkspaceGitCommitResult,
    compute_local_delivery_result_digest,
)


def _ready_package(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> tuple[dict[str, Any], SuiteContext]:
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
    package = _create_package(client, cast(str, completed["id"]))
    decided = client.post(
        f"/api/v1/review-packages/{package['id']}/decisions",
        headers={"Idempotency-Key": f"phase6-review-decision-{uuid.uuid4()}"},
        json={
            "decision": "approve",
            "reason": "Exact fresh fixture Evidence approved for readiness.",
            "expected_generation": package["freshness_generation"],
        },
    )
    assert decided.status_code == 200, decided.text
    readiness = client.post(f"/api/v1/review-packages/{package['id']}/readiness")
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["readiness"]["effective_verdict"] == "ready"
    return cast(dict[str, Any], readiness.json()), context


def _create_authorization(
    client: TestClient,
    package_id: str,
    *,
    key: str | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/delivery-authorizations",
        headers={"Idempotency-Key": key or f"phase6-delivery-{uuid.uuid4()}"},
        json={"review_package_id": package_id},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def _approve_authorization(
    client: TestClient,
    authorization_id: str,
) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/delivery-authorizations/{authorization_id}/decisions",
        headers={"Idempotency-Key": f"phase6-delivery-approve-{uuid.uuid4()}"},
        json={"decision": "approve", "reason": None},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_local_delivery_requires_separate_authority_and_persists_exact_result(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _create_authorization(client, cast(str, package["id"]))
    assert authorization["status"] == "pending"
    assert authorization["job"] is None
    assert authorization["delivery"] is None
    assert authorization["branch_ref"] == (
        f"refs/heads/visual-engineer/{uuid.UUID(authorization['workspace_id']).hex}"
    )
    assert authorization["commit_message"] == (
        f"VisualEngineer: governed local delivery {uuid.UUID(authorization['id']).hex[:8]}"
    )
    for field in (
        "remote_access",
        "push_access",
        "pull_request_access",
        "tag_access",
        "deployment_access",
        "source_repository_write_access",
    ):
        assert authorization[field] is False

    approved = _approve_authorization(client, cast(str, authorization["id"]))
    assert approved["status"] == "approved"
    assert approved["decision"]["local_git_commit_authorized"] is True
    assert approved["job"] is None

    heartbeat = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(context.token),
        json={
            "runner_id": context.runner["runner_id"],
            "protocol_version": 1,
            "software_version": "0.6.0-delivery",
            "capabilities": [
                *WORKSPACE_CAPABILITIES,
                "validation_execute_v1",
                "workspace_git_commit_v1",
            ],
        },
    )
    assert heartbeat.status_code == 200, heartbeat.text

    dispatched = client.post(
        f"/api/v1/delivery-authorizations/{authorization['id']}/dispatch",
    )
    assert dispatched.status_code == 200, dispatched.text
    dispatched_payload = cast(dict[str, Any], dispatched.json())
    assert dispatched_payload["status"] == "dispatched"
    job = cast(dict[str, Any], dispatched_payload["job"])
    assert job["kind"] == "workspace_git_commit_v1"
    assert job["delivery_authorization_id"] == authorization["id"]
    assert job["permission_envelope"]["authorization_source"] == (
        "execution_grant_and_delivery_authorization"
    )
    assert job["permission_envelope"]["repository_access"] == "isolated_workspace"
    assert job["permission_envelope"]["network_policy"] == "control_plane_only"
    assert job["permission_envelope"]["shell_access"] is False

    assignment, identity = claim_start(
        client,
        context.runner,
        context.token,
        job["id"],
    )
    typed_assignment = JobAssignment.model_validate(assignment)
    assert isinstance(typed_assignment.job, WorkspaceGitCommitJobSpec)
    assert typed_assignment.job.delivery_authorization.id == uuid.UUID(
        cast(str, authorization["id"])
    )
    assert typed_assignment.permission_envelope.authorization_source == (
        "execution_grant_and_delivery_authorization"
    )
    permit = acquire_side_effect_permit(
        client,
        context.token,
        assignment,
        identity,
    )
    assert permit["operation"] == "git_commit"
    assert permit["delivery_authorization_id"] == authorization["id"]
    result = WorkspaceGitCommitResult(
        workspace_id=uuid.UUID(cast(str, authorization["workspace_id"])),
        delivery_authorization_id=uuid.UUID(cast(str, authorization["id"])),
        checkpoint_id=uuid.UUID(cast(str, authorization["checkpoint_id"])),
        checkpoint_fingerprint=cast(str, authorization["checkpoint_fingerprint"]),
        checkpoint_diff_hash=cast(str, authorization["checkpoint_diff_hash"]),
        branch_ref=cast(str, authorization["branch_ref"]),
        commit_oid="b" * 40,
        tree_oid="c" * 40,
        parent_oid=cast(str, authorization["source_revision"]),
        result_digest="0" * 64,
        side_effect_permit_id=uuid.UUID(cast(str, permit["id"])),
    )
    result.result_digest = compute_local_delivery_result_digest(result)
    complete(
        client,
        context.token,
        job["id"],
        identity,
        result.model_dump(mode="json"),
    )
    observed = client.get(f"/api/v1/delivery-authorizations/{authorization['id']}")
    assert observed.status_code == 200, observed.text
    delivered = cast(dict[str, Any], observed.json())
    assert delivered["status"] == "succeeded"
    assert delivered["delivery"]["commit_oid"] == "b" * 40
    assert delivered["delivery"]["side_effect_permit_id"] == permit["id"]
    assert delivered["delivery"]["remote_access"] is False
    assert delivered["delivery"]["pushed"] is False
    assert delivered["delivery"]["pull_request_created"] is False
    assert delivered["delivery"]["tagged"] is False
    assert delivered["delivery"]["deployed"] is False


def test_rejection_staleness_and_database_guards_leave_zero_delivery_side_effects(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, _context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _create_authorization(client, cast(str, package["id"]))
    authorization_id = uuid.UUID(cast(str, authorization["id"]))

    rejected = client.post(
        f"/api/v1/delivery-authorizations/{authorization_id}/decisions",
        headers={"Idempotency-Key": f"phase6-delivery-reject-{uuid.uuid4()}"},
        json={"decision": "reject", "reason": "Do not create a local commit."},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["terminal_at"] is not None
    denied = client.post(
        f"/api/v1/delivery-authorizations/{authorization_id}/dispatch",
    )
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "delivery_authorization_not_approved"
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(RunnerJob)
            .where(RunnerJob.delivery_authorization_id == authorization_id)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SideEffectPermit)
            .where(SideEffectPermit.delivery_authorization_id == authorization_id)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(LocalDelivery)
            .where(LocalDelivery.delivery_authorization_id == authorization_id)
        )
        == 0
    )

    try:
        db_session.execute(
            text(
                "UPDATE delivery_authorizations SET remote_access = true "
                "WHERE id = :authorization_id"
            ),
            {"authorization_id": str(authorization_id)},
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
    else:
        raise AssertionError("database accepted remote authority escalation")

    second_package, _second_context = _ready_package(
        client,
        db_session,
        runner_bootstrap_token,
    )
    pending = _create_authorization(client, cast(str, second_package["id"]))
    pending_id = uuid.UUID(cast(str, pending["id"]))
    stored = db_session.get(DeliveryAuthorization, pending_id)
    assert stored is not None
    handle = db_session.get(RepositoryHandle, stored.repository_handle_id)
    assert handle is not None
    handle.current_revision = "f" * 40
    db_session.commit()

    stale = client.post(
        f"/api/v1/delivery-authorizations/{pending_id}/decisions",
        headers={"Idempotency-Key": f"phase6-stale-approve-{uuid.uuid4()}"},
        json={"decision": "approve", "reason": None},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_review_package"
    observed = client.get(f"/api/v1/delivery-authorizations/{pending_id}")
    assert observed.status_code == 200
    assert observed.json()["status"] == "stale"
    assert observed.json()["job"] is None
    assert observed.json()["delivery"] is None


def test_delivery_request_schema_rejects_authority_injection(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, _context = _ready_package(client, db_session, runner_bootstrap_token)
    injected = client.post(
        "/api/v1/delivery-authorizations",
        headers={"Idempotency-Key": f"phase6-injection-{uuid.uuid4()}"},
        json={
            "review_package_id": package["id"],
            "branch_ref": "refs/heads/attacker",
            "command": "git push",
            "remote_access": True,
        },
    )
    assert injected.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(DeliveryAuthorization)) == 0


def test_queued_local_delivery_cancellation_terminalizes_without_permit_or_result(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _create_authorization(client, cast(str, package["id"]))
    approved = _approve_authorization(client, cast(str, authorization["id"]))
    heartbeat = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(context.token),
        json={
            "runner_id": context.runner["runner_id"],
            "protocol_version": 1,
            "software_version": "0.6.0-delivery",
            "capabilities": [
                *WORKSPACE_CAPABILITIES,
                "validation_execute_v1",
                "workspace_git_commit_v1",
            ],
        },
    )
    assert heartbeat.status_code == 200, heartbeat.text
    dispatched = client.post(
        f"/api/v1/delivery-authorizations/{approved['id']}/dispatch",
    )
    assert dispatched.status_code == 200, dispatched.text
    job_id = cast(str, dispatched.json()["job"]["id"])

    cancelled = client.post(f"/api/v1/runner-jobs/{job_id}/cancel")

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["state"] == "cancelled"
    observed = client.get(f"/api/v1/delivery-authorizations/{approved['id']}")
    assert observed.status_code == 200, observed.text
    assert observed.json()["status"] == "cancelled"
    assert observed.json()["delivery"] is None
    authorization_id = uuid.UUID(cast(str, approved["id"]))
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SideEffectPermit)
            .where(SideEffectPermit.delivery_authorization_id == authorization_id)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(LocalDelivery)
            .where(LocalDelivery.delivery_authorization_id == authorization_id)
        )
        == 0
    )
