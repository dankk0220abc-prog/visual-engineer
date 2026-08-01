"""Add governed deterministic Provider planning.

Revision ID: 20260801_0015
Revises: 20260801_0014
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260801_0015"
down_revision: str | None = "20260801_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_plans_source", "plans", type_="check")
    op.create_check_constraint(
        "ck_plans_source",
        "plans",
        "source IN ('deterministic_policy', 'governed_ai')",
    )

    op.create_table(
        "ai_plan_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("delivery_package", sa.String(length=64), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("snapshot_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("prompt_template_id", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=120), nullable=False),
        sa.Column("prompt_digest", sa.String(length=64), nullable=False),
        sa.Column("prompt_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider_id", sa.String(length=120), nullable=False),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deterministic_digest", sa.String(length=64), nullable=True),
        sa.Column("context_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_digest", sa.String(length=64), nullable=False),
        sa.Column("context_bytes", sa.Integer(), nullable=False),
        sa.Column("context_reference_count", sa.Integer(), nullable=False),
        sa.Column("context_excluded_count", sa.Integer(), nullable=False),
        sa.Column("redaction_record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_category", sa.String(length=32), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("idempotency_request_hash", sa.String(length=64), nullable=False),
        sa.Column("handoff_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('requested', 'generating', 'generated', 'rejected', 'approved', "
            "'failed', 'cancelled', 'stale')",
            name="ck_ai_plan_requests_status",
        ),
        sa.CheckConstraint(
            "delivery_package IN ('design_implementation', 'design_system_migration', "
            "'frontend_quality_remediation')",
            name="ck_ai_plan_requests_delivery_package",
        ),
        sa.CheckConstraint(
            "source_revision ~ '^[0-9a-f]{40,64}$' AND "
            "snapshot_fingerprint ~ '^[0-9a-f]{64}$' AND "
            "prompt_digest ~ '^[0-9a-f]{64}$' AND "
            "context_digest ~ '^[0-9a-f]{64}$' AND "
            "request_digest ~ '^[0-9a-f]{64}$' AND "
            "idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_ai_plan_requests_digests",
        ),
        sa.CheckConstraint(
            "deterministic_digest IS NULL OR deterministic_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_plan_requests_response_digest",
        ),
        sa.CheckConstraint(
            "context_bytes >= 0 AND context_reference_count >= 1 AND "
            "context_excluded_count >= 0 AND retry_count BETWEEN 0 AND 2",
            name="ck_ai_plan_requests_counts",
        ),
        sa.CheckConstraint(
            "(response_payload IS NULL) = (deterministic_digest IS NULL) AND (("
            "status IN ('generated', 'approved', 'rejected', 'stale') AND "
            "response_payload IS NOT NULL AND deterministic_digest IS NOT NULL) OR "
            "(status NOT IN ('generated', 'approved', 'rejected', 'stale') AND "
            "((status IN ('requested', 'generating') AND response_payload IS NULL) OR "
            "status IN ('failed', 'cancelled'))))",
            name="ck_ai_plan_requests_response_shape",
        ),
        sa.CheckConstraint(
            "(status IN ('failed', 'cancelled', 'stale') AND error_category IS NOT NULL "
            "AND error_code IS NOT NULL AND error_message IS NOT NULL) OR "
            "(status NOT IN ('failed', 'cancelled', 'stale') AND error_category IS NULL "
            "AND error_code IS NULL AND error_message IS NULL)",
            name="ck_ai_plan_requests_error_shape",
        ),
        sa.CheckConstraint(
            "(status = 'approved' AND handoff_plan_id IS NOT NULL) OR "
            "(status <> 'approved' AND handoff_plan_id IS NULL)",
            name="ck_ai_plan_requests_handoff_shape",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handoff_plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_ai_plan_requests_run"),
        sa.UniqueConstraint("idempotency_key", name="uq_ai_plan_requests_idempotency"),
    )
    op.create_index("ix_ai_plan_requests_run_created", "ai_plan_requests", ["run_id", "created_at"])
    op.create_index("ix_ai_plan_requests_status", "ai_plan_requests", ["status"])

    op.create_table(
        "ai_provider_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_plan_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_id", sa.String(length=120), nullable=False),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("response_digest", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_estimate_microunits", sa.BigInteger(), nullable=False),
        sa.Column("cost_basis", sa.String(length=40), nullable=False),
        sa.Column("error_category", sa.String(length=32), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("redactions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("attempt_number BETWEEN 1 AND 3", name="ck_ai_provider_traces_attempt"),
        sa.CheckConstraint(
            "status IN ('succeeded', 'failed', 'timeout', 'cancelled')",
            name="ck_ai_provider_traces_status",
        ),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0 AND "
            "total_tokens = input_tokens + output_tokens AND cost_estimate_microunits >= 0",
            name="ck_ai_provider_traces_usage",
        ),
        sa.CheckConstraint("latency_ms >= 0", name="ck_ai_provider_traces_latency"),
        sa.CheckConstraint(
            "cost_basis = 'synthetic_not_billable' AND cost_estimate_microunits = 0",
            name="ck_ai_provider_traces_synthetic_cost",
        ),
        sa.CheckConstraint(
            "request_digest ~ '^[0-9a-f]{64}$' AND "
            "(response_digest IS NULL OR response_digest ~ '^[0-9a-f]{64}$')",
            name="ck_ai_provider_traces_digests",
        ),
        sa.ForeignKeyConstraint(
            ["ai_plan_request_id"], ["ai_plan_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ai_plan_request_id", "attempt_number", name="uq_ai_provider_traces_attempt"
        ),
    )
    op.create_index(
        "ix_ai_provider_traces_request_created",
        "ai_provider_traces",
        ["ai_plan_request_id", "created_at"],
    )

    op.create_table(
        "ai_eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_plan_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eval_id", sa.String(length=120), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evaluator_version", sa.String(length=120), nullable=False),
        sa.Column("evaluator_trust", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("severity = 'blocking'", name="ck_ai_eval_results_severity"),
        sa.CheckConstraint("evaluator_trust = 'system_policy'", name="ck_ai_eval_results_trust"),
        sa.ForeignKeyConstraint(
            ["ai_plan_request_id"], ["ai_plan_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ai_plan_request_id", "eval_id", name="uq_ai_eval_results_case"),
    )
    op.create_index(
        "ix_ai_eval_results_request", "ai_eval_results", ["ai_plan_request_id", "eval_id"]
    )

    op.create_table(
        "ai_plan_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_plan_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("handoff_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("decision IN ('approve', 'reject')", name="ck_ai_plan_decisions_value"),
        sa.CheckConstraint("actor_type = 'local_user'", name="ck_ai_plan_decisions_actor"),
        sa.CheckConstraint(
            "decision <> 'reject' OR (comment IS NOT NULL AND char_length(trim(comment)) > 0)",
            name="ck_ai_plan_decisions_reject_comment",
        ),
        sa.CheckConstraint(
            "(decision = 'approve' AND handoff_plan_id IS NOT NULL) OR "
            "(decision = 'reject' AND handoff_plan_id IS NULL)",
            name="ck_ai_plan_decisions_handoff",
        ),
        sa.ForeignKeyConstraint(
            ["ai_plan_request_id"], ["ai_plan_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handoff_plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ai_plan_request_id", name="uq_ai_plan_decisions_request"),
    )
    op.create_index(
        "ix_ai_plan_decisions_run_created", "ai_plan_decisions", ["run_id", "created_at"]
    )
    _install_guards()


def _install_guards() -> None:
    op.execute(
        """
        CREATE FUNCTION reject_ai_evidence_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'AI planning evidence is append-only'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ai_provider_traces_immutable
        BEFORE UPDATE OR DELETE ON ai_provider_traces
        FOR EACH ROW EXECUTE FUNCTION reject_ai_evidence_mutation();

        CREATE TRIGGER ai_eval_results_immutable
        BEFORE UPDATE OR DELETE ON ai_eval_results
        FOR EACH ROW EXECUTE FUNCTION reject_ai_evidence_mutation();

        CREATE TRIGGER ai_plan_decisions_immutable
        BEFORE UPDATE OR DELETE ON ai_plan_decisions
        FOR EACH ROW EXECUTE FUNCTION reject_ai_evidence_mutation();

        CREATE FUNCTION guard_ai_plan_request_insert()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.status <> 'requested'
                OR NEW.response_payload IS NOT NULL
                OR NEW.deterministic_digest IS NOT NULL
                OR NEW.handoff_plan_id IS NOT NULL
                OR NEW.retry_count <> 0
                OR NEW.error_code IS NOT NULL
            THEN
                RAISE EXCEPTION 'AI Plan Request insert state is invalid'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ai_plan_requests_insert_guard
        BEFORE INSERT ON ai_plan_requests
        FOR EACH ROW EXECUTE FUNCTION guard_ai_plan_request_insert();

        CREATE FUNCTION guard_ai_plan_request_update()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
                OR NEW.run_id IS DISTINCT FROM OLD.run_id
                OR NEW.delivery_package IS DISTINCT FROM OLD.delivery_package
                OR NEW.source_revision IS DISTINCT FROM OLD.source_revision
                OR NEW.snapshot_fingerprint IS DISTINCT FROM OLD.snapshot_fingerprint
                OR NEW.prompt_template_id IS DISTINCT FROM OLD.prompt_template_id
                OR NEW.prompt_version IS DISTINCT FROM OLD.prompt_version
                OR NEW.prompt_digest IS DISTINCT FROM OLD.prompt_digest
                OR NEW.prompt_payload IS DISTINCT FROM OLD.prompt_payload
                OR NEW.provider_id IS DISTINCT FROM OLD.provider_id
                OR NEW.provider_metadata IS DISTINCT FROM OLD.provider_metadata
                OR NEW.request_payload IS DISTINCT FROM OLD.request_payload
                OR NEW.request_digest IS DISTINCT FROM OLD.request_digest
                OR NEW.context_manifest IS DISTINCT FROM OLD.context_manifest
                OR NEW.context_digest IS DISTINCT FROM OLD.context_digest
                OR NEW.context_bytes IS DISTINCT FROM OLD.context_bytes
                OR NEW.context_reference_count IS DISTINCT FROM OLD.context_reference_count
                OR NEW.context_excluded_count IS DISTINCT FROM OLD.context_excluded_count
                OR NEW.redaction_record IS DISTINCT FROM OLD.redaction_record
                OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
                OR NEW.idempotency_request_hash IS DISTINCT FROM OLD.idempotency_request_hash
                OR NEW.created_at IS DISTINCT FROM OLD.created_at
                OR NEW.retry_count < OLD.retry_count
                OR (
                    OLD.response_payload IS NOT NULL
                    AND NEW.response_payload IS DISTINCT FROM OLD.response_payload
                )
                OR (
                    OLD.deterministic_digest IS NOT NULL
                    AND NEW.deterministic_digest IS DISTINCT FROM OLD.deterministic_digest
                )
                OR NOT (
                    (
                        OLD.status = 'requested'
                        AND NEW.status IN ('generating', 'failed', 'cancelled')
                    )
                    OR (
                        OLD.status = 'generating'
                        AND NEW.status IN ('generated', 'failed', 'cancelled')
                    )
                    OR (
                        OLD.status = 'generated'
                        AND NEW.status IN ('approved', 'rejected', 'stale', 'cancelled')
                    )
                )
            THEN
                RAISE EXCEPTION 'AI Plan Request mutation is forbidden'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ai_plan_requests_update_guard
        BEFORE UPDATE ON ai_plan_requests
        FOR EACH ROW EXECUTE FUNCTION guard_ai_plan_request_update();

        CREATE TRIGGER ai_plan_requests_delete_guard
        BEFORE DELETE ON ai_plan_requests
        FOR EACH ROW EXECUTE FUNCTION reject_ai_evidence_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER ai_plan_decisions_immutable ON ai_plan_decisions")
    op.execute("DROP TRIGGER ai_eval_results_immutable ON ai_eval_results")
    op.execute("DROP TRIGGER ai_provider_traces_immutable ON ai_provider_traces")
    op.execute("DROP TRIGGER ai_plan_requests_delete_guard ON ai_plan_requests")
    op.execute("DROP TRIGGER ai_plan_requests_update_guard ON ai_plan_requests")
    op.execute("DROP TRIGGER ai_plan_requests_insert_guard ON ai_plan_requests")
    op.execute("DROP FUNCTION guard_ai_plan_request_update()")
    op.execute("DROP FUNCTION guard_ai_plan_request_insert()")
    op.execute("DROP FUNCTION reject_ai_evidence_mutation()")
    op.drop_index("ix_ai_plan_decisions_run_created", table_name="ai_plan_decisions")
    op.drop_table("ai_plan_decisions")
    op.drop_index("ix_ai_eval_results_request", table_name="ai_eval_results")
    op.drop_table("ai_eval_results")
    op.drop_index("ix_ai_provider_traces_request_created", table_name="ai_provider_traces")
    op.drop_table("ai_provider_traces")
    op.drop_index("ix_ai_plan_requests_status", table_name="ai_plan_requests")
    op.drop_index("ix_ai_plan_requests_run_created", table_name="ai_plan_requests")
    op.drop_table("ai_plan_requests")
    op.execute("DELETE FROM plans WHERE source = 'governed_ai'")
    op.drop_constraint("ck_plans_source", "plans", type_="check")
    op.create_check_constraint("ck_plans_source", "plans", "source = 'deterministic_policy'")
