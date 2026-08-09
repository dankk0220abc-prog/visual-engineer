import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from visual_engineer_api.ai_planning.contracts import (
    AIPlanContract,
    AIPlanGenerationRequest,
    ContextManifestEntry,
    DeliveryPackage,
    ProviderCapabilityMetadata,
)
from visual_engineer_api.ai_planning.invocation_contract import (
    DispatchBoundaryStatus,
    InvocationBillingStatus,
    InvocationClassification,
    InvocationStatus,
    InvocationUsageStatus,
    ReportedValueStatus,
    RequestDigestKind,
    ResponseDigestKind,
)
from visual_engineer_api.ai_planning.provider_registry import (
    ProviderConfigurationStatus,
    ProviderId,
)


class AIPlanRequestStatus(StrEnum):
    REQUESTED = "requested"
    GENERATING = "generating"
    GENERATED = "generated"
    REJECTED = "rejected"
    APPROVED = "approved"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STALE = "stale"


class AIPlanRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_package: DeliveryPackage
    provider_id: ProviderId = ProviderId.DETERMINISTIC_FIXTURE


class AIPlanDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None

    @model_validator(mode="after")
    def validate_comment(self) -> "AIPlanDecisionCreate":
        if self.decision == "reject" and not self.comment:
            raise ValueError("a non-blank rejection reason is required")
        if self.comment is not None and "\x00" in self.comment:
            raise ValueError("NUL characters are not allowed")
        return self


class AIProviderInvocationResponse(BaseModel):
    id: uuid.UUID
    ai_plan_request_id: uuid.UUID
    attempt_number: int
    contract_version: int
    classification: InvocationClassification
    status: InvocationStatus
    provider_id: ProviderId
    adapter_version: str
    requested_model_id: str
    effective_model_status: ReportedValueStatus
    effective_model_id: str | None
    upstream_request_id_status: ReportedValueStatus
    upstream_request_fingerprint: str | None
    request_digest: str
    request_digest_kind: RequestDigestKind
    response_digest: str | None
    response_digest_kind: ResponseDigestKind
    usage_status: InvocationUsageStatus
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    queue_wait_ms: int | None
    provider_elapsed_ms: int | None
    client_total_elapsed_ms: int | None
    legacy_latency_ms: float | None
    billing_status: InvocationBillingStatus
    cost_amount: Decimal | None
    cost_currency: str | None
    error_category: str | None
    error_code: str | None
    created_at: datetime
    dispatch_boundary_status: DispatchBoundaryStatus
    dispatch_started_at: datetime | None
    completed_at: datetime | None


class AIEvalResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ai_plan_request_id: uuid.UUID
    eval_id: str
    passed: bool
    severity: Literal["blocking"]
    summary: str
    evidence: dict[str, Any]
    evaluator_version: str
    evaluator_trust: Literal["system_policy"]
    created_at: datetime


class AIPlanDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ai_plan_request_id: uuid.UUID
    run_id: uuid.UUID
    decision: Literal["approve", "reject"]
    comment: str | None
    actor_type: Literal["local_user"]
    request_id: str
    handoff_plan_id: uuid.UUID | None
    created_at: datetime


class AIPlanRequestResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    status: AIPlanRequestStatus
    delivery_package: DeliveryPackage
    source_revision: str
    snapshot_fingerprint: str
    prompt_template_id: str
    prompt_version: str
    prompt_digest: str
    prompt_payload: dict[str, Any]
    provider_id: ProviderId
    provider_metadata: ProviderCapabilityMetadata
    request_payload: AIPlanGenerationRequest
    request_digest: str
    plan: AIPlanContract | None
    deterministic_digest: str | None
    context_manifest: list[ContextManifestEntry]
    context_digest: str
    context_bytes: int
    context_reference_count: int
    context_excluded_count: int
    redaction_record: list[dict[str, Any]]
    retry_count: int
    error_category: str | None
    error_code: str | None
    error_message: str | None
    handoff_plan_id: uuid.UUID | None
    invocations: list[AIProviderInvocationResponse]
    eval_results: list[AIEvalResultResponse]
    decision: AIPlanDecisionResponse | None
    created_at: datetime
    updated_at: datetime


class AIPlanRequestListResponse(BaseModel):
    items: list[AIPlanRequestResponse]
    total: int


class AIProviderListResponse(BaseModel):
    items: list[ProviderConfigurationStatus]
    total: int = Field(ge=0)
