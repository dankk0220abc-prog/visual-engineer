import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ReviewFreshness(StrEnum):
    FRESH = "fresh"
    STALE = "stale"


class ReviewPackageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite_run_id: uuid.UUID


class ReviewDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    reason: Annotated[str | None, StringConstraints(max_length=2000)] = None

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "ReviewDecisionCreate":
        if self.decision == "reject" and not (self.reason or "").strip():
            raise ValueError("reason is required when rejecting a Review Package")
        if self.reason is not None and ("\x00" in self.reason or not self.reason.strip()):
            raise ValueError("reason must be non-blank and contain no NUL characters")
        return self


class ReviewPackageInvalidationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    review_package_id: uuid.UUID
    package_digest: Digest
    reason_code: Literal[
        "workspace_changed",
        "checkpoint_superseded",
        "source_revision_changed",
        "suite_result_superseded",
        "evidence_integrity_failed",
    ]
    observed_value: str
    request_id: str
    created_at: datetime


class ReviewDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    review_package_id: uuid.UUID
    package_digest: Digest
    decision: Literal["approve", "reject"]
    reason: str | None
    actor_type: Literal["local_user"]
    request_id: str
    git_authorization: Literal[False]
    deployment_authorization: Literal[False]
    created_at: datetime


class ReleaseReadinessVerdictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    review_package_id: uuid.UUID
    review_decision_id: uuid.UUID
    package_digest: Digest
    decision_digest: Digest
    evidence_manifest_digest: Digest
    verdict: Literal["ready", "not_ready"]
    effective_verdict: Literal["ready", "not_ready", "stale"]
    reason_codes: list[str]
    verdict_digest: Digest
    git_authorization: Literal[False]
    deployment_authorization: Literal[False]
    created_at: datetime


class ReviewPackageResponse(BaseModel):
    id: uuid.UUID
    schema_version: Literal[1]
    run_id: uuid.UUID
    plan_id: uuid.UUID
    repository_handle_id: uuid.UUID
    source_revision: str
    workspace_id: uuid.UUID
    checkpoint_id: uuid.UUID
    checkpoint_fingerprint: Digest
    suite_run_id: uuid.UUID
    suite_result_id: uuid.UUID
    suite_result_digest: Digest
    evidence_manifest: dict[str, object]
    evidence_manifest_digest: Digest
    package_digest: Digest
    freshness: ReviewFreshness
    stale_reason_code: str | None
    git_authorization: Literal[False]
    deployment_authorization: Literal[False]
    created_at: datetime
    invalidation: ReviewPackageInvalidationResponse | None
    decision: ReviewDecisionResponse | None
    readiness: ReleaseReadinessVerdictResponse | None


class ReviewPackageListResponse(BaseModel):
    items: list[ReviewPackageResponse]
    total: int
