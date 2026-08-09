import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
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


class AIProviderInvocation(Base):
    __tablename__ = "ai_provider_invocations"
    __table_args__ = (
        UniqueConstraint(
            "ai_plan_request_id", "attempt_number", name="uq_ai_provider_invocations_attempt"
        ),
        CheckConstraint(
            "(contract_version = 0 AND attempt_number BETWEEN 1 AND 3) OR "
            "(contract_version = 1 AND attempt_number BETWEEN 1 AND 32767)",
            name="ck_ai_provider_invocations_version_attempt",
        ),
        CheckConstraint(
            "(contract_version = 0 AND classification = 'fixture' AND "
            "provider_id = 'deterministic-fixture' AND "
            "status IN ('succeeded', 'failed', 'timeout', 'cancelled')) OR "
            "(contract_version = 1 AND classification IN ('fixture', 'mock', 'live') AND "
            "status IN ('prepared', 'dispatching', 'succeeded', 'failed', "
            "'cancelled_before_dispatch', 'outcome_unknown') AND "
            "provider_id IN ('deterministic-fixture', 'zhipu', 'qwen', 'deepseek', "
            "'doubao', 'kimi'))",
            name="ck_ai_provider_invocations_closed_identity",
        ),
        CheckConstraint(
            "effective_model_status IN ('reported', 'unavailable') AND "
            "((effective_model_status = 'reported' AND effective_model_id IS NOT NULL AND "
            "char_length(trim(effective_model_id)) > 0) OR "
            "(effective_model_status = 'unavailable' AND effective_model_id IS NULL)) AND "
            "upstream_request_id_status IN ('reported', 'unavailable') AND "
            "((upstream_request_id_status = 'reported' AND upstream_request_id IS NOT NULL AND "
            "char_length(trim(upstream_request_id)) > 0) OR "
            "(upstream_request_id_status = 'unavailable' AND upstream_request_id IS NULL)) AND "
            "(contract_version = 1 OR (effective_model_status = 'unavailable' AND "
            "effective_model_id IS NULL AND upstream_request_id_status = 'unavailable' AND "
            "upstream_request_id IS NULL))",
            name="ck_ai_provider_invocations_reported_identity",
        ),
        CheckConstraint(
            "usage_status IN ('synthetic_complete', 'reported_complete', 'reported_partial', "
            "'reported_invalid', 'unavailable') AND "
            "(input_tokens IS NULL OR input_tokens >= 0) AND "
            "(output_tokens IS NULL OR output_tokens >= 0) AND "
            "(total_tokens IS NULL OR total_tokens >= 0) AND ("
            "(usage_status IN ('synthetic_complete', 'reported_complete') AND "
            "input_tokens IS NOT NULL AND output_tokens IS NOT NULL AND total_tokens IS NOT NULL "
            "AND total_tokens = input_tokens + output_tokens) OR "
            "(usage_status = 'reported_partial' AND "
            "num_nonnulls(input_tokens, output_tokens, total_tokens) BETWEEN 1 AND 2) OR "
            "usage_status = 'reported_invalid' OR "
            "(usage_status = 'unavailable' AND "
            "input_tokens IS NULL AND output_tokens IS NULL AND total_tokens IS NULL))",
            name="ck_ai_provider_invocations_usage",
        ),
        CheckConstraint(
            "(classification = 'fixture' AND usage_status IN "
            "('synthetic_complete', 'unavailable') AND billing_status IN "
            "('not_billable_fixture', 'not_dispatched')) OR "
            "(classification = 'mock' AND usage_status IN "
            "('synthetic_complete', 'unavailable') AND billing_status IN "
            "('mock_not_billable', 'not_dispatched')) OR "
            "(classification = 'live' AND usage_status IN "
            "('reported_complete', 'reported_partial', 'reported_invalid', 'unavailable') AND "
            "billing_status IN ('live_billing_unknown', 'live_cost_reported', "
            "'not_dispatched'))",
            name="ck_ai_provider_invocations_classification_facts",
        ),
        CheckConstraint(
            "billing_status IN ('not_billable_fixture', 'mock_not_billable', "
            "'live_billing_unknown', 'live_cost_reported', 'not_dispatched') AND ("
            "(billing_status <> 'live_cost_reported' AND cost_amount IS NULL AND "
            "cost_currency IS NULL) OR "
            "(billing_status = 'live_cost_reported' AND cost_amount IS NOT NULL AND "
            "cost_amount >= 0 AND cost_currency ~ '^[A-Z]{3}$')) AND ("
            "billing_status <> 'not_dispatched' OR (contract_version = 1 AND ("
            "status = 'cancelled_before_dispatch' OR "
            "(status = 'failed' AND dispatch_started_at IS NULL))))",
            name="ck_ai_provider_invocations_billing",
        ),
        CheckConstraint(
            "request_digest ~ '^[0-9a-f]{64}$' AND "
            "(response_digest IS NULL OR response_digest ~ '^[0-9a-f]{64}$')",
            name="ck_ai_provider_invocations_digests",
        ),
        CheckConstraint(
            "(queue_wait_ms IS NULL OR queue_wait_ms >= 0) AND "
            "(provider_elapsed_ms IS NULL OR provider_elapsed_ms >= 0) AND "
            "(client_total_elapsed_ms IS NULL OR client_total_elapsed_ms >= 0)",
            name="ck_ai_provider_invocations_latency",
        ),
        CheckConstraint(
            "(contract_version = 0 AND status IN "
            "('succeeded', 'failed', 'timeout', 'cancelled') AND "
            "dispatch_started_at IS NULL AND completed_at IS NOT NULL AND "
            "queue_wait_ms IS NULL AND provider_elapsed_ms IS NULL AND "
            "client_total_elapsed_ms IS NULL) OR (contract_version = 1 AND ((status = "
            "'prepared' AND dispatch_started_at IS NULL AND completed_at IS NULL AND "
            "queue_wait_ms IS NULL AND provider_elapsed_ms IS NULL AND "
            "client_total_elapsed_ms IS NULL) OR "
            "(status = 'dispatching' AND dispatch_started_at IS NOT NULL AND "
            "completed_at IS NULL AND queue_wait_ms IS NOT NULL AND "
            "provider_elapsed_ms IS NULL AND client_total_elapsed_ms IS NULL) OR "
            "(status = 'cancelled_before_dispatch' AND dispatch_started_at IS NULL AND "
            "completed_at IS NOT NULL AND provider_elapsed_ms IS NULL AND "
            "client_total_elapsed_ms IS NOT NULL) OR "
            "(status = 'succeeded' AND dispatch_started_at IS NOT NULL AND "
            "completed_at IS NOT NULL AND queue_wait_ms IS NOT NULL AND "
            "provider_elapsed_ms IS NOT NULL AND client_total_elapsed_ms IS NOT NULL) OR "
            "(status = 'outcome_unknown' AND dispatch_started_at IS NOT NULL AND "
            "completed_at IS NOT NULL AND queue_wait_ms IS NOT NULL) OR "
            "(status = 'failed' AND completed_at IS NOT NULL AND "
            "client_total_elapsed_ms IS NOT NULL AND ((dispatch_started_at IS NULL AND "
            "provider_elapsed_ms IS NULL) OR (dispatch_started_at IS NOT NULL AND "
            "queue_wait_ms IS NOT NULL AND provider_elapsed_ms IS NOT NULL)))))",
            name="ck_ai_provider_invocations_lifecycle",
        ),
        CheckConstraint(
            "contract_version = 0 OR (contract_version = 1 AND ((status = 'succeeded' AND "
            "response_digest IS NOT NULL AND error_category IS NULL "
            "AND error_code IS NULL) OR "
            "(status IN ('failed', 'cancelled_before_dispatch', 'outcome_unknown') AND "
            "response_digest IS NULL AND error_category IS NOT NULL AND error_code IS NOT NULL) "
            "OR (status IN ('prepared', 'dispatching') AND response_digest IS NULL AND "
            "error_category IS NULL AND error_code IS NULL)))",
            name="ck_ai_provider_invocations_terminal",
        ),
        CheckConstraint(
            "contract_version = 0 OR error_category IS NULL OR error_category IN "
            "('provider_not_configured', "
            "'provider_disabled', 'authentication_failed', 'rate_limited', 'timeout', "
            "'cancelled', 'model_unavailable', 'upstream_server_error', 'request_rejected', "
            "'budget_exceeded', 'transport_error', 'structured_output_invalid', "
            "'unavailable', 'invalid_response', 'policy_denied', 'internal')",
            name="ck_ai_provider_invocations_error_category",
        ),
        CheckConstraint(
            "contract_version = 0 OR status NOT IN ('prepared', 'dispatching') OR "
            "(effective_model_status = 'unavailable' AND effective_model_id IS NULL AND "
            "upstream_request_id_status = 'unavailable' AND upstream_request_id IS NULL AND "
            "usage_status = 'unavailable' AND input_tokens IS NULL AND "
            "output_tokens IS NULL AND total_tokens IS NULL)",
            name="ck_ai_provider_invocations_nonterminal_audit",
        ),
        CheckConstraint(
            "contract_version = 0 OR NOT (status = 'cancelled_before_dispatch' OR "
            "(status = 'failed' AND dispatch_started_at IS NULL)) OR ("
            "response_digest IS NULL AND effective_model_status = 'unavailable' AND "
            "effective_model_id IS NULL AND upstream_request_id_status = 'unavailable' AND "
            "upstream_request_id IS NULL AND usage_status = 'unavailable' AND "
            "input_tokens IS NULL AND output_tokens IS NULL AND total_tokens IS NULL AND "
            "queue_wait_ms IS NULL AND provider_elapsed_ms IS NULL AND "
            "billing_status = 'not_dispatched' AND cost_amount IS NULL AND "
            "cost_currency IS NULL)",
            name="ck_ai_provider_invocations_pre_dispatch_terminal",
        ),
        CheckConstraint(
            "(contract_version = 0 AND legacy_latency_ms IS NOT NULL AND "
            "legacy_input_tokens IS NOT NULL AND legacy_output_tokens IS NOT NULL AND "
            "legacy_total_tokens IS NOT NULL AND "
            "legacy_cost_estimate_microunits IS NOT NULL AND legacy_cost_basis IS NOT NULL "
            "AND legacy_retryable IS NOT NULL AND legacy_latency_ms >= 0 AND "
            "legacy_input_tokens >= 0 AND legacy_output_tokens >= 0 AND "
            "legacy_total_tokens = legacy_input_tokens + legacy_output_tokens AND "
            "legacy_cost_estimate_microunits = 0 AND "
            "legacy_cost_basis = 'synthetic_not_billable') OR "
            "(contract_version = 1 AND legacy_latency_ms IS NULL AND "
            "legacy_input_tokens IS NULL AND legacy_output_tokens IS NULL AND "
            "legacy_total_tokens IS NULL AND legacy_cost_estimate_microunits IS NULL AND "
            "legacy_cost_basis IS NULL AND legacy_retryable IS NULL)",
            name="ck_ai_provider_invocations_legacy_provenance",
        ),
        Index(
            "ix_ai_provider_invocations_provider_class_created",
            "provider_id",
            "classification",
            "created_at",
        ),
        Index(
            "ix_ai_provider_invocations_recovery",
            "status",
            "dispatch_started_at",
            postgresql_where=text(
                "contract_version = 1 AND status = 'dispatching' "
                "AND dispatch_started_at IS NOT NULL"
            ),
        ),
        Index(
            "ix_ai_provider_invocations_upstream",
            "provider_id",
            "upstream_request_id",
            postgresql_where=text("upstream_request_id_status = 'reported'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_plan_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_plan_requests.id", ondelete="RESTRICT"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    contract_version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    classification: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="prepared")
    provider_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(120), nullable=False)
    requested_model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    effective_model_status: Mapped[str] = mapped_column(String(16), nullable=False)
    effective_model_id: Mapped[str | None] = mapped_column(String(120))
    upstream_request_id_status: Mapped[str] = mapped_column(String(16), nullable=False)
    upstream_request_id: Mapped[str | None] = mapped_column(String(255))
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    response_digest: Mapped[str | None] = mapped_column(String(64))
    legacy_latency_ms: Mapped[float | None] = mapped_column(Float)
    legacy_input_tokens: Mapped[int | None] = mapped_column(Integer)
    legacy_output_tokens: Mapped[int | None] = mapped_column(Integer)
    legacy_total_tokens: Mapped[int | None] = mapped_column(Integer)
    legacy_cost_estimate_microunits: Mapped[int | None] = mapped_column(BigInteger)
    legacy_cost_basis: Mapped[str | None] = mapped_column(String(40))
    legacy_retryable: Mapped[bool | None] = mapped_column(Boolean)
    usage_status: Mapped[str] = mapped_column(String(24), nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(BigInteger)
    output_tokens: Mapped[int | None] = mapped_column(BigInteger)
    total_tokens: Mapped[int | None] = mapped_column(BigInteger)
    queue_wait_ms: Mapped[int | None] = mapped_column(BigInteger)
    provider_elapsed_ms: Mapped[int | None] = mapped_column(BigInteger)
    client_total_elapsed_ms: Mapped[int | None] = mapped_column(BigInteger)
    billing_status: Mapped[str] = mapped_column(String(32), nullable=False)
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    cost_currency: Mapped[str | None] = mapped_column(CHAR(3))
    error_category: Mapped[str | None] = mapped_column(String(32))
    error_code: Mapped[str | None] = mapped_column(String(64))
    redactions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    dispatch_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
