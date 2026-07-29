import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from visual_engineer_api.models.runner import RunnerJob, RunnerJobAttempt
from visual_engineer_api.models.validation import (
    ValidationEvidence,
    ValidationRun,
    ValidationStepRun,
)
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    RepositoryHandle,
    Workspace,
    WorkspaceCheckpoint,
)


class ValidationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, value: ValidationRun | ValidationStepRun | ValidationEvidence) -> None:
        self._session.add(value)

    def get_run(self, validation_run_id: uuid.UUID, *, lock: bool = False) -> ValidationRun | None:
        statement = select(ValidationRun).where(ValidationRun.id == validation_run_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_by_job(self, job_id: uuid.UUID, *, lock: bool = False) -> ValidationRun | None:
        statement = select(ValidationRun).where(ValidationRun.runner_job_id == job_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_by_idempotency(self, key: str, *, lock: bool = False) -> ValidationRun | None:
        statement = select(ValidationRun).where(ValidationRun.idempotency_key == key)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_runs(self, *, workspace_id: uuid.UUID | None = None) -> list[ValidationRun]:
        statement = select(ValidationRun)
        if workspace_id is not None:
            statement = statement.where(ValidationRun.workspace_id == workspace_id)
        return list(
            self._session.scalars(
                statement.order_by(ValidationRun.created_at.desc(), ValidationRun.id.desc())
            )
        )

    def step(self, validation_run_id: uuid.UUID, *, lock: bool = False) -> ValidationStepRun | None:
        statement = select(ValidationStepRun).where(
            ValidationStepRun.validation_run_id == validation_run_id
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def evidence(self, validation_run_id: uuid.UUID) -> ValidationEvidence | None:
        return self._session.scalar(
            select(ValidationEvidence).where(
                ValidationEvidence.validation_run_id == validation_run_id
            )
        )

    def checkpoint_context(
        self, checkpoint_id: uuid.UUID, *, lock: bool = False
    ) -> tuple[WorkspaceCheckpoint, Workspace, ExecutionGrant, RepositoryHandle] | None:
        statement = (
            select(WorkspaceCheckpoint, Workspace, ExecutionGrant, RepositoryHandle)
            .join(Workspace, Workspace.id == WorkspaceCheckpoint.workspace_id)
            .join(ExecutionGrant, ExecutionGrant.id == Workspace.grant_id)
            .join(RepositoryHandle, RepositoryHandle.id == Workspace.repository_handle_id)
            .where(WorkspaceCheckpoint.id == checkpoint_id)
        )
        if lock:
            statement = statement.with_for_update(
                of=(WorkspaceCheckpoint, Workspace, ExecutionGrant, RepositoryHandle)
            )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        checkpoint, workspace, grant, handle = row
        return checkpoint, workspace, grant, handle

    def validation_grant(
        self, grant_id: uuid.UUID, *, lock: bool = False
    ) -> tuple[ExecutionGrant, WorkspaceCheckpoint, Workspace, RepositoryHandle] | None:
        statement = (
            select(ExecutionGrant, WorkspaceCheckpoint, Workspace, RepositoryHandle)
            .join(
                WorkspaceCheckpoint,
                WorkspaceCheckpoint.id == ExecutionGrant.validation_checkpoint_id,
            )
            .join(Workspace, Workspace.id == ExecutionGrant.validation_workspace_id)
            .join(RepositoryHandle, RepositoryHandle.id == ExecutionGrant.repository_handle_id)
            .where(ExecutionGrant.id == grant_id)
        )
        if lock:
            statement = statement.with_for_update(
                of=(ExecutionGrant, WorkspaceCheckpoint, Workspace, RepositoryHandle)
            )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        grant, checkpoint, workspace, handle = row
        return grant, checkpoint, workspace, handle

    def active_run_count(self, grant_id: uuid.UUID) -> int:
        return int(
            self._session.scalar(
                select(func.count(ValidationRun.id)).where(
                    ValidationRun.execution_grant_id == grant_id
                )
            )
            or 0
        )

    def latest_validation_grant_for_checkpoint(
        self, plan_id: uuid.UUID, checkpoint_id: uuid.UUID
    ) -> ExecutionGrant | None:
        return self._session.scalar(
            select(ExecutionGrant)
            .where(
                ExecutionGrant.plan_id == plan_id,
                ExecutionGrant.validation_checkpoint_id == checkpoint_id,
                ExecutionGrant.status.in_(("pending", "approved")),
            )
            .order_by(ExecutionGrant.created_at.desc(), ExecutionGrant.id.desc())
            .limit(1)
        )

    def job(self, job_id: uuid.UUID) -> RunnerJob | None:
        return self._session.get(RunnerJob, job_id)

    def attempt(self, attempt_id: uuid.UUID) -> RunnerJobAttempt | None:
        return self._session.get(RunnerJobAttempt, attempt_id)

    def latest_attempt(self, job_id: uuid.UUID) -> RunnerJobAttempt | None:
        return self._session.scalar(
            select(RunnerJobAttempt)
            .where(RunnerJobAttempt.job_id == job_id)
            .order_by(
                RunnerJobAttempt.attempt_number.desc(),
                RunnerJobAttempt.created_at.desc(),
            )
            .limit(1)
        )
