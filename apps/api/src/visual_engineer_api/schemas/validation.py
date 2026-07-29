import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from visual_engineer_api.schemas.runner import RunnerJobResponse


class ValidationRunState(StrEnum):
    REQUESTED = "requested"
    QUEUED = "queued"
    CLAIMED = "claimed"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    RECOVERY_REQUIRED = "recovery_required"


class ValidationProfileResponse(BaseModel):
    profile_id: Literal["fixture-python-stdlib-v1"]
    version: Literal[1]
    display_name: str
    description: str
    step_id: Literal["fixture-contract"]
    safe_argv: list[str]
    timeout_seconds: int
    max_output_bytes: int
    max_artifact_bytes: int
    max_artifact_count: int
    network_policy: Literal["none"] = "none"
    shell_access: Literal[False] = False
    user_command_input: Literal[False] = False


class ValidationProfileListResponse(BaseModel):
    items: list[ValidationProfileResponse]
    total: int


class ValidationRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_grant_id: uuid.UUID
    profile_id: Literal["fixture-python-stdlib-v1"]


class ValidationStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: Literal[1]
    step_id: Literal["fixture-contract"]
    state: str
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    exit_code: int | None
    failure_code: str | None


class ValidationEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    runner_id: uuid.UUID
    attempt_id: uuid.UUID
    lease_id: uuid.UUID
    fixed_argv: list[str]
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    exit_code: int
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    redaction_count: int
    timed_out: bool
    cancelled: bool
    network_isolated: bool
    filesystem_isolated: bool
    sandbox_cleaned: bool
    artifact_count: int
    artifact_bytes: int
    artifact_summary: dict[str, object]
    side_effect_permit_id: uuid.UUID
    created_at: datetime


class ValidationRunResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    plan_id: uuid.UUID
    source_revision: str
    workspace_id: uuid.UUID
    checkpoint_id: uuid.UUID
    checkpoint_fingerprint: str
    execution_grant_id: uuid.UUID
    runner_job_id: uuid.UUID | None
    runner_id: uuid.UUID | None
    attempt_id: uuid.UUID | None
    lease_id: uuid.UUID | None
    profile_id: Literal["fixture-python-stdlib-v1"]
    profile_version: Literal[1]
    policy_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    state: ValidationRunState
    timeout_seconds: int
    max_output_bytes: int
    max_artifact_bytes: int
    max_artifact_count: int
    requested_at: datetime
    claimed_at: datetime | None
    started_at: datetime | None
    cancel_requested_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    step: ValidationStepResponse
    evidence: ValidationEvidenceResponse | None
    job: RunnerJobResponse | None


class ValidationRunListResponse(BaseModel):
    items: list[ValidationRunResponse]
    total: int


class ValidationEvidenceListResponse(BaseModel):
    items: list[ValidationEvidenceResponse]
    total: int
