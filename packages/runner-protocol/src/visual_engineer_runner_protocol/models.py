import json
import re
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

RUNNER_PROTOCOL_VERSION: Literal[1] = 1
RUNNER_PROTOCOL_PREFIX = "/api/v1/runner-protocol/v1"
MAX_PROTOCOL_PAYLOAD_BYTES = 64 * 1024

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
VersionText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$",
    ),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class RunnerStatus(StrEnum):
    REGISTERED = "registered"
    ONLINE = "online"
    OFFLINE = "offline"
    REVOKED = "revoked"


class Capability(StrEnum):
    SYSTEM_DIAGNOSTIC_V1 = "system_diagnostic_v1"
    CONTROLLED_WAIT_V1 = "controlled_wait_v1"


class JobKind(StrEnum):
    SYSTEM_DIAGNOSTIC_V1 = "system_diagnostic_v1"
    CONTROLLED_WAIT_V1 = "controlled_wait_v1"


class JobState(StrEnum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AttemptState(StrEnum):
    LEASED = "leased"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"
    LEASE_EXPIRED = "lease_expired"


class EventType(StrEnum):
    RUNNER_REGISTERED = "runner_registered"
    RUNNER_HEARTBEAT = "runner_heartbeat"
    JOB_CREATED = "job_created"
    JOB_CLAIMED = "job_claimed"
    JOB_STARTED = "job_started"
    LEASE_RENEWED = "lease_renewed"
    JOB_PROGRESS = "job_progress"
    CANCEL_REQUESTED = "cancel_requested"
    CANCEL_ACKNOWLEDGED = "cancel_acknowledged"
    JOB_SUCCEEDED = "job_succeeded"
    JOB_FAILED = "job_failed"
    LEASE_EXPIRED = "lease_expired"
    JOB_REQUEUED = "job_requeued"
    POLICY_DENIED = "policy_denied"
    RUNNER_REVOKED = "runner_revoked"


class RepositoryAccess(StrEnum):
    NONE = "none"


class NetworkPolicy(StrEnum):
    CONTROL_PLANE_ONLY = "control_plane_only"


class FailureCode(StrEnum):
    POLICY_DENIED = "policy_denied"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    ENVELOPE_EXPIRED = "envelope_expired"
    ENVELOPE_HASH_MISMATCH = "envelope_hash_mismatch"
    RESULT_REJECTED = "result_rejected"
    RUNNER_INTERNAL_ERROR = "runner_internal_error"
    CONTROL_PLANE_UNAVAILABLE = "control_plane_unavailable"
    LEASE_LOST = "lease_lost"
    RETRY_EXHAUSTED = "retry_exhausted"


class SystemDiagnosticJobSpec(StrictModel):
    kind: Literal[JobKind.SYSTEM_DIAGNOSTIC_V1] = JobKind.SYSTEM_DIAGNOSTIC_V1


class ControlledWaitJobSpec(StrictModel):
    kind: Literal[JobKind.CONTROLLED_WAIT_V1] = JobKind.CONTROLLED_WAIT_V1
    duration_ms: int = Field(ge=100, le=10_000)


JobSpec = Annotated[
    SystemDiagnosticJobSpec | ControlledWaitJobSpec,
    Field(discriminator="kind"),
]


class PermissionEnvelope(StrictModel):
    id: uuid.UUID
    envelope_version: Literal[1] = 1
    job_id: uuid.UUID
    authorization_source: Literal["local_user_job_dispatch"] = "local_user_job_dispatch"
    allowed_capabilities: list[Capability] = Field(min_length=1, max_length=2)
    repository_access: Literal[RepositoryAccess.NONE] = RepositoryAccess.NONE
    shell_access: Literal[False] = False
    network_policy: Literal[NetworkPolicy.CONTROL_PLANE_ONLY] = NetworkPolicy.CONTROL_PLANE_ONLY
    max_runtime_seconds: int = Field(ge=1, le=60)
    lease_seconds: int = Field(ge=2, le=60)
    max_attempts: int = Field(ge=1, le=5)
    max_result_bytes: int = Field(ge=256, le=64 * 1024)
    issued_at: datetime
    expires_at: datetime
    policy_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

    @field_validator("issued_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("permission envelope timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_policy_window(self) -> "PermissionEnvelope":
        if self.expires_at <= self.issued_at:
            raise ValueError("permission envelope expiry must follow issue time")
        if len(set(self.allowed_capabilities)) != len(self.allowed_capabilities):
            raise ValueError("allowed capabilities must be unique")
        return self


class RegisterRequest(StrictModel):
    display_name: DisplayName
    protocol_version: Literal[1] = RUNNER_PROTOCOL_VERSION
    software_version: VersionText
    capabilities: list[Capability] = Field(min_length=1, max_length=2)

    @field_validator("capabilities")
    @classmethod
    def normalize_capabilities(cls, value: list[Capability]) -> list[Capability]:
        unique = sorted(set(value), key=str)
        if len(unique) != len(value):
            raise ValueError("capabilities must be unique")
        return unique


class RegisterResponse(StrictModel):
    runner_id: uuid.UUID
    runner_token: Annotated[str, StringConstraints(min_length=32, max_length=256)] = Field(
        repr=False
    )
    token_type: Literal["Bearer"] = "Bearer"
    protocol_version: Literal[1] = RUNNER_PROTOCOL_VERSION
    registered_at: datetime


class HeartbeatRequest(StrictModel):
    runner_id: uuid.UUID
    protocol_version: Literal[1] = RUNNER_PROTOCOL_VERSION
    software_version: VersionText


class HeartbeatResponse(StrictModel):
    runner_id: uuid.UUID
    status: RunnerStatus
    server_time: datetime


class LeaseIdentity(StrictModel):
    runner_id: uuid.UUID
    attempt_id: uuid.UUID
    lease_id: uuid.UUID


class ClaimRequest(StrictModel):
    runner_id: uuid.UUID
    wait_seconds: int = Field(default=0, ge=0, le=10)


class JobAssignment(StrictModel):
    job_id: uuid.UUID
    attempt_id: uuid.UUID
    lease_id: uuid.UUID
    attempt_number: int = Field(ge=1, le=5)
    job: JobSpec
    permission_envelope: PermissionEnvelope
    leased_until: datetime


class ClaimResponse(StrictModel):
    assignment: JobAssignment | None
    server_time: datetime


class StartRequest(LeaseIdentity):
    pass


class RenewRequest(LeaseIdentity):
    pass


class LeaseMutationResponse(StrictModel):
    job_id: uuid.UUID
    attempt_id: uuid.UUID
    state: JobState
    leased_until: datetime | None
    cancel_requested: bool
    idempotent_replay: bool = False


class ProgressEventRequest(LeaseIdentity):
    event_type: Literal["progress"] = "progress"
    sequence: int = Field(ge=1, le=10_000)
    progress_percent: int = Field(ge=0, le=100)
    message_code: Literal["waiting"] = "waiting"


class DiagnosticResult(StrictModel):
    kind: Literal[JobKind.SYSTEM_DIAGNOSTIC_V1] = JobKind.SYSTEM_DIAGNOSTIC_V1
    runner_software_version: VersionText
    protocol_version: Literal[1] = RUNNER_PROTOCOL_VERSION
    python_version: Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
    os_family: Literal["linux", "darwin", "windows", "other"]
    architecture: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
            max_length=64,
            pattern=r"^[A-Za-z0-9._-]+$",
        ),
    ]
    capability_list: list[Capability] = Field(min_length=1, max_length=2)
    started_at: datetime
    completed_at: datetime
    duration_ms: float = Field(ge=0, le=60_000)

    @model_validator(mode="after")
    def validate_timing(self) -> "DiagnosticResult":
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("result timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("completion must not precede start")
        return self


class ControlledWaitResult(StrictModel):
    kind: Literal[JobKind.CONTROLLED_WAIT_V1] = JobKind.CONTROLLED_WAIT_V1
    requested_duration_ms: int = Field(ge=100, le=10_000)
    elapsed_duration_ms: float = Field(ge=0, le=60_000)
    started_at: datetime
    completed_at: datetime

    @model_validator(mode="after")
    def validate_timing(self) -> "ControlledWaitResult":
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("result timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("completion must not precede start")
        return self


ResultPayload = Annotated[
    DiagnosticResult | ControlledWaitResult,
    Field(discriminator="kind"),
]


class CompleteRequest(LeaseIdentity):
    result: ResultPayload


class FailRequest(LeaseIdentity):
    error_code: FailureCode
    error_message: Annotated[
        str | None, StringConstraints(strip_whitespace=True, max_length=500)
    ] = None


class CancelledRequest(LeaseIdentity):
    pass


_SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|"
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:(?:token|secret|password|authorization)\s*[:=]\s*\S{8,}))"
)
_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:(?:^|[\s\"'])(?:/[A-Za-z0-9_.-]+){2,}(?:/|\b)|"
    r"(?:^|[\s\"'])[A-Za-z]:\\)"
)
_PROHIBITED_RESULT_KEYS = {
    "env",
    "environment",
    "environment_variables",
    "file",
    "files",
    "hostname",
    "host_name",
    "ip",
    "ip_address",
    "package_inventory",
    "packages",
    "path",
    "paths",
    "username",
    "user_name",
}


def validate_safe_error_message(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if _SECRET_PATTERN.search(normalized) or _ABSOLUTE_PATH_PATTERN.search(normalized):
        raise ValueError("error message contains prohibited sensitive data")
    return normalized[:500]


def validate_result_payload(result: BaseModel, *, max_result_bytes: int) -> None:
    payload = result.model_dump(mode="json")
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(serialized.encode("utf-8")) > max_result_bytes:
        raise ValueError("result exceeds permission envelope byte limit")

    def inspect(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key.casefold() in _PROHIBITED_RESULT_KEYS:
                    raise ValueError("result contains a prohibited field")
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
        elif isinstance(value, str):
            if _SECRET_PATTERN.search(value) or _ABSOLUTE_PATH_PATTERN.search(value):
                raise ValueError("result contains prohibited sensitive data")

    inspect(payload)
