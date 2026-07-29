"""Add governed fixture Validation Runs and immutable evidence.

Revision ID: 20260729_0006
Revises: 20260728_0005
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260729_0006"
down_revision: str | None = "20260728_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "execution_grants",
        sa.Column("validation_workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "execution_grants",
        sa.Column("validation_checkpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "execution_grants",
        sa.Column(
            "allowed_validation_profiles",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    for name in (
        "max_validation_runs",
        "validation_timeout_seconds",
        "validation_cpu_seconds",
        "validation_memory_bytes",
        "validation_pid_limit",
        "validation_fd_limit",
        "validation_output_bytes",
        "validation_artifact_bytes",
        "validation_artifact_count",
    ):
        op.add_column(
            "execution_grants",
            sa.Column(name, sa.Integer(), server_default="0", nullable=False),
        )
    op.create_foreign_key(
        "fk_execution_grants_validation_workspace",
        "execution_grants",
        "workspaces",
        ["validation_workspace_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_execution_grants_validation_checkpoint",
        "execution_grants",
        "workspace_checkpoints",
        ["validation_checkpoint_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_grants_validation_scope",
        "execution_grants",
        "("
        "validation_checkpoint_id IS NOT NULL "
        "AND validation_workspace_id IS NOT NULL "
        "AND allowed_operations = '[\"validate\"]'::jsonb "
        "AND jsonb_array_length(allowed_validation_profiles) BETWEEN 1 AND 4 "
        "AND max_validation_runs BETWEEN 1 AND 10 "
        "AND validation_timeout_seconds BETWEEN 1 AND 120 "
        "AND validation_cpu_seconds BETWEEN 1 AND 120 "
        "AND validation_memory_bytes BETWEEN 1048576 AND 1073741824 "
        "AND validation_pid_limit BETWEEN 1 AND 64 "
        "AND validation_fd_limit BETWEEN 1 AND 256 "
        "AND validation_output_bytes BETWEEN 256 AND 65536 "
        "AND validation_artifact_bytes BETWEEN 0 AND 1048576 "
        "AND validation_artifact_count BETWEEN 0 AND 20"
        ") OR ("
        "validation_checkpoint_id IS NULL "
        "AND validation_workspace_id IS NULL "
        "AND allowed_validation_profiles = '[]'::jsonb "
        "AND max_validation_runs = 0 "
        "AND validation_timeout_seconds = 0 "
        "AND validation_cpu_seconds = 0 "
        "AND validation_memory_bytes = 0 "
        "AND validation_pid_limit = 0 "
        "AND validation_fd_limit = 0 "
        "AND validation_output_bytes = 0 "
        "AND validation_artifact_bytes = 0 "
        "AND validation_artifact_count = 0"
        ")",
    )

    op.drop_constraint("ck_runner_jobs_kind", "runner_jobs", type_="check")
    op.create_check_constraint(
        "ck_runner_jobs_kind",
        "runner_jobs",
        "kind IN ('system_diagnostic_v1', 'controlled_wait_v1', "
        "'workspace_prepare_v1', 'workspace_list_v1', 'workspace_read_text_v1', "
        "'workspace_write_text_v1', 'workspace_status_v1', 'workspace_diff_v1', "
        "'workspace_rollback_v1', 'workspace_discard_v1', 'validation_execute_v1')",
    )
    op.drop_constraint("ck_runner_jobs_workspace_binding", "runner_jobs", type_="check")
    op.create_check_constraint(
        "ck_runner_jobs_workspace_binding",
        "runner_jobs",
        "(kind IN ('system_diagnostic_v1', 'controlled_wait_v1') "
        "AND execution_grant_id IS NULL AND workspace_id IS NULL "
        "AND repository_handle_id IS NULL AND source_revision IS NULL "
        "AND execution_policy_hash IS NULL) OR "
        "(kind NOT IN ('system_diagnostic_v1', 'controlled_wait_v1') "
        "AND execution_grant_id IS NOT NULL AND workspace_id IS NOT NULL "
        "AND repository_handle_id IS NOT NULL AND source_revision IS NOT NULL "
        "AND execution_policy_hash IS NOT NULL)",
    )
    op.drop_constraint("ck_side_effect_permits_operation", "side_effect_permits", type_="check")
    op.create_check_constraint(
        "ck_side_effect_permits_operation",
        "side_effect_permits",
        "operation IN ('prepare', 'write_text', 'rollback', 'discard', 'validate')",
    )

    op.create_table(
        "validation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("execution_grant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runner_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("policy_digest", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_output_bytes", sa.Integer(), nullable=False),
        sa.Column("max_artifact_bytes", sa.Integer(), nullable=False),
        sa.Column("max_artifact_count", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("idempotency_request_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
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
            "(attempt_id IS NULL AND lease_id IS NULL) OR "
            "(attempt_id IS NOT NULL AND lease_id IS NOT NULL)",
            name="ck_validation_attempt_lease_pair",
        ),
        sa.CheckConstraint(
            "max_artifact_bytes BETWEEN 0 AND 1048576 AND max_artifact_count BETWEEN 0 AND 20",
            name="ck_validation_artifact_budget",
        ),
        sa.CheckConstraint(
            "idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_validation_idempotency_hash",
        ),
        sa.CheckConstraint(
            "max_output_bytes BETWEEN 256 AND 65536",
            name="ck_validation_output_budget",
        ),
        sa.CheckConstraint("policy_digest ~ '^[0-9a-f]{64}$'", name="ck_validation_policy_digest"),
        sa.CheckConstraint("profile_id = 'fixture-python-stdlib-v1'", name="ck_validation_profile"),
        sa.CheckConstraint("profile_version = 1", name="ck_validation_profile_version"),
        sa.CheckConstraint(
            "state IN ('requested', 'queued', 'claimed', 'running', 'cancel_requested', "
            "'succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required')",
            name="ck_validation_runs_state",
        ),
        sa.CheckConstraint(
            "(state IN ('succeeded', 'failed', 'timed_out', 'cancelled', "
            "'recovery_required')) = (completed_at IS NOT NULL)",
            name="ck_validation_terminal_timestamp",
        ),
        sa.CheckConstraint("timeout_seconds BETWEEN 1 AND 120", name="ck_validation_timeout"),
        sa.ForeignKeyConstraint(["attempt_id"], ["runner_job_attempts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"], ["workspace_checkpoints.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["execution_grant_id"], ["execution_grants.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["runner_job_id"], ["runner_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_validation_runs_idempotency_key"),
        sa.UniqueConstraint("runner_job_id", name="uq_validation_runs_runner_job"),
    )
    op.create_index(
        "ix_validation_runs_state_created",
        "validation_runs",
        ["state", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_runs_workspace_created",
        "validation_runs",
        ["workspace_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_validation_runs_grant_created",
        "validation_runs",
        ["execution_grant_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "validation_step_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("step_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "exit_code IS NULL OR exit_code BETWEEN 0 AND 255",
            name="ck_validation_step_exit_code",
        ),
        sa.CheckConstraint("step_id = 'fixture-contract'", name="ck_validation_step_id"),
        sa.CheckConstraint("sequence = 1", name="ck_validation_steps_sequence"),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'succeeded', 'failed', 'timed_out', "
            "'cancelled', 'recovery_required')",
            name="ck_validation_steps_state",
        ),
        sa.ForeignKeyConstraint(["validation_run_id"], ["validation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("validation_run_id", "sequence", name="uq_validation_steps_sequence"),
    )
    op.create_index(
        "ix_validation_steps_run",
        "validation_step_runs",
        ["validation_run_id", "sequence"],
        unique=False,
    )

    op.create_table(
        "validation_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fixed_argv", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False),
        sa.Column("stdout", sa.Text(), nullable=False),
        sa.Column("stderr", sa.Text(), nullable=False),
        sa.Column("stdout_truncated", sa.Boolean(), nullable=False),
        sa.Column("stderr_truncated", sa.Boolean(), nullable=False),
        sa.Column("redaction_count", sa.Integer(), nullable=False),
        sa.Column("timed_out", sa.Boolean(), nullable=False),
        sa.Column("cancelled", sa.Boolean(), nullable=False),
        sa.Column("network_isolated", sa.Boolean(), nullable=False),
        sa.Column("filesystem_isolated", sa.Boolean(), nullable=False),
        sa.Column("sandbox_cleaned", sa.Boolean(), nullable=False),
        sa.Column("artifact_count", sa.Integer(), nullable=False),
        sa.Column("artifact_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "artifact_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("side_effect_permit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "artifact_count BETWEEN 0 AND 20 AND artifact_bytes BETWEEN 0 AND 1048576",
            name="ck_validation_evidence_artifacts",
        ),
        sa.CheckConstraint("duration_ms >= 0", name="ck_validation_evidence_duration"),
        sa.CheckConstraint("exit_code BETWEEN 0 AND 255", name="ck_validation_evidence_exit"),
        sa.CheckConstraint("redaction_count >= 0", name="ck_validation_evidence_redactions"),
        sa.ForeignKeyConstraint(["attempt_id"], ["runner_job_attempts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["side_effect_permit_id"], ["side_effect_permits.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["validation_run_id"], ["validation_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "validation_run_id",
            "attempt_id",
            "lease_id",
            name="uq_validation_evidence_fencing",
        ),
        sa.UniqueConstraint("validation_run_id", name="uq_validation_evidence_run"),
    )

    op.execute(
        """
        CREATE FUNCTION protect_validation_run_authority()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'validation runs cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF (
                to_jsonb(NEW)
                - 'runner_job_id' - 'runner_id' - 'attempt_id' - 'lease_id'
                - 'state' - 'claimed_at' - 'started_at' - 'cancel_requested_at'
                - 'completed_at' - 'error_code' - 'error_message'
                - 'version' - 'updated_at'
            ) IS DISTINCT FROM (
                to_jsonb(OLD)
                - 'runner_job_id' - 'runner_id' - 'attempt_id' - 'lease_id'
                - 'state' - 'claimed_at' - 'started_at' - 'cancel_requested_at'
                - 'completed_at' - 'error_code' - 'error_message'
                - 'version' - 'updated_at'
            ) THEN
                RAISE EXCEPTION 'validation run authority is immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF OLD.state IN (
                'succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required'
            ) AND to_jsonb(NEW) IS DISTINCT FROM to_jsonb(OLD) THEN
                RAISE EXCEPTION 'terminal validation run is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER validation_run_authority_immutable
        BEFORE UPDATE OR DELETE ON validation_runs
        FOR EACH ROW EXECUTE FUNCTION protect_validation_run_authority()
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_validation_evidence()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'validation evidence is immutable'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER validation_evidence_immutable
        BEFORE UPDATE OR DELETE ON validation_evidence
        FOR EACH ROW EXECUTE FUNCTION protect_validation_evidence()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER validation_evidence_immutable ON validation_evidence")
    op.execute("DROP FUNCTION protect_validation_evidence()")
    op.execute("DROP TRIGGER validation_run_authority_immutable ON validation_runs")
    op.execute("DROP FUNCTION protect_validation_run_authority()")
    op.drop_table("validation_evidence")
    op.drop_index("ix_validation_steps_run", table_name="validation_step_runs")
    op.drop_table("validation_step_runs")
    op.drop_index("ix_validation_runs_grant_created", table_name="validation_runs")
    op.drop_index("ix_validation_runs_workspace_created", table_name="validation_runs")
    op.drop_index("ix_validation_runs_state_created", table_name="validation_runs")
    op.drop_table("validation_runs")

    op.drop_constraint("ck_side_effect_permits_operation", "side_effect_permits", type_="check")
    op.create_check_constraint(
        "ck_side_effect_permits_operation",
        "side_effect_permits",
        "operation IN ('prepare', 'write_text', 'rollback', 'discard')",
    )
    op.drop_constraint("ck_runner_jobs_workspace_binding", "runner_jobs", type_="check")
    op.create_check_constraint(
        "ck_runner_jobs_workspace_binding",
        "runner_jobs",
        "(kind IN ('system_diagnostic_v1', 'controlled_wait_v1') "
        "AND execution_grant_id IS NULL AND workspace_id IS NULL "
        "AND repository_handle_id IS NULL AND source_revision IS NULL "
        "AND execution_policy_hash IS NULL) OR "
        "(kind LIKE 'workspace_%' AND execution_grant_id IS NOT NULL "
        "AND workspace_id IS NOT NULL AND repository_handle_id IS NOT NULL "
        "AND source_revision IS NOT NULL AND execution_policy_hash IS NOT NULL)",
    )
    op.drop_constraint("ck_runner_jobs_kind", "runner_jobs", type_="check")
    op.create_check_constraint(
        "ck_runner_jobs_kind",
        "runner_jobs",
        "kind IN ('system_diagnostic_v1', 'controlled_wait_v1', "
        "'workspace_prepare_v1', 'workspace_list_v1', 'workspace_read_text_v1', "
        "'workspace_write_text_v1', 'workspace_status_v1', 'workspace_diff_v1', "
        "'workspace_rollback_v1', 'workspace_discard_v1')",
    )

    op.drop_constraint("ck_grants_validation_scope", "execution_grants", type_="check")
    op.drop_constraint(
        "fk_execution_grants_validation_checkpoint", "execution_grants", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_execution_grants_validation_workspace", "execution_grants", type_="foreignkey"
    )
    for name in (
        "validation_artifact_count",
        "validation_artifact_bytes",
        "validation_output_bytes",
        "validation_fd_limit",
        "validation_pid_limit",
        "validation_memory_bytes",
        "validation_cpu_seconds",
        "validation_timeout_seconds",
        "max_validation_runs",
        "allowed_validation_profiles",
        "validation_checkpoint_id",
        "validation_workspace_id",
    ):
        op.drop_column("execution_grants", name)
