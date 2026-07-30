import hashlib
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
MAX_WORKSPACE_TEXT_BYTES = 32 * 1024
MAX_WORKSPACE_DIFF_BYTES = 32 * 1024
MAX_POLICY_PATH_BYTES = 512
MAX_POLICY_PATH_COMPONENTS = 32

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
OpaqueText = Annotated[str, StringConstraints(strip_whitespace=False)]


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
    WORKSPACE_PREPARE_V1 = "workspace_prepare_v1"
    WORKSPACE_LIST_V1 = "workspace_list_v1"
    WORKSPACE_READ_TEXT_V1 = "workspace_read_text_v1"
    WORKSPACE_WRITE_TEXT_V1 = "workspace_write_text_v1"
    WORKSPACE_STATUS_V1 = "workspace_status_v1"
    WORKSPACE_DIFF_V1 = "workspace_diff_v1"
    WORKSPACE_ROLLBACK_V1 = "workspace_rollback_v1"
    WORKSPACE_DISCARD_V1 = "workspace_discard_v1"
    VALIDATION_EXECUTE_V1 = "validation_execute_v1"


class JobKind(StrEnum):
    SYSTEM_DIAGNOSTIC_V1 = "system_diagnostic_v1"
    CONTROLLED_WAIT_V1 = "controlled_wait_v1"
    WORKSPACE_PREPARE_V1 = "workspace_prepare_v1"
    WORKSPACE_LIST_V1 = "workspace_list_v1"
    WORKSPACE_READ_TEXT_V1 = "workspace_read_text_v1"
    WORKSPACE_WRITE_TEXT_V1 = "workspace_write_text_v1"
    WORKSPACE_STATUS_V1 = "workspace_status_v1"
    WORKSPACE_DIFF_V1 = "workspace_diff_v1"
    WORKSPACE_ROLLBACK_V1 = "workspace_rollback_v1"
    WORKSPACE_DISCARD_V1 = "workspace_discard_v1"
    VALIDATION_EXECUTE_V1 = "validation_execute_v1"


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
    SIDE_EFFECT_PERMIT_ACQUIRED = "side_effect_permit_acquired"
    SIDE_EFFECT_PERMIT_COMPLETED = "side_effect_permit_completed"
    SIDE_EFFECT_PERMIT_DENIED = "side_effect_permit_denied"


class RepositoryAccess(StrEnum):
    NONE = "none"
    ISOLATED_WORKSPACE = "isolated_workspace"


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
    REPOSITORY_UNAVAILABLE = "repository_unavailable"
    SOURCE_NOT_READ_ONLY = "source_not_read_only"
    SOURCE_REVISION_MISMATCH = "source_revision_mismatch"
    WORKSPACE_NOT_FOUND = "workspace_not_found"
    WORKSPACE_IDENTITY_MISMATCH = "workspace_identity_mismatch"
    WORKSPACE_STATE_INVALID = "workspace_state_invalid"
    PATH_INVALID = "path_invalid"
    PATH_DENIED = "path_denied"
    SENSITIVE_PATH_DENIED = "sensitive_path_denied"
    SYMLINK_DENIED = "symlink_denied"
    HARDLINK_DENIED = "hardlink_denied"
    NOT_REGULAR_FILE = "not_regular_file"
    BINARY_DENIED = "binary_denied"
    INVALID_UTF8 = "invalid_utf8"
    FILE_TOO_LARGE = "file_too_large"
    FILE_COUNT_BUDGET_EXCEEDED = "file_count_budget_exceeded"
    TOTAL_WRITE_BUDGET_EXCEEDED = "total_write_budget_exceeded"
    DIFF_BUDGET_EXCEEDED = "diff_budget_exceeded"
    CONTENT_CONFLICT = "content_conflict"
    EXPECTED_ABSENT_CONFLICT = "expected_absent_conflict"
    ATOMIC_WRITE_FAILED = "atomic_write_failed"
    WORKSPACE_CANCELLED = "workspace_cancelled"
    SIDE_EFFECT_PERMIT_REQUIRED = "side_effect_permit_required"
    SIDE_EFFECT_PERMIT_INVALID = "side_effect_permit_invalid"
    SIDE_EFFECT_PERMIT_EXPIRED = "side_effect_permit_expired"
    WORKSPACE_RECOVERY_REQUIRED = "workspace_recovery_required"
    WORKSPACE_QUARANTINED = "workspace_quarantined"
    GIT_OUTPUT_LIMIT_EXCEEDED = "git_output_limit_exceeded"
    MIRROR_BUDGET_EXCEEDED = "mirror_budget_exceeded"
    VALIDATION_PROFILE_DENIED = "validation_profile_denied"
    VALIDATION_CHECKPOINT_MISMATCH = "validation_checkpoint_mismatch"
    VALIDATION_SANDBOX_UNAVAILABLE = "validation_sandbox_unavailable"
    VALIDATION_SANDBOX_DENIED = "validation_sandbox_denied"
    VALIDATION_COMMAND_FAILED = "validation_command_failed"
    VALIDATION_TIMED_OUT = "validation_timed_out"
    VALIDATION_OUTPUT_LIMIT_EXCEEDED = "validation_output_limit_exceeded"
    VALIDATION_ARTIFACT_LIMIT_EXCEEDED = "validation_artifact_limit_exceeded"
    VALIDATION_CLEANUP_FAILED = "validation_cleanup_failed"
    VALIDATION_PROCESS_REMAINED = "validation_process_remained"


class WorkspaceOperation(StrEnum):
    PREPARE = "prepare"
    LIST = "list"
    READ_TEXT = "read_text"
    WRITE_TEXT = "write_text"
    STATUS = "status"
    DIFF = "diff"
    ROLLBACK = "rollback"
    DISCARD = "discard"
    VALIDATE = "validate"


class WorkspaceWriteMode(StrEnum):
    CREATE = "create"
    REPLACE = "replace"


class WorkspaceEntryType(StrEnum):
    DIRECTORY = "directory"
    TEXT = "text"
    BINARY = "binary"
    SYMLINK = "symlink"
    GITLINK = "gitlink"
    SPECIAL = "special"


class WorkspaceStatusCode(StrEnum):
    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"
    UNTRACKED = "untracked"
    TYPE_CHANGED = "type_changed"
    IGNORED = "ignored"


class SourceStatus(StrEnum):
    UNKNOWN = "unknown"


class SideEffectPermitState(StrEnum):
    CONSUMED = "consumed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SystemDiagnosticJobSpec(StrictModel):
    kind: Literal[JobKind.SYSTEM_DIAGNOSTIC_V1] = JobKind.SYSTEM_DIAGNOSTIC_V1


class ControlledWaitJobSpec(StrictModel):
    kind: Literal[JobKind.CONTROLLED_WAIT_V1] = JobKind.CONTROLLED_WAIT_V1
    duration_ms: int = Field(ge=100, le=10_000)


def _validate_relative_policy_value(value: str, *, allow_glob: bool) -> str:
    if not value or "\x00" in value or value.startswith("/") or "\\" in value:
        raise ValueError("policy paths must be relative POSIX paths")
    if len(value.encode("utf-8")) > MAX_POLICY_PATH_BYTES:
        raise ValueError("policy path exceeds its byte limit")
    components = value.split("/")
    if len(components) > MAX_POLICY_PATH_COMPONENTS or any(
        not component
        or component in {".", ".."}
        or any(ord(character) < 32 or ord(character) == 127 for character in component)
        for component in components
    ):
        raise ValueError("policy path contains an invalid component")
    if not allow_glob and any(character in value for character in "*?["):
        raise ValueError("relative paths cannot contain glob syntax")
    if allow_glob:
        for component in components:
            if any(character in component for character in "?["):
                raise ValueError("only literal, star, and double-star components are supported")
            if "**" in component and component != "**":
                raise ValueError("double-star must occupy a complete path component")
    return value


class ExecutionGrantPolicy(StrictModel):
    id: uuid.UUID
    grant_version: Literal[1] = 1
    task_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    plan_id: uuid.UUID
    repository_handle_id: uuid.UUID
    repository_opaque_handle: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=8,
            max_length=120,
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        ),
    ]
    source_revision: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]
    snapshot_fingerprint: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    allowed_operations: list[WorkspaceOperation] = Field(min_length=1, max_length=9)
    allowed_paths: list[str] = Field(min_length=1, max_length=20)
    denied_paths: list[str] = Field(min_length=1, max_length=50)
    max_files_changed: int = Field(ge=1, le=100)
    max_total_write_bytes: int = Field(ge=1, le=1024 * 1024)
    max_single_file_bytes: int = Field(ge=1, le=MAX_WORKSPACE_TEXT_BYTES)
    max_diff_bytes: int = Field(ge=1, le=MAX_WORKSPACE_DIFF_BYTES)
    workspace_ttl_seconds: int = Field(ge=60, le=24 * 60 * 60)
    network_policy: Literal["none"] = "none"
    shell_access: Literal[False] = False
    git_delivery_access: Literal[False] = False
    source_repository_write_access: Literal[False] = False
    validation_workspace_id: uuid.UUID | None = None
    validation_checkpoint_id: uuid.UUID | None = None
    allowed_validation_profiles: list[
        Annotated[
            str,
            StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{2,63}:v[1-9][0-9]{0,2}$"),
        ]
    ] = Field(default_factory=list, max_length=4)
    allowed_validation_suites: list[
        Annotated[
            str,
            StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{2,63}:v[1-9][0-9]{0,2}$"),
        ]
    ] = Field(default_factory=list, max_length=1)
    validation_suite_definition_digest: (
        Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None
    ) = None
    validation_suite_root_run_id: uuid.UUID | None = None
    validation_suite_retry_of_run_id: uuid.UUID | None = None
    validation_suite_attempt_number: int = Field(default=0, ge=0, le=5)
    validation_suite_allowed_run_count: int = Field(default=0, ge=0, le=1)
    max_validation_runs: int = Field(default=0, ge=0, le=10)
    validation_timeout_seconds: int = Field(default=0, ge=0, le=120)
    validation_cpu_seconds: int = Field(default=0, ge=0, le=120)
    validation_memory_bytes: int = Field(default=0, ge=0, le=1024 * 1024 * 1024)
    validation_pid_limit: int = Field(default=0, ge=0, le=64)
    validation_fd_limit: int = Field(default=0, ge=0, le=256)
    validation_output_bytes: int = Field(default=0, ge=0, le=64 * 1024)
    validation_artifact_bytes: int = Field(default=0, ge=0, le=1024 * 1024)
    validation_artifact_count: int = Field(default=0, ge=0, le=20)
    expires_at: datetime
    policy_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

    @field_validator("expires_at")
    @classmethod
    def require_expiry_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("execution grant expiry must be timezone-aware")
        return value

    @field_validator("allowed_operations")
    @classmethod
    def require_unique_operations(cls, value: list[WorkspaceOperation]) -> list[WorkspaceOperation]:
        if len(set(value)) != len(value):
            raise ValueError("allowed operations must be unique")
        return sorted(value, key=str)

    @field_validator("allowed_paths", "denied_paths")
    @classmethod
    def validate_policy_paths(cls, value: list[str]) -> list[str]:
        normalized = [
            _validate_relative_policy_value(item.strip(), allow_glob=True) for item in value
        ]
        if len(set(normalized)) != len(normalized):
            raise ValueError("policy paths must be unique")
        return sorted(normalized)

    @model_validator(mode="after")
    def validate_budgets_and_scope(self) -> "ExecutionGrantPolicy":
        if self.max_single_file_bytes > self.max_total_write_bytes:
            raise ValueError("single-file budget cannot exceed total-write budget")
        if self.allowed_paths == ["**"] or "**" in self.allowed_paths:
            raise ValueError("an unbounded repository-wide path is prohibited")
        validation_values = (
            self.validation_workspace_id,
            self.validation_checkpoint_id,
            self.allowed_validation_profiles,
            self.max_validation_runs,
            self.validation_timeout_seconds,
            self.validation_cpu_seconds,
            self.validation_memory_bytes,
            self.validation_pid_limit,
            self.validation_fd_limit,
            self.validation_output_bytes,
        )
        validation_enabled = any(
            (
                *validation_values,
                self.validation_artifact_bytes,
                self.validation_artifact_count,
            )
        )
        if validation_enabled:
            if (
                self.validation_workspace_id is None
                or self.validation_checkpoint_id is None
                or not self.allowed_validation_profiles
                or any(not value for value in validation_values[3:])
            ):
                raise ValueError(
                    "validation authority requires exact bindings and positive budgets"
                )
            if self.allowed_operations != [WorkspaceOperation.VALIDATE]:
                raise ValueError(
                    "validation authority cannot include Workspace mutation operations"
                )
        suite_enabled = bool(self.allowed_validation_suites)
        suite_binding_values = (
            self.validation_suite_definition_digest,
            self.validation_suite_root_run_id,
            self.validation_suite_retry_of_run_id,
            self.validation_suite_attempt_number,
            self.validation_suite_allowed_run_count,
        )
        if suite_enabled:
            if (
                len(self.allowed_validation_suites) != 1
                or self.validation_suite_definition_digest is None
                or self.validation_suite_attempt_number < 1
                or self.validation_suite_allowed_run_count != 1
            ):
                raise ValueError("Suite authority requires one exact definition and run budget")
            if self.validation_suite_attempt_number == 1:
                if (
                    self.validation_suite_root_run_id is not None
                    or self.validation_suite_retry_of_run_id is not None
                ):
                    raise ValueError("root Suite authority cannot carry retry lineage")
            elif (
                self.validation_suite_root_run_id is None
                or self.validation_suite_retry_of_run_id is None
            ):
                raise ValueError("retry Suite authority requires root and source lineage")
        elif any(suite_binding_values):
            raise ValueError("non-Suite authority cannot carry Suite lineage")
        return self


class WorkspaceBoundJobSpec(StrictModel):
    kind: JobKind
    workspace_id: uuid.UUID
    execution_grant: ExecutionGrantPolicy


class WorkspacePrepareJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.WORKSPACE_PREPARE_V1] = JobKind.WORKSPACE_PREPARE_V1


class WorkspaceListJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.WORKSPACE_LIST_V1] = JobKind.WORKSPACE_LIST_V1
    relative_directory: str
    depth: int = Field(ge=1, le=4)
    max_entries: int = Field(ge=1, le=500)

    @field_validator("relative_directory")
    @classmethod
    def validate_relative_directory(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)


class WorkspaceReadTextJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.WORKSPACE_READ_TEXT_V1] = JobKind.WORKSPACE_READ_TEXT_V1
    relative_path: str
    max_bytes: int = Field(ge=1, le=MAX_WORKSPACE_TEXT_BYTES)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)


class WorkspaceWriteTextJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.WORKSPACE_WRITE_TEXT_V1] = JobKind.WORKSPACE_WRITE_TEXT_V1
    mode: WorkspaceWriteMode
    relative_path: str
    content: OpaqueText
    expected_absent: Literal[True] | None = None
    expected_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None = None

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)

    @model_validator(mode="after")
    def validate_write_precondition(self) -> "WorkspaceWriteTextJobSpec":
        content_bytes = len(self.content.encode("utf-8"))
        if content_bytes > MAX_WORKSPACE_TEXT_BYTES:
            raise ValueError("write content exceeds protocol text limit")
        if content_bytes > self.execution_grant.max_single_file_bytes:
            raise ValueError("write content exceeds execution grant single-file budget")
        if self.mode == WorkspaceWriteMode.CREATE:
            if self.expected_absent is not True or self.expected_sha256 is not None:
                raise ValueError("create requires expected_absent=true only")
        elif self.expected_sha256 is None or self.expected_absent is not None:
            raise ValueError("replace requires expected_sha256 only")
        return self


class WorkspaceStatusJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.WORKSPACE_STATUS_V1] = JobKind.WORKSPACE_STATUS_V1


class WorkspaceDiffJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.WORKSPACE_DIFF_V1] = JobKind.WORKSPACE_DIFF_V1


class WorkspaceRollbackJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.WORKSPACE_ROLLBACK_V1] = JobKind.WORKSPACE_ROLLBACK_V1
    target: Literal["initial"] = "initial"


class WorkspaceDiscardJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.WORKSPACE_DISCARD_V1] = JobKind.WORKSPACE_DISCARD_V1


class ValidationExecuteJobSpec(WorkspaceBoundJobSpec):
    kind: Literal[JobKind.VALIDATION_EXECUTE_V1] = JobKind.VALIDATION_EXECUTE_V1
    validation_run_id: uuid.UUID
    validation_step_id: Literal["fixture-contract", "fixture-manifest"] = "fixture-contract"
    validation_policy_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] = (
        "0" * 64
    )
    result_schema_version: Literal[1] = 1
    profile_id: Literal[
        "fixture-python-stdlib-v1",
        "fixture-python-manifest-v1",
    ] = "fixture-python-stdlib-v1"
    profile_version: Literal[1] = 1
    checkpoint_id: uuid.UUID
    checkpoint_fingerprint: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    timeout_seconds: int = Field(ge=1, le=120)
    max_output_bytes: int = Field(ge=256, le=64 * 1024)
    max_artifact_bytes: int = Field(ge=0, le=1024 * 1024)
    max_artifact_count: int = Field(ge=0, le=20)

    @model_validator(mode="after")
    def validate_profile_authority(self) -> "ValidationExecuteJobSpec":
        grant = self.execution_grant
        profile_ref = f"{self.profile_id}:v{self.profile_version}"
        if (
            WorkspaceOperation.VALIDATE not in grant.allowed_operations
            or grant.validation_workspace_id != self.workspace_id
            or grant.validation_checkpoint_id != self.checkpoint_id
            or profile_ref not in grant.allowed_validation_profiles
            or self.timeout_seconds > grant.validation_timeout_seconds
            or self.max_output_bytes > grant.validation_output_bytes
            or self.max_artifact_bytes > grant.validation_artifact_bytes
            or self.max_artifact_count > grant.validation_artifact_count
        ):
            raise ValueError("validation Job exceeds its exact Execution Grant")
        return self


WorkspaceJobSpec = (
    WorkspacePrepareJobSpec
    | WorkspaceListJobSpec
    | WorkspaceReadTextJobSpec
    | WorkspaceWriteTextJobSpec
    | WorkspaceStatusJobSpec
    | WorkspaceDiffJobSpec
    | WorkspaceRollbackJobSpec
    | WorkspaceDiscardJobSpec
    | ValidationExecuteJobSpec
)


def side_effect_job_binding(spec: WorkspaceJobSpec) -> dict[str, str | None]:
    relative_path: str | None
    expected_current: str | None
    if isinstance(spec, WorkspacePrepareJobSpec):
        operation = WorkspaceOperation.PREPARE
        relative_path = None
        expected_current = "workspace_absent"
        proposed_digest = hashlib.sha256(
            f"prepare:{spec.execution_grant.source_revision}".encode("ascii")
        ).hexdigest()
    elif isinstance(spec, WorkspaceWriteTextJobSpec):
        operation = WorkspaceOperation.WRITE_TEXT
        relative_path = spec.relative_path
        expected_current = (
            "absent" if spec.mode == WorkspaceWriteMode.CREATE else spec.expected_sha256
        )
        proposed_digest = hashlib.sha256(spec.content.encode("utf-8")).hexdigest()
    elif isinstance(spec, WorkspaceRollbackJobSpec):
        operation = WorkspaceOperation.ROLLBACK
        relative_path = None
        expected_current = None
        proposed_digest = hashlib.sha256(b"rollback:initial").hexdigest()
    elif isinstance(spec, WorkspaceDiscardJobSpec):
        operation = WorkspaceOperation.DISCARD
        relative_path = None
        expected_current = None
        proposed_digest = hashlib.sha256(b"discard:workspace").hexdigest()
    elif isinstance(spec, ValidationExecuteJobSpec):
        operation = WorkspaceOperation.VALIDATE
        relative_path = None
        expected_current = spec.checkpoint_fingerprint
        proposed_digest = hashlib.sha256(
            (
                f"{spec.profile_id}:v{spec.profile_version}:"
                f"{spec.checkpoint_id}:{spec.checkpoint_fingerprint}"
            ).encode("ascii")
        ).hexdigest()
    else:
        raise ValueError("Job does not require a side-effect permit")
    return {
        "operation": operation.value,
        "relative_path": relative_path,
        "expected_current": expected_current,
        "proposed_digest": proposed_digest,
    }


JobSpec = Annotated[
    SystemDiagnosticJobSpec | ControlledWaitJobSpec | WorkspaceJobSpec,
    Field(discriminator="kind"),
]


class PermissionEnvelope(StrictModel):
    id: uuid.UUID
    envelope_version: Literal[1] = 1
    job_id: uuid.UUID
    authorization_source: Literal["local_user_job_dispatch", "execution_grant"] = (
        "local_user_job_dispatch"
    )
    allowed_capabilities: list[Capability] = Field(min_length=1, max_length=12)
    repository_access: RepositoryAccess = RepositoryAccess.NONE
    shell_access: Literal[False] = False
    network_policy: Literal[NetworkPolicy.CONTROL_PLANE_ONLY] = NetworkPolicy.CONTROL_PLANE_ONLY
    max_runtime_seconds: int = Field(ge=1, le=120)
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
    capabilities: list[Capability] = Field(min_length=1, max_length=12)

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
    capabilities: list[Capability] | None = None

    @field_validator("capabilities")
    @classmethod
    def normalize_capabilities(cls, value: list[Capability] | None) -> list[Capability] | None:
        if value is None:
            return None
        if not 1 <= len(value) <= 12:
            raise ValueError("capabilities must contain between 1 and 12 items")
        unique = sorted(set(value), key=str)
        if len(unique) != len(value):
            raise ValueError("capabilities must be unique")
        return unique


class HeartbeatResponse(StrictModel):
    runner_id: uuid.UUID
    status: RunnerStatus
    server_time: datetime


class RepositoryRegistrationRequest(StrictModel):
    runner_id: uuid.UUID
    opaque_handle: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=8,
            max_length=120,
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        ),
    ]
    display_name: DisplayName
    vcs_kind: Literal["git"] = "git"
    capabilities: list[Literal["committed_head_read", "isolated_workspace"]] = Field(
        min_length=2, max_length=2
    )
    current_revision: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]
    current_branch: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
        | None
    ) = None
    source_status: Literal[SourceStatus.UNKNOWN] = SourceStatus.UNKNOWN
    source_is_dirty: bool
    dirty_path_count: int = Field(ge=0, le=10_000)
    metadata_version: Literal[1] = 1

    @field_validator("capabilities")
    @classmethod
    def require_repository_capabilities(
        cls, value: list[str]
    ) -> list[Literal["committed_head_read", "isolated_workspace"]]:
        expected = {"committed_head_read", "isolated_workspace"}
        if set(value) != expected or len(value) != len(expected):
            raise ValueError("repository capabilities must match the Phase 4 closed set")
        return ["committed_head_read", "isolated_workspace"]


class RepositoryRegistrationResponse(StrictModel):
    repository_handle_id: uuid.UUID
    opaque_handle: str
    status: Literal["available"]
    current_revision: str
    last_verified_at: datetime


class LeaseIdentity(StrictModel):
    runner_id: uuid.UUID
    attempt_id: uuid.UUID
    lease_id: uuid.UUID


class SideEffectPermitAcquireRequest(LeaseIdentity):
    job_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class SideEffectPermit(StrictModel):
    id: uuid.UUID
    sequence: int = Field(ge=1)
    runner_id: uuid.UUID
    job_id: uuid.UUID
    attempt_id: uuid.UUID
    lease_id: uuid.UUID
    grant_id: uuid.UUID
    workspace_id: uuid.UUID
    repository_handle_id: uuid.UUID
    operation: WorkspaceOperation
    relative_path: str | None = None
    expected_current: Annotated[
        str,
        StringConstraints(
            strip_whitespace=False,
            min_length=6,
            max_length=64,
            pattern=r"^(?:absent|workspace_absent|[0-9a-f]{64})$",
        ),
    ]
    proposed_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    job_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    operation_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    policy_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    source_revision: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]
    issued_at: datetime
    consumed_at: datetime
    expires_at: datetime
    state: Literal[SideEffectPermitState.CONSUMED] = SideEffectPermitState.CONSUMED
    idempotent_replay: bool = False

    @field_validator("relative_path")
    @classmethod
    def validate_optional_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_relative_policy_value(value, allow_glob=False)

    @field_validator("issued_at", "consumed_at", "expires_at")
    @classmethod
    def require_permit_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("side-effect permit timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_permit_window(self) -> "SideEffectPermit":
        if not self.issued_at <= self.consumed_at < self.expires_at:
            raise ValueError("side-effect permit timestamps are inconsistent")
        if self.operation == WorkspaceOperation.WRITE_TEXT:
            if self.relative_path is None:
                raise ValueError("write permit requires a relative path")
        elif self.relative_path is not None:
            raise ValueError("Workspace-scoped permit cannot carry a relative path")
        return self


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
    message_code: Literal["waiting", "validating"] = "waiting"


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
    capability_list: list[Capability] = Field(min_length=1, max_length=12)
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


class WorkspaceCheckpointPayload(StrictModel):
    source_revision: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]
    tree_fingerprint: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    diff_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    changed_paths: list[str] = Field(max_length=100)
    changed_file_count: int = Field(ge=0, le=100)
    total_diff_bytes: int = Field(ge=0, le=MAX_WORKSPACE_DIFF_BYTES)
    diff: OpaqueText
    side_effect_permit_id: uuid.UUID | None = None

    @field_validator("changed_paths")
    @classmethod
    def validate_changed_paths(cls, value: list[str]) -> list[str]:
        normalized = [_validate_relative_policy_value(item, allow_glob=False) for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("changed paths must be unique")
        return sorted(normalized)

    @model_validator(mode="after")
    def validate_checkpoint(self) -> "WorkspaceCheckpointPayload":
        if self.changed_file_count != len(self.changed_paths):
            raise ValueError("changed-file count must match changed paths")
        if len(self.diff.encode("utf-8")) != self.total_diff_bytes:
            raise ValueError("diff byte count must match its content")
        return self


class WorkspacePrepareResult(StrictModel):
    kind: Literal[JobKind.WORKSPACE_PREPARE_V1] = JobKind.WORKSPACE_PREPARE_V1
    workspace_id: uuid.UUID
    repository_handle_id: uuid.UUID
    source_revision: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]
    workspace_fingerprint: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    initial_tree_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    current_tree_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    side_effect_permit_id: uuid.UUID


class WorkspaceEntry(StrictModel):
    relative_path: str
    entry_type: WorkspaceEntryType
    size: int = Field(ge=0, le=1024 * 1024 * 1024)
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None = None

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)


class WorkspaceListResult(StrictModel):
    kind: Literal[JobKind.WORKSPACE_LIST_V1] = JobKind.WORKSPACE_LIST_V1
    workspace_id: uuid.UUID
    relative_directory: str
    entries: list[WorkspaceEntry] = Field(max_length=500)
    truncated: bool

    @field_validator("relative_directory")
    @classmethod
    def validate_relative_directory(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)


class WorkspaceReadTextResult(StrictModel):
    kind: Literal[JobKind.WORKSPACE_READ_TEXT_V1] = JobKind.WORKSPACE_READ_TEXT_V1
    workspace_id: uuid.UUID
    relative_path: str
    content: OpaqueText
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    size: int = Field(ge=0, le=MAX_WORKSPACE_TEXT_BYTES)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)

    @model_validator(mode="after")
    def validate_content_size(self) -> "WorkspaceReadTextResult":
        if len(self.content.encode("utf-8")) != self.size:
            raise ValueError("read byte count must match content")
        return self


class WorkspaceWriteTextResult(StrictModel):
    kind: Literal[JobKind.WORKSPACE_WRITE_TEXT_V1] = JobKind.WORKSPACE_WRITE_TEXT_V1
    workspace_id: uuid.UUID
    relative_path: str
    operation: WorkspaceWriteMode
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    size: int = Field(ge=0, le=MAX_WORKSPACE_TEXT_BYTES)
    current_tree_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    changed_file_count: int = Field(ge=0, le=100)
    total_written_bytes: int = Field(ge=0, le=1024 * 1024)
    checkpoint: WorkspaceCheckpointPayload
    side_effect_permit_id: uuid.UUID

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)

    @model_validator(mode="after")
    def validate_permit_checkpoint_binding(self) -> "WorkspaceWriteTextResult":
        if self.checkpoint.side_effect_permit_id != self.side_effect_permit_id:
            raise ValueError("write result and checkpoint permit IDs must match")
        return self


class WorkspaceStatusEntry(StrictModel):
    relative_path: str
    status: WorkspaceStatusCode

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)


class WorkspaceStatusResult(StrictModel):
    kind: Literal[JobKind.WORKSPACE_STATUS_V1] = JobKind.WORKSPACE_STATUS_V1
    workspace_id: uuid.UUID
    entries: list[WorkspaceStatusEntry] = Field(max_length=100)
    changed_file_count: int = Field(ge=0, le=100)
    current_tree_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

    @model_validator(mode="after")
    def validate_changed_count(self) -> "WorkspaceStatusResult":
        if self.changed_file_count != len(self.entries):
            raise ValueError("changed-file count must match status entries")
        return self


class WorkspaceDiffResult(StrictModel):
    kind: Literal[JobKind.WORKSPACE_DIFF_V1] = JobKind.WORKSPACE_DIFF_V1
    workspace_id: uuid.UUID
    diff: OpaqueText
    diff_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    changed_paths: list[str] = Field(max_length=100)
    total_diff_bytes: int = Field(ge=0, le=MAX_WORKSPACE_DIFF_BYTES)
    current_tree_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    checkpoint: WorkspaceCheckpointPayload

    @field_validator("changed_paths")
    @classmethod
    def validate_changed_paths(cls, value: list[str]) -> list[str]:
        normalized = [_validate_relative_policy_value(item, allow_glob=False) for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("changed paths must be unique")
        return sorted(normalized)

    @model_validator(mode="after")
    def validate_diff_size(self) -> "WorkspaceDiffResult":
        if len(self.diff.encode("utf-8")) != self.total_diff_bytes:
            raise ValueError("diff byte count must match content")
        if self.changed_paths != self.checkpoint.changed_paths:
            raise ValueError("diff and checkpoint paths must match")
        return self


class WorkspaceRollbackResult(StrictModel):
    kind: Literal[JobKind.WORKSPACE_ROLLBACK_V1] = JobKind.WORKSPACE_ROLLBACK_V1
    workspace_id: uuid.UUID
    clean: Literal[True] = True
    current_tree_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    removed_created_paths: list[str] = Field(max_length=100)
    side_effect_permit_id: uuid.UUID

    @field_validator("removed_created_paths")
    @classmethod
    def validate_removed_paths(cls, value: list[str]) -> list[str]:
        normalized = [_validate_relative_policy_value(item, allow_glob=False) for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("removed paths must be unique")
        return sorted(normalized)


class WorkspaceDiscardResult(StrictModel):
    kind: Literal[JobKind.WORKSPACE_DISCARD_V1] = JobKind.WORKSPACE_DISCARD_V1
    workspace_id: uuid.UUID
    discarded: Literal[True] = True
    idempotent: bool
    side_effect_permit_id: uuid.UUID


class ValidationArtifactEvidence(StrictModel):
    relative_path: Annotated[
        str,
        StringConstraints(strip_whitespace=False, min_length=1, max_length=512),
    ]
    file_type: Literal["regular_file"] = "regular_file"
    size_bytes: int = Field(ge=0, le=1024 * 1024)
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_policy_value(value, allow_glob=False)


class ValidationExecutionResult(StrictModel):
    kind: Literal[JobKind.VALIDATION_EXECUTE_V1] = JobKind.VALIDATION_EXECUTE_V1
    result_schema_version: int | None = Field(default=None, ge=1, le=100)
    validation_run_id: uuid.UUID
    validation_step_id: str | None = Field(default=None, min_length=1, max_length=64)
    workspace_id: uuid.UUID
    source_revision: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")] | None = None
    checkpoint_id: uuid.UUID
    checkpoint_fingerprint: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    profile_id: Annotated[
        str,
        StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$"),
    ] = "fixture-python-stdlib-v1"
    profile_version: int = Field(default=1, ge=1, le=999)
    policy_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None = None
    fixed_operation: WorkspaceOperation | None = None
    fixed_argv: list[
        Literal[
            "python",
            "-I",
            "-S",
            "<system-owned-fixture-validator>",
            "<system-owned-profile-mode>",
        ]
    ] = Field(min_length=4, max_length=5)
    fixed_argv_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None = None
    fixed_cwd: (
        Annotated[str, StringConstraints(strip_whitespace=False, min_length=1, max_length=128)]
        | None
    ) = None
    fixed_environment_digest: (
        Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None
    ) = None
    started_at: datetime
    completed_at: datetime
    duration_ms: float = Field(ge=0, le=120_000)
    exit_code: int = Field(ge=0, le=255)
    stdout: Annotated[str, StringConstraints(strip_whitespace=False, max_length=32 * 1024)]
    stderr: Annotated[str, StringConstraints(strip_whitespace=False, max_length=32 * 1024)]
    stdout_truncated: bool
    stderr_truncated: bool
    redaction_count: int = Field(ge=0, le=10_000)
    timed_out: bool
    cancelled: bool
    network_isolated: Literal[True] = True
    filesystem_isolated: Literal[True] = True
    sandbox_cleaned: Literal[True] = True
    artifact_count: int = Field(ge=0, le=20)
    artifact_bytes: int = Field(ge=0, le=1024 * 1024)
    artifacts: list[ValidationArtifactEvidence] | None = Field(
        default=None,
        max_length=20,
    )
    artifact_manifest_digest: (
        Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None
    ) = None
    side_effect_permit_id: uuid.UUID
    side_effect_permit_sequence: int | None = Field(default=None, ge=1)
    side_effect_permit_digest: (
        Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None
    ) = None
    fencing_token: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None = None
    execution_envelope_digest: (
        Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None
    ) = None
    evidence_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None = None

    @model_validator(mode="after")
    def validate_timing_and_outcome(self) -> "ValidationExecutionResult":
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("validation timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("validation completion must not precede start")
        if self.timed_out and self.cancelled:
            raise ValueError("validation cannot be both timed out and cancelled")
        if (self.timed_out or self.cancelled) and self.exit_code == 0:
            raise ValueError("interrupted validation must not report a zero exit")
        return self


ResultPayload = Annotated[
    DiagnosticResult
    | ControlledWaitResult
    | WorkspacePrepareResult
    | WorkspaceListResult
    | WorkspaceReadTextResult
    | WorkspaceWriteTextResult
    | WorkspaceStatusResult
    | WorkspaceDiffResult
    | WorkspaceRollbackResult
    | WorkspaceDiscardResult
    | ValidationExecutionResult,
    Field(discriminator="kind"),
]


class CompleteRequest(LeaseIdentity):
    result: ResultPayload


class FailRequest(LeaseIdentity):
    error_code: FailureCode
    side_effect_permit_id: uuid.UUID | None = None
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
