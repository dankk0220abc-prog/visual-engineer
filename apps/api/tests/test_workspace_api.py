import hashlib
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
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
from visual_engineer_api.models.runner import RunnerJob, RunnerJobEvent
from visual_engineer_api.models.task import Task
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    SideEffectPermit,
    Workspace,
    WorkspaceCheckpoint,
    WorkspaceEvent,
)
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError
from visual_engineer_api.services.workspace import WorkspaceService
from visual_engineer_runner.config import LocalRepositoryConfig, RunnerSettings
from visual_engineer_runner.workspace_manager import WorkspaceManager
from visual_engineer_runner_protocol import (
    JobAssignment,
    SideEffectPermitAcquireRequest,
    WorkspacePrepareJobSpec,
    WorkspacePrepareResult,
    WorkspaceWriteTextJobSpec,
    WorkspaceWriteTextResult,
    compute_side_effect_job_digest,
    side_effect_permit_digest_matches,
)
from visual_engineer_runner_protocol import (
    SideEffectPermit as ProtocolSideEffectPermit,
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
    current_revision: str = REVISION,
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
            "current_revision": current_revision,
            "current_branch": "main",
            "source_is_dirty": True,
            "dirty_path_count": 2,
            "metadata_version": 1,
        },
    )
    assert repository.status_code == 200, repository.text
    return runner, token, cast(dict[str, Any], repository.json())


def seed_approved_plan(db: Session, *, source_revision: str = REVISION) -> Plan:
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
        source_revision=source_revision,
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
    db_session.expire_all()
    failed_permit = db_session.get(SideEffectPermit, uuid.UUID(permit["id"]))
    assert failed_permit is not None
    assert failed_permit.state == "failed"
    assert failed_permit.terminal_at is not None
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


def test_concurrent_permit_acquire_has_one_postgresql_consumer(
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
    created = client.post("/api/v1/workspaces", json={"grant_id": grant["id"]})
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
    job_id = uuid.UUID(job["id"])
    barrier = threading.Barrier(2)
    engine = create_engine(database_url, pool_pre_ping=True)

    def acquire(index: int) -> tuple[str, bool]:
        with Session(engine) as session:
            service = RunnerService(session)
            authenticated = service.authenticate(token)
            barrier.wait(timeout=10)
            permit = service.acquire_side_effect_permit(
                authenticated,
                job_id,
                request,
                request_id=f"single-consumer-{index}-{uuid.uuid4()}",
            )
            return str(permit.id), permit.idempotent_replay

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(acquire, range(2)))
        assert results[0][0] == results[1][0]
        assert sorted(result[1] for result in results) == [False, True]
        with Session(engine) as session:
            permits = list(
                session.scalars(select(SideEffectPermit).where(SideEffectPermit.job_id == job_id))
            )
            acquired_events = list(
                session.scalars(
                    select(RunnerJobEvent).where(
                        RunnerJobEvent.job_id == job_id,
                        RunnerJobEvent.event_type == "side_effect_permit_acquired",
                    )
                )
            )
            assert len(permits) == 1
            assert permits[0].state == "consumed"
            assert len(acquired_events) == 1
    finally:
        engine.dispose()


def test_real_postgresql_permit_crash_windows_retry_and_disk_db_ordering(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    tmp_path: Path,
) -> None:
    source, revision = _real_repository_fixture(tmp_path)
    runner, token, repository = register_workspace_runner(
        client,
        runner_bootstrap_token,
        current_revision=revision,
    )
    plan = seed_approved_plan(db_session, source_revision=revision)
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    settings = RunnerSettings(
        credential_path=tmp_path / "runner-state" / "credential.json",
        repository_handles={
            "fixture-repository-v1": LocalRepositoryConfig(
                path=source,
                display_name="Phase 4 Adversarial Fixture",
            )
        },
        mirror_root=tmp_path / "runner-state" / "mirrors",
        workspace_root=tmp_path / "runner-state" / "workspaces",
        registry_root=tmp_path / "runner-state" / "registry",
        require_source_read_only=False,
    )
    manager = WorkspaceManager(settings)
    created = client.post("/api/v1/workspaces", json={"grant_id": grant["id"]})
    assert created.status_code == 201, created.text
    workspace_id = uuid.UUID(created.json()["workspace"]["id"])
    prepare_job = created.json()["job"]
    prepare_assignment, prepare_identity = claim_start(
        client,
        runner,
        token,
        prepare_job["id"],
    )
    typed_prepare_assignment = JobAssignment.model_validate(prepare_assignment)
    assert isinstance(typed_prepare_assignment.job, WorkspacePrepareJobSpec)
    prepare_endpoint = f"/api/v1/runner-protocol/v1/jobs/{prepare_job['id']}/side-effect-permit"

    denied = client.post(
        prepare_endpoint,
        headers=runner_headers(token),
        json={**prepare_identity, "job_digest": "f" * 64},
    )
    assert denied.status_code == 422, denied.text
    assert denied.json()["error"]["code"] == "operation_digest_mismatch"
    assert not manager._git.workspace_path(workspace_id).exists()
    assert (
        db_session.scalar(
            select(SideEffectPermit).where(SideEffectPermit.job_id == uuid.UUID(prepare_job["id"]))
        )
        is None
    )

    prepare_permit_payload = acquire_side_effect_permit(
        client,
        token,
        prepare_assignment,
        prepare_identity,
    )
    prepare_permit = ProtocolSideEffectPermit.model_validate(prepare_permit_payload)
    assert side_effect_permit_digest_matches(
        prepare_permit,
        prepare_permit.operation_digest,
    )
    assert prepare_permit.runner_id == uuid.UUID(runner["runner_id"])
    assert prepare_permit.grant_id == uuid.UUID(grant["id"])
    assert prepare_permit.workspace_id == workspace_id
    assert prepare_permit.repository_handle_id == uuid.UUID(repository["repository_handle_id"])
    assert prepare_permit.source_revision == revision
    assert prepare_permit.policy_hash == grant["policy_hash"]
    assert prepare_permit.job_digest == compute_side_effect_job_digest(typed_prepare_assignment.job)
    assert not manager._git.workspace_path(workspace_id).exists()

    prepare_result = cast(
        WorkspacePrepareResult,
        manager.execute(
            typed_prepare_assignment.job,
            operation_id=typed_prepare_assignment.job_id,
            cancel_event=threading.Event(),
            side_effect_permit=prepare_permit,
        ),
    )
    workspace_path = manager._git.workspace_path(workspace_id)
    assert workspace_path.is_dir()
    db_session.expire_all()
    durable_prepare_permit = db_session.get(SideEffectPermit, prepare_permit.id)
    durable_workspace = db_session.get(Workspace, workspace_id)
    assert durable_prepare_permit is not None
    assert durable_workspace is not None
    assert durable_prepare_permit.state == "consumed"
    assert durable_workspace.state == "preparing"
    assert durable_workspace.current_tree_hash is None

    prepare_replay = WorkspaceManager(settings).execute(
        typed_prepare_assignment.job,
        operation_id=typed_prepare_assignment.job_id,
        cancel_event=threading.Event(),
        side_effect_permit=prepare_permit,
    )
    assert prepare_replay == prepare_result
    complete(
        client,
        token,
        prepare_job["id"],
        prepare_identity,
        prepare_result.model_dump(mode="json"),
    )

    original = (workspace_path / "sandbox" / "tracked.txt").read_text(encoding="utf-8")
    original_hash = hashlib.sha256(original.encode()).hexdigest()
    updated = "updated through a real PostgreSQL permit\n"
    write_action = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        json={
            "mode": "replace",
            "relative_path": "sandbox/tracked.txt",
            "content": updated,
            "expected_sha256": original_hash,
        },
    )
    assert write_action.status_code == 200, write_action.text
    write_job = write_action.json()["job"]
    write_assignment, write_identity = claim_start(client, runner, token, write_job["id"])
    typed_write_assignment = JobAssignment.model_validate(write_assignment)
    assert isinstance(typed_write_assignment.job, WorkspaceWriteTextJobSpec)
    write_permit_payload = acquire_side_effect_permit(
        client,
        token,
        write_assignment,
        write_identity,
    )
    write_permit = ProtocolSideEffectPermit.model_validate(write_permit_payload)
    assert write_permit.job_digest == compute_side_effect_job_digest(typed_write_assignment.job)
    for budget_field in (
        "max_files_changed",
        "max_total_write_bytes",
        "max_single_file_bytes",
        "max_diff_bytes",
        "workspace_ttl_seconds",
    ):
        assert (
            getattr(typed_write_assignment.job.execution_grant, budget_field) == grant[budget_field]
        )
    assert (workspace_path / "sandbox" / "tracked.txt").read_text() == original
    db_session.expire_all()
    durable_write_permit = db_session.get(SideEffectPermit, write_permit.id)
    durable_workspace = db_session.get(Workspace, workspace_id)
    assert durable_write_permit is not None
    assert durable_workspace is not None
    assert durable_write_permit.state == "consumed"
    assert durable_workspace.total_written_bytes == 0

    write_result = cast(
        WorkspaceWriteTextResult,
        manager.execute(
            typed_write_assignment.job,
            operation_id=typed_write_assignment.job_id,
            cancel_event=threading.Event(),
            side_effect_permit=write_permit,
        ),
    )
    target = workspace_path / "sandbox" / "tracked.txt"
    committed_inode = target.stat().st_ino
    assert target.read_text(encoding="utf-8") == updated
    assert write_result.side_effect_permit_id == write_permit.id
    assert write_result.checkpoint.side_effect_permit_id == write_permit.id
    local_registry = manager._load_registry(workspace_id)
    assert local_registry is not None
    assert local_registry.total_written_bytes == len(updated.encode())
    db_session.expire_all()
    durable_workspace = db_session.get(Workspace, workspace_id)
    durable_write_permit = db_session.get(SideEffectPermit, write_permit.id)
    assert durable_workspace is not None
    assert durable_write_permit is not None
    assert durable_workspace.total_written_bytes == 0
    assert durable_write_permit.state == "consumed"

    write_replay = WorkspaceManager(settings).execute(
        typed_write_assignment.job,
        operation_id=typed_write_assignment.job_id,
        cancel_event=threading.Event(),
        side_effect_permit=write_permit,
    )
    assert write_replay == write_result
    assert target.stat().st_ino == committed_inode
    replay_registry = WorkspaceManager(settings)._load_registry(workspace_id)
    assert replay_registry is not None
    assert replay_registry.total_written_bytes == len(updated.encode())

    _install_completion_crash_trigger(db_session)
    failed_completion = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{write_job['id']}/complete",
        headers=runner_headers(token, "forced-completion-crash"),
        json={
            **write_identity,
            "result": write_result.model_dump(mode="json"),
        },
    )
    assert failed_completion.status_code == 500, failed_completion.text
    db_session.rollback()
    db_session.expire_all()
    durable_write_permit = db_session.get(SideEffectPermit, write_permit.id)
    durable_write_job = db_session.get(RunnerJob, uuid.UUID(write_job["id"]))
    durable_workspace = db_session.get(Workspace, workspace_id)
    assert durable_write_permit is not None
    assert durable_write_job is not None
    assert durable_workspace is not None
    assert durable_write_permit.state == "consumed"
    assert durable_write_permit.terminal_at is None
    assert durable_write_job.state == "running"
    assert durable_workspace.total_written_bytes == 0
    assert (
        db_session.scalar(
            select(WorkspaceCheckpoint).where(
                WorkspaceCheckpoint.side_effect_permit_id == write_permit.id
            )
        )
        is None
    )
    assert target.read_text(encoding="utf-8") == updated
    assert target.stat().st_ino == committed_inode

    _remove_completion_crash_trigger(db_session)
    final_replay = WorkspaceManager(settings).execute(
        typed_write_assignment.job,
        operation_id=typed_write_assignment.job_id,
        cancel_event=threading.Event(),
        side_effect_permit=write_permit,
    )
    assert final_replay == write_result
    assert target.stat().st_ino == committed_inode
    complete(
        client,
        token,
        write_job["id"],
        write_identity,
        write_result.model_dump(mode="json"),
    )
    terminal_replay = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{write_job['id']}/complete",
        headers=runner_headers(token),
        json={
            **write_identity,
            "result": write_result.model_dump(mode="json"),
        },
    )
    assert terminal_replay.status_code == 200, terminal_replay.text
    assert terminal_replay.json()["idempotent_replay"] is True

    db_session.expire_all()
    durable_write_permit = db_session.get(SideEffectPermit, write_permit.id)
    durable_write_job = db_session.get(RunnerJob, uuid.UUID(write_job["id"]))
    durable_workspace = db_session.get(Workspace, workspace_id)
    assert durable_write_permit is not None
    assert durable_write_job is not None
    assert durable_workspace is not None
    assert durable_write_permit.state == "completed"
    assert durable_write_permit.terminal_at is not None
    assert durable_write_job.state == "succeeded"
    assert durable_write_job.result is not None
    assert durable_write_job.result["side_effect_permit_id"] == str(write_permit.id)
    assert durable_write_job.result["checkpoint"]["side_effect_permit_id"] == str(write_permit.id)
    assert durable_workspace.total_written_bytes == len(updated.encode())
    checkpoints = list(
        db_session.scalars(
            select(WorkspaceCheckpoint).where(
                WorkspaceCheckpoint.workspace_id == workspace_id,
                WorkspaceCheckpoint.side_effect_permit_id == write_permit.id,
            )
        )
    )
    assert len(checkpoints) == 1
    permit_workspace_events = list(
        db_session.scalars(
            select(WorkspaceEvent).where(
                WorkspaceEvent.workspace_id == workspace_id,
                WorkspaceEvent.side_effect_permit_id == write_permit.id,
            )
        )
    )
    assert {"permit_acquired", "permit_completed", "checkpoint_created"}.issubset(
        {event.event_type for event in permit_workspace_events}
    )
    permit_runner_events = list(
        db_session.scalars(
            select(RunnerJobEvent).where(
                RunnerJobEvent.job_id == uuid.UUID(write_job["id"]),
                RunnerJobEvent.event_type.in_(
                    (
                        "side_effect_permit_acquired",
                        "side_effect_permit_completed",
                    )
                ),
            )
        )
    )
    assert [event.event_type for event in permit_runner_events].count(
        "side_effect_permit_acquired"
    ) == 1
    assert [event.event_type for event in permit_runner_events].count(
        "side_effect_permit_completed"
    ) == 1
    assert target.read_text(encoding="utf-8") == updated
    assert target.stat().st_ino == committed_inode


def test_permit_identity_and_expired_grant_denials_leave_zero_disk_side_effects(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    tmp_path: Path,
) -> None:
    source, revision = _real_repository_fixture(tmp_path)
    runner, token, repository = register_workspace_runner(
        client,
        runner_bootstrap_token,
        current_revision=revision,
    )
    plan = seed_approved_plan(db_session, source_revision=revision)
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    settings = RunnerSettings(
        credential_path=tmp_path / "runner-state" / "credential.json",
        repository_handles={
            "fixture-repository-v1": LocalRepositoryConfig(
                path=source,
                display_name="Phase 4 Adversarial Fixture",
            )
        },
        mirror_root=tmp_path / "runner-state" / "mirrors",
        workspace_root=tmp_path / "runner-state" / "workspaces",
        registry_root=tmp_path / "runner-state" / "registry",
        require_source_read_only=False,
    )
    manager = WorkspaceManager(settings)
    created = client.post("/api/v1/workspaces", json={"grant_id": grant["id"]})
    assert created.status_code == 201, created.text
    workspace_id = uuid.UUID(created.json()["workspace"]["id"])
    job = created.json()["job"]
    assignment, identity = claim_start(client, runner, token, job["id"])
    typed_assignment = JobAssignment.model_validate(assignment)
    endpoint = f"/api/v1/runner-protocol/v1/jobs/{job['id']}/side-effect-permit"
    digest = compute_side_effect_job_digest(typed_assignment.job)
    denials = (
        (
            {**identity, "runner_id": str(uuid.uuid4()), "job_digest": digest},
            "runner_identity_mismatch",
        ),
        (
            {**identity, "attempt_id": str(uuid.uuid4()), "job_digest": digest},
            "stale_lease",
        ),
        (
            {**identity, "lease_id": str(uuid.uuid4()), "job_digest": digest},
            "stale_lease",
        ),
        (
            {**identity, "job_digest": "f" * 64},
            "operation_digest_mismatch",
        ),
    )
    for payload, expected_code in denials:
        response = client.post(endpoint, headers=runner_headers(token), json=payload)
        assert response.status_code in {403, 409, 422}, response.text
        assert response.json()["error"]["code"] == expected_code
        assert (
            db_session.scalar(
                select(SideEffectPermit).where(SideEffectPermit.job_id == uuid.UUID(job["id"]))
            )
            is None
        )
        assert not manager._git.workspace_path(workspace_id).exists()

    db_session.execute(
        text("UPDATE execution_grants SET status = 'expired' WHERE id = :grant_id"),
        {"grant_id": grant["id"]},
    )
    db_session.commit()
    expired = client.post(
        endpoint,
        headers=runner_headers(token),
        json={**identity, "job_digest": digest},
    )
    assert expired.status_code == 409, expired.text
    assert expired.json()["error"]["code"] == "execution_grant_inactive"
    assert (
        db_session.scalar(
            select(SideEffectPermit).where(SideEffectPermit.job_id == uuid.UUID(job["id"]))
        )
        is None
    )
    assert not manager._git.workspace_path(workspace_id).exists()


def test_permit_last_moment_budget_recheck_prevents_disk_write(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    tmp_path: Path,
) -> None:
    source, revision = _real_repository_fixture(tmp_path)
    runner, token, repository = register_workspace_runner(
        client,
        runner_bootstrap_token,
        current_revision=revision,
    )
    plan = seed_approved_plan(db_session, source_revision=revision)
    grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    settings = RunnerSettings(
        credential_path=tmp_path / "runner-state" / "credential.json",
        repository_handles={
            "fixture-repository-v1": LocalRepositoryConfig(
                path=source,
                display_name="Phase 4 Adversarial Fixture",
            )
        },
        mirror_root=tmp_path / "runner-state" / "mirrors",
        workspace_root=tmp_path / "runner-state" / "workspaces",
        registry_root=tmp_path / "runner-state" / "registry",
        require_source_read_only=False,
    )
    manager = WorkspaceManager(settings)
    created = client.post("/api/v1/workspaces", json={"grant_id": grant["id"]})
    assert created.status_code == 201, created.text
    workspace_id = uuid.UUID(created.json()["workspace"]["id"])
    prepare_job = created.json()["job"]
    prepare_assignment, prepare_identity = claim_start(
        client,
        runner,
        token,
        prepare_job["id"],
    )
    typed_prepare = JobAssignment.model_validate(prepare_assignment)
    assert isinstance(typed_prepare.job, WorkspacePrepareJobSpec)
    prepare_permit = ProtocolSideEffectPermit.model_validate(
        acquire_side_effect_permit(
            client,
            token,
            prepare_assignment,
            prepare_identity,
        )
    )
    prepare_result = cast(
        WorkspacePrepareResult,
        manager.execute(
            typed_prepare.job,
            operation_id=typed_prepare.job_id,
            cancel_event=threading.Event(),
            side_effect_permit=prepare_permit,
        ),
    )
    complete(
        client,
        token,
        prepare_job["id"],
        prepare_identity,
        prepare_result.model_dump(mode="json"),
    )
    target = manager._git.workspace_path(workspace_id) / "sandbox" / "tracked.txt"
    original = target.read_text(encoding="utf-8")
    original_hash = hashlib.sha256(original.encode()).hexdigest()
    write = client.post(
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        json={
            "mode": "replace",
            "relative_path": "sandbox/tracked.txt",
            "content": "must be denied by the final permit budget check\n",
            "expected_sha256": original_hash,
        },
    )
    assert write.status_code == 200, write.text
    write_job = write.json()["job"]
    write_assignment, write_identity = claim_start(client, runner, token, write_job["id"])
    typed_write = JobAssignment.model_validate(write_assignment)
    db_session.execute(
        text("UPDATE workspaces SET total_written_bytes = :budget WHERE id = :workspace_id"),
        {
            "budget": grant["max_total_write_bytes"],
            "workspace_id": str(workspace_id),
        },
    )
    db_session.commit()

    denied = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{write_job['id']}/side-effect-permit",
        headers=runner_headers(token),
        json={
            **write_identity,
            "job_digest": compute_side_effect_job_digest(typed_write.job),
        },
    )
    assert denied.status_code == 422, denied.text
    assert denied.json()["error"]["code"] == "total_write_budget_exceeded"
    assert (
        db_session.scalar(
            select(SideEffectPermit).where(SideEffectPermit.job_id == uuid.UUID(write_job["id"]))
        )
        is None
    )
    assert target.read_text(encoding="utf-8") == original


def _real_repository_fixture(tmp_path: Path) -> tuple[Path, str]:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.name", "Permit Fixture")
    _git(source, "config", "user.email", "permit@example.invalid")
    sandbox = source / "sandbox"
    sandbox.mkdir()
    (sandbox / "tracked.txt").write_text("original permit fixture\n", encoding="utf-8")
    (source / "outside.txt").write_text("outside granted paths\n", encoding="utf-8")
    _git(source, "add", "sandbox/tracked.txt", "outside.txt")
    _git(source, "commit", "-m", "permit fixture")
    revision = _git(source, "rev-parse", "HEAD")
    (sandbox / "source-untracked.txt").write_text(
        "must never enter the workspace\n",
        encoding="utf-8",
    )
    return source, revision


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _install_completion_crash_trigger(db_session: Session) -> None:
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION phase4_test_fail_permit_completion()
            RETURNS trigger AS $$
            BEGIN
                IF NEW.event_type = 'side_effect_permit_completed' THEN
                    RAISE EXCEPTION 'synthetic completion crash'
                        USING ERRCODE = '40001';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
    )
    db_session.execute(
        text(
            """
            CREATE TRIGGER phase4_test_fail_permit_completion
            BEFORE INSERT ON runner_job_events
            FOR EACH ROW EXECUTE FUNCTION phase4_test_fail_permit_completion()
            """
        )
    )
    db_session.commit()


def _remove_completion_crash_trigger(db_session: Session) -> None:
    db_session.execute(
        text("DROP TRIGGER IF EXISTS phase4_test_fail_permit_completion ON runner_job_events")
    )
    db_session.execute(text("DROP FUNCTION IF EXISTS phase4_test_fail_permit_completion()"))
    db_session.commit()
