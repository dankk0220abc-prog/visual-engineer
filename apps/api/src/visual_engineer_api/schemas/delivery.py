import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from visual_engineer_api.schemas.runner import RunnerJobResponse

Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
ObjectId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]


class DeliveryAuthorizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_package_id: uuid.UUID


class DeliveryAuthorizationDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    reason: Annotated[str | None, StringConstraints(max_length=2000)] = None

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "DeliveryAuthorizationDecisionCreate":
        if self.decision == "reject" and not (self.reason or "").strip():
            raise ValueError("reason is required when rejecting Delivery Authorization")
        if self.reason is not None and ("\x00" in self.reason or not self.reason.strip()):
            raise ValueError("reason must be non-blank and contain no NUL characters")
        return self


class DeliveryAuthorizationDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_authorization_id: uuid.UUID
    authorization_policy_hash: Digest
    decision: Literal["approve", "reject"]
    reason: str | None
    actor_type: Literal["local_user"]
    request_id: str
    idempotency_key: str
    idempotency_request_hash: Digest
    decision_digest: Digest
    local_git_commit_authorized: bool
    remote_access: Literal[False]
    push_access: Literal[False]
    pull_request_access: Literal[False]
    tag_access: Literal[False]
    deployment_access: Literal[False]
    created_at: datetime


class LocalDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    delivery_authorization_id: uuid.UUID
    runner_job_id: uuid.UUID
    runner_attempt_id: uuid.UUID
    side_effect_permit_id: uuid.UUID
    workspace_id: uuid.UUID
    checkpoint_id: uuid.UUID
    checkpoint_fingerprint: Digest
    checkpoint_diff_hash: Digest
    branch_ref: str
    commit_oid: ObjectId
    tree_oid: ObjectId
    parent_oid: ObjectId
    result_digest: Digest
    remote_access: Literal[False]
    pushed: Literal[False]
    pull_request_created: Literal[False]
    tagged: Literal[False]
    deployed: Literal[False]
    created_at: datetime


class DeliveryAuthorizationResponse(BaseModel):
    id: uuid.UUID
    authorization_version: Literal[1]
    review_package_id: uuid.UUID
    review_decision_id: uuid.UUID
    readiness_verdict_id: uuid.UUID
    freshness_generation: int
    package_digest: Digest
    decision_digest: Digest
    readiness_digest: Digest
    execution_grant_id: uuid.UUID
    workspace_id: uuid.UUID
    checkpoint_id: uuid.UUID
    checkpoint_fingerprint: Digest
    checkpoint_diff_hash: Digest
    repository_handle_id: uuid.UUID
    source_revision: str
    branch_ref: str
    commit_message: str
    local_git_commit_access: Literal[True]
    remote_access: Literal[False]
    push_access: Literal[False]
    pull_request_access: Literal[False]
    tag_access: Literal[False]
    deployment_access: Literal[False]
    source_repository_write_access: Literal[False]
    status: Literal[
        "pending",
        "approved",
        "rejected",
        "dispatched",
        "succeeded",
        "failed",
        "cancelled",
        "stale",
    ]
    policy_hash: Digest
    created_at: datetime
    decided_at: datetime | None
    dispatched_at: datetime | None
    terminal_at: datetime | None
    expires_at: datetime
    error_code: str | None
    decision: DeliveryAuthorizationDecisionResponse | None
    job: RunnerJobResponse | None
    delivery: LocalDeliveryResponse | None


class DeliveryAuthorizationListResponse(BaseModel):
    items: list[DeliveryAuthorizationResponse]
    total: int
