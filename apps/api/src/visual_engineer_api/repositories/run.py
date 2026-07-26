import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from visual_engineer_api.models.run import (
    ApprovalDecision,
    AuditEvent,
    Plan,
    RepositorySnapshot,
    Run,
)


class RunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, value: Run | RepositorySnapshot | Plan | ApprovalDecision | AuditEvent) -> None:
        self._session.add(value)

    def get(self, run_id: uuid.UUID, *, lock: bool = False) -> Run | None:
        statement = select(Run).where(Run.id == run_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_by_idempotency_key(self, key: str) -> Run | None:
        return self._session.scalar(select(Run).where(Run.idempotency_key == key))

    def list_by_task(self, task_id: uuid.UUID) -> tuple[list[Run], int]:
        items = list(
            self._session.scalars(
                select(Run)
                .where(Run.task_id == task_id)
                .order_by(Run.created_at.desc(), Run.id.desc())
            )
        )
        total = (
            self._session.scalar(
                select(func.count()).select_from(Run).where(Run.task_id == task_id)
            )
            or 0
        )
        return items, total

    def get_snapshot(self, run_id: uuid.UUID) -> RepositorySnapshot | None:
        return self._session.scalar(
            select(RepositorySnapshot).where(RepositorySnapshot.run_id == run_id)
        )

    def get_plan(self, run_id: uuid.UUID, version: int, *, lock: bool = False) -> Plan | None:
        statement = select(Plan).where(Plan.run_id == run_id, Plan.version == version)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_plans(self, run_id: uuid.UUID) -> tuple[list[Plan], int]:
        items = list(
            self._session.scalars(
                select(Plan).where(Plan.run_id == run_id).order_by(Plan.version.desc())
            )
        )
        return items, len(items)

    def latest_plan(self, run_id: uuid.UUID, *, lock: bool = False) -> Plan | None:
        statement = select(Plan).where(Plan.run_id == run_id).order_by(Plan.version.desc()).limit(1)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_decision(self, plan_id: uuid.UUID) -> ApprovalDecision | None:
        return self._session.scalar(
            select(ApprovalDecision).where(ApprovalDecision.plan_id == plan_id)
        )

    def list_audit_events(self, run_id: uuid.UUID) -> tuple[list[AuditEvent], int]:
        items = list(
            self._session.scalars(
                select(AuditEvent)
                .where(AuditEvent.run_id == run_id)
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
            )
        )
        return items, len(items)
