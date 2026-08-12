import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from visual_engineer_runner_protocol import (
    Capability,
    ControlledWaitJobSpec,
    JobKind,
    JobState,
    NetworkPolicy,
    RepositoryAccess,
    ResultPayload,
    RunnerStatus,
    SystemDiagnosticJobSpec,
)


class ActiveJobSummary(BaseModel):
    id: uuid.UUID
    kind: JobKind
    state: JobState


class RunnerResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    protocol_version: int
    software_version: str
    capabilities: list[Capability]
    status: RunnerStatus
    last_seen_at: datetime | None
    registered_at: datetime
    revoked_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    active_job: ActiveJobSummary | None = None


class RunnerListResponse(BaseModel):
    items: list[RunnerResponse]
    total: int


class PermissionEnvelopeResponse(BaseModel):
    id: uuid.UUID
    envelope_version: int
    job_id: uuid.UUID
    authorization_source: str
    allowed_capabilities: list[Capability]
    repository_access: RepositoryAccess
    shell_access: bool
    network_policy: NetworkPolicy
    max_runtime_seconds: int
    lease_seconds: int
    max_attempts: int
    max_result_bytes: int
    issued_at: datetime
    expires_at: datetime
    policy_hash: str
    created_at: datetime


class RunnerJobAttemptResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    runner_id: uuid.UUID
    attempt_number: int
    lease_id_hint: str
    state: str
    leased_until: datetime
    last_heartbeat_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime


class RunnerJobResponse(BaseModel):
    id: uuid.UUID
    kind: JobKind
    state: JobState
    requested_by: str
    parameters: dict[str, Any]
    execution_grant_id: uuid.UUID | None
    delivery_authorization_id: uuid.UUID | None
    workspace_id: uuid.UUID | None
    repository_handle_id: uuid.UUID | None
    source_revision: str | None
    execution_policy_hash: str | None
    active_attempt_id: uuid.UUID | None
    attempt_count: int
    max_attempts: int
    result: ResultPayload | None
    result_projection_status: Literal["not_available", "available", "incompatible_legacy"]
    result_projection_error_code: str | None
    error_code: str | None
    error_message: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    permission_envelope: PermissionEnvelopeResponse
    active_attempt: RunnerJobAttemptResponse | None
    attempts: list[RunnerJobAttemptResponse] = Field(default_factory=list)


class RunnerJobListResponse(BaseModel):
    items: list[RunnerJobResponse]
    total: int


class RunnerJobCreateResponse(BaseModel):
    job: RunnerJobResponse


class RunnerJobEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    runner_id: uuid.UUID | None
    job_id: uuid.UUID | None
    attempt_id: uuid.UUID | None
    event_type: str
    sequence: int
    request_id: str
    metadata: dict[str, Any] = Field(validation_alias="details")
    created_at: datetime


class RunnerJobEventListResponse(BaseModel):
    items: list[RunnerJobEventResponse]
    total: int


RunnerJobCreate = Annotated[
    SystemDiagnosticJobSpec | ControlledWaitJobSpec,
    Field(discriminator="kind"),
]
