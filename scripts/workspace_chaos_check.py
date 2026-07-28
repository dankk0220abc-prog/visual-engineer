import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from typing import Any

API_BASE_URL = os.environ.get("WORKSPACE_CHAOS_API_BASE_URL", "http://127.0.0.1:18003").rstrip("/")
PROJECT_NAME = os.environ.get("WORKSPACE_CHAOS_PROJECT_NAME", "visualengineer-workspace-chaos")
TIMEOUT_SECONDS = float(os.environ.get("WORKSPACE_CHAOS_TIMEOUT", "90"))
COMPOSE_FILES = ("-f", "compose.yaml", "-f", "infra/compose.workspace.yaml")


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
    call = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(call, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error: Any = json.load(exc)
        except (ValueError, json.JSONDecodeError):
            error = {}
        return exc.code, error


def require_json(
    path: str,
    *,
    method: str = "GET",
    payload: object | None = None,
) -> dict[str, Any]:
    status, result = request_json(path, method=method, payload=payload)
    if not 200 <= status < 300 or not isinstance(result, dict):
        raise RuntimeError(f"Control Plane request failed with HTTP {status}")
    return result


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
        last = candidate
        if candidate.get("_ready") is True:
            candidate.pop("_ready", None)
            return candidate
        time.sleep(0.2)
    state = last.get("state") or last.get("status") or "unknown"
    raise RuntimeError(f"Timed out waiting for {description}; last state was {state}")


def compose(*arguments: str) -> str:
    completed = subprocess.run(
        ["docker", "compose", "-p", PROJECT_NAME, *COMPOSE_FILES, *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
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
        raise RuntimeError("Runner credential could not be inspected")
    uuid.UUID(lines[0])
    if len(lines[1]) < 32:
        raise RuntimeError("Runner credential is malformed")
    return lines[0], lines[1]


def active_lease(job_id: str, attempt_number: int) -> tuple[str, str]:
    query = (
        "SELECT id::text || ' ' || lease_id::text "
        "FROM runner_job_attempts "
        f"WHERE job_id = '{uuid.UUID(job_id)}' AND attempt_number = {attempt_number}"
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


def completed_job(action: dict[str, Any]) -> dict[str, Any]:
    job_id = str(action["job"]["id"])
    return wait_for(
        f"Job {job_id[:8]} completion",
        lambda: job_in_states(job_id, {"succeeded", "failed", "cancelled"}),
    )


def require_success(action: dict[str, Any], kind: str) -> dict[str, Any]:
    job = completed_job(action)
    if job.get("state") != "succeeded":
        raise RuntimeError(f"{kind} ended as {job.get('state')}:{job.get('error_code')}")
    result = job.get("result")
    if not isinstance(result, dict) or result.get("kind") != kind:
        raise RuntimeError(f"{kind} returned an invalid result")
    return result


def inspect_interrupted_write(workspace_id: str, operation_id: str) -> dict[str, Any]:
    script = (
        "import hashlib,json;"
        "from pathlib import Path;"
        f"w=Path('/var/lib/visual-engineer-runner/workspaces/workspace-{uuid.UUID(workspace_id).hex}');"
        "target=w/'sandbox/original.txt';"
        f"temp=w/'sandbox/.visual-engineer-write-{uuid.UUID(operation_id).hex}.tmp';"
        "print(json.dumps({'target_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),"
        "'temp_exists':temp.exists(),'temp_size':temp.stat().st_size if temp.exists() else -1}))"
    )
    output = compose(
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        "python",
        "runner",
        "-c",
        script,
    ).strip()
    value = json.loads(output)
    if not isinstance(value, dict):
        raise RuntimeError("Interrupted Workspace inspection failed")
    return value


def workspace_path_exists(workspace_id: str) -> bool:
    script = (
        "from pathlib import Path;"
        f"print(Path('/var/lib/visual-engineer-runner/workspaces/workspace-{uuid.UUID(workspace_id).hex}').exists())"
    )
    return (
        compose(
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "python",
            "runner",
            "-c",
            script,
        ).strip()
        == "True"
    )


def stale_complete(
    *,
    job_id: str,
    runner_id: str,
    runner_token: str,
    attempt_id: str,
    lease_id: str,
    result: dict[str, Any],
) -> None:
    status, body = request_json(
        f"/api/v1/runner-protocol/v1/jobs/{job_id}/complete",
        method="POST",
        token=runner_token,
        payload={
            "runner_id": runner_id,
            "attempt_id": attempt_id,
            "lease_id": lease_id,
            "result": result,
        },
    )
    if status != 409 or "stale_lease" not in json.dumps(body):
        raise RuntimeError(
            f"Expired Workspace lease was not fenced with stable HTTP 409; got HTTP {status}"
        )


def main() -> None:
    fixture = wait_for("Repository Handle registration", repository_fixture)
    contexts = require_json("/api/v1/execution-grants/eligible-contexts").get("items", [])
    context = next(
        (
            item
            for item in contexts
            if isinstance(item, dict) and item.get("repository_handle_id") == fixture.get("id")
        ),
        None,
    )
    if context is None:
        raise RuntimeError("Approved fixture Plan context is unavailable")
    grant = require_json(
        "/api/v1/execution-grants",
        method="POST",
        payload={
            "plan_id": context["plan_id"],
            "repository_handle_id": fixture["id"],
        },
    )
    if grant["status"] == "pending":
        grant = require_json(
            f"/api/v1/execution-grants/{grant['id']}/decisions",
            method="POST",
            payload={
                "decision": "approve",
                "reason": "Workspace chaos fixture approval.",
            },
        )
    if grant.get("status") != "approved":
        raise RuntimeError("Workspace chaos Execution Grant is not approved")

    runner_id, runner_token = runner_credential()
    created = require_json(
        "/api/v1/workspaces",
        method="POST",
        payload={"grant_id": grant["id"]},
    )
    workspace_id = str(created["workspace"]["id"])
    prepare_job_id = str(created["job"]["id"])
    wait_for(
        "Workspace preparing",
        lambda: workspace_job_running(workspace_id, prepare_job_id),
    )
    prepare_attempt_id, prepare_lease_id = active_lease(prepare_job_id, 1)
    compose("stop", "--timeout", "0", "runner")
    wait_for("first prepare lease expiry and requeue", lambda: requeued_job(prepare_job_id))
    stale_complete(
        job_id=prepare_job_id,
        runner_id=runner_id,
        runner_token=runner_token,
        attempt_id=prepare_attempt_id,
        lease_id=prepare_lease_id,
        result={
            "kind": "workspace_prepare_v1",
            "workspace_id": workspace_id,
            "repository_handle_id": fixture["id"],
            "source_revision": fixture["current_revision"],
            "workspace_fingerprint": "1" * 64,
            "initial_tree_hash": "2" * 64,
            "current_tree_hash": "2" * 64,
            "side_effect_permit_id": str(uuid.uuid4()),
        },
    )
    compose("start", "runner")
    prepared = wait_for(
        "recovered Workspace ready",
        lambda: job_in_states(prepare_job_id, {"succeeded"}),
    )
    require_two_attempts(prepared)
    workspace = require_json(f"/api/v1/workspaces/{workspace_id}")
    if workspace.get("state") != "ready":
        raise RuntimeError("Recovered Workspace did not reach ready")

    read = require_success(
        require_json(
            f"/api/v1/workspaces/{workspace_id}/actions/read-text",
            method="POST",
            payload={"relative_path": "sandbox/original.txt", "max_bytes": 32768},
        ),
        "workspace_read_text_v1",
    )
    replacement = "Chaos recovered atomic write.\n"
    replacement_bytes = replacement.encode()
    replacement_sha256 = hashlib.sha256(replacement_bytes).hexdigest()
    write = require_json(
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        method="POST",
        payload={
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": replacement,
            "expected_sha256": read["sha256"],
        },
    )
    write_job_id = str(write["job"]["id"])
    wait_for(
        "write temporary file before commit",
        lambda: write_temp_present(workspace_id, write_job_id),
    )
    write_attempt_id, write_lease_id = active_lease(write_job_id, 1)
    compose("stop", "--timeout", "0", "runner")
    interrupted = inspect_interrupted_write(workspace_id, write_job_id)
    if (
        interrupted.get("target_sha256") != read["sha256"]
        or interrupted.get("temp_exists") is not True
        or interrupted.get("temp_size") != len(replacement_bytes)
    ):
        raise RuntimeError("Interrupted write was not an atomic pre-commit state")
    wait_for("first write lease expiry and requeue", lambda: requeued_job(write_job_id))
    stale_complete(
        job_id=write_job_id,
        runner_id=runner_id,
        runner_token=runner_token,
        attempt_id=write_attempt_id,
        lease_id=write_lease_id,
        result=fake_write_result(
            workspace_id,
            str(fixture["current_revision"]),
            replacement_sha256,
            len(replacement_bytes),
        ),
    )
    compose("start", "runner")
    recovered_write = wait_for(
        "recovered write success",
        lambda: job_in_states(write_job_id, {"succeeded", "failed"}),
    )
    if recovered_write.get("state") != "succeeded":
        raise RuntimeError(f"Recovered write failed with {recovered_write.get('error_code')}")
    require_two_attempts(recovered_write)
    result = recovered_write.get("result")
    if not isinstance(result, dict) or result.get("sha256") != replacement_sha256:
        raise RuntimeError("Recovered write hash is invalid")

    post_rename_replacement = "Chaos recovered after rename.\n"
    post_rename_bytes = post_rename_replacement.encode()
    post_rename_sha256 = hashlib.sha256(post_rename_bytes).hexdigest()
    post_rename_write = require_json(
        f"/api/v1/workspaces/{workspace_id}/actions/write-text",
        method="POST",
        payload={
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": post_rename_replacement,
            "expected_sha256": replacement_sha256,
        },
    )
    post_rename_job_id = str(post_rename_write["job"]["id"])
    wait_for(
        "renamed file before result coordination",
        lambda: write_target_committed(
            workspace_id,
            post_rename_job_id,
            post_rename_sha256,
        ),
    )
    post_rename_attempt_id, post_rename_lease_id = active_lease(post_rename_job_id, 1)
    compose("stop", "--timeout", "0", "runner")
    renamed = inspect_interrupted_write(workspace_id, post_rename_job_id)
    if (
        renamed.get("target_sha256") != post_rename_sha256
        or renamed.get("temp_exists") is not False
    ):
        raise RuntimeError("Post-rename interruption did not preserve the committed file")
    wait_for(
        "post-rename lease expiry and requeue",
        lambda: requeued_job(post_rename_job_id),
    )
    stale_complete(
        job_id=post_rename_job_id,
        runner_id=runner_id,
        runner_token=runner_token,
        attempt_id=post_rename_attempt_id,
        lease_id=post_rename_lease_id,
        result=fake_write_result(
            workspace_id,
            str(fixture["current_revision"]),
            post_rename_sha256,
            len(post_rename_bytes),
        ),
    )
    compose("start", "runner")
    recovered_post_rename = wait_for(
        "post-rename write recovery",
        lambda: job_in_states(post_rename_job_id, {"succeeded", "failed"}),
    )
    if recovered_post_rename.get("state") != "succeeded":
        raise RuntimeError(
            f"Post-rename recovery failed with {recovered_post_rename.get('error_code')}"
        )
    require_two_attempts(recovered_post_rename)
    post_rename_result = recovered_post_rename.get("result")
    if (
        not isinstance(post_rename_result, dict)
        or post_rename_result.get("sha256") != post_rename_sha256
    ):
        raise RuntimeError("Post-rename recovered write hash is invalid")
    durable_workspace = require_json(f"/api/v1/workspaces/{workspace_id}")
    if durable_workspace.get("total_written_bytes") != len(replacement_bytes) + len(
        post_rename_bytes
    ):
        raise RuntimeError("Crash recovery repeated the Workspace write budget")

    status = require_success(
        require_json(
            f"/api/v1/workspaces/{workspace_id}/actions/status",
            method="POST",
        ),
        "workspace_status_v1",
    )
    if status.get("changed_file_count") != 1 or any(
        ".visual-engineer-write-" in str(item.get("relative_path"))
        for item in status.get("entries", [])
        if isinstance(item, dict)
    ):
        raise RuntimeError("Recovered write left an orphan or unexpected file")
    require_success(
        require_json(
            f"/api/v1/workspaces/{workspace_id}/actions/diff",
            method="POST",
        ),
        "workspace_diff_v1",
    )
    rollback = require_success(
        require_json(
            f"/api/v1/workspaces/{workspace_id}/actions/rollback",
            method="POST",
        ),
        "workspace_rollback_v1",
    )
    if rollback.get("clean") is not True:
        raise RuntimeError("Chaos Workspace rollback was not clean")
    require_success(
        require_json(
            f"/api/v1/workspaces/{workspace_id}/actions/discard",
            method="POST",
        ),
        "workspace_discard_v1",
    )
    if workspace_path_exists(workspace_id):
        raise RuntimeError("Discard left the Runner-owned Workspace path behind")

    revoke_workspace_action = require_json(
        "/api/v1/workspaces",
        method="POST",
        payload={"grant_id": grant["id"]},
    )
    revoke_workspace_id = str(revoke_workspace_action["workspace"]["id"])
    require_success(revoke_workspace_action, "workspace_prepare_v1")
    revoke_read = require_success(
        require_json(
            f"/api/v1/workspaces/{revoke_workspace_id}/actions/read-text",
            method="POST",
            payload={"relative_path": "sandbox/original.txt", "max_bytes": 32768},
        ),
        "workspace_read_text_v1",
    )
    revoke_write = require_json(
        f"/api/v1/workspaces/{revoke_workspace_id}/actions/write-text",
        method="POST",
        payload={
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": "Bounded in-flight write during revoke request.\n",
            "expected_sha256": revoke_read["sha256"],
        },
    )
    revoke_write_job_id = str(revoke_write["job"]["id"])
    wait_for(
        "consumed Permit before concurrent Grant revoke",
        lambda: consumed_permit_job(revoke_write_job_id),
    )
    revoke_response = require_json(
        f"/api/v1/execution-grants/{grant['id']}/revoke",
        method="POST",
    )
    if (
        revoke_response.get("status") != "revoke_requested"
        or revoke_response.get("in_flight_permit_count") != 1
    ):
        raise RuntimeError("Concurrent revoke did not expose the bounded in-flight Permit")
    wait_for(
        "effective Grant revocation",
        lambda: execution_grant_in_state(str(grant["id"]), "revoked"),
    )
    effective_hash = workspace_file_sha256(revoke_workspace_id)
    time.sleep(1)
    denied_status, denied_body = request_json(
        f"/api/v1/workspaces/{revoke_workspace_id}/actions/write-text",
        method="POST",
        payload={
            "mode": "replace",
            "relative_path": "sandbox/original.txt",
            "content": "This write is after effective revocation.\n",
            "expected_sha256": effective_hash,
        },
    )
    if denied_status != 409 or "execution_grant_inactive" not in json.dumps(denied_body):
        raise RuntimeError("Effective Grant revocation accepted a new write")
    if workspace_file_sha256(revoke_workspace_id) != effective_hash:
        raise RuntimeError("Workspace changed after Grant revocation became effective")

    print(
        json.dumps(
            {
                "atomic_precommit_verified": True,
                "atomic_postrename_verified": True,
                "budget_replay": False,
                "discard_residual": False,
                "prepare_attempts": 2,
                "revoke_concurrency_verified": True,
                "revoke_effective_side_effects": 0,
                "source_revision": fixture["current_revision"],
                "stale_leases_fenced": 3,
                "workspace_id": workspace_id,
                "write_attempts": 4,
                "write_recovered": True,
            },
            sort_keys=True,
        )
    )


def repository_fixture() -> dict[str, Any]:
    payload = require_json("/api/v1/repositories")
    for item in payload.get("items", []):
        if (
            isinstance(item, dict)
            and item.get("opaque_handle") == "fixture-repository-v1"
            and item.get("status") == "available"
        ):
            return {**item, "_ready": True}
    return {"status": "waiting"}


def workspace_job_running(workspace_id: str, job_id: str) -> dict[str, Any]:
    workspace = require_json(f"/api/v1/workspaces/{workspace_id}")
    job = require_json(f"/api/v1/runner-jobs/{job_id}")
    return {
        **job,
        "_ready": workspace.get("state") == "preparing" and job.get("state") == "running",
    }


def job_in_states(job_id: str, states: set[str]) -> dict[str, Any]:
    job = require_json(f"/api/v1/runner-jobs/{job_id}")
    return {**job, "_ready": job.get("state") in states}


def requeued_job(job_id: str) -> dict[str, Any]:
    job = require_json(f"/api/v1/runner-jobs/{job_id}")
    attempts = job.get("attempts")
    expired = (
        isinstance(attempts, list)
        and len(attempts) == 1
        and isinstance(attempts[0], dict)
        and attempts[0].get("state") == "lease_expired"
    )
    return {**job, "_ready": job.get("state") == "queued" and expired}


def consumed_permit_job(job_id: str) -> dict[str, Any]:
    job = require_json(f"/api/v1/runner-jobs/{job_id}")
    query = (
        "SELECT count(*) FROM side_effect_permits "
        f"WHERE job_id = '{uuid.UUID(job_id)}' AND state = 'consumed'"
    )
    count = compose(
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
    return {**job, "_ready": job.get("state") == "running" and count == "1"}


def execution_grant_in_state(grant_id: str, state: str) -> dict[str, Any]:
    grants = require_json("/api/v1/execution-grants").get("items", [])
    grant = next(
        (item for item in grants if isinstance(item, dict) and item.get("id") == grant_id),
        None,
    )
    if grant is None:
        return {"status": "missing", "_ready": False}
    return {**grant, "_ready": grant.get("status") == state}


def write_temp_present(workspace_id: str, job_id: str) -> dict[str, Any]:
    job = require_json(f"/api/v1/runner-jobs/{job_id}")
    if job.get("state") != "running":
        return {**job, "_ready": False}
    script = (
        "from pathlib import Path;"
        f"print((Path('/var/lib/visual-engineer-runner/workspaces/workspace-{uuid.UUID(workspace_id).hex}')/"
        f"'sandbox/.visual-engineer-write-{uuid.UUID(job_id).hex}.tmp').exists())"
    )
    exists = compose("exec", "-T", "runner", "python", "-c", script).strip() == "True"
    return {**job, "_ready": exists}


def write_target_committed(
    workspace_id: str,
    job_id: str,
    expected_sha256: str,
) -> dict[str, Any]:
    job = require_json(f"/api/v1/runner-jobs/{job_id}")
    if job.get("state") != "running":
        return {**job, "_ready": False}
    script = (
        "import hashlib;"
        "from pathlib import Path;"
        f"p=Path('/var/lib/visual-engineer-runner/workspaces/workspace-{uuid.UUID(workspace_id).hex}')/"
        "'sandbox/original.txt';"
        "print(hashlib.sha256(p.read_bytes()).hexdigest())"
    )
    actual = compose("exec", "-T", "runner", "python", "-c", script).strip()
    return {**job, "_ready": actual == expected_sha256}


def workspace_file_sha256(workspace_id: str) -> str:
    script = (
        "import hashlib;"
        "from pathlib import Path;"
        f"p=Path('/var/lib/visual-engineer-runner/workspaces/workspace-{uuid.UUID(workspace_id).hex}')/"
        "'sandbox/original.txt';"
        "print(hashlib.sha256(p.read_bytes()).hexdigest())"
    )
    value = compose(
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        "python",
        "runner",
        "-c",
        script,
    ).strip()
    if len(value) != 64:
        raise RuntimeError("Workspace file hash inspection failed")
    return value


def require_two_attempts(job: dict[str, Any]) -> None:
    attempts = job.get("attempts")
    if (
        not isinstance(attempts, list)
        or len(attempts) != 2
        or [item.get("state") for item in attempts if isinstance(item, dict)]
        != ["lease_expired", "succeeded"]
    ):
        raise RuntimeError("Recovered Workspace Job Attempt history is invalid")


def fake_write_result(
    workspace_id: str,
    source_revision: str,
    content_sha256: str,
    size: int,
) -> dict[str, Any]:
    empty_diff_hash = hashlib.sha256(b"").hexdigest()
    permit_id = str(uuid.uuid4())
    checkpoint = {
        "source_revision": source_revision,
        "tree_fingerprint": "3" * 64,
        "diff_hash": empty_diff_hash,
        "changed_paths": ["sandbox/original.txt"],
        "changed_file_count": 1,
        "total_diff_bytes": 0,
        "diff": "",
        "side_effect_permit_id": permit_id,
    }
    return {
        "kind": "workspace_write_text_v1",
        "workspace_id": workspace_id,
        "relative_path": "sandbox/original.txt",
        "operation": "replace",
        "sha256": content_sha256,
        "size": size,
        "current_tree_hash": "3" * 64,
        "changed_file_count": 1,
        "total_written_bytes": size,
        "checkpoint": checkpoint,
        "side_effect_permit_id": permit_id,
    }


if __name__ == "__main__":
    main()
