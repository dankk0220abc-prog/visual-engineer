"""Bind Validation result execution-envelope and evidence digests.

Revision ID: 20260729_0007
Revises: 20260729_0006
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0007"
down_revision: str | None = "20260729_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("validation_evidence", sa.Column("result_schema_version", sa.Integer()))
    op.add_column("validation_evidence", sa.Column("validation_step_id", sa.String(64)))
    op.add_column("validation_evidence", sa.Column("source_revision", sa.String(64)))
    op.add_column("validation_evidence", sa.Column("policy_digest", sa.String(64)))
    op.add_column("validation_evidence", sa.Column("fixed_argv_digest", sa.String(64)))
    op.add_column("validation_evidence", sa.Column("fixed_cwd", sa.String(128)))
    op.add_column(
        "validation_evidence",
        sa.Column("fixed_environment_digest", sa.String(64)),
    )
    op.add_column(
        "validation_evidence",
        sa.Column("artifact_manifest_digest", sa.String(64)),
    )
    op.add_column(
        "validation_evidence",
        sa.Column("side_effect_permit_sequence", sa.Integer()),
    )
    op.add_column(
        "validation_evidence",
        sa.Column("side_effect_permit_digest", sa.String(64)),
    )
    op.add_column("validation_evidence", sa.Column("fencing_token", sa.String(64)))
    op.add_column(
        "validation_evidence",
        sa.Column("execution_envelope_digest", sa.String(64)),
    )
    op.add_column("validation_evidence", sa.Column("evidence_digest", sa.String(64)))


def downgrade() -> None:
    op.drop_column("validation_evidence", "evidence_digest")
    op.drop_column("validation_evidence", "execution_envelope_digest")
    op.drop_column("validation_evidence", "fencing_token")
    op.drop_column("validation_evidence", "side_effect_permit_digest")
    op.drop_column("validation_evidence", "side_effect_permit_sequence")
    op.drop_column("validation_evidence", "artifact_manifest_digest")
    op.drop_column("validation_evidence", "fixed_environment_digest")
    op.drop_column("validation_evidence", "fixed_cwd")
    op.drop_column("validation_evidence", "fixed_argv_digest")
    op.drop_column("validation_evidence", "policy_digest")
    op.drop_column("validation_evidence", "source_revision")
    op.drop_column("validation_evidence", "validation_step_id")
    op.drop_column("validation_evidence", "result_schema_version")
