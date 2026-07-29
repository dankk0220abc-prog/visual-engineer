from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_workspace_api import (
    INITIAL_TREE_HASH,
    REVISION,
    WORKSPACE_CAPABILITIES,
    acquire_side_effect_permit,
    claim_start,
    complete,
    create_and_approve_grant,
    governed_validation_result,
    register_workspace_runner,
    runner_headers,
    seed_approved_plan,
)
from visual_engineer_api.models.workspace import Workspace, WorkspaceCheckpoint


@dataclass(frozen=True)
class SuiteContext:
    runner: dict[str, Any]
    token: str
    repository: dict[str, Any]
    plan_id: str
    workspace_id: str
    checkpoint_id: str
    checkpoint_fingerprint: str
    grant_id: str
    idempotency_key: str
    suite_run: dict[str, Any]


def _prepare_suite(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> SuiteContext:
    runner, token, repository = register_workspace_runner(
        client,
        runner_bootstrap_token,
        name="Phase 5 Suite test Runner",
    )
    heartbeat = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(token),
        json={
            "runner_id": runner["runner_id"],
            "protocol_version": 1,
            "software_version": "0.5.0-suite",
            "capabilities": [*WORKSPACE_CAPABILITIES, "validation_execute_v1"],
        },
    )
    assert heartbeat.status_code == 200, heartbeat.text
    plan = seed_approved_plan(db_session)
    implementation_grant = create_and_approve_grant(
        client,
        plan.id,
        repository["repository_handle_id"],
    )
    created_workspace = client.post(
        "/api/v1/workspaces",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={"grant_id": implementation_grant["id"]},
    )
    assert created_workspace.status_code == 201, created_workspace.text
    workspace_id = cast(str, created_workspace.json()["workspace"]["id"])
    prepare_job_id = cast(str, created_workspace.json()["job"]["id"])
    assignment, identity = claim_start(
        client,
        runner,
        token,
        prepare_job_id,
    )
    permit = acquire_side_effect_permit(
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
            "workspace_fingerprint": hashlib.sha256(b"suite-workspace").hexdigest(),
            "initial_tree_hash": INITIAL_TREE_HASH,
            "current_tree_hash": INITIAL_TREE_HASH,
            "side_effect_permit_id": permit["id"],
        },
    )

    checkpoint_fingerprint = hashlib.sha256(b"suite-checkpoint").hexdigest()
    workspace = db_session.get(Workspace, uuid.UUID(workspace_id))
    assert workspace is not None
    workspace.current_tree_hash = checkpoint_fingerprint
    workspace.changed_file_count = 1
    workspace.state = "sealed"
    workspace.sealed_at = datetime.now(UTC)
    checkpoint = WorkspaceCheckpoint(
        workspace_id=workspace.id,
        sequence=1,
        source_revision=REVISION,
        tree_fingerprint=checkpoint_fingerprint,
        diff_hash=hashlib.sha256(b"suite diff").hexdigest(),
        changed_paths=["sandbox/original.txt"],
        changed_file_count=1,
        total_diff_bytes=len(b"suite diff"),
        diff_artifact="suite diff",
    )
    db_session.add(checkpoint)
    db_session.commit()
    db_session.refresh(checkpoint)

    pending_grant = client.post(
        "/api/v1/execution-grants",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={
            "plan_id": str(plan.id),
            "repository_handle_id": repository["repository_handle_id"],
            "validation_checkpoint_id": str(checkpoint.id),
            "validation_suite_id": "fixture-integrity-suite-v1",
            "validation_suite_version": 1,
        },
    )
    assert pending_grant.status_code == 201, pending_grant.text
    grant = cast(dict[str, Any], pending_grant.json())
    assert grant["allowed_validation_suites"] == ["fixture-integrity-suite-v1:v1"]
    assert grant["allowed_validation_profiles"] == [
        "fixture-python-stdlib-v1:v1",
        "fixture-python-manifest-v1:v1",
    ]
    approved = client.post(
        f"/api/v1/execution-grants/{grant['id']}/decisions",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={
            "decision": "approve",
            "reason": "Exact immutable Suite scope approved.",
        },
    )
    assert approved.status_code == 200, approved.text

    idempotency_key = f"suite-create-{uuid.uuid4()}"
    created_suite = client.post(
        "/api/v1/validation-suite-runs",
        headers={"Idempotency-Key": idempotency_key},
        json={
            "execution_grant_id": grant["id"],
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
        },
    )
    assert created_suite.status_code == 201, created_suite.text
    return SuiteContext(
        runner=runner,
        token=token,
        repository=repository,
        plan_id=str(plan.id),
        workspace_id=workspace_id,
        checkpoint_id=str(checkpoint.id),
        checkpoint_fingerprint=checkpoint_fingerprint,
        grant_id=cast(str, grant["id"]),
        idempotency_key=idempotency_key,
        suite_run=cast(dict[str, Any], created_suite.json()),
    )


def _complete_step(
    client: TestClient,
    context: SuiteContext,
    suite_run: dict[str, Any],
    *,
    sequence: int,
    exit_code: int,
    output_bytes: int | None = None,
    output_truncated: bool = False,
    synchronize_suite: bool = True,
) -> dict[str, Any]:
    step = next(item for item in suite_run["steps"] if item["sequence"] == sequence)
    assignment, identity = claim_start(
        client,
        context.runner,
        context.token,
        step["runner_job_id"],
    )
    permit = acquire_side_effect_permit(
        client,
        context.token,
        assignment,
        identity,
    )
    is_manifest = sequence == 2
    result = governed_validation_result(
        assignment,
        permit,
        {
            "kind": "validation_execute_v1",
            "validation_run_id": step["validation_run_id"],
            "workspace_id": context.workspace_id,
            "checkpoint_id": context.checkpoint_id,
            "checkpoint_fingerprint": context.checkpoint_fingerprint,
            "profile_id": (
                "fixture-python-manifest-v1" if is_manifest else "fixture-python-stdlib-v1"
            ),
            "profile_version": 1,
            "fixed_argv": [
                "python",
                "-I",
                "-S",
                "<system-owned-fixture-validator>",
                *(["<system-owned-profile-mode>"] if is_manifest else []),
            ],
            "started_at": "2026-07-30T01:00:00Z",
            "completed_at": "2026-07-30T01:00:01Z",
            "duration_ms": 50,
            "exit_code": exit_code,
            "stdout": (
                "x" * output_bytes
                if output_bytes is not None
                else "VE_VALIDATION_PROFILE_MANIFEST_PASS\n"
                if is_manifest and exit_code == 0
                else "VE_VALIDATION_PROFILE_PASS\n"
                if exit_code == 0
                else ""
            ),
            "stderr": ("" if exit_code == 0 else "VE_VALIDATION_PROFILE_MANIFEST_MISMATCH\n"),
            "stdout_truncated": output_truncated,
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
    )
    completed = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{step['runner_job_id']}/complete",
        headers=runner_headers(context.token),
        json={**identity, "result": result},
    )
    assert completed.status_code == 200, completed.text
    if not synchronize_suite:
        return suite_run
    synchronized = client.get(f"/api/v1/validation-suite-runs/{suite_run['id']}")
    assert synchronized.status_code == 200, synchronized.text
    return cast(dict[str, Any], synchronized.json())


def _new_suite_grant(client: TestClient, context: SuiteContext) -> dict[str, Any]:
    revoked = client.post(
        f"/api/v1/execution-grants/{context.grant_id}/revoke",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoked"
    pending = client.post(
        "/api/v1/execution-grants",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={
            "plan_id": context.plan_id,
            "repository_handle_id": context.repository["repository_handle_id"],
            "validation_checkpoint_id": context.checkpoint_id,
            "validation_suite_id": "fixture-integrity-suite-v1",
            "validation_suite_version": 1,
        },
    )
    assert pending.status_code == 201, pending.text
    grant = cast(dict[str, Any], pending.json())
    approved = client.post(
        f"/api/v1/execution-grants/{grant['id']}/decisions",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json={"decision": "approve", "reason": "Fresh retry authority approved."},
    )
    assert approved.status_code == 200, approved.text
    return grant


def test_suite_catalog_and_request_contract_reject_injection(
    client: TestClient,
) -> None:
    catalog = client.get("/api/v1/validation-suites")
    assert catalog.status_code == 200, catalog.text
    payload = catalog.json()
    assert payload["total"] == 1
    assert [step["step_id"] for step in payload["items"][0]["steps"]] == [
        "fixture-contract",
        "fixture-manifest",
    ]
    assert payload["items"][0]["failure_policy"] == "fail_fast"
    assert payload["items"][0]["artifact_content_transfer"] is False

    for injected in (
        {"suite_id": "unknown-suite", "suite_version": 1},
        {"suite_id": "fixture-integrity-suite-v1", "suite_version": 2},
        {
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
            "steps": [{"command": "pytest"}],
        },
        {
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
            "steps": [
                {
                    "sequence": 2,
                    "profile_id": "arbitrary-profile",
                },
                {
                    "sequence": 1,
                    "profile_id": "fixture-python-stdlib-v1",
                },
            ],
        },
        {
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
            "steps": [
                {
                    "sequence": 1,
                    "profile_id": "fixture-python-stdlib-v1",
                },
                {
                    "sequence": 1,
                    "profile_id": "fixture-python-stdlib-v1",
                },
            ],
        },
        {
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
            "command": "pytest",
            "argv": ["pytest"],
            "env": {"TOKEN": "forbidden"},
            "cwd": "/tmp",
        },
    ):
        response = client.post(
            "/api/v1/validation-suite-runs",
            headers={"Idempotency-Key": str(uuid.uuid4())},
            json={"execution_grant_id": str(uuid.uuid4()), **injected},
        )
        assert response.status_code == 422


def test_suite_serial_success_aggregate_and_direct_profile_bypass_denial(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    created = context.suite_run
    assert [step["state"] for step in created["steps"]] == ["queued", "pending"]
    assert created["steps"][1]["validation_run_id"] is None
    replay = client.post(
        "/api/v1/validation-suite-runs",
        headers={"Idempotency-Key": context.idempotency_key},
        json={
            "execution_grant_id": context.grant_id,
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
        },
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["id"] == created["id"]
    conflict = client.post(
        "/api/v1/validation-suite-runs",
        headers={"Idempotency-Key": context.idempotency_key},
        json={
            "execution_grant_id": str(uuid.uuid4()),
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
        },
    )
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["code"] == "suite_idempotency_conflict"

    direct_bypass = client.post(
        "/api/v1/validation-runs",
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "execution_grant_id": context.grant_id,
            "profile_id": "fixture-python-manifest-v1",
        },
    )
    assert direct_bypass.status_code == 422
    assert direct_bypass.json()["error"]["code"] == "validation_suite_dispatch_required"

    after_first = _complete_step(
        client,
        context,
        created,
        sequence=1,
        exit_code=0,
    )
    assert [step["state"] for step in after_first["steps"]] == [
        "succeeded",
        "queued",
    ]
    assert after_first["steps"][1]["validation_run_id"] is not None
    completed = _complete_step(
        client,
        context,
        after_first,
        sequence=2,
        exit_code=0,
    )
    assert completed["state"] == "succeeded"
    assert completed["result"]["verdict"] == "succeeded"
    assert completed["result"]["artifact_count"] == 0
    assert completed["result"]["cleanup_succeeded"] is True
    assert completed["result"]["source_invariant"] is True
    assert completed["result"]["canonical_workspace_invariant"] is True
    assert len(completed["result"]["evidence_references"]) == 2
    timeline = client.get(f"/api/v1/validation-suite-runs/{completed['id']}/timeline")
    aggregate = client.get(f"/api/v1/validation-suite-runs/{completed['id']}/result")
    assert timeline.status_code == 200
    assert aggregate.status_code == 200
    assert (
        aggregate.json()["result"]["aggregate_digest"] == (completed["result"]["aggregate_digest"])
    )
    revoked = client.post(
        f"/api/v1/execution-grants/{context.grant_id}/revoke",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert revoked.status_code == 200, revoked.text
    denied_after_revocation = client.post(
        "/api/v1/validation-suite-runs",
        headers={"Idempotency-Key": f"revoked-suite-{uuid.uuid4()}"},
        json={
            "execution_grant_id": context.grant_id,
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
        },
    )
    assert denied_after_revocation.status_code == 409, denied_after_revocation.text
    assert denied_after_revocation.json()["error"]["code"] == "validation_grant_inactive"


def test_suite_partial_failure_retry_reuses_success_without_redispatch(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    after_first = _complete_step(
        client,
        context,
        context.suite_run,
        sequence=1,
        exit_code=0,
    )
    failed = _complete_step(
        client,
        context,
        after_first,
        sequence=2,
        exit_code=1,
    )
    assert failed["state"] == "failed"
    assert failed["steps"][0]["state"] == "succeeded"
    original_first_run = failed["steps"][0]["validation_run_id"]
    original_first_evidence = failed["steps"][0]["evidence_id"]

    stale_grant_retry = client.post(
        f"/api/v1/validation-suite-runs/{failed['id']}/retry",
        headers={"Idempotency-Key": f"suite-retry-stale-{uuid.uuid4()}"},
        json={"execution_grant_id": context.grant_id},
    )
    assert stale_grant_retry.status_code == 422, stale_grant_retry.text
    assert stale_grant_retry.json()["error"]["code"] == "validation_suite_new_grant_required"

    new_grant = _new_suite_grant(client, context)
    retried = client.post(
        f"/api/v1/validation-suite-runs/{failed['id']}/retry",
        headers={"Idempotency-Key": f"suite-retry-{uuid.uuid4()}"},
        json={"execution_grant_id": new_grant["id"]},
    )
    assert retried.status_code == 201, retried.text
    retry_payload = retried.json()
    assert retry_payload["attempt_number"] == 2
    assert retry_payload["steps"][0]["state"] == "succeeded"
    assert retry_payload["steps"][0]["validation_run_id"] == original_first_run
    assert retry_payload["steps"][0]["evidence_id"] == original_first_evidence
    assert retry_payload["steps"][0]["reused_from_step_run_id"] is not None
    assert retry_payload["steps"][0]["output_bytes"] == 0
    assert retry_payload["steps"][1]["state"] == "queued"
    assert retry_payload["steps"][1]["validation_run_id"] != failed["steps"][1]["validation_run_id"]

    succeeded = _complete_step(
        client,
        context,
        retry_payload,
        sequence=2,
        exit_code=0,
    )
    assert succeeded["state"] == "succeeded"
    assert succeeded["result"]["verdict"] == "succeeded"
    assert succeeded["result"]["evidence_references"][0]["reused"] is True


def test_suite_cancel_prevents_later_step_dispatch(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    cancelled = client.post(
        f"/api/v1/validation-suite-runs/{context.suite_run['id']}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert cancelled.status_code == 200, cancelled.text
    payload = cancelled.json()
    assert payload["state"] == "cancelled"
    assert [step["state"] for step in payload["steps"]] == [
        "cancelled",
        "cancelled",
    ]
    assert payload["steps"][1]["validation_run_id"] is None
    assert payload["result"]["verdict"] == "cancelled"
    assert payload["result"]["evidence_references"] == []
    with pytest.raises(DBAPIError):
        db_session.execute(
            text(
                "UPDATE validation_suite_runs SET state = 'running', "
                "completed_at = NULL WHERE id = :suite_run_id"
            ),
            {"suite_run_id": payload["id"]},
        )
    db_session.rollback()
    unchanged = client.get(f"/api/v1/validation-suite-runs/{payload['id']}")
    assert unchanged.status_code == 200
    assert unchanged.json()["state"] == "cancelled"


def test_suite_cancel_wins_before_completed_child_can_dispatch_next_step(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    _complete_step(
        client,
        context,
        context.suite_run,
        sequence=1,
        exit_code=0,
        synchronize_suite=False,
    )

    cancelled = client.post(
        f"/api/v1/validation-suite-runs/{context.suite_run['id']}/cancel",
        headers={"X-Request-ID": str(uuid.uuid4())},
    )
    assert cancelled.status_code == 200, cancelled.text
    payload = cancelled.json()
    assert payload["state"] == "cancelled"
    assert [step["state"] for step in payload["steps"]] == [
        "succeeded",
        "cancelled",
    ]
    assert payload["steps"][1]["validation_run_id"] is None
    assert payload["result"]["verdict"] == "cancelled"
    assert len(payload["result"]["evidence_references"]) == 1


def test_suite_timeout_cancels_active_child_before_terminalizing(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    active_child_id = context.suite_run["steps"][0]["validation_run_id"]
    db_session.execute(
        text(
            "UPDATE validation_suite_runs "
            "SET deadline_at = now() - interval '1 second' "
            "WHERE id = :suite_run_id"
        ),
        {"suite_run_id": context.suite_run["id"]},
    )
    db_session.commit()

    synchronized = client.get(f"/api/v1/validation-suite-runs/{context.suite_run['id']}")
    assert synchronized.status_code == 200, synchronized.text
    payload = synchronized.json()
    assert payload["state"] == "timed_out"
    assert payload["error_code"] == "validation_suite_timed_out"
    assert [step["state"] for step in payload["steps"]] == ["cancelled", "skipped"]
    assert payload["steps"][1]["validation_run_id"] is None
    assert payload["result"]["verdict"] == "timed_out"

    child = client.get(f"/api/v1/validation-runs/{active_child_id}")
    assert child.status_code == 200, child.text
    assert child.json()["state"] == "cancelled"


@pytest.mark.parametrize(
    ("failure_code", "expected_state"),
    [
        ("validation_timed_out", "timed_out"),
        ("validation_cleanup_failed", "recovery_required"),
    ],
)
def test_suite_step_timeout_and_cleanup_recovery_fail_fast(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    failure_code: str,
    expected_state: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    first_step = context.suite_run["steps"][0]
    assignment, identity = claim_start(
        client,
        context.runner,
        context.token,
        first_step["runner_job_id"],
    )
    permit = acquire_side_effect_permit(
        client,
        context.token,
        assignment,
        identity,
    )
    failed = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{first_step['runner_job_id']}/fail",
        headers=runner_headers(context.token),
        json={
            **identity,
            "error_code": failure_code,
            "error_message": None,
            "side_effect_permit_id": permit["id"],
        },
    )
    assert failed.status_code == 200, failed.text

    synchronized = client.get(f"/api/v1/validation-suite-runs/{context.suite_run['id']}")
    assert synchronized.status_code == 200, synchronized.text
    payload = synchronized.json()
    assert payload["state"] == expected_state
    assert [step["state"] for step in payload["steps"]] == [
        expected_state,
        "skipped",
    ]
    assert payload["steps"][1]["validation_run_id"] is None
    assert payload["result"]["verdict"] == expected_state
    assert payload["result"]["evidence_references"] == []
    assert payload["result"]["canonical_workspace_invariant"] is True

    db_session.expire_all()
    workspace = db_session.get(Workspace, uuid.UUID(context.workspace_id))
    assert workspace is not None
    assert workspace.current_tree_hash == context.checkpoint_fingerprint


@pytest.mark.parametrize(
    ("second_output_bytes", "expected_state"),
    [(1808, "succeeded"), (1809, "failed")],
    ids=["exact-suite-output-limit", "suite-output-limit-plus-one"],
)
def test_suite_aggregate_output_exact_limit_and_plus_one(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    second_output_bytes: int,
    expected_state: str,
) -> None:
    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    after_first = _complete_step(
        client,
        context,
        context.suite_run,
        sequence=1,
        exit_code=0,
        output_bytes=8192,
        output_truncated=True,
    )
    terminal = _complete_step(
        client,
        context,
        after_first,
        sequence=2,
        exit_code=0,
        output_bytes=second_output_bytes,
    )
    assert terminal["combined_output_bytes"] == 8192 + second_output_bytes
    assert terminal["state"] == expected_state
    assert terminal["result"]["verdict"] == expected_state
    if expected_state == "succeeded":
        assert terminal["combined_output_bytes"] == terminal["total_output_bytes"]
        assert terminal["error_code"] is None
    else:
        assert terminal["error_code"] == "validation_suite_output_limit_exceeded"
        assert terminal["result"]["verdict"] != "succeeded"
