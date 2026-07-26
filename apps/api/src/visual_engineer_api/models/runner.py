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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from visual_engineer_api.db.base import Base


class Runner(Base):
    __tablename__ = "runners"
    __table_args__ = (
        CheckConstraint(
            "status IN ('registered', 'online', 'offline', 'revoked')",
            name="ck_runners_status",
        ),
        CheckConstraint("protocol_version = 1", name="ck_runners_protocol_version"),
        CheckConstraint("version >= 1", name="ck_runners_version"),
        CheckConstraint(
            "(status = 'revoked') = (revoked_at IS NOT NULL)",
            name="ck_runners_revoked_at",
        ),
        Index("ix_runners_last_seen_at", "last_seen_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    protocol_version: Mapped[int] = mapped_column(Integer, nullable=False)
    software_version: Mapped[str] = mapped_column(String(64), nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="registered")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PermissionEnvelope(Base):
    __tablename__ = "permission_envelopes"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_permission_envelopes_job_id"),
        CheckConstraint("envelope_version = 1", name="ck_permission_envelopes_version"),
        CheckConstraint(
            "authorization_source = 'local_user_job_dispatch'",
            name="ck_permission_envelopes_authorization_source",
        ),
        CheckConstraint("repository_access = 'none'", name="ck_permission_envelopes_repository"),
        CheckConstraint("shell_access = false", name="ck_permission_envelopes_shell"),
        CheckConstraint(
            "network_policy = 'control_plane_only'",
            name="ck_permission_envelopes_network",
        ),
        CheckConstraint(
            "max_runtime_seconds BETWEEN 1 AND 60",
            name="ck_permission_envelopes_runtime",
        ),
        CheckConstraint("lease_seconds BETWEEN 2 AND 60", name="ck_permission_envelopes_lease"),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 5",
            name="ck_permission_envelopes_attempts",
        ),
        CheckConstraint(
            "max_result_bytes BETWEEN 256 AND 65536",
            name="ck_permission_envelopes_result_bytes",
        ),
        CheckConstraint("expires_at > issued_at", name="ck_permission_envelopes_expiry"),
        CheckConstraint(
            "policy_hash ~ '^[0-9a-f]{64}$'",
            name="ck_permission_envelopes_policy_hash",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    envelope_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    authorization_source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="local_user_job_dispatch"
    )
    allowed_capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    repository_access: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    shell_access: Mapped[bool] = mapped_column(nullable=False, default=False)
    network_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default="control_plane_only"
    )
    max_runtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    max_result_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RunnerJob(Base):
    __tablename__ = "runner_jobs"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('system_diagnostic_v1', 'controlled_wait_v1')",
            name="ck_runner_jobs_kind",
        ),
        CheckConstraint(
            "state IN ('queued', 'leased', 'running', 'cancel_requested', "
            "'succeeded', 'cancelled', 'failed')",
            name="ck_runner_jobs_state",
        ),
        CheckConstraint("requested_by = 'local_user'", name="ck_runner_jobs_requested_by"),
        CheckConstraint("attempt_count >= 0", name="ck_runner_jobs_attempt_count"),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 5 AND attempt_count <= max_attempts",
            name="ck_runner_jobs_attempt_budget",
        ),
        CheckConstraint("version >= 1", name="ck_runner_jobs_version"),
        UniqueConstraint(
            "permission_envelope_id",
            name="uq_runner_jobs_permission_envelope_id",
        ),
        Index("ix_runner_jobs_state_created_at", "state", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    permission_envelope_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permission_envelopes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_by: Mapped[str] = mapped_column(
        String(32), nullable=False, default="local_user", server_default="local_user"
    )
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    active_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "runner_job_attempts.id",
            name="fk_runner_jobs_active_attempt_id",
            ondelete="SET NULL",
            use_alter=True,
        ),
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunnerJobAttempt(Base):
    __tablename__ = "runner_job_attempts"
    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="uq_runner_job_attempt_number"),
        CheckConstraint("attempt_number >= 1", name="ck_runner_job_attempt_number"),
        CheckConstraint(
            "state IN ('leased', 'running', 'succeeded', 'cancelled', 'failed', 'lease_expired')",
            name="ck_runner_job_attempts_state",
        ),
        Index(
            "uq_runner_job_attempt_active",
            "job_id",
            unique=True,
            postgresql_where=text("state IN ('leased', 'running')"),
        ),
        Index("ix_runner_job_attempts_lease", "state", "leased_until"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runner_jobs.id", ondelete="CASCADE"), nullable=False
    )
    runner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runners.id", ondelete="RESTRICT"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="leased")
    leased_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RunnerJobEvent(Base):
    __tablename__ = "runner_job_events"
    __table_args__ = (
        CheckConstraint("sequence >= 1", name="ck_runner_job_events_sequence"),
        CheckConstraint(
            "event_type IN ('runner_registered', 'runner_heartbeat', 'job_created', "
            "'job_claimed', 'job_started', 'lease_renewed', 'job_progress', "
            "'cancel_requested', 'cancel_acknowledged', 'job_succeeded', "
            "'job_failed', 'lease_expired', 'job_requeued', 'policy_denied', "
            "'runner_revoked')",
            name="ck_runner_job_events_type",
        ),
        UniqueConstraint(
            "job_id",
            "sequence",
            name="uq_runner_job_events_job_sequence",
        ),
        Index("ix_runner_job_events_job_created_at", "job_id", "created_at", "id"),
        Index("ix_runner_job_events_runner_created_at", "runner_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    runner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runners.id", ondelete="SET NULL")
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runner_jobs.id", ondelete="CASCADE")
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runner_job_attempts.id", ondelete="CASCADE")
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
