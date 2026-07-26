import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "apps/api/src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "packages/runner-protocol/src"))

from visual_engineer_api.models.run import (  # noqa: E402
    ApprovalDecision,
    Plan,
    RepositorySnapshot,
    Run,
)
from visual_engineer_api.models.task import Task  # noqa: E402

API_BASE_URL = os.environ.get("WORKSPACE_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
DATABASE_URL = os.environ.get(
    "WORKSPACE_DATABASE_URL",
    ("postgresql+psycopg://visualengineer:visualengineer-local@127.0.0.1:5432/visualengineer"),
)
OPAQUE_HANDLE = "fixture-repository-v1"
SEED_KEY = "phase4-browser-fixture-v1"


def fetch_repositories() -> list[dict[str, Any]]:
    with urllib.request.urlopen(
        f"{API_BASE_URL}/api/v1/repositories",
        timeout=3,
    ) as response:
        payload = json.load(response)
    items = payload.get("items") if isinstance(payload, dict) else None
    return items if isinstance(items, list) else []


def wait_for_repository() -> dict[str, Any]:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            for item in fetch_repositories():
                if (
                    item.get("opaque_handle") == OPAQUE_HANDLE
                    and item.get("status") == "available"
                    and isinstance(item.get("current_revision"), str)
                ):
                    return item
        except (OSError, urllib.error.URLError, ValueError):
            pass
        time.sleep(0.5)
    raise SystemExit("Workspace fixture Repository Handle did not become available")


def seed(repository: dict[str, Any]) -> Plan:
    revision = str(repository["current_revision"])
    fingerprint = hashlib.sha256(f"workspace-fixture:{revision}".encode()).hexdigest()
    engine = create_engine(DATABASE_URL)
    try:
        with Session(engine) as session:
            existing_task = session.scalar(select(Task).where(Task.idempotency_key == SEED_KEY))
            if existing_task is not None:
                run = session.scalar(select(Run).where(Run.task_id == existing_task.id))
                if run is None:
                    raise SystemExit("Existing workspace fixture seed is incomplete")
                plan = session.scalar(
                    select(Plan).where(Plan.run_id == run.id).order_by(Plan.version.desc())
                )
                snapshot = session.scalar(
                    select(RepositorySnapshot).where(RepositorySnapshot.run_id == run.id)
                )
                if (
                    plan is None
                    or snapshot is None
                    or plan.status != "approved"
                    or snapshot.source_revision != revision
                ):
                    raise SystemExit(
                        "Existing workspace fixture seed is stale; use a clean E2E database"
                    )
                return plan

            task = Task(
                title="Phase 4 browser fixture",
                objective="Exercise the isolated synthetic workspace through typed tools.",
                repository_kind="local_path",
                repository_display_name=str(repository["display_name"]),
                repository_locator=f"runner://{OPAQUE_HANDLE}",
                status="draft",
                version=1,
                idempotency_key=SEED_KEY,
                idempotency_request_hash="4" * 64,
            )
            session.add(task)
            session.flush()
            run = Run(
                task_id=task.id,
                status="approved",
                permission_level="read_only",
                snapshot_mode="git_head",
                version=1,
                current_plan_version=1,
            )
            session.add(run)
            session.flush()
            snapshot = RepositorySnapshot(
                run_id=run.id,
                source_revision=revision,
                branch_name=str(repository.get("current_branch") or "detached"),
                repository_is_dirty=bool(repository["source_is_dirty"]),
                dirty_path_count=int(repository["dirty_path_count"]),
                dirty_paths=[],
                scanner_version="workspace-fixture-v1",
                scan_policy_version="workspace-fixture-v1",
                fingerprint=fingerprint,
                tracked_file_count=18,
                selected_file_count=4,
                skipped_file_count=14,
                total_selected_bytes=256,
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
                snapshot_fingerprint=fingerprint,
                delivery_package="frontend_quality_remediation",
                objective_summary="Exercise fixture-only typed file tools.",
                repository_context_summary="Opaque Runner handle at one committed revision.",
                assumptions=[],
                proposed_change_scope=["sandbox/**"],
                explicit_non_goals=[
                    "source writes",
                    "shell",
                    "network",
                    "git delivery",
                ],
                risk_items=["path traversal", "symlink escape", "stale hash"],
                acceptance_criteria=[
                    "Diff is bounded.",
                    "Rollback restores the initial tree.",
                ],
                evidence_requirements=["Workspace Timeline", "Checkpoint hash"],
                stop_conditions=["Grant revoked", "source revision stale"],
                validation_steps=[],
                required_future_permission_level="isolated_workspace",
                execution_available=False,
                content_hash="5" * 64,
            )
            session.add_all([snapshot, plan])
            session.flush()
            session.add(
                ApprovalDecision(
                    run_id=run.id,
                    plan_id=plan.id,
                    decision="approve",
                    comment="Pre-approved synthetic fixture Plan for browser E2E only.",
                    actor_type="local_user",
                    request_id=f"fixture-plan-{uuid.uuid4()}",
                )
            )
            session.commit()
            session.refresh(plan)
            return plan
    finally:
        engine.dispose()


def main() -> None:
    repository = wait_for_repository()
    plan = seed(repository)
    print(
        json.dumps(
            {
                "fixture": OPAQUE_HANDLE,
                "plan_id": str(plan.id),
                "repository_handle_id": str(repository["id"]),
                "source_revision": repository["current_revision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
