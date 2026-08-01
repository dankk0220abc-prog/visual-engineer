import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from visual_engineer_api.db.base import Base


class AIPlanRequest(Base):
    __tablename__ = "ai_plan_requests"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_ai_plan_requests_run"),
        UniqueConstraint("idempotency_key", name="uq_ai_plan_requests_idempotency"),
        CheckConstraint(
            "status IN ('requested', 'generating', 'generated', 'rejected', 'approved', "
            "'failed', 'cancelled', 'stale')",
            name="ck_ai_plan_requests_status",
        ),
        CheckConstraint(
            "delivery_package IN ('design_implementation', 'design_system_migration', "
            "'frontend_quality_remediation')",
            name="ck_ai_plan_requests_delivery_package",
        ),
        CheckConstraint(
            "source_revision ~ '^[0-9a-f]{40,64}$' AND "
            "snapshot_fingerprint ~ '^[0-9a-f]{64}$' AND "
            "prompt_digest ~ '^[0-9a-f]{64}$' AND "
            "context_digest ~ '^[0-9a-f]{64}$' AND "
            "request_digest ~ '^[0-9a-f]{64}$' AND "
            "idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_ai_plan_requests_digests",
        ),
        CheckConstraint(
            "deterministic_digest IS NULL OR deterministic_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_plan_requests_response_digest",
        ),
        CheckConstraint(
            "context_bytes >= 0 AND context_reference_count >= 1 AND "
            "context_excluded_count >= 0 AND retry_count BETWEEN 0 AND 2",
            name="ck_ai_plan_requests_counts",
        ),
        CheckConstraint(
            "(response_payload IS NULL) = (deterministic_digest IS NULL) AND (("
            "status IN ('generated', 'approved', 'rejected', 'stale') AND "
            "response_payload IS NOT NULL AND deterministic_digest IS NOT NULL) OR "
            "(status NOT IN ('generated', 'approved', 'rejected', 'stale') AND "
            "((status IN ('requested', 'generating') AND response_payload IS NULL) OR "
            "status IN ('failed', 'cancelled'))))",
            name="ck_ai_plan_requests_response_shape",
        ),
        CheckConstraint(
            "(status IN ('failed', 'cancelled', 'stale') AND error_category IS NOT NULL "
            "AND error_code IS NOT NULL AND error_message IS NOT NULL) OR "
            "(status NOT IN ('failed', 'cancelled', 'stale') AND error_category IS NULL "
            "AND error_code IS NULL AND error_message IS NULL)",
            name="ck_ai_plan_requests_error_shape",
        ),
        CheckConstraint(
            "(status = 'approved' AND handoff_plan_id IS NOT NULL) OR "
            "(status <> 'approved' AND handoff_plan_id IS NULL)",
            name="ck_ai_plan_requests_handoff_shape",
        ),
        Index("ix_ai_plan_requests_run_created", "run_id", "created_at"),
        Index("ix_ai_plan_requests_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="requested")
    delivery_package: Mapped[str] = mapped_column(String(64), nullable=False)
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_template_id: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    deterministic_digest: Mapped[str | None] = mapped_column(String(64))
    context_manifest: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    context_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    context_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    context_reference_count: Mapped[int] = mapped_column(Integer, nullable=False)
    context_excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redaction_record: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_category: Mapped[str | None] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    handoff_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AIProviderTrace(Base):
    __tablename__ = "ai_provider_traces"
    __table_args__ = (
        UniqueConstraint(
            "ai_plan_request_id", "attempt_number", name="uq_ai_provider_traces_attempt"
        ),
        CheckConstraint("attempt_number BETWEEN 1 AND 3", name="ck_ai_provider_traces_attempt"),
        CheckConstraint(
            "status IN ('succeeded', 'failed', 'timeout', 'cancelled')",
            name="ck_ai_provider_traces_status",
        ),
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0 AND "
            "total_tokens = input_tokens + output_tokens AND cost_estimate_microunits >= 0",
            name="ck_ai_provider_traces_usage",
        ),
        CheckConstraint("latency_ms >= 0", name="ck_ai_provider_traces_latency"),
        CheckConstraint(
            "cost_basis = 'synthetic_not_billable' AND cost_estimate_microunits = 0",
            name="ck_ai_provider_traces_synthetic_cost",
        ),
        Index("ix_ai_provider_traces_request_created", "ai_plan_request_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_plan_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_plan_requests.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    response_digest: Mapped[str | None] = mapped_column(String(64))
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_estimate_microunits: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cost_basis: Mapped[str] = mapped_column(String(40), nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(64))
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    redactions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AIEvalResult(Base):
    __tablename__ = "ai_eval_results"
    __table_args__ = (
        UniqueConstraint("ai_plan_request_id", "eval_id", name="uq_ai_eval_results_case"),
        CheckConstraint("severity = 'blocking'", name="ck_ai_eval_results_severity"),
        CheckConstraint("evaluator_trust = 'system_policy'", name="ck_ai_eval_results_trust"),
        Index("ix_ai_eval_results_request", "ai_plan_request_id", "eval_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_plan_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_plan_requests.id", ondelete="CASCADE"), nullable=False
    )
    eval_id: Mapped[str] = mapped_column(String(120), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="blocking")
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evaluator_version: Mapped[str] = mapped_column(String(120), nullable=False)
    evaluator_trust: Mapped[str] = mapped_column(
        String(32), nullable=False, default="system_policy"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AIPlanDecision(Base):
    __tablename__ = "ai_plan_decisions"
    __table_args__ = (
        UniqueConstraint("ai_plan_request_id", name="uq_ai_plan_decisions_request"),
        CheckConstraint("decision IN ('approve', 'reject')", name="ck_ai_plan_decisions_value"),
        CheckConstraint("actor_type = 'local_user'", name="ck_ai_plan_decisions_actor"),
        CheckConstraint(
            "decision <> 'reject' OR (comment IS NOT NULL AND char_length(trim(comment)) > 0)",
            name="ck_ai_plan_decisions_reject_comment",
        ),
        CheckConstraint(
            "(decision = 'approve' AND handoff_plan_id IS NOT NULL) OR "
            "(decision = 'reject' AND handoff_plan_id IS NULL)",
            name="ck_ai_plan_decisions_handoff",
        ),
        Index("ix_ai_plan_decisions_run_created", "run_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_plan_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_plan_requests.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000))
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="local_user")
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    handoff_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
