"""Create the Foundation task table.

Revision ID: 20260726_0001
Revises:
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260726_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("objective", sa.String(length=4000), nullable=False),
        sa.Column("repository_kind", sa.String(length=32), nullable=False),
        sa.Column("repository_display_name", sa.String(length=120), nullable=False),
        sa.Column("repository_locator", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
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
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("idempotency_request_hash", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "char_length(objective) BETWEEN 1 AND 4000", name="ck_tasks_objective_length"
        ),
        sa.CheckConstraint(
            "char_length(repository_display_name) BETWEEN 1 AND 120",
            name="ck_tasks_repository_display_name_length",
        ),
        sa.CheckConstraint(
            "repository_kind IN ('local_path', 'github')", name="ck_tasks_repository_kind"
        ),
        sa.CheckConstraint(
            "char_length(repository_locator) BETWEEN 1 AND 1024",
            name="ck_tasks_repository_locator_length",
        ),
        sa.CheckConstraint("status IN ('draft')", name="ck_tasks_status"),
        sa.CheckConstraint("char_length(title) BETWEEN 1 AND 120", name="ck_tasks_title_length"),
        sa.CheckConstraint("version >= 1", name="ck_tasks_version"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"], unique=False)
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_created_at", table_name="tasks")
    op.drop_table("tasks")
