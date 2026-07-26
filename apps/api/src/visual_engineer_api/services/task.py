import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from visual_engineer_api.models.task import Task
from visual_engineer_api.repositories.task import TaskRepository
from visual_engineer_api.schemas.task import TaskCreate


class IdempotencyConflictError(Exception):
    """The idempotency key is already associated with a different request."""


def request_fingerprint(payload: TaskCreate) -> str:
    canonical = json.dumps(
        payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TaskService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = TaskRepository(session)

    def create(self, payload: TaskCreate, idempotency_key: str) -> tuple[Task, bool]:
        fingerprint = request_fingerprint(payload)
        existing = self._repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return self._resolve_replay(existing, fingerprint)

        task = Task(
            **payload.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            idempotency_request_hash=fingerprint,
        )
        self._repository.add(task)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            winner = self._repository.get_by_idempotency_key(idempotency_key)
            if winner is None:
                raise
            return self._resolve_replay(winner, fingerprint)

        self._session.refresh(task)
        return task, False

    @staticmethod
    def _resolve_replay(task: Task, fingerprint: str) -> tuple[Task, bool]:
        if task.idempotency_request_hash != fingerprint:
            raise IdempotencyConflictError
        return task, True
