import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from visual_engineer_api.schemas.runner import RunnerJobResponse
from visual_engineer_runner_protocol import (
    MAX_WORKSPACE_TEXT_BYTES,
    SourceStatus,
    WorkspaceOperation,
    WorkspaceWriteMode,
)


def _validate_relative_path(value: str) -> str:
    if (
        not value
        or "\x00" in value
        or value.startswith("/")
        or "\\" in value
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError("a bounded relative POSIX path is required")
    components = value.split("/")
    if len(components) > 32 or any(
        not component
        or component in {".", ".."}
        or any(ord(character) < 32 or ord(character) == 127 for character in component)
        or any(character in component for character in "*?[")
        for component in components
    ):
        raise ValueError("relative path contains an invalid component")
    return value


class RepositoryHandleStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    REVOKED = "revoked"


class RepositoryHandleResponse(BaseModel):
    id: uuid.UUID
    runner_id: uuid.UUID
    runner_display_name: str
    opaque_handle: str
    display_name: str
    vcs_kind: Literal["git"]
    status: RepositoryHandleStatus
    capabilities: list[Literal["committed_head_read", "isolated_workspace"]]
    current_revision: str | None
    current_branch: str | None
    source_status: SourceStatus
    source_is_dirty: bool
    dirty_path_count: int
    last_verified_at: datetime | None
    metadata_version: Literal[1]
    created_at: datetime
    updated_at: datetime


class RepositoryHandleListResponse(BaseModel):
    items: list[RepositoryHandleResponse]
    total: int


class ExecutionGrantStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKE_REQUESTED = "revoke_requested"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ExecutionGrantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: uuid.UUID
    repository_handle_id: uuid.UUID
    validation_checkpoint_id: uuid.UUID | None = None
    validation_profile_id: Literal["fixture-python-stdlib-v1"] | None = None
    validation_suite_id: Literal["fixture-integrity-suite-v1"] | None = None
    validation_suite_version: Literal[1] | None = None

    @model_validator(mode="after")
    def validate_optional_validation_scope(self) -> "ExecutionGrantCreate":
        profile_selected = self.validation_profile_id is not None
        suite_selected = self.validation_suite_id is not None
        if profile_selected and suite_selected:
            raise ValueError("choose one fixed Validation Profile or Suite")
        if self.validation_suite_version is not None and not suite_selected:
            raise ValueError("Suite version requires a fixed Validation Suite")
        if suite_selected and self.validation_suite_version is None:
            raise ValueError("Validation Suite ID and version must be supplied together")
        validation_selected = profile_selected or suite_selected
        if (self.validation_checkpoint_id is not None) != validation_selected:
            raise ValueError(
                "validation checkpoint and fixed Profile or Suite must be supplied together"
            )
        return self


class ExecutionGrantDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "ExecutionGrantDecisionCreate":
        if self.decision == "reject" and not self.reason:
            raise ValueError("a non-blank rejection reason is required")
        if self.reason is not None and "\x00" in self.reason:
            raise ValueError("NUL characters are not allowed")
        return self


class ExecutionGrantDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    grant_id: uuid.UUID
    decision: Literal["approve", "reject"]
    reason: str | None
    actor_type: Literal["local_user"]
    request_id: str
    created_at: datetime


class ExecutionGrantResponse(BaseModel):
    id: uuid.UUID
    grant_version: Literal[1]
    task_id: uuid.UUID | None
    run_id: uuid.UUID | None
    plan_id: uuid.UUID
    repository_handle_id: uuid.UUID
    repository_display_name: str
    runner_id: uuid.UUID
    source_revision: str
    snapshot_fingerprint: str
    allowed_operations: list[WorkspaceOperation]
    allowed_paths: list[str]
    denied_paths: list[str]
    max_files_changed: int
    max_total_write_bytes: int
    max_single_file_bytes: int
    max_diff_bytes: int
    workspace_ttl_seconds: int
    network_policy: Literal["none"]
    shell_access: Literal[False]
    git_delivery_access: Literal[False]
    source_repository_write_access: Literal[False]
    validation_workspace_id: uuid.UUID | None
    validation_checkpoint_id: uuid.UUID | None
    allowed_validation_profiles: list[str]
    allowed_validation_suites: list[str]
    max_validation_runs: int
    validation_timeout_seconds: int
    validation_cpu_seconds: int
    validation_memory_bytes: int
    validation_pid_limit: int
    validation_fd_limit: int
    validation_output_bytes: int
    validation_artifact_bytes: int
    validation_artifact_count: int
    status: ExecutionGrantStatus
    policy_hash: str
    requested_at: datetime
    decided_at: datetime | None
    revocation_requested_at: datetime | None
    revoked_at: datetime | None
    in_flight_permit_count: int
    expires_at: datetime
    created_at: datetime
    decision: ExecutionGrantDecisionResponse | None = None


class ExecutionGrantListResponse(BaseModel):
    items: list[ExecutionGrantResponse]
    total: int


class EligibleExecutionContextResponse(BaseModel):
    plan_id: uuid.UUID
    run_id: uuid.UUID
    task_id: uuid.UUID
    plan_version: int
    task_title: str
    repository_handle_id: uuid.UUID
    repository_display_name: str
    source_revision: str
    snapshot_fingerprint: str


class EligibleExecutionContextListResponse(BaseModel):
    items: list[EligibleExecutionContextResponse]
    total: int


class WorkspaceState(StrEnum):
    REQUESTED = "requested"
    PREPARING = "preparing"
    READY = "ready"
    ACTIVE = "active"
    SEALING = "sealing"
    SEALED = "sealed"
    ROLLBACK_REQUESTED = "rollback_requested"
    ROLLED_BACK = "rolled_back"
    DISCARD_REQUESTED = "discard_requested"
    DISCARDED = "discarded"
    FAILED = "failed"
    EXPIRED = "expired"
    RECOVERY_REQUIRED = "recovery_required"
    QUARANTINED = "quarantined"


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grant_id: uuid.UUID


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    grant_id: uuid.UUID
    runner_id: uuid.UUID
    runner_display_name: str
    repository_handle_id: uuid.UUID
    repository_display_name: str
    source_revision: str
    state: WorkspaceState
    workspace_fingerprint: str | None
    initial_tree_hash: str | None
    current_tree_hash: str | None
    changed_file_count: int
    total_written_bytes: int
    max_files_changed: int
    max_total_write_bytes: int
    max_single_file_bytes: int
    max_diff_bytes: int
    created_paths: list[str]
    active_attempt_id: uuid.UUID | None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    sealed_at: datetime | None
    discarded_at: datetime | None
    error_code: str | None
    error_message: str | None
    latest_job_id: uuid.UUID | None = None
    latest_job_kind: str | None = None
    latest_job_state: str | None = None


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceResponse]
    total: int


class WorkspaceListAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_directory: str
    depth: int = Field(default=2, ge=1, le=4)
    max_entries: int = Field(default=200, ge=1, le=500)

    @field_validator("relative_directory")
    @classmethod
    def validate_relative_directory(cls, value: str) -> str:
        return _validate_relative_path(value)


class WorkspaceReadTextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relative_path: str
    max_bytes: int = Field(default=MAX_WORKSPACE_TEXT_BYTES, ge=1, le=MAX_WORKSPACE_TEXT_BYTES)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_path(value)


class WorkspaceWriteTextAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: WorkspaceWriteMode
    relative_path: str
    content: str
    expected_absent: Literal[True] | None = None
    expected_sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")] | None = None

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        return _validate_relative_path(value)

    @model_validator(mode="after")
    def validate_precondition(self) -> "WorkspaceWriteTextAction":
        if len(self.content.encode("utf-8")) > MAX_WORKSPACE_TEXT_BYTES:
            raise ValueError("content exceeds the Phase 4 text limit")
        if self.mode == WorkspaceWriteMode.CREATE:
            if self.expected_absent is not True or self.expected_sha256 is not None:
                raise ValueError("create requires expected_absent=true only")
        elif self.expected_sha256 is None or self.expected_absent is not None:
            raise ValueError("replace requires expected_sha256 only")
        return self


class WorkspaceActionResponse(BaseModel):
    workspace: WorkspaceResponse
    job: RunnerJobResponse


class WorkspaceEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    runner_id: uuid.UUID
    side_effect_permit_id: uuid.UUID | None
    event_type: str
    sequence: int
    request_id: str
    metadata: dict[str, Any] = Field(validation_alias="details")
    created_at: datetime


class WorkspaceEventListResponse(BaseModel):
    items: list[WorkspaceEventResponse]
    total: int


class WorkspaceCheckpointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    side_effect_permit_id: uuid.UUID | None
    sequence: int
    source_revision: str
    tree_fingerprint: str
    diff_hash: str
    changed_paths: list[str]
    changed_file_count: int
    total_diff_bytes: int
    diff_artifact: str
    created_at: datetime


class WorkspaceCheckpointListResponse(BaseModel):
    items: list[WorkspaceCheckpointResponse]
    total: int
