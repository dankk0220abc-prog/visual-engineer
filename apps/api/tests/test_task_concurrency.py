import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from visual_engineer_api.models.task import Task
from visual_engineer_api.schemas.task import RepositoryKind, TaskCreate
from visual_engineer_api.services.task import TaskService


class SynchronizedCommitSession(Session):
    def __init__(self, *args: Any, barrier: threading.Barrier, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._commit_barrier = barrier

    def commit(self) -> None:
        self._commit_barrier.wait(timeout=10)
        super().commit()


def test_competing_idempotent_creates_converge_on_one_postgresql_row(
    database_url: str,
) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE audit_events, approval_decisions, plans, "
                "repository_snapshots, runs, tasks"
            )
        )

    payload = TaskCreate(
        title="Concurrent Foundation task",
        objective="Prove the unique-key race recovery against PostgreSQL.",
        repository_kind=RepositoryKind.LOCAL_PATH,
        repository_display_name="Concurrency fixture",
        repository_locator="/fixtures/concurrency",
    )
    barrier = threading.Barrier(2)

    def create_once() -> tuple[uuid.UUID, bool]:
        with SynchronizedCommitSession(bind=engine, barrier=barrier) as session:
            task, replayed = TaskService(session).create(payload, "concurrent-create")
            return task.id, replayed

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(create_once)
        second = executor.submit(create_once)
        results = [first.result(timeout=20), second.result(timeout=20)]

    assert results[0][0] == results[1][0]
    assert sorted(replayed for _, replayed in results) == [False, True]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Task)) == 1
    engine.dispose()
