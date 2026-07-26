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
from visual_engineer_api.repositories.runner import RunnerRepository
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
    EventType,
    FailRequest,
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
    StartRequest,
    SystemDiagnosticJobSpec,
    compute_permission_policy_hash,
    validate_result_payload,
    validate_safe_error_message,
)
from visual_engineer_runner_protocol import (
    PermissionEnvelope as ProtocolPermissionEnvelope,
)

LOGGER = logging.getLogger("visual_engineer_api.runner")
RESULT_ADAPTER: TypeAdapter[ResultPayload] = TypeAdapter(ResultPayload)
REAPER_ADVISORY_LOCK = 8_617_203_003


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
        now = utc_now()
        job_id = uuid.uuid4()
        envelope_id = uuid.uuid4()
        kind = JobKind(spec.kind)
        max_runtime = (
            10
            if isinstance(spec, SystemDiagnosticJobSpec)
            else min(60, math.ceil(spec.duration_ms / 1000) + 5)
        )
        envelope_values: dict[str, Any] = {
            "id": envelope_id,
            "envelope_version": 1,
            "job_id": job_id,
            "authorization_source": "local_user_job_dispatch",
            "allowed_capabilities": [kind.value],
            "repository_access": "none",
            "shell_access": False,
            "network_policy": "control_plane_only",
            "max_runtime_seconds": max_runtime,
            "lease_seconds": self._settings.runner_lease_seconds,
            "max_attempts": self._settings.runner_job_max_attempts,
            "max_result_bytes": self._settings.runner_max_result_bytes,
            "issued_at": now,
            "expires_at": now + timedelta(seconds=self._settings.runner_envelope_ttl_seconds),
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

        job = self._runners.claimable_job(runner.capabilities)
        if job is None:
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
        if existing is not None and existing.state == "succeeded":
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
        transition_attempt(attempt, "succeeded")
        transition_job(job, "succeeded")
        attempt.completed_at = now
        job.result = payload.result.model_dump(mode="json")
        job.completed_at = now
        job.active_attempt_id = None
        self._event(
            EventType.JOB_SUCCEEDED,
            request_id=request_id,
            runner_id=authenticated.id,
            job_id=job.id,
            attempt_id=attempt.id,
            metadata={"duration_ms": _result_duration(payload.result)},
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

        job, attempt, _ = self._active_lease(
            authenticated, job_id, payload, allow_cancel_requested=False
        )
        if job.state not in {"leased", "running"}:
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
        transition_attempt(attempt, "failed")
        transition_job(job, "failed")
        attempt.error_code = payload.error_code.value
        attempt.error_message = safe_message
        attempt.completed_at = now
        job.error_code = payload.error_code.value
        job.error_message = safe_message or "Runner reported a typed failure"
        job.completed_at = now
        job.active_attempt_id = None
        if payload.error_code.value in {
            "policy_denied",
            "unsupported_capability",
            "envelope_expired",
            "envelope_hash_mismatch",
            "result_rejected",
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
        transition_attempt(attempt, "cancelled")
        transition_job(job, "cancelled")
        attempt.completed_at = now
        job.completed_at = now
        job.active_attempt_id = None
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
        | CancelledRequest,
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
        if attempt.leased_until <= utc_now():
            self._stale_lease()
        if job.state not in {"leased", "running"} and not (
            allow_cancel_requested and job.state == "cancel_requested"
        ):
            self._stale_lease()
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
        spec: JobSpec
        if job.kind == JobKind.SYSTEM_DIAGNOSTIC_V1.value:
            spec = SystemDiagnosticJobSpec()
        else:
            spec = ControlledWaitJobSpec(
                duration_ms=int(job.parameters["duration_ms"]),
            )
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
    if hasattr(result, "duration_ms"):
        return float(result.duration_ms)
    return float(result.elapsed_duration_ms)


def _sanitize_event_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "attempt_number",
        "duration_ms",
        "error_code",
        "kind",
        "lease_id_hint",
        "message_code",
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
