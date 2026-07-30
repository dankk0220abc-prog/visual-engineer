from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from collections.abc import Sequence
from datetime import timedelta
from typing import NoReturn

from pydantic import ValidationError
from sqlalchemy.orm import Session

from visual_engineer_api.models.run import AuditEvent
from visual_engineer_api.models.validation import (
    ValidationEvidence,
    ValidationSuiteResult,
    ValidationSuiteRun,
    ValidationSuiteStepRun,
)
from visual_engineer_api.models.workspace import (
    ExecutionGrant,
    RepositoryHandle,
    Workspace,
    WorkspaceCheckpoint,
)
from visual_engineer_api.repositories.validation import ValidationRepository
from visual_engineer_api.schemas.validation import (
    ValidationEvidenceResponse,
    ValidationRunCreate,
    ValidationSuiteAggregateResponse,
    ValidationSuiteCatalogStepResponse,
    ValidationSuiteListResponse,
    ValidationSuiteResponse,
    ValidationSuiteRetryCreate,
    ValidationSuiteRunCreate,
    ValidationSuiteRunListResponse,
    ValidationSuiteRunResponse,
    ValidationSuiteStepRunResponse,
    ValidationSuiteTimelineResponse,
)
from visual_engineer_api.services.validation import (
    ValidationService,
    ValidationServiceError,
    utc_now,
)
from visual_engineer_runner_protocol import (
    VALIDATION_SUITE_CATALOG,
    ValidationExecuteJobSpec,
    ValidationExecutionResult,
    WorkspaceOperation,
    compute_validation_evidence_digest,
    compute_validation_policy_digest,
    execution_grant_policy_hash_matches,
    validation_profile,
    validation_suite,
)

_TERMINAL_STATES = {
    "succeeded",
    "failed",
    "timed_out",
    "cancelled",
    "recovery_required",
}
_ACTIVE_STEP_STATES = {"queued", "running"}
_TERMINAL_STEP_STATES = {
    "succeeded",
    "failed",
    "timed_out",
    "cancelled",
    "skipped",
    "recovery_required",
}


class ValidationSuiteServiceError(Exception):
    def __init__(self, code: str, message: str, *, category: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


class ValidationSuiteService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._validation = ValidationRepository(session)

    def catalog(self) -> ValidationSuiteListResponse:
        items = [
            ValidationSuiteResponse(
                suite_id=suite.suite_id,
                suite_version=suite.version,
                name=suite.name,
                purpose=suite.purpose,
                steps=[
                    ValidationSuiteCatalogStepResponse(
                        sequence=step.sequence,
                        step_id=step.step_id,
                        profile_id=step.profile_id,
                        profile_version=step.profile_version,
                        timeout_seconds=step.timeout_seconds,
                        max_output_bytes=step.max_output_bytes,
                    )
                    for step in suite.steps
                ],
                failure_policy="fail_fast",
                total_timeout_seconds=suite.total_timeout_seconds,
                total_output_bytes=suite.total_output_bytes,
                max_attempts=suite.max_attempts,
                policy_digest=suite.policy_digest,
            )
            for suite in VALIDATION_SUITE_CATALOG.values()
        ]
        return ValidationSuiteListResponse(items=items, total=len(items))

    def create(
        self,
        payload: ValidationSuiteRunCreate,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> ValidationSuiteRunResponse:
        request_hash = self._request_hash(payload.model_dump(mode="json"))
        replay = self._validation.get_suite_by_idempotency(
            idempotency_key,
            lock=True,
        )
        if replay is not None:
            if replay.idempotency_request_hash != request_hash:
                self._conflict(
                    "suite_idempotency_conflict",
                    "Idempotency-Key is associated with a different Suite request",
                )
            return self._response(self._sync(replay))

        suite = validation_suite(payload.suite_id)
        if suite is None or suite.version != payload.suite_version:
            raise ValidationSuiteServiceError(
                "validation_suite_denied",
                "Validation Suite ID/version is not in the system-owned catalog",
                category="policy",
            )
        grant, checkpoint, workspace, _handle = self._required_suite_grant(
            payload.execution_grant_id,
            suite.reference,
            expected_attempt_number=1,
            expected_root_suite_run_id=None,
            expected_retry_of_suite_run_id=None,
        )
        replay = self._validation.get_suite_by_idempotency(
            idempotency_key,
            lock=True,
        )
        if replay is not None:
            if replay.idempotency_request_hash != request_hash:
                self._conflict(
                    "suite_idempotency_conflict",
                    "Idempotency-Key is associated with a different Suite request",
                )
            return self._response(self._sync(replay))
        consumed = self._validation.get_suite_by_grant(grant.id, lock=True)
        if consumed is not None:
            self._conflict(
                "validation_suite_grant_already_consumed",
                "Suite-scoped Execution Grant already authorizes a Suite lineage",
            )
        now = utc_now()
        run_id = uuid.uuid4()
        policy_digest = compute_validation_policy_digest(
            {
                "suite_definition_digest": suite.policy_digest,
                "grant_policy_hash": grant.policy_hash,
                "workspace_id": str(workspace.id),
                "checkpoint_id": str(checkpoint.id),
                "checkpoint_fingerprint": checkpoint.tree_fingerprint,
                "source_revision": checkpoint.source_revision,
                "total_timeout_seconds": suite.total_timeout_seconds,
                "total_output_bytes": suite.total_output_bytes,
                "max_attempts": suite.max_attempts,
            }
        )
        suite_run = ValidationSuiteRun(
            id=run_id,
            run_id=grant.run_id,
            plan_id=grant.plan_id,
            source_revision=grant.source_revision,
            workspace_id=workspace.id,
            checkpoint_id=checkpoint.id,
            checkpoint_fingerprint=checkpoint.tree_fingerprint,
            execution_grant_id=grant.id,
            suite_id=suite.suite_id,
            suite_version=suite.version,
            policy_digest=policy_digest,
            failure_policy=suite.failure_policy,
            state="requested",
            step_count=len(suite.steps),
            completed_step_count=0,
            total_timeout_seconds=suite.total_timeout_seconds,
            total_output_bytes=suite.total_output_bytes,
            combined_output_bytes=0,
            max_attempts=suite.max_attempts,
            attempt_number=1,
            idempotency_key=idempotency_key,
            idempotency_request_hash=request_hash,
            root_suite_run_id=run_id,
            requested_at=now,
            version=1,
        )
        self._validation.add(suite_run)
        for definition in suite.steps:
            self._validation.add(
                ValidationSuiteStepRun(
                    suite_run_id=run_id,
                    sequence=definition.sequence,
                    step_id=definition.step_id,
                    profile_id=definition.profile_id,
                    profile_version=definition.profile_version,
                    timeout_seconds=definition.timeout_seconds,
                    max_output_bytes=definition.max_output_bytes,
                    state="pending",
                )
            )
        self._audit(
            suite_run,
            "validation_suite_requested",
            request_id=request_id,
            details={
                "suite": suite.reference,
                "policy_digest": policy_digest,
                "attempt_number": 1,
            },
        )
        self._session.commit()
        self._dispatch_next(suite_run.id, request_id=request_id)
        current = self._required_run(suite_run.id, lock=True)
        return self._response(current)

    def list(
        self,
        *,
        workspace_id: uuid.UUID | None = None,
    ) -> ValidationSuiteRunListResponse:
        responses = [
            self._response(self._sync(item))
            for item in self._validation.list_suite_runs(workspace_id=workspace_id)
        ]
        return ValidationSuiteRunListResponse(items=responses, total=len(responses))

    def get(self, suite_run_id: uuid.UUID) -> ValidationSuiteRunResponse:
        return self._response(self._sync(self._required_run(suite_run_id)))

    def timeline(self, suite_run_id: uuid.UUID) -> ValidationSuiteTimelineResponse:
        response = self.get(suite_run_id)
        return ValidationSuiteTimelineResponse(
            suite_run_id=response.id,
            state=response.state,
            steps=response.steps,
        )

    def aggregate(self, suite_run_id: uuid.UUID) -> ValidationSuiteAggregateResponse:
        response = self.get(suite_run_id)
        return ValidationSuiteAggregateResponse(
            suite_run_id=response.id,
            state=response.state,
            result=response.result,
        )

    def cancel(
        self,
        suite_run_id: uuid.UUID,
        *,
        request_id: str,
    ) -> ValidationSuiteRunResponse:
        synchronized = self._required_run(suite_run_id, lock=True)
        if synchronized.state == "cancelled":
            return self._response(synchronized)
        if synchronized.state in _TERMINAL_STATES:
            self._conflict(
                "validation_suite_terminal",
                "A terminal Validation Suite Run cannot be cancelled",
            )
        if synchronized.state != "cancel_requested":
            synchronized.state = "cancel_requested"
            synchronized.cancel_requested_at = utc_now()
            synchronized.version += 1
            self._audit(
                synchronized,
                "validation_suite_cancel_requested",
                request_id=request_id,
                details={"attempt_number": synchronized.attempt_number},
            )
            self._session.commit()

        steps = self._validation.suite_steps(suite_run_id)
        for step in steps:
            if step.state in _ACTIVE_STEP_STATES and step.validation_run_id is not None:
                try:
                    ValidationService(self._session).cancel(
                        step.validation_run_id,
                        request_id=request_id,
                    )
                except ValidationServiceError as exc:
                    if exc.code != "validation_run_terminal":
                        raise ValidationSuiteServiceError(
                            exc.code,
                            exc.message,
                            category=exc.category,
                        ) from exc
        return self._response(self._sync(self._required_run(suite_run_id)))

    def retry(
        self,
        suite_run_id: uuid.UUID,
        payload: ValidationSuiteRetryCreate,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> ValidationSuiteRunResponse:
        source = self._sync(self._required_run(suite_run_id))
        if source.state not in {
            "failed",
            "timed_out",
            "cancelled",
            "recovery_required",
        }:
            self._conflict(
                "validation_suite_retry_not_allowed",
                "Only a terminal non-success Suite Run can be retried",
            )
        root = self._required_run(source.root_suite_run_id, lock=True)
        attempt_number = source.attempt_number + 1
        if attempt_number > source.max_attempts:
            self._conflict(
                "validation_suite_attempt_budget_exhausted",
                "Validation Suite retry attempt budget is exhausted",
            )
        if payload.execution_grant_id == source.execution_grant_id:
            raise ValidationSuiteServiceError(
                "validation_suite_new_grant_required",
                "Retry requires a newly approved Suite-scoped Execution Grant",
                category="policy",
            )
        replay_payload = {
            "source_suite_run_id": str(source.id),
            "execution_grant_id": str(payload.execution_grant_id),
            "attempt_number": attempt_number,
        }
        request_hash = self._request_hash(replay_payload)
        replay = self._validation.get_suite_by_idempotency(
            idempotency_key,
            lock=True,
        )
        if replay is not None:
            if replay.idempotency_request_hash != request_hash:
                self._conflict(
                    "suite_idempotency_conflict",
                    "Idempotency-Key is associated with a different Suite retry",
                )
            return self._response(self._sync(replay))
        suite = validation_suite(source.suite_id)
        if suite is None or suite.version != source.suite_version:
            raise ValidationSuiteServiceError(
                "validation_suite_definition_unavailable",
                "The immutable Suite definition is unavailable",
                category="policy",
            )
        grant, checkpoint, workspace, _ = self._required_suite_grant(
            payload.execution_grant_id,
            suite.reference,
            expected_attempt_number=attempt_number,
            expected_root_suite_run_id=root.id,
            expected_retry_of_suite_run_id=source.id,
        )
        replay = self._validation.get_suite_by_idempotency(
            idempotency_key,
            lock=True,
        )
        if replay is not None:
            if replay.idempotency_request_hash != request_hash:
                self._conflict(
                    "suite_idempotency_conflict",
                    "Idempotency-Key is associated with a different Suite retry",
                )
            return self._response(self._sync(replay))
        consumed = self._validation.get_suite_by_grant(grant.id, lock=True)
        if consumed is not None:
            self._conflict(
                "validation_suite_grant_already_consumed",
                "Suite-scoped Execution Grant already authorizes a Suite lineage",
            )
        if self._validation.suite_retry(root.id, attempt_number) is not None:
            self._conflict(
                "validation_suite_retry_exists",
                "This Suite attempt already exists",
            )
        if (
            source.run_id != grant.run_id
            or source.plan_id != grant.plan_id
            or source.source_revision != grant.source_revision
            or source.workspace_id != workspace.id
            or source.checkpoint_id != checkpoint.id
            or source.checkpoint_fingerprint != checkpoint.tree_fingerprint
        ):
            raise ValidationSuiteServiceError(
                "validation_suite_retry_binding_mismatch",
                "Retry Grant does not bind the original exact Suite baseline",
                category="policy",
            )
        now = utc_now()
        retry_run = ValidationSuiteRun(
            id=uuid.uuid4(),
            run_id=source.run_id,
            plan_id=source.plan_id,
            source_revision=source.source_revision,
            workspace_id=source.workspace_id,
            checkpoint_id=source.checkpoint_id,
            checkpoint_fingerprint=source.checkpoint_fingerprint,
            execution_grant_id=grant.id,
            suite_id=source.suite_id,
            suite_version=source.suite_version,
            policy_digest=compute_validation_policy_digest(
                {
                    "suite_definition_digest": suite.policy_digest,
                    "grant_policy_hash": grant.policy_hash,
                    "workspace_id": str(workspace.id),
                    "checkpoint_id": str(checkpoint.id),
                    "checkpoint_fingerprint": checkpoint.tree_fingerprint,
                    "source_revision": checkpoint.source_revision,
                    "total_timeout_seconds": suite.total_timeout_seconds,
                    "total_output_bytes": suite.total_output_bytes,
                    "max_attempts": suite.max_attempts,
                    "attempt_number": attempt_number,
                    "retry_of_suite_run_id": str(root.id),
                }
            ),
            failure_policy=source.failure_policy,
            state="requested",
            step_count=source.step_count,
            completed_step_count=0,
            total_timeout_seconds=source.total_timeout_seconds,
            total_output_bytes=source.total_output_bytes,
            combined_output_bytes=0,
            max_attempts=source.max_attempts,
            attempt_number=attempt_number,
            retry_of_suite_run_id=source.id,
            root_suite_run_id=root.id,
            idempotency_key=idempotency_key,
            idempotency_request_hash=request_hash,
            requested_at=now,
            version=1,
        )
        self._validation.add(retry_run)
        source_steps = self._validation.suite_steps(source.id)
        for source_step in source_steps:
            reused = (
                source_step.state == "succeeded"
                and source_step.validation_run_id is not None
                and source_step.evidence_id is not None
            )
            self._validation.add(
                ValidationSuiteStepRun(
                    suite_run_id=retry_run.id,
                    sequence=source_step.sequence,
                    step_id=source_step.step_id,
                    profile_id=source_step.profile_id,
                    profile_version=source_step.profile_version,
                    timeout_seconds=source_step.timeout_seconds,
                    max_output_bytes=source_step.max_output_bytes,
                    state="succeeded" if reused else "pending",
                    validation_run_id=source_step.validation_run_id if reused else None,
                    runner_job_id=source_step.runner_job_id if reused else None,
                    runner_id=source_step.runner_id if reused else None,
                    attempt_id=source_step.attempt_id if reused else None,
                    lease_id=source_step.lease_id if reused else None,
                    evidence_id=source_step.evidence_id if reused else None,
                    reused_from_step_run_id=source_step.id if reused else None,
                    started_at=source_step.started_at if reused else None,
                    completed_at=now if reused else None,
                    duration_ms=source_step.duration_ms if reused else None,
                    exit_code=source_step.exit_code if reused else None,
                    output_bytes=0,
                    redaction_count=0,
                    output_truncated=source_step.output_truncated if reused else False,
                    cleanup_succeeded=source_step.cleanup_succeeded if reused else None,
                )
            )
            if reused:
                retry_run.completed_step_count += 1
        self._audit(
            retry_run,
            "validation_suite_retry_requested",
            request_id=request_id,
            details={
                "root_suite_run_id": str(root.id),
                "source_suite_run_id": str(source.id),
                "attempt_number": attempt_number,
            },
        )
        self._session.commit()
        self._dispatch_next(retry_run.id, request_id=request_id)
        return self._response(self._required_run(retry_run.id))

    def _sync(self, suite_run: ValidationSuiteRun) -> ValidationSuiteRun:
        if suite_run.state in _TERMINAL_STATES:
            return suite_run
        active = [
            step
            for step in self._validation.suite_steps(suite_run.id)
            if step.state in _ACTIVE_STEP_STATES and step.validation_run_id is not None
        ]
        child_responses = {}
        for step in active:
            child_run_id = step.validation_run_id
            if child_run_id is None:
                continue
            try:
                child_responses[step.id] = ValidationService(self._session).get(child_run_id)
            except ValidationServiceError as exc:
                raise ValidationSuiteServiceError(
                    exc.code,
                    exc.message,
                    category=exc.category,
                ) from exc

        current = self._required_run(suite_run.id, lock=True)
        if current.state in _TERMINAL_STATES:
            return current
        steps = self._validation.suite_steps(current.id, lock=True)
        for step in steps:
            child = child_responses.get(step.id)
            if child is None:
                continue
            step.runner_job_id = child.runner_job_id
            step.runner_id = child.runner_id
            step.attempt_id = child.attempt_id
            step.lease_id = child.lease_id
            step.started_at = child.started_at
            if child.state in {"queued", "claimed"}:
                if current.state != "running":
                    current.state = "queued"
            elif child.state == "running":
                current.state = "running"
                step.state = "running"
            elif child.state in _TERMINAL_STATES:
                evidence = child.evidence
                output_bytes = (
                    len(evidence.stdout.encode("utf-8")) + len(evidence.stderr.encode("utf-8"))
                    if evidence is not None
                    else 0
                )
                step.state = child.state.value
                step.completed_at = child.completed_at or utc_now()
                step.duration_ms = evidence.duration_ms if evidence is not None else None
                step.exit_code = evidence.exit_code if evidence is not None else None
                step.output_bytes = output_bytes
                step.redaction_count = evidence.redaction_count if evidence is not None else 0
                step.output_truncated = (
                    evidence.stdout_truncated or evidence.stderr_truncated
                    if evidence is not None
                    else False
                )
                step.cleanup_succeeded = (
                    evidence.sandbox_cleaned if evidence is not None else child.state == "cancelled"
                )
                step.failure_code = child.error_code
                step.evidence_id = evidence.id if evidence is not None else None

        current.completed_step_count = sum(step.state in _TERMINAL_STEP_STATES for step in steps)
        current.combined_output_bytes = sum(step.output_bytes for step in steps)
        current.version += 1
        now = utc_now()

        if current.state == "cancel_requested":
            active_remaining = any(step.state in _ACTIVE_STEP_STATES for step in steps)
            if not active_remaining:
                for step in steps:
                    if step.state == "pending":
                        step.state = "cancelled"
                        step.completed_at = now
                timed_out = current.error_code == "validation_suite_timed_out"
                self._finalize(
                    current,
                    steps,
                    verdict="timed_out" if timed_out else "cancelled",
                    error_code=(
                        "validation_suite_timed_out" if timed_out else "validation_suite_cancelled"
                    ),
                    error_message=(
                        "Validation Suite total timeout was exceeded"
                        if timed_out
                        else "Validation Suite cancellation completed"
                    ),
                )
            self._session.commit()
            return current

        if current.deadline_at is not None and now > current.deadline_at:
            for step in steps:
                if step.state == "pending":
                    step.state = "skipped"
                    step.completed_at = now
                    step.failure_code = "validation_suite_timed_out"
            active_run_ids = [
                step.validation_run_id
                for step in steps
                if step.state in _ACTIVE_STEP_STATES and step.validation_run_id is not None
            ]
            if active_run_ids:
                current.state = "cancel_requested"
                current.cancel_requested_at = now
                current.error_code = "validation_suite_timed_out"
                current.error_message = "Validation Suite total timeout was exceeded"
                current.version += 1
                self._audit(
                    current,
                    "validation_suite_timeout_cancellation_requested",
                    request_id="suite-orchestration",
                    details={
                        "attempt_number": current.attempt_number,
                        "active_child_count": len(active_run_ids),
                    },
                )
                self._session.commit()
                for child_run_id in active_run_ids:
                    try:
                        ValidationService(self._session).cancel(
                            child_run_id,
                            request_id="suite-orchestration",
                        )
                    except ValidationServiceError as exc:
                        if exc.code != "validation_run_terminal":
                            raise ValidationSuiteServiceError(
                                exc.code,
                                exc.message,
                                category=exc.category,
                            ) from exc
                return self._sync(self._required_run(current.id))
            self._finalize(
                current,
                steps,
                verdict="timed_out",
                error_code="validation_suite_timed_out",
                error_message="Validation Suite total timeout was exceeded",
            )
            self._session.commit()
            return current

        overflow = next(
            (step for step in steps if step.output_bytes > step.max_output_bytes),
            None,
        )
        if overflow is not None or current.combined_output_bytes > current.total_output_bytes:
            for step in steps:
                if step.state == "pending":
                    step.state = "skipped"
                    step.completed_at = now
                    step.failure_code = "validation_suite_output_limit_exceeded"
            self._finalize(
                current,
                steps,
                verdict="failed",
                error_code="validation_suite_output_limit_exceeded",
                error_message="Validation Suite output budget was exceeded",
            )
            self._session.commit()
            return current

        failed = next(
            (
                step
                for step in steps
                if step.state
                in {
                    "failed",
                    "timed_out",
                    "cancelled",
                    "recovery_required",
                }
            ),
            None,
        )
        if failed is not None:
            for step in steps:
                if step.state == "pending":
                    step.state = "skipped"
                    step.completed_at = now
                    step.failure_code = "validation_suite_fail_fast"
            verdict = (
                "recovery_required"
                if failed.state == "recovery_required"
                else "timed_out"
                if failed.state == "timed_out"
                else "cancelled"
                if failed.state == "cancelled"
                else "failed"
            )
            self._finalize(
                current,
                steps,
                verdict=verdict,
                error_code=failed.failure_code or f"validation_suite_{verdict}",
                error_message=f"Validation Suite stopped at step {failed.sequence}",
            )
            self._session.commit()
            return current

        if all(step.state == "succeeded" for step in steps):
            self._finalize(
                current,
                steps,
                verdict="succeeded",
                error_code=None,
                error_message=None,
            )
            self._session.commit()
            return current

        self._session.commit()
        if not any(step.state in _ACTIVE_STEP_STATES for step in steps):
            self._dispatch_next(current.id, request_id="suite-orchestration")
        return self._required_run(current.id)

    def _dispatch_next(self, suite_run_id: uuid.UUID, *, request_id: str) -> None:
        probe = self._validation.get_suite_run(suite_run_id)
        if probe is None:
            return
        grant_context = self._validation.validation_grant(
            probe.execution_grant_id,
            lock=True,
        )
        if grant_context is None:
            return
        current = self._required_run(suite_run_id, lock=True)
        if current.state in _TERMINAL_STATES or current.state == "cancel_requested":
            return
        steps = self._validation.suite_steps(current.id, lock=True)
        if any(step.state in _ACTIVE_STEP_STATES for step in steps):
            return
        pending = next((step for step in steps if step.state == "pending"), None)
        if pending is None:
            return
        now = utc_now()
        if current.started_at is None:
            current.started_at = now
            current.deadline_at = now + timedelta(seconds=current.total_timeout_seconds)
            current.state = "queued"
        current.version += 1

        try:
            child = ValidationService(self._session).create(
                ValidationRunCreate(
                    execution_grant_id=current.execution_grant_id,
                    profile_id=pending.profile_id,
                ),
                idempotency_key=(
                    f"suite:{current.id}:attempt:{current.attempt_number}:step:{pending.sequence}"
                ),
                request_id=request_id,
                suite_dispatch_ref=f"{current.suite_id}:v{current.suite_version}",
            )
        except ValidationServiceError as exc:
            failed_run = self._required_run(suite_run_id, lock=True)
            failed_steps = self._validation.suite_steps(suite_run_id, lock=True)
            failed_step = next(step for step in failed_steps if step.id == pending.id)
            failed_step.state = "recovery_required"
            failed_step.completed_at = utc_now()
            failed_step.failure_code = exc.code
            self._finalize(
                failed_run,
                failed_steps,
                verdict="recovery_required",
                error_code=exc.code,
                error_message=exc.message,
            )
            self._session.commit()
            return

        rebound = self._required_run(suite_run_id, lock=True)
        rebound_steps = self._validation.suite_steps(suite_run_id, lock=True)
        rebound_step = next(step for step in rebound_steps if step.id == pending.id)
        if rebound.state == "cancel_requested":
            try:
                ValidationService(self._session).cancel(
                    child.id,
                    request_id=request_id,
                )
            except ValidationServiceError:
                pass
            return
        rebound_step.validation_run_id = child.id
        rebound_step.runner_job_id = child.runner_job_id
        rebound_step.state = "queued"
        rebound.version += 1
        self._session.commit()

    def _finalize(
        self,
        suite_run: ValidationSuiteRun,
        steps: Sequence[ValidationSuiteStepRun],
        *,
        verdict: str,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        if self._validation.suite_result(suite_run.id) is not None:
            return
        now = utc_now()
        started_at = suite_run.started_at or suite_run.requested_at
        evidence_references: list[dict[str, object]] = []
        runner_references: list[str] = []
        redaction_count = 0
        output_truncated = False
        cleanup_succeeded = True
        profile_references: list[str] = []
        trusted_output_bytes = 0
        trusted_success = True
        for step in steps:
            profile_references.append(f"{step.profile_id}:v{step.profile_version}")
            if step.state == "succeeded":
                trusted = self._trusted_success_step(suite_run, step)
                if trusted is None:
                    trusted_success = False
                    continue
                reference, evidence = trusted
                evidence_references.append(reference)
                runner_references.append(str(evidence.runner_id))
                if step.reused_from_step_run_id is None:
                    trusted_output_bytes += len(evidence.stdout.encode("utf-8")) + len(
                        evidence.stderr.encode("utf-8")
                    )
                    redaction_count += evidence.redaction_count
                output_truncated = (
                    output_truncated or evidence.stdout_truncated or evidence.stderr_truncated
                )
                cleanup_succeeded = cleanup_succeeded and evidence.sandbox_cleaned
            else:
                cleanup_succeeded = cleanup_succeeded and step.cleanup_succeeded is not False
        if verdict == "succeeded":
            suite_run.combined_output_bytes = trusted_output_bytes
        invariant = self._baseline_is_current(suite_run)
        if verdict == "succeeded" and (
            not trusted_success
            or len(evidence_references) != len(steps)
            or not invariant
            or not cleanup_succeeded
            or suite_run.combined_output_bytes > suite_run.total_output_bytes
            or any(step.state != "succeeded" for step in steps)
        ):
            verdict = "recovery_required"
            error_code = "validation_suite_aggregate_rejected"
            error_message = "Control Plane rejected inconsistent Suite success"
        suite_run.state = verdict
        suite_run.completed_at = now
        suite_run.completed_step_count = sum(step.state in _TERMINAL_STEP_STATES for step in steps)
        suite_run.error_code = error_code
        suite_run.error_message = error_message
        suite_run.version += 1
        audit = self._audit(
            suite_run,
            "validation_suite_terminal",
            request_id="suite-orchestration",
            details={
                "verdict": verdict,
                "combined_output_bytes": suite_run.combined_output_bytes,
                "step_count": len(steps),
            },
        )
        self._session.flush()
        aggregate_payload = {
            "suite_run_id": str(suite_run.id),
            "suite": f"{suite_run.suite_id}:v{suite_run.suite_version}",
            "policy_digest": suite_run.policy_digest,
            "source_revision": suite_run.source_revision,
            "checkpoint_id": str(suite_run.checkpoint_id),
            "checkpoint_fingerprint": suite_run.checkpoint_fingerprint,
            "attempt_number": suite_run.attempt_number,
            "root_suite_run_id": str(suite_run.root_suite_run_id),
            "execution_grant_id": str(suite_run.execution_grant_id),
            "verdict": verdict,
            "profiles": profile_references,
            "evidence": evidence_references,
            "runners": runner_references,
            "combined_output_bytes": suite_run.combined_output_bytes,
            "redaction_count": redaction_count,
            "output_truncated": output_truncated,
            "cleanup_succeeded": cleanup_succeeded,
            "source_invariant": invariant,
            "canonical_workspace_invariant": invariant,
            "artifact_count": 0,
            "artifact_bytes": 0,
            "budgets": {
                "total_timeout_seconds": suite_run.total_timeout_seconds,
                "total_output_bytes": suite_run.total_output_bytes,
                "max_attempts": suite_run.max_attempts,
            },
        }
        self._validation.add(
            ValidationSuiteResult(
                suite_run_id=suite_run.id,
                root_suite_run_id=suite_run.root_suite_run_id,
                run_id=suite_run.run_id,
                execution_grant_id=suite_run.execution_grant_id,
                suite_id=suite_run.suite_id,
                suite_version=suite_run.suite_version,
                source_revision=suite_run.source_revision,
                checkpoint_id=suite_run.checkpoint_id,
                policy_digest=suite_run.policy_digest,
                attempt_number=suite_run.attempt_number,
                total_timeout_seconds=suite_run.total_timeout_seconds,
                total_output_bytes=suite_run.total_output_bytes,
                max_attempts=suite_run.max_attempts,
                verdict=verdict,
                profile_references=profile_references,
                evidence_references=evidence_references,
                runner_references=runner_references,
                audit_event_references=[str(audit.id)],
                started_at=started_at,
                completed_at=now,
                duration_ms=max(
                    0,
                    round((now - started_at).total_seconds() * 1000),
                ),
                combined_output_bytes=suite_run.combined_output_bytes,
                redaction_count=redaction_count,
                output_truncated=output_truncated,
                timed_out=verdict == "timed_out",
                cancelled=verdict == "cancelled",
                recovery_required=verdict == "recovery_required",
                cleanup_succeeded=cleanup_succeeded,
                source_invariant=invariant,
                canonical_workspace_invariant=invariant,
                artifact_count=0,
                artifact_bytes=0,
                aggregate_digest=compute_validation_policy_digest(aggregate_payload),
            )
        )

    def _trusted_success_step(
        self,
        suite_run: ValidationSuiteRun,
        step: ValidationSuiteStepRun,
        *,
        lock: bool = True,
    ) -> tuple[dict[str, object], ValidationEvidence] | None:
        suite = validation_suite(suite_run.suite_id)
        if suite is None or suite.version != suite_run.suite_version:
            return None
        definitions = {item.sequence: item for item in suite.steps}
        definition = definitions.get(step.sequence)
        if (
            definition is None
            or len(definitions) != suite_run.step_count
            or step.step_id != definition.step_id
            or step.profile_id != definition.profile_id
            or step.profile_version != definition.profile_version
            or step.timeout_seconds != definition.timeout_seconds
            or step.max_output_bytes != definition.max_output_bytes
            or step.state != "succeeded"
            or step.validation_run_id is None
            or step.runner_job_id is None
            or step.runner_id is None
            or step.attempt_id is None
            or step.lease_id is None
            or step.evidence_id is None
            or step.cleanup_succeeded is not True
            or step.exit_code != 0
        ):
            return None

        proof_suite = suite_run
        proof_step = step
        if step.reused_from_step_run_id is not None:
            source_step = self._validation.suite_step(
                step.reused_from_step_run_id,
                lock=lock,
            )
            if source_step is None:
                return None
            source_suite = self._validation.get_suite_run(
                source_step.suite_run_id,
                lock=lock,
            )
            if (
                source_suite is None
                or source_suite.root_suite_run_id != suite_run.root_suite_run_id
                or source_suite.attempt_number >= suite_run.attempt_number
                or source_step.reused_from_step_run_id is not None
                or source_step.sequence != step.sequence
                or source_step.step_id != step.step_id
                or source_step.profile_id != step.profile_id
                or source_step.profile_version != step.profile_version
                or source_step.state != "succeeded"
                or source_step.validation_run_id != step.validation_run_id
                or source_step.runner_job_id != step.runner_job_id
                or source_step.runner_id != step.runner_id
                or source_step.attempt_id != step.attempt_id
                or source_step.lease_id != step.lease_id
                or source_step.evidence_id != step.evidence_id
                or step.output_bytes != 0
                or step.redaction_count != 0
            ):
                return None
            proof_suite = source_suite
            proof_step = source_step

        validation_run = self._validation.get_run(step.validation_run_id, lock=lock)
        evidence = self._validation.evidence_by_id(step.evidence_id, lock=lock)
        job = self._validation.job(step.runner_job_id)
        attempt = self._validation.attempt(step.attempt_id)
        if (
            validation_run is None
            or evidence is None
            or job is None
            or attempt is None
            or evidence.side_effect_permit_id is None
        ):
            return None
        permit = self._validation.permit(evidence.side_effect_permit_id)
        grant_context = self._validation.validation_grant(
            validation_run.execution_grant_id,
            lock=lock,
        )
        profile = validation_profile(step.profile_id)
        if permit is None or grant_context is None or profile is None:
            return None
        grant, checkpoint, workspace, handle = grant_context

        expected_root_binding = (
            None if proof_suite.attempt_number == 1 else proof_suite.root_suite_run_id
        )
        expected_retry_binding = (
            None if proof_suite.attempt_number == 1 else proof_suite.retry_of_suite_run_id
        )
        if (
            proof_suite.run_id != suite_run.run_id
            or proof_suite.plan_id != suite_run.plan_id
            or proof_suite.source_revision != suite_run.source_revision
            or proof_suite.workspace_id != suite_run.workspace_id
            or proof_suite.checkpoint_id != suite_run.checkpoint_id
            or proof_suite.checkpoint_fingerprint != suite_run.checkpoint_fingerprint
            or proof_suite.suite_id != suite_run.suite_id
            or proof_suite.suite_version != suite_run.suite_version
            or grant.id != proof_suite.execution_grant_id
            or grant.allowed_validation_suites != [suite.reference]
            or grant.allowed_validation_profiles != [item.profile_reference for item in suite.steps]
            or grant.validation_suite_definition_digest != suite.policy_digest
            or grant.validation_suite_root_run_id != expected_root_binding
            or grant.validation_suite_retry_of_run_id != expected_retry_binding
            or grant.validation_suite_attempt_number != proof_suite.attempt_number
            or grant.validation_suite_allowed_run_count != 1
            or grant.max_validation_runs != len(suite.steps)
            or checkpoint.id != suite_run.checkpoint_id
            or checkpoint.tree_fingerprint != suite_run.checkpoint_fingerprint
            or checkpoint.source_revision != suite_run.source_revision
            or workspace.id != suite_run.workspace_id
            or workspace.current_tree_hash != suite_run.checkpoint_fingerprint
            or workspace.source_revision != suite_run.source_revision
        ):
            return None
        try:
            grant_policy = ValidationService(self._session)._policy(grant, handle)
        except ValidationServiceError:
            return None
        if not execution_grant_policy_hash_matches(
            grant_policy, grant.policy_hash
        ) or proof_suite.policy_digest != self._suite_policy_digest(
            proof_suite, suite.policy_digest, grant.policy_hash
        ):
            return None

        if (
            validation_run.id != proof_step.validation_run_id
            or validation_run.run_id != proof_suite.run_id
            or validation_run.plan_id != proof_suite.plan_id
            or validation_run.source_revision != proof_suite.source_revision
            or validation_run.workspace_id != proof_suite.workspace_id
            or validation_run.checkpoint_id != proof_suite.checkpoint_id
            or validation_run.checkpoint_fingerprint != proof_suite.checkpoint_fingerprint
            or validation_run.execution_grant_id != grant.id
            or validation_run.runner_job_id != job.id
            or validation_run.runner_id != evidence.runner_id
            or validation_run.attempt_id != evidence.attempt_id
            or validation_run.lease_id != evidence.lease_id
            or validation_run.profile_id != definition.profile_id
            or validation_run.profile_version != definition.profile_version
            or validation_run.timeout_seconds != definition.timeout_seconds
            or validation_run.max_output_bytes != definition.max_output_bytes
            or validation_run.max_artifact_bytes != 0
            or validation_run.max_artifact_count != 0
            or validation_run.state != "succeeded"
            or validation_run.completed_at is None
        ):
            return None

        try:
            stored_spec = ValidationExecuteJobSpec.model_validate(
                {"kind": job.kind, **job.parameters}
            )
            result = ValidationExecutionResult.model_validate(job.result)
        except (TypeError, ValidationError):
            return None
        expected_validation_policy = compute_validation_policy_digest(
            {
                "grant_policy_hash": grant.policy_hash,
                "workspace_id": str(validation_run.workspace_id),
                "checkpoint_id": str(validation_run.checkpoint_id),
                "checkpoint_fingerprint": validation_run.checkpoint_fingerprint,
                "profile": profile.reference,
                "timeout_seconds": profile.timeout_seconds,
                "max_output_bytes": profile.max_output_bytes,
                "max_artifact_bytes": profile.max_artifact_bytes,
                "max_artifact_count": profile.max_artifact_count,
            }
        )
        if (
            job.kind != "validation_execute_v1"
            or job.state != "succeeded"
            or job.execution_grant_id != grant.id
            or job.workspace_id != validation_run.workspace_id
            or job.repository_handle_id != grant.repository_handle_id
            or job.source_revision != validation_run.source_revision
            or job.execution_policy_hash != grant.policy_hash
            or stored_spec.validation_run_id != validation_run.id
            or stored_spec.validation_step_id != definition.step_id
            or stored_spec.profile_id != definition.profile_id
            or stored_spec.profile_version != definition.profile_version
            or stored_spec.checkpoint_id != validation_run.checkpoint_id
            or stored_spec.checkpoint_fingerprint != validation_run.checkpoint_fingerprint
            or stored_spec.validation_policy_digest != expected_validation_policy
            or validation_run.policy_digest != expected_validation_policy
            or attempt.id != evidence.attempt_id
            or attempt.job_id != job.id
            or attempt.runner_id != evidence.runner_id
            or attempt.lease_id != evidence.lease_id
            or attempt.state != "succeeded"
            or attempt.completed_at is None
        ):
            return None

        artifact_payload = [item.model_dump(mode="json") for item in (result.artifacts or [])]
        evidence_matches_result = (
            evidence.validation_run_id == result.validation_run_id
            and evidence.runner_id == attempt.runner_id
            and evidence.attempt_id == attempt.id
            and evidence.lease_id == attempt.lease_id
            and evidence.result_schema_version == result.result_schema_version == 1
            and evidence.validation_step_id == result.validation_step_id == definition.step_id
            and evidence.source_revision == result.source_revision == validation_run.source_revision
            and evidence.policy_digest == result.policy_digest == validation_run.policy_digest
            and evidence.fixed_argv == result.fixed_argv == list(profile.safe_argv)
            and evidence.fixed_argv_digest == result.fixed_argv_digest
            and evidence.fixed_cwd == result.fixed_cwd
            and evidence.fixed_environment_digest == result.fixed_environment_digest
            and evidence.started_at == result.started_at
            and evidence.completed_at == result.completed_at
            and evidence.duration_ms == round(result.duration_ms)
            and evidence.exit_code == result.exit_code == 0
            and evidence.stdout == result.stdout
            and evidence.stderr == result.stderr
            and evidence.stdout_truncated == result.stdout_truncated
            and evidence.stderr_truncated == result.stderr_truncated
            and evidence.redaction_count == result.redaction_count
            and evidence.timed_out == result.timed_out is False
            and evidence.cancelled == result.cancelled is False
            and evidence.network_isolated == result.network_isolated is True
            and evidence.filesystem_isolated == result.filesystem_isolated is True
            and evidence.sandbox_cleaned == result.sandbox_cleaned is True
            and evidence.artifact_count == result.artifact_count == 0
            and evidence.artifact_bytes == result.artifact_bytes == 0
            and evidence.artifact_summary == {"files": artifact_payload}
            and evidence.artifact_manifest_digest == result.artifact_manifest_digest
            and evidence.side_effect_permit_id == result.side_effect_permit_id
            and evidence.side_effect_permit_sequence == result.side_effect_permit_sequence
            and evidence.side_effect_permit_digest == result.side_effect_permit_digest
            and evidence.fencing_token == result.fencing_token
            and evidence.execution_envelope_digest == result.execution_envelope_digest
            and evidence.evidence_digest == result.evidence_digest
            and result.evidence_digest is not None
            and hmac.compare_digest(
                result.evidence_digest,
                compute_validation_evidence_digest(result),
            )
        )
        output_bytes = len(evidence.stdout.encode("utf-8")) + len(evidence.stderr.encode("utf-8"))
        if (
            not evidence_matches_result
            or output_bytes > definition.max_output_bytes
            or (
                proof_step.output_bytes != output_bytes
                or proof_step.redaction_count != evidence.redaction_count
                or proof_step.output_truncated
                != (evidence.stdout_truncated or evidence.stderr_truncated)
                or proof_step.cleanup_succeeded is not True
                or proof_step.exit_code != 0
            )
            or permit.id != evidence.side_effect_permit_id
            or permit.state != "completed"
            or permit.terminal_at is None
            or permit.operation != WorkspaceOperation.VALIDATE.value
            or permit.runner_id != attempt.runner_id
            or permit.job_id != job.id
            or permit.attempt_id != attempt.id
            or permit.lease_id != attempt.lease_id
            or permit.grant_id != grant.id
            or permit.workspace_id != validation_run.workspace_id
            or permit.repository_handle_id != grant.repository_handle_id
            or permit.policy_hash != grant.policy_hash
            or permit.source_revision != validation_run.source_revision
            or permit.sequence != evidence.side_effect_permit_sequence
            or permit.operation_digest != evidence.side_effect_permit_digest
        ):
            return None

        return (
            {
                "sequence": step.sequence,
                "step_id": step.step_id,
                "profile": f"{step.profile_id}:v{step.profile_version}",
                "validation_run_id": str(validation_run.id),
                "runner_job_id": str(job.id),
                "runner_id": str(evidence.runner_id),
                "attempt_id": str(evidence.attempt_id),
                "lease_id": str(evidence.lease_id),
                "grant_id": str(grant.id),
                "evidence_id": str(evidence.id),
                "evidence_digest": evidence.evidence_digest or "",
                "reused": step.reused_from_step_run_id is not None,
            },
            evidence,
        )

    def trusted_success_manifest(
        self,
        suite_run_id: uuid.UUID,
        *,
        lock: bool = True,
    ) -> tuple[ValidationSuiteRun, ValidationSuiteResult, Sequence[dict[str, object]]]:
        """Reconstruct the exact successful Suite proof for final review."""
        suite_run = self._required_run(suite_run_id, lock=lock)
        result = self._validation.suite_result(suite_run.id)
        steps = self._validation.suite_steps(suite_run.id, lock=lock)
        if (
            suite_run.state != "succeeded"
            or result is None
            or result.verdict != "succeeded"
            or len(steps) != suite_run.step_count
        ):
            raise ValidationSuiteServiceError(
                "review_suite_not_successful",
                "Review Package requires one complete successful Validation Suite Result",
                category="policy",
            )

        evidence_references: list[dict[str, object]] = []
        manifest_entries: list[dict[str, object]] = []
        runner_references: list[str] = []
        profile_references: list[str] = []
        trusted_output_bytes = 0
        redaction_count = 0
        output_truncated = False
        for step in steps:
            trusted = self._trusted_success_step(suite_run, step, lock=lock)
            if trusted is None:
                raise ValidationSuiteServiceError(
                    "review_evidence_integrity_failed",
                    "Validation Suite Evidence could not be reconstructed",
                    category="policy",
                )
            reference, evidence = trusted
            evidence_references.append(reference)
            manifest_entries.append(
                {
                    **reference,
                    "side_effect_permit_id": str(evidence.side_effect_permit_id),
                    "side_effect_permit_sequence": evidence.side_effect_permit_sequence,
                    "side_effect_permit_digest": evidence.side_effect_permit_digest or "",
                    "fencing_token": evidence.fencing_token or "",
                    "execution_envelope_digest": evidence.execution_envelope_digest or "",
                }
            )
            runner_references.append(str(evidence.runner_id))
            profile_references.append(f"{step.profile_id}:v{step.profile_version}")
            if step.reused_from_step_run_id is None:
                trusted_output_bytes += len(evidence.stdout.encode("utf-8")) + len(
                    evidence.stderr.encode("utf-8")
                )
                redaction_count += evidence.redaction_count
            output_truncated = (
                output_truncated or evidence.stdout_truncated or evidence.stderr_truncated
            )

        aggregate_payload = {
            "suite_run_id": str(suite_run.id),
            "suite": f"{suite_run.suite_id}:v{suite_run.suite_version}",
            "policy_digest": suite_run.policy_digest,
            "source_revision": suite_run.source_revision,
            "checkpoint_id": str(suite_run.checkpoint_id),
            "checkpoint_fingerprint": suite_run.checkpoint_fingerprint,
            "attempt_number": suite_run.attempt_number,
            "root_suite_run_id": str(suite_run.root_suite_run_id),
            "execution_grant_id": str(suite_run.execution_grant_id),
            "verdict": "succeeded",
            "profiles": profile_references,
            "evidence": evidence_references,
            "runners": runner_references,
            "combined_output_bytes": trusted_output_bytes,
            "redaction_count": redaction_count,
            "output_truncated": output_truncated,
            "cleanup_succeeded": True,
            "source_invariant": True,
            "canonical_workspace_invariant": True,
            "artifact_count": 0,
            "artifact_bytes": 0,
            "budgets": {
                "total_timeout_seconds": suite_run.total_timeout_seconds,
                "total_output_bytes": suite_run.total_output_bytes,
                "max_attempts": suite_run.max_attempts,
            },
        }
        aggregate_digest = compute_validation_policy_digest(aggregate_payload)
        if (
            result.root_suite_run_id != suite_run.root_suite_run_id
            or result.run_id != suite_run.run_id
            or result.execution_grant_id != suite_run.execution_grant_id
            or result.suite_id != suite_run.suite_id
            or result.suite_version != suite_run.suite_version
            or result.source_revision != suite_run.source_revision
            or result.checkpoint_id != suite_run.checkpoint_id
            or result.policy_digest != suite_run.policy_digest
            or result.attempt_number != suite_run.attempt_number
            or result.total_timeout_seconds != suite_run.total_timeout_seconds
            or result.total_output_bytes != suite_run.total_output_bytes
            or result.max_attempts != suite_run.max_attempts
            or result.profile_references != profile_references
            or result.evidence_references != evidence_references
            or result.runner_references != runner_references
            or result.combined_output_bytes != trusted_output_bytes
            or result.redaction_count != redaction_count
            or result.output_truncated != output_truncated
            or not result.cleanup_succeeded
            or not result.source_invariant
            or not result.canonical_workspace_invariant
            or result.artifact_count != 0
            or result.artifact_bytes != 0
            or not hmac.compare_digest(result.aggregate_digest, aggregate_digest)
        ):
            raise ValidationSuiteServiceError(
                "review_aggregate_integrity_failed",
                "Validation Suite aggregate does not match reconstructed Evidence",
                category="policy",
            )
        return suite_run, result, manifest_entries

    @staticmethod
    def _suite_policy_digest(
        suite_run: ValidationSuiteRun,
        definition_digest: str,
        grant_policy_hash: str,
    ) -> str:
        payload: dict[str, object] = {
            "suite_definition_digest": definition_digest,
            "grant_policy_hash": grant_policy_hash,
            "workspace_id": str(suite_run.workspace_id),
            "checkpoint_id": str(suite_run.checkpoint_id),
            "checkpoint_fingerprint": suite_run.checkpoint_fingerprint,
            "source_revision": suite_run.source_revision,
            "total_timeout_seconds": suite_run.total_timeout_seconds,
            "total_output_bytes": suite_run.total_output_bytes,
            "max_attempts": suite_run.max_attempts,
        }
        if suite_run.attempt_number > 1:
            payload["attempt_number"] = suite_run.attempt_number
            payload["retry_of_suite_run_id"] = str(suite_run.root_suite_run_id)
        return compute_validation_policy_digest(payload)

    def _required_suite_grant(
        self,
        grant_id: uuid.UUID,
        suite_reference: str,
        *,
        expected_attempt_number: int,
        expected_root_suite_run_id: uuid.UUID | None,
        expected_retry_of_suite_run_id: uuid.UUID | None,
    ) -> tuple[
        ExecutionGrant,
        WorkspaceCheckpoint,
        Workspace,
        RepositoryHandle,
    ]:
        context = self._validation.validation_grant(grant_id, lock=True)
        if context is None:
            self._not_found(
                "validation_grant_not_found",
                "Suite-scoped Validation Execution Grant was not found",
            )
        grant, checkpoint, workspace, handle = context
        suite = validation_suite(suite_reference.split(":v", 1)[0])
        if (
            suite is None
            or suite.reference != suite_reference
            or grant.allowed_validation_suites != [suite_reference]
            or grant.allowed_validation_profiles != [step.profile_reference for step in suite.steps]
            or grant.validation_suite_definition_digest != suite.policy_digest
            or grant.validation_suite_attempt_number != expected_attempt_number
            or grant.validation_suite_root_run_id != expected_root_suite_run_id
            or grant.validation_suite_retry_of_run_id != expected_retry_of_suite_run_id
            or grant.validation_suite_allowed_run_count != 1
            or grant.max_validation_runs != len(suite.steps)
        ):
            raise ValidationSuiteServiceError(
                "validation_suite_grant_denied",
                "Execution Grant does not bind the exact immutable Suite lineage",
                category="policy",
            )
        now = utc_now()
        if grant.status != "approved" or grant.expires_at <= now:
            self._conflict(
                "validation_grant_inactive",
                "Validation Execution Grant is not approved and active",
            )
        if (
            grant.validation_workspace_id != workspace.id
            or grant.validation_checkpoint_id != checkpoint.id
            or workspace.current_tree_hash != checkpoint.tree_fingerprint
            or workspace.source_revision != checkpoint.source_revision
            or workspace.repository_handle_id != handle.id
            or workspace.runner_id != handle.runner_id
            or workspace.expires_at <= now
            or workspace.state not in {"ready", "active", "sealed", "rolled_back"}
        ):
            self._conflict(
                "stale_validation_baseline",
                "Validation Workspace or Checkpoint no longer matches the Suite Grant",
            )
        policy = ValidationService(self._session)._policy(grant, handle)
        if not execution_grant_policy_hash_matches(policy, grant.policy_hash):
            raise ValidationSuiteServiceError(
                "validation_policy_hash_mismatch",
                "Validation Execution Grant policy hash is invalid",
                category="policy",
            )
        return grant, checkpoint, workspace, handle

    def _baseline_is_current(self, suite_run: ValidationSuiteRun) -> bool:
        context = self._validation.validation_grant(suite_run.execution_grant_id)
        if context is None:
            return False
        grant, checkpoint, workspace, handle = context
        return bool(
            grant.validation_workspace_id == suite_run.workspace_id
            and grant.validation_checkpoint_id == suite_run.checkpoint_id
            and checkpoint.id == suite_run.checkpoint_id
            and checkpoint.tree_fingerprint == suite_run.checkpoint_fingerprint
            and checkpoint.source_revision == suite_run.source_revision
            and workspace.current_tree_hash == suite_run.checkpoint_fingerprint
            and workspace.source_revision == suite_run.source_revision
            and workspace.repository_handle_id == handle.id
        )

    def _response(self, suite_run: ValidationSuiteRun) -> ValidationSuiteRunResponse:
        steps = self._validation.suite_steps(suite_run.id)
        step_responses = []
        for step in steps:
            evidence = (
                self._validation.evidence_by_id(step.evidence_id)
                if step.evidence_id is not None
                else None
            )
            step_responses.append(
                ValidationSuiteStepRunResponse(
                    id=step.id,
                    sequence=step.sequence,
                    step_id=step.step_id,
                    profile_id=step.profile_id,
                    profile_version=step.profile_version,
                    timeout_seconds=step.timeout_seconds,
                    max_output_bytes=step.max_output_bytes,
                    state=step.state,
                    validation_run_id=step.validation_run_id,
                    runner_job_id=step.runner_job_id,
                    runner_id=step.runner_id,
                    attempt_id=step.attempt_id,
                    lease_id=step.lease_id,
                    evidence_id=step.evidence_id,
                    reused_from_step_run_id=step.reused_from_step_run_id,
                    started_at=step.started_at,
                    completed_at=step.completed_at,
                    duration_ms=step.duration_ms,
                    exit_code=step.exit_code,
                    output_bytes=step.output_bytes,
                    redaction_count=step.redaction_count,
                    output_truncated=step.output_truncated,
                    cleanup_succeeded=step.cleanup_succeeded,
                    failure_code=step.failure_code,
                    evidence=(
                        ValidationEvidenceResponse.model_validate(evidence)
                        if evidence is not None
                        else None
                    ),
                )
            )
        result = self._validation.suite_result(suite_run.id)
        return ValidationSuiteRunResponse(
            id=suite_run.id,
            run_id=suite_run.run_id,
            plan_id=suite_run.plan_id,
            source_revision=suite_run.source_revision,
            workspace_id=suite_run.workspace_id,
            checkpoint_id=suite_run.checkpoint_id,
            checkpoint_fingerprint=suite_run.checkpoint_fingerprint,
            execution_grant_id=suite_run.execution_grant_id,
            suite_id=suite_run.suite_id,
            suite_version=suite_run.suite_version,
            policy_digest=suite_run.policy_digest,
            failure_policy=suite_run.failure_policy,
            state=suite_run.state,
            step_count=suite_run.step_count,
            completed_step_count=suite_run.completed_step_count,
            total_timeout_seconds=suite_run.total_timeout_seconds,
            total_output_bytes=suite_run.total_output_bytes,
            combined_output_bytes=suite_run.combined_output_bytes,
            max_attempts=suite_run.max_attempts,
            attempt_number=suite_run.attempt_number,
            retry_of_suite_run_id=suite_run.retry_of_suite_run_id,
            root_suite_run_id=suite_run.root_suite_run_id,
            requested_at=suite_run.requested_at,
            started_at=suite_run.started_at,
            deadline_at=suite_run.deadline_at,
            cancel_requested_at=suite_run.cancel_requested_at,
            completed_at=suite_run.completed_at,
            error_code=suite_run.error_code,
            error_message=suite_run.error_message,
            version=suite_run.version,
            created_at=suite_run.created_at,
            updated_at=suite_run.updated_at,
            steps=step_responses,
            result=result,
        )

    def _audit(
        self,
        suite_run: ValidationSuiteRun,
        event_type: str,
        *,
        request_id: str,
        details: dict[str, object],
    ) -> AuditEvent:
        event = AuditEvent(
            run_id=suite_run.run_id,
            event_type=event_type,
            actor_type="system",
            request_id=request_id[:128],
            details={
                "suite_run_id": str(suite_run.id),
                **details,
            },
        )
        self._session.add(event)
        return event

    def _required_run(
        self,
        suite_run_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> ValidationSuiteRun:
        suite_run = self._validation.get_suite_run(suite_run_id, lock=lock)
        if suite_run is None:
            self._not_found(
                "validation_suite_run_not_found",
                "Validation Suite Run was not found",
            )
        return suite_run

    @staticmethod
    def _request_hash(payload: dict[str, object]) -> str:
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def _not_found(self, code: str, message: str) -> NoReturn:
        raise ValidationSuiteServiceError(code, message, category="not_found")

    def _conflict(self, code: str, message: str) -> NoReturn:
        raise ValidationSuiteServiceError(code, message, category="conflict")
