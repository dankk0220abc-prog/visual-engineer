"""Enforce governed final-review freshness and readiness integrity.

Revision ID: 20260730_0011
Revises: 20260730_0010
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_0011"
down_revision: str | None = "20260730_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    _create_freshness_and_blocker_tables()
    _extend_review_tables()
    _install_canonical_digest()
    _backfill_legacy_review_rows()
    _install_review_integrity_guards()
    _install_freshness_triggers()


def _create_freshness_and_blocker_tables() -> None:
    op.create_table(
        "review_freshness_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generation", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "last_change_kind",
            sa.String(length=64),
            server_default="scope_initialized",
            nullable=False,
        ),
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
        sa.CheckConstraint("generation >= 1", name="ck_review_freshness_generation"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"], ["workspace_checkpoints.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id",
            "workspace_id",
            "checkpoint_id",
            name="uq_review_freshness_scope",
        ),
    )
    op.create_index(
        "ix_review_freshness_workspace",
        "review_freshness_states",
        ["workspace_id", "checkpoint_id"],
    )

    op.create_table(
        "review_blocker_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_key", sa.String(length=128), nullable=False),
        sa.Column("finding_version", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "source",
            sa.String(length=64),
            server_default="governed-review-security-findings",
            nullable=False,
        ),
        sa.Column("source_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("evidence_digest", sa.String(length=64), nullable=False),
        sa.Column("policy_digest", sa.String(length=64), nullable=False),
        sa.Column("finding_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_review_blocker_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'closed')",
            name="ck_review_blocker_status",
        ),
        sa.CheckConstraint(
            "(severity IN ('critical', 'high') AND blocking = true) "
            "OR severity IN ('medium', 'low')",
            name="ck_review_blocker_critical_high",
        ),
        sa.CheckConstraint(
            "finding_version >= 1 AND source_version >= 1",
            name="ck_review_blocker_versions",
        ),
        sa.CheckConstraint(
            "evidence_digest ~ '^[0-9a-f]{64}$' "
            "AND policy_digest ~ '^[0-9a-f]{64}$' "
            "AND finding_digest ~ '^[0-9a-f]{64}$'",
            name="ck_review_blocker_digests",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"], ["workspace_checkpoints.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id",
            "workspace_id",
            "checkpoint_id",
            "finding_key",
            "finding_version",
            name="uq_review_blocker_finding_version",
        ),
    )
    op.create_index(
        "ix_review_blockers_scope",
        "review_blocker_findings",
        ["plan_id", "workspace_id", "checkpoint_id", "finding_key", "finding_version"],
    )


def _extend_review_tables() -> None:
    for table_name in (
        "review_packages",
        "review_decisions",
        "release_readiness_verdicts",
    ):
        op.execute(f"ALTER TABLE {table_name} DISABLE TRIGGER {table_name}_immutable")
    op.drop_constraint("uq_review_packages_suite_result", "review_packages", type_="unique")
    op.drop_constraint(
        "ck_review_packages_schema_version",
        "review_packages",
        type_="check",
    )
    op.drop_constraint("ck_review_packages_digests", "review_packages", type_="check")
    op.drop_constraint("ck_review_packages_manifest", "review_packages", type_="check")
    op.add_column(
        "review_packages",
        sa.Column("package_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "review_packages",
        sa.Column("freshness_state_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "review_packages",
        sa.Column("freshness_generation", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "review_packages",
        sa.Column("checkpoint_diff_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "review_packages",
        sa.Column("execution_grant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "review_packages",
        sa.Column("suite_policy_digest", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "review_packages",
        sa.Column(
            "blocker_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "review_packages",
        sa.Column("blocker_summary_digest", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "review_packages",
        sa.Column(
            "blocker_source",
            sa.String(length=64),
            server_default="governed-review-security-findings",
            nullable=False,
        ),
    )
    op.add_column(
        "review_packages",
        sa.Column("blocker_source_version", sa.Integer(), server_default="1", nullable=False),
    )
    for column_name in ("critical_count", "high_count", "blocking_medium_count"):
        op.add_column(
            "review_packages",
            sa.Column(column_name, sa.Integer(), server_default="0", nullable=False),
        )
    op.create_foreign_key(
        "fk_review_packages_freshness_state",
        "review_packages",
        "review_freshness_states",
        ["freshness_state_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_review_packages_execution_grant",
        "review_packages",
        "execution_grants",
        ["execution_grant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_review_packages_result_generation",
        "review_packages",
        ["suite_result_id", "freshness_generation"],
    )

    op.drop_constraint(
        "ck_review_invalidations_reason",
        "review_package_invalidations",
        type_="check",
    )
    op.execute(
        "DROP TRIGGER review_package_invalidations_immutable ON review_package_invalidations"
    )
    op.execute(
        """
        UPDATE review_package_invalidations
        SET reason_code = 'evidence_integrity_failed',
            observed_value = 'downgraded_from:' || reason_code
        WHERE reason_code NOT IN (
            'workspace_changed',
            'checkpoint_superseded',
            'source_revision_changed',
            'suite_result_superseded',
            'evidence_integrity_failed'
        )
        """
    )
    op.execute(
        """
        CREATE TRIGGER review_package_invalidations_immutable
        BEFORE UPDATE OR DELETE ON review_package_invalidations
        FOR EACH ROW EXECUTE FUNCTION protect_review_immutable()
        """
    )
    op.create_check_constraint(
        "ck_review_invalidations_reason",
        "review_package_invalidations",
        "reason_code IN ('workspace_changed', 'checkpoint_superseded', "
        "'source_revision_changed', 'suite_result_superseded', "
        "'evidence_integrity_failed', 'validation_facts_changed', "
        "'policy_changed', 'grant_lineage_changed', "
        "'blocker_summary_changed', 'remediation_generation_required')",
    )

    op.drop_constraint("ck_review_decisions_digest", "review_decisions", type_="check")
    op.add_column("review_decisions", sa.Column("package_version", sa.Integer(), nullable=True))
    op.add_column(
        "review_decisions",
        sa.Column("expected_generation", sa.Integer(), nullable=True),
    )
    op.add_column(
        "review_decisions",
        sa.Column("policy_digest", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "review_decisions",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "review_decisions",
        sa.Column("idempotency_request_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "review_decisions",
        sa.Column("decision_digest", sa.String(length=64), nullable=True),
    )

    op.drop_constraint(
        "ck_readiness_verdicts_digests",
        "release_readiness_verdicts",
        type_="check",
    )
    op.add_column(
        "release_readiness_verdicts",
        sa.Column("package_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "release_readiness_verdicts",
        sa.Column("freshness_generation", sa.Integer(), nullable=True),
    )
    for column_name in (
        "suite_result_digest",
        "policy_digest",
        "blocker_summary_digest",
    ):
        op.add_column(
            "release_readiness_verdicts",
            sa.Column(column_name, sa.String(length=64), nullable=True),
        )
    for column_name in ("critical_count", "high_count", "blocking_medium_count"):
        op.add_column(
            "release_readiness_verdicts",
            sa.Column(column_name, sa.Integer(), nullable=True),
        )

    op.add_column(
        "audit_events",
        sa.Column("review_package_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("audit_events", sa.Column("review_sequence", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_audit_events_review_package",
        "audit_events",
        "review_packages",
        ["review_package_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def _install_canonical_digest() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION review_canonical_digest(payload jsonb)
        RETURNS text AS $$
            SELECT encode(digest(convert_to(payload::text, 'UTF8'), 'sha256'), 'hex')
        $$ LANGUAGE sql IMMUTABLE STRICT;
        """
    )


def _backfill_legacy_review_rows() -> None:
    op.execute(
        """
        INSERT INTO review_freshness_states (
            id, plan_id, workspace_id, checkpoint_id, generation, last_change_kind
        )
        SELECT gen_random_uuid(), package.plan_id, package.workspace_id,
            package.checkpoint_id, 2, 'remediation_generation_required'
        FROM review_packages AS package
        ON CONFLICT (plan_id, workspace_id, checkpoint_id) DO NOTHING;

        UPDATE review_packages AS package
        SET freshness_state_id = scope.id,
            freshness_generation = 1,
            checkpoint_diff_hash = checkpoint.diff_hash,
            execution_grant_id = suite.execution_grant_id,
            suite_policy_digest = suite.policy_digest,
            blocker_summary = jsonb_build_object(
                'schema_version', 1,
                'source', 'governed-review-security-findings',
                'source_version', 1,
                'plan_id', package.plan_id::text,
                'workspace_id', package.workspace_id::text,
                'checkpoint_id', package.checkpoint_id::text,
                'suite_result_id', package.suite_result_id::text,
                'suite_result_digest', package.suite_result_digest,
                'evidence_manifest_digest', package.evidence_manifest_digest,
                'policy_digest', suite.policy_digest,
                'freshness_generation', 1,
                'critical_count', 0,
                'high_count', 0,
                'blocking_medium_count', 0,
                'findings', '[]'::jsonb
            )
        FROM review_freshness_states AS scope,
             validation_suite_runs AS suite,
             workspace_checkpoints AS checkpoint
        WHERE scope.plan_id = package.plan_id
            AND scope.workspace_id = package.workspace_id
            AND scope.checkpoint_id = package.checkpoint_id
            AND suite.id = package.suite_run_id
            AND checkpoint.id = package.checkpoint_id;

        UPDATE review_packages
        SET blocker_summary_digest = review_canonical_digest(blocker_summary)
        WHERE blocker_summary_digest IS NULL;

        INSERT INTO review_package_invalidations (
            id, review_package_id, package_digest, reason_code,
            observed_value, request_id
        )
        SELECT gen_random_uuid(), package.id, package.package_digest,
            'remediation_generation_required', 'schema_v2_required',
            'migration-20260730-0011'
        FROM review_packages AS package
        ON CONFLICT (review_package_id) DO NOTHING;
        """
    )
    for column_name in (
        "freshness_state_id",
        "checkpoint_diff_hash",
        "execution_grant_id",
        "suite_policy_digest",
        "blocker_summary_digest",
    ):
        op.alter_column("review_packages", column_name, nullable=False)

    op.execute(
        """
        UPDATE review_decisions AS decision
        SET package_version = package.package_version,
            expected_generation = package.freshness_generation,
            policy_digest = package.suite_policy_digest,
            idempotency_key = 'legacy:' || decision.id::text,
            idempotency_request_hash = review_canonical_digest(
                jsonb_build_object(
                    'review_package_id', package.id::text,
                    'package_version', package.package_version,
                    'expected_generation', package.freshness_generation,
                    'package_digest', package.package_digest,
                    'policy_digest', package.suite_policy_digest,
                    'decision', decision.decision,
                    'reason', decision.reason,
                    'actor_type', decision.actor_type
                )
            )
        FROM review_packages AS package
        WHERE package.id = decision.review_package_id;

        UPDATE review_decisions
        SET decision_digest = review_canonical_digest(
            jsonb_build_object(
                'review_decision_id', id::text,
                'review_package_id', review_package_id::text,
                'package_version', package_version,
                'expected_generation', expected_generation,
                'package_digest', package_digest,
                'policy_digest', policy_digest,
                'decision', decision,
                'reason', reason,
                'actor_type', actor_type,
                'idempotency_key', idempotency_key,
                'idempotency_request_hash', idempotency_request_hash,
                'git_authorization', false,
                'deployment_authorization', false
            )
        )
        WHERE decision_digest IS NULL;
        """
    )
    for column_name in (
        "package_version",
        "expected_generation",
        "policy_digest",
        "idempotency_key",
        "idempotency_request_hash",
        "decision_digest",
    ):
        op.alter_column("review_decisions", column_name, nullable=False)
    op.create_unique_constraint(
        "uq_review_decisions_idempotency",
        "review_decisions",
        ["idempotency_key"],
    )

    op.execute(
        """
        UPDATE release_readiness_verdicts AS readiness
        SET package_version = package.package_version,
            freshness_generation = package.freshness_generation,
            decision_digest = decision.decision_digest,
            suite_result_digest = package.suite_result_digest,
            policy_digest = package.suite_policy_digest,
            blocker_summary_digest = package.blocker_summary_digest,
            critical_count = package.critical_count,
            high_count = package.high_count,
            blocking_medium_count = package.blocking_medium_count,
            verdict_digest = review_canonical_digest(jsonb_build_object(
                'review_package_id', package.id::text,
                'review_decision_id', decision.id::text,
                'package_version', package.package_version,
                'freshness_generation', package.freshness_generation,
                'package_digest', package.package_digest,
                'decision_digest', decision.decision_digest,
                'evidence_manifest_digest', package.evidence_manifest_digest,
                'suite_result_digest', package.suite_result_digest,
                'policy_digest', package.suite_policy_digest,
                'blocker_summary_digest', package.blocker_summary_digest,
                'critical_count', package.critical_count,
                'high_count', package.high_count,
                'blocking_medium_count', package.blocking_medium_count,
                'verdict', readiness.verdict,
                'reason_codes', readiness.reason_codes,
                'git_authorization', false,
                'deployment_authorization', false
            ))
        FROM review_packages AS package,
            review_decisions AS decision
        WHERE package.id = readiness.review_package_id
            AND decision.id = readiness.review_decision_id;
        """
    )
    for column_name in (
        "package_version",
        "freshness_generation",
        "suite_result_digest",
        "policy_digest",
        "blocker_summary_digest",
        "critical_count",
        "high_count",
        "blocking_medium_count",
    ):
        op.alter_column("release_readiness_verdicts", column_name, nullable=False)

    op.execute(
        """
        WITH review_events AS (
            SELECT event.id,
                (event.metadata ->> 'review_package_id')::uuid AS package_id,
                row_number() OVER (
                    PARTITION BY event.metadata ->> 'review_package_id'
                    ORDER BY event.created_at, event.id
                ) AS sequence
            FROM audit_events AS event
            WHERE event.event_type IN (
                'review_package_created',
                'review_package_invalidated',
                'review_decision_recorded',
                'release_readiness_evaluated'
            )
            AND event.metadata ? 'review_package_id'
        )
        UPDATE audit_events AS event
        SET review_package_id = review_events.package_id,
            review_sequence = review_events.sequence
        FROM review_events
        WHERE review_events.id = event.id;
        """
    )
    op.create_check_constraint(
        "ck_audit_review_sequence",
        "audit_events",
        "(review_package_id IS NULL AND review_sequence IS NULL) OR "
        "(review_package_id IS NOT NULL AND review_sequence >= 1)",
    )
    op.create_index(
        "uq_audit_review_sequence",
        "audit_events",
        ["review_package_id", "review_sequence"],
        unique=True,
        postgresql_where=sa.text("review_package_id IS NOT NULL"),
    )

    op.create_check_constraint(
        "ck_review_packages_schema_version",
        "review_packages",
        "schema_version IN (1, 2)",
    )
    op.create_check_constraint(
        "ck_review_packages_versions",
        "review_packages",
        "package_version >= 1 AND freshness_generation >= 1",
    )
    op.create_check_constraint(
        "ck_review_packages_digests",
        "review_packages",
        "package_digest ~ '^[0-9a-f]{64}$' "
        "AND evidence_manifest_digest ~ '^[0-9a-f]{64}$' "
        "AND suite_result_digest ~ '^[0-9a-f]{64}$' "
        "AND suite_policy_digest ~ '^[0-9a-f]{64}$' "
        "AND checkpoint_diff_hash ~ '^[0-9a-f]{64}$' "
        "AND blocker_summary_digest ~ '^[0-9a-f]{64}$' "
        "AND checkpoint_fingerprint ~ '^[0-9a-f]{64}$' "
        "AND idempotency_request_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_review_packages_manifest",
        "review_packages",
        "jsonb_typeof(evidence_manifest) = 'object' "
        "AND jsonb_array_length(evidence_manifest -> 'entries') = 2",
    )
    op.create_check_constraint(
        "ck_review_packages_blocker_summary",
        "review_packages",
        "jsonb_typeof(blocker_summary) = 'object' "
        "AND critical_count >= 0 AND high_count >= 0 "
        "AND blocking_medium_count >= 0",
    )
    op.create_check_constraint(
        "ck_review_decisions_digest",
        "review_decisions",
        "package_digest ~ '^[0-9a-f]{64}$' "
        "AND policy_digest ~ '^[0-9a-f]{64}$' "
        "AND idempotency_request_hash ~ '^[0-9a-f]{64}$' "
        "AND decision_digest ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_review_decisions_versions",
        "review_decisions",
        "package_version >= 1 AND expected_generation >= 1",
    )
    op.create_check_constraint(
        "ck_readiness_verdicts_digests",
        "release_readiness_verdicts",
        "package_digest ~ '^[0-9a-f]{64}$' "
        "AND decision_digest ~ '^[0-9a-f]{64}$' "
        "AND evidence_manifest_digest ~ '^[0-9a-f]{64}$' "
        "AND suite_result_digest ~ '^[0-9a-f]{64}$' "
        "AND policy_digest ~ '^[0-9a-f]{64}$' "
        "AND blocker_summary_digest ~ '^[0-9a-f]{64}$' "
        "AND verdict_digest ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_readiness_verdicts_versions_blockers",
        "release_readiness_verdicts",
        "package_version >= 1 AND freshness_generation >= 1 "
        "AND critical_count >= 0 AND high_count >= 0 "
        "AND blocking_medium_count >= 0",
    )

    for table_name in (
        "review_packages",
        "review_decisions",
        "release_readiness_verdicts",
    ):
        op.execute(f"ALTER TABLE {table_name} ENABLE TRIGGER {table_name}_immutable")


def _install_review_integrity_guards() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_audit_event_immutable()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'AuditEvent records are append-only'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_events_immutable
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION protect_audit_event_immutable();

        CREATE TRIGGER review_blocker_findings_immutable
        BEFORE UPDATE OR DELETE ON review_blocker_findings
        FOR EACH ROW EXECUTE FUNCTION protect_review_immutable();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_review_audit_event_insert()
        RETURNS trigger AS $$
        DECLARE expected_sequence integer;
        BEGIN
            IF NEW.event_type IN (
                'review_package_created',
                'review_package_invalidated',
                'review_decision_recorded',
                'release_readiness_evaluated'
            ) THEN
                IF NEW.review_package_id IS NULL
                    OR NEW.review_sequence IS NULL
                    OR NEW.metadata ->> 'review_package_id'
                        IS DISTINCT FROM NEW.review_package_id::text
                THEN
                    RAISE EXCEPTION 'Review AuditEvent binding is invalid'
                        USING ERRCODE = '55000';
                END IF;
                SELECT COALESCE(max(review_sequence), 0) + 1
                INTO expected_sequence
                FROM audit_events
                WHERE review_package_id = NEW.review_package_id;
                IF NEW.review_sequence IS DISTINCT FROM expected_sequence THEN
                    RAISE EXCEPTION 'Review AuditEvent sequence is invalid'
                        USING ERRCODE = '55000';
                END IF;
            ELSIF NEW.review_package_id IS NOT NULL OR NEW.review_sequence IS NOT NULL THEN
                RAISE EXCEPTION 'Non-review AuditEvent cannot claim review sequence'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_events_review_insert_guard
        BEFORE INSERT ON audit_events
        FOR EACH ROW EXECUTE FUNCTION guard_review_audit_event_insert();
        """
    )
    _replace_package_guard()
    _replace_invalidation_decision_readiness_guards()
    _install_blocker_guard()


def _replace_package_guard() -> None:
    op.execute("DROP TRIGGER review_packages_insert_guard ON review_packages")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_review_package_insert()
        RETURNS trigger AS $$
        DECLARE
            suite_run validation_suite_runs%ROWTYPE;
            suite_result validation_suite_results%ROWTYPE;
            workspace_row workspaces%ROWTYPE;
            checkpoint_row workspace_checkpoints%ROWTYPE;
            handle_row repository_handles%ROWTYPE;
            scope_row review_freshness_states%ROWTYPE;
            evidence_one validation_evidence%ROWTYPE;
            evidence_two validation_evidence%ROWTYPE;
            expected_entries jsonb;
            expected_manifest jsonb;
            finding_entries jsonb;
            expected_summary jsonb;
            expected_package jsonb;
            expected_critical integer;
            expected_high integer;
            expected_medium integer;
            summary_source_version integer;
            latest_checkpoint_id uuid;
            latest_result_id uuid;
        BEGIN
            SELECT * INTO suite_run FROM validation_suite_runs
            WHERE id = NEW.suite_run_id FOR UPDATE;
            SELECT * INTO suite_result FROM validation_suite_results
            WHERE id = NEW.suite_result_id;
            SELECT * INTO workspace_row FROM workspaces
            WHERE id = NEW.workspace_id FOR UPDATE;
            SELECT * INTO checkpoint_row FROM workspace_checkpoints
            WHERE id = NEW.checkpoint_id;
            SELECT * INTO handle_row FROM repository_handles
            WHERE id = NEW.repository_handle_id FOR UPDATE;
            SELECT * INTO scope_row FROM review_freshness_states
            WHERE id = NEW.freshness_state_id FOR UPDATE;
            SELECT * INTO evidence_one FROM validation_evidence
            WHERE id = (suite_result.evidence_references #>> '{0,evidence_id}')::uuid;
            SELECT * INTO evidence_two FROM validation_evidence
            WHERE id = (suite_result.evidence_references #>> '{1,evidence_id}')::uuid;

            expected_entries := jsonb_build_array(
                suite_result.evidence_references -> 0 || jsonb_build_object(
                    'side_effect_permit_id', evidence_one.side_effect_permit_id::text,
                    'side_effect_permit_sequence', evidence_one.side_effect_permit_sequence,
                    'side_effect_permit_digest', evidence_one.side_effect_permit_digest,
                    'fencing_token', evidence_one.fencing_token,
                    'execution_envelope_digest', evidence_one.execution_envelope_digest
                ),
                suite_result.evidence_references -> 1 || jsonb_build_object(
                    'side_effect_permit_id', evidence_two.side_effect_permit_id::text,
                    'side_effect_permit_sequence', evidence_two.side_effect_permit_sequence,
                    'side_effect_permit_digest', evidence_two.side_effect_permit_digest,
                    'fencing_token', evidence_two.fencing_token,
                    'execution_envelope_digest', evidence_two.execution_envelope_digest
                )
            );
            expected_manifest := jsonb_build_object(
                'schema_version', 2,
                'plan_id', suite_run.plan_id::text,
                'workspace_id', suite_run.workspace_id::text,
                'suite_run_id', suite_run.id::text,
                'suite_result_id', suite_result.id::text,
                'suite', suite_run.suite_id || chr(58) || 'v'
                    || suite_run.suite_version::text,
                'suite_id', suite_run.suite_id,
                'suite_version', suite_run.suite_version,
                'policy_digest', suite_run.policy_digest,
                'execution_grant_id', suite_run.execution_grant_id::text,
                'root_suite_run_id', suite_run.root_suite_run_id::text,
                'attempt_number', suite_run.attempt_number,
                'source_revision', suite_run.source_revision,
                'checkpoint_id', suite_run.checkpoint_id::text,
                'checkpoint_fingerprint', suite_run.checkpoint_fingerprint,
                'checkpoint_diff_hash', checkpoint_row.diff_hash,
                'suite_result_digest', suite_result.aggregate_digest,
                'profiles', suite_result.profile_references,
                'entries', expected_entries,
                'artifact_count', 0,
                'artifact_bytes', 0,
                'cleanup_succeeded', true,
                'source_invariant', true,
                'canonical_workspace_invariant', true,
                'freshness_generation', NEW.freshness_generation
            );

            WITH ranked AS (
                SELECT finding.*,
                    row_number() OVER (
                        PARTITION BY finding.finding_key
                        ORDER BY finding.finding_version DESC, finding.created_at DESC,
                            finding.id DESC
                    ) AS rank
                FROM review_blocker_findings AS finding
                WHERE finding.plan_id = NEW.plan_id
                    AND finding.workspace_id = NEW.workspace_id
                    AND finding.checkpoint_id = NEW.checkpoint_id
            ),
            active AS (
                SELECT * FROM ranked WHERE rank = 1 AND status = 'open'
            )
            SELECT
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'finding_key', finding_key,
                            'finding_version', finding_version,
                            'severity', severity,
                            'blocking', blocking,
                            'source', source,
                            'source_version', source_version,
                            'evidence_digest', evidence_digest,
                            'policy_digest', policy_digest,
                            'finding_digest', finding_digest
                        ) ORDER BY finding_key
                    ),
                    '[]'::jsonb
                ),
                count(*) FILTER (WHERE severity = 'critical'),
                count(*) FILTER (WHERE severity = 'high'),
                count(*) FILTER (WHERE severity = 'medium' AND blocking),
                COALESCE(max(source_version), 1)
            INTO finding_entries, expected_critical, expected_high,
                expected_medium, summary_source_version
            FROM active;

            expected_summary := jsonb_build_object(
                'schema_version', 1,
                'source', 'governed-review-security-findings',
                'source_version', summary_source_version,
                'plan_id', NEW.plan_id::text,
                'workspace_id', NEW.workspace_id::text,
                'checkpoint_id', NEW.checkpoint_id::text,
                'suite_result_id', NEW.suite_result_id::text,
                'suite_result_digest', NEW.suite_result_digest,
                'evidence_manifest_digest', NEW.evidence_manifest_digest,
                'policy_digest', NEW.suite_policy_digest,
                'freshness_generation', NEW.freshness_generation,
                'critical_count', expected_critical,
                'high_count', expected_high,
                'blocking_medium_count', expected_medium,
                'findings', finding_entries
            );
            expected_package := jsonb_build_object(
                'schema_version', 2,
                'package_id', NEW.id::text,
                'package_version', NEW.package_version,
                'freshness_state_id', NEW.freshness_state_id::text,
                'freshness_generation', NEW.freshness_generation,
                'run_id', NEW.run_id::text,
                'plan_id', NEW.plan_id::text,
                'repository_handle_id', NEW.repository_handle_id::text,
                'source_revision', NEW.source_revision,
                'workspace_id', NEW.workspace_id::text,
                'checkpoint_id', NEW.checkpoint_id::text,
                'checkpoint_fingerprint', NEW.checkpoint_fingerprint,
                'checkpoint_diff_hash', NEW.checkpoint_diff_hash,
                'suite_run_id', NEW.suite_run_id::text,
                'suite_result_id', NEW.suite_result_id::text,
                'execution_grant_id', NEW.execution_grant_id::text,
                'suite_policy_digest', NEW.suite_policy_digest,
                'suite_result_digest', NEW.suite_result_digest,
                'evidence_manifest_digest', NEW.evidence_manifest_digest,
                'blocker_summary_digest', NEW.blocker_summary_digest,
                'git_authorization', false,
                'deployment_authorization', false
            );

            SELECT id INTO latest_checkpoint_id
            FROM workspace_checkpoints
            WHERE workspace_id = NEW.workspace_id
            ORDER BY sequence DESC, created_at DESC, id DESC LIMIT 1;
            SELECT result.id INTO latest_result_id
            FROM validation_suite_results AS result
            JOIN validation_suite_runs AS run ON run.id = result.suite_run_id
            WHERE run.plan_id = NEW.plan_id
                AND result.checkpoint_id = NEW.checkpoint_id
                AND result.verdict = 'succeeded'
            ORDER BY result.created_at DESC, result.id DESC LIMIT 1;

            IF NEW.schema_version IS DISTINCT FROM 2
                OR suite_run.id IS NULL OR suite_result.id IS NULL
                OR workspace_row.id IS NULL OR checkpoint_row.id IS NULL
                OR handle_row.id IS NULL OR scope_row.id IS NULL
                OR evidence_one.id IS NULL OR evidence_two.id IS NULL
                OR suite_run.state IS DISTINCT FROM 'succeeded'
                OR suite_result.verdict IS DISTINCT FROM 'succeeded'
                OR suite_result.suite_run_id IS DISTINCT FROM suite_run.id
                OR suite_run.run_id IS DISTINCT FROM NEW.run_id
                OR suite_run.plan_id IS DISTINCT FROM NEW.plan_id
                OR suite_run.workspace_id IS DISTINCT FROM NEW.workspace_id
                OR suite_run.checkpoint_id IS DISTINCT FROM NEW.checkpoint_id
                OR suite_run.execution_grant_id IS DISTINCT FROM NEW.execution_grant_id
                OR suite_run.policy_digest IS DISTINCT FROM NEW.suite_policy_digest
                OR suite_result.aggregate_digest IS DISTINCT FROM NEW.suite_result_digest
                OR checkpoint_row.diff_hash IS DISTINCT FROM NEW.checkpoint_diff_hash
                OR workspace_row.repository_handle_id IS DISTINCT FROM NEW.repository_handle_id
                OR scope_row.plan_id IS DISTINCT FROM NEW.plan_id
                OR scope_row.workspace_id IS DISTINCT FROM NEW.workspace_id
                OR scope_row.checkpoint_id IS DISTINCT FROM NEW.checkpoint_id
                OR scope_row.generation IS DISTINCT FROM NEW.freshness_generation
                OR workspace_row.source_revision IS DISTINCT FROM NEW.source_revision
                OR checkpoint_row.source_revision IS DISTINCT FROM NEW.source_revision
                OR handle_row.current_revision IS DISTINCT FROM NEW.source_revision
                OR handle_row.status IS DISTINCT FROM 'available'
                OR workspace_row.current_tree_hash IS DISTINCT FROM NEW.checkpoint_fingerprint
                OR checkpoint_row.tree_fingerprint IS DISTINCT FROM NEW.checkpoint_fingerprint
                OR latest_checkpoint_id IS DISTINCT FROM NEW.checkpoint_id
                OR latest_result_id IS DISTINCT FROM NEW.suite_result_id
                OR jsonb_array_length(suite_result.evidence_references) IS DISTINCT FROM 2
                OR NEW.evidence_manifest IS DISTINCT FROM expected_manifest
                OR NEW.evidence_manifest_digest
                    IS DISTINCT FROM review_canonical_digest(expected_manifest)
                OR NEW.blocker_summary IS DISTINCT FROM expected_summary
                OR NEW.blocker_summary_digest
                    IS DISTINCT FROM review_canonical_digest(expected_summary)
                OR NEW.blocker_source IS DISTINCT FROM 'governed-review-security-findings'
                OR NEW.blocker_source_version IS DISTINCT FROM summary_source_version
                OR NEW.critical_count IS DISTINCT FROM expected_critical
                OR NEW.high_count IS DISTINCT FROM expected_high
                OR NEW.blocking_medium_count IS DISTINCT FROM expected_medium
                OR NEW.package_digest IS DISTINCT FROM review_canonical_digest(expected_package)
                OR EXISTS (
                    SELECT 1 FROM validation_runs AS validation
                    WHERE validation.plan_id = NEW.plan_id
                        AND validation.checkpoint_id = NEW.checkpoint_id
                        AND validation.created_at > suite_result.created_at
                )
                OR EXISTS (
                    SELECT 1 FROM validation_suite_runs AS later_suite
                    WHERE later_suite.plan_id = NEW.plan_id
                        AND later_suite.checkpoint_id = NEW.checkpoint_id
                        AND later_suite.created_at > suite_run.created_at
                )
            THEN
                RAISE EXCEPTION 'Review Package canonical proof is invalid or stale'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER review_packages_insert_guard
        BEFORE INSERT ON review_packages
        FOR EACH ROW EXECUTE FUNCTION guard_review_package_insert();
        """
    )


def _replace_invalidation_decision_readiness_guards() -> None:
    op.execute("DROP TRIGGER review_decisions_insert_guard ON review_decisions")
    op.execute("DROP TRIGGER readiness_verdicts_insert_guard ON release_readiness_verdicts")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_review_decision_insert()
        RETURNS trigger AS $$
        DECLARE
            package_row review_packages%ROWTYPE;
            scope_row review_freshness_states%ROWTYPE;
            expected_request_hash text;
            expected_decision_digest text;
        BEGIN
            SELECT * INTO package_row FROM review_packages
            WHERE id = NEW.review_package_id FOR UPDATE;
            SELECT * INTO scope_row FROM review_freshness_states
            WHERE id = package_row.freshness_state_id FOR UPDATE;
            expected_request_hash := review_canonical_digest(jsonb_build_object(
                'review_package_id', package_row.id::text,
                'package_version', package_row.package_version,
                'expected_generation', NEW.expected_generation,
                'package_digest', package_row.package_digest,
                'policy_digest', package_row.suite_policy_digest,
                'decision', NEW.decision,
                'reason', NEW.reason,
                'actor_type', NEW.actor_type
            ));
            expected_decision_digest := review_canonical_digest(jsonb_build_object(
                'review_decision_id', NEW.id::text,
                'review_package_id', package_row.id::text,
                'package_version', NEW.package_version,
                'expected_generation', NEW.expected_generation,
                'package_digest', NEW.package_digest,
                'policy_digest', NEW.policy_digest,
                'decision', NEW.decision,
                'reason', NEW.reason,
                'actor_type', NEW.actor_type,
                'idempotency_key', NEW.idempotency_key,
                'idempotency_request_hash', NEW.idempotency_request_hash,
                'git_authorization', false,
                'deployment_authorization', false
            ));
            IF package_row.id IS NULL OR package_row.schema_version IS DISTINCT FROM 2
                OR scope_row.id IS NULL
                OR NEW.package_version IS DISTINCT FROM package_row.package_version
                OR NEW.expected_generation IS DISTINCT FROM package_row.freshness_generation
                OR scope_row.generation IS DISTINCT FROM NEW.expected_generation
                OR NEW.package_digest IS DISTINCT FROM package_row.package_digest
                OR NEW.policy_digest IS DISTINCT FROM package_row.suite_policy_digest
                OR NEW.idempotency_request_hash IS DISTINCT FROM expected_request_hash
                OR NEW.decision_digest IS DISTINCT FROM expected_decision_digest
                OR EXISTS (
                    SELECT 1 FROM review_package_invalidations
                    WHERE review_package_id = package_row.id
                )
                OR (
                    NEW.decision = 'approve'
                    AND (
                        package_row.critical_count <> 0
                        OR package_row.high_count <> 0
                        OR package_row.blocking_medium_count <> 0
                    )
                )
            THEN
                RAISE EXCEPTION 'Stale or inconsistent Review Package cannot be decided'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER review_decisions_insert_guard
        BEFORE INSERT ON review_decisions
        FOR EACH ROW EXECUTE FUNCTION guard_review_decision_insert();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_readiness_insert()
        RETURNS trigger AS $$
        DECLARE
            package_row review_packages%ROWTYPE;
            decision_row review_decisions%ROWTYPE;
            scope_row review_freshness_states%ROWTYPE;
            expected_verdict_digest text;
        BEGIN
            SELECT * INTO package_row FROM review_packages
            WHERE id = NEW.review_package_id FOR UPDATE;
            SELECT * INTO decision_row FROM review_decisions
            WHERE id = NEW.review_decision_id FOR UPDATE;
            SELECT * INTO scope_row FROM review_freshness_states
            WHERE id = package_row.freshness_state_id FOR UPDATE;
            expected_verdict_digest := review_canonical_digest(jsonb_build_object(
                'review_package_id', NEW.review_package_id::text,
                'review_decision_id', NEW.review_decision_id::text,
                'package_version', NEW.package_version,
                'freshness_generation', NEW.freshness_generation,
                'package_digest', NEW.package_digest,
                'decision_digest', NEW.decision_digest,
                'evidence_manifest_digest', NEW.evidence_manifest_digest,
                'suite_result_digest', NEW.suite_result_digest,
                'policy_digest', NEW.policy_digest,
                'blocker_summary_digest', NEW.blocker_summary_digest,
                'critical_count', NEW.critical_count,
                'high_count', NEW.high_count,
                'blocking_medium_count', NEW.blocking_medium_count,
                'verdict', NEW.verdict,
                'reason_codes', NEW.reason_codes,
                'git_authorization', false,
                'deployment_authorization', false
            ));
            IF package_row.id IS NULL OR decision_row.id IS NULL
                OR package_row.schema_version IS DISTINCT FROM 2
                OR decision_row.review_package_id IS DISTINCT FROM package_row.id
                OR NEW.package_version IS DISTINCT FROM package_row.package_version
                OR NEW.freshness_generation IS DISTINCT FROM package_row.freshness_generation
                OR NEW.package_digest IS DISTINCT FROM package_row.package_digest
                OR NEW.package_digest IS DISTINCT FROM decision_row.package_digest
                OR NEW.decision_digest IS DISTINCT FROM decision_row.decision_digest
                OR NEW.evidence_manifest_digest
                    IS DISTINCT FROM package_row.evidence_manifest_digest
                OR NEW.suite_result_digest IS DISTINCT FROM package_row.suite_result_digest
                OR NEW.policy_digest IS DISTINCT FROM package_row.suite_policy_digest
                OR NEW.blocker_summary_digest
                    IS DISTINCT FROM package_row.blocker_summary_digest
                OR NEW.critical_count IS DISTINCT FROM package_row.critical_count
                OR NEW.high_count IS DISTINCT FROM package_row.high_count
                OR NEW.blocking_medium_count
                    IS DISTINCT FROM package_row.blocking_medium_count
                OR NEW.verdict_digest IS DISTINCT FROM expected_verdict_digest
            THEN
                RAISE EXCEPTION 'Readiness canonical proof binding is invalid'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.verdict = 'ready' AND (
                decision_row.decision IS DISTINCT FROM 'approve'
                OR scope_row.generation IS DISTINCT FROM NEW.freshness_generation
                OR EXISTS (
                    SELECT 1 FROM review_package_invalidations
                    WHERE review_package_id = package_row.id
                )
                OR NEW.critical_count <> 0
                OR NEW.high_count <> 0
                OR NEW.blocking_medium_count <> 0
                OR jsonb_array_length(NEW.reason_codes) <> 1
                OR NEW.reason_codes ->> 0 IS DISTINCT FROM 'all_required_evidence_verified'
            ) THEN
                RAISE EXCEPTION 'Blocking findings or rejected review cannot be ready'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER readiness_verdicts_insert_guard
        BEFORE INSERT ON release_readiness_verdicts
        FOR EACH ROW EXECUTE FUNCTION guard_readiness_insert();
        """
    )


def _install_blocker_guard() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_review_blocker_insert()
        RETURNS trigger AS $$
        DECLARE expected_version integer;
        DECLARE expected_digest text;
        BEGIN
            SELECT COALESCE(max(finding_version), 0) + 1
            INTO expected_version
            FROM review_blocker_findings
            WHERE plan_id = NEW.plan_id
                AND workspace_id = NEW.workspace_id
                AND checkpoint_id = NEW.checkpoint_id
                AND finding_key = NEW.finding_key;
            expected_digest := review_canonical_digest(jsonb_build_object(
                'plan_id', NEW.plan_id::text,
                'workspace_id', NEW.workspace_id::text,
                'checkpoint_id', NEW.checkpoint_id::text,
                'finding_key', NEW.finding_key,
                'finding_version', NEW.finding_version,
                'severity', NEW.severity,
                'blocking', NEW.blocking,
                'status', NEW.status,
                'source', NEW.source,
                'source_version', NEW.source_version,
                'evidence_digest', NEW.evidence_digest,
                'policy_digest', NEW.policy_digest
            ));
            IF NEW.source IS DISTINCT FROM 'governed-review-security-findings'
                OR NEW.finding_version IS DISTINCT FROM expected_version
                OR NEW.finding_digest IS DISTINCT FROM expected_digest
            THEN
                RAISE EXCEPTION 'Blocker Finding canonical proof is invalid'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER review_blocker_findings_insert_guard
        BEFORE INSERT ON review_blocker_findings
        FOR EACH ROW EXECUTE FUNCTION guard_review_blocker_insert();
        """
    )


def _install_freshness_triggers() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION bump_review_freshness_scope(
            target_plan uuid,
            target_workspace uuid,
            target_checkpoint uuid,
            change_kind text,
            invalidation_reason text
        )
        RETURNS void AS $$
        DECLARE scope_row review_freshness_states%ROWTYPE;
        DECLARE package_row review_packages%ROWTYPE;
        DECLARE next_sequence integer;
        BEGIN
            UPDATE review_freshness_states
            SET generation = generation + 1,
                last_change_kind = change_kind,
                updated_at = CURRENT_TIMESTAMP
            WHERE plan_id = target_plan
                AND workspace_id = target_workspace
                AND checkpoint_id = target_checkpoint
            RETURNING * INTO scope_row;
            IF scope_row.id IS NULL THEN
                RETURN;
            END IF;
            FOR package_row IN
                SELECT * FROM review_packages
                WHERE freshness_state_id = scope_row.id
                    AND freshness_generation < scope_row.generation
                FOR UPDATE
            LOOP
                INSERT INTO review_package_invalidations (
                    id, review_package_id, package_digest, reason_code,
                    observed_value, request_id
                )
                VALUES (
                    gen_random_uuid(), package_row.id, package_row.package_digest,
                    invalidation_reason, change_kind, 'database-freshness-trigger'
                )
                ON CONFLICT (review_package_id) DO NOTHING;
                IF FOUND THEN
                    SELECT COALESCE(max(review_sequence), 0) + 1
                    INTO next_sequence
                    FROM audit_events
                    WHERE review_package_id = package_row.id;
                    INSERT INTO audit_events (
                        id, run_id, event_type, actor_type, request_id, metadata,
                        review_package_id, review_sequence
                    )
                    VALUES (
                        gen_random_uuid(), package_row.run_id,
                        'review_package_invalidated', 'system',
                        'database-freshness-trigger',
                        jsonb_build_object(
                            'review_package_id', package_row.id::text,
                            'reason_code', invalidation_reason,
                            'change_kind', change_kind,
                            'package_digest', package_row.package_digest,
                            'freshness_generation', scope_row.generation
                        ),
                        package_row.id, next_sequence
                    );
                END IF;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;

        CREATE OR REPLACE FUNCTION bump_review_freshness_workspace(
            target_workspace uuid,
            change_kind text,
            invalidation_reason text
        )
        RETURNS void AS $$
        DECLARE scope_row review_freshness_states%ROWTYPE;
        BEGIN
            FOR scope_row IN
                SELECT * FROM review_freshness_states
                WHERE workspace_id = target_workspace
            LOOP
                PERFORM bump_review_freshness_scope(
                    scope_row.plan_id, scope_row.workspace_id,
                    scope_row.checkpoint_id, change_kind, invalidation_reason
                );
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION review_validation_fact_changed()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                PERFORM bump_review_freshness_scope(
                    OLD.plan_id, OLD.workspace_id, OLD.checkpoint_id,
                    TG_TABLE_NAME || ':' || TG_OP, 'validation_facts_changed'
                );
                RETURN OLD;
            END IF;
            PERFORM bump_review_freshness_scope(
                NEW.plan_id, NEW.workspace_id, NEW.checkpoint_id,
                TG_TABLE_NAME || ':' || TG_OP, 'validation_facts_changed'
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER validation_runs_review_freshness
        AFTER INSERT OR UPDATE OR DELETE ON validation_runs
        FOR EACH ROW EXECUTE FUNCTION review_validation_fact_changed();

        CREATE TRIGGER validation_suite_runs_review_freshness
        AFTER INSERT OR UPDATE OR DELETE ON validation_suite_runs
        FOR EACH ROW EXECUTE FUNCTION review_validation_fact_changed();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION review_evidence_fact_changed()
        RETURNS trigger AS $$
        DECLARE evidence_row validation_evidence%ROWTYPE;
        DECLARE validation_row validation_runs%ROWTYPE;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                evidence_row := OLD;
            ELSE
                evidence_row := NEW;
            END IF;
            SELECT * INTO validation_row FROM validation_runs
            WHERE id = evidence_row.validation_run_id;
            IF validation_row.id IS NOT NULL THEN
                PERFORM bump_review_freshness_scope(
                    validation_row.plan_id, validation_row.workspace_id,
                    validation_row.checkpoint_id,
                    TG_TABLE_NAME || ':' || TG_OP, 'validation_facts_changed'
                );
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER validation_evidence_review_freshness
        AFTER INSERT OR UPDATE OR DELETE ON validation_evidence
        FOR EACH ROW EXECUTE FUNCTION review_evidence_fact_changed();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION review_suite_result_changed()
        RETURNS trigger AS $$
        DECLARE result_row validation_suite_results%ROWTYPE;
        DECLARE suite_row validation_suite_runs%ROWTYPE;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                result_row := OLD;
            ELSE
                result_row := NEW;
            END IF;
            SELECT * INTO suite_row FROM validation_suite_runs
            WHERE id = result_row.suite_run_id;
            IF suite_row.id IS NOT NULL THEN
                PERFORM bump_review_freshness_scope(
                    suite_row.plan_id, suite_row.workspace_id, suite_row.checkpoint_id,
                    TG_TABLE_NAME || ':' || TG_OP, 'validation_facts_changed'
                );
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER validation_suite_results_review_freshness
        AFTER INSERT OR UPDATE OR DELETE ON validation_suite_results
        FOR EACH ROW EXECUTE FUNCTION review_suite_result_changed();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION review_grant_changed()
        RETURNS trigger AS $$
        DECLARE grant_row execution_grants%ROWTYPE;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                grant_row := OLD;
            ELSE
                grant_row := NEW;
            END IF;
            IF grant_row.validation_checkpoint_id IS NOT NULL
                AND grant_row.validation_workspace_id IS NOT NULL
            THEN
                PERFORM bump_review_freshness_scope(
                    grant_row.plan_id, grant_row.validation_workspace_id,
                    grant_row.validation_checkpoint_id,
                    TG_TABLE_NAME || ':' || TG_OP, 'grant_lineage_changed'
                );
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER execution_grants_review_freshness
        AFTER INSERT OR UPDATE OR DELETE ON execution_grants
        FOR EACH ROW EXECUTE FUNCTION review_grant_changed();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION review_workspace_changed()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.source_revision IS DISTINCT FROM NEW.source_revision
                OR OLD.current_tree_hash IS DISTINCT FROM NEW.current_tree_hash
            THEN
                PERFORM bump_review_freshness_workspace(
                    NEW.id, 'workspaces:UPDATE', 'workspace_changed'
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER workspaces_review_freshness
        AFTER UPDATE ON workspaces
        FOR EACH ROW EXECUTE FUNCTION review_workspace_changed();

        CREATE OR REPLACE FUNCTION review_checkpoint_changed()
        RETURNS trigger AS $$
        DECLARE checkpoint_row workspace_checkpoints%ROWTYPE;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                checkpoint_row := OLD;
            ELSE
                checkpoint_row := NEW;
            END IF;
            PERFORM bump_review_freshness_workspace(
                checkpoint_row.workspace_id,
                TG_TABLE_NAME || ':' || TG_OP,
                'checkpoint_superseded'
            );
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER workspace_checkpoints_review_freshness
        AFTER INSERT OR UPDATE OR DELETE ON workspace_checkpoints
        FOR EACH ROW EXECUTE FUNCTION review_checkpoint_changed();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION review_blocker_changed()
        RETURNS trigger AS $$
        BEGIN
            PERFORM bump_review_freshness_scope(
                NEW.plan_id, NEW.workspace_id, NEW.checkpoint_id,
                'review_blocker_findings:INSERT', 'blocker_summary_changed'
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER review_blocker_findings_freshness
        AFTER INSERT ON review_blocker_findings
        FOR EACH ROW EXECUTE FUNCTION review_blocker_changed();
        """
    )


def downgrade() -> None:
    for table, trigger in (
        ("review_blocker_findings", "review_blocker_findings_freshness"),
        ("workspace_checkpoints", "workspace_checkpoints_review_freshness"),
        ("workspaces", "workspaces_review_freshness"),
        ("execution_grants", "execution_grants_review_freshness"),
        ("validation_suite_results", "validation_suite_results_review_freshness"),
        ("validation_evidence", "validation_evidence_review_freshness"),
        ("validation_suite_runs", "validation_suite_runs_review_freshness"),
        ("validation_runs", "validation_runs_review_freshness"),
        ("review_blocker_findings", "review_blocker_findings_insert_guard"),
        ("review_blocker_findings", "review_blocker_findings_immutable"),
        ("audit_events", "audit_events_review_insert_guard"),
        ("audit_events", "audit_events_immutable"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")

    for function_name in (
        "review_blocker_changed",
        "review_checkpoint_changed",
        "review_workspace_changed",
        "review_grant_changed",
        "review_suite_result_changed",
        "review_evidence_fact_changed",
        "review_validation_fact_changed",
        "bump_review_freshness_workspace",
        "bump_review_freshness_scope",
        "guard_review_blocker_insert",
        "guard_review_audit_event_insert",
        "protect_audit_event_immutable",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS {function_name} CASCADE")

    op.drop_index("uq_audit_review_sequence", table_name="audit_events")
    op.drop_constraint("ck_audit_review_sequence", "audit_events", type_="check")
    op.drop_constraint("fk_audit_events_review_package", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "review_sequence")
    op.drop_column("audit_events", "review_package_id")

    op.drop_constraint(
        "ck_readiness_verdicts_versions_blockers",
        "release_readiness_verdicts",
        type_="check",
    )
    op.drop_constraint(
        "ck_readiness_verdicts_digests",
        "release_readiness_verdicts",
        type_="check",
    )
    for column_name in (
        "blocking_medium_count",
        "high_count",
        "critical_count",
        "blocker_summary_digest",
        "policy_digest",
        "suite_result_digest",
        "freshness_generation",
        "package_version",
    ):
        op.drop_column("release_readiness_verdicts", column_name)

    op.drop_constraint("ck_review_decisions_versions", "review_decisions", type_="check")
    op.drop_constraint("ck_review_decisions_digest", "review_decisions", type_="check")
    op.drop_constraint(
        "uq_review_decisions_idempotency",
        "review_decisions",
        type_="unique",
    )
    for column_name in (
        "decision_digest",
        "idempotency_request_hash",
        "idempotency_key",
        "policy_digest",
        "expected_generation",
        "package_version",
    ):
        op.drop_column("review_decisions", column_name)

    op.drop_constraint(
        "ck_review_invalidations_reason",
        "review_package_invalidations",
        type_="check",
    )
    op.create_check_constraint(
        "ck_review_invalidations_reason",
        "review_package_invalidations",
        "reason_code IN ('workspace_changed', 'checkpoint_superseded', "
        "'source_revision_changed', 'suite_result_superseded', "
        "'evidence_integrity_failed')",
    )

    op.drop_constraint(
        "ck_review_packages_blocker_summary",
        "review_packages",
        type_="check",
    )
    op.drop_constraint("ck_review_packages_versions", "review_packages", type_="check")
    op.drop_constraint("ck_review_packages_digests", "review_packages", type_="check")
    op.drop_constraint("ck_review_packages_manifest", "review_packages", type_="check")
    op.drop_constraint(
        "ck_review_packages_schema_version",
        "review_packages",
        type_="check",
    )
    op.drop_constraint(
        "uq_review_packages_result_generation",
        "review_packages",
        type_="unique",
    )
    op.drop_constraint(
        "fk_review_packages_execution_grant",
        "review_packages",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_review_packages_freshness_state",
        "review_packages",
        type_="foreignkey",
    )
    for column_name in (
        "blocking_medium_count",
        "high_count",
        "critical_count",
        "blocker_source_version",
        "blocker_source",
        "blocker_summary_digest",
        "blocker_summary",
        "suite_policy_digest",
        "execution_grant_id",
        "checkpoint_diff_hash",
        "freshness_generation",
        "freshness_state_id",
        "package_version",
    ):
        op.drop_column("review_packages", column_name)
    op.execute("DROP TRIGGER review_packages_immutable ON review_packages")
    op.execute("UPDATE review_packages SET schema_version = 1")
    op.execute(
        """
        CREATE TRIGGER review_packages_immutable
        BEFORE UPDATE OR DELETE ON review_packages
        FOR EACH ROW EXECUTE FUNCTION protect_review_immutable()
        """
    )
    op.create_unique_constraint(
        "uq_review_packages_suite_result",
        "review_packages",
        ["suite_result_id"],
    )
    op.create_check_constraint(
        "ck_review_packages_schema_version",
        "review_packages",
        "schema_version = 1",
    )
    op.create_check_constraint(
        "ck_review_packages_digests",
        "review_packages",
        "package_digest ~ '^[0-9a-f]{64}$' "
        "AND evidence_manifest_digest ~ '^[0-9a-f]{64}$' "
        "AND suite_result_digest ~ '^[0-9a-f]{64}$' "
        "AND checkpoint_fingerprint ~ '^[0-9a-f]{64}$' "
        "AND idempotency_request_hash ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_review_packages_manifest",
        "review_packages",
        "jsonb_typeof(evidence_manifest) = 'object' "
        "AND jsonb_array_length(evidence_manifest -> 'entries') = 2",
    )

    op.drop_index("ix_review_blockers_scope", table_name="review_blocker_findings")
    op.drop_table("review_blocker_findings")
    op.drop_index("ix_review_freshness_workspace", table_name="review_freshness_states")
    op.drop_table("review_freshness_states")
    op.execute("DROP FUNCTION IF EXISTS review_canonical_digest(jsonb)")
