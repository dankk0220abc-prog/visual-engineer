"""Add durable product-safe task content classification.

Revision ID: 20260810_0017
Revises: 20260809_0016
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0017"
down_revision: str | None = "20260809_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("classification", sa.String(24), nullable=True, server_default="user"),
    )
    op.execute(
        """
        UPDATE tasks
        SET classification = CASE
            WHEN idempotency_key LIKE 'zhipu-live-canary-task-%' THEN 'live_canary'
            WHEN idempotency_key = 'phase4-browser-fixture-v1' THEN 'fixture'
            ELSE 'user'
        END
        """
    )
    op.alter_column("tasks", "classification", nullable=False, server_default="user")
    op.create_check_constraint(
        "ck_tasks_classification",
        "tasks",
        "classification IN ('user', 'demo', 'system_validation', 'security_test', "
        "'fixture', 'live_canary')",
    )
    op.create_index("ix_tasks_classification_created", "tasks", ["classification", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_tasks_classification_created", table_name="tasks")
    op.drop_constraint("ck_tasks_classification", "tasks", type_="check")
    op.drop_column("tasks", "classification")
