import json
import os
import time
import urllib.request
import uuid
from typing import Any

API_BASE_URL = os.environ.get("RUNNER_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = float(os.environ.get("RUNNER_SMOKE_TIMEOUT", "30"))


def request_json(path: str, *, method: str = "GET", payload: object | None = None) -> Any:
    body = (
        json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload is not None else None
    )
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid.uuid4()),
        },
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def main() -> None:
    job = request_json(
        "/api/v1/runner-jobs",
        method="POST",
        payload={"kind": "system_diagnostic_v1"},
    )
    if not isinstance(job, dict) or not isinstance(job.get("id"), str):
        raise SystemExit("Runner smoke dispatch returned an invalid Job")
    job_id = job["id"]
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        current = request_json(f"/api/v1/runner-jobs/{job_id}")
        if isinstance(current, dict) and current.get("state") == "succeeded":
            envelope = current.get("permission_envelope", {})
            result = current.get("result", {})
            if (
                envelope.get("repository_access") != "none"
                or envelope.get("shell_access") is not False
                or envelope.get("network_policy") != "control_plane_only"
            ):
                raise SystemExit("Runner smoke Envelope expanded authority")
            prohibited = {"hostname", "username", "ip", "environment", "path", "files"}
            if not isinstance(result, dict) or prohibited & set(result):
                raise SystemExit("Runner smoke result violated redaction")
            print(f"Runner smoke succeeded: Job {job_id[:8]}")
            return
        if isinstance(current, dict) and current.get("state") in {"failed", "cancelled"}:
            raise SystemExit(f"Runner smoke Job ended as {current.get('state')}")
        time.sleep(0.25)
    raise SystemExit("Runner smoke Job did not complete before timeout")


if __name__ == "__main__":
    main()
