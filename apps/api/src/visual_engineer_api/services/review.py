from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from collections.abc import Sequence
from typing import NoReturn

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewDecision,
    ReviewPackage,
    ReviewPackageInvalidation,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.validation import ValidationSuiteResult, ValidationSuiteRun
from visual_engineer_api.repositories.review import ReviewRepository
from visual_engineer_api.schemas.review import (
    ReleaseReadinessVerdictResponse,
    ReviewDecisionCreate,
    ReviewDecisionResponse,
    ReviewPackageCreate,
    ReviewPackageInvalidationResponse,
    ReviewPackageListResponse,
    ReviewPackageResponse,
)
from visual_engineer_api.services.validation_suite import (
    ValidationSuiteService,
    ValidationSuiteServiceError,
)


class ReviewServiceError(Exception):
    def __init__(self, code: str, message: str, *, category: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


class ReviewService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._reviews = ReviewRepository(session)

    def create(
        self,
        payload: ReviewPackageCreate,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> ReviewPackageResponse:
        request_hash = self._digest(payload.model_dump(mode="json"))
        replay = self._reviews.package_by_idempotency(idempotency_key, lock=True)
        if replay is not None:
            if replay.idempotency_request_hash != request_hash:
                self._conflict(
                    "review_package_idempotency_conflict",
                    "Idempotency-Key is associated with a different Review Package request",
                )
            return self._response(replay)

        context = self._reviews.suite_context(payload.suite_run_id, lock=True)
        if context is None:
            self._not_found(
                "validation_suite_result_not_found",
                "Validation Suite Result was not found",
            )
        suite_run, result, workspace, checkpoint, handle = context
        try:
            trusted_suite, trusted_result, entries = ValidationSuiteService(
                self._session
            ).trusted_success_manifest(payload.suite_run_id)
        except ValidationSuiteServiceError as exc:
            raise ReviewServiceError(exc.code, exc.message, category=exc.category) from exc
        if trusted_suite.id != suite_run.id or trusted_result.id != result.id:
            self._policy(
                "review_evidence_integrity_failed",
                "Trusted Suite proof changed while the Review Package was created",
            )
        stale_reason, _observed = self._freshness_reason_for_context(
            suite_run, result, workspace, checkpoint, handle
        )
        if stale_reason is not None:
            self._conflict(
                "review_package_stale",
                "Review Package baseline is no longer the current successful Suite baseline",
            )

        existing = self._reviews.package_by_result(result.id, lock=True)
        if existing is not None:
            return self._response(existing)

        manifest = self._manifest(suite_run, result, entries)
        manifest_digest = self._digest(manifest)
        package_id = uuid.uuid4()
        package_payload = {
            "schema_version": 1,
            "package_id": str(package_id),
            "run_id": str(suite_run.run_id),
            "plan_id": str(suite_run.plan_id),
            "repository_handle_id": str(handle.id),
            "source_revision": suite_run.source_revision,
            "workspace_id": str(suite_run.workspace_id),
            "checkpoint_id": str(suite_run.checkpoint_id),
            "checkpoint_fingerprint": suite_run.checkpoint_fingerprint,
            "suite_run_id": str(suite_run.id),
            "suite_result_id": str(result.id),
            "suite_result_digest": result.aggregate_digest,
            "evidence_manifest_digest": manifest_digest,
            "git_authorization": False,
            "deployment_authorization": False,
        }
        package = ReviewPackage(
            id=package_id,
            schema_version=1,
            run_id=suite_run.run_id,
            plan_id=suite_run.plan_id,
            repository_handle_id=handle.id,
            source_revision=suite_run.source_revision,
            workspace_id=suite_run.workspace_id,
            checkpoint_id=suite_run.checkpoint_id,
            checkpoint_fingerprint=suite_run.checkpoint_fingerprint,
            suite_run_id=suite_run.id,
            suite_result_id=result.id,
            suite_result_digest=result.aggregate_digest,
            evidence_manifest=manifest,
            evidence_manifest_digest=manifest_digest,
            package_digest=self._digest(package_payload),
            idempotency_key=idempotency_key,
            idempotency_request_hash=request_hash,
            git_authorization=False,
            deployment_authorization=False,
        )
        self._reviews.add(package)
        self._audit(
            suite_run.run_id,
            "review_package_created",
            request_id=request_id,
            details={
                "review_package_id": str(package.id),
                "suite_run_id": str(suite_run.id),
                "suite_result_id": str(result.id),
                "package_digest": package.package_digest,
                "evidence_manifest_digest": manifest_digest,
            },
        )
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            winner = self._reviews.package_by_result(result.id)
            if winner is not None:
                return self._response(winner)
            raise ReviewServiceError(
                "review_package_conflict",
                "A concurrent Review Package request won",
                category="conflict",
            ) from exc
        self._session.refresh(package)
        return self._response(package)

    def list(self) -> ReviewPackageListResponse:
        packages = self._reviews.list_packages()
        return ReviewPackageListResponse(
            items=[self._response(package) for package in packages],
            total=len(packages),
        )

    def get(self, package_id: uuid.UUID) -> ReviewPackageResponse:
        return self._response(self._required_package(package_id))

    def decide(
        self,
        package_id: uuid.UUID,
        payload: ReviewDecisionCreate,
        *,
        request_id: str,
    ) -> ReviewPackageResponse:
        package = self._required_package(package_id, lock=True)
        reason = payload.reason.strip() if payload.reason is not None else None
        existing = self._reviews.decision(package.id, lock=True)
        if existing is not None:
            if existing.decision == payload.decision and existing.reason == reason:
                return self._response(package)
            self._conflict(
                "review_decision_conflict",
                "Review Package already has a different final decision",
            )

        stale_reason, observed = self._freshness_reason(package)
        if stale_reason is not None:
            self._record_invalidation(
                package,
                reason_code=stale_reason,
                observed_value=observed,
                request_id=request_id,
            )
            self._conflict(
                "stale_review_package",
                "Stale Review Package cannot receive a final decision",
            )

        decision = ReviewDecision(
            review_package_id=package.id,
            package_digest=package.package_digest,
            decision=payload.decision,
            reason=reason,
            actor_type="local_user",
            request_id=request_id,
            git_authorization=False,
            deployment_authorization=False,
        )
        self._reviews.add(decision)
        self._audit(
            package.run_id,
            "review_decision_recorded",
            request_id=request_id,
            details={
                "review_package_id": str(package.id),
                "decision": payload.decision,
                "package_digest": package.package_digest,
                "git_authorization": False,
                "deployment_authorization": False,
            },
        )
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            winner = self._reviews.decision(package.id)
            if (
                winner is not None
                and winner.decision == payload.decision
                and winner.reason == reason
            ):
                return self._response(self._required_package(package.id))
            raise ReviewServiceError(
                "review_decision_conflict",
                "A concurrent final Review Decision won",
                category="conflict",
            ) from exc
        return self._response(self._required_package(package.id))

    def evaluate_readiness(
        self,
        package_id: uuid.UUID,
        *,
        request_id: str,
    ) -> ReviewPackageResponse:
        package = self._required_package(package_id, lock=True)
        decision = self._reviews.decision(package.id, lock=True)
        if decision is None:
            self._conflict(
                "review_decision_required",
                "Release Readiness requires one final Review Decision",
            )
        existing = self._reviews.readiness(package.id, lock=True)
        if existing is not None:
            stale_reason, observed = self._freshness_reason(package)
            if stale_reason is not None:
                self._record_invalidation(
                    package,
                    reason_code=stale_reason,
                    observed_value=observed,
                    request_id=request_id,
                )
            return self._response(package)

        stale_reason, observed = self._freshness_reason(package)
        if stale_reason is not None:
            self._record_invalidation(
                package,
                reason_code=stale_reason,
                observed_value=observed,
                request_id=request_id,
            )
        reason_codes = (
            [f"stale:{stale_reason}"]
            if stale_reason is not None
            else (
                ["review_rejected"]
                if decision.decision == "reject"
                else ["all_required_evidence_verified"]
            )
        )
        verdict = (
            "ready" if stale_reason is None and decision.decision == "approve" else "not_ready"
        )
        decision_digest = self._decision_digest(decision)
        verdict_payload = {
            "review_package_id": str(package.id),
            "review_decision_id": str(decision.id),
            "package_digest": package.package_digest,
            "decision_digest": decision_digest,
            "evidence_manifest_digest": package.evidence_manifest_digest,
            "verdict": verdict,
            "reason_codes": reason_codes,
            "git_authorization": False,
            "deployment_authorization": False,
        }
        readiness = ReleaseReadinessVerdict(
            review_package_id=package.id,
            review_decision_id=decision.id,
            package_digest=package.package_digest,
            decision_digest=decision_digest,
            evidence_manifest_digest=package.evidence_manifest_digest,
            verdict=verdict,
            reason_codes=reason_codes,
            verdict_digest=self._digest(verdict_payload),
            git_authorization=False,
            deployment_authorization=False,
        )
        self._reviews.add(readiness)
        self._audit(
            package.run_id,
            "release_readiness_evaluated",
            request_id=request_id,
            details={
                "review_package_id": str(package.id),
                "verdict": verdict,
                "reason_codes": reason_codes,
                "git_authorization": False,
                "deployment_authorization": False,
            },
        )
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if self._reviews.readiness(package.id) is None:
                raise ReviewServiceError(
                    "release_readiness_conflict",
                    "A concurrent Release Readiness evaluation won",
                    category="conflict",
                ) from exc
        return self._response(self._required_package(package.id))

    def refresh_freshness(self, package_id: uuid.UUID, *, request_id: str) -> ReviewPackageResponse:
        package = self._required_package(package_id, lock=True)
        stale_reason, observed = self._freshness_reason(package)
        if stale_reason is not None:
            self._record_invalidation(
                package,
                reason_code=stale_reason,
                observed_value=observed,
                request_id=request_id,
            )
        return self._response(package)

    def _freshness_reason(self, package: ReviewPackage) -> tuple[str | None, str]:
        invalidation = self._reviews.invalidation(package.id)
        if invalidation is not None:
            return invalidation.reason_code, invalidation.observed_value
        context = self._reviews.suite_context(package.suite_run_id, lock=True)
        if context is None:
            return "evidence_integrity_failed", "suite_context_missing"
        suite_run, result, workspace, checkpoint, handle = context
        if (
            package.suite_result_id != result.id
            or package.suite_result_digest != result.aggregate_digest
            or package.run_id != suite_run.run_id
            or package.plan_id != suite_run.plan_id
            or package.workspace_id != workspace.id
            or package.checkpoint_id != checkpoint.id
            or package.repository_handle_id != handle.id
        ):
            return "evidence_integrity_failed", "identity_mismatch"
        reason, observed = self._freshness_reason_for_context(
            suite_run, result, workspace, checkpoint, handle
        )
        if reason is not None:
            return reason, observed
        try:
            _, trusted_result, entries = ValidationSuiteService(
                self._session
            ).trusted_success_manifest(package.suite_run_id)
        except ValidationSuiteServiceError:
            return "evidence_integrity_failed", "trusted_reconstruction_failed"
        manifest = self._manifest(suite_run, trusted_result, entries)
        manifest_digest = self._digest(manifest)
        if package.evidence_manifest != manifest or not hmac.compare_digest(
            package.evidence_manifest_digest, manifest_digest
        ):
            return "evidence_integrity_failed", manifest_digest
        return None, package.package_digest

    def _freshness_reason_for_context(
        self,
        suite_run: ValidationSuiteRun,
        result: ValidationSuiteResult,
        workspace: object,
        checkpoint: object,
        handle: object,
    ) -> tuple[str | None, str]:
        if (
            getattr(handle, "current_revision", None) != suite_run.source_revision
            or getattr(handle, "status", None) != "available"
        ):
            return "source_revision_changed", str(
                getattr(handle, "current_revision", None) or "unavailable"
            )
        if (
            getattr(workspace, "source_revision", None) != suite_run.source_revision
            or getattr(checkpoint, "source_revision", None) != suite_run.source_revision
        ):
            return "source_revision_changed", str(
                getattr(workspace, "source_revision", None) or "missing"
            )
        if (
            getattr(workspace, "current_tree_hash", None) != suite_run.checkpoint_fingerprint
            or getattr(checkpoint, "tree_fingerprint", None) != suite_run.checkpoint_fingerprint
        ):
            return "workspace_changed", str(
                getattr(workspace, "current_tree_hash", None) or "missing"
            )
        latest_checkpoint = self._reviews.latest_checkpoint(suite_run.workspace_id)
        if latest_checkpoint is None or latest_checkpoint.id != suite_run.checkpoint_id:
            return "checkpoint_superseded", str(
                latest_checkpoint.id if latest_checkpoint is not None else "missing"
            )
        latest_result = self._reviews.latest_success_result(
            plan_id=suite_run.plan_id,
            checkpoint_id=suite_run.checkpoint_id,
        )
        if latest_result is None or latest_result.id != result.id:
            return "suite_result_superseded", str(
                latest_result.id if latest_result is not None else "missing"
            )
        return None, result.aggregate_digest

    def _record_invalidation(
        self,
        package: ReviewPackage,
        *,
        reason_code: str,
        observed_value: str,
        request_id: str,
    ) -> None:
        if self._reviews.invalidation(package.id) is not None:
            return
        self._reviews.add(
            ReviewPackageInvalidation(
                review_package_id=package.id,
                package_digest=package.package_digest,
                reason_code=reason_code,
                observed_value=observed_value[:128],
                request_id=request_id,
            )
        )
        self._audit(
            package.run_id,
            "review_package_invalidated",
            request_id=request_id,
            details={
                "review_package_id": str(package.id),
                "reason_code": reason_code,
                "package_digest": package.package_digest,
            },
        )
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()

    def _response(self, package: ReviewPackage) -> ReviewPackageResponse:
        stale_reason, _observed = self._freshness_reason(package)
        invalidation = self._reviews.invalidation(package.id)
        decision = self._reviews.decision(package.id)
        readiness = self._reviews.readiness(package.id)
        readiness_response = None
        if readiness is not None:
            readiness_response = ReleaseReadinessVerdictResponse(
                id=readiness.id,
                review_package_id=readiness.review_package_id,
                review_decision_id=readiness.review_decision_id,
                package_digest=readiness.package_digest,
                decision_digest=readiness.decision_digest,
                evidence_manifest_digest=readiness.evidence_manifest_digest,
                verdict=readiness.verdict,
                effective_verdict=(
                    "stale"
                    if stale_reason is not None and readiness.verdict == "ready"
                    else readiness.verdict
                ),
                reason_codes=readiness.reason_codes,
                verdict_digest=readiness.verdict_digest,
                git_authorization=False,
                deployment_authorization=False,
                created_at=readiness.created_at,
            )
        return ReviewPackageResponse(
            id=package.id,
            schema_version=1,
            run_id=package.run_id,
            plan_id=package.plan_id,
            repository_handle_id=package.repository_handle_id,
            source_revision=package.source_revision,
            workspace_id=package.workspace_id,
            checkpoint_id=package.checkpoint_id,
            checkpoint_fingerprint=package.checkpoint_fingerprint,
            suite_run_id=package.suite_run_id,
            suite_result_id=package.suite_result_id,
            suite_result_digest=package.suite_result_digest,
            evidence_manifest=package.evidence_manifest,
            evidence_manifest_digest=package.evidence_manifest_digest,
            package_digest=package.package_digest,
            freshness="stale" if stale_reason is not None else "fresh",
            stale_reason_code=stale_reason,
            git_authorization=False,
            deployment_authorization=False,
            created_at=package.created_at,
            invalidation=(
                ReviewPackageInvalidationResponse.model_validate(invalidation)
                if invalidation is not None
                else None
            ),
            decision=(
                ReviewDecisionResponse.model_validate(decision) if decision is not None else None
            ),
            readiness=readiness_response,
        )

    @staticmethod
    def _manifest(
        suite_run: ValidationSuiteRun,
        result: ValidationSuiteResult,
        entries: Sequence[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "schema_version": 1,
            "suite_run_id": str(suite_run.id),
            "suite_result_id": str(result.id),
            "suite": f"{suite_run.suite_id}:v{suite_run.suite_version}",
            "source_revision": suite_run.source_revision,
            "checkpoint_id": str(suite_run.checkpoint_id),
            "checkpoint_fingerprint": suite_run.checkpoint_fingerprint,
            "suite_result_digest": result.aggregate_digest,
            "entries": entries,
            "artifact_count": 0,
            "artifact_bytes": 0,
            "cleanup_succeeded": True,
            "source_invariant": True,
            "canonical_workspace_invariant": True,
        }

    @staticmethod
    def _decision_digest(decision: ReviewDecision) -> str:
        return ReviewService._digest(
            {
                "review_decision_id": str(decision.id),
                "review_package_id": str(decision.review_package_id),
                "package_digest": decision.package_digest,
                "decision": decision.decision,
                "reason": decision.reason,
                "actor_type": decision.actor_type,
                "git_authorization": False,
                "deployment_authorization": False,
            }
        )

    @staticmethod
    def _digest(value: object) -> str:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _audit(
        self,
        run_id: uuid.UUID,
        event_type: str,
        *,
        request_id: str,
        details: dict[str, object],
    ) -> None:
        self._session.add(
            AuditEvent(
                run_id=run_id,
                event_type=event_type,
                actor_type=("local_user" if event_type == "review_decision_recorded" else "system"),
                request_id=request_id,
                details=details,
            )
        )

    def _required_package(self, package_id: uuid.UUID, *, lock: bool = False) -> ReviewPackage:
        package = self._reviews.package(package_id, lock=lock)
        if package is None:
            self._not_found("review_package_not_found", "Review Package was not found")
        return package

    @staticmethod
    def _not_found(code: str, message: str) -> NoReturn:
        raise ReviewServiceError(code, message, category="not_found")

    @staticmethod
    def _conflict(code: str, message: str) -> NoReturn:
        raise ReviewServiceError(code, message, category="conflict")

    @staticmethod
    def _policy(code: str, message: str) -> NoReturn:
        raise ReviewServiceError(code, message, category="policy")
