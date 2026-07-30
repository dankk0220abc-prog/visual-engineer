"""Add governed final review and release readiness.

Revision ID: 20260730_0010
Revises: 20260730_0009
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_0010"
down_revision: str | None = "20260730_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_handle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_revision", sa.String(length=64), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checkpoint_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("suite_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suite_result_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "evidence_manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("evidence_manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("package_digest", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("idempotency_request_hash", sa.String(length=64), nullable=False),
        sa.Column("git_authorization", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "deployment_authorization",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("schema_version = 1", name="ck_review_packages_schema_version"),
        sa.CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$' "
            "AND evidence_manifest_digest ~ '^[0-9a-f]{64}$' "
            "AND suite_result_digest ~ '^[0-9a-f]{64}$' "
            "AND checkpoint_fingerprint ~ '^[0-9a-f]{64}$' "
            "AND idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_review_packages_digests",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence_manifest) = 'object' "
            "AND jsonb_array_length(evidence_manifest -> 'entries') = 2",
            name="ck_review_packages_manifest",
        ),
        sa.CheckConstraint(
            "git_authorization = false AND deployment_authorization = false",
            name="ck_review_packages_no_delivery_authority",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["repository_handle_id"], ["repository_handles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["checkpoint_id"], ["workspace_checkpoints.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["suite_run_id"], ["validation_suite_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["suite_result_id"], ["validation_suite_results.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("suite_result_id", name="uq_review_packages_suite_result"),
        sa.UniqueConstraint("idempotency_key", name="uq_review_packages_idempotency"),
    )
    op.create_index(
        "ix_review_packages_run_created",
        "review_packages",
        ["run_id", "created_at"],
    )
    op.create_index(
        "ix_review_packages_workspace_created",
        "review_packages",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "review_package_invalidations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_digest", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=False),
        sa.Column("observed_value", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reason_code IN ('workspace_changed', 'checkpoint_superseded', "
            "'source_revision_changed', 'suite_result_superseded', "
            "'evidence_integrity_failed')",
            name="ck_review_invalidations_reason",
        ),
        sa.CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$'",
            name="ck_review_invalidations_digest",
        ),
        sa.ForeignKeyConstraint(["review_package_id"], ["review_packages.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_package_id", name="uq_review_invalidations_package"),
    )

    op.create_table(
        "review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_digest", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=2000), nullable=True),
        sa.Column(
            "actor_type",
            sa.String(length=32),
            server_default="local_user",
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("git_authorization", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "deployment_authorization",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('approve', 'reject')",
            name="ck_review_decisions_decision",
        ),
        sa.CheckConstraint("actor_type = 'local_user'", name="ck_review_decisions_actor"),
        sa.CheckConstraint(
            "decision <> 'reject' OR (reason IS NOT NULL AND char_length(trim(reason)) > 0)",
            name="ck_review_decisions_reject_reason",
        ),
        sa.CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$'",
            name="ck_review_decisions_digest",
        ),
        sa.CheckConstraint(
            "git_authorization = false AND deployment_authorization = false",
            name="ck_review_decisions_no_delivery_authority",
        ),
        sa.ForeignKeyConstraint(["review_package_id"], ["review_packages.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_package_id", name="uq_review_decisions_package"),
    )

    op.create_table(
        "release_readiness_verdicts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_digest", sa.String(length=64), nullable=False),
        sa.Column("decision_digest", sa.String(length=64), nullable=False),
        sa.Column("evidence_manifest_digest", sa.String(length=64), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verdict_digest", sa.String(length=64), nullable=False),
        sa.Column("git_authorization", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "deployment_authorization",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "verdict IN ('ready', 'not_ready')",
            name="ck_readiness_verdicts_verdict",
        ),
        sa.CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$' "
            "AND decision_digest ~ '^[0-9a-f]{64}$' "
            "AND evidence_manifest_digest ~ '^[0-9a-f]{64}$' "
            "AND verdict_digest ~ '^[0-9a-f]{64}$'",
            name="ck_readiness_verdicts_digests",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(reason_codes) = 'array' "
            "AND jsonb_array_length(reason_codes) BETWEEN 1 AND 8",
            name="ck_readiness_verdicts_reasons",
        ),
        sa.CheckConstraint(
            "git_authorization = false AND deployment_authorization = false",
            name="ck_readiness_verdicts_no_delivery_authority",
        ),
        sa.ForeignKeyConstraint(["review_package_id"], ["review_packages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["review_decision_id"], ["review_decisions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_package_id", name="uq_readiness_verdicts_package"),
        sa.UniqueConstraint("review_decision_id", name="uq_readiness_verdicts_decision"),
    )
    _install_review_guards()


def _install_review_guards() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_review_immutable()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'governed review records are immutable'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in (
        "review_packages",
        "review_package_invalidations",
        "review_decisions",
        "release_readiness_verdicts",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION protect_review_immutable()
            """
        )

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
            evidence_one validation_evidence%ROWTYPE;
            evidence_two validation_evidence%ROWTYPE;
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
            SELECT * INTO evidence_one FROM validation_evidence
            WHERE id = (NEW.evidence_manifest #>> '{entries,0,evidence_id}')::uuid;
            SELECT * INTO evidence_two FROM validation_evidence
            WHERE id = (NEW.evidence_manifest #>> '{entries,1,evidence_id}')::uuid;

            IF suite_run.id IS NULL OR suite_result.id IS NULL
                OR workspace_row.id IS NULL OR checkpoint_row.id IS NULL
                OR handle_row.id IS NULL
                OR suite_run.state IS DISTINCT FROM 'succeeded'
                OR suite_result.verdict IS DISTINCT FROM 'succeeded'
                OR suite_result.suite_run_id IS DISTINCT FROM suite_run.id
                OR suite_result.aggregate_digest IS DISTINCT FROM NEW.suite_result_digest
                OR suite_run.run_id IS DISTINCT FROM NEW.run_id
                OR suite_run.plan_id IS DISTINCT FROM NEW.plan_id
                OR suite_run.workspace_id IS DISTINCT FROM NEW.workspace_id
                OR suite_run.checkpoint_id IS DISTINCT FROM NEW.checkpoint_id
                OR workspace_row.repository_handle_id
                    IS DISTINCT FROM NEW.repository_handle_id
                OR suite_run.source_revision IS DISTINCT FROM NEW.source_revision
                OR checkpoint_row.source_revision IS DISTINCT FROM NEW.source_revision
                OR workspace_row.source_revision IS DISTINCT FROM NEW.source_revision
                OR handle_row.current_revision IS DISTINCT FROM NEW.source_revision
                OR handle_row.status IS DISTINCT FROM 'available'
                OR checkpoint_row.tree_fingerprint
                    IS DISTINCT FROM NEW.checkpoint_fingerprint
                OR workspace_row.current_tree_hash
                    IS DISTINCT FROM NEW.checkpoint_fingerprint
                OR NEW.evidence_manifest ->> 'suite_run_id'
                    IS DISTINCT FROM NEW.suite_run_id::text
                OR NEW.evidence_manifest ->> 'suite_result_id'
                    IS DISTINCT FROM NEW.suite_result_id::text
                OR NEW.evidence_manifest ->> 'suite_result_digest'
                    IS DISTINCT FROM NEW.suite_result_digest
                OR NEW.evidence_manifest ->> 'checkpoint_id'
                    IS DISTINCT FROM NEW.checkpoint_id::text
                OR NEW.evidence_manifest ->> 'checkpoint_fingerprint'
                    IS DISTINCT FROM NEW.checkpoint_fingerprint
                OR NEW.evidence_manifest ->> 'source_revision'
                    IS DISTINCT FROM NEW.source_revision
                OR NEW.evidence_manifest ->> 'artifact_count' IS DISTINCT FROM '0'
                OR NEW.evidence_manifest ->> 'artifact_bytes' IS DISTINCT FROM '0'
                OR NEW.evidence_manifest ->> 'cleanup_succeeded'
                    IS DISTINCT FROM 'true'
                OR NEW.evidence_manifest ->> 'source_invariant'
                    IS DISTINCT FROM 'true'
                OR NEW.evidence_manifest ->> 'canonical_workspace_invariant'
                    IS DISTINCT FROM 'true'
                OR NEW.evidence_manifest #>> '{entries,0,sequence}' IS DISTINCT FROM '1'
                OR NEW.evidence_manifest #>> '{entries,1,sequence}' IS DISTINCT FROM '2'
                OR NEW.evidence_manifest #>> '{entries,0,evidence_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,evidence_id}'
                OR NEW.evidence_manifest #>> '{entries,1,evidence_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,evidence_id}'
                OR NEW.evidence_manifest #>> '{entries,0,evidence_digest}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,evidence_digest}'
                OR NEW.evidence_manifest #>> '{entries,1,evidence_digest}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,evidence_digest}'
                OR NEW.evidence_manifest #>> '{entries,0,step_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,step_id}'
                OR NEW.evidence_manifest #>> '{entries,1,step_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,step_id}'
                OR NEW.evidence_manifest #>> '{entries,0,profile}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,profile}'
                OR NEW.evidence_manifest #>> '{entries,1,profile}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,profile}'
                OR NEW.evidence_manifest #>> '{entries,0,validation_run_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,validation_run_id}'
                OR NEW.evidence_manifest #>> '{entries,1,validation_run_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,validation_run_id}'
                OR NEW.evidence_manifest #>> '{entries,0,runner_job_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,runner_job_id}'
                OR NEW.evidence_manifest #>> '{entries,1,runner_job_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,runner_job_id}'
                OR NEW.evidence_manifest #>> '{entries,0,runner_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,runner_id}'
                OR NEW.evidence_manifest #>> '{entries,1,runner_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,runner_id}'
                OR NEW.evidence_manifest #>> '{entries,0,attempt_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,attempt_id}'
                OR NEW.evidence_manifest #>> '{entries,1,attempt_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,attempt_id}'
                OR NEW.evidence_manifest #>> '{entries,0,lease_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,lease_id}'
                OR NEW.evidence_manifest #>> '{entries,1,lease_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,lease_id}'
                OR NEW.evidence_manifest #>> '{entries,0,grant_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{0,grant_id}'
                OR NEW.evidence_manifest #>> '{entries,1,grant_id}'
                    IS DISTINCT FROM suite_result.evidence_references #>> '{1,grant_id}'
                OR evidence_one.id IS NULL OR evidence_two.id IS NULL
                OR NEW.evidence_manifest #>> '{entries,0,side_effect_permit_id}'
                    IS DISTINCT FROM evidence_one.side_effect_permit_id::text
                OR NEW.evidence_manifest #>> '{entries,1,side_effect_permit_id}'
                    IS DISTINCT FROM evidence_two.side_effect_permit_id::text
                OR NEW.evidence_manifest #>> '{entries,0,side_effect_permit_sequence}'
                    IS DISTINCT FROM evidence_one.side_effect_permit_sequence::text
                OR NEW.evidence_manifest #>> '{entries,1,side_effect_permit_sequence}'
                    IS DISTINCT FROM evidence_two.side_effect_permit_sequence::text
                OR NEW.evidence_manifest #>> '{entries,0,side_effect_permit_digest}'
                    IS DISTINCT FROM evidence_one.side_effect_permit_digest
                OR NEW.evidence_manifest #>> '{entries,1,side_effect_permit_digest}'
                    IS DISTINCT FROM evidence_two.side_effect_permit_digest
                OR NEW.evidence_manifest #>> '{entries,0,fencing_token}'
                    IS DISTINCT FROM evidence_one.fencing_token
                OR NEW.evidence_manifest #>> '{entries,1,fencing_token}'
                    IS DISTINCT FROM evidence_two.fencing_token
                OR NEW.evidence_manifest #>> '{entries,0,execution_envelope_digest}'
                    IS DISTINCT FROM evidence_one.execution_envelope_digest
                OR NEW.evidence_manifest #>> '{entries,1,execution_envelope_digest}'
                    IS DISTINCT FROM evidence_two.execution_envelope_digest
            THEN
                RAISE EXCEPTION 'Review Package does not match trusted Suite Evidence'
                    USING ERRCODE = '55000';
            END IF;

            SELECT id INTO latest_checkpoint_id
            FROM workspace_checkpoints
            WHERE workspace_id = NEW.workspace_id
            ORDER BY sequence DESC, created_at DESC, id DESC
            LIMIT 1;
            SELECT result.id INTO latest_result_id
            FROM validation_suite_results AS result
            JOIN validation_suite_runs AS run ON run.id = result.suite_run_id
            WHERE run.plan_id = NEW.plan_id
                AND result.checkpoint_id = NEW.checkpoint_id
                AND result.verdict = 'succeeded'
            ORDER BY result.created_at DESC, result.id DESC
            LIMIT 1;
            IF latest_checkpoint_id IS DISTINCT FROM NEW.checkpoint_id
                OR latest_result_id IS DISTINCT FROM NEW.suite_result_id
            THEN
                RAISE EXCEPTION 'Review Package baseline is stale'
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
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_review_invalidation_insert()
        RETURNS trigger AS $$
        DECLARE package_row review_packages%ROWTYPE;
        BEGIN
            SELECT * INTO package_row FROM review_packages
            WHERE id = NEW.review_package_id FOR UPDATE;
            IF package_row.id IS NULL
                OR package_row.package_digest IS DISTINCT FROM NEW.package_digest
            THEN
                RAISE EXCEPTION 'Review invalidation package binding is invalid'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER review_invalidations_insert_guard
        BEFORE INSERT ON review_package_invalidations
        FOR EACH ROW EXECUTE FUNCTION guard_review_invalidation_insert();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_review_decision_insert()
        RETURNS trigger AS $$
        DECLARE
            package_row review_packages%ROWTYPE;
            workspace_row workspaces%ROWTYPE;
            checkpoint_row workspace_checkpoints%ROWTYPE;
            handle_row repository_handles%ROWTYPE;
            latest_checkpoint_id uuid;
            latest_result_id uuid;
        BEGIN
            SELECT * INTO package_row FROM review_packages
            WHERE id = NEW.review_package_id FOR UPDATE;
            SELECT * INTO workspace_row FROM workspaces
            WHERE id = package_row.workspace_id FOR UPDATE;
            SELECT * INTO checkpoint_row FROM workspace_checkpoints
            WHERE id = package_row.checkpoint_id;
            SELECT * INTO handle_row FROM repository_handles
            WHERE id = package_row.repository_handle_id FOR UPDATE;
            SELECT id INTO latest_checkpoint_id FROM workspace_checkpoints
            WHERE workspace_id = package_row.workspace_id
            ORDER BY sequence DESC, created_at DESC, id DESC LIMIT 1;
            SELECT result.id INTO latest_result_id
            FROM validation_suite_results AS result
            JOIN validation_suite_runs AS run ON run.id = result.suite_run_id
            WHERE run.plan_id = package_row.plan_id
                AND result.checkpoint_id = package_row.checkpoint_id
                AND result.verdict = 'succeeded'
            ORDER BY result.created_at DESC, result.id DESC LIMIT 1;

            IF package_row.id IS NULL
                OR NEW.package_digest IS DISTINCT FROM package_row.package_digest
                OR EXISTS (
                    SELECT 1 FROM review_package_invalidations
                    WHERE review_package_id = package_row.id
                )
                OR workspace_row.source_revision
                    IS DISTINCT FROM package_row.source_revision
                OR checkpoint_row.source_revision
                    IS DISTINCT FROM package_row.source_revision
                OR workspace_row.current_tree_hash
                    IS DISTINCT FROM package_row.checkpoint_fingerprint
                OR checkpoint_row.tree_fingerprint
                    IS DISTINCT FROM package_row.checkpoint_fingerprint
                OR handle_row.current_revision
                    IS DISTINCT FROM package_row.source_revision
                OR handle_row.status IS DISTINCT FROM 'available'
                OR latest_checkpoint_id IS DISTINCT FROM package_row.checkpoint_id
                OR latest_result_id IS DISTINCT FROM package_row.suite_result_id
            THEN
                RAISE EXCEPTION 'Stale Review Package cannot be decided'
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
            workspace_row workspaces%ROWTYPE;
            checkpoint_row workspace_checkpoints%ROWTYPE;
            handle_row repository_handles%ROWTYPE;
            latest_checkpoint_id uuid;
            latest_result_id uuid;
        BEGIN
            SELECT * INTO package_row FROM review_packages
            WHERE id = NEW.review_package_id FOR UPDATE;
            SELECT * INTO decision_row FROM review_decisions
            WHERE id = NEW.review_decision_id FOR UPDATE;
            SELECT * INTO workspace_row FROM workspaces
            WHERE id = package_row.workspace_id FOR UPDATE;
            SELECT * INTO checkpoint_row FROM workspace_checkpoints
            WHERE id = package_row.checkpoint_id;
            SELECT * INTO handle_row FROM repository_handles
            WHERE id = package_row.repository_handle_id FOR UPDATE;
            SELECT id INTO latest_checkpoint_id FROM workspace_checkpoints
            WHERE workspace_id = package_row.workspace_id
            ORDER BY sequence DESC, created_at DESC, id DESC LIMIT 1;
            SELECT result.id INTO latest_result_id
            FROM validation_suite_results AS result
            JOIN validation_suite_runs AS run ON run.id = result.suite_run_id
            WHERE run.plan_id = package_row.plan_id
                AND result.checkpoint_id = package_row.checkpoint_id
                AND result.verdict = 'succeeded'
            ORDER BY result.created_at DESC, result.id DESC LIMIT 1;

            IF package_row.id IS NULL OR decision_row.id IS NULL
                OR decision_row.review_package_id IS DISTINCT FROM package_row.id
                OR NEW.package_digest IS DISTINCT FROM package_row.package_digest
                OR NEW.package_digest IS DISTINCT FROM decision_row.package_digest
                OR NEW.evidence_manifest_digest
                    IS DISTINCT FROM package_row.evidence_manifest_digest
            THEN
                RAISE EXCEPTION 'Readiness proof binding is invalid'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.verdict = 'ready' AND (
                decision_row.decision IS DISTINCT FROM 'approve'
                OR EXISTS (
                    SELECT 1 FROM review_package_invalidations
                    WHERE review_package_id = package_row.id
                )
                OR workspace_row.source_revision
                    IS DISTINCT FROM package_row.source_revision
                OR checkpoint_row.source_revision
                    IS DISTINCT FROM package_row.source_revision
                OR workspace_row.current_tree_hash
                    IS DISTINCT FROM package_row.checkpoint_fingerprint
                OR checkpoint_row.tree_fingerprint
                    IS DISTINCT FROM package_row.checkpoint_fingerprint
                OR handle_row.current_revision
                    IS DISTINCT FROM package_row.source_revision
                OR handle_row.status IS DISTINCT FROM 'available'
                OR latest_checkpoint_id IS DISTINCT FROM package_row.checkpoint_id
                OR latest_result_id IS DISTINCT FROM package_row.suite_result_id
            ) THEN
                RAISE EXCEPTION 'Stale or rejected review cannot be ready'
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


def downgrade() -> None:
    op.drop_table("release_readiness_verdicts")
    op.drop_table("review_decisions")
    op.drop_table("review_package_invalidations")
    op.drop_index("ix_review_packages_workspace_created", table_name="review_packages")
    op.drop_index("ix_review_packages_run_created", table_name="review_packages")
    op.drop_table("review_packages")
    op.execute("DROP FUNCTION IF EXISTS guard_readiness_insert()")
    op.execute("DROP FUNCTION IF EXISTS guard_review_decision_insert()")
    op.execute("DROP FUNCTION IF EXISTS guard_review_invalidation_insert()")
    op.execute("DROP FUNCTION IF EXISTS guard_review_package_insert()")
    op.execute("DROP FUNCTION IF EXISTS protect_review_immutable()")
