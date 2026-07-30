"""Fence review decisions on trusted revision freshness.

Revision ID: 20260730_0012
Revises: 20260730_0011
Create Date: 2026-07-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260730_0012"
down_revision: str | None = "20260730_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _install_repository_revision_freshness()
    _install_revision_insert_guards()


def _install_repository_revision_freshness() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION lock_review_revision_authority(
            target_handle uuid
        )
        RETURNS void AS $$
            SELECT pg_advisory_xact_lock(
                hashtextextended(
                    'visualengineer:review-revision:' || target_handle::text,
                    0
                )
            )
        $$ LANGUAGE sql VOLATILE STRICT;

        CREATE OR REPLACE FUNCTION bump_review_freshness_repository_handle(
            target_handle uuid,
            change_kind text
        )
        RETURNS void AS $$
        DECLARE target_scope record;
        BEGIN
            FOR target_scope IN
                SELECT DISTINCT
                    scope.plan_id,
                    scope.workspace_id,
                    scope.checkpoint_id
                FROM review_freshness_states AS scope
                JOIN review_packages AS package
                    ON package.freshness_state_id = scope.id
                WHERE package.repository_handle_id = target_handle
                ORDER BY scope.plan_id, scope.workspace_id, scope.checkpoint_id
            LOOP
                PERFORM bump_review_freshness_scope(
                    target_scope.plan_id,
                    target_scope.workspace_id,
                    target_scope.checkpoint_id,
                    change_kind,
                    'source_revision_changed'
                );
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def _install_revision_insert_guards() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION guard_review_decision_revision_insert()
        RETURNS trigger AS $$
        DECLARE package_handle_id uuid;
        DECLARE package_revision text;
        DECLARE handle_row repository_handles%ROWTYPE;
        BEGIN
            SELECT package.repository_handle_id, package.source_revision
            INTO package_handle_id, package_revision
            FROM review_packages AS package
            WHERE package.id = NEW.review_package_id;

            PERFORM lock_review_revision_authority(package_handle_id);
            SELECT * INTO handle_row
            FROM repository_handles
            WHERE id = package_handle_id
            FOR UPDATE;

            IF package_handle_id IS NULL
                OR handle_row.id IS NULL
                OR handle_row.current_revision IS DISTINCT FROM package_revision
                OR handle_row.status IS DISTINCT FROM 'available'
            THEN
                RAISE EXCEPTION
                    'Trusted Repository revision cannot receive a Review Decision'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER review_decisions_00_revision_guard
        BEFORE INSERT ON review_decisions
        FOR EACH ROW EXECUTE FUNCTION guard_review_decision_revision_insert();

        CREATE OR REPLACE FUNCTION guard_readiness_revision_insert()
        RETURNS trigger AS $$
        DECLARE package_handle_id uuid;
        DECLARE package_revision text;
        DECLARE handle_row repository_handles%ROWTYPE;
        BEGIN
            SELECT package.repository_handle_id, package.source_revision
            INTO package_handle_id, package_revision
            FROM review_packages AS package
            WHERE package.id = NEW.review_package_id;

            PERFORM lock_review_revision_authority(package_handle_id);
            SELECT * INTO handle_row
            FROM repository_handles
            WHERE id = package_handle_id
            FOR UPDATE;

            IF package_handle_id IS NULL
                OR handle_row.id IS NULL
                OR handle_row.current_revision IS DISTINCT FROM package_revision
                OR handle_row.status IS DISTINCT FROM 'available'
            THEN
                RAISE EXCEPTION
                    'Trusted Repository revision cannot receive readiness'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER readiness_verdicts_00_revision_guard
        BEFORE INSERT ON release_readiness_verdicts
        FOR EACH ROW EXECUTE FUNCTION guard_readiness_revision_insert();
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS readiness_verdicts_00_revision_guard
            ON release_readiness_verdicts;
        DROP TRIGGER IF EXISTS review_decisions_00_revision_guard
            ON review_decisions;
        DROP FUNCTION IF EXISTS guard_readiness_revision_insert();
        DROP FUNCTION IF EXISTS guard_review_decision_revision_insert();

        DROP FUNCTION IF EXISTS bump_review_freshness_repository_handle(uuid, text);
        DROP FUNCTION IF EXISTS lock_review_revision_authority(uuid);
        """
    )
