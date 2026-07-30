import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewDecision,
    ReviewPackage,
    ReviewPackageInvalidation,
)
from visual_engineer_api.models.validation import ValidationSuiteResult, ValidationSuiteRun
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
        self, result_id: uuid.UUID, *, lock: bool = False
    ) -> ReviewPackage | None:
        statement = select(ReviewPackage).where(ReviewPackage.suite_result_id == result_id)
        if lock:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def list_packages(self) -> list[ReviewPackage]:
        return list(
            self._session.scalars(
                select(ReviewPackage).order_by(
                    ReviewPackage.created_at.desc(), ReviewPackage.id.desc()
                )
            )
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
