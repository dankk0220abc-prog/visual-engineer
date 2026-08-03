from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_validation_suites import _prepare_suite
from visual_engineer_api.models.runner import RunnerJob
from visual_engineer_api.models.validation import (
    ValidationRun,
    ValidationSuiteRun,
    ValidationSuiteStepRun,
)
from visual_engineer_api.schemas.validation import ValidationSuiteRunCreate
from visual_engineer_api.services.runner import RunnerService
from visual_engineer_api.services.validation_suite import ValidationSuiteService


def _normalized_sql(statement: str) -> str:
    return " ".join(statement.lower().split())


def _parameter_values(parameters: Any) -> set[str]:
    if isinstance(parameters, dict):
        return {str(value) for value in parameters.values()}
    if isinstance(parameters, (list, tuple)):
        return {str(value) for value in parameters}
    return {str(parameters)}


def _backend_pid(connection: Connection) -> int:
    driver_connection = connection.connection.driver_connection
    assert driver_connection is not None
    return int(driver_connection.info.backend_pid)


def _activity(engine: Engine, backend_pid: int) -> dict[str, Any] | None:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as observer:
        row = (
            observer.execute(
                text(
                    "SELECT pid, pg_blocking_pids(pid) AS blockers, "
                    "wait_event_type, wait_event, state, query "
                    "FROM pg_stat_activity WHERE pid = :pid"
                ),
                {"pid": backend_pid},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    return {
        "pid": int(row["pid"]),
        "blockers": [int(pid) for pid in row["blockers"]],
        "wait_event_type": row["wait_event_type"],
        "wait_event": row["wait_event"],
        "state": row["state"],
        "query": str(row["query"]),
    }


def _wait_for_blocker(
    engine: Engine,
    *,
    blocked_pid: int,
    blocker_pid: int,
    sql_fragment: str,
    timeout_seconds: float = 10,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        snapshot = _activity(engine, blocked_pid)
        if (
            snapshot is not None
            and blocker_pid in snapshot["blockers"]
            and snapshot["wait_event_type"] == "Lock"
            and sql_fragment in _normalized_sql(snapshot["query"])
        ):
            return snapshot
    raise TimeoutError(f"backend {blocked_pid} did not wait on {blocker_pid} at {sql_fragment}")


def _is_deadlock(error: BaseException) -> bool:
    return isinstance(error, DBAPIError) and getattr(error.orig, "sqlstate", None) == "40P01"


def test_child_visibility_window_cannot_deadlock_suite_replay(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _prepare_suite(
        client,
        db_session,
        runner_bootstrap_token,
        start_suite=False,
    )
    db_session.commit()

    engine = create_engine(database_url, pool_size=6)
    grant_id = uuid.UUID(context.grant_id)
    shared_key = f"suite-child-visibility-{uuid.uuid4()}"
    runner_returned = threading.Event()
    release_runner = threading.Event()
    child_select_entered = threading.Event()
    release_child_select = threading.Event()
    arm_binding_update = threading.Event()
    first_binding_update_executed = threading.Event()
    release_final_binding_update = threading.Event()
    winner_pid_ready = threading.Event()
    loser_pid_ready = threading.Event()
    trace_lock = threading.Lock()
    trace: list[dict[str, Any]] = []
    outcomes: dict[int, tuple[str, str]] = {}
    backend_pids: dict[str, int] = {}
    child_identity: dict[str, str] = {}
    visibility: list[dict[str, Any]] = []
    winner_update_count = 0
    original_create_workspace_job = RunnerService.create_workspace_job

    def record(stage: str, **details: Any) -> None:
        with trace_lock:
            trace.append({"sequence": len(trace) + 1, "stage": stage, **details})

    def tag_worker_transaction(
        session: Session,
        _transaction: Any,
        connection: Connection,
    ) -> None:
        worker = session.info.get("deadlock_worker")
        if worker is None:
            connection.info.pop("deadlock_worker", None)
        else:
            connection.info["deadlock_worker"] = worker

    def before_cursor_execute(
        connection: Connection,
        _cursor: Any,
        statement: str,
        parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if connection.info.get("deadlock_worker") != "loser":
            return
        child_key = child_identity.get("idempotency_key")
        if child_key is None:
            return
        normalized = _normalized_sql(statement)
        if not (
            "from validation_runs" in normalized
            and "where validation_runs.idempotency_key =" in normalized
            and normalized.endswith("for update")
            and child_key in _parameter_values(parameters)
        ):
            return
        backend_pids["loser_child_select"] = _backend_pid(connection)
        record(
            "loser_child_select_entered",
            backend_pid=backend_pids["loser_child_select"],
            idempotency_key=child_key,
        )
        child_select_entered.set()
        if not release_child_select.wait(timeout=10):
            raise TimeoutError("timed out before the exact child SELECT FOR UPDATE")

    def after_cursor_execute(
        connection: Connection,
        _cursor: Any,
        statement: str,
        parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        nonlocal winner_update_count
        if connection.info.get("deadlock_worker") != "winner":
            return
        child_run_id = child_identity.get("run_id")
        if child_run_id is None:
            return
        normalized = _normalized_sql(statement)
        if not (
            normalized.startswith("update validation_runs set")
            and "where validation_runs.id =" in normalized
            and child_run_id in _parameter_values(parameters)
        ):
            return
        winner_update_count += 1
        record(
            "winner_child_update_executed",
            backend_pid=_backend_pid(connection),
            update_number=winner_update_count,
            sql=normalized,
        )
        if winner_update_count != 1 or not arm_binding_update.is_set():
            return
        backend_pids["winner_binding"] = _backend_pid(connection)
        first_binding_update_executed.set()
        if not release_final_binding_update.wait(timeout=10):
            raise TimeoutError("timed out before the final child binding UPDATE")

    def controlled_create_workspace_job(
        service: RunnerService,
        spec: Any,
        *,
        request_id: str,
        commit: bool = True,
    ) -> Any:
        result = original_create_workspace_job(
            service,
            spec,
            request_id=request_id,
            commit=commit,
        )
        if service._session.info.get("deadlock_worker") != "winner":
            return result

        service._session.connection().info["deadlock_worker"] = "winner"
        backend_pid, transaction_id = service._session.execute(
            text("SELECT pg_backend_pid(), pg_current_xact_id()::text")
        ).one()
        backend_pids["winner_runner_return"] = int(backend_pid)
        child_identity["run_id"] = str(spec.validation_run_id)
        with Session(engine) as observer:
            child = observer.get(ValidationRun, spec.validation_run_id)
            job = observer.get(RunnerJob, result.id)
            observed = {
                "child_visible": child is not None,
                "job_visible": job is not None,
                "runner_job_id": str(child.runner_job_id)
                if child and child.runner_job_id
                else None,
                "state": child.state if child else None,
                "version": child.version if child else None,
            }
        visibility.append(observed)
        record(
            "runner_create_returned",
            backend_pid=int(backend_pid),
            transaction_id=str(transaction_id),
            commit=commit,
            **observed,
        )
        winner_pid_ready.set()
        runner_returned.set()
        if not release_runner.wait(timeout=10):
            raise TimeoutError("timed out after Runner create returned")
        return result

    monkeypatch.setattr(
        RunnerService,
        "create_workspace_job",
        controlled_create_workspace_job,
    )
    event.listen(Session, "after_begin", tag_worker_transaction)
    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    event.listen(engine, "after_cursor_execute", after_cursor_execute)

    def create_once(worker: int) -> None:
        with Session(engine) as session:
            session.info["deadlock_worker"] = "winner" if worker == 1 else "loser"
            try:
                backend_pid, transaction_id = session.execute(
                    text("SELECT pg_backend_pid(), pg_current_xact_id()::text")
                ).one()
                backend_pids[f"worker_{worker}_initial"] = int(backend_pid)
                if worker == 2:
                    loser_pid_ready.set()
                record(
                    "worker_started",
                    worker=worker,
                    backend_pid=int(backend_pid),
                    transaction_id=str(transaction_id),
                )
                response = ValidationSuiteService(session).create(
                    ValidationSuiteRunCreate(
                        execution_grant_id=grant_id,
                        suite_id="fixture-integrity-suite-v1",
                        suite_version=1,
                    ),
                    idempotency_key=shared_key,
                    request_id=f"suite-child-visibility-{worker}",
                )
                outcomes[worker] = ("created", str(response.id))
                record("worker_completed", worker=worker, suite_run_id=str(response.id))
            except Exception as error:
                session.rollback()
                error_name = (
                    type(error.orig).__name__
                    if isinstance(error, DBAPIError)
                    else type(error).__name__
                )
                outcomes[worker] = ("error", error_name)
                record(
                    "worker_rolled_back",
                    worker=worker,
                    exception_type=error_name,
                    sqlstate=(
                        getattr(error.orig, "sqlstate", None)
                        if isinstance(error, DBAPIError)
                        else None
                    ),
                    deadlock=_is_deadlock(error),
                )

    executor = ThreadPoolExecutor(max_workers=2)
    winner_future = executor.submit(create_once, 1)
    loser_future = None
    barrier_error: BaseException | None = None
    opposing_wait: dict[str, Any] | None = None
    try:
        if not runner_returned.wait(timeout=10) or not winner_pid_ready.is_set():
            raise TimeoutError("winner did not reach the Runner create seam")
        with Session(engine) as observer:
            suite_run_id = observer.scalar(
                select(ValidationSuiteRun.id).where(
                    ValidationSuiteRun.execution_grant_id == grant_id
                )
            )
        if suite_run_id is None:
            raise AssertionError("Suite Run was not visible before child dispatch")
        child_identity["idempotency_key"] = f"suite:{suite_run_id}:attempt:1:step:1"

        loser_future = executor.submit(create_once, 2)
        if not loser_pid_ready.wait(timeout=10):
            raise TimeoutError("loser did not open its independent PostgreSQL transaction")

        deadline = time.monotonic() + 10
        competition_stage = ""
        while time.monotonic() < deadline:
            if child_select_entered.is_set():
                competition_stage = "child_select"
                break
            initial_loser_pid = backend_pids["worker_2_initial"]
            snapshot = _activity(engine, initial_loser_pid)
            if (
                snapshot is not None
                and backend_pids["winner_runner_return"] in snapshot["blockers"]
                and snapshot["wait_event_type"] == "Lock"
            ):
                competition_stage = "outer_transaction"
                opposing_wait = snapshot
                break
        if not competition_stage:
            raise TimeoutError("loser reached neither the child nor outer lock competition point")
        record("competition_stage", stage_name=competition_stage)

        if competition_stage == "child_select":
            arm_binding_update.set()
            release_runner.set()
            if not first_binding_update_executed.wait(timeout=10):
                raise TimeoutError("winner did not execute the first child binding UPDATE")
            release_child_select.set()
            opposing_wait = _wait_for_blocker(
                engine,
                blocked_pid=backend_pids["loser_child_select"],
                blocker_pid=backend_pids["winner_binding"],
                sql_fragment="from validation_runs",
            )
            record(
                "loser_child_select_waiting_on_winner",
                backend_pid=opposing_wait["pid"],
                blockers=opposing_wait["blockers"],
                wait_event=opposing_wait["wait_event"],
                query=_normalized_sql(opposing_wait["query"]),
            )
            release_final_binding_update.set()
        else:
            assert opposing_wait is not None
            record(
                "loser_waiting_on_atomic_outer_transaction",
                backend_pid=opposing_wait["pid"],
                blockers=opposing_wait["blockers"],
                wait_event=opposing_wait["wait_event"],
                query=_normalized_sql(opposing_wait["query"]),
            )
            release_child_select.set()
            release_final_binding_update.set()
            release_runner.set()

        winner_future.result(timeout=20)
        if loser_future is not None:
            loser_future.result(timeout=20)
    except BaseException as error:
        barrier_error = error
    finally:
        release_runner.set()
        release_child_select.set()
        release_final_binding_update.set()
        winner_future.result(timeout=20)
        if loser_future is not None:
            loser_future.result(timeout=20)
        executor.shutdown(wait=True)
        event.remove(engine, "after_cursor_execute", after_cursor_execute)
        event.remove(engine, "before_cursor_execute", before_cursor_execute)
        event.remove(Session, "after_begin", tag_worker_transaction)

    with Session(engine) as verification:
        suite_runs = list(
            verification.scalars(
                select(ValidationSuiteRun).where(ValidationSuiteRun.execution_grant_id == grant_id)
            )
        )
        child_runs = list(
            verification.scalars(
                select(ValidationRun).where(ValidationRun.execution_grant_id == grant_id)
            )
        )
        jobs = list(
            verification.scalars(select(RunnerJob).where(RunnerJob.execution_grant_id == grant_id))
        )
        suite_steps = list(
            verification.scalars(
                select(ValidationSuiteStepRun)
                .where(
                    ValidationSuiteStepRun.suite_run_id.in_(
                        select(ValidationSuiteRun.id).where(
                            ValidationSuiteRun.execution_grant_id == grant_id
                        )
                    )
                )
                .order_by(ValidationSuiteStepRun.sequence)
            )
        )
        unbound_children = int(
            verification.scalar(
                select(func.count(ValidationRun.id)).where(
                    ValidationRun.execution_grant_id == grant_id,
                    ValidationRun.runner_job_id.is_(None),
                )
            )
            or 0
        )
    engine.dispose()

    print("VALIDATION_DEADLOCK_TRACE=" + json.dumps(trace, sort_keys=True))
    assert barrier_error is None, f"barrier failed: {barrier_error!r}; trace={trace!r}"
    errors = {worker: outcome for worker, outcome in outcomes.items() if outcome[0] == "error"}
    assert not errors, f"database exception during Suite replay: {errors!r}; trace={trace!r}"
    assert visibility == [
        {
            "child_visible": False,
            "job_visible": False,
            "runner_job_id": None,
            "state": None,
            "version": None,
        }
    ]
    assert len(suite_runs) == 1
    assert len(child_runs) == 1
    assert len(jobs) == 1
    assert len(suite_steps) == 2
    assert unbound_children == 0
    assert child_runs[0].runner_job_id == jobs[0].id
    assert suite_steps[0].validation_run_id == child_runs[0].id
    assert suite_steps[0].runner_job_id == jobs[0].id
    assert suite_steps[1].validation_run_id is None
    assert outcomes == {
        1: ("created", str(suite_runs[0].id)),
        2: ("created", str(suite_runs[0].id)),
    }
