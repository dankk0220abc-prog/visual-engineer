"""Replace fixture Trace rows with durable Provider invocation audit.

Revision ID: 20260809_0016
Revises: 20260801_0015
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_0016"
down_revision: str | None = "20260801_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP TRIGGER ai_provider_traces_immutable ON ai_provider_traces")
    op.drop_index("ix_ai_provider_traces_request_created", table_name="ai_provider_traces")
    for constraint in (
        "ck_ai_provider_traces_attempt",
        "ck_ai_provider_traces_status",
        "ck_ai_provider_traces_usage",
        "ck_ai_provider_traces_latency",
        "ck_ai_provider_traces_synthetic_cost",
        "ck_ai_provider_traces_digests",
    ):
        op.drop_constraint(constraint, "ai_provider_traces", type_="check")
    op.drop_constraint("uq_ai_provider_traces_attempt", "ai_provider_traces", type_="unique")
    op.drop_constraint(
        "ai_provider_traces_ai_plan_request_id_fkey",
        "ai_provider_traces",
        type_="foreignkey",
    )
    op.rename_table("ai_provider_traces", "ai_provider_invocations")

    for old_name, legacy_name in (
        ("latency_ms", "legacy_latency_ms"),
        ("input_tokens", "legacy_input_tokens"),
        ("output_tokens", "legacy_output_tokens"),
        ("total_tokens", "legacy_total_tokens"),
        ("cost_estimate_microunits", "legacy_cost_estimate_microunits"),
        ("cost_basis", "legacy_cost_basis"),
        ("retryable", "legacy_retryable"),
    ):
        op.alter_column(
            "ai_provider_invocations",
            old_name,
            new_column_name=legacy_name,
        )

    op.add_column(
        "ai_provider_invocations", sa.Column("contract_version", sa.SmallInteger(), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("classification", sa.String(16), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("adapter_version", sa.String(120), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("requested_model_id", sa.String(120), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations",
        sa.Column("effective_model_status", sa.String(16), nullable=True),
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("effective_model_id", sa.String(120), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations",
        sa.Column("upstream_request_id_status", sa.String(16), nullable=True),
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("upstream_request_id", sa.String(255), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("usage_status", sa.String(24), nullable=True)
    )
    for column in ("input_tokens", "output_tokens", "total_tokens"):
        op.add_column("ai_provider_invocations", sa.Column(column, sa.BigInteger(), nullable=True))
    op.add_column(
        "ai_provider_invocations", sa.Column("queue_wait_ms", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("provider_elapsed_ms", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations",
        sa.Column("client_total_elapsed_ms", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("billing_status", sa.String(32), nullable=True)
    )
    op.add_column(
        "ai_provider_invocations", sa.Column("cost_amount", sa.Numeric(20, 8), nullable=True)
    )
    op.add_column("ai_provider_invocations", sa.Column("cost_currency", sa.CHAR(3), nullable=True))
    op.add_column(
        "ai_provider_invocations",
        sa.Column("dispatch_started_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        UPDATE ai_provider_invocations
        SET contract_version = 0,
            classification = 'fixture',
            adapter_version = COALESCE(
                NULLIF(provider_metadata ->> 'implementation_version', ''),
                'legacy-unknown'
            ),
            requested_model_id = COALESCE(
                NULLIF(provider_metadata ->> 'model_label', ''),
                'legacy-unknown'
            ),
            effective_model_status = 'unavailable',
            effective_model_id = NULL,
            upstream_request_id_status = 'unavailable',
            upstream_request_id = NULL,
            usage_status = CASE
                WHEN status = 'succeeded' THEN 'synthetic_complete'
                ELSE 'unavailable'
            END,
            input_tokens = CASE WHEN status = 'succeeded' THEN legacy_input_tokens END,
            output_tokens = CASE WHEN status = 'succeeded' THEN legacy_output_tokens END,
            total_tokens = CASE WHEN status = 'succeeded' THEN legacy_total_tokens END,
            queue_wait_ms = NULL,
            provider_elapsed_ms = NULL,
            client_total_elapsed_ms = NULL,
            billing_status = 'not_billable_fixture',
            cost_amount = NULL,
            cost_currency = NULL,
            dispatch_started_at = NULL
        """
    )
    for column in (
        "legacy_latency_ms",
        "legacy_input_tokens",
        "legacy_output_tokens",
        "legacy_total_tokens",
        "legacy_cost_estimate_microunits",
        "legacy_cost_basis",
        "legacy_retryable",
    ):
        op.alter_column("ai_provider_invocations", column, nullable=True)

    op.alter_column(
        "ai_provider_invocations",
        "attempt_number",
        existing_type=sa.Integer(),
        type_=sa.SmallInteger(),
        existing_nullable=False,
        postgresql_using="attempt_number::smallint",
    )
    op.alter_column(
        "ai_provider_invocations",
        "status",
        existing_type=sa.String(16),
        type_=sa.String(32),
        existing_nullable=False,
    )
    op.alter_column(
        "ai_provider_invocations",
        "completed_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        nullable=True,
        server_default=None,
    )
    for column in (
        "contract_version",
        "classification",
        "adapter_version",
        "requested_model_id",
        "effective_model_status",
        "upstream_request_id_status",
        "usage_status",
        "billing_status",
    ):
        op.alter_column("ai_provider_invocations", column, nullable=False)
    _create_constraints_and_indexes()
    _install_invocation_guards()


def _create_constraints_and_indexes() -> None:
    op.create_foreign_key(
        "ai_provider_invocations_ai_plan_request_id_fkey",
        "ai_provider_invocations",
        "ai_plan_requests",
        ["ai_plan_request_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_ai_provider_invocations_attempt",
        "ai_provider_invocations",
        ["ai_plan_request_id", "attempt_number"],
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_version_attempt",
        "ai_provider_invocations",
        "(contract_version = 0 AND attempt_number BETWEEN 1 AND 3) OR "
        "(contract_version = 1 AND attempt_number BETWEEN 1 AND 32767)",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_closed_identity",
        "ai_provider_invocations",
        "(contract_version = 0 AND classification = 'fixture' AND "
        "provider_id = 'deterministic-fixture' AND "
        "status IN ('succeeded', 'failed', 'timeout', 'cancelled')) OR "
        "(contract_version = 1 AND classification IN ('fixture', 'mock', 'live') AND "
        "status IN ('prepared', 'dispatching', 'succeeded', 'failed', "
        "'cancelled_before_dispatch', 'outcome_unknown') AND "
        "provider_id IN ('deterministic-fixture', 'zhipu', 'qwen', 'deepseek', "
        "'doubao', 'kimi'))",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_reported_identity",
        "ai_provider_invocations",
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
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_usage",
        "ai_provider_invocations",
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
        "(usage_status = 'unavailable' AND input_tokens IS NULL AND output_tokens IS NULL "
        "AND total_tokens IS NULL))",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_classification_facts",
        "ai_provider_invocations",
        "(classification = 'fixture' AND usage_status IN "
        "('synthetic_complete', 'unavailable') AND billing_status IN "
        "('not_billable_fixture', 'not_dispatched')) OR "
        "(classification = 'mock' AND usage_status IN "
        "('synthetic_complete', 'unavailable') AND billing_status IN "
        "('mock_not_billable', 'not_dispatched')) OR "
        "(classification = 'live' AND usage_status IN "
        "('reported_complete', 'reported_partial', 'reported_invalid', 'unavailable') AND "
        "billing_status IN ('live_billing_unknown', 'live_cost_reported', 'not_dispatched'))",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_billing",
        "ai_provider_invocations",
        "billing_status IN ('not_billable_fixture', 'mock_not_billable', "
        "'live_billing_unknown', 'live_cost_reported', 'not_dispatched') AND ("
        "(billing_status <> 'live_cost_reported' AND cost_amount IS NULL AND "
        "cost_currency IS NULL) OR "
        "(billing_status = 'live_cost_reported' AND cost_amount IS NOT NULL AND "
        "cost_amount >= 0 AND cost_currency ~ '^[A-Z]{3}$')) AND ("
        "billing_status <> 'not_dispatched' OR (contract_version = 1 AND ("
        "status = 'cancelled_before_dispatch' OR "
        "(status = 'failed' AND dispatch_started_at IS NULL))))",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_digests",
        "ai_provider_invocations",
        "request_digest ~ '^[0-9a-f]{64}$' AND "
        "(response_digest IS NULL OR response_digest ~ '^[0-9a-f]{64}$')",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_latency",
        "ai_provider_invocations",
        "(queue_wait_ms IS NULL OR queue_wait_ms >= 0) AND "
        "(provider_elapsed_ms IS NULL OR provider_elapsed_ms >= 0) AND "
        "(client_total_elapsed_ms IS NULL OR client_total_elapsed_ms >= 0)",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_lifecycle",
        "ai_provider_invocations",
        "(contract_version = 0 AND status IN ('succeeded', 'failed', 'timeout', 'cancelled') "
        "AND dispatch_started_at IS NULL AND completed_at IS NOT NULL AND "
        "queue_wait_ms IS NULL AND provider_elapsed_ms IS NULL AND "
        "client_total_elapsed_ms IS NULL) OR (contract_version = 1 AND ((status = 'prepared' "
        "AND dispatch_started_at IS NULL AND completed_at IS NULL AND "
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
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_terminal",
        "ai_provider_invocations",
        "contract_version = 0 OR (contract_version = 1 AND ((status = 'succeeded' AND "
        "response_digest IS NOT NULL AND error_category IS NULL "
        "AND error_code IS NULL) OR "
        "(status IN ('failed', 'cancelled_before_dispatch', 'outcome_unknown') AND "
        "response_digest IS NULL AND error_category IS NOT NULL AND error_code IS NOT NULL) OR "
        "(status IN ('prepared', 'dispatching') AND response_digest IS NULL AND "
        "error_category IS NULL AND error_code IS NULL)))",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_error_category",
        "ai_provider_invocations",
        "contract_version = 0 OR error_category IS NULL OR error_category IN "
        "('provider_not_configured', "
        "'provider_disabled', 'authentication_failed', 'rate_limited', 'timeout', "
        "'cancelled', 'model_unavailable', 'upstream_server_error', 'request_rejected', "
        "'budget_exceeded', 'transport_error', 'structured_output_invalid', 'unavailable', "
        "'invalid_response', 'policy_denied', 'internal')",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_nonterminal_audit",
        "ai_provider_invocations",
        "contract_version = 0 OR status NOT IN ('prepared', 'dispatching') OR "
        "(effective_model_status = 'unavailable' AND effective_model_id IS NULL AND "
        "upstream_request_id_status = 'unavailable' AND upstream_request_id IS NULL AND "
        "usage_status = 'unavailable' AND input_tokens IS NULL AND "
        "output_tokens IS NULL AND total_tokens IS NULL)",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_pre_dispatch_terminal",
        "ai_provider_invocations",
        "contract_version = 0 OR NOT (status = 'cancelled_before_dispatch' OR "
        "(status = 'failed' AND dispatch_started_at IS NULL)) OR ("
        "response_digest IS NULL AND effective_model_status = 'unavailable' AND "
        "effective_model_id IS NULL AND upstream_request_id_status = 'unavailable' AND "
        "upstream_request_id IS NULL AND usage_status = 'unavailable' AND "
        "input_tokens IS NULL AND output_tokens IS NULL AND total_tokens IS NULL AND "
        "queue_wait_ms IS NULL AND provider_elapsed_ms IS NULL AND "
        "billing_status = 'not_dispatched' AND cost_amount IS NULL AND "
        "cost_currency IS NULL)",
    )
    op.create_check_constraint(
        "ck_ai_provider_invocations_legacy_provenance",
        "ai_provider_invocations",
        "(contract_version = 0 AND legacy_latency_ms IS NOT NULL AND "
        "legacy_input_tokens IS NOT NULL AND legacy_output_tokens IS NOT NULL AND "
        "legacy_total_tokens IS NOT NULL AND legacy_cost_estimate_microunits IS NOT NULL AND "
        "legacy_cost_basis IS NOT NULL AND legacy_retryable IS NOT NULL AND "
        "legacy_latency_ms >= 0 AND legacy_input_tokens >= 0 AND "
        "legacy_output_tokens >= 0 AND legacy_total_tokens = legacy_input_tokens + "
        "legacy_output_tokens AND legacy_cost_estimate_microunits = 0 AND "
        "legacy_cost_basis = 'synthetic_not_billable') OR "
        "(contract_version = 1 AND legacy_latency_ms IS NULL AND "
        "legacy_input_tokens IS NULL AND legacy_output_tokens IS NULL AND "
        "legacy_total_tokens IS NULL AND legacy_cost_estimate_microunits IS NULL AND "
        "legacy_cost_basis IS NULL AND legacy_retryable IS NULL)",
    )
    op.create_index(
        "ix_ai_provider_invocations_provider_class_created",
        "ai_provider_invocations",
        ["provider_id", "classification", "created_at"],
    )
    op.create_index(
        "ix_ai_provider_invocations_recovery",
        "ai_provider_invocations",
        ["status", "dispatch_started_at"],
        postgresql_where=sa.text(
            "contract_version = 1 AND status = 'dispatching' AND dispatch_started_at IS NOT NULL"
        ),
    )
    op.create_index(
        "ix_ai_provider_invocations_upstream",
        "ai_provider_invocations",
        ["provider_id", "upstream_request_id"],
        postgresql_where=sa.text("upstream_request_id_status = 'reported'"),
    )


def _install_invocation_guards() -> None:
    op.execute(
        """
        CREATE FUNCTION guard_ai_provider_invocation_insert()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.contract_version <> 1 OR NEW.status <> 'prepared' THEN
                RAISE EXCEPTION 'Provider invocation must begin prepared'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE FUNCTION guard_ai_provider_invocation_update()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.contract_version <> 1
                OR OLD.status IN ('succeeded', 'failed', 'cancelled_before_dispatch',
                    'outcome_unknown')
                OR NEW.id IS DISTINCT FROM OLD.id
                OR NEW.ai_plan_request_id IS DISTINCT FROM OLD.ai_plan_request_id
                OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
                OR NEW.contract_version IS DISTINCT FROM OLD.contract_version
                OR NEW.classification IS DISTINCT FROM OLD.classification
                OR NEW.provider_id IS DISTINCT FROM OLD.provider_id
                OR NEW.provider_metadata IS DISTINCT FROM OLD.provider_metadata
                OR NEW.redactions IS DISTINCT FROM OLD.redactions
                OR NEW.adapter_version IS DISTINCT FROM OLD.adapter_version
                OR NEW.requested_model_id IS DISTINCT FROM OLD.requested_model_id
                OR NEW.request_digest IS DISTINCT FROM OLD.request_digest
                OR NEW.created_at IS DISTINCT FROM OLD.created_at
                OR (OLD.dispatch_started_at IS NOT NULL AND
                    NEW.dispatch_started_at IS DISTINCT FROM OLD.dispatch_started_at)
                OR (OLD.queue_wait_ms IS NOT NULL AND
                    NEW.queue_wait_ms IS DISTINCT FROM OLD.queue_wait_ms)
                OR (OLD.status = 'prepared'
                    AND NEW.status IN ('failed', 'cancelled_before_dispatch')
                    AND (NEW.dispatch_started_at IS NOT NULL
                        OR NEW.queue_wait_ms IS NOT NULL
                        OR NEW.provider_elapsed_ms IS NOT NULL
                        OR NEW.response_digest IS NOT NULL
                        OR NEW.effective_model_status <> 'unavailable'
                        OR NEW.effective_model_id IS NOT NULL
                        OR NEW.upstream_request_id_status <> 'unavailable'
                        OR NEW.upstream_request_id IS NOT NULL
                        OR NEW.usage_status <> 'unavailable'
                        OR NEW.input_tokens IS NOT NULL
                        OR NEW.output_tokens IS NOT NULL
                        OR NEW.total_tokens IS NOT NULL
                        OR NEW.billing_status <> 'not_dispatched'
                        OR NEW.cost_amount IS NOT NULL
                        OR NEW.cost_currency IS NOT NULL))
                OR NOT (
                    (OLD.status = 'prepared' AND NEW.status IN
                        ('dispatching', 'failed', 'cancelled_before_dispatch'))
                    OR (OLD.status = 'dispatching' AND NEW.status IN
                        ('succeeded', 'failed', 'outcome_unknown'))
                )
            THEN
                RAISE EXCEPTION 'Provider invocation mutation is forbidden'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER ai_provider_invocations_insert_guard
        BEFORE INSERT ON ai_provider_invocations
        FOR EACH ROW EXECUTE FUNCTION guard_ai_provider_invocation_insert();

        CREATE TRIGGER ai_provider_invocations_update_guard
        BEFORE UPDATE ON ai_provider_invocations
        FOR EACH ROW EXECUTE FUNCTION guard_ai_provider_invocation_update();

        CREATE TRIGGER ai_provider_invocations_delete_guard
        BEFORE DELETE ON ai_provider_invocations
        FOR EACH ROW EXECUTE FUNCTION reject_ai_evidence_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM ai_provider_invocations
                WHERE contract_version <> 0
            ) THEN
                RAISE EXCEPTION 'downgrade would lose provider invocation audit semantics'
                    USING ERRCODE = '55000';
            END IF;
        END;
        $$;
        """
    )
    op.execute("DROP TRIGGER ai_provider_invocations_delete_guard ON ai_provider_invocations")
    op.execute("DROP TRIGGER ai_provider_invocations_update_guard ON ai_provider_invocations")
    op.execute("DROP TRIGGER ai_provider_invocations_insert_guard ON ai_provider_invocations")
    op.execute("DROP FUNCTION guard_ai_provider_invocation_update()")
    op.execute("DROP FUNCTION guard_ai_provider_invocation_insert()")
    for index in (
        "ix_ai_provider_invocations_upstream",
        "ix_ai_provider_invocations_recovery",
        "ix_ai_provider_invocations_provider_class_created",
    ):
        op.drop_index(index, table_name="ai_provider_invocations")
    for constraint in (
        "ck_ai_provider_invocations_legacy_provenance",
        "ck_ai_provider_invocations_pre_dispatch_terminal",
        "ck_ai_provider_invocations_nonterminal_audit",
        "ck_ai_provider_invocations_error_category",
        "ck_ai_provider_invocations_terminal",
        "ck_ai_provider_invocations_lifecycle",
        "ck_ai_provider_invocations_latency",
        "ck_ai_provider_invocations_digests",
        "ck_ai_provider_invocations_billing",
        "ck_ai_provider_invocations_classification_facts",
        "ck_ai_provider_invocations_usage",
        "ck_ai_provider_invocations_reported_identity",
        "ck_ai_provider_invocations_closed_identity",
        "ck_ai_provider_invocations_version_attempt",
    ):
        op.drop_constraint(constraint, "ai_provider_invocations", type_="check")
    op.drop_constraint(
        "uq_ai_provider_invocations_attempt", "ai_provider_invocations", type_="unique"
    )
    op.drop_constraint(
        "ai_provider_invocations_ai_plan_request_id_fkey",
        "ai_provider_invocations",
        type_="foreignkey",
    )

    for column in ("input_tokens", "output_tokens", "total_tokens"):
        op.drop_column("ai_provider_invocations", column)
    for column in (
        "legacy_latency_ms",
        "legacy_input_tokens",
        "legacy_output_tokens",
        "legacy_total_tokens",
        "legacy_cost_estimate_microunits",
        "legacy_cost_basis",
        "legacy_retryable",
    ):
        op.alter_column("ai_provider_invocations", column, nullable=False)
    for legacy_name, old_name in (
        ("legacy_latency_ms", "latency_ms"),
        ("legacy_input_tokens", "input_tokens"),
        ("legacy_output_tokens", "output_tokens"),
        ("legacy_total_tokens", "total_tokens"),
        ("legacy_cost_estimate_microunits", "cost_estimate_microunits"),
        ("legacy_cost_basis", "cost_basis"),
        ("legacy_retryable", "retryable"),
    ):
        op.alter_column(
            "ai_provider_invocations",
            legacy_name,
            new_column_name=old_name,
        )
    op.alter_column(
        "ai_provider_invocations",
        "attempt_number",
        existing_type=sa.SmallInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="attempt_number::integer",
    )
    op.alter_column(
        "ai_provider_invocations",
        "status",
        existing_type=sa.String(32),
        type_=sa.String(16),
        existing_nullable=False,
    )
    op.alter_column(
        "ai_provider_invocations",
        "completed_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    for column in (
        "dispatch_started_at",
        "cost_currency",
        "cost_amount",
        "billing_status",
        "client_total_elapsed_ms",
        "provider_elapsed_ms",
        "queue_wait_ms",
        "usage_status",
        "upstream_request_id",
        "upstream_request_id_status",
        "effective_model_id",
        "effective_model_status",
        "requested_model_id",
        "adapter_version",
        "classification",
        "contract_version",
    ):
        op.drop_column("ai_provider_invocations", column)

    op.rename_table("ai_provider_invocations", "ai_provider_traces")
    op.create_foreign_key(
        "ai_provider_traces_ai_plan_request_id_fkey",
        "ai_provider_traces",
        "ai_plan_requests",
        ["ai_plan_request_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_ai_provider_traces_attempt",
        "ai_provider_traces",
        ["ai_plan_request_id", "attempt_number"],
    )
    op.create_check_constraint(
        "ck_ai_provider_traces_attempt",
        "ai_provider_traces",
        "attempt_number BETWEEN 1 AND 3",
    )
    op.create_check_constraint(
        "ck_ai_provider_traces_status",
        "ai_provider_traces",
        "status IN ('succeeded', 'failed', 'timeout', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_ai_provider_traces_usage",
        "ai_provider_traces",
        "input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0 AND "
        "total_tokens = input_tokens + output_tokens AND cost_estimate_microunits >= 0",
    )
    op.create_check_constraint(
        "ck_ai_provider_traces_latency", "ai_provider_traces", "latency_ms >= 0"
    )
    op.create_check_constraint(
        "ck_ai_provider_traces_synthetic_cost",
        "ai_provider_traces",
        "cost_basis = 'synthetic_not_billable' AND cost_estimate_microunits = 0",
    )
    op.create_check_constraint(
        "ck_ai_provider_traces_digests",
        "ai_provider_traces",
        "request_digest ~ '^[0-9a-f]{64}$' AND "
        "(response_digest IS NULL OR response_digest ~ '^[0-9a-f]{64}$')",
    )
    op.create_index(
        "ix_ai_provider_traces_request_created",
        "ai_provider_traces",
        ["ai_plan_request_id", "created_at"],
    )
    op.execute(
        """
        CREATE TRIGGER ai_provider_traces_immutable
        BEFORE UPDATE OR DELETE ON ai_provider_traces
        FOR EACH ROW EXECUTE FUNCTION reject_ai_evidence_mutation();
        """
    )
