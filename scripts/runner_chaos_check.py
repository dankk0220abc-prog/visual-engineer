import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

API_BASE_URL = os.environ.get("RUNNER_CHAOS_API_BASE_URL", "http://127.0.0.1:18002").rstrip("/")
PROJECT_NAME = os.environ.get("RUNNER_CHAOS_PROJECT_NAME", "visualengineer-runner-chaos")
TIMEOUT_SECONDS = float(os.environ.get("RUNNER_CHAOS_TIMEOUT", "60"))


def request_json(
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    token: str | None = None,
) -> tuple[int, Any]:
    body = (
        json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
    )
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Request-ID": str(uuid.uuid4()),
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=body,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error_payload: Any = json.load(exc)
        except (json.JSONDecodeError, ValueError):
            error_payload = {}
        return exc.code, error_payload


def require_json(
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
) -> dict[str, Any]:
    status, response = request_json(path, method=method, payload=payload)
    if not 200 <= status < 300 or not isinstance(response, dict):
        raise RuntimeError(f"Control Plane request failed with HTTP {status}")
    return response


def wait_for(
    description: str,
    probe: Callable[[], dict[str, Any]],
    *,
    timeout: float = TIMEOUT_SECONDS,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        candidate = probe()
        if isinstance(candidate, dict):
            last = candidate
            if candidate.get("_ready") is True:
                candidate.pop("_ready", None)
                return candidate
        time.sleep(0.25)
    state = last.get("state") or last.get("status") or "unknown"
    raise RuntimeError(f"Timed out waiting for {description}; last state was {state}")


def compose(*arguments: str) -> str:
    completed = subprocess.run(
        ["docker", "compose", "-p", PROJECT_NAME, *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Docker Compose action failed: {' '.join(arguments)}")
    return completed.stdout


def runner_credential() -> tuple[str, str]:
    output = compose(
        "exec",
        "-T",
        "runner",
        "python",
        "-c",
        (
            "import json;"
            "p=json.load(open('/var/lib/visual-engineer-runner/credentials.json',"
            "encoding='utf-8'));"
            "print(p['runner_id']);print(p['token'])"
        ),
    )
    lines = output.splitlines()
    if len(lines) != 2:
        raise RuntimeError("Runner credential could not be inspected safely")
    uuid.UUID(lines[0])
    if len(lines[1]) < 32:
        raise RuntimeError("Runner credential is malformed")
    return lines[0], lines[1]


def active_lease(job_id: str) -> tuple[str, str]:
    query = (
        "SELECT id::text || ' ' || lease_id::text "
        "FROM runner_job_attempts "
        f"WHERE job_id = '{uuid.UUID(job_id)}' "
        "ORDER BY attempt_number LIMIT 1"
    )
    output = compose(
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        "visualengineer",
        "-d",
        "visualengineer",
        "-At",
        "-c",
        query,
    ).strip()
    fields = output.split()
    if len(fields) != 2:
        raise RuntimeError("Active lease identity was not found")
    uuid.UUID(fields[0])
    uuid.UUID(fields[1])
    return fields[0], fields[1]


def main() -> None:
    runners = wait_for(
        "initial Runner online",
        lambda: _online_runner(require_json("/api/v1/runners")),
    )
    expected_runner_id = runners["id"]
    created = require_json(
        "/api/v1/runner-jobs",
        method="POST",
        payload={"kind": "controlled_wait_v1", "duration_ms": 10_000},
    )
    job_id = str(created["id"])
    running = wait_for(
        "first Attempt running",
        lambda: _job_with_state(job_id, {"running"}),
    )
    if running.get("attempt_count") != 1:
        raise RuntimeError("First Runner Attempt count is not one")

    credential_runner_id, runner_token = runner_credential()
    if credential_runner_id != expected_runner_id:
        raise RuntimeError("Runner credential identity does not match the registry")
    old_attempt_id, old_lease_id = active_lease(job_id)

    compose("stop", "--timeout", "0", "runner")
    wait_for(
        "Runner offline",
        lambda: _runner_with_status(expected_runner_id, "offline"),
    )
    recovered = wait_for(
        "lease expiry and Job requeue",
        lambda: _requeued_job(job_id),
    )
    attempts = recovered.get("attempts")
    if not isinstance(attempts, list) or attempts[0].get("state") != "lease_expired":
        raise RuntimeError("Expired Attempt evidence is missing")

    now = datetime.now(UTC).isoformat()
    stale_status, stale_body = request_json(
        f"/api/v1/runner-protocol/v1/jobs/{job_id}/complete",
        method="POST",
        token=runner_token,
        payload={
            "runner_id": expected_runner_id,
            "attempt_id": old_attempt_id,
            "lease_id": old_lease_id,
            "result": {
                "kind": "controlled_wait_v1",
                "requested_duration_ms": 10_000,
                "elapsed_duration_ms": 10_000,
                "started_at": now,
                "completed_at": now,
            },
        },
    )
    if stale_status != 409 or "stale_lease" not in json.dumps(stale_body):
        raise RuntimeError("Expired lease was not fenced with stable HTTP 409")

    compose("start", "runner")
    second = wait_for(
        "second Attempt",
        lambda: _job_with_attempt_count(job_id, 2),
    )
    if second.get("state") not in {"leased", "running", "succeeded"}:
        raise RuntimeError("Second Attempt did not acquire the requeued Job")
    succeeded = wait_for(
        "recovered Job success",
        lambda: _job_with_state(job_id, {"succeeded"}),
    )
    final_attempts = succeeded.get("attempts")
    if (
        not isinstance(final_attempts, list)
        or len(final_attempts) != 2
        or [item.get("state") for item in final_attempts] != ["lease_expired", "succeeded"]
    ):
        raise RuntimeError("Recovered Job Attempt history is invalid")

    events = require_json(f"/api/v1/runner-jobs/{job_id}/events").get("items")
    event_types = (
        [event.get("event_type") for event in events if isinstance(event, dict)]
        if isinstance(events, list)
        else []
    )
    for required in (
        "lease_expired",
        "job_requeued",
        "job_claimed",
        "job_succeeded",
    ):
        if required not in event_types:
            raise RuntimeError(f"Chaos timeline is missing {required}")
    if event_types.count("job_claimed") != 2:
        raise RuntimeError("Chaos timeline does not show exactly two claims")

    wait_for(
        "Runner recovery online",
        lambda: _runner_with_status(expected_runner_id, "online"),
    )
    print(
        "Runner chaos check passed: offline, lease expiry, requeue, "
        "stale fencing, recovery, and final success."
    )


def _online_runner(payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("status") == "online":
                return {**item, "_ready": True}
    return {"status": "waiting"}


def _runner_with_status(runner_id: str, status: str) -> dict[str, Any]:
    current = require_json(f"/api/v1/runners/{runner_id}")
    return {**current, "_ready": current.get("status") == status}


def _job_with_state(job_id: str, states: set[str]) -> dict[str, Any]:
    current = require_json(f"/api/v1/runner-jobs/{job_id}")
    return {**current, "_ready": current.get("state") in states}


def _job_with_attempt_count(job_id: str, count: int) -> dict[str, Any]:
    current = require_json(f"/api/v1/runner-jobs/{job_id}")
    return {**current, "_ready": current.get("attempt_count", 0) >= count}


def _requeued_job(job_id: str) -> dict[str, Any]:
    current = require_json(f"/api/v1/runner-jobs/{job_id}")
    attempts = current.get("attempts")
    expired = (
        isinstance(attempts, list)
        and len(attempts) == 1
        and isinstance(attempts[0], dict)
        and attempts[0].get("state") == "lease_expired"
    )
    return {
        **current,
        "_ready": current.get("state") == "queued" and expired,
    }


if __name__ == "__main__":
    main()
