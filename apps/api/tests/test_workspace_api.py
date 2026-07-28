import hashlib
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from visual_engineer_api.models.run import (
    ApprovalDecision,
    Plan,
    RepositorySnapshot,
    Run,
)
from visual_engineer_api.models.runner import RunnerJob
from visual_engineer_api.models.task import Task
from visual_engineer_api.models.workspace import ExecutionGrant, SideEffectPermit
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError
from visual_engineer_api.services.workspace import WorkspaceService
from visual_engineer_runner_protocol import (
    JobAssignment,
    SideEffectPermitAcquireRequest,
    compute_side_effect_job_digest,
)

WORKSPACE_CAPABILITIES = [
    "controlled_wait_v1",
    "system_diagnostic_v1",
    "workspace_diff_v1",
    "workspace_discard_v1",
    "workspace_list_v1",
    "workspace_prepare_v1",
    "workspace_read_text_v1",
    "workspace_rollback_v1",
    "workspace_status_v1",
    "workspace_write_text_v1",
]
REVISION = "a" * 40
SNAPSHOT_FINGERPRINT = hashlib.sha256(b"phase-4-snapshot").hexdigest()
INITIAL_TREE_HASH = hashlib.sha256(b"initial-tree").hexdigest()


def runner_headers(token: str, request_id: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": request_id or str(uuid.uuid4()),
    }


def register_workspace_runner(
    client: TestClient,
    bootstrap_token: str,
    *,
    name: str = "Phase 4 Runner",
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    registered = client.post(
        "/api/v1/runner-protocol/v1/register",
        headers={
            "Authorization": f"Bearer {bootstrap_token}",
            "X-Request-ID": str(uuid.uuid4()),
        },
        json={
            "display_name": name,
            "protocol_version": 1,
            "software_version": "0.4.0",
            "capabilities": WORKSPACE_CAPABILITIES,
        },
    )
    assert registered.status_code == 201, registered.text
    runner = cast(dict[str, Any], registered.json())
    token = str(runner["runner_token"])
    heartbeat = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(token),
        json={
            "runner_id": runner["runner_id"],
            "protocol_version": 1,
            "software_version": "0.4.0",
            "capabilities": WORKSPACE_CAPABILITIES,
        },
    )
    assert heartbeat.status_code == 200, heartbeat.text
    repository = client.post(
        "/api/v1/runner-protocol/v1/repositories/register",
        headers=runner_headers(token),
        json={
            "runner_id": runner["runner_id"],
            "opaque_handle": "fixture-repository-v1",
            "display_name": "Phase 4 Adversarial Fixture",
            "vcs_kind": "git",
            "capabilities": ["committed_head_read", "isolated_workspace"],
            "current_revision": REVISION,
            "current_branch": "main",
            "source_is_dirty": True,
            "dirty_path_count": 2,
            "metadata_version": 1,
        },
    )
    assert repository.status_code == 200, repository.text
    return runner, token, cast(dict[str, Any], repository.json())


def seed_approved_plan(db: Session) -> Plan:
    task = Task(
        title="Phase 4 fixture execution",
        objective="Exercise only the isolated synthetic fixture workspace.",
        repository_kind="local_path",
        repository_display_name="Phase 4 Adversarial Fixture",
        repository_locator="runner-handle-only",
        status="draft",
        version=1,
        idempotency_key=f"phase4-task-{uuid.uuid4()}",
        idempotency_request_hash="1" * 64,
    )
    db.add(task)
    db.flush()
    run = Run(
        task_id=task.id,
        status="approved",
        permission_level="read_only",
        snapshot_mode="git_head",
        version=1,
        current_plan_version=1,
    )
    db.add(run)
    db.flush()
    snapshot = RepositorySnapshot(
        run_id=run.id,
        source_revision=REVISION,
        branch_name="main",
        repository_is_dirty=True,
        dirty_path_count=2,
        dirty_paths=[],
        scanner_version="fixture-v1",
        scan_policy_version="fixture-v1",
        fingerprint=SNAPSHOT_FINGERPRINT,
        tracked_file_count=10,
        selected_file_count=3,
        skipped_file_count=7,
        total_selected_bytes=100,
        tech_stack={},
        package_manager=None,
        available_scripts=[],
        test_surfaces=[],
        design_system_signals=[],
        repository_instructions=[],
        safety_findings=[],
        manifest=[],
    )
    plan = Plan(
        run_id=run.id,
        version=1,
        status="approved",
        source="deterministic_policy",
        snapshot_fingerprint=SNAPSHOT_FINGERPRINT,
        delivery_package="frontend_quality_remediation",
        objective_summary="Modify only explicitly granted synthetic fixture files.",
        repository_context_summary="Runner-owned isolated workspace.",
        assumptions=[],
        proposed_change_scope=["sandbox/**"],
        explicit_non_goals=["source repository writes"],
        risk_items=["path traversal"],
        acceptance_criteria=["Rollback restores the exact initial tree."],
        evidence_requirements=["bounded diff"],
        stop_conditions=["grant revoked"],
        validation_steps=[],
        required_future_permission_level="isolated_workspace",
        execution_available=False,
        content_hash="2" * 64,
    )
    db.add_all([snapshot, plan])
    db.flush()
    db.add(
        ApprovalDecision(
            run_id=run.id,
            plan_id=plan.id,
            decision="approve",
            comment="Fixture plan approved.",
            actor_type="local_user",
            request_id=f"plan-approve-{uuid.uuid4()}",
        )
    )
    db.commit()
    db.refresh(plan)
    return plan


def create_and_approve_grant(
    client: TestClient,
    plan_id: object,
    repository_id: object,
) -> dict[str, Any]:
    created = client.post(
        "/api/v1/execution-grants",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={"plan_id": str(plan_id), "repository_handle_id": str(repository_id)},
    )
    assert created.status_code == 201, created.text
    grant = cast(dict[str, Any], created.json())
    assert grant["status"] == "pending"
    assert grant["shell_access"] is False
    assert grant["network_policy"] == "none"
    assert grant["source_repository_write_access"] is False
    assert grant["git_delivery_access"] is False
    approved = client.post(
        f"/api/v1/execution-grants/{grant['id']}/decisions",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={"decision": "approve", "reason": "Narrow fixture-only execution approved."},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    return cast(dict[str, Any], approved.json())


def claim_start(
    client: TestClient,
    runner: dict[str, Any],
    token: str,
    expected_job_id: object,
) -> tuple[dict[str, Any], dict[str, str]]:
    claim = client.post(
        "/api/v1/runner-protocol/v1/jobs/claim",
        headers=runner_headers(token),
        json={"runner_id": runner["runner_id"], "wait_seconds": 0},
    )
    assert claim.status_code == 200, claim.text
    assignment = cast(dict[str, Any], claim.json()["assignment"])
    assert assignment["job_id"] == str(expected_job_id)
    identity = {
        "runner_id": str(runner["runner_id"]),
        "attempt_id": str(assignment["attempt_id"]),
        "lease_id": str(assignment["lease_id"]),
    }
    started = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{expected_job_id}/start",
        headers=runner_headers(token),
        json=identity,
    )
    assert started.status_code == 200, started.text
    return assignment, identity


def complete(
    client: TestClient,
    token: str,
    job_id: object,
    identity: dict[str, str],
    result: dict[str, Any],
) -> None:
    response = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job_id}/complete",
        headers=runner_headers(token),
        json={**identity, "result": result},
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "succeeded"


def acquire_side_effect_permit(
    client: TestClient,
    token: str,
    assignment: dict[str, Any],
    identity: dict[str, str],
) -> dict[str, Any]:
    typed_assignment = JobAssignment.model_validate(assignment)
    response = client.post(
        (f"/api/v1/runner-protocol/v1/jobs/{typed_assignment.job_id}/side-effect-permit"),
        headers=runner_headers(token),
        json={
            **identity,
            "job_digest": compute_side_effect_job_digest(typed_assignment.job),
        },
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def checkpoint(
    diff: str,
    tree_hash: str,
    *,
    side_effect_permit_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_revision": REVISION,
        "tree_fingerprint": tree_hash,
        "diff_hash": hashlib.sha256(diff.encode()).hexdigest(),
        "changed_paths": ["sandbox/original.txt"],
        "changed_file_count": 1,
        "total_diff_bytes": len(diff.encode()),
        "diff": diff,
    }
    if side_effect_permit_id is not None:
        payload["side_effect_permit_id"] = side_effect_permit_id
    return payload


def test_execution_grant_is_independent_narrow_and_database_immutable(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    _, _, repository = register_workspace_runner(client, runner_bootstrap_token)
    plan = seed_approved_plan(db_session)
    eligible = client.get("/api/v1/execution-grants/eligible-contexts")
    assert eligible.status_code == 200
    assert eligible.json()["total"] == 1
    assert "runner-handle-only" not in eligible.text

    response = client.post(
        "/api/v1/execution-grants",
        json={
            "plan_id": str(plan.id),
            "repository_handle_id": repository["repository_handle_id"],
        },
    )
    assert response.status_code == 201, response.text
    grant = response.json()
    assert grant["status"] == "pending"
    assert grant["allowed_paths"] == ["sandbox/**"]
    assert "**" not in grant["allowed_paths"]
    assert ".env" in grant["denied_paths"]
    assert len(grant["policy_hash"]) == 64
    assert not any(value.startswith("/") for value in grant["allowed_paths"])

    missing_reason = client.post(
        f"/api/v1/execution-grants/{grant['id']}/decisions",
        json={"decision": "reject"},
    )
    assert missing_reason.status_code == 422
    approved = client.post(
        f"/api/v1/execution-grants/{grant['id']}/decisions",
        headers={"X-Request-ID": "grant-approval"},
        json={"decision": "approve"},
    )
    assert approved.status_code == 200
    assert approved.json()["decision"]["actor_type"] == "local_user"
    replay = client.post(
        f"/api/v1/execution-grants/{grant['id']}/decisions",
        json={"decision": "approve"},
    )
    assert replay.status_code == 200
    conflict = client.post(
        f"/api/v1/execution-grants/{grant['id']}/decisions",
        json={"decision": "reject", "reason": "Different decision."},
    )
    assert conflict.status_code == 409

    with pytest.raises(DBAPIError):
        db_session.execute(
            text("UPDATE execution_grants SET max_files_changed = 99 WHERE id = :grant_id"),
            {"grant_id": grant["id"]},
        )
        db_session.commit()
    db_session.rollback()


def test_workspace_full_runner_protocol_state_machine_and_evidence(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    runner, token, repository = register_workspace_runner(client, runner_bootstrap_token)
    plan = seed_approved_plan(db_session)
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    created = client.post(
        "/api/v1/workspaces",
        headers={"X-Request-ID": "workspace-create"},
        json={"grant_id": grant["id"]},
    )
    assert created.status_code == 201, created.text
    workspace_id = created.json()["workspace"]["id"]
    prepare_job = created.json()["job"]
    assert prepare_job["permission_envelope"]["repository_access"] == "isolated_workspace"
    assert prepare_job["permission_envelope"]["authorization_source"] == "execution_grant"
    assert "path" not in prepare_job["parameters"]
    assignment, identity = claim_start(client, runner, token, prepare_job["id"])
    permit = acquire_side_effect_permit(client, token, assignment, identity)
    complete(
        client,
        token,
        prepare_job["id"],
        identity,
        {
            "kind": "workspace_prepare_v1",
            "workspace_id": workspace_id,
            "repository_handle_id": repository["repository_handle_id"],
            "source_revision": REVISION,
            "workspace_fingerprint": hashlib.sha256(b"workspace").hexdigest(),
            "initial_tree_hash": INITIAL_TREE_HASH,
            "current_tree_hash": INITIAL_TREE_HASH,
            "side_effect_permit_id": permit["id"],
        },
    )
    assert client.get(f"/api/v1/workspaces/{workspace_id}").json()["state"] == "ready"

    read_action = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions/read-text",
        json={"relative_path": "sandbox/original.txt", "max_bytes": 1024},
    )
    assert read_action.status_code == 200
    read_job = read_action.json()["job"]
    _, identity = claim_start(client, runner, token, read_job["id"])
    original = "Original fixture text.\n"
    original_hash = hashlib.sha256(original.encode()).hexdigest()
    complete(
        client,
        token,
        read_job["id"],
        identity,
        {
            "kind": "workspace_read_text_v1",
            "workspace_id": workspace_id,
            "relative_path": "sandbox/original.txt",
            "content": original,
            "sha256": original_hash,
            "size": len(original.encode()),
        },
    )

    denied_sensitive = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        json={
            "mode": "replace",
            "relative_path": "sandbox/.env",
            "content": "denied",
            "expected_sha256": original_hash,
        },
    )
    assert denied_sensitive.status_code == 422
    assert denied_sensitive.json()["error"]["code"] == "sensitive_path_denied"
    traversal = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions/read-text",
        json={"relative_path": "../outside", "max_bytes": 10},
    )
    assert traversal.status_code == 422
    assert traversal.json()["error"]["code"] == "validation_error"

    write_action = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        headers={"X-Request-ID": "replace-original"},
        json={
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": "Updated fixture text.\n",
            "expected_sha256": original_hash,
        },
    )
    assert write_action.status_code == 200, write_action.text
    replay = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        headers={"X-Request-ID": "replace-original"},
        json={
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": "Updated fixture text.\n",
            "expected_sha256": original_hash,
        },
    )
    assert replay.status_code == 200
    assert replay.json()["job"]["id"] == write_action.json()["job"]["id"]
    write_job = write_action.json()["job"]
    assignment, identity = claim_start(client, runner, token, write_job["id"])
    permit = acquire_side_effect_permit(client, token, assignment, identity)
    diff_text = (
        "--- a/sandbox/original.txt\n"
        "+++ b/sandbox/original.txt\n"
        "@@ -1 +1 @@\n"
        "-Original fixture text.\n"
        "+Updated fixture text.\n"
    )
    changed_tree = hashlib.sha256(b"changed-tree").hexdigest()
    updated_hash = hashlib.sha256(b"Updated fixture text.\n").hexdigest()
    complete(
        client,
        token,
        write_job["id"],
        identity,
        {
            "kind": "workspace_write_text_v1",
            "workspace_id": workspace_id,
            "relative_path": "sandbox/original.txt",
            "operation": "replace",
            "sha256": updated_hash,
            "size": len(b"Updated fixture text.\n"),
            "current_tree_hash": changed_tree,
            "changed_file_count": 1,
            "total_written_bytes": len(b"Updated fixture text.\n"),
            "checkpoint": checkpoint(
                diff_text,
                changed_tree,
                side_effect_permit_id=str(permit["id"]),
            ),
            "side_effect_permit_id": permit["id"],
        },
    )
    checkpoints = client.get(f"/api/v1/workspaces/{workspace_id}/checkpoints")
    assert checkpoints.status_code == 200
    assert checkpoints.json()["total"] == 1
    assert (
        checkpoints.json()["items"][0]["diff_hash"]
        == hashlib.sha256(diff_text.encode()).hexdigest()
    )
    assert checkpoints.json()["items"][0]["side_effect_permit_id"] == permit["id"]

    conflict_action = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        json={
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": "Conflicting text.",
            "expected_sha256": original_hash,
        },
    )
    assert conflict_action.status_code == 200
    conflict_job = conflict_action.json()["job"]
    assignment, identity = claim_start(client, runner, token, conflict_job["id"])
    permit = acquire_side_effect_permit(client, token, assignment, identity)
    failed = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{conflict_job['id']}/fail",
        headers=runner_headers(token),
        json={
            **identity,
            "error_code": "content_conflict",
            "error_message": None,
            "side_effect_permit_id": permit["id"],
        },
    )
    assert failed.status_code == 200
    assert client.get(f"/api/v1/workspaces/{workspace_id}").json()["state"] == "active"

    diff_action = client.post(f"/api/v1/workspaces/{workspace_id}/actions/diff")
    assert diff_action.status_code == 200
    diff_job = diff_action.json()["job"]
    _, identity = claim_start(client, runner, token, diff_job["id"])
    complete(
        client,
        token,
        diff_job["id"],
        identity,
        {
            "kind": "workspace_diff_v1",
            "workspace_id": workspace_id,
            "diff": diff_text,
            "diff_hash": hashlib.sha256(diff_text.encode()).hexdigest(),
            "changed_paths": ["sandbox/original.txt"],
            "total_diff_bytes": len(diff_text.encode()),
            "current_tree_hash": changed_tree,
            "checkpoint": checkpoint(diff_text, changed_tree),
        },
    )
    assert client.get(f"/api/v1/workspaces/{workspace_id}").json()["state"] == "sealed"

    rollback_action = client.post(f"/api/v1/workspaces/{workspace_id}/actions/rollback")
    assert rollback_action.status_code == 200
    rollback_job = rollback_action.json()["job"]
    assignment, identity = claim_start(client, runner, token, rollback_job["id"])
    permit = acquire_side_effect_permit(client, token, assignment, identity)
    complete(
        client,
        token,
        rollback_job["id"],
        identity,
        {
            "kind": "workspace_rollback_v1",
            "workspace_id": workspace_id,
            "clean": True,
            "current_tree_hash": INITIAL_TREE_HASH,
            "removed_created_paths": [],
            "side_effect_permit_id": permit["id"],
        },
    )
    rolled_back = client.get(f"/api/v1/workspaces/{workspace_id}").json()
    assert rolled_back["state"] == "rolled_back"
    assert rolled_back["changed_file_count"] == 0

    discard_action = client.post(f"/api/v1/workspaces/{workspace_id}/actions/discard")
    assert discard_action.status_code == 200
    discard_job = discard_action.json()["job"]
    assignment, identity = claim_start(client, runner, token, discard_job["id"])
    permit = acquire_side_effect_permit(client, token, assignment, identity)
    complete(
        client,
        token,
        discard_job["id"],
        identity,
        {
            "kind": "workspace_discard_v1",
            "workspace_id": workspace_id,
            "discarded": True,
            "idempotent": False,
            "side_effect_permit_id": permit["id"],
        },
    )
    repeated_discard = client.post(f"/api/v1/workspaces/{workspace_id}/actions/discard")
    assert repeated_discard.status_code == 200
    assert repeated_discard.json()["job"]["id"] == discard_job["id"]
    durable = client.get(f"/api/v1/workspaces/{workspace_id}").json()
    assert durable["state"] == "discarded"
    events = client.get(f"/api/v1/workspaces/{workspace_id}/events").json()["items"]
    event_types = [item["event_type"] for item in events]
    for required in (
        "grant_approved",
        "workspace_requested",
        "mirror_prepared",
        "workspace_prepared",
        "checkpoint_created",
        "diff_generated",
        "rollback_completed",
        "workspace_discarded",
    ):
        assert required in event_types


def test_stale_repository_and_revoked_grant_block_execution(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    runner, token, repository = register_workspace_runner(client, runner_bootstrap_token)
    plan = seed_approved_plan(db_session)
    stale_registration = client.post(
        "/api/v1/runner-protocol/v1/repositories/register",
        headers=runner_headers(token),
        json={
            "runner_id": runner["runner_id"],
            "opaque_handle": "fixture-repository-v1",
            "display_name": "Phase 4 Adversarial Fixture",
            "vcs_kind": "git",
            "capabilities": ["committed_head_read", "isolated_workspace"],
            "current_revision": "b" * 40,
            "current_branch": "main",
            "source_is_dirty": False,
            "dirty_path_count": 0,
            "metadata_version": 1,
        },
    )
    assert stale_registration.status_code == 200
    stale = client.post(
        "/api/v1/execution-grants",
        json={
            "plan_id": str(plan.id),
            "repository_handle_id": repository["repository_handle_id"],
        },
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_execution_baseline"

    refreshed = client.post(
        "/api/v1/runner-protocol/v1/repositories/register",
        headers=runner_headers(token),
        json={
            "runner_id": runner["runner_id"],
            "opaque_handle": "fixture-repository-v1",
            "display_name": "Phase 4 Adversarial Fixture",
            "vcs_kind": "git",
            "capabilities": ["committed_head_read", "isolated_workspace"],
            "current_revision": REVISION,
            "current_branch": "main",
            "source_is_dirty": True,
            "dirty_path_count": 2,
            "metadata_version": 1,
        },
    )
    assert refreshed.status_code == 200
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    workspace = client.post("/api/v1/workspaces", json={"grant_id": grant["id"]})
    assert workspace.status_code == 201
    revoked = client.post(f"/api/v1/execution-grants/{grant['id']}/revoke")
    assert revoked.status_code == 200
    claim = client.post(
        "/api/v1/runner-protocol/v1/jobs/claim",
        headers=runner_headers(token),
        json={"runner_id": runner["runner_id"], "wait_seconds": 0},
    )
    assert claim.status_code == 200
    assert claim.json()["assignment"] is None
    job = client.get(f"/api/v1/runner-jobs/{workspace.json()['job']['id']}").json()
    assert job["state"] == "cancelled"
    assert job["error_code"] == "execution_grant_inactive"


def test_phase_four_openapi_has_closed_workspace_surface(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    paths = document["paths"]
    for path in (
        "/api/v1/repositories",
        "/api/v1/execution-grants/eligible-contexts",
        "/api/v1/execution-grants",
        "/api/v1/execution-grants/{grant_id}/decisions",
        "/api/v1/workspaces",
        "/api/v1/workspaces/{workspace_id}",
        "/api/v1/workspaces/{workspace_id}/actions/list",
        "/api/v1/workspaces/{workspace_id}/actions/read-text",
        "/api/v1/workspaces/{workspace_id}/actions/write-text",
        "/api/v1/workspaces/{workspace_id}/actions/status",
        "/api/v1/workspaces/{workspace_id}/actions/diff",
        "/api/v1/workspaces/{workspace_id}/actions/rollback",
        "/api/v1/workspaces/{workspace_id}/actions/discard",
        "/api/v1/workspaces/{workspace_id}/events",
        "/api/v1/workspaces/{workspace_id}/checkpoints",
    ):
        assert path in paths
    write_schema = document["components"]["schemas"]["WorkspaceWriteTextAction"]
    assert "relative_path" in write_schema["properties"]
    assert "path" not in write_schema["properties"]


def test_side_effect_permit_endpoint_rejects_stale_or_wrong_binding_and_replays(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    runner, token, repository = register_workspace_runner(client, runner_bootstrap_token)
    plan = seed_approved_plan(db_session)
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    created = client.post(
        "/api/v1/workspaces",
        json={"grant_id": grant["id"]},
    )
    assert created.status_code == 201, created.text
    workspace_id = created.json()["workspace"]["id"]
    job = created.json()["job"]
    assignment, identity = claim_start(client, runner, token, job["id"])
    typed_assignment = JobAssignment.model_validate(assignment)
    endpoint = f"/api/v1/runner-protocol/v1/jobs/{job['id']}/side-effect-permit"
    digest = compute_side_effect_job_digest(typed_assignment.job)

    stale = client.post(
        endpoint,
        headers=runner_headers(token),
        json={**identity, "lease_id": str(uuid.uuid4()), "job_digest": digest},
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["error"]["code"] == "stale_lease"

    wrong_digest = client.post(
        endpoint,
        headers=runner_headers(token),
        json={**identity, "job_digest": "f" * 64},
    )
    assert wrong_digest.status_code == 422, wrong_digest.text
    assert wrong_digest.json()["error"]["code"] == "operation_digest_mismatch"

    acquired = client.post(
        endpoint,
        headers=runner_headers(token),
        json={**identity, "job_digest": digest},
    )
    assert acquired.status_code == 200, acquired.text
    permit = acquired.json()
    assert permit["state"] == "consumed"
    assert permit["idempotent_replay"] is False
    replay = client.post(
        endpoint,
        headers=runner_headers(token),
        json={**identity, "job_digest": digest},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == permit["id"]
    assert replay.json()["idempotent_replay"] is True

    wrong_result_binding = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/complete",
        headers=runner_headers(token),
        json={
            **identity,
            "result": {
                "kind": "workspace_prepare_v1",
                "workspace_id": workspace_id,
                "repository_handle_id": repository["repository_handle_id"],
                "source_revision": REVISION,
                "workspace_fingerprint": hashlib.sha256(b"workspace").hexdigest(),
                "initial_tree_hash": INITIAL_TREE_HASH,
                "current_tree_hash": INITIAL_TREE_HASH,
                "side_effect_permit_id": str(uuid.uuid4()),
            },
        },
    )
    assert wrong_result_binding.status_code == 409, wrong_result_binding.text
    assert wrong_result_binding.json()["error"]["code"] == "side_effect_permit_invalid"

    complete(
        client,
        token,
        job["id"],
        identity,
        {
            "kind": "workspace_prepare_v1",
            "workspace_id": workspace_id,
            "repository_handle_id": repository["repository_handle_id"],
            "source_revision": REVISION,
            "workspace_fingerprint": hashlib.sha256(b"workspace").hexdigest(),
            "initial_tree_hash": INITIAL_TREE_HASH,
            "current_tree_hash": INITIAL_TREE_HASH,
            "side_effect_permit_id": permit["id"],
        },
    )
    db_session.expire_all()
    persisted = db_session.get(SideEffectPermit, uuid.UUID(permit["id"]))
    assert persisted is not None
    assert persisted.state == "completed"
    assert persisted.terminal_at is not None
    workspace_events = client.get(f"/api/v1/workspaces/{workspace_id}/events").json()["items"]
    permit_events = [
        item
        for item in workspace_events
        if item["event_type"] in {"permit_acquired", "permit_completed"}
    ]
    assert len(permit_events) == 2
    assert all(item["side_effect_permit_id"] == permit["id"] for item in permit_events)
    with pytest.raises(DBAPIError):
        db_session.execute(
            text("UPDATE side_effect_permits SET operation_digest = :digest WHERE id = :permit_id"),
            {"digest": "f" * 64, "permit_id": permit["id"]},
        )
        db_session.commit()
    db_session.rollback()


def test_permit_acquire_and_grant_revoke_serialize_without_deadlock(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
) -> None:
    runner, token, repository = register_workspace_runner(client, runner_bootstrap_token)
    plan = seed_approved_plan(db_session)
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    created = client.post(
        "/api/v1/workspaces",
        json={"grant_id": grant["id"]},
    )
    assert created.status_code == 201, created.text
    job = created.json()["job"]
    assignment, identity = claim_start(client, runner, token, job["id"])
    typed_assignment = JobAssignment.model_validate(assignment)
    request = SideEffectPermitAcquireRequest.model_validate(
        {
            **identity,
            "job_digest": compute_side_effect_job_digest(typed_assignment.job),
        }
    )
    grant_id = uuid.UUID(grant["id"])
    job_id = uuid.UUID(job["id"])
    barrier = threading.Barrier(2)
    engine = create_engine(database_url, pool_pre_ping=True)

    def acquire() -> tuple[str, str]:
        with Session(engine) as session:
            service = RunnerService(session)
            authenticated = service.authenticate(token)
            barrier.wait(timeout=10)
            try:
                permit = service.acquire_side_effect_permit(
                    authenticated,
                    job_id,
                    request,
                    request_id=f"concurrent-permit-{uuid.uuid4()}",
                )
            except RunnerServiceError as exc:
                session.rollback()
                return "denied", exc.code
            return "acquired", str(permit.id)

    def revoke() -> tuple[str, str]:
        with Session(engine) as session:
            barrier.wait(timeout=10)
            result = WorkspaceService(session).revoke_grant(
                grant_id,
                request_id=f"concurrent-revoke-{uuid.uuid4()}",
            )
            return "revoked", result.status

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            acquire_future = executor.submit(acquire)
            revoke_future = executor.submit(revoke)
            acquire_result = acquire_future.result(timeout=20)
            revoke_result = revoke_future.result(timeout=20)

        assert revoke_result[0] == "revoked"
        with Session(engine) as session:
            durable_grant = session.get(ExecutionGrant, grant_id)
            durable_job = session.get(RunnerJob, job_id)
            permits = list(
                session.scalars(
                    select(SideEffectPermit).where(SideEffectPermit.grant_id == grant_id)
                )
            )
            assert durable_grant is not None
            assert durable_job is not None
            assert len(permits) <= 1
            assert durable_job.state == "cancel_requested"
            if acquire_result[0] == "acquired":
                assert durable_grant.status == "revoke_requested"
                assert revoke_result[1] == "revoke_requested"
                assert len(permits) == 1
                assert permits[0].state == "consumed"
                assert str(permits[0].id) == acquire_result[1]
            else:
                assert acquire_result[1] in {"execution_grant_inactive", "stale_lease"}
                assert durable_grant.status == "revoked"
                assert revoke_result[1] == "revoked"
                assert permits == []
    finally:
        engine.dispose()


def test_revocation_waits_for_consumed_permit_then_cancel_ack_finalizes(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    runner, token, repository = register_workspace_runner(client, runner_bootstrap_token)
    plan = seed_approved_plan(db_session)
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    created = client.post(
        "/api/v1/workspaces",
        json={"grant_id": grant["id"]},
    )
    assert created.status_code == 201, created.text
    job = created.json()["job"]
    assignment, identity = claim_start(client, runner, token, job["id"])
    permit = acquire_side_effect_permit(client, token, assignment, identity)

    revoked = client.post(f"/api/v1/execution-grants/{grant['id']}/revoke")
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoke_requested"
    assert revoked.json()["in_flight_permit_count"] == 1
    assert revoked.json()["revocation_requested_at"] is not None
    assert revoked.json()["revoked_at"] is None

    cancelled = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/cancelled",
        headers=runner_headers(token),
        json=identity,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["state"] == "cancelled"
    db_session.expire_all()
    durable_grant = db_session.get(ExecutionGrant, uuid.UUID(grant["id"]))
    durable_permit = db_session.get(SideEffectPermit, uuid.UUID(permit["id"]))
    assert durable_grant is not None
    assert durable_permit is not None
    assert durable_grant.status == "revoked"
    assert durable_grant.revoked_at is not None
    assert durable_permit.state == "cancelled"
    assert durable_permit.terminal_at is not None


def test_expired_lease_cannot_acquire_side_effect_permit(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    runner, token, repository = register_workspace_runner(client, runner_bootstrap_token)
    plan = seed_approved_plan(db_session)
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    created = client.post(
        "/api/v1/workspaces",
        json={"grant_id": grant["id"]},
    )
    assert created.status_code == 201, created.text
    job = created.json()["job"]
    assignment, identity = claim_start(client, runner, token, job["id"])
    typed_assignment = JobAssignment.model_validate(assignment)
    db_session.execute(
        text(
            "UPDATE runner_job_attempts "
            "SET leased_until = now() - interval '1 second' "
            "WHERE id = :attempt_id"
        ),
        {"attempt_id": identity["attempt_id"]},
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/side-effect-permit",
        headers=runner_headers(token),
        json={
            **identity,
            "job_digest": compute_side_effect_job_digest(typed_assignment.job),
        },
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "stale_lease"
    assert (
        db_session.scalar(
            select(SideEffectPermit).where(SideEffectPermit.job_id == uuid.UUID(job["id"]))
        )
        is None
    )
