import hashlib
import json
import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from visual_engineer_api.models.task import Task
from visual_engineer_api.repositories.task import TaskRepository
from visual_engineer_api.schemas.task import TaskClassification, TaskCreate, TaskResponse


class IdempotencyConflictError(Exception):
    """The idempotency key is already associated with a different request."""


_RISK_BEARING_PRODUCT_CONTENT = re.compile(
    r"ignore\s+previous|read\s+\.env|prompt[ -]?injection|adversarial|"
    r"(?:^|\W)sk-[A-Za-z0-9_-]+",
    re.IGNORECASE,
)
_SYSTEM_PROJECTIONS: dict[TaskClassification, tuple[str, str, str, str]] = {
    TaskClassification.SYSTEM_VALIDATION: (
        "System validation task",
        "System-managed validation content is hidden from ordinary product surfaces.",
        "System validation context",
        "system-managed://validation",
    ),
    TaskClassification.SECURITY_TEST: (
        "Security test task",
        "Sensitive adversarial fixture content is hidden from product surfaces.",
        "System-managed security fixture",
        "system-managed://security-test",
    ),
    TaskClassification.FIXTURE: (
        "Fixture task",
        "Deterministic fixture content is isolated from ordinary product tasks.",
        "System-managed fixture",
        "system-managed://fixture",
    ),
    TaskClassification.LIVE_CANARY: (
        "Live Provider verification",
        "A governed live Provider verification record. Request content is hidden.",
        "Synthetic public verification context",
        "system-managed://live-canary",
    ),
}


def task_response(task: Task) -> TaskResponse:
    classification = TaskClassification(task.classification)
    projection = _SYSTEM_PROJECTIONS.get(classification)
    content_redacted = projection is not None
    if projection is None:
        title = task.title
        objective = task.objective
        repository_display_name = task.repository_display_name
        repository_locator = task.repository_locator
        if _RISK_BEARING_PRODUCT_CONTENT.search(title):
            title = "Sensitive user task"
            content_redacted = True
        if _RISK_BEARING_PRODUCT_CONTENT.search(objective):
            objective = "Sensitive user-provided task content is hidden from product surfaces."
            content_redacted = True
    else:
        title, objective, repository_display_name, repository_locator = projection
    return TaskResponse(
        id=task.id,
        title=title,
        objective=objective,
        repository_kind=task.repository_kind,
        repository_display_name=repository_display_name,
        repository_locator=repository_locator,
        status=task.status,
        classification=classification,
        content_redacted=content_redacted,
        version=task.version,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


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
            **payload.model_dump(mode="json", exclude={"classification"}),
            classification=TaskClassification(payload.classification).value,
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
