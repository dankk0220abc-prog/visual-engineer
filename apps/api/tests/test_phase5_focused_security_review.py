from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from test_workspace_api import (
    INITIAL_TREE_HASH,
    REVISION,
    WORKSPACE_CAPABILITIES,
    acquire_side_effect_permit,
    claim_start,
    complete,
    create_and_approve_grant,
    register_workspace_runner,
    runner_headers,
    seed_approved_plan,
)
from visual_engineer_api.models.workspace import Workspace, WorkspaceCheckpoint


@dataclass(frozen=True)
class _ValidationJobContext:
    token: str
    job_id: str
    identity: dict[str, str]
    validation_run_id: str
    workspace_id: str
    checkpoint_id: str
    checkpoint_fingerprint: str
    permit_id: str


def _prepare_validation_job(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> _ValidationJobContext:
    runner, token, repository = register_workspace_runner(
        client,
        runner_bootstrap_token,
        name="Phase 5 independent focused security audit runner",
    )
    validation_capabilities = [*WORKSPACE_CAPABILITIES, "validation_execute_v1"]
    heartbeat = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(token),
        json={
            "runner_id": runner["runner_id"],
            "protocol_version": 1,
            "software_version": "0.5.0-audit",
            "capabilities": validation_capabilities,
        },
    )
    assert heartbeat.status_code == 200, heartbeat.text

    plan = seed_approved_plan(db_session)
    implementation_grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    created = client.post(
        "/api/v1/workspaces",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={"grant_id": implementation_grant["id"]},
    )
    assert created.status_code == 201, created.text
    workspace_id = cast(str, created.json()["workspace"]["id"])
    prepare_job_id = cast(str, created.json()["job"]["id"])
    assignment, identity = claim_start(
        client,
        runner,
        token,
        prepare_job_id,
    )
    prepare_permit = acquire_side_effect_permit(
        client,
        token,
        assignment,
        identity,
    )
    complete(
        client,
        token,
        prepare_job_id,
        identity,
        {
            "kind": "workspace_prepare_v1",
            "workspace_id": workspace_id,
            "repository_handle_id": repository["repository_handle_id"],
            "source_revision": REVISION,
            "workspace_fingerprint": hashlib.sha256(b"phase5-audit-workspace").hexdigest(),
            "initial_tree_hash": INITIAL_TREE_HASH,
            "current_tree_hash": INITIAL_TREE_HASH,
            "side_effect_permit_id": prepare_permit["id"],
        },
    )

    checkpoint_fingerprint = hashlib.sha256(b"phase5-audit-validation-checkpoint").hexdigest()
    persisted_workspace = db_session.get(Workspace, uuid.UUID(workspace_id))
    assert persisted_workspace is not None
    persisted_workspace.current_tree_hash = checkpoint_fingerprint
    persisted_workspace.changed_file_count = 1
    persisted_workspace.state = "sealed"
    persisted_workspace.sealed_at = datetime.now(UTC)
    persisted_checkpoint = WorkspaceCheckpoint(
        workspace_id=persisted_workspace.id,
        sequence=1,
        source_revision=REVISION,
        tree_fingerprint=checkpoint_fingerprint,
        diff_hash=hashlib.sha256(b"phase5 audit validation diff").hexdigest(),
        changed_paths=["sandbox/original.txt"],
        changed_file_count=1,
        total_diff_bytes=len(b"phase5 audit validation diff"),
        diff_artifact="phase5 audit validation diff",
    )
    db_session.add(persisted_checkpoint)
    db_session.commit()
    db_session.refresh(persisted_checkpoint)

    pending_grant = client.post(
        "/api/v1/execution-grants",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={
            "plan_id": str(plan.id),
            "repository_handle_id": repository["repository_handle_id"],
            "validation_checkpoint_id": str(persisted_checkpoint.id),
            "validation_profile_id": "fixture-python-stdlib-v1",
        },
    )
    assert pending_grant.status_code == 201, pending_grant.text
    validation_grant = cast(dict[str, Any], pending_grant.json())
    approved = client.post(
        f"/api/v1/execution-grants/{validation_grant['id']}/decisions",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={
            "decision": "approve",
            "reason": "Independent focused audit exact validation scope.",
        },
    )
    assert approved.status_code == 200, approved.text

    created_run = client.post(
        "/api/v1/validation-runs",
        headers={"Idempotency-Key": f"phase5-focused-audit-{uuid.uuid4()}"},
        json={
            "execution_grant_id": validation_grant["id"],
            "profile_id": "fixture-python-stdlib-v1",
        },
    )
    assert created_run.status_code == 201, created_run.text
    validation_run = cast(dict[str, Any], created_run.json())
    assignment, identity = claim_start(
        client,
        runner,
        token,
        validation_run["runner_job_id"],
    )
    permit = acquire_side_effect_permit(client, token, assignment, identity)
    return _ValidationJobContext(
        token=token,
        job_id=cast(str, validation_run["runner_job_id"]),
        identity=identity,
        validation_run_id=cast(str, validation_run["id"]),
        workspace_id=workspace_id,
        checkpoint_id=str(persisted_checkpoint.id),
        checkpoint_fingerprint=checkpoint_fingerprint,
        permit_id=cast(str, permit["id"]),
    )


def _valid_result(context: _ValidationJobContext) -> dict[str, Any]:
    return {
        "kind": "validation_execute_v1",
        "validation_run_id": context.validation_run_id,
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
        "started_at": "2026-07-29T01:00:00Z",
        "completed_at": "2026-07-29T01:00:01Z",
        "duration_ms": 50,
        "exit_code": 0,
        "stdout": "VE_VALIDATION_PROFILE_PASS\n",
        "stderr": "",
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
        "side_effect_permit_id": context.permit_id,
    }


def _post_completion(
    client: TestClient,
    context: _ValidationJobContext,
    *,
    identity: dict[str, str] | None = None,
    result: dict[str, Any] | None = None,
):
    return client.post(
        f"/api/v1/runner-protocol/v1/jobs/{context.job_id}/complete",
        headers=runner_headers(context.token),
        json={
            **(identity or context.identity),
            "result": result or _valid_result(context),
        },
    )


def test_phase5_aud_004_attempt_lease_permit_and_grant_fencing(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """P5-AUD-004: outer result identity and Permit/Grant fencing stay closed."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)

    stale_attempt = {
        **context.identity,
        "attempt_id": str(uuid.uuid4()),
    }
    assert _post_completion(client, context, identity=stale_attempt).status_code == 409

    stale_lease = {
        **context.identity,
        "lease_id": str(uuid.uuid4()),
    }
    assert _post_completion(client, context, identity=stale_lease).status_code == 409

    wrong_permit = {
        **_valid_result(context),
        "side_effect_permit_id": str(uuid.uuid4()),
    }
    assert _post_completion(client, context, result=wrong_permit).status_code == 409


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("validation_run_id", lambda: str(uuid.uuid4())),
        ("workspace_id", lambda: str(uuid.uuid4())),
        ("checkpoint_id", lambda: str(uuid.uuid4())),
        ("checkpoint_fingerprint", lambda: hashlib.sha256(b"wrong").hexdigest()),
        ("fixed_argv", lambda: ["python", "python", "python", "python"]),
    ],
)
def test_phase5_aud_005_result_identity_matches_assigned_job(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    field: str,
    value,
) -> None:
    """P5-AUD-005: inner result identity must exactly match the assigned Job."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    forged = {
        **_valid_result(context),
        field: value(),
    }
    response = _post_completion(client, context, result=forged)
    assert response.status_code == 409, response.text


@pytest.mark.parametrize(
    "overrides",
    [
        {"stdout": "x" * 8193},
        {"artifact_count": 1, "artifact_bytes": 1},
    ],
)
def test_phase5_aud_006_result_respects_exact_grant_budgets(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    overrides: dict[str, Any],
) -> None:
    """P5-AUD-006: result output/artifacts must respect the exact Job/Grant budgets."""

    context = _prepare_validation_job(client, db_session, runner_bootstrap_token)
    over_budget = {
        **_valid_result(context),
        **overrides,
    }
    response = _post_completion(client, context, result=over_budget)
    assert response.status_code == 409, response.text
