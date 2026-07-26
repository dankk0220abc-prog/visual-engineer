import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from visual_engineer_api.models.task import Task


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self._session.get(Task, task_id)

    def get_by_idempotency_key(self, key: str) -> Task | None:
        return self._session.scalar(select(Task).where(Task.idempotency_key == key))

    def list(self, *, limit: int, offset: int) -> tuple[list[Task], int]:
        tasks = list(
            self._session.scalars(
                select(Task)
                .order_by(Task.created_at.desc(), Task.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        total = self._session.scalar(select(func.count()).select_from(Task)) or 0
        return tasks, total

    def add(self, task: Task) -> None:
        self._session.add(task)
