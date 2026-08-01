from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from test_phase6_governed_local_delivery import (
    _approve_authorization,
    _create_authorization,
    _dispatch_delivery,
    _ready_package,
)
from test_workspace_api import (
    WORKSPACE_CAPABILITIES,
    claim_start,
    complete,
    runner_headers,
)
from visual_engineer_api.models.delivery import (
    DeliveryAuthorization,
    DeliveryDispatch,
    LocalDelivery,
)
from visual_engineer_api.models.runner import RunnerJob, RunnerJobAttempt
from visual_engineer_api.models.workspace import SideEffectPermit
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError
from visual_engineer_runner_protocol import (
    JobAssignment,
    SideEffectPermitAcquireRequest,
    WorkspaceGitCommitJobSpec,
    WorkspaceGitCommitResult,
    compute_local_delivery_result_digest,
    compute_side_effect_job_digest,
)
from visual_engineer_runner_protocol import (
    SideEffectPermit as ProtocolSideEffectPermit,
)


class CommitGateSession(Session):
    def __init__(
        self,
        *args: Any,
        commit_entered: threading.Event,
        commit_release: threading.Event,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._commit_entered = commit_entered
        self._commit_release = commit_release

    def commit(self) -> None:
        self._commit_entered.set()
        if not self._commit_release.wait(timeout=10):
            raise TimeoutError("commit gate was not released")
        super().commit()


@dataclass(frozen=True)
class RunningDelivery:
    token: str
    runner_id: uuid.UUID
    authorization: dict[str, Any]
    dispatch: dict[str, Any]
    job_id: uuid.UUID
    assignment: JobAssignment
    identity: dict[str, str]

    @property
    def permit_request(self) -> SideEffectPermitAcquireRequest:
        return SideEffectPermitAcquireRequest(
            runner_id=self.runner_id,
            attempt_id=uuid.UUID(self.identity["attempt_id"]),
            lease_id=uuid.UUID(self.identity["lease_id"]),
            job_digest=compute_side_effect_job_digest(self.assignment.job),
        )


type CallOutcome = tuple[str, object]


def _running_delivery(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> RunningDelivery:
    package, context = _ready_package(client, db_session, runner_bootstrap_token)
    authorization = _approve_authorization(
        client,
        cast(
            str,
            _create_authorization(client, cast(str, package["id"]))["id"],
        ),
    )
    heartbeat = client.post(
        "/api/v1/runner-protocol/v1/heartbeat",
        headers=runner_headers(context.token),
        json={
            "runner_id": context.runner["runner_id"],
            "protocol_version": 1,
            "software_version": "0.6.0-cancel-mutation-arbitration",
            "capabilities": [
                *WORKSPACE_CAPABILITIES,
                "validation_execute_v1",
                "workspace_git_commit_v1",
            ],
        },
    )
    assert heartbeat.status_code == 200, heartbeat.text
    dispatched = _dispatch_delivery(client, cast(str, authorization["id"]))
    job = cast(dict[str, Any], dispatched["job"])
    dispatch = cast(list[dict[str, Any]], dispatched["dispatches"])[-1]
    assignment_payload, identity = claim_start(
        client,
        context.runner,
        context.token,
        job["id"],
    )
    assignment = JobAssignment.model_validate(assignment_payload)
    assert isinstance(assignment.job, WorkspaceGitCommitJobSpec)
    db_session.commit()
    return RunningDelivery(
        token=context.token,
        runner_id=uuid.UUID(cast(str, context.runner["runner_id"])),
        authorization=authorization,
        dispatch=dispatch,
        job_id=uuid.UUID(cast(str, job["id"])),
        assignment=assignment,
        identity=identity,
    )


def _backend_pid(session: Session) -> int:
    return int(session.scalar(text("SELECT pg_backend_pid()")) or 0)


def _wait_for_blocked_row_lock(
    engine: Engine,
    *,
    blocked_pid: int,
    blocker_pid: int,
) -> tuple[str, str]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT wait_event_type, wait_event, pg_blocking_pids(pid) "
                    "FROM pg_stat_activity WHERE pid = :pid"
                ),
                {"pid": blocked_pid},
            ).one_or_none()
        if (
            row is not None
            and row.wait_event_type == "Lock"
            and blocker_pid in list(row.pg_blocking_pids)
        ):
            return cast(str, row.wait_event_type), cast(str, row.wait_event)
        threading.Event().wait(0.01)
    raise AssertionError(f"backend {blocked_pid} was not observed waiting on backend {blocker_pid}")


def _acquire_permit(
    engine: Engine,
    delivery: RunningDelivery,
    *,
    pid: list[int],
    started: threading.Event,
    commit_entered: threading.Event | None = None,
    commit_release: threading.Event | None = None,
    start_barrier: threading.Barrier | None = None,
) -> CallOutcome:
    session: Session
    if commit_entered is not None and commit_release is not None:
        session = CommitGateSession(
            bind=engine,
            commit_entered=commit_entered,
            commit_release=commit_release,
        )
    else:
        session = Session(engine)
    with session:
        pid.append(_backend_pid(session))
        started.set()
        if start_barrier is not None:
            start_barrier.wait(timeout=10)
        service = RunnerService(session)
        authenticated = service.authenticate(delivery.token)
        try:
            permit = service.acquire_side_effect_permit(
                authenticated,
                delivery.job_id,
                delivery.permit_request,
                request_id=f"permit-race-{uuid.uuid4()}",
            )
            return "permit", permit
        except RunnerServiceError as exc:
            session.rollback()
            return "error", exc.code


def _cancel_job(
    engine: Engine,
    delivery: RunningDelivery,
    *,
    pid: list[int],
    started: threading.Event,
    commit_entered: threading.Event | None = None,
    commit_release: threading.Event | None = None,
    start_barrier: threading.Barrier | None = None,
) -> CallOutcome:
    session: Session
    if commit_entered is not None and commit_release is not None:
        session = CommitGateSession(
            bind=engine,
            commit_entered=commit_entered,
            commit_release=commit_release,
        )
    else:
        session = Session(engine)
    with session:
        pid.append(_backend_pid(session))
        started.set()
        if start_barrier is not None:
            start_barrier.wait(timeout=10)
        try:
            response = RunnerService(session).cancel_job(
                delivery.job_id,
                request_id=f"cancel-race-{uuid.uuid4()}",
            )
            return "cancel", response.state.value
        except RunnerServiceError as exc:
            session.rollback()
            return "error", exc.code


def _acknowledge_cancel(client: TestClient, delivery: RunningDelivery) -> None:
    response = client.post(
        f"/api/v1/runner-protocol/v1/jobs/{delivery.job_id}/cancelled",
        headers=runner_headers(delivery.token),
        json=delivery.identity,
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "cancelled"


def _complete_delivery(
    client: TestClient,
    delivery: RunningDelivery,
    permit: ProtocolSideEffectPermit,
) -> None:
    spec = cast(WorkspaceGitCommitJobSpec, delivery.assignment.job)
    result = WorkspaceGitCommitResult(
        workspace_id=spec.workspace_id,
        delivery_authorization_id=spec.delivery_authorization.id,
        delivery_dispatch_id=spec.delivery_dispatch_id,
        delivery_attempt_number=spec.delivery_attempt_number,
        delivery_manifest_digest=spec.delivery_manifest.manifest_digest,
        checkpoint_id=spec.checkpoint_id,
        checkpoint_fingerprint=spec.checkpoint_fingerprint,
        checkpoint_diff_hash=spec.checkpoint_diff_hash,
        branch_ref=spec.delivery_authorization.branch_ref,
        commit_oid="b" * 40,
        tree_oid="c" * 40,
        parent_oid=spec.execution_grant.source_revision,
        result_digest="0" * 64,
        side_effect_permit_id=permit.id,
    )
    result.result_digest = compute_local_delivery_result_digest(result)
    complete(
        client,
        delivery.token,
        delivery.job_id,
        delivery.identity,
        result.model_dump(mode="json"),
    )


def _assert_cancelled_without_delivery(
    db_session: Session,
    delivery: RunningDelivery,
) -> None:
    db_session.expire_all()
    job = db_session.get(RunnerJob, delivery.job_id)
    attempt = db_session.get(
        RunnerJobAttempt,
        uuid.UUID(delivery.identity["attempt_id"]),
    )
    authorization = db_session.get(
        DeliveryAuthorization,
        uuid.UUID(cast(str, delivery.authorization["id"])),
    )
    dispatch = db_session.get(DeliveryDispatch, uuid.UUID(delivery.dispatch["id"]))
    assert job is not None and job.state == "cancelled" and job.result is None
    assert attempt is not None and attempt.state == "cancelled"
    assert authorization is not None and authorization.status == "cancelled"
    assert dispatch is not None and dispatch.status == "cancelled"
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SideEffectPermit)
            .where(SideEffectPermit.job_id == delivery.job_id)
        )
        == 0
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(LocalDelivery)
            .where(LocalDelivery.runner_job_id == delivery.job_id)
        )
        == 0
    )


def test_cancel_commit_wins_before_git_mutation_permit_ownership(
    client: TestClient,
    db_session: Session,
    database_url: str,
    runner_bootstrap_token: str,
) -> None:
    delivery = _running_delivery(client, db_session, runner_bootstrap_token)
    engine = create_engine(database_url)
    cancel_entered = threading.Event()
    cancel_release = threading.Event()
    cancel_started = threading.Event()
    permit_started = threading.Event()
    cancel_pid: list[int] = []
    permit_pid: list[int] = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        cancel_future = executor.submit(
            _cancel_job,
            engine,
            delivery,
            pid=cancel_pid,
            started=cancel_started,
            commit_entered=cancel_entered,
            commit_release=cancel_release,
        )
        assert cancel_started.wait(timeout=10)
        assert cancel_entered.wait(timeout=10)
        permit_future = executor.submit(
            _acquire_permit,
            engine,
            delivery,
            pid=permit_pid,
            started=permit_started,
        )
        assert permit_started.wait(timeout=10)
        try:
            assert (
                _wait_for_blocked_row_lock(
                    engine,
                    blocked_pid=permit_pid[0],
                    blocker_pid=cancel_pid[0],
                )[0]
                == "Lock"
            )
        finally:
            cancel_release.set()
        cancel_outcome = cancel_future.result(timeout=20)
        permit_outcome = permit_future.result(timeout=20)

    assert cancel_outcome == ("cancel", "cancel_requested")
    assert permit_outcome == ("error", "stale_lease")
    db_session.expire_all()
    _acknowledge_cancel(client, delivery)
    _assert_cancelled_without_delivery(db_session, delivery)
    engine.dispose()


def test_git_mutation_permit_commit_wins_and_rejects_late_cancel(
    client: TestClient,
    db_session: Session,
    database_url: str,
    runner_bootstrap_token: str,
) -> None:
    delivery = _running_delivery(client, db_session, runner_bootstrap_token)
    engine = create_engine(database_url)
    permit_entered = threading.Event()
    permit_release = threading.Event()
    permit_started = threading.Event()
    cancel_started = threading.Event()
    permit_pid: list[int] = []
    cancel_pid: list[int] = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        permit_future = executor.submit(
            _acquire_permit,
            engine,
            delivery,
            pid=permit_pid,
            started=permit_started,
            commit_entered=permit_entered,
            commit_release=permit_release,
        )
        assert permit_started.wait(timeout=10)
        assert permit_entered.wait(timeout=10)
        cancel_future = executor.submit(
            _cancel_job,
            engine,
            delivery,
            pid=cancel_pid,
            started=cancel_started,
        )
        assert cancel_started.wait(timeout=10)
        try:
            assert (
                _wait_for_blocked_row_lock(
                    engine,
                    blocked_pid=cancel_pid[0],
                    blocker_pid=permit_pid[0],
                )[0]
                == "Lock"
            )
        finally:
            permit_release.set()
        permit_outcome = permit_future.result(timeout=20)
        cancel_outcome = cancel_future.result(timeout=20)

    assert permit_outcome[0] == "permit"
    assert cancel_outcome == ("error", "runner_job_terminal")
    permit = cast(ProtocolSideEffectPermit, permit_outcome[1])
    db_session.expire_all()
    _complete_delivery(client, delivery, permit)
    db_session.expire_all()
    job = db_session.get(RunnerJob, delivery.job_id)
    attempt = db_session.get(RunnerJobAttempt, uuid.UUID(delivery.identity["attempt_id"]))
    authorization = db_session.get(
        DeliveryAuthorization,
        uuid.UUID(cast(str, delivery.authorization["id"])),
    )
    dispatch = db_session.get(DeliveryDispatch, uuid.UUID(delivery.dispatch["id"]))
    assert job is not None and job.state == "succeeded"
    assert attempt is not None and attempt.state == "succeeded"
    assert authorization is not None and authorization.status == "succeeded"
    assert dispatch is not None and dispatch.status == "succeeded"
    stored_permit = db_session.get(SideEffectPermit, permit.id)
    assert stored_permit is not None and stored_permit.state == "completed"
    engine.dispose()


def test_simultaneous_cancel_and_git_mutation_permit_has_one_legal_winner(
    client: TestClient,
    db_session: Session,
    database_url: str,
    runner_bootstrap_token: str,
) -> None:
    delivery = _running_delivery(client, db_session, runner_bootstrap_token)
    engine = create_engine(database_url)
    start_barrier = threading.Barrier(2)
    permit_started = threading.Event()
    cancel_started = threading.Event()
    permit_pid: list[int] = []
    cancel_pid: list[int] = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        permit_future = executor.submit(
            _acquire_permit,
            engine,
            delivery,
            pid=permit_pid,
            started=permit_started,
            start_barrier=start_barrier,
        )
        cancel_future = executor.submit(
            _cancel_job,
            engine,
            delivery,
            pid=cancel_pid,
            started=cancel_started,
            start_barrier=start_barrier,
        )
        assert permit_started.wait(timeout=10)
        assert cancel_started.wait(timeout=10)
        permit_outcome = permit_future.result(timeout=20)
        cancel_outcome = cancel_future.result(timeout=20)

    legal_outcomes = {
        (("permit", "success"), ("error", "runner_job_terminal")),
        (("error", "stale_lease"), ("cancel", "cancel_requested")),
    }
    normalized = (
        (
            permit_outcome[0],
            "success" if permit_outcome[0] == "permit" else cast(str, permit_outcome[1]),
        ),
        (cancel_outcome[0], cast(str, cancel_outcome[1])),
    )
    assert normalized in legal_outcomes
    assert [permit_outcome[0], cancel_outcome[0]].count("error") == 1

    db_session.expire_all()
    if permit_outcome[0] == "permit":
        _complete_delivery(
            client,
            delivery,
            cast(ProtocolSideEffectPermit, permit_outcome[1]),
        )
        db_session.expire_all()
        job = db_session.get(RunnerJob, delivery.job_id)
        assert job is not None and job.state == "succeeded"
    else:
        _acknowledge_cancel(client, delivery)
        _assert_cancelled_without_delivery(db_session, delivery)
    engine.dispose()


def test_grant_revoke_waits_for_owned_git_mutation_then_finalizes(
    client: TestClient,
    db_session: Session,
    database_url: str,
    runner_bootstrap_token: str,
) -> None:
    delivery = _running_delivery(client, db_session, runner_bootstrap_token)
    engine = create_engine(database_url)
    permit_started = threading.Event()
    permit_pid: list[int] = []
    permit_outcome = _acquire_permit(
        engine,
        delivery,
        pid=permit_pid,
        started=permit_started,
    )
    assert permit_started.is_set()
    assert permit_outcome[0] == "permit"
    permit = cast(ProtocolSideEffectPermit, permit_outcome[1])

    revoked = client.post(
        f"/api/v1/execution-grants/{delivery.authorization['execution_grant_id']}/revoke"
    )

    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "revoke_requested"
    db_session.expire_all()
    job = db_session.get(RunnerJob, delivery.job_id)
    assert job is not None and job.state == "running"
    assert job.error_code is None
    stored_permit = db_session.get(SideEffectPermit, permit.id)
    assert stored_permit is not None and stored_permit.state == "consumed"

    _complete_delivery(client, delivery, permit)
    finalized = client.get(
        f"/api/v1/execution-grants/{delivery.authorization['execution_grant_id']}"
    )
    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["status"] == "revoked"
    db_session.expire_all()
    job = db_session.get(RunnerJob, delivery.job_id)
    stored_permit = db_session.get(SideEffectPermit, permit.id)
    assert job is not None and job.state == "succeeded"
    assert stored_permit is not None and stored_permit.state == "completed"
    engine.dispose()
