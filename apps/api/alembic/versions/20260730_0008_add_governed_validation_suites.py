"""Add governed multi-step Validation Suites.

Revision ID: 20260730_0008
Revises: 20260729_0007
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_0008"
down_revision: str | None = "20260729_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_validation_profile", "validation_runs", type_="check")
    op.create_check_constraint(
        "ck_validation_profile",
        "validation_runs",
        "profile_id IN ('fixture-python-stdlib-v1', 'fixture-python-manifest-v1')",
    )
    op.drop_constraint(
        "ck_validation_step_id",
        "validation_step_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_validation_step_id",
        "validation_step_runs",
        "step_id IN ('fixture-contract', 'fixture-manifest')",
    )

    op.add_column(
        "execution_grants",
        sa.Column(
            "allowed_validation_suites",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_grants_validation_suite_scope",
        "execution_grants",
        "jsonb_typeof(allowed_validation_suites) = 'array' "
        "AND jsonb_array_length(allowed_validation_suites) BETWEEN 0 AND 1 "
        "AND allowed_validation_suites <@ "
        "'[\"fixture-integrity-suite-v1:v1\"]'::jsonb",
    )

    op.create_table(
        "validation_suite_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("execution_grant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_id", sa.String(length=64), nullable=False),
        sa.Column("suite_version", sa.Integer(), nullable=False),
        sa.Column("policy_digest", sa.String(length=64), nullable=False),
        sa.Column("failure_policy", sa.String(length=24), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("step_count", sa.Integer(), nullable=False),
        sa.Column("completed_step_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("total_output_bytes", sa.Integer(), nullable=False),
        sa.Column("combined_output_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "retry_of_suite_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("idempotency_request_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
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
            "attempt_number BETWEEN 1 AND max_attempts AND max_attempts BETWEEN 1 AND 5",
            name="ck_validation_suite_attempt_budget",
        ),
        sa.CheckConstraint(
            "combined_output_bytes BETWEEN 0 AND 262144",
            name="ck_validation_suite_output_consumption",
        ),
        sa.CheckConstraint(
            "failure_policy = 'fail_fast'",
            name="ck_validation_suite_failure_policy",
        ),
        sa.CheckConstraint(
            "idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_validation_suite_idempotency_hash",
        ),
        sa.CheckConstraint(
            "suite_id = 'fixture-integrity-suite-v1'",
            name="ck_validation_suite_id",
        ),
        sa.CheckConstraint(
            "policy_digest ~ '^[0-9a-f]{64}$'",
            name="ck_validation_suite_policy_digest",
        ),
        sa.CheckConstraint(
            "(attempt_number = 1 AND retry_of_suite_run_id IS NULL) OR "
            "(attempt_number > 1 AND retry_of_suite_run_id IS NOT NULL)",
            name="ck_validation_suite_retry_binding",
        ),
        sa.CheckConstraint(
            "state IN ('requested', 'queued', 'running', 'cancel_requested', "
            "'succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required')",
            name="ck_validation_suite_state",
        ),
        sa.CheckConstraint(
            "completed_step_count BETWEEN 0 AND step_count AND step_count BETWEEN 2 AND 16",
            name="ck_validation_suite_step_count",
        ),
        sa.CheckConstraint(
            "(state IN ('succeeded', 'failed', 'timed_out', 'cancelled', "
            "'recovery_required')) = (completed_at IS NOT NULL)",
            name="ck_validation_suite_terminal_timestamp",
        ),
        sa.CheckConstraint(
            "total_output_bytes BETWEEN 256 AND 262144",
            name="ck_validation_suite_output_budget",
        ),
        sa.CheckConstraint(
            "total_timeout_seconds BETWEEN 1 AND 600",
            name="ck_validation_suite_timeout",
        ),
        sa.CheckConstraint(
            "suite_version = 1",
            name="ck_validation_suite_version",
        ),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"],
            ["workspace_checkpoints.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_grant_id"],
            ["execution_grants.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["retry_of_suite_run_id"],
            ["validation_suite_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_validation_suite_runs_idempotency_key",
        ),
        sa.UniqueConstraint(
            "retry_of_suite_run_id",
            "attempt_number",
            name="uq_validation_suite_runs_retry_attempt",
        ),
    )
    op.create_index(
        "ix_validation_suite_runs_state_created",
        "validation_suite_runs",
        ["state", "created_at"],
    )
    op.create_index(
        "ix_validation_suite_runs_workspace_created",
        "validation_suite_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_validation_suite_runs_grant_created",
        "validation_suite_runs",
        ["execution_grant_id", "created_at"],
    )

    op.create_table(
        "validation_suite_step_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=False),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_output_bytes", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("validation_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("runner_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "reused_from_step_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("output_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("redaction_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_truncated", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("cleanup_succeeded", sa.Boolean(), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "exit_code IS NULL OR exit_code BETWEEN 0 AND 255",
            name="ck_validation_suite_step_exit_code",
        ),
        sa.CheckConstraint(
            "output_bytes BETWEEN 0 AND 65536",
            name="ck_validation_suite_step_output_consumption",
        ),
        sa.CheckConstraint(
            "max_output_bytes BETWEEN 256 AND 65536",
            name="ck_validation_suite_step_output_budget",
        ),
        sa.CheckConstraint(
            "profile_id IN ('fixture-python-stdlib-v1', 'fixture-python-manifest-v1')",
            name="ck_validation_suite_step_profile",
        ),
        sa.CheckConstraint(
            "profile_version = 1",
            name="ck_validation_suite_step_profile_version",
        ),
        sa.CheckConstraint(
            "(reused_from_step_run_id IS NULL) OR "
            "(state = 'succeeded' AND validation_run_id IS NOT NULL "
            "AND evidence_id IS NOT NULL)",
            name="ck_validation_suite_step_reuse",
        ),
        sa.CheckConstraint(
            "sequence BETWEEN 1 AND 16",
            name="ck_validation_suite_step_sequence",
        ),
        sa.CheckConstraint(
            "step_id IN ('fixture-contract', 'fixture-manifest')",
            name="ck_validation_suite_step_id",
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'queued', 'running', 'succeeded', 'failed', "
            "'timed_out', 'cancelled', 'skipped', 'recovery_required')",
            name="ck_validation_suite_step_state",
        ),
        sa.CheckConstraint(
            "(state IN ('succeeded', 'failed', 'timed_out', 'cancelled', "
            "'skipped', 'recovery_required')) = (completed_at IS NOT NULL)",
            name="ck_validation_suite_step_terminal_timestamp",
        ),
        sa.CheckConstraint(
            "timeout_seconds BETWEEN 1 AND 120",
            name="ck_validation_suite_step_timeout",
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["runner_job_attempts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["validation_evidence.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reused_from_step_run_id"],
            ["validation_suite_step_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["runner_id"],
            ["runners.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["runner_job_id"],
            ["runner_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["suite_run_id"],
            ["validation_suite_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["validation_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "suite_run_id",
            "step_id",
            name="uq_validation_suite_steps_id",
        ),
        sa.UniqueConstraint(
            "suite_run_id",
            "sequence",
            name="uq_validation_suite_steps_sequence",
        ),
    )
    op.create_index(
        "ix_validation_suite_steps_run",
        "validation_suite_step_runs",
        ["suite_run_id", "sequence"],
    )
    op.create_index(
        "ix_validation_suite_steps_validation_run",
        "validation_suite_step_runs",
        ["validation_run_id"],
    )

    op.create_table(
        "validation_suite_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verdict", sa.String(length=24), nullable=False),
        sa.Column(
            "profile_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "evidence_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "audit_event_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("combined_output_bytes", sa.Integer(), nullable=False),
        sa.Column("redaction_count", sa.Integer(), nullable=False),
        sa.Column("output_truncated", sa.Boolean(), nullable=False),
        sa.Column("timed_out", sa.Boolean(), nullable=False),
        sa.Column("cancelled", sa.Boolean(), nullable=False),
        sa.Column("recovery_required", sa.Boolean(), nullable=False),
        sa.Column("cleanup_succeeded", sa.Boolean(), nullable=False),
        sa.Column("source_invariant", sa.Boolean(), nullable=False),
        sa.Column("canonical_workspace_invariant", sa.Boolean(), nullable=False),
        sa.Column("artifact_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("artifact_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("aggregate_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "aggregate_digest ~ '^[0-9a-f]{64}$'",
            name="ck_validation_suite_result_digest",
        ),
        sa.CheckConstraint(
            "combined_output_bytes >= 0 AND redaction_count >= 0",
            name="ck_validation_suite_result_consumption",
        ),
        sa.CheckConstraint(
            "verdict IN ('succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required')",
            name="ck_validation_suite_result_verdict",
        ),
        sa.CheckConstraint(
            "artifact_count = 0 AND artifact_bytes = 0",
            name="ck_validation_suite_result_zero_artifacts",
        ),
        sa.ForeignKeyConstraint(
            ["suite_run_id"],
            ["validation_suite_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "suite_run_id",
            name="uq_validation_suite_results_run",
        ),
    )

    op.execute(
        """
        CREATE FUNCTION protect_validation_suite_run()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'validation Suite runs cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF (
                to_jsonb(NEW)
                - 'state' - 'completed_step_count' - 'combined_output_bytes'
                - 'started_at' - 'deadline_at' - 'cancel_requested_at'
                - 'completed_at' - 'error_code' - 'error_message'
                - 'version' - 'updated_at'
            ) IS DISTINCT FROM (
                to_jsonb(OLD)
                - 'state' - 'completed_step_count' - 'combined_output_bytes'
                - 'started_at' - 'deadline_at' - 'cancel_requested_at'
                - 'completed_at' - 'error_code' - 'error_message'
                - 'version' - 'updated_at'
            ) THEN
                RAISE EXCEPTION 'validation Suite authority is immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF OLD.state IN (
                'succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required'
            ) AND to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD) THEN
                RAISE EXCEPTION 'terminal validation Suite run is immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF OLD.state <> NEW.state AND NOT (
                (OLD.state = 'requested' AND NEW.state IN (
                    'queued', 'cancelled', 'recovery_required'
                )) OR
                (OLD.state = 'queued' AND NEW.state IN (
                    'running', 'cancel_requested', 'succeeded', 'failed', 'timed_out',
                    'cancelled', 'recovery_required'
                )) OR
                (OLD.state = 'running' AND NEW.state IN (
                    'cancel_requested', 'succeeded', 'failed', 'timed_out',
                    'cancelled', 'recovery_required'
                )) OR
                (OLD.state = 'cancel_requested' AND NEW.state IN (
                    'timed_out', 'cancelled', 'recovery_required'
                ))
            ) THEN
                RAISE EXCEPTION 'illegal validation Suite transition'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.state = 'succeeded'
                AND NEW.combined_output_bytes > NEW.total_output_bytes THEN
                RAISE EXCEPTION 'successful validation Suite exceeds output budget'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER validation_suite_run_guard
        BEFORE UPDATE OR DELETE ON validation_suite_runs
        FOR EACH ROW EXECUTE FUNCTION protect_validation_suite_run()
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_validation_suite_step()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'validation Suite steps cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF (
                to_jsonb(NEW)
                - 'state' - 'validation_run_id' - 'runner_job_id' - 'runner_id'
                - 'attempt_id' - 'lease_id' - 'evidence_id'
                - 'reused_from_step_run_id' - 'started_at' - 'completed_at'
                - 'duration_ms' - 'exit_code' - 'output_bytes'
                - 'redaction_count' - 'output_truncated' - 'cleanup_succeeded'
                - 'failure_code'
            ) IS DISTINCT FROM (
                to_jsonb(OLD)
                - 'state' - 'validation_run_id' - 'runner_job_id' - 'runner_id'
                - 'attempt_id' - 'lease_id' - 'evidence_id'
                - 'reused_from_step_run_id' - 'started_at' - 'completed_at'
                - 'duration_ms' - 'exit_code' - 'output_bytes'
                - 'redaction_count' - 'output_truncated' - 'cleanup_succeeded'
                - 'failure_code'
            ) THEN
                RAISE EXCEPTION 'validation Suite step definition is immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF OLD.state IN (
                'succeeded', 'failed', 'timed_out', 'cancelled', 'skipped',
                'recovery_required'
            ) AND to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD) THEN
                RAISE EXCEPTION 'terminal validation Suite step is immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.state = 'succeeded'
                AND NEW.output_bytes > NEW.max_output_bytes THEN
                RAISE EXCEPTION 'successful validation Suite step exceeds output budget'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER validation_suite_step_guard
        BEFORE UPDATE OR DELETE ON validation_suite_step_runs
        FOR EACH ROW EXECUTE FUNCTION protect_validation_suite_step()
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_validation_suite_result()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'validation Suite results are immutable'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER validation_suite_result_immutable
        BEFORE UPDATE OR DELETE ON validation_suite_results
        FOR EACH ROW EXECUTE FUNCTION protect_validation_suite_result()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER validation_suite_result_immutable ON validation_suite_results")
    op.execute("DROP FUNCTION protect_validation_suite_result()")
    op.execute("DROP TRIGGER validation_suite_step_guard ON validation_suite_step_runs")
    op.execute("DROP FUNCTION protect_validation_suite_step()")
    op.execute("DROP TRIGGER validation_suite_run_guard ON validation_suite_runs")
    op.execute("DROP FUNCTION protect_validation_suite_run()")
    op.drop_table("validation_suite_results")
    op.drop_index(
        "ix_validation_suite_steps_validation_run",
        table_name="validation_suite_step_runs",
    )
    op.drop_index(
        "ix_validation_suite_steps_run",
        table_name="validation_suite_step_runs",
    )
    op.drop_table("validation_suite_step_runs")
    op.drop_index(
        "ix_validation_suite_runs_grant_created",
        table_name="validation_suite_runs",
    )
    op.drop_index(
        "ix_validation_suite_runs_workspace_created",
        table_name="validation_suite_runs",
    )
    op.drop_index(
        "ix_validation_suite_runs_state_created",
        table_name="validation_suite_runs",
    )
    op.drop_table("validation_suite_runs")
    op.drop_constraint(
        "ck_grants_validation_suite_scope",
        "execution_grants",
        type_="check",
    )
    op.drop_column("execution_grants", "allowed_validation_suites")
    op.drop_constraint(
        "ck_validation_step_id",
        "validation_step_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_validation_step_id",
        "validation_step_runs",
        "step_id = 'fixture-contract'",
    )
    op.drop_constraint("ck_validation_profile", "validation_runs", type_="check")
    op.create_check_constraint(
        "ck_validation_profile",
        "validation_runs",
        "profile_id = 'fixture-python-stdlib-v1'",
    )
