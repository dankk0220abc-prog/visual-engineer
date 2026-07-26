import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from repository_fixture import create_adversarial_repository
from test_runs import create_run, create_task
from visual_engineer_api.core.config import get_settings
from visual_engineer_api.models.run import ApprovalDecision, Run
from visual_engineer_api.schemas.run import DecisionKind, PlanDecisionCreate
from visual_engineer_api.services.run import RunService, RunServiceError


def test_concurrent_approve_reject_allows_exactly_one_final_decision(
    client: TestClient,
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = create_adversarial_repository(tmp_path)
    monkeypatch.setenv("READ_ONLY_REPOSITORY_ROOTS", str(tmp_path))
    monkeypatch.setenv("REPOSITORY_SCAN_MAX_FILE_BYTES", "1024")
    get_settings.cache_clear()

    task = create_task(client, repository, "decision-race")
    run = create_run(client, task["id"], "decision-race")
    assert client.post(f"/api/v1/runs/{run['id']}/snapshot").status_code == 201
    plan = client.post(
        f"/api/v1/runs/{run['id']}/plans",
        json={"delivery_package": "frontend_quality_remediation"},
    ).json()
    assert (
        client.post(f"/api/v1/runs/{run['id']}/plans/{plan['version']}/submit").status_code == 200
    )

    engine = create_engine(database_url)
    barrier = threading.Barrier(2)

    def decide(decision: DecisionKind) -> tuple[str, str]:
        barrier.wait(timeout=10)
        with Session(engine) as session:
            try:
                result, _ = RunService(session).decide_plan(
                    uuid.UUID(str(run["id"])),
                    int(plan["version"]),
                    PlanDecisionCreate(
                        decision=decision,
                        comment="Concurrent synthetic decision.",
                    ),
                    request_id=f"race-{decision}",
                )
                return "success", result.decision
            except RunServiceError as exc:
                return "error", exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        approve = executor.submit(decide, DecisionKind.APPROVE)
        reject = executor.submit(decide, DecisionKind.REJECT)
        results = [approve.result(timeout=20), reject.result(timeout=20)]

    assert sorted(result[0] for result in results) == ["error", "success"]
    assert next(result[1] for result in results if result[0] == "error") == "decision_conflict"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ApprovalDecision)) == 1
        durable_run = session.get(Run, run["id"])
        assert durable_run is not None
        assert durable_run.status in {"approved", "rejected"}
    engine.dispose()
    get_settings.cache_clear()
