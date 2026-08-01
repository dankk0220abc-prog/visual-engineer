"""Add governed local delivery lifecycle attempts.

Revision ID: 20260801_0014
Revises: 20260731_0013
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260801_0014"
down_revision: str | None = "20260731_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE delivery_dispatches (
            id uuid PRIMARY KEY,
            delivery_authorization_id uuid NOT NULL
                REFERENCES delivery_authorizations(id) ON DELETE RESTRICT,
            attempt_number integer NOT NULL,
            retry_of_dispatch_id uuid
                REFERENCES delivery_dispatches(id) ON DELETE RESTRICT,
            runner_job_id uuid NOT NULL
                REFERENCES runner_jobs(id) ON DELETE RESTRICT,
            manifest jsonb NOT NULL,
            manifest_digest varchar(64) NOT NULL,
            confirmation_digest varchar(64) NOT NULL,
            status varchar(16) NOT NULL DEFAULT 'dispatched',
            request_id varchar(128) NOT NULL,
            idempotency_key varchar(255) NOT NULL,
            idempotency_request_hash varchar(64) NOT NULL,
            error_code varchar(64),
            created_at timestamptz NOT NULL DEFAULT now(),
            terminal_at timestamptz,
            CONSTRAINT uq_delivery_dispatches_authorization_attempt
                UNIQUE (delivery_authorization_id, attempt_number),
            CONSTRAINT uq_delivery_dispatches_job UNIQUE (runner_job_id),
            CONSTRAINT uq_delivery_dispatches_idempotency UNIQUE (idempotency_key),
            CONSTRAINT ck_delivery_dispatches_attempt
                CHECK (attempt_number BETWEEN 1 AND 3),
            CONSTRAINT ck_delivery_dispatches_retry_shape CHECK (
                (attempt_number = 1 AND retry_of_dispatch_id IS NULL)
                OR (attempt_number > 1 AND retry_of_dispatch_id IS NOT NULL)
            ),
            CONSTRAINT ck_delivery_dispatches_status CHECK (
                status IN ('dispatched', 'succeeded', 'failed', 'cancelled')
            ),
            CONSTRAINT ck_delivery_dispatches_digests CHECK (
                manifest_digest ~ '^[0-9a-f]{64}$'
                AND confirmation_digest = manifest_digest
                AND idempotency_request_hash ~ '^[0-9a-f]{64}$'
            ),
            CONSTRAINT ck_delivery_dispatches_manifest_local_only CHECK (
                manifest ->> 'manifest_version' = '1'
                AND manifest ->> 'manifest_digest' = manifest_digest
                AND manifest ->> 'local_git_commit_access' = 'true'
                AND manifest ->> 'remote_access' = 'false'
                AND manifest ->> 'push_access' = 'false'
                AND manifest ->> 'pull_request_access' = 'false'
                AND manifest ->> 'tag_access' = 'false'
                AND manifest ->> 'deployment_access' = 'false'
                AND manifest ->> 'source_repository_write_access' = 'false'
            ),
            CONSTRAINT ck_delivery_dispatches_terminal_time CHECK (
                (status = 'dispatched' AND terminal_at IS NULL)
                OR (
                    status IN ('succeeded', 'failed', 'cancelled')
                    AND terminal_at IS NOT NULL
                )
            )
        );
        CREATE UNIQUE INDEX uq_delivery_dispatches_active_authorization
            ON delivery_dispatches(delivery_authorization_id)
            WHERE status = 'dispatched';
        CREATE INDEX ix_delivery_dispatches_authorization_created
            ON delivery_dispatches(delivery_authorization_id, created_at);
        """
    )
    _replace_authorization_guard(allow_retry=True)
    _install_dispatch_guards()
    _replace_review_audit_guard(include_lifecycle=True)


def _replace_authorization_guard(*, allow_retry: bool) -> None:
    retry_transition = (
        """
                    OR (
                        OLD.status IN ('failed', 'cancelled')
                        AND NEW.status = 'stale'
                    )
                    OR (
                        OLD.status IN ('failed', 'cancelled')
                        AND NEW.status = 'dispatched'
                        AND NEW.dispatched_at > OLD.dispatched_at
                        AND NEW.terminal_at IS NULL
                        AND NEW.error_code IS NULL
                    )
    """
        if allow_retry
        else ""
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION guard_delivery_authorization_update()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
                OR NEW.authorization_version IS DISTINCT FROM OLD.authorization_version
                OR NEW.review_package_id IS DISTINCT FROM OLD.review_package_id
                OR NEW.review_decision_id IS DISTINCT FROM OLD.review_decision_id
                OR NEW.readiness_verdict_id IS DISTINCT FROM OLD.readiness_verdict_id
                OR NEW.freshness_generation IS DISTINCT FROM OLD.freshness_generation
                OR NEW.package_digest IS DISTINCT FROM OLD.package_digest
                OR NEW.decision_digest IS DISTINCT FROM OLD.decision_digest
                OR NEW.readiness_digest IS DISTINCT FROM OLD.readiness_digest
                OR NEW.execution_grant_id IS DISTINCT FROM OLD.execution_grant_id
                OR NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
                OR NEW.checkpoint_id IS DISTINCT FROM OLD.checkpoint_id
                OR NEW.checkpoint_fingerprint IS DISTINCT FROM OLD.checkpoint_fingerprint
                OR NEW.checkpoint_diff_hash IS DISTINCT FROM OLD.checkpoint_diff_hash
                OR NEW.repository_handle_id IS DISTINCT FROM OLD.repository_handle_id
                OR NEW.source_revision IS DISTINCT FROM OLD.source_revision
                OR NEW.branch_ref IS DISTINCT FROM OLD.branch_ref
                OR NEW.commit_message IS DISTINCT FROM OLD.commit_message
                OR NEW.local_git_commit_access
                    IS DISTINCT FROM OLD.local_git_commit_access
                OR NEW.remote_access IS DISTINCT FROM OLD.remote_access
                OR NEW.push_access IS DISTINCT FROM OLD.push_access
                OR NEW.pull_request_access IS DISTINCT FROM OLD.pull_request_access
                OR NEW.tag_access IS DISTINCT FROM OLD.tag_access
                OR NEW.deployment_access IS DISTINCT FROM OLD.deployment_access
                OR NEW.source_repository_write_access
                    IS DISTINCT FROM OLD.source_repository_write_access
                OR NEW.policy_hash IS DISTINCT FROM OLD.policy_hash
                OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
                OR NEW.idempotency_request_hash
                    IS DISTINCT FROM OLD.idempotency_request_hash
                OR NEW.created_at IS DISTINCT FROM OLD.created_at
                OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
                OR NOT (
                    (OLD.status = 'pending' AND NEW.status IN ('approved', 'rejected', 'stale'))
                    OR (OLD.status = 'approved' AND NEW.status IN ('dispatched', 'stale'))
                    OR (
                        OLD.status = 'dispatched'
                        AND NEW.status IN ('succeeded', 'failed', 'cancelled', 'stale')
                    )
                    {retry_transition}
                )
            THEN
                RAISE EXCEPTION 'Delivery Authorization mutation is forbidden'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def _install_dispatch_guards() -> None:
    op.execute(
        """
        CREATE FUNCTION guard_delivery_dispatch_insert()
        RETURNS trigger AS $$
        DECLARE authorization_row delivery_authorizations%ROWTYPE;
        DECLARE job_row runner_jobs%ROWTYPE;
        DECLARE prior_row delivery_dispatches%ROWTYPE;
        BEGIN
            SELECT * INTO authorization_row FROM delivery_authorizations
                WHERE id = NEW.delivery_authorization_id FOR UPDATE;
            SELECT * INTO job_row FROM runner_jobs
                WHERE id = NEW.runner_job_id FOR UPDATE;
            SELECT * INTO prior_row FROM delivery_dispatches
                WHERE delivery_authorization_id = NEW.delivery_authorization_id
                ORDER BY attempt_number DESC LIMIT 1 FOR UPDATE;

            IF authorization_row.id IS NULL
                OR job_row.id IS NULL
                OR authorization_row.status IS DISTINCT FROM 'dispatched'
                OR job_row.kind IS DISTINCT FROM 'workspace_git_commit_v1'
                OR job_row.delivery_authorization_id
                    IS DISTINCT FROM authorization_row.id
                OR job_row.parameters ->> 'delivery_dispatch_id'
                    IS DISTINCT FROM NEW.id::text
                OR (job_row.parameters ->> 'delivery_attempt_number')::integer
                    IS DISTINCT FROM NEW.attempt_number
                OR job_row.parameters -> 'delivery_manifest'
                    IS DISTINCT FROM NEW.manifest
                OR NEW.manifest ->> 'delivery_authorization_id'
                    IS DISTINCT FROM NEW.delivery_authorization_id::text
                OR NEW.manifest ->> 'workspace_id'
                    IS DISTINCT FROM authorization_row.workspace_id::text
                OR NEW.manifest ->> 'checkpoint_id'
                    IS DISTINCT FROM authorization_row.checkpoint_id::text
                OR NEW.manifest ->> 'checkpoint_fingerprint'
                    IS DISTINCT FROM authorization_row.checkpoint_fingerprint
                OR NEW.manifest ->> 'checkpoint_diff_hash'
                    IS DISTINCT FROM authorization_row.checkpoint_diff_hash
                OR NEW.manifest ->> 'source_revision'
                    IS DISTINCT FROM authorization_row.source_revision
                OR NEW.manifest ->> 'branch_ref'
                    IS DISTINCT FROM authorization_row.branch_ref
                OR NEW.manifest ->> 'commit_message'
                    IS DISTINCT FROM authorization_row.commit_message
                OR (
                    NEW.attempt_number = 1
                    AND prior_row.id IS NOT NULL
                )
                OR (
                    NEW.attempt_number > 1
                    AND (
                        prior_row.id IS NULL
                        OR NEW.attempt_number IS DISTINCT FROM prior_row.attempt_number + 1
                        OR NEW.retry_of_dispatch_id IS DISTINCT FROM prior_row.id
                        OR prior_row.status NOT IN ('failed', 'cancelled')
                    )
                )
            THEN
                RAISE EXCEPTION 'Delivery Dispatch binding is invalid'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER delivery_dispatches_00_insert_guard
        BEFORE INSERT ON delivery_dispatches
        FOR EACH ROW EXECUTE FUNCTION guard_delivery_dispatch_insert();

        CREATE FUNCTION guard_delivery_dispatch_update()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
                OR NEW.delivery_authorization_id
                    IS DISTINCT FROM OLD.delivery_authorization_id
                OR NEW.attempt_number IS DISTINCT FROM OLD.attempt_number
                OR NEW.retry_of_dispatch_id IS DISTINCT FROM OLD.retry_of_dispatch_id
                OR NEW.runner_job_id IS DISTINCT FROM OLD.runner_job_id
                OR NEW.manifest IS DISTINCT FROM OLD.manifest
                OR NEW.manifest_digest IS DISTINCT FROM OLD.manifest_digest
                OR NEW.confirmation_digest IS DISTINCT FROM OLD.confirmation_digest
                OR NEW.request_id IS DISTINCT FROM OLD.request_id
                OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
                OR NEW.idempotency_request_hash
                    IS DISTINCT FROM OLD.idempotency_request_hash
                OR NEW.created_at IS DISTINCT FROM OLD.created_at
                OR OLD.status <> 'dispatched'
                OR NEW.status NOT IN ('succeeded', 'failed', 'cancelled')
                OR NEW.terminal_at IS NULL
                OR (
                    NEW.status = 'succeeded'
                    AND NEW.error_code IS NOT NULL
                )
                OR (
                    NEW.status IN ('failed', 'cancelled')
                    AND NEW.error_code IS NULL
                )
            THEN
                RAISE EXCEPTION 'Delivery Dispatch mutation is forbidden'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER delivery_dispatches_10_update_guard
        BEFORE UPDATE ON delivery_dispatches
        FOR EACH ROW EXECUTE FUNCTION guard_delivery_dispatch_update();

        CREATE TRIGGER delivery_dispatches_99_delete_guard
        BEFORE DELETE ON delivery_dispatches
        FOR EACH ROW EXECUTE FUNCTION reject_delivery_immutable_change();
        """
    )


def _replace_review_audit_guard(*, include_lifecycle: bool) -> None:
    lifecycle_events = (
        """
                'local_delivery_failed',
                'local_delivery_cancelled',
    """
        if include_lifecycle
        else ""
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION guard_review_audit_event_insert()
        RETURNS trigger AS $$
        DECLARE expected_sequence integer;
        BEGIN
            IF NEW.event_type IN (
                'review_package_created',
                'review_package_invalidated',
                'review_decision_recorded',
                'release_readiness_evaluated',
                'delivery_authorization_created',
                'delivery_decision_recorded',
                'local_delivery_dispatched',
                {lifecycle_events}
                'local_delivery_succeeded'
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
            ELSIF NEW.review_package_id IS NOT NULL
                OR NEW.review_sequence IS NOT NULL
            THEN
                RAISE EXCEPTION 'Non-review AuditEvent cannot claim review sequence'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    _replace_review_audit_guard(include_lifecycle=False)
    op.execute(
        """
        DROP TRIGGER IF EXISTS delivery_dispatches_99_delete_guard
            ON delivery_dispatches;
        DROP TRIGGER IF EXISTS delivery_dispatches_10_update_guard
            ON delivery_dispatches;
        DROP TRIGGER IF EXISTS delivery_dispatches_00_insert_guard
            ON delivery_dispatches;
        DROP FUNCTION IF EXISTS guard_delivery_dispatch_update();
        DROP FUNCTION IF EXISTS guard_delivery_dispatch_insert();
        DROP TABLE IF EXISTS delivery_dispatches;
        """
    )
    _replace_authorization_guard(allow_retry=False)
