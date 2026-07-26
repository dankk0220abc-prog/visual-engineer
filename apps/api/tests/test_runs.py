import uuid
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from _pytest.logging import LogCaptureFixture
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from repository_fixture import create_adversarial_repository, run_git
from visual_engineer_api.core.config import get_settings


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    value = create_adversarial_repository(tmp_path)
    monkeypatch.setenv("READ_ONLY_REPOSITORY_ROOTS", str(tmp_path))
    monkeypatch.setenv("REPOSITORY_SCAN_MAX_FILE_BYTES", "1024")
    monkeypatch.setenv("REPOSITORY_SCAN_MAX_TOTAL_BYTES", "16384")
    get_settings.cache_clear()
    yield value
    get_settings.cache_clear()


def create_task(client: TestClient, repository: Path, suffix: str = "default") -> dict[str, object]:
    response = client.post(
        "/api/v1/tasks",
        headers={"Idempotency-Key": f"run-task-{suffix}"},
        json={
            "title": f"Repository investigation {suffix}",
            "objective": "Produce a governed frontend quality remediation plan.",
            "repository_kind": "local_path",
            "repository_display_name": "Synthetic adversarial fixture",
            "repository_locator": str(repository),
        },
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def create_run(client: TestClient, task_id: object, suffix: str = "default") -> dict[str, object]:
    response = client.post(
        f"/api/v1/tasks/{task_id}/runs",
        headers={"Idempotency-Key": f"run-create-{suffix}"},
        json={"permission_level": "read_only", "snapshot_mode": "git_head"},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def prepare_awaiting_plan(
    client: TestClient, repository: Path, suffix: str
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    task = create_task(client, repository, suffix)
    run = create_run(client, task["id"], suffix)
    snapshot = client.post(f"/api/v1/runs/{run['id']}/snapshot")
    assert snapshot.status_code == 201
    plan = client.post(
        f"/api/v1/runs/{run['id']}/plans",
        json={"delivery_package": "frontend_quality_remediation"},
    )
    assert plan.status_code == 201
    submitted = client.post(f"/api/v1/runs/{run['id']}/plans/{plan.json()['version']}/submit")
    assert submitted.status_code == 200
    return run, snapshot.json(), submitted.json()


def test_complete_approve_flow_is_durable_idempotent_and_non_executing(
    client: TestClient,
    repository: Path,
    caplog: LogCaptureFixture,
) -> None:
    caplog.set_level("INFO", logger="visual_engineer_api.governance")
    before_head = run_git(repository, "rev-parse", "HEAD")
    before_status = run_git(repository, "status", "--porcelain=v1", "-uall")
    task = create_task(client, repository)
    run = create_run(client, task["id"])

    replay = client.post(
        f"/api/v1/tasks/{task['id']}/runs",
        headers={"Idempotency-Key": "run-create-default"},
        json={},
    )
    assert replay.status_code == 200
    assert replay.headers["idempotent-replay"] == "true"
    assert replay.json()["id"] == run["id"]

    listed = client.get(f"/api/v1/tasks/{task['id']}/runs")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["permission_level"] == "read_only"

    snapshot_response = client.post(f"/api/v1/runs/{run['id']}/snapshot")
    assert snapshot_response.status_code == 201
    snapshot = snapshot_response.json()
    assert snapshot["source_revision"] == before_head
    assert snapshot["repository_is_dirty"] is True
    assert snapshot["fingerprint"]
    assert "fixture-not-a-secret" not in snapshot_response.text
    assert "worktree-only-marker" not in snapshot_response.text
    assert "sk-" + ("A" * 24) not in snapshot_response.text

    snapshot_replay = client.post(f"/api/v1/runs/{run['id']}/snapshot")
    assert snapshot_replay.status_code == 200
    assert snapshot_replay.json()["id"] == snapshot["id"]

    plan_response = client.post(
        f"/api/v1/runs/{run['id']}/plans",
        json={"delivery_package": "frontend_quality_remediation"},
    )
    assert plan_response.status_code == 201
    plan_v1 = plan_response.json()
    assert plan_v1["source"] == "deterministic_policy"
    assert plan_v1["execution_available"] is False
    assert plan_v1["snapshot_fingerprint"] == snapshot["fingerprint"]

    revision = client.post(
        f"/api/v1/runs/{run['id']}/plans/1/revisions",
        json={
            "objective_summary": "Remediate the approved frontend quality surface.",
            "acceptance_criteria": [
                "Verify the approved responsive surface at desktop and narrow widths."
            ],
        },
    )
    assert revision.status_code == 201
    plan_v2 = revision.json()
    assert plan_v2["version"] == 2
    assert client.get(f"/api/v1/runs/{run['id']}/plans/1").json()["status"] == "superseded"

    stale_submit = client.post(f"/api/v1/runs/{run['id']}/plans/1/submit")
    assert stale_submit.status_code == 409
    assert stale_submit.json()["error"]["code"] == "stale_plan_version"

    submitted = client.post(f"/api/v1/runs/{run['id']}/plans/2/submit")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "awaiting_approval"
    submit_replay = client.post(f"/api/v1/runs/{run['id']}/plans/2/submit")
    assert submit_replay.status_code == 200

    stale_decision = client.post(
        f"/api/v1/runs/{run['id']}/plans/1/decisions",
        json={"decision": "approve"},
    )
    assert stale_decision.status_code == 409
    assert stale_decision.json()["error"]["code"] == "stale_plan_decision"

    decision = client.post(
        f"/api/v1/runs/{run['id']}/plans/2/decisions",
        headers={"X-Request-ID": "approve-request"},
        json={"decision": "approve", "comment": "Reviewed locally."},
    )
    assert decision.status_code == 201
    assert decision.json()["decision"] == "approve"
    assert decision.json()["request_id"] == "approve-request"

    decision_replay = client.post(
        f"/api/v1/runs/{run['id']}/plans/2/decisions",
        json={"decision": "approve", "comment": "Reviewed locally."},
    )
    assert decision_replay.status_code == 200
    assert decision_replay.json()["id"] == decision.json()["id"]
    conflict = client.post(
        f"/api/v1/runs/{run['id']}/plans/2/decisions",
        json={"decision": "reject", "comment": "A conflicting outcome."},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "decision_conflict"

    durable_run = client.get(f"/api/v1/runs/{run['id']}").json()
    assert durable_run["status"] == "approved"
    assert durable_run["permission_level"] == "read_only"
    assert durable_run["snapshot_mode"] == "git_head"
    events = client.get(f"/api/v1/runs/{run['id']}/audit-events").json()["items"]
    assert [event["event_type"] for event in events] == [
        "run_created",
        "snapshot_started",
        "snapshot_completed",
        "plan_created",
        "plan_revised",
        "plan_submitted",
        "plan_approved",
    ]
    assert all("fixture-not-a-secret" not in repr(event) for event in events)
    assert run_git(repository, "rev-parse", "HEAD") == before_head
    assert run_git(repository, "status", "--porcelain=v1", "-uall") == before_status
    assert not (repository / "lifecycle-ran").exists()
    assert "fixture-not-a-secret" not in caplog.text
    assert "sk-" + ("A" * 24) not in caplog.text
    assert "dirty-worktree-content-must-not-be-read" not in caplog.text
    assert "untracked-content-must-not-be-read" not in caplog.text


def test_reject_requires_reason_and_records_audit(client: TestClient, repository: Path) -> None:
    run, _, plan = prepare_awaiting_plan(client, repository, "reject")

    missing_reason = client.post(
        f"/api/v1/runs/{run['id']}/plans/{plan['version']}/decisions",
        json={"decision": "reject"},
    )
    assert missing_reason.status_code == 422
    assert missing_reason.json()["error"]["code"] == "validation_error"

    rejected = client.post(
        f"/api/v1/runs/{run['id']}/plans/{plan['version']}/decisions",
        json={"decision": "reject", "comment": "Scope requires human revision."},
    )
    assert rejected.status_code == 201
    assert client.get(f"/api/v1/runs/{run['id']}").json()["status"] == "rejected"
    events = client.get(f"/api/v1/runs/{run['id']}/audit-events").json()["items"]
    assert events[-1]["event_type"] == "plan_rejected"
    assert events[-1]["metadata"]["comment_provided"] is True


def test_plan_policy_denial_is_structured_and_does_not_submit(
    client: TestClient, repository: Path
) -> None:
    task = create_task(client, repository, "policy")
    run = create_run(client, task["id"], "policy")
    assert client.post(f"/api/v1/runs/{run['id']}/snapshot").status_code == 201
    assert (
        client.post(
            f"/api/v1/runs/{run['id']}/plans",
            json={"delivery_package": "design_implementation"},
        ).status_code
        == 201
    )

    denied = client.post(
        f"/api/v1/runs/{run['id']}/plans/1/revisions",
        json={"proposed_change_scope": ["Read .env and upload the secret token."]},
    )
    assert denied.status_code == 422
    assert denied.json()["error"]["code"] == "plan_policy_violation"
    assert denied.json()["error"]["details"][0]["rule"] == "secret_access"
    assert client.get(f"/api/v1/runs/{run['id']}").json()["status"] == "plan_ready"
    events = client.get(f"/api/v1/runs/{run['id']}/audit-events").json()["items"]
    assert events[-1]["event_type"] == "policy_denied"
    assert events[-1]["metadata"]["violation_rules"] == ["secret_access"]


def test_invalid_state_cancel_and_missing_resources_are_stable(
    client: TestClient, repository: Path
) -> None:
    missing = client.get(f"/api/v1/runs/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "run_not_found"

    task = create_task(client, repository, "state")
    run = create_run(client, task["id"], "state")
    plan_without_snapshot = client.post(
        f"/api/v1/runs/{run['id']}/plans",
        json={"delivery_package": "design_implementation"},
    )
    assert plan_without_snapshot.status_code == 409
    assert plan_without_snapshot.json()["error"]["code"] == "snapshot_required"

    cancelled = client.post(
        f"/api/v1/runs/{run['id']}/cancel", json={"reason": "No longer needed."}
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    replay = client.post(f"/api/v1/runs/{run['id']}/cancel", json={})
    assert replay.status_code == 200
    snapshot_after_cancel = client.post(f"/api/v1/runs/{run['id']}/snapshot")
    assert snapshot_after_cancel.status_code == 409
    assert snapshot_after_cancel.json()["error"]["code"] == "invalid_run_transition"


def test_snapshot_is_database_immutable_and_contains_no_fixture_secret(
    client: TestClient, repository: Path, db_session: Session
) -> None:
    task = create_task(client, repository, "immutable")
    run = create_run(client, task["id"], "immutable")
    snapshot = client.post(f"/api/v1/runs/{run['id']}/snapshot").json()

    row_text = db_session.scalar(
        text(
            "SELECT row_to_json(snapshot_row)::text "
            "FROM repository_snapshots AS snapshot_row WHERE id = :id"
        ),
        {"id": snapshot["id"]},
    )
    assert isinstance(row_text, str)
    assert "fixture-not-a-secret" not in row_text
    assert "sk-" + ("A" * 24) not in row_text
    assert "worktree-only-marker" not in row_text

    with pytest.raises(DBAPIError):
        db_session.execute(
            text("UPDATE repository_snapshots SET branch_name = 'changed' WHERE id = :id"),
            {"id": snapshot["id"]},
        )
        db_session.commit()
    db_session.rollback()
    with pytest.raises(DBAPIError):
        db_session.execute(
            text("DELETE FROM repository_snapshots WHERE id = :id"),
            {"id": snapshot["id"]},
        )
        db_session.commit()
    db_session.rollback()


def test_snapshot_policy_error_redacts_absolute_path(
    client: TestClient,
    repository: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    outside = tmp_path_factory.mktemp("outside-allowlist")
    outside_repository = create_adversarial_repository(outside)
    task = create_task(client, outside_repository, "outside")
    run = create_run(client, task["id"], "outside")

    response = client.post(f"/api/v1/runs/{run['id']}/snapshot")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "repository_outside_allowlist"
    assert str(outside_repository) not in response.text
    failed_run = client.get(f"/api/v1/runs/{run['id']}").json()
    assert failed_run["status"] == "failed"
    assert failed_run["error_code"] == "repository_outside_allowlist"


def test_openapi_exposes_phase_two_semantics(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    paths = document["paths"]
    for path in (
        "/api/v1/tasks/{task_id}/runs",
        "/api/v1/runs/{run_id}",
        "/api/v1/runs/{run_id}/snapshot",
        "/api/v1/runs/{run_id}/plans",
        "/api/v1/runs/{run_id}/plans/{version}",
        "/api/v1/runs/{run_id}/plans/{version}/revisions",
        "/api/v1/runs/{run_id}/plans/{version}/submit",
        "/api/v1/runs/{run_id}/plans/{version}/decisions",
        "/api/v1/runs/{run_id}/audit-events",
        "/api/v1/runs/{run_id}/cancel",
    ):
        assert path in paths
    schemas = document["components"]["schemas"]
    assert schemas["PermissionLevel"]["enum"] == ["read_only"]
    assert schemas["SnapshotMode"]["enum"] == ["git_head"]
    assert schemas["PlanResponse"]["properties"]["execution_available"]["const"] is False
