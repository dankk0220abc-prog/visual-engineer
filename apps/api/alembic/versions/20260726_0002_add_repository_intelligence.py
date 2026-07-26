"""Add governed read-only repository intelligence entities.

Revision ID: 20260726_0002
Revises: 20260726_0001
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260726_0002"
down_revision: str | None = "20260726_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="created", nullable=False),
        sa.Column(
            "permission_level", sa.String(length=32), server_default="read_only", nullable=False
        ),
        sa.Column("snapshot_mode", sa.String(length=32), server_default="git_head", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_plan_version", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("idempotency_request_hash", sa.String(length=64), nullable=True),
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
            "current_plan_version IS NULL OR current_plan_version >= 1",
            name="ck_runs_current_plan_version",
        ),
        sa.CheckConstraint("permission_level = 'read_only'", name="ck_runs_permission_level"),
        sa.CheckConstraint("snapshot_mode = 'git_head'", name="ck_runs_snapshot_mode"),
        sa.CheckConstraint(
            "status IN ('created', 'snapshotting', 'snapshot_ready', 'plan_ready', "
            "'awaiting_plan_approval', 'approved', 'rejected', 'failed', 'cancelled')",
            name="ck_runs_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_runs_version"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_runs_status", "runs", ["status"], unique=False)
    op.create_index("ix_runs_task_created_at", "runs", ["task_id", "created_at"], unique=False)

    op.create_table(
        "repository_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("branch_name", sa.String(length=255), nullable=False),
        sa.Column("repository_is_dirty", sa.Boolean(), nullable=False),
        sa.Column("dirty_path_count", sa.Integer(), nullable=False),
        sa.Column("dirty_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scanner_version", sa.String(length=32), nullable=False),
        sa.Column("scan_policy_version", sa.String(length=32), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("tracked_file_count", sa.Integer(), nullable=False),
        sa.Column("selected_file_count", sa.Integer(), nullable=False),
        sa.Column("skipped_file_count", sa.Integer(), nullable=False),
        sa.Column("total_selected_bytes", sa.Integer(), nullable=False),
        sa.Column("tech_stack", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("package_manager", sa.String(length=64), nullable=True),
        sa.Column("available_scripts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("test_surfaces", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("design_system_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "repository_instructions", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("safety_findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("dirty_path_count >= 0", name="ck_snapshots_dirty_path_count"),
        sa.CheckConstraint("skipped_file_count >= 0", name="ck_snapshots_skipped_file_count"),
        sa.CheckConstraint("selected_file_count >= 0", name="ck_snapshots_selected_file_count"),
        sa.CheckConstraint("total_selected_bytes >= 0", name="ck_snapshots_total_selected_bytes"),
        sa.CheckConstraint("tracked_file_count >= 0", name="ck_snapshots_tracked_file_count"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_repository_snapshots_run_id"),
    )
    op.create_index(
        "ix_repository_snapshots_fingerprint",
        "repository_snapshots",
        ["fingerprint"],
        unique=False,
    )

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("snapshot_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("delivery_package", sa.String(length=64), nullable=False),
        sa.Column("objective_summary", sa.String(length=4000), nullable=False),
        sa.Column("repository_context_summary", sa.String(length=4000), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("proposed_change_scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explicit_non_goals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("acceptance_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("stop_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_future_permission_level", sa.String(length=64), nullable=False),
        sa.Column("execution_available", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "delivery_package IN ('design_implementation', 'design_system_migration', "
            "'frontend_quality_remediation')",
            name="ck_plans_delivery_package",
        ),
        sa.CheckConstraint("execution_available = false", name="ck_plans_execution_unavailable"),
        sa.CheckConstraint("source = 'deterministic_policy'", name="ck_plans_source"),
        sa.CheckConstraint(
            "status IN ('draft', 'awaiting_approval', 'approved', 'rejected', 'superseded')",
            name="ck_plans_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_plans_version"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "version", name="uq_plans_run_version"),
    )
    op.create_index("ix_plans_run_created_at", "plans", ["run_id", "created_at"], unique=False)

    op.create_table(
        "approval_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column("actor_type", sa.String(length=32), server_default="local_user", nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("actor_type = 'local_user'", name="ck_decisions_actor_type"),
        sa.CheckConstraint("decision IN ('approve', 'reject')", name="ck_decisions_decision"),
        sa.CheckConstraint(
            "decision <> 'reject' OR (comment IS NOT NULL AND char_length(trim(comment)) > 0)",
            name="ck_decisions_reject_comment",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", name="uq_approval_decisions_plan_id"),
    )
    op.create_index(
        "ix_approval_decisions_run_created_at",
        "approval_decisions",
        ["run_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("actor_type IN ('local_user', 'system')", name="ck_audit_actor_type"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_events_run_created_at",
        "audit_events",
        ["run_id", "created_at", "id"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION reject_repository_snapshot_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'repository snapshots are immutable'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER repository_snapshots_immutable
        BEFORE UPDATE OR DELETE ON repository_snapshots
        FOR EACH ROW EXECUTE FUNCTION reject_repository_snapshot_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER repository_snapshots_immutable ON repository_snapshots")
    op.execute("DROP FUNCTION reject_repository_snapshot_mutation()")
    op.drop_index("ix_audit_events_run_created_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_approval_decisions_run_created_at", table_name="approval_decisions")
    op.drop_table("approval_decisions")
    op.drop_index("ix_plans_run_created_at", table_name="plans")
    op.drop_table("plans")
    op.drop_index("ix_repository_snapshots_fingerprint", table_name="repository_snapshots")
    op.drop_table("repository_snapshots")
    op.drop_index("ix_runs_task_created_at", table_name="runs")
    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_table("runs")
