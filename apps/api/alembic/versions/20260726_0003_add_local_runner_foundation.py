"""Add the browser-orchestrated Local Runner foundation.

Revision ID: 20260726_0003
Revises: 20260726_0002
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260726_0003"
down_revision: str | None = "20260726_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("protocol_version", sa.Integer(), nullable=False),
        sa.Column("software_version", sa.String(length=64), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="registered", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("protocol_version = 1", name="ck_runners_protocol_version"),
        sa.CheckConstraint(
            "(status = 'revoked') = (revoked_at IS NOT NULL)",
            name="ck_runners_revoked_at",
        ),
        sa.CheckConstraint(
            "status IN ('registered', 'online', 'offline', 'revoked')",
            name="ck_runners_status",
        ),
        sa.CheckConstraint("version >= 1", name="ck_runners_version"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_digest"),
    )
    op.create_index("ix_runners_last_seen_at", "runners", ["last_seen_at"], unique=False)

    op.create_table(
        "permission_envelopes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("envelope_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "authorization_source",
            sa.String(length=64),
            server_default="local_user_job_dispatch",
            nullable=False,
        ),
        sa.Column(
            "allowed_capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("repository_access", sa.String(length=16), server_default="none", nullable=False),
        sa.Column("shell_access", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "network_policy",
            sa.String(length=32),
            server_default="control_plane_only",
            nullable=False,
        ),
        sa.Column("max_runtime_seconds", sa.Integer(), nullable=False),
        sa.Column("lease_seconds", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("max_result_bytes", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "authorization_source = 'local_user_job_dispatch'",
            name="ck_permission_envelopes_authorization_source",
        ),
        sa.CheckConstraint(
            "max_attempts BETWEEN 1 AND 5",
            name="ck_permission_envelopes_attempts",
        ),
        sa.CheckConstraint(
            "expires_at > issued_at",
            name="ck_permission_envelopes_expiry",
        ),
        sa.CheckConstraint(
            "lease_seconds BETWEEN 2 AND 60",
            name="ck_permission_envelopes_lease",
        ),
        sa.CheckConstraint(
            "network_policy = 'control_plane_only'",
            name="ck_permission_envelopes_network",
        ),
        sa.CheckConstraint(
            "policy_hash ~ '^[0-9a-f]{64}$'",
            name="ck_permission_envelopes_policy_hash",
        ),
        sa.CheckConstraint(
            "repository_access = 'none'",
            name="ck_permission_envelopes_repository",
        ),
        sa.CheckConstraint(
            "max_result_bytes BETWEEN 256 AND 65536",
            name="ck_permission_envelopes_result_bytes",
        ),
        sa.CheckConstraint(
            "max_runtime_seconds BETWEEN 1 AND 60",
            name="ck_permission_envelopes_runtime",
        ),
        sa.CheckConstraint(
            "shell_access = false",
            name="ck_permission_envelopes_shell",
        ),
        sa.CheckConstraint(
            "envelope_version = 1",
            name="ck_permission_envelopes_version",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_permission_envelopes_job_id"),
    )

    op.create_table(
        "runner_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=24), server_default="queued", nullable=False),
        sa.Column(
            "permission_envelope_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "requested_by", sa.String(length=32), server_default="local_user", nullable=False
        ),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("active_attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_count >= 0", name="ck_runner_jobs_attempt_count"),
        sa.CheckConstraint(
            "max_attempts BETWEEN 1 AND 5 AND attempt_count <= max_attempts",
            name="ck_runner_jobs_attempt_budget",
        ),
        sa.CheckConstraint(
            "kind IN ('system_diagnostic_v1', 'controlled_wait_v1')",
            name="ck_runner_jobs_kind",
        ),
        sa.CheckConstraint(
            "requested_by = 'local_user'",
            name="ck_runner_jobs_requested_by",
        ),
        sa.CheckConstraint(
            "state IN ('queued', 'leased', 'running', 'cancel_requested', "
            "'succeeded', 'cancelled', 'failed')",
            name="ck_runner_jobs_state",
        ),
        sa.CheckConstraint("version >= 1", name="ck_runner_jobs_version"),
        sa.ForeignKeyConstraint(
            ["permission_envelope_id"],
            ["permission_envelopes.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "permission_envelope_id",
            name="uq_runner_jobs_permission_envelope_id",
        ),
    )
    op.create_index(
        "ix_runner_jobs_state_created_at",
        "runner_jobs",
        ["state", "created_at"],
        unique=False,
    )

    op.create_table(
        "runner_job_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("lease_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=24), server_default="leased", nullable=False),
        sa.Column("leased_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_number >= 1",
            name="ck_runner_job_attempt_number",
        ),
        sa.CheckConstraint(
            "state IN ('leased', 'running', 'succeeded', 'cancelled', 'failed', 'lease_expired')",
            name="ck_runner_job_attempts_state",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["runner_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "attempt_number",
            name="uq_runner_job_attempt_number",
        ),
    )
    op.create_index(
        "ix_runner_job_attempts_lease",
        "runner_job_attempts",
        ["state", "leased_until"],
        unique=False,
    )
    op.create_index(
        "uq_runner_job_attempt_active",
        "runner_job_attempts",
        ["job_id"],
        unique=True,
        postgresql_where=sa.text("state IN ('leased', 'running')"),
    )
    op.create_foreign_key(
        "fk_runner_jobs_active_attempt_id",
        "runner_jobs",
        "runner_job_attempts",
        ["active_attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "runner_job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "event_type IN ('runner_registered', 'runner_heartbeat', 'job_created', "
            "'job_claimed', 'job_started', 'lease_renewed', 'job_progress', "
            "'cancel_requested', 'cancel_acknowledged', 'job_succeeded', "
            "'job_failed', 'lease_expired', 'job_requeued', 'policy_denied', "
            "'runner_revoked')",
            name="ck_runner_job_events_type",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_runner_job_events_sequence"),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["runner_job_attempts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["runner_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["runner_id"], ["runners.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "sequence",
            name="uq_runner_job_events_job_sequence",
        ),
    )
    op.create_index(
        "ix_runner_job_events_job_created_at",
        "runner_job_events",
        ["job_id", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_runner_job_events_runner_created_at",
        "runner_job_events",
        ["runner_id", "created_at", "id"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION reject_permission_envelope_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'permission envelopes are immutable'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER permission_envelopes_immutable
        BEFORE UPDATE OR DELETE ON permission_envelopes
        FOR EACH ROW EXECUTE FUNCTION reject_permission_envelope_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER permission_envelopes_immutable ON permission_envelopes")
    op.execute("DROP FUNCTION reject_permission_envelope_mutation()")
    op.drop_index("ix_runner_job_events_runner_created_at", table_name="runner_job_events")
    op.drop_index("ix_runner_job_events_job_created_at", table_name="runner_job_events")
    op.drop_table("runner_job_events")
    op.drop_constraint(
        "fk_runner_jobs_active_attempt_id",
        "runner_jobs",
        type_="foreignkey",
    )
    op.drop_index("uq_runner_job_attempt_active", table_name="runner_job_attempts")
    op.drop_index("ix_runner_job_attempts_lease", table_name="runner_job_attempts")
    op.drop_table("runner_job_attempts")
    op.drop_index("ix_runner_jobs_state_created_at", table_name="runner_jobs")
    op.drop_table("runner_jobs")
    op.drop_table("permission_envelopes")
    op.drop_index("ix_runners_last_seen_at", table_name="runners")
    op.drop_table("runners")
