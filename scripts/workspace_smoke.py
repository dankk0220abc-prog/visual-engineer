import hashlib
import json
import os
import stat
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
FIXTURE_ROOT = Path(
    os.environ.get(
        "WORKSPACE_FIXTURE_REPOSITORY_PATH",
        Path(__file__).resolve().parents[1] / ".runtime" / "workspace-fixture",
    )
)


class RequestError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(f"{status}:{code}")
        self.status = status
        self.code = code


def request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode()
    headers = {
        "Accept": "application/json",
        "X-Request-ID": request_id or str(uuid.uuid4()),
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(call, timeout=10) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error = json.load(exc)
            code = str(error.get("error", {}).get("code", "request_failed"))
        except (ValueError, AttributeError):
            code = "request_failed"
        raise RequestError(exc.code, code) from exc
    if not isinstance(result, dict):
        raise RequestError(502, "invalid_response")
    return result


def wait_for_job(job_id: str, timeout: float = 90) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = request("GET", f"/api/v1/runner-jobs/{job_id}")
        if job.get("state") in {"succeeded", "failed", "cancelled"}:
            return job
        time.sleep(0.25)
    raise SystemExit(f"Workspace Job {job_id[:8]} timed out")


def require_success(action: dict[str, Any], kind: str) -> dict[str, Any]:
    job = wait_for_job(str(action["job"]["id"]))
    if job.get("state") != "succeeded":
        raise SystemExit(f"{kind} failed with {job.get('error_code', 'unknown_failure')}")
    result = job.get("result")
    if not isinstance(result, dict) or result.get("kind") != kind:
        raise SystemExit(f"{kind} returned an invalid result")
    return result


def require_failure(
    action: dict[str, Any],
    expected_code: str,
) -> None:
    job = wait_for_job(str(action["job"]["id"]))
    if job.get("state") != "failed" or job.get("error_code") != expected_code:
        raise SystemExit(
            f"Expected {expected_code}, got {job.get('state')}:{job.get('error_code')}"
        )


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(FIXTURE_ROOT.rglob("*")):
        relative = path.relative_to(FIXTURE_ROOT).as_posix()
        metadata = path.lstat()
        digest.update(relative.encode())
        digest.update(f":{stat.S_IFMT(metadata.st_mode)}:".encode())
        if path.is_symlink():
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> None:
    before_source = source_fingerprint()
    repositories = request("GET", "/api/v1/repositories").get("items", [])
    fixture = next(
        (item for item in repositories if item.get("opaque_handle") == "fixture-repository-v1"),
        None,
    )
    if fixture is None:
        raise SystemExit("Fixture Repository Handle is unavailable")
    contexts = request("GET", "/api/v1/execution-grants/eligible-contexts").get("items", [])
    context = next(
        (item for item in contexts if item.get("repository_handle_id") == fixture.get("id")),
        None,
    )
    if context is None:
        raise SystemExit("Approved fixture Plan context is unavailable")
    grant = request(
        "POST",
        "/api/v1/execution-grants",
        {
            "plan_id": context["plan_id"],
            "repository_handle_id": fixture["id"],
        },
    )
    if grant["status"] == "pending":
        grant = request(
            "POST",
            f"/api/v1/execution-grants/{grant['id']}/decisions",
            {
                "decision": "approve",
                "reason": "Local Phase 4 smoke approval for the synthetic fixture.",
            },
        )
    if grant["status"] != "approved":
        raise SystemExit(f"Execution Grant is not usable: {grant['status']}")

    workspace_action = request(
        "POST",
        "/api/v1/workspaces",
        {"grant_id": grant["id"]},
    )
    workspace_id = str(workspace_action["workspace"]["id"])
    prepared = require_success(workspace_action, "workspace_prepare_v1")
    if prepared["source_revision"] != fixture["current_revision"]:
        raise SystemExit("Workspace revision does not match the registered source")

    read_action = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/actions/read-text",
        {"relative_path": "sandbox/original.txt", "max_bytes": 32768},
    )
    read_result = require_success(read_action, "workspace_read_text_v1")
    if read_result["content"] != "Original fixture text.\n":
        raise SystemExit("Workspace imported dirty or unexpected source content")

    replace_action = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        {
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": "Updated by the Phase 4 typed tool.\n",
            "expected_sha256": read_result["sha256"],
        },
        request_id=f"smoke-replace-{workspace_id}",
    )
    replace_result = require_success(replace_action, "workspace_write_text_v1")

    duplicate = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        {
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": "Updated by the Phase 4 typed tool.\n",
            "expected_sha256": read_result["sha256"],
        },
        request_id=f"smoke-replace-{workspace_id}",
    )
    if duplicate["job"]["id"] != replace_action["job"]["id"]:
        raise SystemExit("Duplicate write request was not idempotent")

    create_action = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        {
            "mode": "create",
            "relative_path": "sandbox/create-here/smoke-created.txt",
            "content": "Created atomically.\n",
            "expected_absent": True,
        },
    )
    require_success(create_action, "workspace_write_text_v1")

    for path, expected_code in (
        ("sandbox/outside-link", "symlink_denied"),
        ("sandbox/sensitive-link", "symlink_denied"),
    ):
        action = request(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/actions/read-text",
            {"relative_path": path, "max_bytes": 1024},
        )
        require_failure(action, expected_code)

    stale_write = request(
        "POST",
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        {
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": "This stale write must fail.\n",
            "expected_sha256": read_result["sha256"],
        },
    )
    require_failure(stale_write, "content_conflict")

    try:
        request(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/actions/write-text",
            {
                "mode": "create",
                "relative_path": "sandbox/.env",
                "content": "denied",
                "expected_absent": True,
            },
        )
    except RequestError as exc:
        if exc.status != 422 or exc.code != "sensitive_path_denied":
            raise
    else:
        raise SystemExit("Sensitive path was unexpectedly accepted")
    try:
        request(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/actions/read-text",
            {"relative_path": "../outside", "max_bytes": 32},
        )
    except RequestError as exc:
        if exc.status != 422 or exc.code != "validation_error":
            raise
    else:
        raise SystemExit("Traversal path was unexpectedly accepted")

    status_result = require_success(
        request(
            "POST",
            f"/api/v1/workspaces/{workspace_id}/actions/status",
        ),
        "workspace_status_v1",
    )
    if status_result["changed_file_count"] != 2:
        raise SystemExit("Workspace status does not contain the two typed writes")
    diff_result = require_success(
        request("POST", f"/api/v1/workspaces/{workspace_id}/actions/diff"),
        "workspace_diff_v1",
    )
    if "smoke-created.txt" not in diff_result["diff"]:
        raise SystemExit("Bounded diff omitted the created fixture file")
    checkpoints = request("GET", f"/api/v1/workspaces/{workspace_id}/checkpoints").get("items", [])
    if len(checkpoints) < 3:
        raise SystemExit("Expected write and diff Checkpoints")

    rollback_result = require_success(
        request("POST", f"/api/v1/workspaces/{workspace_id}/actions/rollback"),
        "workspace_rollback_v1",
    )
    if not rollback_result["clean"]:
        raise SystemExit("Rollback did not report a clean baseline")
    clean_status = require_success(
        request("POST", f"/api/v1/workspaces/{workspace_id}/actions/status"),
        "workspace_status_v1",
    )
    if clean_status["changed_file_count"] != 0:
        raise SystemExit("Rollback left Workspace changes")
    discard_result = require_success(
        request("POST", f"/api/v1/workspaces/{workspace_id}/actions/discard"),
        "workspace_discard_v1",
    )
    if not discard_result["discarded"]:
        raise SystemExit("Workspace discard did not complete")
    repeated_discard = request("POST", f"/api/v1/workspaces/{workspace_id}/actions/discard")
    if repeated_discard["workspace"]["state"] != "discarded":
        raise SystemExit("Repeated discard was not idempotent")

    after_source = source_fingerprint()
    if before_source != after_source:
        raise SystemExit("Read-only source fixture changed during Workspace smoke")
    print(
        json.dumps(
            {
                "checkpoint_count": len(checkpoints),
                "created_path": "sandbox/create-here/smoke-created.txt",
                "discarded": True,
                "policy_denials": [
                    "sensitive_path_denied",
                    "validation_error",
                    "symlink_denied",
                    "content_conflict",
                ],
                "replace_sha256": replace_result["sha256"],
                "source_unchanged": True,
                "workspace_id": workspace_id,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
