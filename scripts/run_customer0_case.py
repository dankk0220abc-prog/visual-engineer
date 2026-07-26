import json
import os
import urllib.error
import urllib.request
from typing import Any

API_BASE_URL = os.environ.get("CUSTOMER0_API_BASE_URL", "http://127.0.0.1:18001").rstrip("/")
WEB_BASE_URL = os.environ.get("CUSTOMER0_WEB_BASE_URL", "http://127.0.0.1:13001").rstrip("/")


def request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    value = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(value, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"Customer 0 API request failed with HTTP {exc.code}: {payload}") from exc


def main() -> None:
    _, task = request(
        "POST",
        "/api/v1/tasks",
        headers={"Idempotency-Key": "customer0-phase2-task-v1"},
        body={
            "title": "CreativeDeploy read-only delivery discovery",
            "objective": (
                "Produce a governed read-only implementation plan for a future Frontend "
                "Quality Remediation delivery on the committed CreativeDeploy HEAD. Identify "
                "the frontend stack, design-system and testing surfaces, responsive and "
                "accessibility validation opportunities, repository constraints, risks and "
                "evidence requirements. Do not modify or execute commands in CreativeDeploy."
            ),
            "repository_kind": "local_path",
            "repository_display_name": "CreativeDeploy Customer 0",
            "repository_locator": "/repositories/customer0/creative-deploy",
        },
    )
    _, run = request(
        "POST",
        f"/api/v1/tasks/{task['id']}/runs",
        headers={"Idempotency-Key": "customer0-phase2-run-v1"},
        body={"permission_level": "read_only", "snapshot_mode": "git_head"},
    )
    _, snapshot = request("POST", f"/api/v1/runs/{run['id']}/snapshot")
    _, plans = request("GET", f"/api/v1/runs/{run['id']}/plans")
    if plans["items"]:
        plan = plans["items"][0]
    else:
        _, plan = request(
            "POST",
            f"/api/v1/runs/{run['id']}/plans",
            body={"delivery_package": "frontend_quality_remediation"},
        )
    if plan["status"] == "draft":
        _, plan = request(
            "POST",
            f"/api/v1/runs/{run['id']}/plans/{plan['version']}/submit",
        )
    _, durable_run = request("GET", f"/api/v1/runs/{run['id']}")
    if durable_run["status"] != "awaiting_plan_approval" or plan["status"] != "awaiting_approval":
        raise SystemExit("Customer 0 Run is not safely stopped at awaiting approval")
    print(
        json.dumps(
            {
                "task_id": task["id"],
                "run_id": run["id"],
                "snapshot_fingerprint": snapshot["fingerprint"],
                "plan_version": plan["version"],
                "run_status": durable_run["status"],
                "plan_status": plan["status"],
                "page_url": f"{WEB_BASE_URL}/runs/{run['id']}",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
