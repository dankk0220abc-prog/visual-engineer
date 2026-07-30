"""Enforce Suite Grant lineage and trusted aggregate Evidence.

Revision ID: 20260730_0009
Revises: 20260730_0008
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_0009"
down_revision: str | None = "20260730_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SUITE_DEFINITION_DIGEST = "e786080f7dd179dd8d0416b2ec0232b46d7c70834d372ea6a2a2808606890350"


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS validation_suite_step_guard ON validation_suite_step_runs")
    op.execute("DROP TRIGGER IF EXISTS validation_suite_run_guard ON validation_suite_runs")
    op.execute(
        "DROP TRIGGER IF EXISTS validation_suite_result_immutable ON validation_suite_results"
    )
    op.execute("DROP TRIGGER IF EXISTS execution_grants_policy_immutable ON execution_grants")
    op.add_column(
        "validation_suite_runs",
        sa.Column("root_suite_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE validation_suite_runs
        SET root_suite_run_id = COALESCE(retry_of_suite_run_id, id)
        """
    )
    op.alter_column("validation_suite_runs", "root_suite_run_id", nullable=False)
    op.create_foreign_key(
        "fk_validation_suite_runs_root",
        "validation_suite_runs",
        "validation_suite_runs",
        ["root_suite_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "ck_validation_suite_retry_binding",
        "validation_suite_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_validation_suite_retry_binding",
        "validation_suite_runs",
        "(attempt_number = 1 AND retry_of_suite_run_id IS NULL "
        "AND root_suite_run_id = id) OR "
        "(attempt_number > 1 AND retry_of_suite_run_id IS NOT NULL "
        "AND root_suite_run_id <> id)",
    )
    op.create_unique_constraint(
        "uq_validation_suite_runs_execution_grant",
        "validation_suite_runs",
        ["execution_grant_id"],
    )
    op.create_unique_constraint(
        "uq_validation_suite_runs_root_attempt",
        "validation_suite_runs",
        ["root_suite_run_id", "attempt_number"],
    )
    op.create_check_constraint(
        "ck_validation_suite_trusted_definition",
        "validation_suite_runs",
        "suite_id = 'fixture-integrity-suite-v1' AND suite_version = 1 "
        "AND failure_policy = 'fail_fast' AND step_count = 2 "
        "AND total_timeout_seconds = 30 AND total_output_bytes = 10000 "
        "AND max_attempts = 2 AND attempt_number BETWEEN 1 AND 2",
    )

    op.add_column(
        "execution_grants",
        sa.Column("validation_suite_definition_digest", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "execution_grants",
        sa.Column("validation_suite_root_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "execution_grants",
        sa.Column(
            "validation_suite_retry_of_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "execution_grants",
        sa.Column(
            "validation_suite_attempt_number",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "execution_grants",
        sa.Column(
            "validation_suite_allowed_run_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE execution_grants
            SET validation_suite_definition_digest = :definition_digest,
                validation_suite_attempt_number = 1,
                validation_suite_allowed_run_count = 1,
                max_validation_runs = 2
            WHERE jsonb_array_length(allowed_validation_suites) = 1
            """
        ).bindparams(definition_digest=_SUITE_DEFINITION_DIGEST)
    )
    op.execute(
        """
        UPDATE execution_grants AS target_grant
        SET validation_suite_root_run_id = CASE
                WHEN suite_run.attempt_number > 1
                THEN suite_run.root_suite_run_id
                ELSE NULL
            END,
            validation_suite_retry_of_run_id = suite_run.retry_of_suite_run_id,
            validation_suite_attempt_number = suite_run.attempt_number
        FROM validation_suite_runs AS suite_run
        WHERE suite_run.execution_grant_id = target_grant.id
        """
    )
    op.create_foreign_key(
        "fk_grants_validation_suite_root_run",
        "execution_grants",
        "validation_suite_runs",
        ["validation_suite_root_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_grants_validation_suite_retry_of_run",
        "execution_grants",
        "validation_suite_runs",
        ["validation_suite_retry_of_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_grants_validation_suite_lineage",
        "execution_grants",
        "("
        "jsonb_array_length(allowed_validation_suites) = 0 "
        "AND validation_suite_definition_digest IS NULL "
        "AND validation_suite_root_run_id IS NULL "
        "AND validation_suite_retry_of_run_id IS NULL "
        "AND validation_suite_attempt_number = 0 "
        "AND validation_suite_allowed_run_count = 0"
        ") OR ("
        "jsonb_array_length(allowed_validation_suites) = 1 "
        "AND validation_suite_definition_digest ~ '^[0-9a-f]{64}$' "
        "AND validation_suite_attempt_number BETWEEN 1 AND 5 "
        "AND validation_suite_allowed_run_count = 1 "
        "AND max_validation_runs = 2 "
        "AND ("
        "(validation_suite_attempt_number = 1 "
        "AND validation_suite_root_run_id IS NULL "
        "AND validation_suite_retry_of_run_id IS NULL) OR "
        "(validation_suite_attempt_number > 1 "
        "AND validation_suite_root_run_id IS NOT NULL "
        "AND validation_suite_retry_of_run_id IS NOT NULL)"
        ")"
        ")",
    )
    op.create_index(
        "uq_active_root_suite_grant",
        "execution_grants",
        ["plan_id", "validation_checkpoint_id", "validation_suite_definition_digest"],
        unique=True,
        postgresql_where=sa.text(
            "validation_suite_attempt_number = 1 AND status IN ('pending', 'approved')"
        ),
    )
    op.create_index(
        "uq_active_retry_suite_grant",
        "execution_grants",
        ["validation_suite_retry_of_run_id"],
        unique=True,
        postgresql_where=sa.text(
            "validation_suite_attempt_number > 1 AND status IN ('pending', 'approved')"
        ),
    )
    op.execute(
        """
        CREATE TRIGGER execution_grants_policy_immutable
        BEFORE UPDATE OR DELETE ON execution_grants
        FOR EACH ROW EXECUTE FUNCTION protect_execution_grant_policy()
        """
    )

    result_columns = (
        sa.Column("root_suite_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("execution_grant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suite_id", sa.String(length=64), nullable=True),
        sa.Column("suite_version", sa.Integer(), nullable=True),
        sa.Column("source_revision", sa.String(length=64), nullable=True),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_digest", sa.String(length=64), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("total_timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("total_output_bytes", sa.Integer(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=True),
        sa.Column(
            "runner_references",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    for column in result_columns:
        op.add_column("validation_suite_results", column)
    op.execute(
        """
        UPDATE validation_suite_results AS result
        SET root_suite_run_id = suite_run.root_suite_run_id,
            run_id = suite_run.run_id,
            execution_grant_id = suite_run.execution_grant_id,
            suite_id = suite_run.suite_id,
            suite_version = suite_run.suite_version,
            source_revision = suite_run.source_revision,
            checkpoint_id = suite_run.checkpoint_id,
            policy_digest = suite_run.policy_digest,
            attempt_number = suite_run.attempt_number,
            total_timeout_seconds = suite_run.total_timeout_seconds,
            total_output_bytes = suite_run.total_output_bytes,
            max_attempts = suite_run.max_attempts,
            runner_references = COALESCE(
                (
                    SELECT jsonb_agg(reference ->> 'runner_id' ORDER BY ordinal)
                    FROM jsonb_array_elements(result.evidence_references)
                        WITH ORDINALITY AS evidence_items(reference, ordinal)
                ),
                '[]'::jsonb
            )
        FROM validation_suite_runs AS suite_run
        WHERE suite_run.id = result.suite_run_id
        """
    )
    for column_name in (
        "root_suite_run_id",
        "run_id",
        "execution_grant_id",
        "suite_id",
        "suite_version",
        "source_revision",
        "checkpoint_id",
        "policy_digest",
        "attempt_number",
        "total_timeout_seconds",
        "total_output_bytes",
        "max_attempts",
    ):
        op.alter_column("validation_suite_results", column_name, nullable=False)
    op.create_foreign_key(
        "fk_validation_suite_results_root",
        "validation_suite_results",
        "validation_suite_runs",
        ["root_suite_run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_validation_suite_results_run",
        "validation_suite_results",
        "runs",
        ["run_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_validation_suite_results_grant",
        "validation_suite_results",
        "execution_grants",
        ["execution_grant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_validation_suite_results_checkpoint",
        "validation_suite_results",
        "workspace_checkpoints",
        ["checkpoint_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_validation_suite_result_definition",
        "validation_suite_results",
        "suite_id = 'fixture-integrity-suite-v1' AND suite_version = 1",
    )
    op.create_check_constraint(
        "ck_validation_suite_result_policy_digest",
        "validation_suite_results",
        "policy_digest ~ '^[0-9a-f]{64}$'",
    )
    op.create_check_constraint(
        "ck_validation_suite_result_attempt",
        "validation_suite_results",
        "attempt_number BETWEEN 1 AND max_attempts AND max_attempts BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        "ck_validation_suite_result_budgets",
        "validation_suite_results",
        "total_timeout_seconds BETWEEN 1 AND 600 AND total_output_bytes BETWEEN 256 AND 262144",
    )

    _install_trusted_triggers()


def _install_trusted_triggers() -> None:
    op.execute("DROP TRIGGER IF EXISTS validation_suite_step_guard ON validation_suite_step_runs")
    op.execute("DROP TRIGGER IF EXISTS validation_suite_run_guard ON validation_suite_runs")
    op.execute(
        "DROP TRIGGER IF EXISTS validation_suite_result_immutable ON validation_suite_results"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_validation_suite_step()
        RETURNS trigger AS $$
        DECLARE
            parent_suite validation_suite_runs%ROWTYPE;
            proof_suite validation_suite_runs%ROWTYPE;
            source_step validation_suite_step_runs%ROWTYPE;
            child_run validation_runs%ROWTYPE;
            child_evidence validation_evidence%ROWTYPE;
            child_job runner_jobs%ROWTYPE;
            child_attempt runner_job_attempts%ROWTYPE;
            child_permit side_effect_permits%ROWTYPE;
            child_grant execution_grants%ROWTYPE;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'validation Suite steps cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;

            SELECT * INTO parent_suite
            FROM validation_suite_runs
            WHERE id = NEW.suite_run_id
            FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'validation Suite parent is unavailable'
                    USING ERRCODE = '55000';
            END IF;
            IF parent_suite.state IN (
                'succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required'
            ) THEN
                RAISE EXCEPTION 'terminal validation Suite cannot accept step mutation'
                    USING ERRCODE = '55000';
            END IF;

            IF NOT (
                (NEW.sequence = 1
                    AND NEW.step_id = 'fixture-contract'
                    AND NEW.profile_id = 'fixture-python-stdlib-v1'
                    AND NEW.timeout_seconds = 10
                    AND NEW.max_output_bytes = 8192)
                OR
                (NEW.sequence = 2
                    AND NEW.step_id = 'fixture-manifest'
                    AND NEW.profile_id = 'fixture-python-manifest-v1'
                    AND NEW.timeout_seconds = 10
                    AND NEW.max_output_bytes = 4096)
            ) OR NEW.profile_version <> 1 THEN
                RAISE EXCEPTION 'validation Suite step definition is not trusted'
                    USING ERRCODE = '55000';
            END IF;

            IF TG_OP = 'UPDATE' THEN
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
                IF OLD.state <> NEW.state AND NOT (
                    (OLD.state = 'pending' AND NEW.state IN (
                        'queued', 'cancelled', 'skipped', 'recovery_required'
                    )) OR
                    (OLD.state = 'queued' AND NEW.state IN (
                        'running', 'succeeded', 'failed', 'timed_out',
                        'cancelled', 'recovery_required'
                    )) OR
                    (OLD.state = 'running' AND NEW.state IN (
                        'succeeded', 'failed', 'timed_out',
                        'cancelled', 'recovery_required'
                    ))
                ) THEN
                    RAISE EXCEPTION 'illegal validation Suite step transition'
                        USING ERRCODE = '55000';
                END IF;
            END IF;

            IF NEW.state = 'succeeded' THEN
                IF NEW.validation_run_id IS NULL
                    OR NEW.runner_job_id IS NULL
                    OR NEW.runner_id IS NULL
                    OR NEW.attempt_id IS NULL
                    OR NEW.lease_id IS NULL
                    OR NEW.evidence_id IS NULL
                    OR NEW.exit_code <> 0
                    OR NEW.cleanup_succeeded IS DISTINCT FROM TRUE
                    OR NEW.output_bytes > NEW.max_output_bytes THEN
                    RAISE EXCEPTION 'successful validation Suite step lacks trusted bindings'
                        USING ERRCODE = '55000';
                END IF;

                proof_suite := parent_suite;
                IF NEW.reused_from_step_run_id IS NOT NULL THEN
                    SELECT * INTO source_step
                    FROM validation_suite_step_runs
                    WHERE id = NEW.reused_from_step_run_id;
                    IF NOT FOUND
                        OR source_step.suite_run_id = NEW.suite_run_id
                        OR source_step.sequence IS DISTINCT FROM NEW.sequence
                        OR source_step.step_id IS DISTINCT FROM NEW.step_id
                        OR source_step.profile_id IS DISTINCT FROM NEW.profile_id
                        OR source_step.profile_version
                            IS DISTINCT FROM NEW.profile_version
                        OR source_step.state IS DISTINCT FROM 'succeeded'
                        OR source_step.validation_run_id
                            IS DISTINCT FROM NEW.validation_run_id
                        OR source_step.runner_job_id
                            IS DISTINCT FROM NEW.runner_job_id
                        OR source_step.runner_id IS DISTINCT FROM NEW.runner_id
                        OR source_step.attempt_id IS DISTINCT FROM NEW.attempt_id
                        OR source_step.lease_id IS DISTINCT FROM NEW.lease_id
                        OR source_step.evidence_id IS DISTINCT FROM NEW.evidence_id
                        OR NEW.output_bytes IS DISTINCT FROM 0
                        OR NEW.redaction_count IS DISTINCT FROM 0 THEN
                        RAISE EXCEPTION 'reused validation Suite Evidence is untrusted'
                            USING ERRCODE = '55000';
                    END IF;
                    SELECT * INTO proof_suite
                    FROM validation_suite_runs
                    WHERE id = source_step.suite_run_id;
                    IF NOT FOUND
                        OR proof_suite.root_suite_run_id
                            IS DISTINCT FROM parent_suite.root_suite_run_id
                        OR proof_suite.attempt_number >= parent_suite.attempt_number THEN
                        RAISE EXCEPTION 'reused validation Suite lineage is invalid'
                            USING ERRCODE = '55000';
                    END IF;
                END IF;

                SELECT * INTO child_run
                FROM validation_runs WHERE id = NEW.validation_run_id;
                SELECT * INTO child_evidence
                FROM validation_evidence WHERE id = NEW.evidence_id;
                SELECT * INTO child_job
                FROM runner_jobs WHERE id = NEW.runner_job_id;
                SELECT * INTO child_attempt
                FROM runner_job_attempts WHERE id = NEW.attempt_id;
                IF child_evidence.side_effect_permit_id IS NOT NULL THEN
                    SELECT * INTO child_permit
                    FROM side_effect_permits
                    WHERE id = child_evidence.side_effect_permit_id;
                END IF;
                SELECT * INTO child_grant
                FROM execution_grants WHERE id = child_run.execution_grant_id;

                IF child_run.id IS NULL
                    OR child_evidence.id IS NULL
                    OR child_job.id IS NULL
                    OR child_attempt.id IS NULL
                    OR child_permit.id IS NULL
                    OR child_grant.id IS NULL
                    OR child_run.state IS DISTINCT FROM 'succeeded'
                    OR child_run.completed_at IS NULL
                    OR child_run.run_id IS DISTINCT FROM proof_suite.run_id
                    OR child_run.plan_id IS DISTINCT FROM proof_suite.plan_id
                    OR child_run.source_revision
                        IS DISTINCT FROM proof_suite.source_revision
                    OR child_run.workspace_id IS DISTINCT FROM proof_suite.workspace_id
                    OR child_run.checkpoint_id
                        IS DISTINCT FROM proof_suite.checkpoint_id
                    OR child_run.checkpoint_fingerprint
                        IS DISTINCT FROM proof_suite.checkpoint_fingerprint
                    OR child_run.execution_grant_id
                        IS DISTINCT FROM proof_suite.execution_grant_id
                    OR child_run.runner_job_id IS DISTINCT FROM NEW.runner_job_id
                    OR child_run.runner_id IS DISTINCT FROM NEW.runner_id
                    OR child_run.attempt_id IS DISTINCT FROM NEW.attempt_id
                    OR child_run.lease_id IS DISTINCT FROM NEW.lease_id
                    OR child_run.profile_id IS DISTINCT FROM NEW.profile_id
                    OR child_run.profile_version IS DISTINCT FROM NEW.profile_version
                    OR child_job.state IS DISTINCT FROM 'succeeded'
                    OR child_job.kind IS DISTINCT FROM 'validation_execute_v1'
                    OR child_job.execution_grant_id IS DISTINCT FROM child_grant.id
                    OR child_job.workspace_id IS DISTINCT FROM child_run.workspace_id
                    OR child_job.source_revision IS DISTINCT FROM child_run.source_revision
                    OR child_job.execution_policy_hash
                        IS DISTINCT FROM child_grant.policy_hash
                    OR child_attempt.job_id IS DISTINCT FROM child_job.id
                    OR child_attempt.runner_id IS DISTINCT FROM NEW.runner_id
                    OR child_attempt.lease_id IS DISTINCT FROM NEW.lease_id
                    OR child_attempt.state IS DISTINCT FROM 'succeeded'
                    OR child_evidence.validation_run_id IS DISTINCT FROM child_run.id
                    OR child_evidence.runner_id IS DISTINCT FROM NEW.runner_id
                    OR child_evidence.attempt_id IS DISTINCT FROM NEW.attempt_id
                    OR child_evidence.lease_id IS DISTINCT FROM NEW.lease_id
                    OR child_evidence.result_schema_version IS DISTINCT FROM 1
                    OR child_evidence.validation_step_id IS DISTINCT FROM NEW.step_id
                    OR child_evidence.source_revision
                        IS DISTINCT FROM child_run.source_revision
                    OR child_evidence.policy_digest
                        IS DISTINCT FROM child_run.policy_digest
                    OR child_evidence.exit_code IS DISTINCT FROM 0
                    OR child_evidence.timed_out
                    OR child_evidence.cancelled
                    OR NOT child_evidence.network_isolated
                    OR NOT child_evidence.filesystem_isolated
                    OR NOT child_evidence.sandbox_cleaned
                    OR child_evidence.artifact_count IS DISTINCT FROM 0
                    OR child_evidence.artifact_bytes IS DISTINCT FROM 0
                    OR child_evidence.evidence_digest IS NULL
                    OR child_job.result ->> 'evidence_digest'
                        IS DISTINCT FROM child_evidence.evidence_digest
                    OR child_permit.state IS DISTINCT FROM 'completed'
                    OR child_permit.terminal_at IS NULL
                    OR child_permit.operation IS DISTINCT FROM 'validate'
                    OR child_permit.runner_id IS DISTINCT FROM NEW.runner_id
                    OR child_permit.job_id IS DISTINCT FROM child_job.id
                    OR child_permit.attempt_id IS DISTINCT FROM child_attempt.id
                    OR child_permit.lease_id IS DISTINCT FROM child_attempt.lease_id
                    OR child_permit.grant_id IS DISTINCT FROM child_grant.id
                    OR child_permit.workspace_id IS DISTINCT FROM child_run.workspace_id
                    OR child_permit.policy_hash IS DISTINCT FROM child_grant.policy_hash
                    OR child_permit.source_revision
                        IS DISTINCT FROM child_run.source_revision
                    OR child_permit.sequence
                        IS DISTINCT FROM child_evidence.side_effect_permit_sequence
                    OR child_permit.operation_digest
                        IS DISTINCT FROM child_evidence.side_effect_permit_digest
                    OR child_grant.allowed_validation_suites
                        IS DISTINCT FROM '["fixture-integrity-suite-v1:v1"]'::jsonb
                    OR child_grant.validation_suite_definition_digest
                        IS DISTINCT FROM
                            'e786080f7dd179dd8d0416b2ec0232b46d7c70834d372ea6a2a2808606890350'
                    OR child_grant.validation_suite_attempt_number
                        IS DISTINCT FROM proof_suite.attempt_number
                    OR child_grant.validation_suite_allowed_run_count
                        IS DISTINCT FROM 1 THEN
                    RAISE EXCEPTION 'successful validation Suite step is not trusted'
                        USING ERRCODE = '55000';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER validation_suite_step_guard
        BEFORE INSERT OR UPDATE OR DELETE ON validation_suite_step_runs
        FOR EACH ROW EXECUTE FUNCTION protect_validation_suite_step()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_validation_suite_run()
        RETURNS trigger AS $$
        DECLARE
            trusted_step_count integer;
            bound_grant execution_grants%ROWTYPE;
            root_suite validation_suite_runs%ROWTYPE;
            source_suite validation_suite_runs%ROWTYPE;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'validation Suite runs cannot be deleted'
                    USING ERRCODE = '55000';
            END IF;
            IF TG_OP = 'INSERT' THEN
                SELECT * INTO bound_grant
                FROM execution_grants
                WHERE id = NEW.execution_grant_id
                FOR UPDATE;
                IF NOT FOUND
                    OR NEW.suite_id IS DISTINCT FROM 'fixture-integrity-suite-v1'
                    OR NEW.suite_version IS DISTINCT FROM 1
                    OR NEW.failure_policy IS DISTINCT FROM 'fail_fast'
                    OR NEW.step_count IS DISTINCT FROM 2
                    OR NEW.total_timeout_seconds IS DISTINCT FROM 30
                    OR NEW.total_output_bytes IS DISTINCT FROM 10000
                    OR NEW.max_attempts IS DISTINCT FROM 2
                    OR bound_grant.status IS DISTINCT FROM 'approved'
                    OR bound_grant.allowed_validation_suites IS DISTINCT FROM
                        '["fixture-integrity-suite-v1:v1"]'::jsonb
                    OR bound_grant.validation_suite_definition_digest IS DISTINCT FROM
                        'e786080f7dd179dd8d0416b2ec0232b46d7c70834d372ea6a2a2808606890350'
                    OR bound_grant.validation_suite_attempt_number
                        IS DISTINCT FROM NEW.attempt_number
                    OR bound_grant.validation_suite_allowed_run_count IS DISTINCT FROM 1
                    OR bound_grant.max_validation_runs IS DISTINCT FROM 2 THEN
                    RAISE EXCEPTION 'validation Suite Grant lineage is invalid'
                        USING ERRCODE = '55000';
                END IF;
                IF NEW.attempt_number = 1 THEN
                    IF NEW.root_suite_run_id IS DISTINCT FROM NEW.id
                        OR NEW.retry_of_suite_run_id IS NOT NULL
                        OR bound_grant.validation_suite_root_run_id IS NOT NULL
                        OR bound_grant.validation_suite_retry_of_run_id IS NOT NULL THEN
                        RAISE EXCEPTION 'validation Suite root lineage is invalid'
                            USING ERRCODE = '55000';
                    END IF;
                ELSE
                    SELECT * INTO root_suite
                    FROM validation_suite_runs
                    WHERE id = NEW.root_suite_run_id
                    FOR UPDATE;
                    SELECT * INTO source_suite
                    FROM validation_suite_runs
                    WHERE id = NEW.retry_of_suite_run_id
                    FOR UPDATE;
                    IF root_suite.id IS NULL
                        OR source_suite.id IS NULL
                        OR root_suite.id IS DISTINCT FROM root_suite.root_suite_run_id
                        OR source_suite.root_suite_run_id
                            IS DISTINCT FROM root_suite.id
                        OR source_suite.attempt_number + 1
                            IS DISTINCT FROM NEW.attempt_number
                        OR source_suite.state NOT IN (
                            'failed', 'timed_out', 'cancelled', 'recovery_required'
                        )
                        OR bound_grant.validation_suite_root_run_id
                            IS DISTINCT FROM root_suite.id
                        OR bound_grant.validation_suite_retry_of_run_id
                            IS DISTINCT FROM source_suite.id THEN
                        RAISE EXCEPTION 'validation Suite retry lineage is invalid'
                            USING ERRCODE = '55000';
                    END IF;
                END IF;
                RETURN NEW;
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
            IF OLD.state IS DISTINCT FROM NEW.state AND NOT (
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
            IF NEW.state IS NOT DISTINCT FROM 'succeeded' THEN
                SELECT count(*) INTO trusted_step_count
                FROM validation_suite_step_runs AS step
                JOIN validation_evidence AS evidence ON evidence.id = step.evidence_id
                JOIN validation_runs AS child_run
                    ON child_run.id = step.validation_run_id
                JOIN runner_jobs AS job ON job.id = step.runner_job_id
                JOIN runner_job_attempts AS attempt ON attempt.id = step.attempt_id
                JOIN side_effect_permits AS permit
                    ON permit.id = evidence.side_effect_permit_id
                WHERE step.suite_run_id = NEW.id
                    AND step.state = 'succeeded'
                    AND step.cleanup_succeeded
                    AND step.exit_code = 0
                    AND evidence.validation_run_id = child_run.id
                    AND evidence.runner_id = step.runner_id
                    AND evidence.attempt_id = attempt.id
                    AND evidence.lease_id = step.lease_id
                    AND evidence.evidence_digest IS NOT NULL
                    AND child_run.state = 'succeeded'
                    AND job.state = 'succeeded'
                    AND attempt.state = 'succeeded'
                    AND permit.state = 'completed'
                    AND permit.terminal_at IS NOT NULL;
                IF trusted_step_count <> NEW.step_count
                    OR NEW.completed_step_count <> NEW.step_count
                    OR NEW.combined_output_bytes > NEW.total_output_bytes THEN
                    RAISE EXCEPTION 'successful validation Suite lacks complete Evidence'
                        USING ERRCODE = '55000';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER validation_suite_run_guard
        BEFORE INSERT OR UPDATE OR DELETE ON validation_suite_runs
        FOR EACH ROW EXECUTE FUNCTION protect_validation_suite_run()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_validation_suite_result()
        RETURNS trigger AS $$
        DECLARE
            parent_suite validation_suite_runs%ROWTYPE;
            invalid_reference_count integer;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'validation Suite results are immutable'
                    USING ERRCODE = '55000';
            END IF;
            SELECT * INTO parent_suite
            FROM validation_suite_runs
            WHERE id = NEW.suite_run_id
            FOR UPDATE;
            IF NOT FOUND
                OR NEW.root_suite_run_id
                    IS DISTINCT FROM parent_suite.root_suite_run_id
                OR NEW.run_id IS DISTINCT FROM parent_suite.run_id
                OR NEW.execution_grant_id
                    IS DISTINCT FROM parent_suite.execution_grant_id
                OR NEW.suite_id IS DISTINCT FROM parent_suite.suite_id
                OR NEW.suite_version IS DISTINCT FROM parent_suite.suite_version
                OR NEW.source_revision IS DISTINCT FROM parent_suite.source_revision
                OR NEW.checkpoint_id IS DISTINCT FROM parent_suite.checkpoint_id
                OR NEW.policy_digest IS DISTINCT FROM parent_suite.policy_digest
                OR NEW.attempt_number IS DISTINCT FROM parent_suite.attempt_number
                OR NEW.total_timeout_seconds
                    IS DISTINCT FROM parent_suite.total_timeout_seconds
                OR NEW.total_output_bytes
                    IS DISTINCT FROM parent_suite.total_output_bytes
                OR NEW.max_attempts IS DISTINCT FROM parent_suite.max_attempts
                OR NEW.verdict IS DISTINCT FROM parent_suite.state
                OR NEW.combined_output_bytes
                    IS DISTINCT FROM parent_suite.combined_output_bytes
                OR jsonb_typeof(NEW.profile_references) IS DISTINCT FROM 'array'
                OR jsonb_typeof(NEW.evidence_references) IS DISTINCT FROM 'array'
                OR jsonb_typeof(NEW.runner_references) IS DISTINCT FROM 'array' THEN
                RAISE EXCEPTION 'validation Suite result binding is invalid'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.verdict = 'succeeded' THEN
                IF jsonb_array_length(NEW.evidence_references)
                        <> parent_suite.step_count
                    OR jsonb_array_length(NEW.runner_references)
                        <> parent_suite.step_count
                    OR jsonb_array_length(NEW.profile_references)
                        <> parent_suite.step_count THEN
                    RAISE EXCEPTION 'successful validation Suite result lacks Evidence'
                        USING ERRCODE = '55000';
                END IF;
                SELECT count(*) INTO invalid_reference_count
                FROM validation_suite_step_runs AS step
                LEFT JOIN LATERAL (
                    SELECT reference, ordinal
                    FROM jsonb_array_elements(NEW.evidence_references)
                        WITH ORDINALITY AS evidence_items(reference, ordinal)
                    WHERE ordinal = step.sequence
                ) AS evidence_reference ON TRUE
                LEFT JOIN LATERAL (
                    SELECT reference, ordinal
                    FROM jsonb_array_elements(NEW.runner_references)
                        WITH ORDINALITY AS runner_items(reference, ordinal)
                    WHERE ordinal = step.sequence
                ) AS runner_reference ON TRUE
                LEFT JOIN LATERAL (
                    SELECT reference, ordinal
                    FROM jsonb_array_elements(NEW.profile_references)
                        WITH ORDINALITY AS profile_items(reference, ordinal)
                    WHERE ordinal = step.sequence
                ) AS profile_reference ON TRUE
                WHERE step.suite_run_id = NEW.suite_run_id
                    AND (
                        step.state IS DISTINCT FROM 'succeeded'
                        OR step.evidence_id IS NULL
                        OR evidence_reference.reference ->> 'sequence'
                            IS DISTINCT FROM step.sequence::text
                        OR evidence_reference.reference ->> 'step_id'
                            IS DISTINCT FROM step.step_id
                        OR evidence_reference.reference ->> 'profile'
                            IS DISTINCT FROM
                                step.profile_id || ':' || 'v' || step.profile_version::text
                        OR evidence_reference.reference ->> 'validation_run_id'
                            IS DISTINCT FROM step.validation_run_id::text
                        OR evidence_reference.reference ->> 'runner_job_id'
                            IS DISTINCT FROM step.runner_job_id::text
                        OR evidence_reference.reference ->> 'runner_id'
                            IS DISTINCT FROM step.runner_id::text
                        OR evidence_reference.reference ->> 'attempt_id'
                            IS DISTINCT FROM step.attempt_id::text
                        OR evidence_reference.reference ->> 'lease_id'
                            IS DISTINCT FROM step.lease_id::text
                        OR evidence_reference.reference ->> 'grant_id'
                            IS DISTINCT FROM (
                                SELECT execution_grant_id::text
                                FROM validation_runs
                                WHERE id = step.validation_run_id
                            )
                        OR evidence_reference.reference ->> 'evidence_id'
                            IS DISTINCT FROM step.evidence_id::text
                        OR evidence_reference.reference ->> 'evidence_digest'
                            IS DISTINCT FROM (
                                SELECT evidence_digest
                                FROM validation_evidence
                                WHERE id = step.evidence_id
                            )
                        OR (evidence_reference.reference ->> 'reused')::boolean
                            IS DISTINCT FROM
                                (step.reused_from_step_run_id IS NOT NULL)
                        OR runner_reference.reference #>> '{}'
                            IS DISTINCT FROM step.runner_id::text
                        OR profile_reference.reference #>> '{}'
                            IS DISTINCT FROM
                                step.profile_id || ':' || 'v' || step.profile_version::text
                    );
                IF invalid_reference_count <> 0 THEN
                    RAISE EXCEPTION 'validation Suite result Evidence order is invalid'
                        USING ERRCODE = '55000';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER validation_suite_result_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON validation_suite_results
        FOR EACH ROW EXECUTE FUNCTION protect_validation_suite_result()
        """
    )


def downgrade() -> None:
    _restore_original_triggers()

    for constraint in (
        "ck_validation_suite_result_budgets",
        "ck_validation_suite_result_attempt",
        "ck_validation_suite_result_policy_digest",
        "ck_validation_suite_result_definition",
        "fk_validation_suite_results_checkpoint",
        "fk_validation_suite_results_grant",
        "fk_validation_suite_results_run",
        "fk_validation_suite_results_root",
    ):
        op.drop_constraint(constraint, "validation_suite_results")
    for column_name in (
        "runner_references",
        "max_attempts",
        "total_output_bytes",
        "total_timeout_seconds",
        "attempt_number",
        "policy_digest",
        "checkpoint_id",
        "source_revision",
        "suite_version",
        "suite_id",
        "execution_grant_id",
        "run_id",
        "root_suite_run_id",
    ):
        op.drop_column("validation_suite_results", column_name)

    op.execute("DROP INDEX IF EXISTS uq_active_retry_suite_grant")
    op.drop_index("uq_active_root_suite_grant", table_name="execution_grants")
    op.drop_constraint(
        "ck_grants_validation_suite_lineage",
        "execution_grants",
        type_="check",
    )
    op.drop_constraint(
        "fk_grants_validation_suite_retry_of_run",
        "execution_grants",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_grants_validation_suite_root_run",
        "execution_grants",
        type_="foreignkey",
    )
    for column_name in (
        "validation_suite_allowed_run_count",
        "validation_suite_attempt_number",
        "validation_suite_retry_of_run_id",
        "validation_suite_root_run_id",
        "validation_suite_definition_digest",
    ):
        op.drop_column("execution_grants", column_name)

    op.execute(
        "ALTER TABLE validation_suite_runs "
        "DROP CONSTRAINT IF EXISTS ck_validation_suite_trusted_definition"
    )
    op.execute(
        "ALTER TABLE validation_suite_runs "
        "DROP CONSTRAINT IF EXISTS uq_validation_suite_runs_root_attempt"
    )
    op.drop_constraint(
        "uq_validation_suite_runs_execution_grant",
        "validation_suite_runs",
        type_="unique",
    )
    op.drop_constraint(
        "ck_validation_suite_retry_binding",
        "validation_suite_runs",
        type_="check",
    )
    op.create_check_constraint(
        "ck_validation_suite_retry_binding",
        "validation_suite_runs",
        "(attempt_number = 1 AND retry_of_suite_run_id IS NULL) OR "
        "(attempt_number > 1 AND retry_of_suite_run_id IS NOT NULL)",
    )
    op.drop_constraint(
        "fk_validation_suite_runs_root",
        "validation_suite_runs",
        type_="foreignkey",
    )
    op.drop_column("validation_suite_runs", "root_suite_run_id")


def _restore_original_triggers() -> None:
    op.execute("DROP TRIGGER validation_suite_step_guard ON validation_suite_step_runs")
    op.execute("DROP TRIGGER validation_suite_run_guard ON validation_suite_runs")
    op.execute("DROP TRIGGER validation_suite_result_immutable ON validation_suite_results")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION protect_validation_suite_run()
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
        CREATE OR REPLACE FUNCTION protect_validation_suite_step()
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
        CREATE OR REPLACE FUNCTION protect_validation_suite_result()
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
