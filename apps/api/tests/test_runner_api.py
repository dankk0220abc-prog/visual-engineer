import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from visual_engineer_api.models.runner import (
    PermissionEnvelope,
    Runner,
    RunnerJobAttempt,
    RunnerJobEvent,
)
from visual_engineer_api.services.runner import RunnerService


def register_runner(
    client: TestClient,
    bootstrap_token: str,
    *,
    name: str = "Test Local Runner",
) -> tuple[dict[str, Any], str]:
    response = client.post(
        "/api/v1/runner-protocol/v1/register",
        headers={
            "Authorization": f"Bearer {bootstrap_token}",
            "X-Request-ID": str(uuid.uuid4()),
        },
        json={
            "display_name": name,
            "protocol_version": 1,
            "software_version": "0.3.0",
            "capabilities": [
                "system_diagnostic_v1",
                "controlled_wait_v1",
            ],
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return payload, str(payload["runner_token"])


def runner_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": str(uuid.uuid4()),
    }


def heartbeat(client: TestClient, runner: dict[str, Any], token: str) -> None:
    response = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(token),
        json={
            "runner_id": runner["runner_id"],
            "protocol_version": 1,
            "software_version": "0.3.0",
        },
    )
    assert response.status_code == 200, response.text


def create_job(
    client: TestClient,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/runner-jobs",
        headers={"X-Request-ID": str(uuid.uuid4())},
        json=payload or {"kind": "system_diagnostic_v1"},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


def claim_job(
    client: TestClient,
    runner: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/runner-protocol/v1/jobs/claim",
        headers=runner_headers(token),
        json={"runner_id": runner["runner_id"], "wait_seconds": 0},
    )
    assert response.status_code == 200, response.text
    assignment = response.json()["assignment"]
    assert assignment is not None
    return cast(dict[str, Any], assignment)


def lease_payload(runner: dict[str, Any], assignment: dict[str, Any]) -> dict[str, str]:
    return {
        "runner_id": runner["runner_id"],
        "attempt_id": assignment["attempt_id"],
        "lease_id": assignment["lease_id"],
    }


def test_registration_heartbeat_registry_and_token_redaction(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    runner, token = register_runner(client, runner_bootstrap_token)
    heartbeat(client, runner, token)

    registry = client.get("/api/v1/runners")
    assert registry.status_code == 200
    item = registry.json()["items"][0]
    assert item["status"] == "online"
    assert item["capabilities"] == [
        "controlled_wait_v1",
        "system_diagnostic_v1",
    ]
    assert "runner_token" not in registry.text
    assert token not in registry.text
    assert token not in caplog.text

    db_session.expire_all()
    durable = db_session.get(Runner, runner["runner_id"])
    assert durable is not None
    assert durable.token_digest != token
    assert len(durable.token_digest) == 64

    first_count = db_session.scalar(select(func.count()).select_from(RunnerJobEvent))
    heartbeat(client, runner, token)
    heartbeat(client, runner, token)
    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(RunnerJobEvent)) == first_count


def test_diagnostic_job_full_lifecycle_and_idempotent_complete(
    client: TestClient,
    runner_bootstrap_token: str,
) -> None:
    runner, token = register_runner(client, runner_bootstrap_token)
    heartbeat(client, runner, token)
    job = create_job(client)
    assert job["permission_envelope"]["repository_access"] == "none"
    assert job["permission_envelope"]["shell_access"] is False
    assert job["permission_envelope"]["network_policy"] == "control_plane_only"
    assignment = claim_job(client, runner, token)
    identity = lease_payload(runner, assignment)

    start = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/start",
        headers=runner_headers(token),
        json=identity,
    )
    assert start.status_code == 200
    assert start.json()["state"] == "running"

    renew_headers = runner_headers(token)
    renew = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/renew",
        headers=renew_headers,
        json=identity,
    )
    assert renew.status_code == 200
    replay = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/renew",
        headers=renew_headers,
        json=identity,
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True

    started = datetime.now(UTC)
    result = {
        "kind": "system_diagnostic_v1",
        "runner_software_version": "0.3.0",
        "protocol_version": 1,
        "python_version": "3.12.13",
        "os_family": "linux",
        "architecture": "arm64",
        "capability_list": [
            "controlled_wait_v1",
            "system_diagnostic_v1",
        ],
        "started_at": started.isoformat(),
        "completed_at": (started + timedelta(milliseconds=5)).isoformat(),
        "duration_ms": 5.0,
    }
    complete_headers = runner_headers(token)
    complete = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/complete",
        headers=complete_headers,
        json={**identity, "result": result},
    )
    assert complete.status_code == 200, complete.text
    assert complete.json()["state"] == "succeeded"
    duplicate = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/complete",
        headers=complete_headers,
        json={**identity, "result": result},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["idempotent_replay"] is True
    terminal_cancel = client.post(f"/api/v1/runner-jobs/{job['id']}/cancel")
    assert terminal_cancel.status_code == 409
    assert terminal_cancel.json()["error"]["code"] == "runner_job_terminal"

    durable = client.get(f"/api/v1/runner-jobs/{job['id']}").json()
    assert durable["state"] == "succeeded"
    assert durable["result"]["architecture"] == "arm64"
    assert len(durable["attempts"]) == 1
    assert len(durable["attempts"][0]["lease_id_hint"]) == 8
    assert assignment["lease_id"] not in str(durable)
    events = client.get(f"/api/v1/runner-jobs/{job['id']}/events").json()["items"]
    assert [event["event_type"] for event in events] == [
        "job_created",
        "job_claimed",
        "job_started",
        "lease_renewed",
        "job_succeeded",
    ]


def test_cancel_prevents_success_and_is_idempotent(
    client: TestClient,
    runner_bootstrap_token: str,
) -> None:
    runner, token = register_runner(client, runner_bootstrap_token)
    heartbeat(client, runner, token)
    job = create_job(
        client,
        {"kind": "controlled_wait_v1", "duration_ms": 1000},
    )
    assignment = claim_job(client, runner, token)
    identity = lease_payload(runner, assignment)
    assert (
        client.post(
            f"/api/v1/runner-protocol/v1/jobs/{job['id']}/start",
            headers=runner_headers(token),
            json=identity,
        ).status_code
        == 200
    )

    cancel = client.post(f"/api/v1/runner-jobs/{job['id']}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["state"] == "cancel_requested"
    assert client.post(f"/api/v1/runner-jobs/{job['id']}/cancel").status_code == 200

    now = datetime.now(UTC)
    forbidden_complete = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/complete",
        headers=runner_headers(token),
        json={
            **identity,
            "result": {
                "kind": "controlled_wait_v1",
                "requested_duration_ms": 1000,
                "elapsed_duration_ms": 1000,
                "started_at": now.isoformat(),
                "completed_at": (now + timedelta(seconds=1)).isoformat(),
            },
        },
    )
    assert forbidden_complete.status_code == 409
    assert forbidden_complete.json()["error"]["code"] == "completion_after_cancel"

    cancelled_headers = runner_headers(token)
    cancelled = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/cancelled",
        headers=cancelled_headers,
        json=identity,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"
    duplicate = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/cancelled",
        headers=cancelled_headers,
        json=identity,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["idempotent_replay"] is True


def test_auth_identity_revocation_and_closed_payload_failures(
    client: TestClient,
    runner_bootstrap_token: str,
) -> None:
    bad_bootstrap = client.post(
        "/api/v1/runner-protocol/v1/register",
        headers={"Authorization": "Bearer incorrect-dynamic-token"},
        json={
            "display_name": "Denied",
            "protocol_version": 1,
            "software_version": "0.3.0",
            "capabilities": ["system_diagnostic_v1"],
        },
    )
    assert bad_bootstrap.status_code == 401
    assert (
        client.post(
            "/api/v1/runner-protocol/v1/register",
            json={
                "display_name": "Denied",
                "protocol_version": 1,
                "software_version": "0.3.0",
                "capabilities": ["system_diagnostic_v1"],
            },
        ).status_code
        == 401
    )

    first, first_token = register_runner(client, runner_bootstrap_token, name="First")
    second, second_token = register_runner(client, runner_bootstrap_token, name="Second")
    impersonation = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(first_token),
        json={
            "runner_id": second["runner_id"],
            "protocol_version": 1,
            "software_version": "0.3.0",
        },
    )
    assert impersonation.status_code == 403
    assert (
        client.post(
            "/api/v1/runner-protocol/v1/heartbeat",
            headers=runner_headers("wrong-" + second_token),
            json={
                "runner_id": second["runner_id"],
                "protocol_version": 1,
                "software_version": "0.3.0",
            },
        ).status_code
        == 401
    )
    revoke = client.post(f"/api/v1/runners/{first['runner_id']}/revoke")
    assert revoke.status_code == 200
    assert revoke.json()["status"] == "revoked"
    assert (
        client.post(
            "/api/v1/runner-protocol/v1/heartbeat",
            headers=runner_headers(first_token),
            json={
                "runner_id": first["runner_id"],
                "protocol_version": 1,
                "software_version": "0.3.0",
            },
        ).status_code
        == 403
    )

    assert (
        client.post(
            "/api/v1/runner-jobs",
            json={"kind": "controlled_wait_v1", "duration_ms": 10_001},
        ).status_code
        == 422
    )
    oversized = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(second_token),
        content=b"{" + b'"padding":"' + (b"x" * (64 * 1024)) + b'"}',
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "protocol_payload_too_large"


def test_fenced_identity_and_closed_progress_payload(
    client: TestClient,
    runner_bootstrap_token: str,
) -> None:
    runner, token = register_runner(client, runner_bootstrap_token)
    heartbeat(client, runner, token)
    job = create_job(
        client,
        {"kind": "controlled_wait_v1", "duration_ms": 1000},
    )
    assignment = claim_job(client, runner, token)
    identity = lease_payload(runner, assignment)
    assert (
        client.post(
            f"/api/v1/runner-protocol/v1/jobs/{job['id']}/start",
            headers=runner_headers(token),
            json=identity,
        ).status_code
        == 200
    )

    wrong_attempt = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/renew",
        headers=runner_headers(token),
        json={**identity, "attempt_id": str(uuid.uuid4())},
    )
    assert wrong_attempt.status_code == 409
    assert wrong_attempt.json()["error"]["code"] == "stale_lease"
    wrong_lease = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/renew",
        headers=runner_headers(token),
        json={**identity, "lease_id": str(uuid.uuid4())},
    )
    assert wrong_lease.status_code == 409
    assert wrong_lease.json()["error"]["code"] == "stale_lease"
    arbitrary_metadata = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/events",
        headers=runner_headers(token),
        json={
            **identity,
            "event_type": "progress",
            "sequence": 1,
            "progress_percent": 50,
            "metadata": {"hostname": "forbidden"},
        },
    )
    assert arbitrary_metadata.status_code == 422
    assert arbitrary_metadata.json()["error"]["code"] == "validation_error"
    assert (
        client.post(
            "/api/v1/runner-jobs",
            json={"kind": "system_diagnostic_v1", "command": "whoami"},
        ).status_code
        == 422
    )


def test_lease_expiry_requeue_stale_fencing_retry_budget_and_offline(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    runner, token = register_runner(client, runner_bootstrap_token)
    heartbeat(client, runner, token)
    job = create_job(
        client,
        {"kind": "controlled_wait_v1", "duration_ms": 1000},
    )
    first = claim_job(client, runner, token)
    identity = lease_payload(runner, first)
    assert (
        client.post(
            f"/api/v1/runner-protocol/v1/jobs/{job['id']}/start",
            headers=runner_headers(token),
            json=identity,
        ).status_code
        == 200
    )
    db_session.execute(
        update(RunnerJobAttempt)
        .where(RunnerJobAttempt.id == first["attempt_id"])
        .values(leased_until=datetime.now(UTC) - timedelta(seconds=1))
    )
    db_session.commit()
    result = RunnerService(db_session).reap_expired(request_id="test-reaper-1")
    assert result == {"expired": 1, "requeued": 1, "failed": 0, "offline": 0}

    stale = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/renew",
        headers=runner_headers(token),
        json=identity,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "stale_lease"

    second = claim_job(client, runner, token)
    assert second["attempt_id"] != first["attempt_id"]
    db_session.execute(
        update(RunnerJobAttempt)
        .where(RunnerJobAttempt.id == second["attempt_id"])
        .values(leased_until=datetime.now(UTC) - timedelta(seconds=1))
    )
    db_session.commit()
    exhausted = RunnerService(db_session).reap_expired(request_id="test-reaper-2")
    assert exhausted["failed"] == 1
    assert client.get(f"/api/v1/runner-jobs/{job['id']}").json()["state"] == "failed"

    db_session.execute(
        update(Runner)
        .where(Runner.id == runner["runner_id"])
        .values(
            status="online",
            last_seen_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )
    db_session.commit()
    offline = RunnerService(db_session).reap_expired(request_id="test-reaper-offline")
    assert offline["offline"] == 1
    assert client.get(f"/api/v1/runners/{runner['runner_id']}").json()["status"] == "offline"


def test_permission_envelope_is_immutable_and_result_policy_rejects_secrets(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    runner, token = register_runner(client, runner_bootstrap_token)
    heartbeat(client, runner, token)
    job = create_job(client)
    envelope_id = job["permission_envelope"]["id"]
    with pytest.raises(DBAPIError):
        db_session.execute(
            update(PermissionEnvelope)
            .where(PermissionEnvelope.id == envelope_id)
            .values(shell_access=True)
        )
        db_session.commit()
    db_session.rollback()

    assignment = claim_job(client, runner, token)
    identity = lease_payload(runner, assignment)
    assert (
        client.post(
            f"/api/v1/runner-protocol/v1/jobs/{job['id']}/start",
            headers=runner_headers(token),
            json=identity,
        ).status_code
        == 200
    )
    now = datetime.now(UTC)
    rejected = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{job['id']}/complete",
        headers=runner_headers(token),
        json={
            **identity,
            "result": {
                "kind": "system_diagnostic_v1",
                "runner_software_version": "0.3.0",
                "protocol_version": 1,
                "python_version": "3.12.13",
                "os_family": "linux",
                "architecture": "sk-" + "x" * 24,
                "capability_list": ["system_diagnostic_v1"],
                "started_at": now.isoformat(),
                "completed_at": now.isoformat(),
                "duration_ms": 0,
            },
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "result_rejected"


def test_openapi_has_separate_runner_protocol_and_browser_routes(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    paths = document["paths"]
    for path in (
        "/api/v1/runner-protocol/v1/register",
        "/api/v1/runner-protocol/v1/jobs/claim",
        "/api/v1/runner-protocol/v1/jobs/{job_id}/complete",
        "/api/v1/runners",
        "/api/v1/runner-jobs",
        "/api/v1/runner-jobs/{job_id}/cancel",
    ):
        assert path in paths
    create_schema = paths["/api/v1/runner-jobs"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert "discriminator" in create_schema or "oneOf" in create_schema


def test_no_plaintext_runner_token_column_exists(db_session: Session) -> None:
    columns = db_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'runners' ORDER BY column_name"
        )
    ).scalars()
    names = set(columns)
    assert "token_digest" in names
    assert "runner_token" not in names
    assert "bootstrap_token" not in names
