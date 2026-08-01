from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
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
    DeliveryDispatch,
    LocalDelivery,
)
from visual_engineer_api.models.runner import RunnerJob
from visual_engineer_api.models.workspace import RepositoryHandle, SideEffectPermit
from visual_engineer_api.schemas.delivery import DeliveryDispatchCreate
from visual_engineer_api.services.delivery import DeliveryService, DeliveryServiceError
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


def _preview_delivery(client: TestClient, authorization_id: str) -> dict[str, Any]:
    response = client.get(
        f"/api/v1/delivery-authorizations/{authorization_id}/preview",
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _dispatch_delivery(
    client: TestClient,
    authorization_id: str,
    *,
    retry_of_dispatch_id: str | None = None,
    key: str | None = None,
) -> dict[str, Any]:
    preview = _preview_delivery(client, authorization_id)
    response = client.post(
        f"/api/v1/delivery-authorizations/{authorization_id}/dispatch",
        headers={"Idempotency-Key": key or f"phase6-dispatch-{uuid.uuid4()}"},
        json={
            "confirmation_digest": preview["manifest"]["manifest_digest"],
            "retry_of_dispatch_id": retry_of_dispatch_id,
        },
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

    preview = _preview_delivery(client, cast(str, authorization["id"]))
    assert preview["manifest"]["changed_file_count"] > 0
    assert preview["manifest"]["total_diff_bytes"] == len(preview["diff_artifact"].encode("utf-8"))
    dispatched_payload = _dispatch_delivery(client, cast(str, authorization["id"]))
    assert dispatched_payload["status"] == "dispatched"
    job = cast(dict[str, Any], dispatched_payload["job"])
    dispatch = cast(list[dict[str, Any]], dispatched_payload["dispatches"])[-1]
    assert dispatch["attempt_number"] == 1
    assert dispatch["manifest_digest"] == preview["manifest"]["manifest_digest"]
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
    assert typed_assignment.job.delivery_dispatch_id == uuid.UUID(dispatch["id"])
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
        delivery_dispatch_id=uuid.UUID(dispatch["id"]),
        delivery_attempt_number=1,
        delivery_manifest_digest=dispatch["manifest_digest"],
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
    assert delivered["dispatches"][-1]["status"] == "succeeded"


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
        headers={"Idempotency-Key": f"phase6-denied-{uuid.uuid4()}"},
        json={"confirmation_digest": "0" * 64, "retry_of_dispatch_id": None},
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
    dispatched = _dispatch_delivery(client, cast(str, approved["id"]))
    job_id = cast(str, dispatched["job"]["id"])

    cancelled = client.post(f"/api/v1/runner-jobs/{job_id}/cancel")

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["state"] == "cancelled"
    observed = client.get(f"/api/v1/delivery-authorizations/{approved['id']}")
    assert observed.status_code == 200, observed.text
    assert observed.json()["status"] == "cancelled"
    assert observed.json()["delivery"] is None
    assert observed.json()["dispatches"][-1]["status"] == "cancelled"
    authorization_id = uuid.UUID(cast(str, approved["id"]))
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SideEffectPermit)
            .where(SideEffectPermit.delivery_authorization_id == authorization_id)
        )
        == 0
    )


def test_dispatch_requires_exact_manifest_confirmation_and_keyed_replay(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, _context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _create_authorization(client, cast(str, package["id"]))
    approved = _approve_authorization(client, cast(str, authorization["id"]))
    preview = _preview_delivery(client, cast(str, approved["id"]))
    authorization_id = uuid.UUID(cast(str, approved["id"]))

    denied = client.post(
        f"/api/v1/delivery-authorizations/{authorization_id}/dispatch",
        headers={"Idempotency-Key": f"phase6-wrong-confirmation-{uuid.uuid4()}"},
        json={"confirmation_digest": "f" * 64, "retry_of_dispatch_id": None},
    )
    assert denied.status_code == 409, denied.text
    assert denied.json()["error"]["code"] == "delivery_confirmation_mismatch"
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
            .select_from(DeliveryDispatch)
            .where(DeliveryDispatch.delivery_authorization_id == authorization_id)
        )
        == 0
    )

    key = f"phase6-dispatch-replay-{uuid.uuid4()}"
    payload = {
        "confirmation_digest": preview["manifest"]["manifest_digest"],
        "retry_of_dispatch_id": None,
    }
    first = client.post(
        f"/api/v1/delivery-authorizations/{authorization_id}/dispatch",
        headers={"Idempotency-Key": key},
        json=payload,
    )
    replay = client.post(
        f"/api/v1/delivery-authorizations/{authorization_id}/dispatch",
        headers={"Idempotency-Key": key},
        json=payload,
    )
    assert first.status_code == replay.status_code == 200
    assert first.json()["dispatches"] == replay.json()["dispatches"]
    assert first.json()["job"]["id"] == replay.json()["job"]["id"]
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DeliveryDispatch)
            .where(DeliveryDispatch.delivery_authorization_id == authorization_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(RunnerJob)
            .where(RunnerJob.delivery_authorization_id == authorization_id)
        )
        == 1
    )


def test_cancelled_dispatch_retries_with_linear_manifest_bound_history(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _approve_authorization(
        client,
        cast(str, _create_authorization(client, cast(str, package["id"]))["id"]),
    )
    heartbeat = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(context.token),
        json={
            "runner_id": context.runner["runner_id"],
            "protocol_version": 1,
            "software_version": "0.6.0-delivery-lifecycle",
            "capabilities": [
                *WORKSPACE_CAPABILITIES,
                "validation_execute_v1",
                "workspace_git_commit_v1",
            ],
        },
    )
    assert heartbeat.status_code == 200, heartbeat.text

    first = _dispatch_delivery(client, cast(str, authorization["id"]))
    first_dispatch = cast(list[dict[str, Any]], first["dispatches"])[-1]
    cancelled = client.post(f"/api/v1/runner-jobs/{first['job']['id']}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    retry_preview = _preview_delivery(client, cast(str, authorization["id"]))
    assert retry_preview["can_dispatch"] is True
    assert retry_preview["next_attempt_number"] == 2
    assert retry_preview["retry_of_dispatch_id"] == first_dispatch["id"]
    assert retry_preview["manifest"]["manifest_digest"] == first_dispatch["manifest_digest"]

    second = _dispatch_delivery(
        client,
        cast(str, authorization["id"]),
        retry_of_dispatch_id=cast(str, first_dispatch["id"]),
    )
    history = cast(list[dict[str, Any]], second["dispatches"])
    assert [item["status"] for item in history] == ["cancelled", "dispatched"]
    assert history[1]["attempt_number"] == 2
    assert history[1]["retry_of_dispatch_id"] == history[0]["id"]
    assert history[1]["manifest_digest"] == history[0]["manifest_digest"]

    job = cast(dict[str, Any], second["job"])
    assignment, identity = claim_start(client, context.runner, context.token, job["id"])
    permit = acquire_side_effect_permit(client, context.token, assignment, identity)
    result = WorkspaceGitCommitResult(
        workspace_id=uuid.UUID(cast(str, authorization["workspace_id"])),
        delivery_authorization_id=uuid.UUID(cast(str, authorization["id"])),
        delivery_dispatch_id=uuid.UUID(history[1]["id"]),
        delivery_attempt_number=2,
        delivery_manifest_digest=history[1]["manifest_digest"],
        checkpoint_id=uuid.UUID(cast(str, authorization["checkpoint_id"])),
        checkpoint_fingerprint=cast(str, authorization["checkpoint_fingerprint"]),
        checkpoint_diff_hash=cast(str, authorization["checkpoint_diff_hash"]),
        branch_ref=cast(str, authorization["branch_ref"]),
        commit_oid="d" * 40,
        tree_oid="e" * 40,
        parent_oid=cast(str, authorization["source_revision"]),
        result_digest="0" * 64,
        side_effect_permit_id=uuid.UUID(cast(str, permit["id"])),
    )
    result.result_digest = compute_local_delivery_result_digest(result)
    complete(client, context.token, job["id"], identity, result.model_dump(mode="json"))
    delivered = client.get(f"/api/v1/delivery-authorizations/{authorization['id']}").json()
    assert delivered["status"] == "succeeded"
    assert [item["status"] for item in delivered["dispatches"]] == [
        "cancelled",
        "succeeded",
    ]
    assert delivered["delivery"]["runner_job_id"] == history[1]["runner_job_id"]


def test_concurrent_dispatch_allows_one_durable_attempt(
    client: TestClient,
    db_session: Session,
    database_url: str,
    runner_bootstrap_token: str,
) -> None:
    package, _context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _approve_authorization(
        client,
        cast(str, _create_authorization(client, cast(str, package["id"]))["id"]),
    )
    preview = _preview_delivery(client, cast(str, authorization["id"]))
    authorization_id = uuid.UUID(cast(str, authorization["id"]))
    db_session.commit()
    barrier = threading.Barrier(2)
    engine = create_engine(database_url)

    def dispatch(index: int) -> tuple[str, str]:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            try:
                result = DeliveryService(session).dispatch(
                    authorization_id,
                    DeliveryDispatchCreate(
                        confirmation_digest=preview["manifest"]["manifest_digest"],
                    ),
                    idempotency_key=f"phase6-concurrent-dispatch-{index}-{uuid.uuid4()}",
                    request_id=f"phase6-concurrent-dispatch-{index}",
                )
                return "success", str(result.dispatches[-1].id)
            except DeliveryServiceError as exc:
                return "error", exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = [
            future.result(timeout=20)
            for future in (executor.submit(dispatch, 1), executor.submit(dispatch, 2))
        ]
    engine.dispose()

    assert sorted(item[0] for item in outcomes) == ["error", "success"]
    assert next(item[1] for item in outcomes if item[0] == "error") in {
        "delivery_authorization_not_approved",
        "delivery_dispatch_conflict",
    }
    db_session.expire_all()
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DeliveryDispatch)
            .where(DeliveryDispatch.delivery_authorization_id == authorization_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(RunnerJob)
            .where(RunnerJob.delivery_authorization_id == authorization_id)
        )
        == 1
    )


def test_revoked_implementation_grant_blocks_safe_retry_without_new_job(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, _context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _approve_authorization(
        client,
        cast(str, _create_authorization(client, cast(str, package["id"]))["id"]),
    )
    first = _dispatch_delivery(client, cast(str, authorization["id"]))
    first_dispatch = cast(list[dict[str, Any]], first["dispatches"])[-1]
    cancelled = client.post(f"/api/v1/runner-jobs/{first['job']['id']}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    revoked = client.post(f"/api/v1/execution-grants/{authorization['execution_grant_id']}/revoke")
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoked"
    preview = _preview_delivery(client, cast(str, authorization["id"]))
    assert preview["can_dispatch"] is False
    assert preview["blocking_code"] == "delivery_execution_authority_inactive"

    denied = client.post(
        f"/api/v1/delivery-authorizations/{authorization['id']}/dispatch",
        headers={"Idempotency-Key": f"phase6-revoked-retry-{uuid.uuid4()}"},
        json={
            "confirmation_digest": preview["manifest"]["manifest_digest"],
            "retry_of_dispatch_id": first_dispatch["id"],
        },
    )
    assert denied.status_code == 409, denied.text
    assert denied.json()["error"]["code"] == "delivery_execution_authority_inactive"
    authorization_id = uuid.UUID(cast(str, authorization["id"]))
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DeliveryDispatch)
            .where(DeliveryDispatch.delivery_authorization_id == authorization_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(RunnerJob)
            .where(RunnerJob.delivery_authorization_id == authorization_id)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(LocalDelivery)
            .where(LocalDelivery.delivery_authorization_id == authorization_id)
        )
        == 0
    )


def test_legacy_terminal_authorization_without_dispatch_is_not_retryable(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, _context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _approve_authorization(
        client,
        cast(str, _create_authorization(client, cast(str, package["id"]))["id"]),
    )
    authorization_id = uuid.UUID(cast(str, authorization["id"]))
    stored = db_session.get(DeliveryAuthorization, authorization_id)
    assert stored is not None
    stored.status = "dispatched"
    stored.dispatched_at = datetime.now(UTC)
    db_session.commit()
    stored.status = "failed"
    stored.error_code = "legacy_delivery_failed"
    stored.terminal_at = datetime.now(UTC)
    db_session.commit()

    preview = _preview_delivery(client, cast(str, authorization["id"]))
    assert preview["can_dispatch"] is False
    assert preview["next_attempt_number"] is None
    assert preview["retry_of_dispatch_id"] is None
    assert preview["blocking_code"] == "delivery_retry_lineage_invalid"


def test_cancelled_delivery_retry_budget_stops_after_three_linear_attempts(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    package, _context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _approve_authorization(
        client,
        cast(str, _create_authorization(client, cast(str, package["id"]))["id"]),
    )
    authorization_id = cast(str, authorization["id"])
    retry_of_dispatch_id: str | None = None

    for attempt_number in range(1, 4):
        preview = _preview_delivery(client, authorization_id)
        assert preview["can_dispatch"] is True
        assert preview["next_attempt_number"] == attempt_number
        assert preview["retry_of_dispatch_id"] == retry_of_dispatch_id
        dispatched = _dispatch_delivery(
            client,
            authorization_id,
            retry_of_dispatch_id=retry_of_dispatch_id,
        )
        latest = cast(list[dict[str, Any]], dispatched["dispatches"])[-1]
        assert latest["attempt_number"] == attempt_number
        cancelled = client.post(f"/api/v1/runner-jobs/{latest['runner_job_id']}/cancel")
        assert cancelled.status_code == 200, cancelled.text
        observed = client.get(f"/api/v1/delivery-authorizations/{authorization_id}").json()
        assert observed["status"] == "cancelled"
        assert observed["dispatches"][-1]["status"] == "cancelled"
        retry_of_dispatch_id = cast(str, latest["id"])

    blocked = _preview_delivery(client, authorization_id)
    assert blocked["can_dispatch"] is False
    assert blocked["next_attempt_number"] is None
    assert blocked["retry_of_dispatch_id"] is None
    assert blocked["blocking_code"] == "delivery_dispatch_budget_exhausted"
    denied = client.post(
        f"/api/v1/delivery-authorizations/{authorization_id}/dispatch",
        headers={"Idempotency-Key": f"phase6-budget-exhausted-{uuid.uuid4()}"},
        json={
            "confirmation_digest": blocked["manifest"]["manifest_digest"],
            "retry_of_dispatch_id": retry_of_dispatch_id,
        },
    )
    assert denied.status_code == 409, denied.text
    assert denied.json()["error"]["code"] == "delivery_dispatch_budget_exhausted"
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(DeliveryDispatch)
            .where(DeliveryDispatch.delivery_authorization_id == uuid.UUID(authorization_id))
        )
        == 3
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(RunnerJob)
            .where(RunnerJob.delivery_authorization_id == uuid.UUID(authorization_id))
        )
        == 3
    )
