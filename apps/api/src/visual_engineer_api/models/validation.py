import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
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

VALIDATION_SUITE_STATES = (
    "requested",
    "queued",
    "running",
    "cancel_requested",
    "succeeded",
    "failed",
    "timed_out",
    "cancelled",
    "recovery_required",
)

VALIDATION_SUITE_STEP_STATES = (
    "pending",
    "queued",
    "running",
    "succeeded",
    "failed",
    "timed_out",
    "cancelled",
    "skipped",
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
        CheckConstraint(
            "profile_id IN ('fixture-python-stdlib-v1', 'fixture-python-manifest-v1')",
            name="ck_validation_profile",
        ),
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
        CheckConstraint(
            "step_id IN ('fixture-contract', 'fixture-manifest')",
            name="ck_validation_step_id",
        ),
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


class ValidationSuiteRun(Base):
    __tablename__ = "validation_suite_runs"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_validation_suite_runs_idempotency_key",
        ),
        UniqueConstraint(
            "execution_grant_id",
            name="uq_validation_suite_runs_execution_grant",
        ),
        UniqueConstraint(
            "root_suite_run_id",
            "attempt_number",
            name="uq_validation_suite_runs_root_attempt",
        ),
        UniqueConstraint(
            "retry_of_suite_run_id",
            "attempt_number",
            name="uq_validation_suite_runs_retry_attempt",
        ),
        CheckConstraint(
            "suite_id = 'fixture-integrity-suite-v1'",
            name="ck_validation_suite_id",
        ),
        CheckConstraint("suite_version = 1", name="ck_validation_suite_version"),
        CheckConstraint(
            "policy_digest ~ '^[0-9a-f]{64}$'",
            name="ck_validation_suite_policy_digest",
        ),
        CheckConstraint(
            "idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_validation_suite_idempotency_hash",
        ),
        CheckConstraint(
            "state IN ('requested', 'queued', 'running', 'cancel_requested', "
            "'succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required')",
            name="ck_validation_suite_state",
        ),
        CheckConstraint(
            "failure_policy = 'fail_fast'",
            name="ck_validation_suite_failure_policy",
        ),
        CheckConstraint(
            "total_timeout_seconds BETWEEN 1 AND 600",
            name="ck_validation_suite_timeout",
        ),
        CheckConstraint(
            "total_output_bytes BETWEEN 256 AND 262144",
            name="ck_validation_suite_output_budget",
        ),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 5 AND attempt_number BETWEEN 1 AND max_attempts",
            name="ck_validation_suite_attempt_budget",
        ),
        CheckConstraint(
            "combined_output_bytes BETWEEN 0 AND 262144",
            name="ck_validation_suite_output_consumption",
        ),
        CheckConstraint(
            "completed_step_count BETWEEN 0 AND step_count AND step_count BETWEEN 2 AND 16",
            name="ck_validation_suite_step_count",
        ),
        CheckConstraint(
            "(state IN ('succeeded', 'failed', 'timed_out', 'cancelled', "
            "'recovery_required')) = (completed_at IS NOT NULL)",
            name="ck_validation_suite_terminal_timestamp",
        ),
        CheckConstraint(
            "(attempt_number = 1 AND retry_of_suite_run_id IS NULL "
            "AND root_suite_run_id = id) OR "
            "(attempt_number > 1 AND retry_of_suite_run_id IS NOT NULL "
            "AND root_suite_run_id <> id)",
            name="ck_validation_suite_retry_binding",
        ),
        CheckConstraint(
            "suite_id = 'fixture-integrity-suite-v1' AND suite_version = 1 "
            "AND failure_policy = 'fail_fast' AND step_count = 2 "
            "AND total_timeout_seconds = 30 AND total_output_bytes = 10000 "
            "AND max_attempts = 2 AND attempt_number BETWEEN 1 AND 2",
            name="ck_validation_suite_trusted_definition",
        ),
        Index(
            "ix_validation_suite_runs_state_created",
            "state",
            "created_at",
        ),
        Index(
            "ix_validation_suite_runs_workspace_created",
            "workspace_id",
            "created_at",
        ),
        Index(
            "ix_validation_suite_runs_grant_created",
            "execution_grant_id",
            "created_at",
        ),
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
    suite_id: Mapped[str] = mapped_column(String(64), nullable=False)
    suite_version: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_policy: Mapped[str] = mapped_column(String(24), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="requested")
    step_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_step_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    total_output_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    combined_output_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    retry_of_suite_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_suite_runs.id", ondelete="RESTRICT"),
    )
    root_suite_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "validation_suite_runs.id",
            name="fk_validation_suite_runs_root",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ValidationSuiteStepRun(Base):
    __tablename__ = "validation_suite_step_runs"
    __table_args__ = (
        UniqueConstraint(
            "suite_run_id",
            "sequence",
            name="uq_validation_suite_steps_sequence",
        ),
        UniqueConstraint(
            "suite_run_id",
            "step_id",
            name="uq_validation_suite_steps_id",
        ),
        CheckConstraint(
            "sequence BETWEEN 1 AND 16",
            name="ck_validation_suite_step_sequence",
        ),
        CheckConstraint(
            "step_id IN ('fixture-contract', 'fixture-manifest')",
            name="ck_validation_suite_step_id",
        ),
        CheckConstraint(
            "profile_id IN ('fixture-python-stdlib-v1', 'fixture-python-manifest-v1')",
            name="ck_validation_suite_step_profile",
        ),
        CheckConstraint(
            "profile_version = 1",
            name="ck_validation_suite_step_profile_version",
        ),
        CheckConstraint(
            "state IN ('pending', 'queued', 'running', 'succeeded', 'failed', "
            "'timed_out', 'cancelled', 'skipped', 'recovery_required')",
            name="ck_validation_suite_step_state",
        ),
        CheckConstraint(
            "timeout_seconds BETWEEN 1 AND 120",
            name="ck_validation_suite_step_timeout",
        ),
        CheckConstraint(
            "max_output_bytes BETWEEN 256 AND 65536",
            name="ck_validation_suite_step_output_budget",
        ),
        CheckConstraint(
            "output_bytes BETWEEN 0 AND 65536",
            name="ck_validation_suite_step_output_consumption",
        ),
        CheckConstraint(
            "exit_code IS NULL OR exit_code BETWEEN 0 AND 255",
            name="ck_validation_suite_step_exit_code",
        ),
        CheckConstraint(
            "(state IN ('succeeded', 'failed', 'timed_out', 'cancelled', "
            "'skipped', 'recovery_required')) = (completed_at IS NOT NULL)",
            name="ck_validation_suite_step_terminal_timestamp",
        ),
        CheckConstraint(
            "(reused_from_step_run_id IS NULL) OR "
            "(state = 'succeeded' AND validation_run_id IS NOT NULL "
            "AND evidence_id IS NOT NULL)",
            name="ck_validation_suite_step_reuse",
        ),
        Index(
            "ix_validation_suite_steps_run",
            "suite_run_id",
            "sequence",
        ),
        Index(
            "ix_validation_suite_steps_validation_run",
            "validation_run_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_suite_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_id: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_output_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    validation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_runs.id", ondelete="RESTRICT"),
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
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("validation_evidence.id", ondelete="RESTRICT")
    )
    reused_from_step_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_suite_step_runs.id", ondelete="RESTRICT"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    output_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cleanup_succeeded: Mapped[bool | None] = mapped_column(Boolean)
    failure_code: Mapped[str | None] = mapped_column(String(64))


class ValidationSuiteResult(Base):
    __tablename__ = "validation_suite_results"
    __table_args__ = (
        UniqueConstraint(
            "suite_run_id",
            name="uq_validation_suite_results_run",
        ),
        CheckConstraint(
            "verdict IN ('succeeded', 'failed', 'timed_out', 'cancelled', 'recovery_required')",
            name="ck_validation_suite_result_verdict",
        ),
        CheckConstraint(
            "aggregate_digest ~ '^[0-9a-f]{64}$'",
            name="ck_validation_suite_result_digest",
        ),
        CheckConstraint(
            "combined_output_bytes >= 0 AND redaction_count >= 0",
            name="ck_validation_suite_result_consumption",
        ),
        CheckConstraint(
            "artifact_count = 0 AND artifact_bytes = 0",
            name="ck_validation_suite_result_zero_artifacts",
        ),
        CheckConstraint(
            "suite_id = 'fixture-integrity-suite-v1' AND suite_version = 1",
            name="ck_validation_suite_result_definition",
        ),
        CheckConstraint(
            "policy_digest ~ '^[0-9a-f]{64}$'",
            name="ck_validation_suite_result_policy_digest",
        ),
        CheckConstraint(
            "attempt_number BETWEEN 1 AND max_attempts AND max_attempts BETWEEN 1 AND 5",
            name="ck_validation_suite_result_attempt",
        ),
        CheckConstraint(
            "total_timeout_seconds BETWEEN 1 AND 600 AND total_output_bytes BETWEEN 256 AND 262144",
            name="ck_validation_suite_result_budgets",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_suite_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    root_suite_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_suite_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    execution_grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_grants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    suite_id: Mapped[str] = mapped_column(String(64), nullable=False)
    suite_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    policy_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    total_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    total_output_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[str] = mapped_column(String(24), nullable=False)
    profile_references: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence_references: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    runner_references: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    audit_event_references: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    combined_output_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    redaction_count: Mapped[int] = mapped_column(Integer, nullable=False)
    output_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    timed_out: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recovery_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cleanup_succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_invariant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    canonical_workspace_invariant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    artifact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    artifact_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    aggregate_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
