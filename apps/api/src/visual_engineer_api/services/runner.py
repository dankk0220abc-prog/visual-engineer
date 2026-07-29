import hashlib
import hmac
import logging
import math
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, NoReturn

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from visual_engineer_api.core.config import Settings, get_settings
from visual_engineer_api.models.runner import (
    PermissionEnvelope,
    Runner,
    RunnerJob,
    RunnerJobAttempt,
    RunnerJobEvent,
)
from visual_engineer_api.models.workspace import SideEffectPermit as PersistedSideEffectPermit
from visual_engineer_api.models.workspace import (
    Workspace,
    WorkspaceCheckpoint,
    WorkspaceEvent,
)
from visual_engineer_api.repositories.runner import RunnerRepository
from visual_engineer_api.repositories.validation import ValidationRepository
from visual_engineer_api.repositories.workspace import WorkspaceRepository
from visual_engineer_api.schemas.runner import (
    ActiveJobSummary,
    PermissionEnvelopeResponse,
    RunnerJobAttemptResponse,
    RunnerJobEventResponse,
    RunnerJobResponse,
    RunnerResponse,
)
from visual_engineer_api.services.runner_state import (
    transition_attempt,
    transition_job,
)
from visual_engineer_runner_protocol import (
    RUNNER_PROTOCOL_VERSION,
    CancelledRequest,
    ClaimRequest,
    ClaimResponse,
    CompleteRequest,
    ControlledWaitJobSpec,
    ControlledWaitResult,
    DiagnosticResult,
    EventType,
    ExecutionGrantPolicy,
    FailRequest,
    FailureCode,
    HeartbeatRequest,
    HeartbeatResponse,
    JobAssignment,
    JobKind,
    JobSpec,
    JobState,
    LeaseMutationResponse,
    ProgressEventRequest,
    RegisterRequest,
    RegisterResponse,
    RenewRequest,
    ResultPayload,
    RunnerStatus,
    SideEffectPermit,
    SideEffectPermitAcquireRequest,
    SideEffectPermitState,
    StartRequest,
    SystemDiagnosticJobSpec,
    ValidationExecuteJobSpec,
    ValidationExecutionResult,
    WorkspaceBoundJobSpec,
    WorkspaceCheckpointPayload,
    WorkspaceDiffResult,
    WorkspaceDiscardJobSpec,
    WorkspaceDiscardResult,
    WorkspaceJobSpec,
    WorkspaceListResult,
    WorkspaceOperation,
    WorkspacePrepareJobSpec,
    WorkspacePrepareResult,
    WorkspaceReadTextResult,
    WorkspaceRollbackJobSpec,
    WorkspaceRollbackResult,
    WorkspaceStatusResult,
    WorkspaceWriteTextJobSpec,
    WorkspaceWriteTextResult,
    compute_permission_policy_hash,
    compute_side_effect_job_digest,
    compute_side_effect_permit_digest,
    compute_validation_artifact_manifest_digest,
    compute_validation_evidence_digest,
    compute_validation_policy_digest,
    execution_grant_policy_hash_matches,
    side_effect_job_binding,
    side_effect_permit_digest_matches,
    validate_result_payload,
    validate_safe_error_message,
    validation_profile,
    validation_result_binding,
)
from visual_engineer_runner_protocol import (
    PermissionEnvelope as ProtocolPermissionEnvelope,
)

LOGGER = logging.getLogger("visual_engineer_api.runner")
RESULT_ADAPTER: TypeAdapter[ResultPayload] = TypeAdapter(ResultPayload)
JOB_SPEC_ADAPTER: TypeAdapter[JobSpec] = TypeAdapter(JobSpec)
REAPER_ADVISORY_LOCK = 8_617_203_003
VALIDATION_RECOVERY_FAILURES = {
    FailureCode.VALIDATION_CLEANUP_FAILED,
    FailureCode.VALIDATION_PROCESS_REMAINED,
    FailureCode.VALIDATION_SANDBOX_UNAVAILABLE,
}


class RunnerServiceError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        category: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.category = category


def runner_token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _constant_time_token_match(candidate: str, expected: str) -> bool:
    candidate_digest = hashlib.sha256(candidate.encode("utf-8")).digest()
    expected_digest = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(candidate_digest, expected_digest)


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunnerService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self._session = session
        self._runners = RunnerRepository(session)
        self._validation = ValidationRepository(session)
        self._workspaces = WorkspaceRepository(session)
        self._settings = settings or get_settings()

    def register(
        self,
        payload: RegisterRequest,
        *,
        bootstrap_token: str,
        request_id: str,
    ) -> RegisterResponse:
        configured = self._settings.runner_bootstrap_token.get_secret_value()
        if len(configured) < 32:
            raise RunnerServiceError(
                "runner_registration_unavailable",
                "Runner registration is not configured",
                category="unavailable",
            )
        if not bootstrap_token or not _constant_time_token_match(bootstrap_token, configured):
            raise RunnerServiceError(
                "runner_auth_invalid",
                "Runner authentication failed",
                category="auth",
            )

        issued_token = secrets.token_urlsafe(48)
        now = utc_now()
        runner = Runner(
            display_name=payload.display_name,
            protocol_version=payload.protocol_version,
            software_version=payload.software_version,
            capabilities=[capability.value for capability in payload.capabilities],
            token_digest=runner_token_digest(issued_token),
            status="registered",
            registered_at=now,
        )
        self._runners.add(runner)
        self._session.flush()
        self._event(
            EventType.RUNNER_REGISTERED,
            request_id=request_id,
            runner_id=runner.id,
            metadata={
                "protocol_version": payload.protocol_version,
                "status": "registered",
            },
        )
        self._session.commit()
        self._session.refresh(runner)
        self._log_event("runner_registered", runner_id=runner.id)
        return RegisterResponse(
            runner_id=runner.id,
            runner_token=issued_token,
            protocol_version=RUNNER_PROTOCOL_VERSION,
            registered_at=runner.registered_at,
        )

    def authenticate(self, token: str) -> Runner:
        if not token or len(token) > 256:
            raise RunnerServiceError(
                "runner_auth_invalid",
                "Runner authentication failed",
                category="auth",
            )
        supplied_digest = runner_token_digest(token)
        match: Runner | None = None
        for candidate in self._runners.auth_candidates():
            if hmac.compare_digest(candidate.token_digest, supplied_digest):
                match = candidate
        if match is None:
            raise RunnerServiceError(
                "runner_auth_invalid",
                "Runner authentication failed",
                category="auth",
            )
        if match.status == "revoked":
            raise RunnerServiceError(
                "runner_revoked",
                "Runner authentication is revoked",
                category="forbidden",
            )
        return match

    def heartbeat(
        self,
        authenticated: Runner,
        payload: HeartbeatRequest,
        *,
        request_id: str,
    ) -> HeartbeatResponse:
        self._require_runner_identity(authenticated, payload.runner_id)
        runner = self._locked_runner(authenticated.id)
        now = utc_now()
        meaningful_transition = runner.status != "online"
        runner.last_seen_at = now
        runner.software_version = payload.software_version
        if payload.capabilities is not None:
            runner.capabilities = [capability.value for capability in payload.capabilities]
        runner.status = "online"
        runner.version += 1
        if meaningful_transition:
            self._event(
                EventType.RUNNER_HEARTBEAT,
                request_id=request_id,
                runner_id=runner.id,
                metadata={"status": "online"},
            )
        self._session.commit()
        return HeartbeatResponse(runner_id=runner.id, status=RunnerStatus.ONLINE, server_time=now)

    def list_runners(self) -> list[RunnerResponse]:
        return [self._runner_response(item) for item in self._runners.list_runners()]

    def get_runner(self, runner_id: uuid.UUID) -> RunnerResponse:
        runner = self._runners.get_runner(runner_id)
        if runner is None:
            raise RunnerServiceError(
                "runner_not_found",
                "Runner was not found",
                category="not_found",
            )
        return self._runner_response(runner)

    def revoke_runner(self, runner_id: uuid.UUID, *, request_id: str) -> RunnerResponse:
        runner = self._runners.get_runner(runner_id, lock=True)
        if runner is None:
            raise RunnerServiceError(
                "runner_not_found",
                "Runner was not found",
                category="not_found",
            )
        if runner.status == "revoked":
            return self._runner_response(runner)

        now = utc_now()
        runner.status = "revoked"
        runner.revoked_at = now
        runner.version += 1
        active = self._runners.active_attempt_for_runner(runner.id)
        if active is not None:
            job = self._runners.get_job(active.job_id, lock=True)
            if job is not None and job.state in {"leased", "running"}:
                transition_job(job, "cancel_requested")
                self._event(
                    EventType.CANCEL_REQUESTED,
                    request_id=request_id,
                    runner_id=runner.id,
                    job_id=job.id,
                    attempt_id=active.id,
                    metadata={"reason_code": "runner_revoked"},
                )
        self._event(
            EventType.RUNNER_REVOKED,
            request_id=request_id,
            runner_id=runner.id,
            metadata={"status": "revoked"},
        )
        self._session.commit()
        self._log_event("runner_revoked", runner_id=runner.id)
        return self._runner_response(runner)

    def create_job(self, spec: JobSpec, *, request_id: str) -> RunnerJobResponse:
        if isinstance(spec, WorkspaceBoundJobSpec):
            raise RunnerServiceError(
                "execution_grant_required",
                "Workspace Jobs can only be created by typed Workspace actions",
                category="policy",
            )
        return self._create_job(spec, request_id=request_id)

    def create_workspace_job(
        self,
        spec: WorkspaceJobSpec,
        *,
        request_id: str,
    ) -> RunnerJobResponse:
        grant = spec.execution_grant
        if not execution_grant_policy_hash_matches(grant, grant.policy_hash):
            raise RunnerServiceError(
                "execution_grant_hash_mismatch",
                "Execution Grant policy hash is invalid",
                category="policy",
            )
        if grant.expires_at <= utc_now():
            raise RunnerServiceError(
                "execution_grant_expired",
                "Execution Grant is expired",
                category="conflict",
            )
        expected_operation = (
            WorkspaceOperation.VALIDATE.value
            if isinstance(spec, ValidationExecuteJobSpec)
            else spec.kind.value.removeprefix("workspace_").removesuffix("_v1")
        )
        if expected_operation not in {item.value for item in grant.allowed_operations}:
            raise RunnerServiceError(
                "operation_not_granted",
                "Workspace operation is outside the Execution Grant",
                category="policy",
            )
        return self._create_job(spec, request_id=request_id)

    def _create_job(self, spec: JobSpec, *, request_id: str) -> RunnerJobResponse:
        now = utc_now()
        job_id = uuid.uuid4()
        envelope_id = uuid.uuid4()
        kind = JobKind(spec.kind)
        workspace_spec = spec if isinstance(spec, WorkspaceBoundJobSpec) else None
        if isinstance(spec, SystemDiagnosticJobSpec):
            max_runtime = 10
        elif isinstance(spec, ControlledWaitJobSpec):
            max_runtime = min(60, math.ceil(spec.duration_ms / 1000) + 5)
        elif kind == JobKind.WORKSPACE_PREPARE_V1:
            max_runtime = 120
        elif kind in {
            JobKind.WORKSPACE_ROLLBACK_V1,
            JobKind.WORKSPACE_DISCARD_V1,
        }:
            max_runtime = 60
        elif isinstance(spec, ValidationExecuteJobSpec):
            max_runtime = min(120, spec.timeout_seconds + 10)
        else:
            max_runtime = 30
        envelope_expiry = now + timedelta(seconds=self._settings.runner_envelope_ttl_seconds)
        if workspace_spec is not None:
            envelope_expiry = min(envelope_expiry, workspace_spec.execution_grant.expires_at)
        envelope_values: dict[str, Any] = {
            "id": envelope_id,
            "envelope_version": 1,
            "job_id": job_id,
            "authorization_source": (
                "execution_grant" if workspace_spec is not None else "local_user_job_dispatch"
            ),
            "allowed_capabilities": [kind.value],
            "repository_access": ("isolated_workspace" if workspace_spec is not None else "none"),
            "shell_access": False,
            "network_policy": "control_plane_only",
            "max_runtime_seconds": max_runtime,
            "lease_seconds": self._settings.runner_lease_seconds,
            "max_attempts": self._settings.runner_job_max_attempts,
            "max_result_bytes": (
                64 * 1024 if workspace_spec is not None else self._settings.runner_max_result_bytes
            ),
            "issued_at": now,
            "expires_at": envelope_expiry,
            "policy_hash": "0" * 64,
        }
        draft = ProtocolPermissionEnvelope.model_validate(envelope_values)
        envelope_values["policy_hash"] = compute_permission_policy_hash(draft)
        protocol_envelope = ProtocolPermissionEnvelope.model_validate(envelope_values)
        envelope = PermissionEnvelope(**protocol_envelope.model_dump(mode="python"))
        parameters = spec.model_dump(mode="json", exclude={"kind"})
        job = RunnerJob(
            id=job_id,
            kind=kind.value,
            state="queued",
            permission_envelope_id=envelope_id,
            requested_by="local_user",
            parameters=parameters,
            execution_grant_id=(
                workspace_spec.execution_grant.id if workspace_spec is not None else None
            ),
            workspace_id=(workspace_spec.workspace_id if workspace_spec is not None else None),
            repository_handle_id=(
                workspace_spec.execution_grant.repository_handle_id
                if workspace_spec is not None
                else None
            ),
            source_revision=(
                workspace_spec.execution_grant.source_revision
                if workspace_spec is not None
                else None
            ),
            execution_policy_hash=(
                workspace_spec.execution_grant.policy_hash if workspace_spec is not None else None
            ),
            attempt_count=0,
            max_attempts=protocol_envelope.max_attempts,
            version=1,
        )
        self._runners.add(envelope)
        self._runners.add(job)
        self._session.flush()
        self._event(
            EventType.JOB_CREATED,
            request_id=request_id,
            job_id=job.id,
            metadata={
                "kind": job.kind,
                "policy_hash": envelope.policy_hash,
            },
        )
        self._session.commit()
        self._session.refresh(job)
        self._log_event("job_created", job_id=job.id)
        return self._job_response(job)

    def list_jobs(self) -> list[RunnerJobResponse]:
        return [self._job_response(job) for job in self._runners.list_jobs()]

    def get_job(self, job_id: uuid.UUID) -> RunnerJobResponse:
        job = self._runners.get_job(job_id)
        if job is None:
            raise RunnerServiceError(
                "runner_job_not_found",
                "Runner Job was not found",
                category="not_found",
            )
        return self._job_response(job)

    def list_events(self, job_id: uuid.UUID) -> list[RunnerJobEventResponse]:
        if self._runners.get_job(job_id) is None:
            raise RunnerServiceError(
                "runner_job_not_found",
                "Runner Job was not found",
                category="not_found",
            )
        return [
            RunnerJobEventResponse.model_validate(event)
            for event in self._runners.list_events(job_id)
        ]

    def claim(
        self,
        authenticated: Runner,
        payload: ClaimRequest,
        *,
        request_id: str,
    ) -> ClaimResponse:
        self._require_runner_identity(authenticated, payload.runner_id)
        runner = self._locked_runner(authenticated.id)
        now = utc_now()
        runner.last_seen_at = now
        runner.status = "online"
        runner.version += 1

        replay_event = self._runners.event_by_request(
            event_type=EventType.JOB_CLAIMED.value,
            request_id=request_id,
            runner_id=runner.id,
        )
        if replay_event is not None and replay_event.attempt_id is not None:
            attempt = self._runners.get_attempt(replay_event.attempt_id)
            if attempt is not None:
                job = self._runners.get_job(attempt.job_id)
                if job is not None:
                    return ClaimResponse(
                        assignment=self._assignment(job, attempt),
                        server_time=now,
                    )

        job = self._runners.claimable_job(runner.capabilities, runner.id)
        if job is None:
            self._session.commit()
            return ClaimResponse(assignment=None, server_time=now)
        if job.workspace_id is not None:
            try:
                self._require_workspace_authority(job, runner, now)
            except RunnerServiceError as exc:
                transition_job(job, "failed")
                job.error_code = exc.code
                job.error_message = exc.message
                job.completed_at = now
                self._event(
                    EventType.POLICY_DENIED,
                    request_id=request_id,
                    runner_id=runner.id,
                    job_id=job.id,
                    metadata={"reason_code": exc.code},
                )
                self._event(
                    EventType.JOB_FAILED,
                    request_id=request_id,
                    runner_id=runner.id,
                    job_id=job.id,
                    metadata={"error_code": exc.code},
                )
                if job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
                    self._workspace_job_failed(
                        job,
                        error_code=exc.code,
                        error_message=exc.message,
                        request_id=request_id,
                    )
                self._session.commit()
                return ClaimResponse(assignment=None, server_time=now)
        envelope = self._required_envelope(job)
        if envelope.expires_at <= now:
            transition_job(job, "failed")
            job.error_code = "envelope_expired"
            job.error_message = "Permission Envelope expired before dispatch"
            job.completed_at = now
            self._event(
                EventType.POLICY_DENIED,
                request_id=request_id,
                runner_id=runner.id,
                job_id=job.id,
                metadata={"reason_code": "envelope_expired"},
            )
            self._event(
                EventType.JOB_FAILED,
                request_id=request_id,
                runner_id=runner.id,
                job_id=job.id,
                metadata={"error_code": "envelope_expired"},
            )
            if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
                self._workspace_job_failed(
                    job,
                    error_code="envelope_expired",
                    error_message=job.error_message,
                    request_id=request_id,
                )
            self._session.commit()
            return ClaimResponse(assignment=None, server_time=now)

        attempt = RunnerJobAttempt(
            job_id=job.id,
            runner_id=runner.id,
            attempt_number=job.attempt_count + 1,
            lease_id=uuid.uuid4(),
            state="leased",
            leased_until=now + timedelta(seconds=envelope.lease_seconds),
            last_heartbeat_at=now,
        )
        self._runners.add(attempt)
        self._session.flush()
        transition_job(job, "leased")
        job.attempt_count += 1
        job.active_attempt_id = attempt.id
        self._event(
            EventType.JOB_CLAIMED,
            request_id=request_id,
            runner_id=runner.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={
                "attempt_number": attempt.attempt_number,
                "lease_id_hint": _identifier_hint(attempt.lease_id),
            },
        )
        self._session.commit()
        self._log_event(
            "job_claimed",
            runner_id=runner.id,
            job_id=job.id,
            attempt_id=attempt.id,
            lease_id=attempt.lease_id,
        )
        return ClaimResponse(assignment=self._assignment(job, attempt), server_time=now)

    def start(
        self,
        authenticated: Runner,
        job_id: uuid.UUID,
        payload: StartRequest,
        *,
        request_id: str,
    ) -> LeaseMutationResponse:
        job, attempt, envelope = self._active_lease(
            authenticated, job_id, payload, allow_cancel_requested=True
        )
        if job.state == "cancel_requested":
            return self._lease_response(job, attempt, cancel_requested=True)
        if job.state == "running" and attempt.state == "running":
            return self._lease_response(job, attempt, idempotent_replay=True)
        if job.state != "leased" or attempt.state != "leased":
            self._conflict("invalid_job_transition", "Job cannot be started from its current state")
        now = utc_now()
        transition_attempt(attempt, "running")
        transition_job(job, "running")
        attempt.started_at = now
        attempt.last_heartbeat_at = now
        attempt.leased_until = now + timedelta(seconds=envelope.lease_seconds)
        if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
            self._workspace_job_started(job, attempt, request_id=request_id)
        self._event(
            EventType.JOB_STARTED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={"attempt_number": attempt.attempt_number},
        )
        self._session.commit()
        self._log_event(
            "job_started",
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            lease_id=attempt.lease_id,
        )
        return self._lease_response(job, attempt)

    def acquire_side_effect_permit(
        self,
        authenticated: Runner,
        job_id: uuid.UUID,
        payload: SideEffectPermitAcquireRequest,
        *,
        request_id: str,
    ) -> SideEffectPermit:
        job, attempt, envelope = self._active_lease(authenticated, job_id, payload)
        if job.state != "running" or attempt.state != "running":
            self._conflict(
                "side_effect_permit_denied",
                "Side-effect Permit requires the active running Attempt",
            )
        if job.workspace_id is None or job.execution_grant_id is None:
            raise RunnerServiceError(
                "side_effect_permit_not_applicable",
                "This Job has no Workspace side effect",
                category="policy",
            )
        now = utc_now()
        policy = self._require_workspace_authority(job, authenticated, now)
        grant = self._workspaces.get_grant(job.execution_grant_id, lock=True)
        workspace = self._workspaces.get_workspace(job.workspace_id, lock=True)
        if (
            grant is None
            or workspace is None
            or grant.status != "approved"
            or grant.revocation_requested_at is not None
            or grant.expires_at <= now
            or (
                job.kind != JobKind.VALIDATION_EXECUTE_V1.value
                and workspace.active_attempt_id != attempt.id
            )
        ):
            self._permit_denied_event(
                job,
                attempt,
                authenticated,
                request_id=request_id,
                reason_code="execution_grant_inactive",
            )
            self._session.commit()
            self._conflict(
                "execution_grant_inactive",
                "Execution Grant is revoked, expired, or unavailable",
            )
        try:
            spec = JOB_SPEC_ADAPTER.validate_python({"kind": job.kind, **job.parameters})
        except ValidationError as exc:
            raise RunnerServiceError(
                "stored_job_spec_invalid",
                "Stored Runner Job specification is invalid",
                category="internal",
            ) from exc
        if not isinstance(
            spec,
            (
                WorkspacePrepareJobSpec,
                WorkspaceWriteTextJobSpec,
                WorkspaceRollbackJobSpec,
                WorkspaceDiscardJobSpec,
                ValidationExecuteJobSpec,
            ),
        ):
            raise RunnerServiceError(
                "side_effect_permit_not_applicable",
                "This Workspace Job does not require a Side-effect Permit",
                category="policy",
            )
        job_digest = compute_side_effect_job_digest(spec)
        if not hmac.compare_digest(job_digest, payload.job_digest):
            self._permit_denied_event(
                job,
                attempt,
                authenticated,
                request_id=request_id,
                reason_code="operation_digest_mismatch",
            )
            self._session.commit()
            raise RunnerServiceError(
                "operation_digest_mismatch",
                "Side-effect operation digest does not match the stored Job",
                category="policy",
            )
        existing = self._workspaces.side_effect_permit_for_attempt(
            job.id,
            attempt.id,
            job_digest,
            lock=True,
        )
        if existing is not None:
            if (
                existing.state == "consumed"
                and existing.expires_at > now
                and existing.runner_id == authenticated.id
                and hmac.compare_digest(str(existing.lease_id), str(attempt.lease_id))
            ):
                return self._protocol_side_effect_permit(
                    existing,
                    idempotent_replay=True,
                )
            self._conflict(
                "side_effect_permit_replay_denied",
                "The Side-effect Permit is no longer active",
            )
        if self._workspaces.in_flight_permits_for_workspace(workspace.id, lock=True):
            self._permit_denied_event(
                job,
                attempt,
                authenticated,
                request_id=request_id,
                reason_code="workspace_side_effect_in_flight",
            )
            self._session.commit()
            self._conflict(
                "workspace_side_effect_in_flight",
                "Another bounded Workspace side effect is still in flight",
            )

        binding = side_effect_job_binding(spec)
        expected_current = binding["expected_current"]
        if expected_current is None:
            expected_current = workspace.current_tree_hash
        if expected_current is None:
            self._conflict(
                "workspace_state_invalid",
                "Workspace current state is unavailable for side-effect fencing",
            )
        if isinstance(spec, WorkspaceWriteTextJobSpec):
            proposed_bytes = len(spec.content.encode("utf-8"))
            if workspace.total_written_bytes + proposed_bytes > policy.max_total_write_bytes:
                raise RunnerServiceError(
                    "total_write_budget_exceeded",
                    "Workspace write budget is exhausted",
                    category="policy",
                )

        permit_id = uuid.uuid4()
        sequence = self._workspaces.next_side_effect_permit_sequence(workspace.id)
        expires_at = min(
            attempt.leased_until,
            envelope.expires_at,
            grant.expires_at,
            now + timedelta(seconds=self._settings.side_effect_permit_ttl_seconds),
        )
        values: dict[str, Any] = {
            "id": permit_id,
            "sequence": sequence,
            "runner_id": authenticated.id,
            "job_id": job.id,
            "attempt_id": attempt.id,
            "lease_id": attempt.lease_id,
            "grant_id": grant.id,
            "workspace_id": workspace.id,
            "repository_handle_id": workspace.repository_handle_id,
            "operation": binding["operation"],
            "relative_path": binding["relative_path"],
            "expected_current": expected_current,
            "proposed_digest": binding["proposed_digest"],
            "job_digest": job_digest,
            "operation_digest": "0" * 64,
            "policy_hash": policy.policy_hash,
            "source_revision": policy.source_revision,
            "issued_at": now,
            "consumed_at": now,
            "expires_at": expires_at,
            "state": SideEffectPermitState.CONSUMED,
        }
        values["operation_digest"] = compute_side_effect_permit_digest(values)
        protocol_permit = SideEffectPermit.model_validate(values)
        permit = PersistedSideEffectPermit(
            **protocol_permit.model_dump(
                mode="python",
                exclude={"idempotent_replay"},
            ),
            request_id=request_id[:128],
        )
        self._workspaces.add(permit)
        self._session.flush()
        self._event(
            EventType.SIDE_EFFECT_PERMIT_ACQUIRED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={
                "operation": permit.operation,
                "permit_id_hint": _identifier_hint(permit.id),
            },
        )
        self._workspace_event(
            workspace,
            "permit_acquired",
            request_id=request_id,
            metadata={
                "job_id": str(job.id),
                "operation": permit.operation,
                "permit_id_hint": _identifier_hint(permit.id),
            },
            side_effect_permit_id=permit.id,
        )
        self._session.commit()
        return protocol_permit

    def renew(
        self,
        authenticated: Runner,
        job_id: uuid.UUID,
        payload: RenewRequest,
        *,
        request_id: str,
    ) -> LeaseMutationResponse:
        job, attempt, envelope = self._active_lease(
            authenticated, job_id, payload, allow_cancel_requested=True
        )
        replay = self._runners.event_by_request(
            event_type=EventType.LEASE_RENEWED.value,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
        )
        if replay is not None:
            return self._lease_response(
                job,
                attempt,
                cancel_requested=job.state == "cancel_requested",
                idempotent_replay=True,
            )
        now = utc_now()
        attempt.last_heartbeat_at = now
        attempt.leased_until = now + timedelta(seconds=envelope.lease_seconds)
        runner = self._locked_runner(authenticated.id)
        runner.last_seen_at = now
        runner.status = "online"
        runner.version += 1
        self._event(
            EventType.LEASE_RENEWED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={
                "lease_id_hint": _identifier_hint(attempt.lease_id),
            },
        )
        self._session.commit()
        return self._lease_response(
            job,
            attempt,
            cancel_requested=job.state == "cancel_requested",
        )

    def progress(
        self,
        authenticated: Runner,
        job_id: uuid.UUID,
        payload: ProgressEventRequest,
        *,
        request_id: str,
    ) -> LeaseMutationResponse:
        job, attempt, _ = self._active_lease(
            authenticated, job_id, payload, allow_cancel_requested=True
        )
        replay = self._runners.event_by_request(
            event_type=EventType.JOB_PROGRESS.value,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
        )
        if replay is None:
            self._event(
                EventType.JOB_PROGRESS,
                request_id=request_id,
                runner_id=authenticated.id,
                job_id=job.id,
                attempt_id=attempt.id,
                metadata={
                    "progress_percent": payload.progress_percent,
                    "message_code": payload.message_code,
                    "runner_sequence": payload.sequence,
                },
            )
            self._session.commit()
        return self._lease_response(
            job,
            attempt,
            cancel_requested=job.state == "cancel_requested",
            idempotent_replay=replay is not None,
        )

    def complete(
        self,
        authenticated: Runner,
        job_id: uuid.UUID,
        payload: CompleteRequest,
        *,
        request_id: str,
    ) -> LeaseMutationResponse:
        existing = self._runners.get_job(job_id, lock=True)
        if existing is not None and (
            existing.state == "succeeded"
            or (
                existing.state == "failed"
                and existing.kind == JobKind.VALIDATION_EXECUTE_V1.value
                and existing.result is not None
            )
        ):
            attempt = self._idempotent_terminal_attempt(authenticated, existing, payload)
            submitted = payload.result.model_dump(mode="json")
            if existing.result != submitted:
                self._conflict(
                    "terminal_result_conflict",
                    "A different terminal result is already stored",
                )
            return self._lease_response(existing, attempt, idempotent_replay=True)
        self._session.rollback()

        job, attempt, envelope = self._active_lease(
            authenticated,
            job_id,
            payload,
            allow_cancel_requested=True,
        )
        if job.state == "cancel_requested":
            self._conflict(
                "completion_after_cancel",
                "A cancel-requested Job cannot succeed",
            )
        if job.state != "running" or attempt.state != "running":
            self._conflict("invalid_job_transition", "Job cannot complete from its current state")
        if payload.result.kind.value != job.kind:
            raise RunnerServiceError(
                "result_kind_mismatch",
                "Result kind does not match the Job",
                category="policy",
            )
        try:
            validate_result_payload(payload.result, max_result_bytes=envelope.max_result_bytes)
        except ValueError as exc:
            raise RunnerServiceError(
                "result_rejected",
                "Runner result violated the result policy",
                category="policy",
            ) from exc

        now = utc_now()
        if isinstance(payload.result, ValidationExecutionResult):
            self._validate_validation_result(
                job,
                attempt,
                authenticated,
                payload.result,
                now=now,
            )
        self._complete_side_effect_permit(
            job,
            attempt,
            authenticated,
            payload.result,
            request_id=request_id,
            now=now,
        )
        if isinstance(payload.result, ValidationExecutionResult) and (
            payload.result.exit_code != 0 or payload.result.timed_out or payload.result.cancelled
        ):
            error_code = (
                FailureCode.VALIDATION_TIMED_OUT
                if payload.result.timed_out
                else FailureCode.VALIDATION_COMMAND_FAILED
            )
            transition_attempt(attempt, "failed")
            transition_job(job, "failed")
            attempt.error_code = error_code.value
            attempt.completed_at = now
            job.error_code = error_code.value
            job.error_message = "Validation Profile returned a governed failure"
            job.result = payload.result.model_dump(mode="json")
            job.completed_at = now
            job.active_attempt_id = None
            self._event(
                EventType.JOB_FAILED,
                request_id=request_id,
                runner_id=authenticated.id,
                job_id=job.id,
                attempt_id=attempt.id,
                metadata={"error_code": error_code.value, "kind": job.kind},
            )
            self._session.commit()
            self._log_event(
                "job_failed",
                runner_id=authenticated.id,
                job_id=job.id,
                attempt_id=attempt.id,
                lease_id=attempt.lease_id,
            )
            return self._lease_response(job, attempt)
        transition_attempt(attempt, "succeeded")
        transition_job(job, "succeeded")
        attempt.completed_at = now
        job.result = payload.result.model_dump(mode="json")
        job.completed_at = now
        job.active_attempt_id = None
        if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
            self._workspace_job_completed(
                job,
                payload.result,
                request_id=request_id,
                now=now,
            )
        self._event(
            EventType.JOB_SUCCEEDED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata=(
                {"duration_ms": _result_duration(payload.result)}
                if job.workspace_id is None
                else {"kind": job.kind}
            ),
        )
        self._session.commit()
        self._log_event(
            "job_succeeded",
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            lease_id=attempt.lease_id,
        )
        return self._lease_response(job, attempt)

    def fail(
        self,
        authenticated: Runner,
        job_id: uuid.UUID,
        payload: FailRequest,
        *,
        request_id: str,
    ) -> LeaseMutationResponse:
        existing = self._runners.get_job(job_id, lock=True)
        if existing is not None and existing.state == "failed":
            attempt = self._idempotent_terminal_attempt(authenticated, existing, payload)
            if existing.error_code != payload.error_code.value:
                self._conflict(
                    "terminal_result_conflict",
                    "A different terminal failure is already stored",
                )
            return self._lease_response(existing, attempt, idempotent_replay=True)
        self._session.rollback()

        allow_cancel_failure = payload.error_code in VALIDATION_RECOVERY_FAILURES
        job, attempt, _ = self._active_lease(
            authenticated,
            job_id,
            payload,
            allow_cancel_requested=allow_cancel_failure,
        )
        if job.state == "cancel_requested" and (
            job.kind != JobKind.VALIDATION_EXECUTE_V1.value or not allow_cancel_failure
        ):
            self._conflict(
                "invalid_cancel_failure",
                "Only a typed Validation recovery failure may terminalize cancellation",
            )
        if job.state not in {"leased", "running", "cancel_requested"}:
            self._conflict("invalid_job_transition", "Job cannot fail from its current state")
        try:
            safe_message = validate_safe_error_message(payload.error_message)
        except ValueError as exc:
            raise RunnerServiceError(
                "error_message_rejected",
                "Runner error message violated the redaction policy",
                category="policy",
            ) from exc
        now = utc_now()
        self._terminalize_side_effect_permit(
            payload.side_effect_permit_id,
            job,
            attempt,
            state="failed",
            request_id=request_id,
        )
        transition_attempt(attempt, "failed")
        transition_job(job, "failed")
        attempt.error_code = payload.error_code.value
        attempt.error_message = safe_message
        attempt.completed_at = now
        job.error_code = payload.error_code.value
        job.error_message = safe_message or "Runner reported a typed failure"
        job.completed_at = now
        job.active_attempt_id = None
        if (
            job.kind == JobKind.VALIDATION_EXECUTE_V1.value
            and payload.error_code in VALIDATION_RECOVERY_FAILURES
        ):
            validation_run = self._validation.get_by_job(job.id, lock=True)
            if validation_run is None:
                raise RunnerServiceError(
                    "validation_result_binding_missing",
                    "Trusted Validation Run binding is missing",
                    category="internal",
                )
            validation_step = self._validation.step(validation_run.id, lock=True)
            if validation_step is None:
                raise RunnerServiceError(
                    "validation_result_binding_missing",
                    "Trusted Validation step binding is missing",
                    category="internal",
                )
            validation_run.runner_id = authenticated.id
            validation_run.attempt_id = attempt.id
            validation_run.lease_id = attempt.lease_id
            validation_run.claimed_at = validation_run.claimed_at or attempt.created_at
            validation_run.started_at = validation_run.started_at or attempt.started_at
            validation_run.state = "recovery_required"
            validation_run.completed_at = now
            validation_run.error_code = payload.error_code.value
            validation_run.error_message = job.error_message
            validation_run.version += 1
            validation_step.state = "recovery_required"
            validation_step.started_at = (
                validation_step.started_at or validation_run.started_at or validation_run.claimed_at
            )
            validation_step.completed_at = now
            validation_step.failure_code = payload.error_code.value
        if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
            self._workspace_job_failed(
                job,
                error_code=payload.error_code.value,
                error_message=job.error_message,
                request_id=request_id,
                side_effect_permit_id=payload.side_effect_permit_id,
            )
        if payload.error_code.value in {
            "policy_denied",
            "unsupported_capability",
            "envelope_expired",
            "envelope_hash_mismatch",
            "result_rejected",
            "path_invalid",
            "path_denied",
            "sensitive_path_denied",
            "symlink_denied",
            "hardlink_denied",
            "not_regular_file",
            "binary_denied",
            "invalid_utf8",
            "file_too_large",
            "file_count_budget_exceeded",
            "total_write_budget_exceeded",
            "diff_budget_exceeded",
            "content_conflict",
            "expected_absent_conflict",
            "workspace_state_invalid",
            "side_effect_permit_required",
            "side_effect_permit_invalid",
            "side_effect_permit_expired",
            "workspace_recovery_required",
            "workspace_quarantined",
            "git_output_limit_exceeded",
            "mirror_budget_exceeded",
        }:
            self._event(
                EventType.POLICY_DENIED,
                request_id=request_id,
                runner_id=authenticated.id,
                job_id=job.id,
                attempt_id=attempt.id,
                metadata={"reason_code": payload.error_code.value},
            )
        self._event(
            EventType.JOB_FAILED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={"error_code": payload.error_code.value},
        )
        self._session.commit()
        self._log_event(
            "job_failed",
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            lease_id=attempt.lease_id,
            error_code=payload.error_code.value,
        )
        return self._lease_response(job, attempt)

    def cancelled(
        self,
        authenticated: Runner,
        job_id: uuid.UUID,
        payload: CancelledRequest,
        *,
        request_id: str,
    ) -> LeaseMutationResponse:
        existing = self._runners.get_job(job_id, lock=True)
        if existing is not None and existing.state == "cancelled":
            attempt = self._idempotent_terminal_attempt(authenticated, existing, payload)
            return self._lease_response(existing, attempt, idempotent_replay=True)
        self._session.rollback()

        job, attempt, _ = self._active_lease(
            authenticated, job_id, payload, allow_cancel_requested=True
        )
        if job.state != "cancel_requested":
            self._conflict(
                "cancel_not_requested",
                "Runner cannot acknowledge cancellation before it is requested",
            )
        now = utc_now()
        try:
            stored_spec = JOB_SPEC_ADAPTER.validate_python({"kind": job.kind, **job.parameters})
        except ValidationError as exc:
            raise RunnerServiceError(
                "stored_job_spec_invalid",
                "Stored Runner Job specification is invalid",
                category="internal",
            ) from exc
        validation_run = None
        validation_step = None
        if isinstance(
            stored_spec,
            (
                WorkspacePrepareJobSpec,
                WorkspaceWriteTextJobSpec,
                WorkspaceRollbackJobSpec,
                WorkspaceDiscardJobSpec,
                ValidationExecuteJobSpec,
            ),
        ):
            if isinstance(stored_spec, ValidationExecuteJobSpec):
                validation_run = self._validation.get_by_job(job.id, lock=True)
                if (
                    validation_run is None
                    or validation_run.id != stored_spec.validation_run_id
                    or validation_run.runner_job_id != job.id
                    or validation_run.workspace_id != stored_spec.workspace_id
                    or validation_run.workspace_id != job.workspace_id
                    or validation_run.execution_grant_id != job.execution_grant_id
                    or validation_run.execution_grant_id != stored_spec.execution_grant.id
                    or validation_run.run_id != stored_spec.execution_grant.run_id
                    or validation_run.plan_id != stored_spec.execution_grant.plan_id
                    or validation_run.source_revision != stored_spec.execution_grant.source_revision
                    or validation_run.checkpoint_id != stored_spec.checkpoint_id
                    or validation_run.checkpoint_fingerprint != stored_spec.checkpoint_fingerprint
                    or validation_run.profile_id != stored_spec.profile_id
                    or validation_run.profile_version != stored_spec.profile_version
                    or validation_run.policy_digest != stored_spec.validation_policy_digest
                    or validation_run.timeout_seconds != stored_spec.timeout_seconds
                    or validation_run.max_output_bytes != stored_spec.max_output_bytes
                    or validation_run.max_artifact_bytes != stored_spec.max_artifact_bytes
                    or validation_run.max_artifact_count != stored_spec.max_artifact_count
                    or validation_run.state
                    in {
                        "succeeded",
                        "failed",
                        "timed_out",
                        "cancelled",
                        "recovery_required",
                    }
                ):
                    self._conflict(
                        "validation_result_binding_mismatch",
                        "Validation cancellation does not match the trusted Run binding",
                    )
                validation_step = self._validation.step(validation_run.id, lock=True)
                if (
                    validation_step is None
                    or validation_step.validation_run_id != validation_run.id
                    or validation_step.step_id != stored_spec.validation_step_id
                ):
                    self._conflict(
                        "validation_result_binding_missing",
                        "Trusted Validation step binding is missing",
                    )
            existing_permit = self._workspaces.side_effect_permit_for_attempt(
                job.id,
                attempt.id,
                compute_side_effect_job_digest(stored_spec),
                lock=True,
            )
            self._terminalize_side_effect_permit(
                existing_permit.id if existing_permit is not None else None,
                job,
                attempt,
                state="cancelled",
                request_id=request_id,
            )
        transition_attempt(attempt, "cancelled")
        transition_job(job, "cancelled")
        attempt.completed_at = now
        job.completed_at = now
        job.active_attempt_id = None
        if (
            isinstance(stored_spec, ValidationExecuteJobSpec)
            and validation_run is not None
            and validation_step is not None
        ):
            validation_run.runner_id = authenticated.id
            validation_run.attempt_id = attempt.id
            validation_run.lease_id = attempt.lease_id
            validation_run.claimed_at = validation_run.claimed_at or attempt.created_at
            validation_run.started_at = validation_run.started_at or attempt.started_at
            validation_run.cancel_requested_at = validation_run.cancel_requested_at or now
            validation_run.state = "cancelled"
            validation_run.completed_at = now
            validation_run.error_code = None
            validation_run.error_message = None
            validation_run.version += 1
            validation_step.state = "cancelled"
            validation_step.started_at = (
                validation_step.started_at or validation_run.started_at or validation_run.claimed_at
            )
            validation_step.completed_at = now
            validation_step.failure_code = None
        if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
            self._workspace_job_cancelled(job, request_id=request_id)
        self._event(
            EventType.CANCEL_ACKNOWLEDGED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={"attempt_number": attempt.attempt_number},
        )
        self._session.commit()
        self._log_event(
            "cancel_acknowledged",
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            lease_id=attempt.lease_id,
        )
        return self._lease_response(job, attempt)

    def cancel_job(self, job_id: uuid.UUID, *, request_id: str) -> RunnerJobResponse:
        job = self._runners.get_job(job_id, lock=True)
        if job is None:
            raise RunnerServiceError(
                "runner_job_not_found",
                "Runner Job was not found",
                category="not_found",
            )
        if job.state == "cancelled" or job.state == "cancel_requested":
            return self._job_response(job)
        if job.state in {"succeeded", "failed"}:
            self._conflict("runner_job_terminal", "A terminal Runner Job cannot be cancelled")

        now = utc_now()
        if job.state == "queued":
            transition_job(job, "cancelled")
            job.completed_at = now
            if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
                self._workspace_job_cancelled(job, request_id=request_id)
        else:
            transition_job(job, "cancel_requested")
        attempt = (
            self._runners.get_attempt(job.active_attempt_id)
            if job.active_attempt_id is not None
            else None
        )
        self._event(
            EventType.CANCEL_REQUESTED,
            request_id=request_id,
            runner_id=attempt.runner_id if attempt is not None else None,
            job_id=job.id,
            attempt_id=attempt.id if attempt is not None else None,
            metadata={"state": job.state},
        )
        self._session.commit()
        self._log_event("cancel_requested", job_id=job.id)
        return self._job_response(job)

    def reap_expired(self, *, request_id: str = "lease-reaper") -> dict[str, int]:
        acquired = bool(
            self._session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": REAPER_ADVISORY_LOCK},
            )
        )
        if not acquired:
            self._session.rollback()
            return {"expired": 0, "requeued": 0, "failed": 0, "offline": 0}

        now = utc_now()
        expired_grant_ids: set[uuid.UUID] = set()
        permit_cutoff = now - timedelta(seconds=self._settings.side_effect_permit_safety_seconds)
        for permit in self._workspaces.expired_in_flight_permits(
            permit_cutoff,
            lock=True,
        ):
            permit.state = "expired"
            permit.terminal_at = now
            expired_grant_ids.add(permit.grant_id)
            self._event(
                EventType.SIDE_EFFECT_PERMIT_DENIED,
                request_id=request_id,
                runner_id=permit.runner_id,
                job_id=permit.job_id,
                attempt_id=permit.attempt_id,
                metadata={
                    "reason_code": "side_effect_permit_expired",
                    "permit_id_hint": _identifier_hint(permit.id),
                },
            )
        for grant_id in expired_grant_ids:
            self._maybe_finalize_grant_revocation(grant_id, request_id=request_id)
        cutoff = now - timedelta(seconds=self._settings.runner_online_threshold_seconds)
        offline_count = 0
        for runner in self._runners.runners_past_heartbeat(cutoff):
            runner.status = "offline"
            runner.version += 1
            offline_count += 1
            self._event(
                EventType.RUNNER_HEARTBEAT,
                request_id=request_id,
                runner_id=runner.id,
                metadata={
                    "status": "offline",
                    "reason_code": "heartbeat_timeout",
                },
            )

        expired_count = 0
        requeued_count = 0
        failed_count = 0
        for job in self._runners.expired_jobs(now):
            if job.active_attempt_id is None:
                continue
            attempt = self._runners.get_attempt(job.active_attempt_id, lock=True)
            if (
                attempt is None
                or attempt.state not in {"leased", "running"}
                or attempt.leased_until > now
            ):
                continue
            transition_attempt(attempt, "lease_expired")
            attempt.completed_at = now
            attempt.error_code = "lease_expired"
            attempt.error_message = "Runner lease expired"
            job.active_attempt_id = None
            if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
                workspace = self._workspaces.get_workspace(job.workspace_id, lock=True)
                if workspace is not None:
                    workspace.active_attempt_id = None
            expired_count += 1
            self._event(
                EventType.LEASE_EXPIRED,
                request_id=request_id,
                runner_id=attempt.runner_id,
                job_id=job.id,
                attempt_id=attempt.id,
                metadata={
                    "attempt_number": attempt.attempt_number,
                    "lease_id_hint": _identifier_hint(attempt.lease_id),
                },
            )
            if job.state == "cancel_requested":
                transition_job(job, "cancelled")
                job.completed_at = now
                if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
                    self._workspace_job_cancelled(job, request_id=request_id)
                continue
            if job.attempt_count < job.max_attempts:
                transition_job(job, "queued")
                requeued_count += 1
                self._event(
                    EventType.JOB_REQUEUED,
                    request_id=request_id,
                    runner_id=attempt.runner_id,
                    job_id=job.id,
                    attempt_id=attempt.id,
                    metadata={"retry_count": job.attempt_count},
                )
            else:
                transition_job(job, "failed")
                job.error_code = "retry_exhausted"
                job.error_message = "Runner Job retry budget was exhausted"
                job.completed_at = now
                failed_count += 1
                if job.workspace_id is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
                    self._workspace_job_failed(
                        job,
                        error_code="retry_exhausted",
                        error_message=job.error_message,
                        request_id=request_id,
                    )
                self._event(
                    EventType.JOB_FAILED,
                    request_id=request_id,
                    runner_id=attempt.runner_id,
                    job_id=job.id,
                    attempt_id=attempt.id,
                    metadata={"error_code": "retry_exhausted"},
                )

        self._session.commit()
        if expired_count or offline_count:
            self._log_event(
                "lease_reaper_completed",
                duration_ms=0,
                retry_count=requeued_count,
                event_count=expired_count,
            )
        return {
            "expired": expired_count,
            "requeued": requeued_count,
            "failed": failed_count,
            "offline": offline_count,
        }

    def _active_lease(
        self,
        authenticated: Runner,
        job_id: uuid.UUID,
        payload: StartRequest
        | RenewRequest
        | ProgressEventRequest
        | CompleteRequest
        | FailRequest
        | CancelledRequest
        | SideEffectPermitAcquireRequest,
        *,
        allow_cancel_requested: bool = False,
    ) -> tuple[RunnerJob, RunnerJobAttempt, PermissionEnvelope]:
        self._require_runner_identity(authenticated, payload.runner_id)
        job = self._runners.get_job(job_id, lock=True)
        if job is None:
            self._stale_lease()
        if job.active_attempt_id != payload.attempt_id:
            self._stale_lease()
        attempt = self._runners.get_attempt(payload.attempt_id, lock=True)
        if (
            attempt is None
            or attempt.job_id != job.id
            or attempt.runner_id != authenticated.id
            or not hmac.compare_digest(str(attempt.lease_id), str(payload.lease_id))
            or attempt.state not in {"leased", "running"}
        ):
            self._stale_lease()
        now = utc_now()
        if attempt.leased_until <= now:
            self._stale_lease()
        if job.state not in {"leased", "running"} and not (
            allow_cancel_requested and job.state == "cancel_requested"
        ):
            self._stale_lease()
        if job.workspace_id is not None:
            self._require_workspace_authority(job, authenticated, now)
        return job, attempt, self._required_envelope(job)

    def _idempotent_terminal_attempt(
        self,
        authenticated: Runner,
        job: RunnerJob,
        payload: CompleteRequest | FailRequest | CancelledRequest,
    ) -> RunnerJobAttempt:
        self._require_runner_identity(authenticated, payload.runner_id)
        attempt = self._runners.get_attempt(payload.attempt_id, lock=True)
        if (
            attempt is None
            or attempt.job_id != job.id
            or attempt.runner_id != authenticated.id
            or not hmac.compare_digest(str(attempt.lease_id), str(payload.lease_id))
        ):
            self._stale_lease()
        return attempt

    def _require_workspace_authority(
        self,
        job: RunnerJob,
        runner: Runner,
        now: datetime,
    ) -> ExecutionGrantPolicy:
        if (
            job.execution_grant_id is None
            or job.workspace_id is None
            or job.repository_handle_id is None
            or job.source_revision is None
            or job.execution_policy_hash is None
        ):
            raise RunnerServiceError(
                "workspace_binding_missing",
                "Workspace Job binding is incomplete",
                category="policy",
            )
        authority = self._workspaces.approved_grant_for_job(
            job.execution_grant_id,
            job.workspace_id,
            now,
        )
        if authority is None:
            raise RunnerServiceError(
                "execution_grant_inactive",
                "Execution Grant is revoked, expired, or unavailable",
                category="conflict",
            )
        grant, workspace = authority
        handle = self._workspaces.get_repository_handle(job.repository_handle_id, lock=True)
        cleanup_job = job.kind == JobKind.WORKSPACE_DISCARD_V1.value
        if (
            handle is None
            or handle.status != "available"
            or handle.runner_id != runner.id
            or handle.current_revision != grant.source_revision
            or workspace.runner_id != runner.id
            or workspace.repository_handle_id != handle.id
            or workspace.source_revision != grant.source_revision
            or job.repository_handle_id != grant.repository_handle_id
            or job.source_revision != grant.source_revision
            or job.execution_policy_hash != grant.policy_hash
            or (
                not cleanup_job
                and (
                    workspace.expires_at <= now
                    or workspace.state in {"discarded", "failed", "expired"}
                )
            )
        ):
            raise RunnerServiceError(
                "workspace_authority_mismatch",
                "Workspace, Runner, revision, or Grant binding is stale",
                category="conflict",
            )
        values = {
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
        try:
            policy = ExecutionGrantPolicy.model_validate(values)
            stored_spec = JOB_SPEC_ADAPTER.validate_python({"kind": job.kind, **job.parameters})
        except ValidationError as exc:
            raise RunnerServiceError(
                "execution_grant_invalid",
                "Stored Execution Grant policy is invalid",
                category="policy",
            ) from exc
        if (
            not execution_grant_policy_hash_matches(policy, policy.policy_hash)
            or not isinstance(stored_spec, WorkspaceBoundJobSpec)
            or stored_spec.workspace_id != workspace.id
            or stored_spec.execution_grant.model_dump(mode="json") != policy.model_dump(mode="json")
            or (
                isinstance(stored_spec, ValidationExecuteJobSpec)
                and (
                    grant.validation_workspace_id != workspace.id
                    or grant.validation_checkpoint_id != stored_spec.checkpoint_id
                    or workspace.current_tree_hash != stored_spec.checkpoint_fingerprint
                    or workspace.state not in {"ready", "active", "sealed", "rolled_back"}
                )
            )
        ):
            raise RunnerServiceError(
                "execution_grant_hash_mismatch",
                "Execution Grant policy hash or Job copy is invalid",
                category="policy",
            )
        return policy

    def _protocol_side_effect_permit(
        self,
        permit: PersistedSideEffectPermit,
        *,
        idempotent_replay: bool = False,
    ) -> SideEffectPermit:
        if permit.state != "consumed":
            self._conflict(
                "side_effect_permit_inactive",
                "Side-effect Permit is no longer active",
            )
        protocol = SideEffectPermit(
            id=permit.id,
            sequence=permit.sequence,
            runner_id=permit.runner_id,
            job_id=permit.job_id,
            attempt_id=permit.attempt_id,
            lease_id=permit.lease_id,
            grant_id=permit.grant_id,
            workspace_id=permit.workspace_id,
            repository_handle_id=permit.repository_handle_id,
            operation=permit.operation,
            relative_path=permit.relative_path,
            expected_current=permit.expected_current,
            proposed_digest=permit.proposed_digest,
            job_digest=permit.job_digest,
            operation_digest=permit.operation_digest,
            policy_hash=permit.policy_hash,
            source_revision=permit.source_revision,
            issued_at=permit.issued_at,
            consumed_at=permit.consumed_at,
            expires_at=permit.expires_at,
            state=SideEffectPermitState.CONSUMED,
            idempotent_replay=idempotent_replay,
        )
        if not side_effect_permit_digest_matches(protocol, protocol.operation_digest):
            raise RunnerServiceError(
                "side_effect_permit_digest_invalid",
                "Stored Side-effect Permit digest is invalid",
                category="policy",
            )
        return protocol

    def _validate_validation_result(
        self,
        job: RunnerJob,
        attempt: RunnerJobAttempt,
        authenticated: Runner,
        result: ValidationExecutionResult,
        *,
        now: datetime,
    ) -> None:
        try:
            stored_spec = JOB_SPEC_ADAPTER.validate_python({"kind": job.kind, **job.parameters})
        except ValidationError as exc:
            raise RunnerServiceError(
                "stored_job_spec_invalid",
                "Stored Runner Job specification is invalid",
                category="internal",
            ) from exc
        if not isinstance(stored_spec, ValidationExecuteJobSpec):
            self._conflict(
                "validation_result_binding_mismatch",
                "Validation result does not match the stored execution envelope",
            )

        validation_run = self._validation.get_by_job(job.id, lock=True)
        if validation_run is None:
            self._conflict(
                "validation_result_binding_missing",
                "Trusted Validation Run binding is missing",
            )
        step = self._validation.step(validation_run.id, lock=True)
        profile = validation_profile(validation_run.profile_id)
        if step is None or profile is None:
            self._conflict(
                "validation_result_binding_missing",
                "Trusted Validation step or Profile binding is missing",
            )
        if job.execution_grant_id is None:
            self._conflict(
                "validation_result_binding_missing",
                "Trusted Validation Grant binding is missing",
            )
        grant = self._workspaces.get_grant(job.execution_grant_id, lock=True)
        if grant is None:
            self._conflict(
                "validation_result_binding_missing",
                "Trusted Validation Grant binding is missing",
            )

        expected_policy_digest = compute_validation_policy_digest(
            {
                "grant_policy_hash": grant.policy_hash,
                "workspace_id": str(validation_run.workspace_id),
                "checkpoint_id": str(validation_run.checkpoint_id),
                "checkpoint_fingerprint": validation_run.checkpoint_fingerprint,
                "profile": profile.reference,
                "timeout_seconds": validation_run.timeout_seconds,
                "max_output_bytes": validation_run.max_output_bytes,
                "max_artifact_bytes": validation_run.max_artifact_bytes,
                "max_artifact_count": validation_run.max_artifact_count,
            }
        )
        trusted_binding_matches = (
            validation_run.id == stored_spec.validation_run_id
            and validation_run.runner_job_id == job.id
            and validation_run.workspace_id == stored_spec.workspace_id == job.workspace_id
            and validation_run.execution_grant_id
            == stored_spec.execution_grant.id
            == grant.id
            == job.execution_grant_id
            and validation_run.run_id == grant.run_id == stored_spec.execution_grant.run_id
            and validation_run.plan_id == grant.plan_id == stored_spec.execution_grant.plan_id
            and validation_run.profile_id == stored_spec.profile_id == profile.profile_id
            and validation_run.profile_version == stored_spec.profile_version == profile.version
            and validation_run.source_revision
            == stored_spec.execution_grant.source_revision
            == grant.source_revision
            == job.source_revision
            and validation_run.checkpoint_id
            == stored_spec.checkpoint_id
            == grant.validation_checkpoint_id
            and validation_run.checkpoint_fingerprint == stored_spec.checkpoint_fingerprint
            and validation_run.policy_digest
            == stored_spec.validation_policy_digest
            == expected_policy_digest
            and validation_run.timeout_seconds
            == stored_spec.timeout_seconds
            == profile.timeout_seconds
            and validation_run.max_output_bytes
            == stored_spec.max_output_bytes
            == profile.max_output_bytes
            and profile.max_output_bytes <= grant.validation_output_bytes
            and validation_run.max_artifact_bytes
            == stored_spec.max_artifact_bytes
            == profile.max_artifact_bytes
            == grant.validation_artifact_bytes
            and validation_run.max_artifact_count
            == stored_spec.max_artifact_count
            == profile.max_artifact_count
            == grant.validation_artifact_count
            and step.validation_run_id == validation_run.id
            and step.sequence == 1
            and step.step_id == stored_spec.validation_step_id == profile.step_id
            and validation_run.completed_at is None
            and validation_run.state
            not in {
                "succeeded",
                "failed",
                "timed_out",
                "cancelled",
                "recovery_required",
            }
        )
        result_binding_matches = (
            result.validation_run_id == validation_run.id
            and result.workspace_id == validation_run.workspace_id
            and result.checkpoint_id == validation_run.checkpoint_id
            and hmac.compare_digest(
                result.checkpoint_fingerprint,
                validation_run.checkpoint_fingerprint,
            )
            and result.profile_id == validation_run.profile_id
            and result.profile_version == validation_run.profile_version
            and result.fixed_argv == list(profile.safe_argv)
        )
        if not trusted_binding_matches or not result_binding_matches:
            self._conflict(
                "validation_result_binding_mismatch",
                "Validation result does not match the trusted execution envelope",
            )

        combined_output_bytes = len(result.stdout.encode("utf-8")) + len(
            result.stderr.encode("utf-8")
        )
        truncated = result.stdout_truncated or result.stderr_truncated
        if combined_output_bytes > validation_run.max_output_bytes or (
            truncated and combined_output_bytes != validation_run.max_output_bytes
        ):
            self._conflict(
                "validation_result_budget_exceeded",
                "Validation output violates the trusted byte budget",
            )
        if (
            result.artifact_count > validation_run.max_artifact_count
            or result.artifact_bytes > validation_run.max_artifact_bytes
        ):
            self._conflict(
                "validation_result_budget_exceeded",
                "Validation artifacts violate the trusted count or byte budget",
            )

        required_evidence = (
            result.result_schema_version,
            result.validation_step_id,
            result.source_revision,
            result.policy_digest,
            result.fixed_operation,
            result.fixed_argv_digest,
            result.fixed_cwd,
            result.fixed_environment_digest,
            result.artifacts,
            result.artifact_manifest_digest,
            result.side_effect_permit_sequence,
            result.side_effect_permit_digest,
            result.fencing_token,
            result.execution_envelope_digest,
            result.evidence_digest,
        )
        if any(value is None for value in required_evidence):
            self._conflict(
                "validation_result_evidence_missing",
                "Validation result is missing required execution evidence",
            )
        assert result.artifacts is not None
        artifact_payload = [artifact.model_dump(mode="json") for artifact in result.artifacts]
        artifact_paths = [artifact.relative_path for artifact in result.artifacts]
        computed_artifact_bytes = sum(artifact.size_bytes for artifact in result.artifacts)
        if (
            len(set(artifact_paths)) != len(artifact_paths)
            or result.artifact_count != len(result.artifacts)
            or result.artifact_bytes != computed_artifact_bytes
            or any(
                artifact.size_bytes > validation_run.max_artifact_bytes
                for artifact in result.artifacts
            )
            or result.artifact_count > validation_run.max_artifact_count
            or computed_artifact_bytes > validation_run.max_artifact_bytes
            or not hmac.compare_digest(
                result.artifact_manifest_digest or "",
                compute_validation_artifact_manifest_digest(artifact_payload),
            )
        ):
            self._conflict(
                "validation_result_artifact_invalid",
                "Validation artifact evidence is malformed or exceeds its trusted budget",
            )

        permit = self._workspaces.get_side_effect_permit(
            result.side_effect_permit_id,
            lock=True,
        )
        if permit is None:
            self._conflict(
                "side_effect_permit_invalid",
                "Validation result Permit is unavailable",
            )
        protocol_permit = self._protocol_side_effect_permit(permit)
        expected_binding = side_effect_job_binding(stored_spec)
        if (
            permit.job_id != job.id
            or permit.attempt_id != attempt.id
            or permit.runner_id != authenticated.id
            or permit.lease_id != attempt.lease_id
            or permit.grant_id != grant.id
            or permit.workspace_id != validation_run.workspace_id
            or permit.repository_handle_id != grant.repository_handle_id
            or permit.operation != WorkspaceOperation.VALIDATE.value
            or permit.expected_current != expected_binding["expected_current"]
            or permit.proposed_digest != expected_binding["proposed_digest"]
            or permit.job_digest != compute_side_effect_job_digest(stored_spec)
            or permit.policy_hash != grant.policy_hash
            or permit.source_revision != validation_run.source_revision
            or result.side_effect_permit_sequence != permit.sequence
            or not hmac.compare_digest(
                result.side_effect_permit_digest or "",
                permit.operation_digest,
            )
        ):
            self._conflict(
                "validation_result_fencing_mismatch",
                "Validation result does not match the active Permit fence",
            )
        safety_deadline = permit.expires_at + timedelta(
            seconds=self._settings.side_effect_permit_safety_seconds
        )
        if now > safety_deadline:
            self._conflict(
                "side_effect_permit_expired",
                "Validation result arrived outside the Permit fencing window",
            )

        expected_result_binding = validation_result_binding(stored_spec, protocol_permit)
        if (
            any(
                getattr(result, field) != expected
                for field, expected in expected_result_binding.items()
            )
            or not hmac.compare_digest(
                result.evidence_digest or "",
                compute_validation_evidence_digest(result),
            )
            or protocol_permit.operation_digest != permit.operation_digest
        ):
            self._conflict(
                "validation_result_evidence_invalid",
                "Validation result evidence does not match the trusted execution envelope",
            )

    def _complete_side_effect_permit(
        self,
        job: RunnerJob,
        attempt: RunnerJobAttempt,
        authenticated: Runner,
        result: ResultPayload,
        *,
        request_id: str,
        now: datetime,
    ) -> PersistedSideEffectPermit | None:
        if not isinstance(
            result,
            (
                WorkspacePrepareResult,
                WorkspaceWriteTextResult,
                WorkspaceRollbackResult,
                WorkspaceDiscardResult,
                ValidationExecutionResult,
            ),
        ):
            return None
        permit = self._workspaces.get_side_effect_permit(
            result.side_effect_permit_id,
            lock=True,
        )
        if (
            permit is None
            or permit.job_id != job.id
            or permit.attempt_id != attempt.id
            or permit.runner_id != authenticated.id
            or not hmac.compare_digest(str(permit.lease_id), str(attempt.lease_id))
            or permit.workspace_id != job.workspace_id
            or permit.grant_id != job.execution_grant_id
            or permit.state != "consumed"
        ):
            self._conflict(
                "side_effect_permit_invalid",
                "Side-effect result is not bound to the active Permit",
            )
        safety_deadline = permit.expires_at + timedelta(
            seconds=self._settings.side_effect_permit_safety_seconds
        )
        if now > safety_deadline:
            permit.state = "expired"
            permit.terminal_at = now
            workspace = self._workspaces.get_workspace(permit.workspace_id, lock=True)
            if workspace is not None and job.kind != JobKind.VALIDATION_EXECUTE_V1.value:
                workspace.state = "quarantined"
                workspace.error_code = "side_effect_permit_expired"
                workspace.error_message = "Side-effect result arrived outside the fencing window"
                workspace.active_attempt_id = None
                self._workspace_event(
                    workspace,
                    "workspace_quarantined",
                    request_id=request_id,
                    metadata={
                        "job_id": str(job.id),
                        "reason_code": "side_effect_permit_expired",
                        "state": workspace.state,
                    },
                    side_effect_permit_id=permit.id,
                )
            self._event(
                EventType.SIDE_EFFECT_PERMIT_DENIED,
                request_id=request_id,
                runner_id=authenticated.id,
                job_id=job.id,
                attempt_id=attempt.id,
                metadata={"reason_code": "side_effect_permit_expired"},
            )
            self._session.commit()
            self._conflict(
                "side_effect_permit_expired",
                "Side-effect Permit expired before result coordination",
            )
        permit.state = "completed"
        permit.terminal_at = now
        self._event(
            EventType.SIDE_EFFECT_PERMIT_COMPLETED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={
                "operation": permit.operation,
                "permit_id_hint": _identifier_hint(permit.id),
            },
        )
        workspace = self._workspaces.get_workspace(permit.workspace_id, lock=True)
        if workspace is not None:
            self._workspace_event(
                workspace,
                "permit_completed",
                request_id=request_id,
                metadata={
                    "job_id": str(job.id),
                    "operation": permit.operation,
                    "permit_id_hint": _identifier_hint(permit.id),
                },
                side_effect_permit_id=permit.id,
            )
        self._maybe_finalize_grant_revocation(permit.grant_id, request_id=request_id)
        return permit

    def _terminalize_side_effect_permit(
        self,
        permit_id: uuid.UUID | None,
        job: RunnerJob,
        attempt: RunnerJobAttempt,
        *,
        state: str,
        request_id: str,
    ) -> None:
        if permit_id is None:
            return
        permit = self._workspaces.get_side_effect_permit(permit_id, lock=True)
        if (
            permit is None
            or permit.job_id != job.id
            or permit.attempt_id != attempt.id
            or not hmac.compare_digest(str(permit.lease_id), str(attempt.lease_id))
        ):
            self._conflict(
                "side_effect_permit_invalid",
                "Side-effect Permit does not match the active Attempt",
            )
        if permit.state == "consumed":
            permit.state = state
            permit.terminal_at = utc_now()
        elif permit.state not in {state, "expired"}:
            self._conflict(
                "side_effect_permit_terminal",
                "Side-effect Permit already has a different terminal state",
            )
        self._maybe_finalize_grant_revocation(permit.grant_id, request_id=request_id)

    def _maybe_finalize_grant_revocation(
        self,
        grant_id: uuid.UUID,
        *,
        request_id: str,
    ) -> None:
        grant = self._workspaces.get_grant(grant_id, lock=True)
        if grant is None or grant.status != "revoke_requested":
            return
        now = utc_now()
        cutoff = now - timedelta(seconds=self._settings.side_effect_permit_safety_seconds)
        for permit in self._workspaces.expired_in_flight_permits(cutoff, lock=True):
            if permit.grant_id == grant.id:
                permit.state = "expired"
                permit.terminal_at = now
        if self._workspaces.in_flight_permits_for_grant(grant.id, lock=True):
            return
        grant.status = "revoked"
        grant.revoked_at = now
        workspace_jobs = self._workspaces.active_jobs_for_grant(grant.id, lock=True)
        for active_job in workspace_jobs:
            if active_job.workspace_id is None:
                continue
            workspace = self._workspaces.get_workspace(active_job.workspace_id, lock=True)
            if workspace is not None:
                self._workspace_event(
                    workspace,
                    "grant_revoke_effective",
                    request_id=request_id,
                    metadata={"state": "revoked"},
                )

    def _permit_denied_event(
        self,
        job: RunnerJob,
        attempt: RunnerJobAttempt,
        authenticated: Runner,
        *,
        request_id: str,
        reason_code: str,
    ) -> None:
        self._event(
            EventType.SIDE_EFFECT_PERMIT_DENIED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={"reason_code": reason_code},
        )
        if job.workspace_id is not None:
            workspace = self._workspaces.get_workspace(job.workspace_id, lock=True)
            if workspace is not None:
                self._workspace_event(
                    workspace,
                    "permit_denied",
                    request_id=request_id,
                    metadata={
                        "job_id": str(job.id),
                        "reason_code": reason_code,
                        "state": workspace.state,
                    },
                )

    def _workspace_job_started(
        self,
        job: RunnerJob,
        attempt: RunnerJobAttempt,
        *,
        request_id: str,
    ) -> None:
        if job.workspace_id is None:
            return
        workspace = self._workspaces.get_workspace(job.workspace_id, lock=True)
        if workspace is None:
            raise RunnerServiceError(
                "workspace_not_found",
                "Workspace was not found",
                category="conflict",
            )
        if job.kind == JobKind.WORKSPACE_PREPARE_V1.value:
            if workspace.state not in {"requested", "preparing"}:
                self._conflict(
                    "workspace_state_invalid",
                    "Workspace cannot be prepared from its current state",
                )
            workspace.state = "preparing"
        elif job.kind == JobKind.WORKSPACE_DIFF_V1.value:
            if workspace.state not in {"ready", "active", "sealed"}:
                self._conflict(
                    "workspace_state_invalid",
                    "Workspace diff is unavailable from its current state",
                )
            if workspace.state != "sealed":
                workspace.state = "sealing"
        elif job.kind == JobKind.WORKSPACE_ROLLBACK_V1.value:
            if workspace.state != "rollback_requested":
                self._conflict(
                    "workspace_state_invalid",
                    "Workspace rollback was not requested",
                )
        elif job.kind == JobKind.WORKSPACE_DISCARD_V1.value:
            if workspace.state != "discard_requested":
                self._conflict(
                    "workspace_state_invalid",
                    "Workspace discard was not requested",
                )
        else:
            allowed_states = {"ready", "active", "sealed", "rolled_back"}
            if workspace.state not in allowed_states:
                self._conflict(
                    "workspace_state_invalid",
                    "Workspace tool is unavailable from its current state",
                )
            if job.kind == JobKind.WORKSPACE_WRITE_TEXT_V1.value and workspace.state not in {
                "ready",
                "active",
            }:
                self._conflict(
                    "workspace_state_invalid",
                    "A sealed or rolled-back Workspace cannot be written",
                )
            if workspace.state == "ready":
                workspace.state = "active"
        workspace.active_attempt_id = attempt.id
        self._workspace_event(
            workspace,
            "tool_started",
            request_id=request_id,
            metadata={"job_id": str(job.id), "kind": job.kind},
        )

    def _workspace_job_completed(
        self,
        job: RunnerJob,
        result: ResultPayload,
        *,
        request_id: str,
        now: datetime,
    ) -> None:
        if job.workspace_id is None:
            return
        workspace = self._workspaces.get_workspace(job.workspace_id, lock=True)
        if workspace is None:
            raise RunnerServiceError(
                "workspace_not_found",
                "Workspace was not found",
                category="conflict",
            )
        workspace.active_attempt_id = None
        workspace.error_code = None
        workspace.error_message = None
        side_effect_permit_id = getattr(result, "side_effect_permit_id", None)
        if isinstance(result, WorkspacePrepareResult):
            if (
                result.workspace_id != workspace.id
                or result.repository_handle_id != workspace.repository_handle_id
                or result.source_revision != workspace.source_revision
                or result.initial_tree_hash != result.current_tree_hash
            ):
                raise RunnerServiceError(
                    "workspace_result_mismatch",
                    "Workspace preparation result does not match its binding",
                    category="policy",
                )
            workspace.workspace_fingerprint = result.workspace_fingerprint
            workspace.initial_tree_hash = result.initial_tree_hash
            workspace.current_tree_hash = result.current_tree_hash
            workspace.state = "ready"
            self._workspace_event(
                workspace,
                "mirror_prepared",
                request_id=request_id,
                metadata={"source_revision": result.source_revision},
                side_effect_permit_id=side_effect_permit_id,
            )
            self._workspace_event(
                workspace,
                "workspace_prepared",
                request_id=request_id,
                metadata={"state": workspace.state},
                side_effect_permit_id=side_effect_permit_id,
            )
        elif isinstance(result, (WorkspaceListResult, WorkspaceReadTextResult)):
            if workspace.state == "ready":
                workspace.state = "active"
        elif isinstance(result, WorkspaceStatusResult):
            workspace.current_tree_hash = result.current_tree_hash
            workspace.changed_file_count = result.changed_file_count
            if workspace.state == "ready":
                workspace.state = "active"
        elif isinstance(result, WorkspaceWriteTextResult):
            workspace.current_tree_hash = result.current_tree_hash
            workspace.changed_file_count = result.changed_file_count
            workspace.total_written_bytes = result.total_written_bytes
            if result.operation.value == "create":
                workspace.created_paths = sorted(
                    set([*workspace.created_paths, result.relative_path])
                )
            workspace.state = "active"
            self._create_workspace_checkpoint(
                workspace,
                result.checkpoint,
                request_id=request_id,
            )
        elif isinstance(result, WorkspaceDiffResult):
            workspace.current_tree_hash = result.current_tree_hash
            workspace.changed_file_count = len(result.changed_paths)
            workspace.state = "sealed"
            workspace.sealed_at = now
            self._create_workspace_checkpoint(
                workspace,
                result.checkpoint,
                request_id=request_id,
            )
            self._workspace_event(
                workspace,
                "diff_generated",
                request_id=request_id,
                metadata={
                    "diff_hash": result.diff_hash,
                    "changed_file_count": len(result.changed_paths),
                },
            )
            self._workspace_event(
                workspace,
                "workspace_sealed",
                request_id=request_id,
                metadata={"state": workspace.state},
                side_effect_permit_id=side_effect_permit_id,
            )
        elif isinstance(result, WorkspaceRollbackResult):
            if (
                not result.clean
                or workspace.initial_tree_hash is None
                or result.current_tree_hash != workspace.initial_tree_hash
            ):
                raise RunnerServiceError(
                    "rollback_verification_failed",
                    "Workspace rollback did not restore the initial baseline",
                    category="policy",
                )
            workspace.current_tree_hash = result.current_tree_hash
            workspace.changed_file_count = 0
            workspace.total_written_bytes = 0
            workspace.created_paths = []
            workspace.state = "rolled_back"
            self._workspace_event(
                workspace,
                "rollback_completed",
                request_id=request_id,
                metadata={"state": workspace.state},
                side_effect_permit_id=side_effect_permit_id,
            )
        elif isinstance(result, WorkspaceDiscardResult):
            workspace.state = "discarded"
            workspace.discarded_at = now
            self._workspace_event(
                workspace,
                "workspace_discarded",
                request_id=request_id,
                metadata={"state": workspace.state},
                side_effect_permit_id=side_effect_permit_id,
            )
        else:
            raise RunnerServiceError(
                "workspace_result_mismatch",
                "Workspace Job returned an incompatible result",
                category="policy",
            )
        self._workspace_event(
            workspace,
            "tool_succeeded",
            request_id=request_id,
            metadata={"job_id": str(job.id), "kind": job.kind, "state": workspace.state},
            side_effect_permit_id=side_effect_permit_id,
        )

    def _workspace_job_failed(
        self,
        job: RunnerJob,
        *,
        error_code: str,
        error_message: str,
        request_id: str,
        side_effect_permit_id: uuid.UUID | None = None,
    ) -> None:
        if job.workspace_id is None:
            return
        workspace = self._workspaces.get_workspace(job.workspace_id, lock=True)
        if workspace is None:
            return
        workspace.active_attempt_id = None
        denial_codes = {
            "path_invalid",
            "path_denied",
            "sensitive_path_denied",
            "symlink_denied",
            "hardlink_denied",
            "not_regular_file",
            "binary_denied",
            "invalid_utf8",
            "file_too_large",
            "file_count_budget_exceeded",
            "total_write_budget_exceeded",
            "diff_budget_exceeded",
            "content_conflict",
            "expected_absent_conflict",
            "workspace_state_invalid",
            "side_effect_permit_required",
            "side_effect_permit_invalid",
            "side_effect_permit_expired",
        }
        if error_code == "workspace_recovery_required":
            workspace.state = "recovery_required"
            workspace.error_code = error_code
            workspace.error_message = error_message[:500]
            event_type = "recovery_required"
        elif error_code == "workspace_quarantined":
            workspace.state = "quarantined"
            workspace.error_code = error_code
            workspace.error_message = error_message[:500]
            event_type = "workspace_quarantined"
        elif job.kind == JobKind.WORKSPACE_PREPARE_V1.value or error_code not in denial_codes:
            workspace.state = "failed"
            workspace.error_code = error_code[:64]
            workspace.error_message = error_message[:500]
            event_type = "workspace_failed"
        else:
            if workspace.state == "sealing":
                workspace.state = "sealed" if workspace.sealed_at is not None else "active"
            event_type = "tool_denied"
        self._workspace_event(
            workspace,
            event_type,
            request_id=request_id,
            metadata={
                "job_id": str(job.id),
                "kind": job.kind,
                "error_code": error_code,
                "state": workspace.state,
            },
            side_effect_permit_id=side_effect_permit_id,
        )

    def _workspace_job_cancelled(
        self,
        job: RunnerJob,
        *,
        request_id: str,
    ) -> None:
        if job.workspace_id is None:
            return
        workspace = self._workspaces.get_workspace(job.workspace_id, lock=True)
        if workspace is None:
            return
        workspace.active_attempt_id = None
        if job.kind in {
            JobKind.WORKSPACE_PREPARE_V1.value,
            JobKind.WORKSPACE_ROLLBACK_V1.value,
            JobKind.WORKSPACE_DISCARD_V1.value,
        }:
            workspace.state = "failed"
            workspace.error_code = "workspace_cancelled"
            workspace.error_message = "Workspace operation was cancelled"
            event_type = "workspace_failed"
        else:
            if workspace.state == "sealing":
                workspace.state = "sealed" if workspace.sealed_at is not None else "active"
            event_type = "tool_denied"
        self._workspace_event(
            workspace,
            event_type,
            request_id=request_id,
            metadata={
                "job_id": str(job.id),
                "kind": job.kind,
                "reason_code": "workspace_cancelled",
                "state": workspace.state,
            },
        )

    def _create_workspace_checkpoint(
        self,
        workspace: Workspace,
        payload: WorkspaceCheckpointPayload,
        *,
        request_id: str,
    ) -> None:
        sequence = self._workspaces.next_checkpoint_sequence(workspace.id)
        checkpoint = WorkspaceCheckpoint(
            workspace_id=workspace.id,
            side_effect_permit_id=payload.side_effect_permit_id,
            sequence=sequence,
            source_revision=payload.source_revision,
            tree_fingerprint=payload.tree_fingerprint,
            diff_hash=payload.diff_hash,
            changed_paths=payload.changed_paths,
            changed_file_count=payload.changed_file_count,
            total_diff_bytes=payload.total_diff_bytes,
            diff_artifact=payload.diff,
        )
        self._workspaces.add(checkpoint)
        self._session.flush()
        self._workspace_event(
            workspace,
            "checkpoint_created",
            request_id=request_id,
            metadata={
                "checkpoint_sequence": sequence,
                "diff_hash": payload.diff_hash,
                "changed_file_count": payload.changed_file_count,
                "permit_id_hint": _identifier_hint(payload.side_effect_permit_id),
            },
            side_effect_permit_id=payload.side_effect_permit_id,
        )

    def _workspace_event(
        self,
        workspace: Workspace,
        event_type: str,
        *,
        request_id: str,
        metadata: dict[str, Any],
        side_effect_permit_id: uuid.UUID | None = None,
    ) -> None:
        allowed = {
            "changed_file_count",
            "checkpoint_sequence",
            "diff_hash",
            "error_code",
            "job_id",
            "kind",
            "operation",
            "permit_id_hint",
            "policy_hash",
            "reason_code",
            "relative_path",
            "source_revision",
            "state",
            "total_written_bytes",
        }
        sanitized: dict[str, Any] = {}
        for key, value in metadata.items():
            if key not in allowed:
                continue
            if isinstance(value, str):
                if key == "relative_path" and value.startswith("/"):
                    continue
                sanitized[key] = value[:128]
            elif isinstance(value, (bool, int, float)):
                sanitized[key] = value
        self._workspaces.add(
            WorkspaceEvent(
                workspace_id=workspace.id,
                runner_id=workspace.runner_id,
                side_effect_permit_id=side_effect_permit_id,
                event_type=event_type,
                sequence=self._workspaces.next_workspace_event_sequence(workspace.id),
                request_id=request_id[:128],
                details=sanitized,
            )
        )
        self._session.flush()

    def _required_envelope(self, job: RunnerJob) -> PermissionEnvelope:
        envelope = self._runners.get_envelope(job.permission_envelope_id)
        if envelope is None or envelope.job_id != job.id:
            raise RunnerServiceError(
                "permission_envelope_missing",
                "Runner Job permission policy is unavailable",
                category="policy",
            )
        return envelope

    def _protocol_envelope(self, envelope: PermissionEnvelope) -> ProtocolPermissionEnvelope:
        return ProtocolPermissionEnvelope.model_validate(
            {
                "id": envelope.id,
                "envelope_version": envelope.envelope_version,
                "job_id": envelope.job_id,
                "authorization_source": envelope.authorization_source,
                "allowed_capabilities": envelope.allowed_capabilities,
                "repository_access": envelope.repository_access,
                "shell_access": envelope.shell_access,
                "network_policy": envelope.network_policy,
                "max_runtime_seconds": envelope.max_runtime_seconds,
                "lease_seconds": envelope.lease_seconds,
                "max_attempts": envelope.max_attempts,
                "max_result_bytes": envelope.max_result_bytes,
                "issued_at": envelope.issued_at,
                "expires_at": envelope.expires_at,
                "policy_hash": envelope.policy_hash,
            }
        )

    def _assignment(self, job: RunnerJob, attempt: RunnerJobAttempt) -> JobAssignment:
        envelope = self._required_envelope(job)
        try:
            spec = JOB_SPEC_ADAPTER.validate_python({"kind": job.kind, **job.parameters})
        except ValidationError as exc:
            raise RunnerServiceError(
                "stored_job_spec_invalid",
                "Stored Runner Job specification is invalid",
                category="internal",
            ) from exc
        return JobAssignment(
            job_id=job.id,
            attempt_id=attempt.id,
            lease_id=attempt.lease_id,
            attempt_number=attempt.attempt_number,
            job=spec,
            permission_envelope=self._protocol_envelope(envelope),
            leased_until=attempt.leased_until,
        )

    def _runner_response(self, runner: Runner) -> RunnerResponse:
        active_attempt = self._runners.active_attempt_for_runner(runner.id)
        active_job = (
            self._runners.get_job(active_attempt.job_id) if active_attempt is not None else None
        )
        return RunnerResponse(
            id=runner.id,
            display_name=runner.display_name,
            protocol_version=runner.protocol_version,
            software_version=runner.software_version,
            capabilities=runner.capabilities,
            status=self._effective_runner_status(runner),
            last_seen_at=runner.last_seen_at,
            registered_at=runner.registered_at,
            revoked_at=runner.revoked_at,
            version=runner.version,
            created_at=runner.created_at,
            updated_at=runner.updated_at,
            active_job=(
                ActiveJobSummary(
                    id=active_job.id,
                    kind=JobKind(active_job.kind),
                    state=JobState(active_job.state),
                )
                if active_job is not None
                else None
            ),
        )

    def _job_response(self, job: RunnerJob) -> RunnerJobResponse:
        envelope = self._required_envelope(job)
        attempts = self._runners.list_attempts(job.id)
        active_attempt = next(
            (item for item in attempts if item.id == job.active_attempt_id),
            None,
        )
        result: ResultPayload | None = None
        if job.result is not None:
            try:
                result = RESULT_ADAPTER.validate_python(job.result)
            except ValidationError as exc:
                raise RunnerServiceError(
                    "stored_result_invalid",
                    "Stored Runner result is invalid",
                    category="internal",
                ) from exc
        return RunnerJobResponse(
            id=job.id,
            kind=JobKind(job.kind),
            state=JobState(job.state),
            requested_by=job.requested_by,
            parameters=job.parameters,
            execution_grant_id=job.execution_grant_id,
            workspace_id=job.workspace_id,
            repository_handle_id=job.repository_handle_id,
            source_revision=job.source_revision,
            execution_policy_hash=job.execution_policy_hash,
            active_attempt_id=job.active_attempt_id,
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            result=result,
            error_code=job.error_code,
            error_message=job.error_message,
            version=job.version,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            permission_envelope=PermissionEnvelopeResponse(
                id=envelope.id,
                envelope_version=envelope.envelope_version,
                job_id=envelope.job_id,
                authorization_source=envelope.authorization_source,
                allowed_capabilities=envelope.allowed_capabilities,
                repository_access=envelope.repository_access,
                shell_access=envelope.shell_access,
                network_policy=envelope.network_policy,
                max_runtime_seconds=envelope.max_runtime_seconds,
                lease_seconds=envelope.lease_seconds,
                max_attempts=envelope.max_attempts,
                max_result_bytes=envelope.max_result_bytes,
                issued_at=envelope.issued_at,
                expires_at=envelope.expires_at,
                policy_hash=envelope.policy_hash,
                created_at=envelope.created_at,
            ),
            active_attempt=(
                self._attempt_response(active_attempt) if active_attempt is not None else None
            ),
            attempts=[self._attempt_response(item) for item in attempts],
        )

    @staticmethod
    def _attempt_response(attempt: RunnerJobAttempt) -> RunnerJobAttemptResponse:
        return RunnerJobAttemptResponse(
            id=attempt.id,
            job_id=attempt.job_id,
            runner_id=attempt.runner_id,
            attempt_number=attempt.attempt_number,
            lease_id_hint=_identifier_hint(attempt.lease_id),
            state=attempt.state,
            leased_until=attempt.leased_until,
            last_heartbeat_at=attempt.last_heartbeat_at,
            started_at=attempt.started_at,
            completed_at=attempt.completed_at,
            error_code=attempt.error_code,
            error_message=attempt.error_message,
            created_at=attempt.created_at,
        )

    def _effective_runner_status(self, runner: Runner) -> RunnerStatus:
        if runner.status == "revoked":
            return RunnerStatus.REVOKED
        if runner.last_seen_at is None:
            return RunnerStatus.REGISTERED
        threshold = timedelta(seconds=self._settings.runner_online_threshold_seconds)
        if utc_now() - runner.last_seen_at > threshold:
            return RunnerStatus.OFFLINE
        return RunnerStatus.ONLINE

    def _locked_runner(self, runner_id: uuid.UUID) -> Runner:
        runner = self._runners.get_runner(runner_id, lock=True)
        if runner is None or runner.status == "revoked":
            raise RunnerServiceError(
                "runner_auth_invalid",
                "Runner authentication failed",
                category="auth",
            )
        return runner

    @staticmethod
    def _require_runner_identity(authenticated: Runner, supplied: uuid.UUID) -> None:
        if authenticated.id != supplied:
            raise RunnerServiceError(
                "runner_identity_mismatch",
                "Runner identity does not match its credential",
                category="forbidden",
            )

    def _event(
        self,
        event_type: EventType,
        *,
        request_id: str,
        runner_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
        attempt_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = RunnerJobEvent(
            runner_id=runner_id,
            job_id=job_id,
            attempt_id=attempt_id,
            event_type=event_type.value,
            sequence=self._runners.next_event_sequence(
                job_id=job_id,
                runner_id=runner_id,
            ),
            request_id=request_id[:128],
            details=_sanitize_event_metadata(metadata or {}),
        )
        self._runners.add(event)
        self._session.flush()

    @staticmethod
    def _lease_response(
        job: RunnerJob,
        attempt: RunnerJobAttempt,
        *,
        cancel_requested: bool = False,
        idempotent_replay: bool = False,
    ) -> LeaseMutationResponse:
        return LeaseMutationResponse(
            job_id=job.id,
            attempt_id=attempt.id,
            state=JobState(job.state),
            leased_until=(attempt.leased_until if attempt.state in {"leased", "running"} else None),
            cancel_requested=cancel_requested or job.state == "cancel_requested",
            idempotent_replay=idempotent_replay,
        )

    @staticmethod
    def _stale_lease() -> NoReturn:
        raise RunnerServiceError(
            "stale_lease",
            "Runner lease is expired, mismatched, or superseded",
            category="conflict",
        )

    @staticmethod
    def _conflict(code: str, message: str) -> NoReturn:
        raise RunnerServiceError(code, message, category="conflict")

    @staticmethod
    def _log_event(
        event: str,
        *,
        runner_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
        attempt_id: uuid.UUID | None = None,
        lease_id: uuid.UUID | None = None,
        error_code: str | None = None,
        duration_ms: float | None = None,
        retry_count: int | None = None,
        event_count: int | None = None,
    ) -> None:
        LOGGER.info(
            "%s",
            {
                "event": event,
                "protocol_version": RUNNER_PROTOCOL_VERSION,
                "runner_id": _identifier_hint(runner_id),
                "job_id": _identifier_hint(job_id),
                "attempt_id": _identifier_hint(attempt_id),
                "lease_id": _identifier_hint(lease_id),
                "error_code": error_code,
                "duration_ms": duration_ms,
                "retry_count": retry_count,
                "event_count": event_count,
            },
        )


def _identifier_hint(value: uuid.UUID | None) -> str | None:
    return str(value)[:8] if value is not None else None


def _result_duration(result: ResultPayload) -> float:
    if isinstance(result, DiagnosticResult):
        return float(result.duration_ms)
    if isinstance(result, ControlledWaitResult):
        return float(result.elapsed_duration_ms)
    return 0.0


def _sanitize_event_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "attempt_number",
        "duration_ms",
        "error_code",
        "kind",
        "lease_id_hint",
        "message_code",
        "operation",
        "permit_id_hint",
        "policy_hash",
        "progress_percent",
        "protocol_version",
        "reason_code",
        "retry_count",
        "runner_sequence",
        "state",
        "status",
    }
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        if key not in allowed_keys:
            continue
        if isinstance(value, str):
            sanitized[key] = value[:128]
        elif isinstance(value, (bool, int, float)):
            sanitized[key] = value
    return sanitized
