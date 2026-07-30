from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from collections.abc import Sequence
from typing import NoReturn, TypedDict

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from visual_engineer_api.models.review import (
    ReleaseReadinessVerdict,
    ReviewBlockerFinding,
    ReviewDecision,
    ReviewPackage,
    ReviewPackageInvalidation,
)
from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.validation import ValidationSuiteResult, ValidationSuiteRun
from visual_engineer_api.models.workspace import WorkspaceCheckpoint
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


class BlockerSummary(TypedDict):
    schema_version: int
    source: str
    source_version: int
    plan_id: str
    workspace_id: str
    checkpoint_id: str
    suite_result_id: str
    suite_result_digest: str
    evidence_manifest_digest: str
    policy_digest: str
    freshness_generation: int
    critical_count: int
    high_count: int
    blocking_medium_count: int
    findings: list[dict[str, object]]


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
        request_hash = self._trusted_digest(payload.model_dump(mode="json"))
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
        scope = self._reviews.freshness_state(
            plan_id=suite_run.plan_id,
            workspace_id=suite_run.workspace_id,
            checkpoint_id=suite_run.checkpoint_id,
            create=True,
            lock=True,
        )
        if scope is None:
            self._conflict(
                "review_freshness_scope_conflict",
                "Review freshness scope could not be initialized",
            )
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
        if (
            scope.last_change_kind
            not in {
                "scope_initialized",
                "review_blocker_findings:INSERT",
                "remediation_generation_required",
            }
            and result.created_at < scope.updated_at
        ):
            self._conflict(
                "review_package_stale",
                "A new trusted Suite Result is required after validation or authority changed",
            )

        existing = self._reviews.package_by_result(
            result.id,
            generation=scope.generation,
            lock=True,
        )
        if existing is not None:
            return self._response(existing)

        manifest = self._manifest(
            suite_run,
            result,
            entries,
            checkpoint=checkpoint,
            freshness_generation=scope.generation,
        )
        manifest_digest = self._trusted_digest(manifest)
        blocker_summary = self._blocker_summary(
            suite_run=suite_run,
            result=result,
            manifest_digest=manifest_digest,
            freshness_generation=scope.generation,
            lock=True,
        )
        blocker_summary_digest = self._trusted_digest(blocker_summary)
        package_id = uuid.uuid4()
        package_version = self._reviews.next_package_version(result.id)
        package_payload = {
            "schema_version": 2,
            "package_id": str(package_id),
            "package_version": package_version,
            "freshness_state_id": str(scope.id),
            "freshness_generation": scope.generation,
            "run_id": str(suite_run.run_id),
            "plan_id": str(suite_run.plan_id),
            "repository_handle_id": str(handle.id),
            "source_revision": suite_run.source_revision,
            "workspace_id": str(suite_run.workspace_id),
            "checkpoint_id": str(suite_run.checkpoint_id),
            "checkpoint_fingerprint": suite_run.checkpoint_fingerprint,
            "checkpoint_diff_hash": checkpoint.diff_hash,
            "suite_run_id": str(suite_run.id),
            "suite_result_id": str(result.id),
            "execution_grant_id": str(suite_run.execution_grant_id),
            "suite_policy_digest": suite_run.policy_digest,
            "suite_result_digest": result.aggregate_digest,
            "evidence_manifest_digest": manifest_digest,
            "blocker_summary_digest": blocker_summary_digest,
            "git_authorization": False,
            "deployment_authorization": False,
        }
        package = ReviewPackage(
            id=package_id,
            schema_version=2,
            package_version=package_version,
            freshness_state_id=scope.id,
            freshness_generation=scope.generation,
            run_id=suite_run.run_id,
            plan_id=suite_run.plan_id,
            repository_handle_id=handle.id,
            source_revision=suite_run.source_revision,
            workspace_id=suite_run.workspace_id,
            checkpoint_id=suite_run.checkpoint_id,
            checkpoint_fingerprint=suite_run.checkpoint_fingerprint,
            checkpoint_diff_hash=checkpoint.diff_hash,
            suite_run_id=suite_run.id,
            suite_result_id=result.id,
            execution_grant_id=suite_run.execution_grant_id,
            suite_policy_digest=suite_run.policy_digest,
            suite_result_digest=result.aggregate_digest,
            evidence_manifest=manifest,
            evidence_manifest_digest=manifest_digest,
            blocker_summary=blocker_summary,
            blocker_summary_digest=blocker_summary_digest,
            blocker_source="governed-review-security-findings",
            blocker_source_version=blocker_summary["source_version"],
            critical_count=blocker_summary["critical_count"],
            high_count=blocker_summary["high_count"],
            blocking_medium_count=blocker_summary["blocking_medium_count"],
            package_digest=self._trusted_digest(package_payload),
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
                "package_version": package.package_version,
                "freshness_generation": package.freshness_generation,
                "suite_run_id": str(suite_run.id),
                "suite_result_id": str(result.id),
                "package_digest": package.package_digest,
                "evidence_manifest_digest": manifest_digest,
                "blocker_summary_digest": blocker_summary_digest,
            },
            review_package_id=package.id,
        )
        try:
            self._session.commit()
        except DBAPIError as exc:
            self._session.rollback()
            winner = self._reviews.package_by_result(
                result.id,
                generation=scope.generation,
            )
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
        idempotency_key: str | None = None,
    ) -> ReviewPackageResponse:
        package = self._required_package_with_revision_authority(package_id)
        reason = payload.reason.strip() if payload.reason is not None else None
        expected_generation = (
            payload.expected_generation
            if payload.expected_generation is not None
            else package.freshness_generation
        )
        request_payload = {
            "review_package_id": str(package.id),
            "package_version": package.package_version,
            "expected_generation": expected_generation,
            "package_digest": package.package_digest,
            "policy_digest": package.suite_policy_digest,
            "decision": payload.decision,
            "reason": reason,
            "actor_type": "local_user",
        }
        request_hash = self._trusted_digest(request_payload)
        decision_key = idempotency_key or f"legacy:{package.id}:{request_hash}"

        scope = self._reviews.freshness_state_by_id(package.freshness_state_id, lock=True)
        if (
            scope is None
            or expected_generation != package.freshness_generation
            or scope.generation != expected_generation
        ):
            self._conflict(
                "review_generation_mismatch",
                "Review Decision expected generation does not match the current Package generation",
            )
        stale_reason, observed = self._freshness_reason(package, lock_context=True)
        if stale_reason is not None:
            self._record_invalidation(
                package,
                reason_code=stale_reason,
                observed_value=observed,
                request_id=request_id,
            )
            self._conflict(
                "stale_review_package",
                "Stale Review Package cannot receive or replay a final decision",
            )

        keyed_replay = self._reviews.decision_by_idempotency(decision_key, lock=True)
        if keyed_replay is not None:
            if (
                keyed_replay.review_package_id != package.id
                or keyed_replay.idempotency_request_hash != request_hash
            ):
                self._conflict(
                    "review_decision_idempotency_conflict",
                    "Idempotency-Key is associated with a different Review Decision request",
                )
            return self._response(package)

        existing = self._reviews.decision(package.id, lock=True)
        if existing is not None:
            if (
                idempotency_key is None
                and existing.decision == payload.decision
                and existing.reason == reason
                and existing.expected_generation == expected_generation
            ):
                return self._response(package)
            self._conflict(
                "review_decision_conflict",
                "Review Package already has a different final decision",
            )

        self._verify_package_integrity(package)
        if payload.decision == "approve" and (
            package.critical_count > 0
            or package.high_count > 0
            or package.blocking_medium_count > 0
        ):
            self._conflict(
                "review_blockers_present",
                "Review Package with blocking security findings cannot be approved",
            )

        decision_id = uuid.uuid4()
        decision_payload = {
            "review_decision_id": str(decision_id),
            **request_payload,
            "idempotency_key": decision_key,
            "idempotency_request_hash": request_hash,
            "git_authorization": False,
            "deployment_authorization": False,
        }
        decision = ReviewDecision(
            id=decision_id,
            review_package_id=package.id,
            package_version=package.package_version,
            expected_generation=expected_generation,
            package_digest=package.package_digest,
            policy_digest=package.suite_policy_digest,
            decision=payload.decision,
            reason=reason,
            actor_type="local_user",
            request_id=request_id,
            idempotency_key=decision_key,
            idempotency_request_hash=request_hash,
            decision_digest=self._trusted_digest(decision_payload),
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
                "package_version": package.package_version,
                "expected_generation": expected_generation,
                "decision": payload.decision,
                "package_digest": package.package_digest,
                "policy_digest": package.suite_policy_digest,
                "git_authorization": False,
                "deployment_authorization": False,
            },
            review_package_id=package.id,
        )
        try:
            self._session.commit()
        except DBAPIError as exc:
            self._session.rollback()
            winner = self._reviews.decision_by_idempotency(decision_key)
            if (
                winner is not None
                and winner.review_package_id == package.id
                and winner.idempotency_request_hash == request_hash
            ):
                return self._response(self._required_package(package.id))
            winner = self._reviews.decision(package.id)
            if (
                winner is not None
                and idempotency_key is None
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
        package = self._required_package_with_revision_authority(package_id)
        scope = self._reviews.freshness_state_by_id(package.freshness_state_id, lock=True)
        if scope is None:
            self._conflict(
                "review_freshness_scope_missing",
                "Release Readiness requires a trusted Package freshness scope",
            )
        decision = self._reviews.decision(package.id, lock=True)
        if decision is None:
            self._conflict(
                "review_decision_required",
                "Release Readiness requires one final Review Decision",
            )
        existing = self._reviews.readiness(package.id, lock=True)
        if existing is not None:
            stale_reason, observed = self._freshness_reason(package, lock_context=True)
            if stale_reason is not None:
                self._record_invalidation(
                    package,
                    reason_code=stale_reason,
                    observed_value=observed,
                    request_id=request_id,
                )
            return self._response(package)

        stale_reason, observed = self._freshness_reason(package, lock_context=True)
        if stale_reason is not None:
            self._record_invalidation(
                package,
                reason_code=stale_reason,
                observed_value=observed,
                request_id=request_id,
            )
        if stale_reason is None:
            self._verify_package_integrity(package)
        blockers_present = (
            package.critical_count > 0
            or package.high_count > 0
            or package.blocking_medium_count > 0
        )
        reason_codes = (
            [f"stale:{stale_reason}"]
            if stale_reason is not None
            else (
                ["review_rejected"]
                if decision.decision == "reject"
                else (
                    ["blocking_security_findings_present"]
                    if blockers_present
                    else ["all_required_evidence_verified"]
                )
            )
        )
        verdict = (
            "ready"
            if stale_reason is None and decision.decision == "approve" and not blockers_present
            else "not_ready"
        )
        verdict_payload = {
            "review_package_id": str(package.id),
            "review_decision_id": str(decision.id),
            "package_version": package.package_version,
            "freshness_generation": package.freshness_generation,
            "package_digest": package.package_digest,
            "decision_digest": decision.decision_digest,
            "evidence_manifest_digest": package.evidence_manifest_digest,
            "suite_result_digest": package.suite_result_digest,
            "policy_digest": package.suite_policy_digest,
            "blocker_summary_digest": package.blocker_summary_digest,
            "critical_count": package.critical_count,
            "high_count": package.high_count,
            "blocking_medium_count": package.blocking_medium_count,
            "verdict": verdict,
            "reason_codes": reason_codes,
            "git_authorization": False,
            "deployment_authorization": False,
        }
        readiness = ReleaseReadinessVerdict(
            review_package_id=package.id,
            review_decision_id=decision.id,
            package_version=package.package_version,
            freshness_generation=package.freshness_generation,
            package_digest=package.package_digest,
            decision_digest=decision.decision_digest,
            evidence_manifest_digest=package.evidence_manifest_digest,
            suite_result_digest=package.suite_result_digest,
            policy_digest=package.suite_policy_digest,
            blocker_summary_digest=package.blocker_summary_digest,
            critical_count=package.critical_count,
            high_count=package.high_count,
            blocking_medium_count=package.blocking_medium_count,
            verdict=verdict,
            reason_codes=reason_codes,
            verdict_digest=self._trusted_digest(verdict_payload),
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
                "package_version": package.package_version,
                "freshness_generation": package.freshness_generation,
                "verdict": verdict,
                "reason_codes": reason_codes,
                "blocker_summary_digest": package.blocker_summary_digest,
                "git_authorization": False,
                "deployment_authorization": False,
            },
            review_package_id=package.id,
        )
        try:
            self._session.commit()
        except DBAPIError as exc:
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
        stale_reason, observed = self._freshness_reason(package, lock_context=True)
        if stale_reason is not None:
            self._record_invalidation(
                package,
                reason_code=stale_reason,
                observed_value=observed,
                request_id=request_id,
            )
        return self._response(package)

    def _freshness_reason(
        self,
        package: ReviewPackage,
        *,
        lock_context: bool = False,
    ) -> tuple[str | None, str]:
        invalidation = self._reviews.invalidation(package.id)
        if invalidation is not None:
            return invalidation.reason_code, invalidation.observed_value
        if package.schema_version != 2:
            return "remediation_generation_required", "schema_v2_required"
        scope = self._reviews.freshness_state_by_id(package.freshness_state_id)
        if scope is None:
            return "evidence_integrity_failed", "freshness_scope_missing"
        if scope.generation != package.freshness_generation:
            reason_by_change = {
                "review_blocker_findings:INSERT": "blocker_summary_changed",
                "execution_grants:INSERT": "grant_lineage_changed",
                "execution_grants:UPDATE": "grant_lineage_changed",
                "execution_grants:DELETE": "grant_lineage_changed",
            }
            return (
                reason_by_change.get(scope.last_change_kind, "validation_facts_changed"),
                f"generation:{scope.generation}",
            )
        context = self._reviews.suite_context(
            package.suite_run_id,
            lock=lock_context,
        )
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
            ).trusted_success_manifest(
                package.suite_run_id,
                lock=lock_context,
            )
        except ValidationSuiteServiceError:
            return "evidence_integrity_failed", "trusted_reconstruction_failed"
        manifest = self._manifest(
            suite_run,
            trusted_result,
            entries,
            checkpoint=checkpoint,
            freshness_generation=package.freshness_generation,
        )
        manifest_digest = self._trusted_digest(manifest)
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
        latest_validation = self._reviews.latest_validation_run(
            plan_id=suite_run.plan_id,
            checkpoint_id=suite_run.checkpoint_id,
        )
        if latest_validation is not None and latest_validation.created_at > result.created_at:
            return "validation_facts_changed", str(latest_validation.id)
        latest_suite = self._reviews.latest_suite_run(
            plan_id=suite_run.plan_id,
            checkpoint_id=suite_run.checkpoint_id,
        )
        if (
            latest_suite is not None
            and latest_suite.id != suite_run.id
            and latest_suite.created_at > suite_run.created_at
        ):
            return "validation_facts_changed", str(latest_suite.id)
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
            review_package_id=package.id,
        )
        try:
            self._session.commit()
        except DBAPIError:
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
                package_version=readiness.package_version,
                freshness_generation=readiness.freshness_generation,
                package_digest=readiness.package_digest,
                decision_digest=readiness.decision_digest,
                evidence_manifest_digest=readiness.evidence_manifest_digest,
                suite_result_digest=readiness.suite_result_digest,
                policy_digest=readiness.policy_digest,
                blocker_summary_digest=readiness.blocker_summary_digest,
                critical_count=readiness.critical_count,
                high_count=readiness.high_count,
                blocking_medium_count=readiness.blocking_medium_count,
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
        scope = self._reviews.freshness_state_by_id(package.freshness_state_id)
        return ReviewPackageResponse(
            id=package.id,
            schema_version=package.schema_version,
            package_version=package.package_version,
            freshness_state_id=package.freshness_state_id,
            freshness_generation=package.freshness_generation,
            current_freshness_generation=(
                scope.generation if scope is not None else package.freshness_generation
            ),
            run_id=package.run_id,
            plan_id=package.plan_id,
            repository_handle_id=package.repository_handle_id,
            source_revision=package.source_revision,
            workspace_id=package.workspace_id,
            checkpoint_id=package.checkpoint_id,
            checkpoint_fingerprint=package.checkpoint_fingerprint,
            checkpoint_diff_hash=package.checkpoint_diff_hash,
            suite_run_id=package.suite_run_id,
            suite_result_id=package.suite_result_id,
            execution_grant_id=package.execution_grant_id,
            suite_policy_digest=package.suite_policy_digest,
            suite_result_digest=package.suite_result_digest,
            evidence_manifest=package.evidence_manifest,
            evidence_manifest_digest=package.evidence_manifest_digest,
            blocker_summary=package.blocker_summary,
            blocker_summary_digest=package.blocker_summary_digest,
            blocker_source=package.blocker_source,
            blocker_source_version=package.blocker_source_version,
            critical_count=package.critical_count,
            high_count=package.high_count,
            blocking_medium_count=package.blocking_medium_count,
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

    def _blocker_summary(
        self,
        *,
        suite_run: ValidationSuiteRun,
        result: ValidationSuiteResult,
        manifest_digest: str,
        freshness_generation: int,
        lock: bool,
    ) -> BlockerSummary:
        findings = self._reviews.blocker_findings(
            plan_id=suite_run.plan_id,
            workspace_id=suite_run.workspace_id,
            checkpoint_id=suite_run.checkpoint_id,
            lock=lock,
        )
        latest: dict[str, ReviewBlockerFinding] = {}
        for finding in findings:
            latest.setdefault(finding.finding_key, finding)
        active = sorted(
            (finding for finding in latest.values() if finding.status == "open"),
            key=lambda finding: finding.finding_key,
        )
        entries = [
            {
                "finding_key": finding.finding_key,
                "finding_version": finding.finding_version,
                "severity": finding.severity,
                "blocking": finding.blocking,
                "source": finding.source,
                "source_version": finding.source_version,
                "evidence_digest": finding.evidence_digest,
                "policy_digest": finding.policy_digest,
                "finding_digest": finding.finding_digest,
            }
            for finding in active
        ]
        return {
            "schema_version": 1,
            "source": "governed-review-security-findings",
            "source_version": max(
                (finding.source_version for finding in active),
                default=1,
            ),
            "plan_id": str(suite_run.plan_id),
            "workspace_id": str(suite_run.workspace_id),
            "checkpoint_id": str(suite_run.checkpoint_id),
            "suite_result_id": str(result.id),
            "suite_result_digest": result.aggregate_digest,
            "evidence_manifest_digest": manifest_digest,
            "policy_digest": suite_run.policy_digest,
            "freshness_generation": freshness_generation,
            "critical_count": sum(finding.severity == "critical" for finding in active),
            "high_count": sum(finding.severity == "high" for finding in active),
            "blocking_medium_count": sum(
                finding.severity == "medium" and finding.blocking for finding in active
            ),
            "findings": entries,
        }

    def _verify_package_integrity(self, package: ReviewPackage) -> None:
        context = self._reviews.suite_context(package.suite_run_id, lock=True)
        if context is None:
            self._policy(
                "review_evidence_integrity_failed",
                "Review Package trusted Suite context is missing",
            )
        suite_run, result, _workspace, checkpoint, _handle = context
        scope = self._reviews.freshness_state_by_id(package.freshness_state_id, lock=True)
        if (
            scope is None
            or scope.generation != package.freshness_generation
            or package.schema_version != 2
        ):
            self._conflict(
                "stale_review_package",
                "Review Package generation is not current",
            )
        try:
            trusted_suite, trusted_result, entries = ValidationSuiteService(
                self._session
            ).trusted_success_manifest(package.suite_run_id)
        except ValidationSuiteServiceError as exc:
            raise ReviewServiceError(exc.code, exc.message, category=exc.category) from exc
        if trusted_suite.id != suite_run.id or trusted_result.id != result.id:
            self._policy(
                "review_evidence_integrity_failed",
                "Trusted Suite proof changed during Review Package verification",
            )
        manifest = self._manifest(
            suite_run,
            result,
            entries,
            checkpoint=checkpoint,
            freshness_generation=package.freshness_generation,
        )
        manifest_digest = self._trusted_digest(manifest)
        summary = self._blocker_summary(
            suite_run=suite_run,
            result=result,
            manifest_digest=manifest_digest,
            freshness_generation=package.freshness_generation,
            lock=True,
        )
        summary_digest = self._trusted_digest(summary)
        package_payload = {
            "schema_version": 2,
            "package_id": str(package.id),
            "package_version": package.package_version,
            "freshness_state_id": str(package.freshness_state_id),
            "freshness_generation": package.freshness_generation,
            "run_id": str(package.run_id),
            "plan_id": str(package.plan_id),
            "repository_handle_id": str(package.repository_handle_id),
            "source_revision": package.source_revision,
            "workspace_id": str(package.workspace_id),
            "checkpoint_id": str(package.checkpoint_id),
            "checkpoint_fingerprint": package.checkpoint_fingerprint,
            "checkpoint_diff_hash": package.checkpoint_diff_hash,
            "suite_run_id": str(package.suite_run_id),
            "suite_result_id": str(package.suite_result_id),
            "execution_grant_id": str(package.execution_grant_id),
            "suite_policy_digest": package.suite_policy_digest,
            "suite_result_digest": package.suite_result_digest,
            "evidence_manifest_digest": package.evidence_manifest_digest,
            "blocker_summary_digest": package.blocker_summary_digest,
            "git_authorization": False,
            "deployment_authorization": False,
        }
        expected_counts = (
            summary["critical_count"],
            summary["high_count"],
            summary["blocking_medium_count"],
        )
        if (
            package.evidence_manifest != manifest
            or not hmac.compare_digest(package.evidence_manifest_digest, manifest_digest)
            or package.blocker_summary != summary
            or not hmac.compare_digest(package.blocker_summary_digest, summary_digest)
            or (
                package.critical_count,
                package.high_count,
                package.blocking_medium_count,
            )
            != expected_counts
            or not hmac.compare_digest(
                package.package_digest,
                self._trusted_digest(package_payload),
            )
        ):
            self._policy(
                "review_package_integrity_failed",
                "Review Package digest, Evidence, or blocker summary is inconsistent",
            )

    @staticmethod
    def _manifest(
        suite_run: ValidationSuiteRun,
        result: ValidationSuiteResult,
        entries: Sequence[dict[str, object]],
        *,
        checkpoint: WorkspaceCheckpoint | None = None,
        freshness_generation: int | None = None,
    ) -> dict[str, object]:
        manifest: dict[str, object] = {
            "schema_version": 2 if checkpoint is not None else 1,
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
        if checkpoint is not None and freshness_generation is not None:
            manifest.update(
                {
                    "plan_id": str(suite_run.plan_id),
                    "workspace_id": str(suite_run.workspace_id),
                    "suite_id": suite_run.suite_id,
                    "suite_version": suite_run.suite_version,
                    "policy_digest": suite_run.policy_digest,
                    "execution_grant_id": str(suite_run.execution_grant_id),
                    "root_suite_run_id": str(suite_run.root_suite_run_id),
                    "attempt_number": suite_run.attempt_number,
                    "checkpoint_diff_hash": checkpoint.diff_hash,
                    "profiles": result.profile_references,
                    "freshness_generation": freshness_generation,
                }
            )
        return manifest

    def _trusted_digest(self, value: object) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = self._session.scalar(
            text("SELECT review_canonical_digest(CAST(:payload AS jsonb))"),
            {"payload": encoded},
        )
        if not isinstance(digest, str):
            self._policy(
                "review_digest_unavailable",
                "Trusted review digest could not be reconstructed",
            )
        return digest

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
        review_package_id: uuid.UUID,
    ) -> None:
        self._session.add(
            AuditEvent(
                run_id=run_id,
                event_type=event_type,
                actor_type=("local_user" if event_type == "review_decision_recorded" else "system"),
                request_id=request_id,
                details=details,
                review_package_id=review_package_id,
                review_sequence=self._reviews.next_review_event_sequence(review_package_id),
            )
        )

    def _required_package(self, package_id: uuid.UUID, *, lock: bool = False) -> ReviewPackage:
        package = self._reviews.package(package_id, lock=lock)
        if package is None:
            self._not_found("review_package_not_found", "Review Package was not found")
        return package

    def _required_package_with_revision_authority(self, package_id: uuid.UUID) -> ReviewPackage:
        package = self._required_package(package_id)
        self._reviews.lock_revision_authority(package.repository_handle_id)
        authority = self._reviews.revision_authority(
            package.repository_handle_id,
            lock=True,
        )
        if authority is None:
            self._conflict(
                "review_revision_authority_missing",
                "Review Package trusted Repository revision authority is missing",
            )
        return self._required_package(package_id, lock=True)

    @staticmethod
    def _not_found(code: str, message: str) -> NoReturn:
        raise ReviewServiceError(code, message, category="not_found")

    @staticmethod
    def _conflict(code: str, message: str) -> NoReturn:
        raise ReviewServiceError(code, message, category="conflict")

    @staticmethod
    def _policy(code: str, message: str) -> NoReturn:
        raise ReviewServiceError(code, message, category="policy")
