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
    profile_id: Literal[
        "fixture-python-stdlib-v1",
        "fixture-python-manifest-v1",
    ]
    version: Literal[1]
    display_name: str
    description: str
    step_id: Literal["fixture-contract", "fixture-manifest"]
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
    profile_id: Literal[
        "fixture-python-stdlib-v1",
        "fixture-python-manifest-v1",
    ]


class ValidationStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence: Literal[1]
    step_id: Literal["fixture-contract", "fixture-manifest"]
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
    result_schema_version: int | None
    validation_step_id: str | None
    source_revision: str | None
    policy_digest: str | None
    fixed_argv: list[str]
    fixed_argv_digest: str | None
    fixed_cwd: str | None
    fixed_environment_digest: str | None
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
    artifact_manifest_digest: str | None
    side_effect_permit_id: uuid.UUID
    side_effect_permit_sequence: int | None
    side_effect_permit_digest: str | None
    fencing_token: str | None
    execution_envelope_digest: str | None
    evidence_digest: str | None
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
    profile_id: Literal[
        "fixture-python-stdlib-v1",
        "fixture-python-manifest-v1",
    ]
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


class ValidationSuiteRunState(StrEnum):
    REQUESTED = "requested"
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    RECOVERY_REQUIRED = "recovery_required"


class ValidationSuiteStepState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    RECOVERY_REQUIRED = "recovery_required"


class ValidationSuiteCatalogStepResponse(BaseModel):
    sequence: int
    step_id: Literal["fixture-contract", "fixture-manifest"]
    profile_id: Literal[
        "fixture-python-stdlib-v1",
        "fixture-python-manifest-v1",
    ]
    profile_version: Literal[1]
    timeout_seconds: int
    max_output_bytes: int
    max_artifact_bytes: Literal[0] = 0
    max_artifact_count: Literal[0] = 0


class ValidationSuiteResponse(BaseModel):
    suite_id: Literal["fixture-integrity-suite-v1"]
    suite_version: Literal[1]
    name: str
    purpose: str
    steps: list[ValidationSuiteCatalogStepResponse]
    failure_policy: Literal["fail_fast"]
    total_timeout_seconds: int
    total_output_bytes: int
    max_attempts: int
    policy_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    network_policy: Literal["none"] = "none"
    shell_access: Literal[False] = False
    user_command_input: Literal[False] = False
    artifact_content_transfer: Literal[False] = False


class ValidationSuiteListResponse(BaseModel):
    items: list[ValidationSuiteResponse]
    total: int


class ValidationSuiteRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_grant_id: uuid.UUID
    suite_id: Literal["fixture-integrity-suite-v1"]
    suite_version: Literal[1]


class ValidationSuiteRetryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_grant_id: uuid.UUID


class ValidationSuiteStepRunResponse(BaseModel):
    id: uuid.UUID
    sequence: int
    step_id: Literal["fixture-contract", "fixture-manifest"]
    profile_id: Literal[
        "fixture-python-stdlib-v1",
        "fixture-python-manifest-v1",
    ]
    profile_version: Literal[1]
    timeout_seconds: int
    max_output_bytes: int
    state: ValidationSuiteStepState
    validation_run_id: uuid.UUID | None
    runner_job_id: uuid.UUID | None
    runner_id: uuid.UUID | None
    attempt_id: uuid.UUID | None
    lease_id: uuid.UUID | None
    evidence_id: uuid.UUID | None
    reused_from_step_run_id: uuid.UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    exit_code: int | None
    output_bytes: int
    redaction_count: int
    output_truncated: bool
    cleanup_succeeded: bool | None
    failure_code: str | None
    evidence: ValidationEvidenceResponse | None


class ValidationSuiteResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    verdict: Literal[
        "succeeded",
        "failed",
        "timed_out",
        "cancelled",
        "recovery_required",
    ]
    profile_references: list[str]
    evidence_references: list[dict[str, object]]
    audit_event_references: list[str]
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    combined_output_bytes: int
    redaction_count: int
    output_truncated: bool
    timed_out: bool
    cancelled: bool
    recovery_required: bool
    cleanup_succeeded: bool
    source_invariant: bool
    canonical_workspace_invariant: bool
    artifact_count: Literal[0]
    artifact_bytes: Literal[0]
    aggregate_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    created_at: datetime


class ValidationSuiteRunResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    plan_id: uuid.UUID
    source_revision: str
    workspace_id: uuid.UUID
    checkpoint_id: uuid.UUID
    checkpoint_fingerprint: str
    execution_grant_id: uuid.UUID
    suite_id: Literal["fixture-integrity-suite-v1"]
    suite_version: Literal[1]
    policy_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    failure_policy: Literal["fail_fast"]
    state: ValidationSuiteRunState
    step_count: int
    completed_step_count: int
    total_timeout_seconds: int
    total_output_bytes: int
    combined_output_bytes: int
    max_attempts: int
    attempt_number: int
    retry_of_suite_run_id: uuid.UUID | None
    requested_at: datetime
    started_at: datetime | None
    deadline_at: datetime | None
    cancel_requested_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    steps: list[ValidationSuiteStepRunResponse]
    result: ValidationSuiteResultResponse | None


class ValidationSuiteRunListResponse(BaseModel):
    items: list[ValidationSuiteRunResponse]
    total: int


class ValidationSuiteTimelineResponse(BaseModel):
    suite_run_id: uuid.UUID
    state: ValidationSuiteRunState
    steps: list[ValidationSuiteStepRunResponse]


class ValidationSuiteAggregateResponse(BaseModel):
    suite_run_id: uuid.UUID
    state: ValidationSuiteRunState
    result: ValidationSuiteResultResponse | None
