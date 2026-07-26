import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from test_runner_api import create_job, register_runner
from visual_engineer_api.models.runner import RunnerJob, RunnerJobAttempt
from visual_engineer_api.services.runner import RunnerService
from visual_engineer_runner_protocol import ClaimRequest


def test_two_runners_concurrently_claim_exactly_one_attempt(
    client: TestClient,
    database_url: str,
    runner_bootstrap_token: str,
) -> None:
    first, first_token = register_runner(client, runner_bootstrap_token, name="Race First")
    second, second_token = register_runner(client, runner_bootstrap_token, name="Race Second")
    job = create_job(client)
    engine = create_engine(database_url)
    barrier = threading.Barrier(2)

    def claim(runner: dict[str, Any], token: str) -> str | None:
        with Session(engine) as session:
            service = RunnerService(session)
            authenticated = service.authenticate(token)
            barrier.wait(timeout=10)
            result = service.claim(
                authenticated,
                ClaimRequest(runner_id=uuid.UUID(runner["runner_id"])),
                request_id=str(uuid.uuid4()),
            )
            return str(result.assignment.attempt_id) if result.assignment is not None else None

    with ThreadPoolExecutor(max_workers=2) as executor:
        one = executor.submit(claim, first, first_token)
        two = executor.submit(claim, second, second_token)
        results = [one.result(timeout=20), two.result(timeout=20)]

    assert sum(result is not None for result in results) == 1
    with Session(engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(RunnerJobAttempt)
                .where(
                    RunnerJobAttempt.job_id == uuid.UUID(job["id"]),
                    RunnerJobAttempt.state.in_(("leased", "running")),
                )
            )
            == 1
        )
        durable = session.get(RunnerJob, uuid.UUID(job["id"]))
        assert durable is not None
        assert durable.attempt_count == 1
        assert durable.active_attempt_id is not None
    engine.dispose()
