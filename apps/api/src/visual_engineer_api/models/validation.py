import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from visual_engineer_api.db.base import Base

VALIDATION_STATES = (
    "requested",
    "queued",
    "claimed",
    "running",
    "cancel_requested",
    "succeeded",
    "failed",
    "timed_out",
    "cancelled",
    "recovery_required",
)


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_validation_runs_idempotency_key"),
        UniqueConstraint("runner_job_id", name="uq_validation_runs_runner_job"),
        CheckConstraint(
            "state IN ('requested', 'queued', 'claimed', 'running', 'cancel_requested', "
            "'succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required')",
            name="ck_validation_runs_state",
        ),
        CheckConstraint("profile_id = 'fixture-python-stdlib-v1'", name="ck_validation_profile"),
        CheckConstraint("profile_version = 1", name="ck_validation_profile_version"),
        CheckConstraint("policy_digest ~ '^[0-9a-f]{64}$'", name="ck_validation_policy_digest"),
        CheckConstraint(
            "idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_validation_idempotency_hash",
        ),
        CheckConstraint("timeout_seconds BETWEEN 1 AND 120", name="ck_validation_timeout"),
        CheckConstraint(
            "max_output_bytes BETWEEN 256 AND 65536",
            name="ck_validation_output_budget",
        ),
        CheckConstraint(
            "max_artifact_bytes BETWEEN 0 AND 1048576 AND max_artifact_count BETWEEN 0 AND 20",
            name="ck_validation_artifact_budget",
        ),
        CheckConstraint(
            "(state IN ('succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required')) "
            "= (completed_at IS NOT NULL)",
            name="ck_validation_terminal_timestamp",
        ),
        CheckConstraint(
            "(attempt_id IS NULL AND lease_id IS NULL) OR "
            "(attempt_id IS NOT NULL AND lease_id IS NOT NULL)",
            name="ck_validation_attempt_lease_pair",
        ),
        Index("ix_validation_runs_state_created", "state", "created_at"),
        Index("ix_validation_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_validation_runs_grant_created", "execution_grant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    checkpoint_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_grants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    runner_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runner_jobs.id", ondelete="RESTRICT")
    )
    runner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runners.id", ondelete="RESTRICT")
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runner_job_attempts.id", ondelete="RESTRICT")
    )
    lease_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="requested")
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_output_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_artifact_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_artifact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ValidationStepRun(Base):
    __tablename__ = "validation_step_runs"
    __table_args__ = (
        UniqueConstraint("validation_run_id", "sequence", name="uq_validation_steps_sequence"),
        CheckConstraint("sequence = 1", name="ck_validation_steps_sequence"),
        CheckConstraint("step_id = 'fixture-contract'", name="ck_validation_step_id"),
        CheckConstraint(
            "state IN ('queued', 'running', 'succeeded', 'failed', 'timed_out', "
            "'cancelled', 'recovery_required')",
            name="ck_validation_steps_state",
        ),
        CheckConstraint(
            "exit_code IS NULL OR exit_code BETWEEN 0 AND 255",
            name="ck_validation_step_exit_code",
        ),
        Index("ix_validation_steps_run", "validation_run_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    failure_code: Mapped[str | None] = mapped_column(String(64))


class ValidationEvidence(Base):
    __tablename__ = "validation_evidence"
    __table_args__ = (
        UniqueConstraint("validation_run_id", name="uq_validation_evidence_run"),
        UniqueConstraint(
            "validation_run_id",
            "attempt_id",
            "lease_id",
            name="uq_validation_evidence_fencing",
        ),
        CheckConstraint("exit_code BETWEEN 0 AND 255", name="ck_validation_evidence_exit"),
        CheckConstraint("duration_ms >= 0", name="ck_validation_evidence_duration"),
        CheckConstraint("redaction_count >= 0", name="ck_validation_evidence_redactions"),
        CheckConstraint(
            "artifact_count BETWEEN 0 AND 20 AND artifact_bytes BETWEEN 0 AND 1048576",
            name="ck_validation_evidence_artifacts",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("validation_runs.id", ondelete="RESTRICT"), nullable=False
    )
    runner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runners.id", ondelete="RESTRICT"), nullable=False
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runner_job_attempts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lease_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    result_schema_version: Mapped[int | None] = mapped_column(Integer)
    validation_step_id: Mapped[str | None] = mapped_column(String(64))
    source_revision: Mapped[str | None] = mapped_column(String(64))
    policy_digest: Mapped[str | None] = mapped_column(String(64))
    fixed_argv: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    fixed_argv_digest: Mapped[str | None] = mapped_column(String(64))
    fixed_cwd: Mapped[str | None] = mapped_column(String(128))
    fixed_environment_digest: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    exit_code: Mapped[int] = mapped_column(Integer, nullable=False)
    stdout: Mapped[str] = mapped_column(Text, nullable=False)
    stderr: Mapped[str] = mapped_column(Text, nullable=False)
    stdout_truncated: Mapped[bool] = mapped_column(nullable=False)
    stderr_truncated: Mapped[bool] = mapped_column(nullable=False)
    redaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    timed_out: Mapped[bool] = mapped_column(nullable=False)
    cancelled: Mapped[bool] = mapped_column(nullable=False)
    network_isolated: Mapped[bool] = mapped_column(nullable=False)
    filesystem_isolated: Mapped[bool] = mapped_column(nullable=False)
    sandbox_cleaned: Mapped[bool] = mapped_column(nullable=False)
    artifact_count: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    artifact_manifest_digest: Mapped[str | None] = mapped_column(String(64))
    side_effect_permit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("side_effect_permits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    side_effect_permit_sequence: Mapped[int | None] = mapped_column(Integer)
    side_effect_permit_digest: Mapped[str | None] = mapped_column(String(64))
    fencing_token: Mapped[str | None] = mapped_column(String(64))
    execution_envelope_digest: Mapped[str | None] = mapped_column(String(64))
    evidence_digest: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
