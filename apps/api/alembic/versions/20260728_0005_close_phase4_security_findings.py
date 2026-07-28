"""Add side-effect fencing and fail-closed Workspace ownership states.

Revision ID: 20260728_0005
Revises: 20260727_0004
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260728_0005"
down_revision: str | None = "20260727_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "repository_handles",
        sa.Column(
            "source_status",
            sa.String(length=16),
            server_default="unknown",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_repository_handles_source_status",
        "repository_handles",
        "source_status = 'unknown'",
    )
    op.alter_column("repository_handles", "source_status", server_default=None)

    op.add_column(
        "execution_grants",
        sa.Column("revocation_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "execution_grants",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_execution_grant_policy()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'execution grants cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF (
                to_jsonb(NEW)
                - 'status'
                - 'decided_at'
                - 'revocation_requested_at'
                - 'revoked_at'
            ) IS DISTINCT FROM (
                to_jsonb(OLD)
                - 'status'
                - 'decided_at'
                - 'revocation_requested_at'
                - 'revoked_at'
            ) THEN
                RAISE EXCEPTION 'execution grant policy is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.drop_constraint(
        "ck_execution_grants_status",
        "execution_grants",
        type_="check",
    )
    op.create_check_constraint(
        "ck_execution_grants_status",
        "execution_grants",
        "status IN ('pending', 'approved', 'rejected', 'revoke_requested', 'revoked', 'expired')",
    )
    op.create_check_constraint(
        "ck_grants_revocation_lifecycle",
        "execution_grants",
        "(status = 'revoke_requested' AND revocation_requested_at IS NOT NULL "
        "AND revoked_at IS NULL) OR "
        "(status = 'revoked' AND revocation_requested_at IS NOT NULL "
        "AND revoked_at IS NOT NULL) OR "
        "(status NOT IN ('revoke_requested', 'revoked') "
        "AND revocation_requested_at IS NULL AND revoked_at IS NULL)",
    )

    op.drop_constraint("ck_workspaces_state", "workspaces", type_="check")
    op.create_check_constraint(
        "ck_workspaces_state",
        "workspaces",
        "state IN ('requested', 'preparing', 'ready', 'active', 'sealing', "
        "'sealed', 'rollback_requested', 'rolled_back', 'discard_requested', "
        "'discarded', 'failed', 'expired', 'recovery_required', 'quarantined')",
    )

    op.create_table(
        "side_effect_permits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_handle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("relative_path", sa.String(length=512), nullable=True),
        sa.Column("expected_current", sa.String(length=64), nullable=False),
        sa.Column("proposed_digest", sa.String(length=64), nullable=False),
        sa.Column("job_digest", sa.String(length=64), nullable=False),
        sa.Column("operation_digest", sa.String(length=64), nullable=False),
        sa.Column("policy_hash", sa.String(length=64), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.CheckConstraint(
            "proposed_digest ~ '^[0-9a-f]{64}$' "
            "AND job_digest ~ '^[0-9a-f]{64}$' "
            "AND operation_digest ~ '^[0-9a-f]{64}$' "
            "AND policy_hash ~ '^[0-9a-f]{64}$' "
            "AND char_length(source_revision) IN (40, 64) "
            "AND source_revision ~ '^[0-9a-f]+$'",
            name="ck_side_effect_permits_digests",
        ),
        sa.CheckConstraint(
            "expected_current IN ('absent', 'workspace_absent') "
            "OR expected_current ~ '^[0-9a-f]{64}$'",
            name="ck_side_effect_permits_expected_current",
        ),
        sa.CheckConstraint(
            "operation IN ('prepare', 'write_text', 'rollback', 'discard')",
            name="ck_side_effect_permits_operation",
        ),
        sa.CheckConstraint(
            "(operation = 'write_text' AND relative_path IS NOT NULL) OR "
            "(operation <> 'write_text' AND relative_path IS NULL)",
            name="ck_side_effect_permits_path_scope",
        ),
        sa.CheckConstraint(
            "relative_path IS NULL OR "
            "(relative_path !~ '(^/|(^|/)\\.\\.(/|$)|\\\\)' "
            "AND octet_length(relative_path) BETWEEN 1 AND 512)",
            name="ck_side_effect_permits_relative_path",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_side_effect_permits_sequence"),
        sa.CheckConstraint(
            "state IN ('consumed', 'completed', 'failed', 'cancelled', 'expired')",
            name="ck_side_effect_permits_state",
        ),
        sa.CheckConstraint(
            "(state = 'consumed' AND terminal_at IS NULL) OR "
            "(state <> 'consumed' AND terminal_at IS NOT NULL)",
            name="ck_side_effect_permits_terminal",
        ),
        sa.CheckConstraint(
            "issued_at <= consumed_at AND consumed_at < expires_at",
            name="ck_side_effect_permits_window",
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["runner_job_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["grant_id"],
            ["execution_grants.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["runner_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["repository_handle_id"],
            ["repository_handles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "attempt_id",
            "job_digest",
            name="uq_side_effect_permits_attempt_job_digest",
        ),
        sa.UniqueConstraint(
            "operation_digest",
            name="uq_side_effect_permits_operation_digest",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "sequence",
            name="uq_side_effect_permits_workspace_sequence",
        ),
    )
    op.create_index(
        "ix_side_effect_permits_grant_state",
        "side_effect_permits",
        ["grant_id", "state"],
        unique=False,
    )
    op.create_index(
        "ix_side_effect_permits_state_expires",
        "side_effect_permits",
        ["state", "expires_at"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION protect_side_effect_permit()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'side-effect permits cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF (to_jsonb(NEW) - 'state' - 'terminal_at')
               IS DISTINCT FROM
               (to_jsonb(OLD) - 'state' - 'terminal_at') THEN
                RAISE EXCEPTION 'side-effect permit authority is immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF OLD.state <> 'consumed'
               AND (NEW.state, NEW.terminal_at)
                   IS DISTINCT FROM (OLD.state, OLD.terminal_at) THEN
                RAISE EXCEPTION 'terminal side-effect permit state is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER side_effect_permit_immutable
        BEFORE UPDATE OR DELETE ON side_effect_permits
        FOR EACH ROW EXECUTE FUNCTION protect_side_effect_permit()
        """
    )

    op.add_column(
        "workspace_events",
        sa.Column("side_effect_permit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workspace_events_side_effect_permit_id",
        "workspace_events",
        "side_effect_permits",
        ["side_effect_permit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("ck_workspace_events_type", "workspace_events", type_="check")
    op.create_check_constraint(
        "ck_workspace_events_type",
        "workspace_events",
        "event_type IN ('grant_approved', 'workspace_requested', 'mirror_prepared', "
        "'workspace_prepared', 'tool_started', 'tool_succeeded', 'tool_denied', "
        "'checkpoint_created', 'diff_generated', 'rollback_requested', "
        "'rollback_completed', 'workspace_sealed', 'discard_requested', "
        "'workspace_discarded', 'workspace_expired', 'workspace_failed', "
        "'permit_acquired', 'permit_completed', 'permit_denied', "
        "'grant_revoke_requested', 'grant_revoke_effective', "
        "'recovery_required', 'workspace_quarantined')",
    )

    op.add_column(
        "workspace_checkpoints",
        sa.Column("side_effect_permit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workspace_checkpoints_side_effect_permit_id",
        "workspace_checkpoints",
        "side_effect_permits",
        ["side_effect_permit_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("ck_runner_job_events_type", "runner_job_events", type_="check")
    op.create_check_constraint(
        "ck_runner_job_events_type",
        "runner_job_events",
        "event_type IN ('runner_registered', 'runner_heartbeat', 'job_created', "
        "'job_claimed', 'job_started', 'lease_renewed', 'job_progress', "
        "'cancel_requested', 'cancel_acknowledged', 'job_succeeded', "
        "'job_failed', 'lease_expired', 'job_requeued', 'policy_denied', "
        "'runner_revoked', 'side_effect_permit_acquired', "
        "'side_effect_permit_completed', 'side_effect_permit_denied')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE runner_job_events SET event_type = CASE "
        "WHEN event_type = 'side_effect_permit_completed' THEN 'job_progress' "
        "ELSE 'policy_denied' END "
        "WHERE event_type IN ('side_effect_permit_acquired', "
        "'side_effect_permit_completed', 'side_effect_permit_denied')"
    )
    op.drop_constraint("ck_runner_job_events_type", "runner_job_events", type_="check")
    op.create_check_constraint(
        "ck_runner_job_events_type",
        "runner_job_events",
        "event_type IN ('runner_registered', 'runner_heartbeat', 'job_created', "
        "'job_claimed', 'job_started', 'lease_renewed', 'job_progress', "
        "'cancel_requested', 'cancel_acknowledged', 'job_succeeded', "
        "'job_failed', 'lease_expired', 'job_requeued', 'policy_denied', "
        "'runner_revoked')",
    )

    op.drop_constraint(
        "fk_workspace_checkpoints_side_effect_permit_id",
        "workspace_checkpoints",
        type_="foreignkey",
    )
    op.drop_column("workspace_checkpoints", "side_effect_permit_id")

    op.execute(
        "UPDATE workspace_events SET event_type = CASE "
        "WHEN event_type = 'permit_completed' THEN 'tool_succeeded' "
        "WHEN event_type IN ('permit_acquired', 'grant_revoke_requested') "
        "THEN 'tool_started' ELSE 'tool_denied' END "
        "WHERE event_type IN ('permit_acquired', 'permit_completed', 'permit_denied', "
        "'grant_revoke_requested', 'grant_revoke_effective', "
        "'recovery_required', 'workspace_quarantined')"
    )
    op.drop_constraint("ck_workspace_events_type", "workspace_events", type_="check")
    op.create_check_constraint(
        "ck_workspace_events_type",
        "workspace_events",
        "event_type IN ('grant_approved', 'workspace_requested', 'mirror_prepared', "
        "'workspace_prepared', 'tool_started', 'tool_succeeded', 'tool_denied', "
        "'checkpoint_created', 'diff_generated', 'rollback_requested', "
        "'rollback_completed', 'workspace_sealed', 'discard_requested', "
        "'workspace_discarded', 'workspace_expired', 'workspace_failed')",
    )
    op.drop_constraint(
        "fk_workspace_events_side_effect_permit_id",
        "workspace_events",
        type_="foreignkey",
    )
    op.drop_column("workspace_events", "side_effect_permit_id")

    op.execute("DROP TRIGGER IF EXISTS side_effect_permit_immutable ON side_effect_permits")
    op.execute("DROP FUNCTION IF EXISTS protect_side_effect_permit()")
    op.drop_index(
        "ix_side_effect_permits_state_expires",
        table_name="side_effect_permits",
    )
    op.drop_index(
        "ix_side_effect_permits_grant_state",
        table_name="side_effect_permits",
    )
    op.drop_table("side_effect_permits")

    op.execute(
        "UPDATE workspaces SET state = 'failed', "
        "error_code = COALESCE(error_code, 'repair_migration_downgrade') "
        "WHERE state IN ('recovery_required', 'quarantined')"
    )
    op.drop_constraint("ck_workspaces_state", "workspaces", type_="check")
    op.create_check_constraint(
        "ck_workspaces_state",
        "workspaces",
        "state IN ('requested', 'preparing', 'ready', 'active', 'sealing', "
        "'sealed', 'rollback_requested', 'rolled_back', 'discard_requested', "
        "'discarded', 'failed', 'expired')",
    )

    op.execute(
        "UPDATE execution_grants SET status = 'revoked', "
        "revoked_at = COALESCE(revoked_at, CURRENT_TIMESTAMP) "
        "WHERE status = 'revoke_requested'"
    )
    op.drop_constraint(
        "ck_grants_revocation_lifecycle",
        "execution_grants",
        type_="check",
    )
    op.drop_constraint(
        "ck_execution_grants_status",
        "execution_grants",
        type_="check",
    )
    op.create_check_constraint(
        "ck_execution_grants_status",
        "execution_grants",
        "status IN ('pending', 'approved', 'rejected', 'revoked', 'expired')",
    )
    op.drop_column("execution_grants", "revoked_at")
    op.drop_column("execution_grants", "revocation_requested_at")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_execution_grant_policy()
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

    op.drop_constraint(
        "ck_repository_handles_source_status",
        "repository_handles",
        type_="check",
    )
    op.drop_column("repository_handles", "source_status")
