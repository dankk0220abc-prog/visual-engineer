"""Add governed fixture-only local Git delivery.

Revision ID: 20260731_0013
Revises: 20260730_0012
Create Date: 2026-07-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260731_0013"
down_revision: str | None = "20260730_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE delivery_authorizations (
            id uuid PRIMARY KEY,
            authorization_version integer NOT NULL DEFAULT 1,
            review_package_id uuid NOT NULL
                REFERENCES review_packages(id) ON DELETE RESTRICT,
            review_decision_id uuid NOT NULL
                REFERENCES review_decisions(id) ON DELETE RESTRICT,
            readiness_verdict_id uuid NOT NULL
                REFERENCES release_readiness_verdicts(id) ON DELETE RESTRICT,
            freshness_generation integer NOT NULL,
            package_digest varchar(64) NOT NULL,
            decision_digest varchar(64) NOT NULL,
            readiness_digest varchar(64) NOT NULL,
            execution_grant_id uuid NOT NULL
                REFERENCES execution_grants(id) ON DELETE RESTRICT,
            workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
            checkpoint_id uuid NOT NULL
                REFERENCES workspace_checkpoints(id) ON DELETE RESTRICT,
            checkpoint_fingerprint varchar(64) NOT NULL,
            checkpoint_diff_hash varchar(64) NOT NULL,
            repository_handle_id uuid NOT NULL
                REFERENCES repository_handles(id) ON DELETE RESTRICT,
            source_revision varchar(64) NOT NULL,
            branch_ref varchar(96) NOT NULL,
            commit_message varchar(160) NOT NULL,
            local_git_commit_access boolean NOT NULL DEFAULT true,
            remote_access boolean NOT NULL DEFAULT false,
            push_access boolean NOT NULL DEFAULT false,
            pull_request_access boolean NOT NULL DEFAULT false,
            tag_access boolean NOT NULL DEFAULT false,
            deployment_access boolean NOT NULL DEFAULT false,
            source_repository_write_access boolean NOT NULL DEFAULT false,
            status varchar(16) NOT NULL DEFAULT 'pending',
            policy_hash varchar(64) NOT NULL,
            idempotency_key varchar(255) NOT NULL,
            idempotency_request_hash varchar(64) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            decided_at timestamptz,
            dispatched_at timestamptz,
            terminal_at timestamptz,
            expires_at timestamptz NOT NULL,
            error_code varchar(64),
            CONSTRAINT uq_delivery_authorizations_package UNIQUE (review_package_id),
            CONSTRAINT uq_delivery_authorizations_branch_ref UNIQUE (branch_ref),
            CONSTRAINT uq_delivery_authorizations_idempotency UNIQUE (idempotency_key),
            CONSTRAINT ck_delivery_authorizations_version
                CHECK (authorization_version = 1),
            CONSTRAINT ck_delivery_authorizations_status CHECK (
                status IN (
                    'pending', 'approved', 'rejected', 'dispatched',
                    'succeeded', 'failed', 'cancelled', 'stale'
                )
            ),
            CONSTRAINT ck_delivery_authorizations_generation
                CHECK (freshness_generation >= 1),
            CONSTRAINT ck_delivery_authorizations_digests CHECK (
                package_digest ~ '^[0-9a-f]{64}$'
                AND decision_digest ~ '^[0-9a-f]{64}$'
                AND readiness_digest ~ '^[0-9a-f]{64}$'
                AND checkpoint_fingerprint ~ '^[0-9a-f]{64}$'
                AND checkpoint_diff_hash ~ '^[0-9a-f]{64}$'
                AND policy_hash ~ '^[0-9a-f]{64}$'
                AND idempotency_request_hash ~ '^[0-9a-f]{64}$'
            ),
            CONSTRAINT ck_delivery_authorizations_branch CHECK (
                branch_ref ~ '^refs/heads/visual-engineer/[0-9a-f]{32}$'
            ),
            CONSTRAINT ck_delivery_authorizations_message CHECK (
                commit_message ~
                    '^VisualEngineer: governed local delivery [0-9a-f]{8}$'
            ),
            CONSTRAINT ck_delivery_authorizations_local_only CHECK (
                local_git_commit_access = true
                AND remote_access = false
                AND push_access = false
                AND pull_request_access = false
                AND tag_access = false
                AND deployment_access = false
                AND source_repository_write_access = false
            ),
            CONSTRAINT ck_delivery_authorizations_expiry
                CHECK (expires_at > created_at),
            CONSTRAINT ck_delivery_authorizations_decision_time CHECK (
                (status = 'pending' AND decided_at IS NULL)
                OR (status <> 'pending' AND decided_at IS NOT NULL)
            ),
            CONSTRAINT ck_delivery_authorizations_dispatch_time CHECK (
                (
                    status IN ('dispatched', 'succeeded', 'failed', 'cancelled')
                    AND dispatched_at IS NOT NULL
                )
                OR (
                    status NOT IN ('dispatched', 'succeeded', 'failed', 'cancelled')
                    AND dispatched_at IS NULL
                )
            ),
            CONSTRAINT ck_delivery_authorizations_terminal_time CHECK (
                (
                    status IN ('rejected', 'succeeded', 'failed', 'cancelled', 'stale')
                    AND terminal_at IS NOT NULL
                )
                OR (
                    status NOT IN ('rejected', 'succeeded', 'failed', 'cancelled', 'stale')
                    AND terminal_at IS NULL
                )
            )
        );
        CREATE INDEX ix_delivery_authorizations_status_created
            ON delivery_authorizations(status, created_at);
        CREATE INDEX ix_delivery_authorizations_workspace
            ON delivery_authorizations(workspace_id, created_at);

        CREATE TABLE delivery_authorization_decisions (
            id uuid PRIMARY KEY,
            delivery_authorization_id uuid NOT NULL
                REFERENCES delivery_authorizations(id) ON DELETE RESTRICT,
            authorization_policy_hash varchar(64) NOT NULL,
            decision varchar(16) NOT NULL,
            reason varchar(2000),
            actor_type varchar(32) NOT NULL DEFAULT 'local_user',
            request_id varchar(128) NOT NULL,
            idempotency_key varchar(255) NOT NULL,
            idempotency_request_hash varchar(64) NOT NULL,
            decision_digest varchar(64) NOT NULL,
            local_git_commit_authorized boolean NOT NULL,
            remote_access boolean NOT NULL DEFAULT false,
            push_access boolean NOT NULL DEFAULT false,
            pull_request_access boolean NOT NULL DEFAULT false,
            tag_access boolean NOT NULL DEFAULT false,
            deployment_access boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_delivery_authorization_decisions_authorization
                UNIQUE (delivery_authorization_id),
            CONSTRAINT uq_delivery_authorization_decisions_idempotency
                UNIQUE (idempotency_key),
            CONSTRAINT ck_delivery_authorization_decisions_decision
                CHECK (decision IN ('approve', 'reject')),
            CONSTRAINT ck_delivery_authorization_decisions_actor
                CHECK (actor_type = 'local_user'),
            CONSTRAINT ck_delivery_authorization_decisions_reason CHECK (
                decision <> 'reject'
                OR (reason IS NOT NULL AND char_length(trim(reason)) > 0)
            ),
            CONSTRAINT ck_delivery_authorization_decisions_digests CHECK (
                authorization_policy_hash ~ '^[0-9a-f]{64}$'
                AND idempotency_request_hash ~ '^[0-9a-f]{64}$'
                AND decision_digest ~ '^[0-9a-f]{64}$'
            ),
            CONSTRAINT ck_delivery_authorization_decisions_authority CHECK (
                (decision = 'approve' AND local_git_commit_authorized = true)
                OR (decision = 'reject' AND local_git_commit_authorized = false)
            ),
            CONSTRAINT ck_delivery_authorization_decisions_no_remote CHECK (
                remote_access = false AND push_access = false
                AND pull_request_access = false AND tag_access = false
                AND deployment_access = false
            )
        );

        ALTER TABLE runner_jobs
            ADD COLUMN delivery_authorization_id uuid
            REFERENCES delivery_authorizations(id) ON DELETE RESTRICT;
        ALTER TABLE side_effect_permits
            ADD COLUMN delivery_authorization_id uuid
            REFERENCES delivery_authorizations(id) ON DELETE RESTRICT;

        ALTER TABLE permission_envelopes
            DROP CONSTRAINT ck_permission_envelopes_authorization_source;
        ALTER TABLE permission_envelopes
            ADD CONSTRAINT ck_permission_envelopes_authorization_source CHECK (
                authorization_source IN (
                    'local_user_job_dispatch',
                    'execution_grant',
                    'execution_grant_and_delivery_authorization'
                )
            );
        ALTER TABLE permission_envelopes
            DROP CONSTRAINT ck_permission_envelopes_authority_repository;
        ALTER TABLE permission_envelopes
            ADD CONSTRAINT ck_permission_envelopes_authority_repository CHECK (
                (
                    authorization_source = 'local_user_job_dispatch'
                    AND repository_access = 'none'
                )
                OR (
                    authorization_source IN (
                        'execution_grant',
                        'execution_grant_and_delivery_authorization'
                    )
                    AND repository_access = 'isolated_workspace'
                )
            );

        ALTER TABLE runner_jobs DROP CONSTRAINT ck_runner_jobs_kind;
        ALTER TABLE runner_jobs ADD CONSTRAINT ck_runner_jobs_kind CHECK (
            kind IN (
                'system_diagnostic_v1', 'controlled_wait_v1',
                'workspace_prepare_v1', 'workspace_list_v1',
                'workspace_read_text_v1', 'workspace_write_text_v1',
                'workspace_status_v1', 'workspace_diff_v1',
                'workspace_rollback_v1', 'workspace_discard_v1',
                'validation_execute_v1', 'workspace_git_commit_v1'
            )
        );
        ALTER TABLE runner_jobs ADD CONSTRAINT ck_runner_jobs_delivery_binding CHECK (
            (
                kind = 'workspace_git_commit_v1'
                AND delivery_authorization_id IS NOT NULL
            )
            OR (
                kind <> 'workspace_git_commit_v1'
                AND delivery_authorization_id IS NULL
            )
        );

        ALTER TABLE side_effect_permits
            DROP CONSTRAINT ck_side_effect_permits_operation;
        ALTER TABLE side_effect_permits
            ADD CONSTRAINT ck_side_effect_permits_operation CHECK (
                operation IN (
                    'prepare', 'write_text', 'rollback', 'discard',
                    'validate', 'git_commit'
                )
            );
        ALTER TABLE side_effect_permits
            ADD CONSTRAINT ck_side_effect_permits_delivery_binding CHECK (
                (
                    operation = 'git_commit'
                    AND delivery_authorization_id IS NOT NULL
                )
                OR (
                    operation <> 'git_commit'
                    AND delivery_authorization_id IS NULL
                )
            );

        CREATE TABLE local_deliveries (
            id uuid PRIMARY KEY,
            delivery_authorization_id uuid NOT NULL
                REFERENCES delivery_authorizations(id) ON DELETE RESTRICT,
            runner_job_id uuid NOT NULL
                REFERENCES runner_jobs(id) ON DELETE RESTRICT,
            runner_attempt_id uuid NOT NULL
                REFERENCES runner_job_attempts(id) ON DELETE RESTRICT,
            side_effect_permit_id uuid NOT NULL
                REFERENCES side_effect_permits(id) ON DELETE RESTRICT,
            workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
            checkpoint_id uuid NOT NULL
                REFERENCES workspace_checkpoints(id) ON DELETE RESTRICT,
            checkpoint_fingerprint varchar(64) NOT NULL,
            checkpoint_diff_hash varchar(64) NOT NULL,
            branch_ref varchar(96) NOT NULL,
            commit_oid varchar(64) NOT NULL,
            tree_oid varchar(64) NOT NULL,
            parent_oid varchar(64) NOT NULL,
            result_digest varchar(64) NOT NULL,
            remote_access boolean NOT NULL DEFAULT false,
            pushed boolean NOT NULL DEFAULT false,
            pull_request_created boolean NOT NULL DEFAULT false,
            tagged boolean NOT NULL DEFAULT false,
            deployed boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_local_deliveries_authorization
                UNIQUE (delivery_authorization_id),
            CONSTRAINT uq_local_deliveries_job UNIQUE (runner_job_id),
            CONSTRAINT uq_local_deliveries_branch_ref UNIQUE (branch_ref),
            CONSTRAINT ck_local_deliveries_digests CHECK (
                commit_oid ~ '^[0-9a-f]{40,64}$'
                AND tree_oid ~ '^[0-9a-f]{40,64}$'
                AND parent_oid ~ '^[0-9a-f]{40,64}$'
                AND checkpoint_fingerprint ~ '^[0-9a-f]{64}$'
                AND checkpoint_diff_hash ~ '^[0-9a-f]{64}$'
                AND result_digest ~ '^[0-9a-f]{64}$'
            ),
            CONSTRAINT ck_local_deliveries_branch CHECK (
                branch_ref ~ '^refs/heads/visual-engineer/[0-9a-f]{32}$'
            ),
            CONSTRAINT ck_local_deliveries_no_remote CHECK (
                remote_access = false AND pushed = false
                AND pull_request_created = false AND tagged = false
                AND deployed = false
            )
        );
        """
    )
    _install_delivery_guards()
    _extend_review_audit_guard()


def _install_delivery_guards() -> None:
    op.execute(
        """
        CREATE FUNCTION guard_delivery_authorization_insert()
        RETURNS trigger AS $$
        DECLARE package_row review_packages%ROWTYPE;
        DECLARE decision_row review_decisions%ROWTYPE;
        DECLARE readiness_row release_readiness_verdicts%ROWTYPE;
        DECLARE scope_generation integer;
        DECLARE workspace_row workspaces%ROWTYPE;
        DECLARE checkpoint_row workspace_checkpoints%ROWTYPE;
        DECLARE handle_row repository_handles%ROWTYPE;
        BEGIN
            SELECT * INTO package_row FROM review_packages
                WHERE id = NEW.review_package_id FOR UPDATE;
            SELECT * INTO decision_row FROM review_decisions
                WHERE id = NEW.review_decision_id FOR UPDATE;
            SELECT * INTO readiness_row FROM release_readiness_verdicts
                WHERE id = NEW.readiness_verdict_id FOR UPDATE;
            SELECT generation INTO scope_generation FROM review_freshness_states
                WHERE id = package_row.freshness_state_id FOR UPDATE;
            SELECT * INTO workspace_row FROM workspaces
                WHERE id = NEW.workspace_id FOR UPDATE;
            SELECT * INTO checkpoint_row FROM workspace_checkpoints
                WHERE id = NEW.checkpoint_id FOR UPDATE;
            SELECT * INTO handle_row FROM repository_handles
                WHERE id = NEW.repository_handle_id FOR UPDATE;

            IF package_row.id IS NULL
                OR decision_row.id IS NULL
                OR readiness_row.id IS NULL
                OR workspace_row.id IS NULL
                OR checkpoint_row.id IS NULL
                OR handle_row.id IS NULL
                OR decision_row.review_package_id IS DISTINCT FROM package_row.id
                OR readiness_row.review_package_id IS DISTINCT FROM package_row.id
                OR readiness_row.review_decision_id IS DISTINCT FROM decision_row.id
                OR decision_row.decision IS DISTINCT FROM 'approve'
                OR readiness_row.verdict IS DISTINCT FROM 'ready'
                OR package_row.freshness_generation IS DISTINCT FROM scope_generation
                OR NEW.freshness_generation IS DISTINCT FROM scope_generation
                OR EXISTS (
                    SELECT 1 FROM review_package_invalidations
                    WHERE review_package_id = package_row.id
                )
                OR NEW.package_digest IS DISTINCT FROM package_row.package_digest
                OR NEW.decision_digest IS DISTINCT FROM decision_row.decision_digest
                OR NEW.readiness_digest IS DISTINCT FROM readiness_row.verdict_digest
                OR NEW.execution_grant_id IS DISTINCT FROM workspace_row.grant_id
                OR NEW.workspace_id IS DISTINCT FROM package_row.workspace_id
                OR NEW.checkpoint_id IS DISTINCT FROM package_row.checkpoint_id
                OR NEW.checkpoint_fingerprint
                    IS DISTINCT FROM package_row.checkpoint_fingerprint
                OR NEW.checkpoint_diff_hash
                    IS DISTINCT FROM package_row.checkpoint_diff_hash
                OR NEW.repository_handle_id
                    IS DISTINCT FROM package_row.repository_handle_id
                OR NEW.source_revision IS DISTINCT FROM package_row.source_revision
                OR workspace_row.state IS DISTINCT FROM 'sealed'
                OR workspace_row.current_tree_hash
                    IS DISTINCT FROM NEW.checkpoint_fingerprint
                OR checkpoint_row.workspace_id IS DISTINCT FROM NEW.workspace_id
                OR checkpoint_row.tree_fingerprint
                    IS DISTINCT FROM NEW.checkpoint_fingerprint
                OR checkpoint_row.diff_hash IS DISTINCT FROM NEW.checkpoint_diff_hash
                OR handle_row.status IS DISTINCT FROM 'available'
                OR handle_row.current_revision IS DISTINCT FROM NEW.source_revision
                OR NEW.branch_ref IS DISTINCT FROM
                    'refs/heads/visual-engineer/' ||
                    replace(NEW.workspace_id::text, '-', '')
                OR NEW.commit_message IS DISTINCT FROM
                    'VisualEngineer: governed local delivery ' ||
                    substring(replace(NEW.id::text, '-', '') FROM 1 FOR 8)
            THEN
                RAISE EXCEPTION 'Delivery Authorization binding is stale or invalid'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER delivery_authorizations_00_insert_guard
        BEFORE INSERT ON delivery_authorizations
        FOR EACH ROW EXECUTE FUNCTION guard_delivery_authorization_insert();

        CREATE FUNCTION guard_delivery_authorization_update()
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
                )
            THEN
                RAISE EXCEPTION 'Delivery Authorization mutation is forbidden'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER delivery_authorizations_10_update_guard
        BEFORE UPDATE ON delivery_authorizations
        FOR EACH ROW EXECUTE FUNCTION guard_delivery_authorization_update();

        CREATE FUNCTION reject_delivery_immutable_change()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Governed delivery evidence is immutable'
                USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER delivery_authorizations_99_delete_guard
        BEFORE DELETE ON delivery_authorizations
        FOR EACH ROW EXECUTE FUNCTION reject_delivery_immutable_change();
        CREATE TRIGGER delivery_authorization_decisions_99_mutation_guard
        BEFORE UPDATE OR DELETE ON delivery_authorization_decisions
        FOR EACH ROW EXECUTE FUNCTION reject_delivery_immutable_change();
        CREATE TRIGGER local_deliveries_99_mutation_guard
        BEFORE UPDATE OR DELETE ON local_deliveries
        FOR EACH ROW EXECUTE FUNCTION reject_delivery_immutable_change();
        """
    )


def _extend_review_audit_guard() -> None:
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
                'release_readiness_evaluated',
                'delivery_authorization_created',
                'delivery_decision_recorded',
                'local_delivery_dispatched',
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
    op.execute(
        """
        DROP TRIGGER IF EXISTS local_deliveries_99_mutation_guard
            ON local_deliveries;
        DROP TRIGGER IF EXISTS delivery_authorization_decisions_99_mutation_guard
            ON delivery_authorization_decisions;
        DROP TRIGGER IF EXISTS delivery_authorizations_99_delete_guard
            ON delivery_authorizations;
        DROP TRIGGER IF EXISTS delivery_authorizations_10_update_guard
            ON delivery_authorizations;
        DROP TRIGGER IF EXISTS delivery_authorizations_00_insert_guard
            ON delivery_authorizations;
        DROP FUNCTION IF EXISTS reject_delivery_immutable_change();
        DROP FUNCTION IF EXISTS guard_delivery_authorization_update();
        DROP FUNCTION IF EXISTS guard_delivery_authorization_insert();

        DROP TABLE IF EXISTS local_deliveries;

        ALTER TABLE side_effect_permits
            DROP CONSTRAINT IF EXISTS ck_side_effect_permits_delivery_binding;
        ALTER TABLE side_effect_permits
            DROP CONSTRAINT ck_side_effect_permits_operation;
        ALTER TABLE side_effect_permits
            ADD CONSTRAINT ck_side_effect_permits_operation CHECK (
                operation IN ('prepare', 'write_text', 'rollback', 'discard', 'validate')
            );
        ALTER TABLE side_effect_permits
            DROP COLUMN IF EXISTS delivery_authorization_id;

        ALTER TABLE runner_jobs
            DROP CONSTRAINT IF EXISTS ck_runner_jobs_delivery_binding;
        ALTER TABLE runner_jobs DROP CONSTRAINT ck_runner_jobs_kind;
        ALTER TABLE runner_jobs ADD CONSTRAINT ck_runner_jobs_kind CHECK (
            kind IN (
                'system_diagnostic_v1', 'controlled_wait_v1',
                'workspace_prepare_v1', 'workspace_list_v1',
                'workspace_read_text_v1', 'workspace_write_text_v1',
                'workspace_status_v1', 'workspace_diff_v1',
                'workspace_rollback_v1', 'workspace_discard_v1',
                'validation_execute_v1'
            )
        );
        ALTER TABLE runner_jobs DROP COLUMN IF EXISTS delivery_authorization_id;

        ALTER TABLE permission_envelopes
            DROP CONSTRAINT ck_permission_envelopes_authority_repository;
        ALTER TABLE permission_envelopes
            ADD CONSTRAINT ck_permission_envelopes_authority_repository CHECK (
                (
                    authorization_source = 'local_user_job_dispatch'
                    AND repository_access = 'none'
                )
                OR (
                    authorization_source = 'execution_grant'
                    AND repository_access = 'isolated_workspace'
                )
            );
        ALTER TABLE permission_envelopes
            DROP CONSTRAINT ck_permission_envelopes_authorization_source;
        ALTER TABLE permission_envelopes
            ADD CONSTRAINT ck_permission_envelopes_authorization_source CHECK (
                authorization_source IN (
                    'local_user_job_dispatch', 'execution_grant'
                )
            );

        DROP TABLE IF EXISTS delivery_authorization_decisions;
        DROP TABLE IF EXISTS delivery_authorizations;
        """
    )
