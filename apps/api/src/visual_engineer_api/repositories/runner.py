import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from visual_engineer_api.models.runner import (
    PermissionEnvelope,
    Runner,
    RunnerJob,
    RunnerJobAttempt,
    RunnerJobEvent,
)
from visual_engineer_api.models.workspace import RepositoryHandle


class RunnerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        value: Runner | PermissionEnvelope | RunnerJob | RunnerJobAttempt | RunnerJobEvent,
    ) -> None:
        self._session.add(value)

    def get_runner(self, runner_id: uuid.UUID, *, lock: bool = False) -> Runner | None:
        statement = select(Runner).where(Runner.id == runner_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_runners(self) -> list[Runner]:
        return list(
            self._session.scalars(
                select(Runner).order_by(Runner.registered_at.desc(), Runner.id.desc())
            )
        )

    def auth_candidates(self) -> list[Runner]:
        return list(self._session.scalars(select(Runner).order_by(Runner.id)))

    def runners_past_heartbeat(
        self,
        cutoff: datetime,
    ) -> list[Runner]:
        return list(
            self._session.scalars(
                select(Runner)
                .where(
                    Runner.status.in_(("registered", "online")),
                    Runner.last_seen_at.is_not(None),
                    Runner.last_seen_at < cutoff,
                )
                .order_by(Runner.last_seen_at.asc())
                .with_for_update(skip_locked=True)
            )
        )

    def get_job(self, job_id: uuid.UUID, *, lock: bool = False) -> RunnerJob | None:
        statement = select(RunnerJob).where(RunnerJob.id == job_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_jobs(self) -> list[RunnerJob]:
        return list(
            self._session.scalars(
                select(RunnerJob).order_by(RunnerJob.created_at.desc(), RunnerJob.id.desc())
            )
        )

    def claimable_job(
        self,
        capabilities: list[str],
        runner_id: uuid.UUID,
    ) -> RunnerJob | None:
        return self._session.scalar(
            select(RunnerJob)
            .where(
                RunnerJob.state == "queued",
                RunnerJob.attempt_count < RunnerJob.max_attempts,
                RunnerJob.kind.in_(capabilities),
                or_(
                    RunnerJob.repository_handle_id.is_(None),
                    RunnerJob.repository_handle_id.in_(
                        select(RepositoryHandle.id).where(
                            RepositoryHandle.runner_id == runner_id,
                            RepositoryHandle.status == "available",
                        )
                    ),
                ),
            )
            .order_by(RunnerJob.created_at.asc(), RunnerJob.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )

    def get_envelope(self, envelope_id: uuid.UUID) -> PermissionEnvelope | None:
        return self._session.get(PermissionEnvelope, envelope_id)

    def get_envelope_for_job(self, job_id: uuid.UUID) -> PermissionEnvelope | None:
        return self._session.scalar(
            select(PermissionEnvelope).where(PermissionEnvelope.job_id == job_id)
        )

    def get_attempt(
        self,
        attempt_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> RunnerJobAttempt | None:
        statement = select(RunnerJobAttempt).where(RunnerJobAttempt.id == attempt_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_attempts(self, job_id: uuid.UUID) -> list[RunnerJobAttempt]:
        return list(
            self._session.scalars(
                select(RunnerJobAttempt)
                .where(RunnerJobAttempt.job_id == job_id)
                .order_by(RunnerJobAttempt.attempt_number.asc())
            )
        )

    def active_attempt_for_runner(self, runner_id: uuid.UUID) -> RunnerJobAttempt | None:
        return self._session.scalar(
            select(RunnerJobAttempt)
            .where(
                RunnerJobAttempt.runner_id == runner_id,
                RunnerJobAttempt.state.in_(("leased", "running")),
            )
            .order_by(RunnerJobAttempt.created_at.desc())
            .limit(1)
        )

    def expired_jobs(self, now: datetime) -> list[RunnerJob]:
        return list(
            self._session.scalars(
                select(RunnerJob)
                .join(
                    RunnerJobAttempt,
                    RunnerJobAttempt.id == RunnerJob.active_attempt_id,
                )
                .where(
                    RunnerJob.state.in_(("leased", "running", "cancel_requested")),
                    RunnerJobAttempt.state.in_(("leased", "running")),
                    RunnerJobAttempt.leased_until <= now,
                )
                .order_by(RunnerJobAttempt.leased_until.asc(), RunnerJob.id.asc())
                .with_for_update(of=RunnerJob, skip_locked=True)
            )
        )

    def list_events(self, job_id: uuid.UUID) -> list[RunnerJobEvent]:
        return list(
            self._session.scalars(
                select(RunnerJobEvent)
                .where(RunnerJobEvent.job_id == job_id)
                .order_by(RunnerJobEvent.sequence.asc(), RunnerJobEvent.id.asc())
            )
        )

    def event_by_request(
        self,
        *,
        event_type: str,
        request_id: str,
        runner_id: uuid.UUID | None,
        job_id: uuid.UUID | None = None,
    ) -> RunnerJobEvent | None:
        statement = select(RunnerJobEvent).where(
            RunnerJobEvent.event_type == event_type,
            RunnerJobEvent.request_id == request_id,
        )
        if runner_id is None:
            statement = statement.where(RunnerJobEvent.runner_id.is_(None))
        else:
            statement = statement.where(RunnerJobEvent.runner_id == runner_id)
        if job_id is not None:
            statement = statement.where(RunnerJobEvent.job_id == job_id)
        return self._session.scalar(statement.order_by(RunnerJobEvent.created_at.desc()).limit(1))

    def next_event_sequence(
        self,
        *,
        job_id: uuid.UUID | None,
        runner_id: uuid.UUID | None,
    ) -> int:
        statement = select(func.coalesce(func.max(RunnerJobEvent.sequence), 0))
        if job_id is not None:
            statement = statement.where(RunnerJobEvent.job_id == job_id)
        elif runner_id is not None:
            statement = statement.where(
                RunnerJobEvent.job_id.is_(None),
                RunnerJobEvent.runner_id == runner_id,
            )
        else:
            statement = statement.where(
                RunnerJobEvent.job_id.is_(None),
                RunnerJobEvent.runner_id.is_(None),
            )
        return int(self._session.scalar(statement) or 0) + 1
