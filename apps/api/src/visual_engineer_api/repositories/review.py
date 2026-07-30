import uuid

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewBlockerFinding,
    ReviewDecision,
    ReviewFreshnessState,
    ReviewPackage,
    ReviewPackageInvalidation,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.validation import (
    ValidationRun,
    ValidationSuiteResult,
    ValidationSuiteRun,
)
from visual_engineer_api.models.workspace import RepositoryHandle, Workspace, WorkspaceCheckpoint


class ReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        value: (
            ReviewPackage | ReviewPackageInvalidation | ReviewDecision | ReleaseReadinessVerdict
        ),
    ) -> None:
        self._session.add(value)

    def package(self, package_id: uuid.UUID, *, lock: bool = False) -> ReviewPackage | None:
        statement = select(ReviewPackage).where(ReviewPackage.id == package_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def package_by_idempotency(self, key: str, *, lock: bool = False) -> ReviewPackage | None:
        statement = select(ReviewPackage).where(ReviewPackage.idempotency_key == key)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def package_by_result(
        self,
        result_id: uuid.UUID,
        *,
        generation: int | None = None,
        lock: bool = False,
    ) -> ReviewPackage | None:
        statement = select(ReviewPackage).where(ReviewPackage.suite_result_id == result_id)
        if generation is not None:
            statement = statement.where(ReviewPackage.freshness_generation == generation)
        statement = statement.order_by(
            ReviewPackage.package_version.desc(),
            ReviewPackage.created_at.desc(),
            ReviewPackage.id.desc(),
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def next_package_version(self, result_id: uuid.UUID) -> int:
        return (
            self._session.scalar(
                select(func.coalesce(func.max(ReviewPackage.package_version), 0)).where(
                    ReviewPackage.suite_result_id == result_id
                )
            )
            or 0
        ) + 1

    def list_packages(self) -> list[ReviewPackage]:
        return list(
            self._session.scalars(
                select(ReviewPackage).order_by(
                    ReviewPackage.created_at.desc(), ReviewPackage.id.desc()
                )
            )
        )

    def revision_authority(
        self, repository_handle_id: uuid.UUID, *, lock: bool = False
    ) -> RepositoryHandle | None:
        statement = select(RepositoryHandle).where(RepositoryHandle.id == repository_handle_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def lock_revision_authority(self, repository_handle_id: uuid.UUID) -> None:
        self._session.execute(
            text("SELECT lock_review_revision_authority(CAST(:repository_handle_id AS uuid))"),
            {"repository_handle_id": str(repository_handle_id)},
        )

    def invalidation(self, package_id: uuid.UUID) -> ReviewPackageInvalidation | None:
        return self._session.scalar(
            select(ReviewPackageInvalidation).where(
                ReviewPackageInvalidation.review_package_id == package_id
            )
        )

    def decision(self, package_id: uuid.UUID, *, lock: bool = False) -> ReviewDecision | None:
        statement = select(ReviewDecision).where(ReviewDecision.review_package_id == package_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def decision_by_idempotency(self, key: str, *, lock: bool = False) -> ReviewDecision | None:
        statement = select(ReviewDecision).where(ReviewDecision.idempotency_key == key)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def readiness(
        self, package_id: uuid.UUID, *, lock: bool = False
    ) -> ReleaseReadinessVerdict | None:
        statement = select(ReleaseReadinessVerdict).where(
            ReleaseReadinessVerdict.review_package_id == package_id
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def suite_context(
        self, suite_run_id: uuid.UUID, *, lock: bool = False
    ) -> (
        tuple[
            ValidationSuiteRun,
            ValidationSuiteResult,
            Workspace,
            WorkspaceCheckpoint,
            RepositoryHandle,
        ]
        | None
    ):
        statement = (
            select(
                ValidationSuiteRun,
                ValidationSuiteResult,
                Workspace,
                WorkspaceCheckpoint,
                RepositoryHandle,
            )
            .join(
                ValidationSuiteResult,
                ValidationSuiteResult.suite_run_id == ValidationSuiteRun.id,
            )
            .join(Workspace, Workspace.id == ValidationSuiteRun.workspace_id)
            .join(
                WorkspaceCheckpoint,
                WorkspaceCheckpoint.id == ValidationSuiteRun.checkpoint_id,
            )
            .join(
                RepositoryHandle,
                RepositoryHandle.id == Workspace.repository_handle_id,
            )
            .where(ValidationSuiteRun.id == suite_run_id)
        )
        if lock:
            statement = statement.with_for_update(
                of=(
                    ValidationSuiteRun,
                    ValidationSuiteResult,
                    Workspace,
                    WorkspaceCheckpoint,
                    RepositoryHandle,
                )
            )
        row = self._session.execute(statement).one_or_none()
        if row is None:
            return None
        suite_run, result, workspace, checkpoint, handle = row
        return suite_run, result, workspace, checkpoint, handle

    def latest_checkpoint(self, workspace_id: uuid.UUID) -> WorkspaceCheckpoint | None:
        return self._session.scalar(
            select(WorkspaceCheckpoint)
            .where(WorkspaceCheckpoint.workspace_id == workspace_id)
            .order_by(
                WorkspaceCheckpoint.sequence.desc(),
                WorkspaceCheckpoint.created_at.desc(),
                WorkspaceCheckpoint.id.desc(),
            )
            .limit(1)
        )

    def latest_success_result(
        self, *, plan_id: uuid.UUID, checkpoint_id: uuid.UUID
    ) -> ValidationSuiteResult | None:
        return self._session.scalar(
            select(ValidationSuiteResult)
            .join(
                ValidationSuiteRun,
                ValidationSuiteRun.id == ValidationSuiteResult.suite_run_id,
            )
            .where(
                ValidationSuiteRun.plan_id == plan_id,
                ValidationSuiteResult.checkpoint_id == checkpoint_id,
                ValidationSuiteResult.verdict == "succeeded",
            )
            .order_by(
                ValidationSuiteResult.created_at.desc(),
                ValidationSuiteResult.id.desc(),
            )
            .limit(1)
        )

    def freshness_state(
        self,
        *,
        plan_id: uuid.UUID,
        workspace_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        create: bool = False,
        lock: bool = False,
    ) -> ReviewFreshnessState | None:
        if create:
            self._session.execute(
                insert(ReviewFreshnessState)
                .values(
                    id=uuid.uuid4(),
                    plan_id=plan_id,
                    workspace_id=workspace_id,
                    checkpoint_id=checkpoint_id,
                    generation=1,
                    last_change_kind="scope_initialized",
                )
                .on_conflict_do_nothing(index_elements=("plan_id", "workspace_id", "checkpoint_id"))
            )
        statement = select(ReviewFreshnessState).where(
            ReviewFreshnessState.plan_id == plan_id,
            ReviewFreshnessState.workspace_id == workspace_id,
            ReviewFreshnessState.checkpoint_id == checkpoint_id,
        )
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def freshness_state_by_id(
        self, state_id: uuid.UUID, *, lock: bool = False
    ) -> ReviewFreshnessState | None:
        statement = select(ReviewFreshnessState).where(ReviewFreshnessState.id == state_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def blocker_findings(
        self,
        *,
        plan_id: uuid.UUID,
        workspace_id: uuid.UUID,
        checkpoint_id: uuid.UUID,
        lock: bool = False,
    ) -> list[ReviewBlockerFinding]:
        statement = (
            select(ReviewBlockerFinding)
            .where(
                ReviewBlockerFinding.plan_id == plan_id,
                ReviewBlockerFinding.workspace_id == workspace_id,
                ReviewBlockerFinding.checkpoint_id == checkpoint_id,
            )
            .order_by(
                ReviewBlockerFinding.finding_key,
                ReviewBlockerFinding.finding_version.desc(),
                ReviewBlockerFinding.created_at.desc(),
                ReviewBlockerFinding.id.desc(),
            )
        )
        if lock:
            statement = statement.with_for_update()
        return list(self._session.scalars(statement))

    def latest_validation_run(
        self, *, plan_id: uuid.UUID, checkpoint_id: uuid.UUID
    ) -> ValidationRun | None:
        return self._session.scalar(
            select(ValidationRun)
            .where(
                ValidationRun.plan_id == plan_id,
                ValidationRun.checkpoint_id == checkpoint_id,
            )
            .order_by(ValidationRun.created_at.desc(), ValidationRun.id.desc())
            .limit(1)
        )

    def latest_suite_run(
        self, *, plan_id: uuid.UUID, checkpoint_id: uuid.UUID
    ) -> ValidationSuiteRun | None:
        return self._session.scalar(
            select(ValidationSuiteRun)
            .where(
                ValidationSuiteRun.plan_id == plan_id,
                ValidationSuiteRun.checkpoint_id == checkpoint_id,
            )
            .order_by(ValidationSuiteRun.created_at.desc(), ValidationSuiteRun.id.desc())
            .limit(1)
        )

    def next_review_event_sequence(self, package_id: uuid.UUID) -> int:
        return (
            self._session.scalar(
                select(func.coalesce(func.max(AuditEvent.review_sequence), 0)).where(
                    AuditEvent.review_package_id == package_id
                )
            )
            or 0
        ) + 1
