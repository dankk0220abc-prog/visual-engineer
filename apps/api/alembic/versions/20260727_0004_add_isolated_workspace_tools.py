"""Add isolated workspace grants, handles, checkpoints, and job bindings.

Revision ID: 20260727_0004
Revises: 20260726_0003
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260727_0004"
down_revision: str | None = "20260726_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repository_handles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opaque_handle", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("vcs_kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_revision", sa.String(length=64), nullable=True),
        sa.Column("current_branch", sa.String(length=255), nullable=True),
        sa.Column("source_is_dirty", sa.Boolean(), nullable=False),
        sa.Column("dirty_path_count", sa.Integer(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_version", sa.Integer(), nullable=False),
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
            "dirty_path_count >= 0",
            name="ck_repository_handles_dirty_count",
        ),
        sa.CheckConstraint(
            "metadata_version = 1",
            name="ck_repository_handles_metadata_version",
        ),
        sa.CheckConstraint(
            "status IN ('available', 'unavailable', 'revoked')",
            name="ck_repository_handles_status",
        ),
        sa.CheckConstraint("vcs_kind = 'git'", name="ck_repository_handles_vcs"),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "runner_id",
            "opaque_handle",
            name="uq_repository_handles_runner_opaque",
        ),
    )
    op.create_index(
        "ix_repository_handles_runner_status",
        "repository_handles",
        ["runner_id", "status"],
        unique=False,
    )

    op.create_table(
        "execution_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grant_version", sa.Integer(), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_handle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("snapshot_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "allowed_operations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("allowed_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("denied_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("max_files_changed", sa.Integer(), nullable=False),
        sa.Column("max_total_write_bytes", sa.Integer(), nullable=False),
        sa.Column("max_single_file_bytes", sa.Integer(), nullable=False),
        sa.Column("max_diff_bytes", sa.Integer(), nullable=False),
        sa.Column("workspace_ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("network_policy", sa.String(length=16), nullable=False),
        sa.Column("shell_access", sa.Boolean(), nullable=False),
        sa.Column("git_delivery_access", sa.Boolean(), nullable=False),
        sa.Column("source_repository_write_access", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("policy_hash", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND decided_at IS NULL) OR "
            "(status <> 'pending' AND decided_at IS NOT NULL)",
            name="ck_grants_decided_at",
        ),
        sa.CheckConstraint("expires_at > requested_at", name="ck_grants_expiry"),
        sa.CheckConstraint(
            "max_diff_bytes BETWEEN 1 AND 32768",
            name="ck_grants_diff_budget",
        ),
        sa.CheckConstraint(
            "git_delivery_access = false",
            name="ck_grants_delivery_false",
        ),
        sa.CheckConstraint(
            "max_files_changed BETWEEN 1 AND 100",
            name="ck_grants_file_budget",
        ),
        sa.CheckConstraint("network_policy = 'none'", name="ck_grants_network_none"),
        sa.CheckConstraint(
            "policy_hash ~ '^[0-9a-f]{64}$'",
            name="ck_grants_policy_hash",
        ),
        sa.CheckConstraint("shell_access = false", name="ck_grants_shell_false"),
        sa.CheckConstraint(
            "max_single_file_bytes BETWEEN 1 AND 32768 "
            "AND max_single_file_bytes <= max_total_write_bytes",
            name="ck_grants_single_file_budget",
        ),
        sa.CheckConstraint(
            "snapshot_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_grants_snapshot_fingerprint",
        ),
        sa.CheckConstraint(
            "source_repository_write_access = false",
            name="ck_grants_source_write_false",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'revoked', 'expired')",
            name="ck_execution_grants_status",
        ),
        sa.CheckConstraint(
            "max_total_write_bytes BETWEEN 1 AND 1048576",
            name="ck_grants_total_write_budget",
        ),
        sa.CheckConstraint("grant_version = 1", name="ck_execution_grants_version"),
        sa.CheckConstraint(
            "workspace_ttl_seconds BETWEEN 60 AND 86400",
            name="ck_grants_workspace_ttl",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["repository_handle_id"],
            ["repository_handles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_execution_grants_plan_created",
        "execution_grants",
        ["plan_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_execution_grants_status_expires",
        "execution_grants",
        ["status", "expires_at"],
        unique=False,
    )

    op.create_table(
        "execution_grant_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=2000), nullable=True),
        sa.Column(
            "actor_type",
            sa.String(length=32),
            server_default="local_user",
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actor_type = 'local_user'",
            name="ck_execution_grant_decisions_actor",
        ),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject')",
            name="ck_execution_grant_decisions_decision",
        ),
        sa.CheckConstraint(
            "decision <> 'reject' OR char_length(trim(reason)) > 0",
            name="ck_execution_grant_decisions_reject_reason",
        ),
        sa.ForeignKeyConstraint(["grant_id"], ["execution_grants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grant_id", name="uq_execution_grant_decisions_grant"),
    )

    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_handle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("workspace_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("initial_tree_hash", sa.String(length=64), nullable=True),
        sa.Column("current_tree_hash", sa.String(length=64), nullable=True),
        sa.Column("changed_file_count", sa.Integer(), nullable=False),
        sa.Column("total_written_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_paths",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("active_attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "changed_file_count >= 0",
            name="ck_workspaces_changed_count",
        ),
        sa.CheckConstraint(
            "current_tree_hash IS NULL OR current_tree_hash ~ '^[0-9a-f]{64}$'",
            name="ck_workspaces_current_tree_hash",
        ),
        sa.CheckConstraint(
            "workspace_fingerprint IS NULL OR workspace_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_workspaces_fingerprint",
        ),
        sa.CheckConstraint(
            "initial_tree_hash IS NULL OR initial_tree_hash ~ '^[0-9a-f]{64}$'",
            name="ck_workspaces_initial_tree_hash",
        ),
        sa.CheckConstraint(
            "state IN ('requested', 'preparing', 'ready', 'active', 'sealing', "
            "'sealed', 'rollback_requested', 'rolled_back', 'discard_requested', "
            "'discarded', 'failed', 'expired')",
            name="ck_workspaces_state",
        ),
        sa.CheckConstraint(
            "total_written_bytes >= 0",
            name="ck_workspaces_written_bytes",
        ),
        sa.ForeignKeyConstraint(
            ["active_attempt_id"],
            ["runner_job_attempts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["grant_id"], ["execution_grants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["repository_handle_id"],
            ["repository_handles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspaces_grant_created",
        "workspaces",
        ["grant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_workspaces_runner_state",
        "workspaces",
        ["runner_id", "state"],
        unique=False,
    )

    op.create_table(
        "workspace_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('grant_approved', 'workspace_requested', 'mirror_prepared', "
            "'workspace_prepared', 'tool_started', 'tool_succeeded', 'tool_denied', "
            "'checkpoint_created', 'diff_generated', 'rollback_requested', "
            "'rollback_completed', 'workspace_sealed', 'discard_requested', "
            "'workspace_discarded', 'workspace_expired', 'workspace_failed')",
            name="ck_workspace_events_type",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_workspace_events_sequence"),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "sequence", name="uq_workspace_events_sequence"),
    )
    op.create_index(
        "ix_workspace_events_workspace_created",
        "workspace_events",
        ["workspace_id", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "workspace_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("tree_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("diff_hash", sa.String(length=64), nullable=False),
        sa.Column("changed_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_file_count", sa.Integer(), nullable=False),
        sa.Column("total_diff_bytes", sa.Integer(), nullable=False),
        sa.Column("diff_artifact", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "changed_file_count BETWEEN 0 AND 100",
            name="ck_workspace_checkpoints_changed_count",
        ),
        sa.CheckConstraint(
            "diff_hash ~ '^[0-9a-f]{64}$'",
            name="ck_workspace_checkpoints_diff_hash",
        ),
        sa.CheckConstraint(
            "total_diff_bytes BETWEEN 0 AND 32768",
            name="ck_workspace_checkpoints_diff_bytes",
        ),
        sa.CheckConstraint(
            "sequence >= 1",
            name="ck_workspace_checkpoints_sequence",
        ),
        sa.CheckConstraint(
            "tree_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_workspace_checkpoints_tree_fingerprint",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "sequence",
            name="uq_workspace_checkpoints_sequence",
        ),
    )
    op.create_index(
        "ix_workspace_checkpoints_workspace_created",
        "workspace_checkpoints",
        ["workspace_id", "created_at", "id"],
        unique=False,
    )

    op.drop_constraint(
        "ck_permission_envelopes_authorization_source",
        "permission_envelopes",
        type_="check",
    )
    op.drop_constraint(
        "ck_permission_envelopes_repository",
        "permission_envelopes",
        type_="check",
    )
    op.drop_constraint(
        "ck_permission_envelopes_runtime",
        "permission_envelopes",
        type_="check",
    )
    op.alter_column(
        "permission_envelopes",
        "repository_access",
        existing_type=sa.String(length=16),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_permission_envelopes_authorization_source",
        "permission_envelopes",
        "authorization_source IN ('local_user_job_dispatch', 'execution_grant')",
    )
    op.create_check_constraint(
        "ck_permission_envelopes_repository",
        "permission_envelopes",
        "repository_access IN ('none', 'isolated_workspace')",
    )
    op.create_check_constraint(
        "ck_permission_envelopes_authority_repository",
        "permission_envelopes",
        "(authorization_source = 'local_user_job_dispatch' AND repository_access = 'none') "
        "OR (authorization_source = 'execution_grant' "
        "AND repository_access = 'isolated_workspace')",
    )
    op.create_check_constraint(
        "ck_permission_envelopes_runtime",
        "permission_envelopes",
        "max_runtime_seconds BETWEEN 1 AND 120",
    )

    op.drop_constraint("ck_runner_jobs_kind", "runner_jobs", type_="check")
    op.add_column(
        "runner_jobs",
        sa.Column("execution_grant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "runner_jobs",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "runner_jobs",
        sa.Column("repository_handle_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "runner_jobs",
        sa.Column("source_revision", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "runner_jobs",
        sa.Column("execution_policy_hash", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_runner_jobs_execution_grant_id",
        "runner_jobs",
        "execution_grants",
        ["execution_grant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_runner_jobs_workspace_id",
        "runner_jobs",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_runner_jobs_repository_handle_id",
        "runner_jobs",
        "repository_handles",
        ["repository_handle_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_runner_jobs_kind",
        "runner_jobs",
        "kind IN ('system_diagnostic_v1', 'controlled_wait_v1', "
        "'workspace_prepare_v1', 'workspace_list_v1', 'workspace_read_text_v1', "
        "'workspace_write_text_v1', 'workspace_status_v1', 'workspace_diff_v1', "
        "'workspace_rollback_v1', 'workspace_discard_v1')",
    )
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
    op.create_index(
        "ix_runner_jobs_workspace_created_at",
        "runner_jobs",
        ["workspace_id", "created_at"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION protect_execution_grant_policy()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'execution grants cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF (to_jsonb(NEW) - 'status' - 'decided_at')
               IS DISTINCT FROM
               (to_jsonb(OLD) - 'status' - 'decided_at') THEN
                RAISE EXCEPTION 'execution grant policy is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER execution_grants_policy_immutable
        BEFORE UPDATE OR DELETE ON execution_grants
        FOR EACH ROW EXECUTE FUNCTION protect_execution_grant_policy()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_workspace_evidence_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'workspace evidence is immutable'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER workspace_events_immutable
        BEFORE UPDATE OR DELETE ON workspace_events
        FOR EACH ROW EXECUTE FUNCTION reject_workspace_evidence_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER workspace_checkpoints_immutable
        BEFORE UPDATE OR DELETE ON workspace_checkpoints
        FOR EACH ROW EXECUTE FUNCTION reject_workspace_evidence_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM runner_jobs WHERE kind LIKE 'workspace_%'
            ) THEN
                RAISE EXCEPTION
                    'remove Phase 4 workspace jobs through the lifecycle before downgrade';
            END IF;
        END
        $$
        """
    )
    op.execute("DROP TRIGGER workspace_checkpoints_immutable ON workspace_checkpoints")
    op.execute("DROP TRIGGER workspace_events_immutable ON workspace_events")
    op.execute("DROP FUNCTION reject_workspace_evidence_mutation()")
    op.execute("DROP TRIGGER execution_grants_policy_immutable ON execution_grants")
    op.execute("DROP FUNCTION protect_execution_grant_policy()")

    op.drop_index("ix_runner_jobs_workspace_created_at", table_name="runner_jobs")
    op.drop_constraint("ck_runner_jobs_workspace_binding", "runner_jobs", type_="check")
    op.drop_constraint("ck_runner_jobs_kind", "runner_jobs", type_="check")
    op.drop_constraint(
        "fk_runner_jobs_repository_handle_id",
        "runner_jobs",
        type_="foreignkey",
    )
    op.drop_constraint("fk_runner_jobs_workspace_id", "runner_jobs", type_="foreignkey")
    op.drop_constraint(
        "fk_runner_jobs_execution_grant_id",
        "runner_jobs",
        type_="foreignkey",
    )
    op.drop_column("runner_jobs", "execution_policy_hash")
    op.drop_column("runner_jobs", "source_revision")
    op.drop_column("runner_jobs", "repository_handle_id")
    op.drop_column("runner_jobs", "workspace_id")
    op.drop_column("runner_jobs", "execution_grant_id")
    op.create_check_constraint(
        "ck_runner_jobs_kind",
        "runner_jobs",
        "kind IN ('system_diagnostic_v1', 'controlled_wait_v1')",
    )

    op.drop_constraint(
        "ck_permission_envelopes_runtime",
        "permission_envelopes",
        type_="check",
    )
    op.drop_constraint(
        "ck_permission_envelopes_authority_repository",
        "permission_envelopes",
        type_="check",
    )
    op.drop_constraint(
        "ck_permission_envelopes_repository",
        "permission_envelopes",
        type_="check",
    )
    op.drop_constraint(
        "ck_permission_envelopes_authorization_source",
        "permission_envelopes",
        type_="check",
    )
    op.create_check_constraint(
        "ck_permission_envelopes_runtime",
        "permission_envelopes",
        "max_runtime_seconds BETWEEN 1 AND 60",
    )
    op.create_check_constraint(
        "ck_permission_envelopes_repository",
        "permission_envelopes",
        "repository_access = 'none'",
    )
    op.create_check_constraint(
        "ck_permission_envelopes_authorization_source",
        "permission_envelopes",
        "authorization_source = 'local_user_job_dispatch'",
    )
    op.alter_column(
        "permission_envelopes",
        "repository_access",
        existing_type=sa.String(length=32),
        type_=sa.String(length=16),
        existing_nullable=False,
    )

    op.drop_index(
        "ix_workspace_checkpoints_workspace_created",
        table_name="workspace_checkpoints",
    )
    op.drop_table("workspace_checkpoints")
    op.drop_index("ix_workspace_events_workspace_created", table_name="workspace_events")
    op.drop_table("workspace_events")
    op.drop_index("ix_workspaces_runner_state", table_name="workspaces")
    op.drop_index("ix_workspaces_grant_created", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_table("execution_grant_decisions")
    op.drop_index("ix_execution_grants_status_expires", table_name="execution_grants")
    op.drop_index("ix_execution_grants_plan_created", table_name="execution_grants")
    op.drop_table("execution_grants")
    op.drop_index("ix_repository_handles_runner_status", table_name="repository_handles")
    op.drop_table("repository_handles")
