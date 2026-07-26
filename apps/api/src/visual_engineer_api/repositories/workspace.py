import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from visual_engineer_api.models.run import Plan, RepositorySnapshot, Run
from visual_engineer_api.models.runner import Runner, RunnerJob, RunnerJobEvent
from visual_engineer_api.models.task import Task
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    ExecutionGrantDecision,
    RepositoryHandle,
    Workspace,
    WorkspaceCheckpoint,
    WorkspaceEvent,
)

type ExecutionContext = tuple[
    Plan,
    Run,
    Task,
    RepositorySnapshot,
    RepositoryHandle,
]


class WorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        value: RepositoryHandle
        | ExecutionGrant
        | ExecutionGrantDecision
        | Workspace
        | WorkspaceEvent
        | WorkspaceCheckpoint,
    ) -> None:
        self._session.add(value)

    def get_repository_handle(
        self, repository_id: uuid.UUID, *, lock: bool = False
    ) -> RepositoryHandle | None:
        statement = select(RepositoryHandle).where(RepositoryHandle.id == repository_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def get_repository_handle_by_opaque(
        self, runner_id: uuid.UUID, opaque_handle: str, *, lock: bool = False
    ) -> RepositoryHandle | None:
        statement = select(RepositoryHandle).where(
            RepositoryHandle.runner_id == runner_id,
            RepositoryHandle.opaque_handle == opaque_handle,
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_repository_handles(self) -> list[RepositoryHandle]:
        return list(
            self._session.scalars(
                select(RepositoryHandle).order_by(
                    RepositoryHandle.display_name.asc(), RepositoryHandle.id.asc()
                )
            )
        )

    def get_runner(self, runner_id: uuid.UUID) -> Runner | None:
        return self._session.get(Runner, runner_id)

    def eligible_execution_contexts(self) -> list[ExecutionContext]:
        statement = (
            select(Plan, Run, Task, RepositorySnapshot, RepositoryHandle)
            .join(Run, Run.id == Plan.run_id)
            .join(Task, Task.id == Run.task_id)
            .join(RepositorySnapshot, RepositorySnapshot.run_id == Run.id)
            .join(
                RepositoryHandle,
                RepositoryHandle.display_name == Task.repository_display_name,
            )
            .where(
                Plan.status == "approved",
                Run.status == "approved",
                Plan.snapshot_fingerprint == RepositorySnapshot.fingerprint,
                RepositoryHandle.status == "available",
                RepositoryHandle.current_revision == RepositorySnapshot.source_revision,
            )
            .order_by(Plan.created_at.desc(), RepositoryHandle.id.asc())
        )
        return [
            (plan, run, task, snapshot, handle)
            for plan, run, task, snapshot, handle in self._session.execute(statement).all()
        ]

    def execution_context(
        self, plan_id: uuid.UUID, repository_id: uuid.UUID, *, lock: bool = False
    ) -> ExecutionContext | None:
        statement = (
            select(Plan, Run, Task, RepositorySnapshot, RepositoryHandle)
            .join(Run, Run.id == Plan.run_id)
            .join(Task, Task.id == Run.task_id)
            .join(RepositorySnapshot, RepositorySnapshot.run_id == Run.id)
            .join(RepositoryHandle, RepositoryHandle.id == repository_id)
            .where(Plan.id == plan_id)
        )
        if lock:
            statement = statement.with_for_update(of=(Plan, Run, RepositoryHandle))
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        plan, run, task, snapshot, handle = row
        return plan, run, task, snapshot, handle

    def get_grant(self, grant_id: uuid.UUID, *, lock: bool = False) -> ExecutionGrant | None:
        statement = select(ExecutionGrant).where(ExecutionGrant.id == grant_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_grants(self) -> list[ExecutionGrant]:
        return list(
            self._session.scalars(
                select(ExecutionGrant).order_by(
                    ExecutionGrant.created_at.desc(), ExecutionGrant.id.desc()
                )
            )
        )

    def latest_grant_for_context(
        self, plan_id: uuid.UUID, repository_id: uuid.UUID
    ) -> ExecutionGrant | None:
        return self._session.scalar(
            select(ExecutionGrant)
            .where(
                ExecutionGrant.plan_id == plan_id,
                ExecutionGrant.repository_handle_id == repository_id,
                ExecutionGrant.status.in_(("pending", "approved")),
            )
            .order_by(ExecutionGrant.created_at.desc(), ExecutionGrant.id.desc())
            .limit(1)
        )

    def grant_decision(self, grant_id: uuid.UUID) -> ExecutionGrantDecision | None:
        return self._session.scalar(
            select(ExecutionGrantDecision).where(ExecutionGrantDecision.grant_id == grant_id)
        )

    def get_workspace(self, workspace_id: uuid.UUID, *, lock: bool = False) -> Workspace | None:
        statement = select(Workspace).where(Workspace.id == workspace_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_workspaces(self) -> list[Workspace]:
        return list(
            self._session.scalars(
                select(Workspace).order_by(Workspace.created_at.desc(), Workspace.id.desc())
            )
        )

    def nonterminal_workspace_for_grant(
        self, grant_id: uuid.UUID, *, lock: bool = False
    ) -> Workspace | None:
        statement = (
            select(Workspace)
            .where(
                Workspace.grant_id == grant_id,
                Workspace.state.not_in(("discarded", "failed", "expired")),
            )
            .order_by(Workspace.created_at.desc())
            .limit(1)
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def workspace_by_request(self, grant_id: uuid.UUID, request_id: str) -> Workspace | None:
        return self._session.scalar(
            select(Workspace)
            .join(WorkspaceEvent, WorkspaceEvent.workspace_id == Workspace.id)
            .where(
                Workspace.grant_id == grant_id,
                WorkspaceEvent.event_type == "workspace_requested",
                WorkspaceEvent.request_id == request_id,
            )
            .order_by(Workspace.created_at.desc())
            .limit(1)
        )

    def latest_workspace_job(self, workspace_id: uuid.UUID) -> RunnerJob | None:
        return self._session.scalar(
            select(RunnerJob)
            .where(RunnerJob.workspace_id == workspace_id)
            .order_by(RunnerJob.created_at.desc(), RunnerJob.id.desc())
            .limit(1)
        )

    def workspace_job_by_request(
        self, workspace_id: uuid.UUID, request_id: str
    ) -> RunnerJob | None:
        return self._session.scalar(
            select(RunnerJob)
            .join(RunnerJobEvent, RunnerJobEvent.job_id == RunnerJob.id)
            .where(
                RunnerJob.workspace_id == workspace_id,
                RunnerJobEvent.event_type == "job_created",
                RunnerJobEvent.request_id == request_id,
            )
            .order_by(RunnerJob.created_at.desc())
            .limit(1)
        )

    def list_workspace_events(self, workspace_id: uuid.UUID) -> list[WorkspaceEvent]:
        return list(
            self._session.scalars(
                select(WorkspaceEvent)
                .where(WorkspaceEvent.workspace_id == workspace_id)
                .order_by(WorkspaceEvent.sequence.asc(), WorkspaceEvent.id.asc())
            )
        )

    def next_workspace_event_sequence(self, workspace_id: uuid.UUID) -> int:
        return (
            int(
                self._session.scalar(
                    select(func.coalesce(func.max(WorkspaceEvent.sequence), 0)).where(
                        WorkspaceEvent.workspace_id == workspace_id
                    )
                )
                or 0
            )
            + 1
        )

    def list_checkpoints(self, workspace_id: uuid.UUID) -> list[WorkspaceCheckpoint]:
        return list(
            self._session.scalars(
                select(WorkspaceCheckpoint)
                .where(WorkspaceCheckpoint.workspace_id == workspace_id)
                .order_by(WorkspaceCheckpoint.sequence.asc(), WorkspaceCheckpoint.id.asc())
            )
        )

    def next_checkpoint_sequence(self, workspace_id: uuid.UUID) -> int:
        return (
            int(
                self._session.scalar(
                    select(func.coalesce(func.max(WorkspaceCheckpoint.sequence), 0)).where(
                        WorkspaceCheckpoint.workspace_id == workspace_id
                    )
                )
                or 0
            )
            + 1
        )

    def approved_grant_for_job(
        self, grant_id: uuid.UUID, workspace_id: uuid.UUID, now: datetime
    ) -> tuple[ExecutionGrant, Workspace] | None:
        row = self._session.execute(
            select(ExecutionGrant, Workspace)
            .join(Workspace, Workspace.grant_id == ExecutionGrant.id)
            .where(
                ExecutionGrant.id == grant_id,
                ExecutionGrant.status == "approved",
                ExecutionGrant.expires_at > now,
                Workspace.id == workspace_id,
            )
            .with_for_update(of=(ExecutionGrant, Workspace))
        ).one_or_none()
        if row is None:
            return None
        grant, workspace = row
        return grant, workspace
