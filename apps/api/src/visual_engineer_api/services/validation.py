import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import NoReturn

from pydantic import ValidationError
from sqlalchemy.orm import Session

from visual_engineer_api.models.validation import (
    ValidationEvidence,
    ValidationRun,
    ValidationStepRun,
)
from visual_engineer_api.models.workspace import ExecutionGrant, RepositoryHandle
from visual_engineer_api.repositories.validation import ValidationRepository
from visual_engineer_api.schemas.validation import (
    ValidationEvidenceResponse,
    ValidationProfileListResponse,
    ValidationProfileResponse,
    ValidationRunCreate,
    ValidationRunListResponse,
    ValidationRunResponse,
    ValidationStepResponse,
)
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError
from visual_engineer_runner_protocol import (
    VALIDATION_PROFILE_CATALOG,
    ExecutionGrantPolicy,
    ValidationExecuteJobSpec,
    ValidationExecutionResult,
    execution_grant_policy_hash_matches,
    validation_profile,
)

_TERMINAL_STATES = {
    "succeeded",
    "failed",
    "timed_out",
    "cancelled",
    "recovery_required",
}
_RECOVERY_FAILURES = {
    "validation_cleanup_failed",
    "validation_process_remained",
    "validation_sandbox_unavailable",
}


class ValidationServiceError(Exception):
    def __init__(self, code: str, message: str, *, category: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


def utc_now() -> datetime:
    return datetime.now(UTC)


class ValidationService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._validation = ValidationRepository(session)

    def profiles(self) -> ValidationProfileListResponse:
        items = [
            ValidationProfileResponse(
                profile_id=profile.profile_id,
                version=profile.version,
                display_name=profile.display_name,
                description=profile.description,
                step_id=profile.step_id,
                safe_argv=list(profile.safe_argv),
                timeout_seconds=profile.timeout_seconds,
                max_output_bytes=profile.max_output_bytes,
                max_artifact_bytes=profile.max_artifact_bytes,
                max_artifact_count=profile.max_artifact_count,
            )
            for profile in VALIDATION_PROFILE_CATALOG.values()
        ]
        return ValidationProfileListResponse(items=items, total=len(items))

    def create(
        self,
        payload: ValidationRunCreate,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> ValidationRunResponse:
        request_hash = hashlib.sha256(
            json.dumps(
                payload.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        replay = self._validation.get_by_idempotency(idempotency_key, lock=True)
        if replay is not None:
            if replay.idempotency_request_hash != request_hash:
                self._conflict(
                    "idempotency_conflict",
                    "Idempotency-Key is already associated with a different Validation request",
                )
            return self._response(self._sync(replay))

        context = self._validation.validation_grant(payload.execution_grant_id, lock=True)
        if context is None:
            self._not_found(
                "validation_grant_not_found",
                "Validation-scoped Execution Grant was not found",
            )
        grant, checkpoint, workspace, handle = context
        profile = validation_profile(payload.profile_id)
        if profile is None or profile.reference not in grant.allowed_validation_profiles:
            raise ValidationServiceError(
                "validation_profile_denied",
                "Validation Profile is outside the Execution Grant",
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
                "Validation Workspace or Checkpoint no longer matches the Grant",
            )
        policy = self._policy(grant, handle)
        if not execution_grant_policy_hash_matches(policy, grant.policy_hash):
            raise ValidationServiceError(
                "validation_policy_hash_mismatch",
                "Validation Execution Grant policy hash is invalid",
                category="policy",
            )
        if self._validation.active_run_count(grant.id) >= grant.max_validation_runs:
            self._conflict(
                "validation_run_budget_exhausted",
                "Validation Execution Grant run budget is exhausted",
            )

        validation_run_id = uuid.uuid4()
        policy_digest = hashlib.sha256(
            json.dumps(
                {
                    "grant_policy_hash": grant.policy_hash,
                    "workspace_id": str(workspace.id),
                    "checkpoint_id": str(checkpoint.id),
                    "checkpoint_fingerprint": checkpoint.tree_fingerprint,
                    "profile": profile.reference,
                    "timeout_seconds": profile.timeout_seconds,
                    "max_output_bytes": profile.max_output_bytes,
                    "max_artifact_bytes": profile.max_artifact_bytes,
                    "max_artifact_count": profile.max_artifact_count,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        validation_run = ValidationRun(
            id=validation_run_id,
            run_id=grant.run_id,
            plan_id=grant.plan_id,
            source_revision=grant.source_revision,
            workspace_id=workspace.id,
            checkpoint_id=checkpoint.id,
            checkpoint_fingerprint=checkpoint.tree_fingerprint,
            execution_grant_id=grant.id,
            profile_id=profile.profile_id,
            profile_version=profile.version,
            policy_digest=policy_digest,
            state="requested",
            timeout_seconds=profile.timeout_seconds,
            max_output_bytes=profile.max_output_bytes,
            max_artifact_bytes=profile.max_artifact_bytes,
            max_artifact_count=profile.max_artifact_count,
            idempotency_key=idempotency_key,
            idempotency_request_hash=request_hash,
            requested_at=now,
            version=1,
        )
        step = ValidationStepRun(
            validation_run_id=validation_run_id,
            sequence=1,
            step_id=profile.step_id,
            state="queued",
        )
        self._validation.add(validation_run)
        self._validation.add(step)
        self._session.flush()

        spec = ValidationExecuteJobSpec(
            validation_run_id=validation_run.id,
            workspace_id=workspace.id,
            execution_grant=policy,
            profile_id=profile.profile_id,
            profile_version=profile.version,
            checkpoint_id=checkpoint.id,
            checkpoint_fingerprint=checkpoint.tree_fingerprint,
            timeout_seconds=profile.timeout_seconds,
            max_output_bytes=profile.max_output_bytes,
            max_artifact_bytes=profile.max_artifact_bytes,
            max_artifact_count=profile.max_artifact_count,
        )
        try:
            job = RunnerService(self._session).create_workspace_job(spec, request_id=request_id)
        except RunnerServiceError as exc:
            raise ValidationServiceError(exc.code, exc.message, category=exc.category) from exc
        validation_run.runner_job_id = job.id
        validation_run.state = "queued"
        validation_run.version += 1
        self._session.commit()
        self._session.refresh(validation_run)
        return self._response(validation_run)

    def list(self, *, workspace_id: uuid.UUID | None = None) -> ValidationRunListResponse:
        runs = [self._sync(item) for item in self._validation.list_runs(workspace_id=workspace_id)]
        self._session.commit()
        return ValidationRunListResponse(
            items=[self._response(item) for item in runs],
            total=len(runs),
        )

    def get(self, validation_run_id: uuid.UUID) -> ValidationRunResponse:
        validation_run = self._validation.get_run(validation_run_id, lock=True)
        if validation_run is None:
            self._not_found("validation_run_not_found", "Validation Run was not found")
        validation_run = self._sync(validation_run)
        self._session.commit()
        return self._response(validation_run)

    def cancel(self, validation_run_id: uuid.UUID, *, request_id: str) -> ValidationRunResponse:
        validation_run = self._validation.get_run(validation_run_id, lock=True)
        if validation_run is None:
            self._not_found("validation_run_not_found", "Validation Run was not found")
        validation_run = self._sync(validation_run)
        if validation_run.state in _TERMINAL_STATES:
            self._conflict(
                "validation_run_terminal",
                "A terminal Validation Run cannot be cancelled",
            )
        if validation_run.runner_job_id is None:
            self._conflict(
                "validation_job_missing",
                "Validation Run has no dispatchable Runner Job",
            )
        try:
            job = RunnerService(self._session).cancel_job(
                validation_run.runner_job_id,
                request_id=request_id,
            )
        except RunnerServiceError as exc:
            raise ValidationServiceError(exc.code, exc.message, category=exc.category) from exc
        now = utc_now()
        step = self._required_step(validation_run.id)
        validation_run.state = "cancelled" if job.state.value == "cancelled" else "cancel_requested"
        validation_run.cancel_requested_at = now
        if validation_run.state == "cancelled":
            validation_run.completed_at = now
            step.state = "cancelled"
            step.completed_at = now
        validation_run.version += 1
        self._session.commit()
        return self._response(validation_run)

    def _sync(self, validation_run: ValidationRun) -> ValidationRun:
        if validation_run.runner_job_id is None or validation_run.state in _TERMINAL_STATES:
            return validation_run
        job = self._validation.job(validation_run.runner_job_id)
        if job is None:
            return validation_run
        attempt = self._validation.latest_attempt(job.id)
        if attempt is not None:
            validation_run.runner_id = attempt.runner_id
            validation_run.attempt_id = attempt.id
            validation_run.lease_id = attempt.lease_id
            validation_run.claimed_at = validation_run.claimed_at or attempt.created_at
        mapped = {
            "queued": "queued",
            "leased": "claimed",
            "running": "running",
            "cancel_requested": "cancel_requested",
            "succeeded": "succeeded",
            "cancelled": "cancelled",
            "failed": (
                "timed_out"
                if job.error_code == "validation_timed_out"
                else "recovery_required"
                if job.error_code in _RECOVERY_FAILURES
                else "failed"
            ),
        }[job.state]
        if mapped == validation_run.state and (
            mapped not in _TERMINAL_STATES
            or self._validation.evidence(validation_run.id) is not None
        ):
            return validation_run
        step = self._required_step(validation_run.id)
        now = utc_now()
        validation_run.state = mapped
        validation_run.started_at = validation_run.started_at or (
            attempt.started_at if attempt is not None else None
        )
        validation_run.error_code = job.error_code
        validation_run.error_message = job.error_message
        validation_run.version += 1
        if mapped == "running":
            step.state = "running"
            step.started_at = validation_run.started_at or now
        if mapped in _TERMINAL_STATES:
            validation_run.completed_at = job.completed_at or now
            step.state = mapped
            step.completed_at = validation_run.completed_at
            step.started_at = step.started_at or (
                attempt.started_at if attempt is not None else validation_run.claimed_at
            )
            step.failure_code = job.error_code
            if (
                mapped in {"succeeded", "failed", "timed_out"}
                and attempt is not None
                and job.result is not None
                and self._validation.evidence(validation_run.id) is None
            ):
                try:
                    result = ValidationExecutionResult.model_validate(job.result)
                except ValidationError as exc:
                    raise ValidationServiceError(
                        "validation_result_invalid",
                        "Stored Validation result is invalid",
                        category="internal",
                    ) from exc
                evidence = ValidationEvidence(
                    validation_run_id=validation_run.id,
                    runner_id=attempt.runner_id,
                    attempt_id=attempt.id,
                    lease_id=attempt.lease_id,
                    fixed_argv=result.fixed_argv,
                    started_at=result.started_at,
                    completed_at=result.completed_at,
                    duration_ms=round(result.duration_ms),
                    exit_code=result.exit_code,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    stdout_truncated=result.stdout_truncated,
                    stderr_truncated=result.stderr_truncated,
                    redaction_count=result.redaction_count,
                    timed_out=result.timed_out,
                    cancelled=result.cancelled,
                    network_isolated=result.network_isolated,
                    filesystem_isolated=result.filesystem_isolated,
                    sandbox_cleaned=result.sandbox_cleaned,
                    artifact_count=result.artifact_count,
                    artifact_bytes=result.artifact_bytes,
                    artifact_summary={"files": []},
                    side_effect_permit_id=result.side_effect_permit_id,
                )
                self._validation.add(evidence)
                step.exit_code = result.exit_code
                step.duration_ms = round(result.duration_ms)
        self._session.flush()
        return validation_run

    def _policy(self, grant: ExecutionGrant, handle: RepositoryHandle) -> ExecutionGrantPolicy:
        try:
            return ExecutionGrantPolicy.model_validate(
                {
                    "id": grant.id,
                    "grant_version": grant.grant_version,
                    "task_id": grant.task_id,
                    "run_id": grant.run_id,
                    "plan_id": grant.plan_id,
                    "repository_handle_id": grant.repository_handle_id,
                    "repository_opaque_handle": handle.opaque_handle,
                    "source_revision": grant.source_revision,
                    "snapshot_fingerprint": grant.snapshot_fingerprint,
                    "allowed_operations": grant.allowed_operations,
                    "allowed_paths": grant.allowed_paths,
                    "denied_paths": grant.denied_paths,
                    "max_files_changed": grant.max_files_changed,
                    "max_total_write_bytes": grant.max_total_write_bytes,
                    "max_single_file_bytes": grant.max_single_file_bytes,
                    "max_diff_bytes": grant.max_diff_bytes,
                    "workspace_ttl_seconds": grant.workspace_ttl_seconds,
                    "network_policy": grant.network_policy,
                    "shell_access": grant.shell_access,
                    "git_delivery_access": grant.git_delivery_access,
                    "source_repository_write_access": grant.source_repository_write_access,
                    "validation_workspace_id": grant.validation_workspace_id,
                    "validation_checkpoint_id": grant.validation_checkpoint_id,
                    "allowed_validation_profiles": grant.allowed_validation_profiles,
                    "max_validation_runs": grant.max_validation_runs,
                    "validation_timeout_seconds": grant.validation_timeout_seconds,
                    "validation_cpu_seconds": grant.validation_cpu_seconds,
                    "validation_memory_bytes": grant.validation_memory_bytes,
                    "validation_pid_limit": grant.validation_pid_limit,
                    "validation_fd_limit": grant.validation_fd_limit,
                    "validation_output_bytes": grant.validation_output_bytes,
                    "validation_artifact_bytes": grant.validation_artifact_bytes,
                    "validation_artifact_count": grant.validation_artifact_count,
                    "expires_at": grant.expires_at,
                    "policy_hash": grant.policy_hash,
                }
            )
        except ValidationError as exc:
            raise ValidationServiceError(
                "validation_grant_invalid",
                "Stored Validation Grant is invalid",
                category="policy",
            ) from exc

    def _response(self, validation_run: ValidationRun) -> ValidationRunResponse:
        step = self._required_step(validation_run.id)
        evidence = self._validation.evidence(validation_run.id)
        job = (
            RunnerService(self._session).get_job(validation_run.runner_job_id)
            if validation_run.runner_job_id is not None
            else None
        )
        return ValidationRunResponse(
            id=validation_run.id,
            run_id=validation_run.run_id,
            plan_id=validation_run.plan_id,
            source_revision=validation_run.source_revision,
            workspace_id=validation_run.workspace_id,
            checkpoint_id=validation_run.checkpoint_id,
            checkpoint_fingerprint=validation_run.checkpoint_fingerprint,
            execution_grant_id=validation_run.execution_grant_id,
            runner_job_id=validation_run.runner_job_id,
            runner_id=validation_run.runner_id,
            attempt_id=validation_run.attempt_id,
            lease_id=validation_run.lease_id,
            profile_id=validation_run.profile_id,
            profile_version=validation_run.profile_version,
            policy_digest=validation_run.policy_digest,
            state=validation_run.state,
            timeout_seconds=validation_run.timeout_seconds,
            max_output_bytes=validation_run.max_output_bytes,
            max_artifact_bytes=validation_run.max_artifact_bytes,
            max_artifact_count=validation_run.max_artifact_count,
            requested_at=validation_run.requested_at,
            claimed_at=validation_run.claimed_at,
            started_at=validation_run.started_at,
            cancel_requested_at=validation_run.cancel_requested_at,
            completed_at=validation_run.completed_at,
            error_code=validation_run.error_code,
            error_message=validation_run.error_message,
            version=validation_run.version,
            created_at=validation_run.created_at,
            updated_at=validation_run.updated_at,
            step=ValidationStepResponse.model_validate(step),
            evidence=(
                ValidationEvidenceResponse.model_validate(evidence)
                if evidence is not None
                else None
            ),
            job=job,
        )

    def _required_step(self, validation_run_id: uuid.UUID) -> ValidationStepRun:
        step = self._validation.step(validation_run_id)
        if step is None:
            raise ValidationServiceError(
                "validation_step_missing",
                "Validation Run step record is missing",
                category="internal",
            )
        return step

    def _not_found(self, code: str, message: str) -> NoReturn:
        raise ValidationServiceError(code, message, category="not_found")

    def _conflict(self, code: str, message: str) -> NoReturn:
        raise ValidationServiceError(code, message, category="conflict")
