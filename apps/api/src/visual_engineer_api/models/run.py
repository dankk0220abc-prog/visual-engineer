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


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'snapshotting', 'snapshot_ready', 'plan_ready', "
            "'awaiting_plan_approval', 'approved', 'rejected', 'failed', 'cancelled')",
            name="ck_runs_status",
        ),
        CheckConstraint("permission_level = 'read_only'", name="ck_runs_permission_level"),
        CheckConstraint("snapshot_mode = 'git_head'", name="ck_runs_snapshot_mode"),
        CheckConstraint("version >= 1", name="ck_runs_version"),
        CheckConstraint(
            "current_plan_version IS NULL OR current_plan_version >= 1",
            name="ck_runs_current_plan_version",
        ),
        Index("ix_runs_task_created_at", "task_id", "created_at"),
        Index("ix_runs_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), default="created", server_default="created")
    permission_level: Mapped[str] = mapped_column(
        String(32), default="read_only", server_default="read_only"
    )
    snapshot_mode: Mapped[str] = mapped_column(
        String(32), default="git_head", server_default="git_head"
    )
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    current_plan_version: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    idempotency_request_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RepositorySnapshot(Base):
    __tablename__ = "repository_snapshots"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_repository_snapshots_run_id"),
        CheckConstraint("dirty_path_count >= 0", name="ck_snapshots_dirty_path_count"),
        CheckConstraint("tracked_file_count >= 0", name="ck_snapshots_tracked_file_count"),
        CheckConstraint("selected_file_count >= 0", name="ck_snapshots_selected_file_count"),
        CheckConstraint("skipped_file_count >= 0", name="ck_snapshots_skipped_file_count"),
        CheckConstraint("total_selected_bytes >= 0", name="ck_snapshots_total_selected_bytes"),
        Index("ix_repository_snapshots_fingerprint", "fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_is_dirty: Mapped[bool] = mapped_column(nullable=False)
    dirty_path_count: Mapped[int] = mapped_column(Integer, nullable=False)
    dirty_paths: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    scanner_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scan_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    tracked_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    skipped_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_selected_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    tech_stack: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    package_manager: Mapped[str | None] = mapped_column(String(64))
    available_scripts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    test_surfaces: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    design_system_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    repository_instructions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    safety_findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    manifest: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("run_id", "version", name="uq_plans_run_version"),
        CheckConstraint("version >= 1", name="ck_plans_version"),
        CheckConstraint(
            "status IN ('draft', 'awaiting_approval', 'approved', 'rejected', 'superseded')",
            name="ck_plans_status",
        ),
        CheckConstraint("source = 'deterministic_policy'", name="ck_plans_source"),
        CheckConstraint(
            "delivery_package IN ('design_implementation', 'design_system_migration', "
            "'frontend_quality_remediation')",
            name="ck_plans_delivery_package",
        ),
        CheckConstraint("execution_available = false", name="ck_plans_execution_unavailable"),
        Index("ix_plans_run_created_at", "run_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="deterministic_policy")
    snapshot_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    delivery_package: Mapped[str] = mapped_column(String(64), nullable=False)
    objective_summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    repository_context_summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    proposed_change_scope: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    explicit_non_goals: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    risk_items: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    acceptance_criteria: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence_requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    stop_conditions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    validation_steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    required_future_permission_level: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_available: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        UniqueConstraint("plan_id", name="uq_approval_decisions_plan_id"),
        CheckConstraint("decision IN ('approve', 'reject')", name="ck_decisions_decision"),
        CheckConstraint("actor_type = 'local_user'", name="ck_decisions_actor_type"),
        CheckConstraint(
            "decision <> 'reject' OR (comment IS NOT NULL AND char_length(trim(comment)) > 0)",
            name="ck_decisions_reject_comment",
        ),
        Index("ix_approval_decisions_run_created_at", "run_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000))
    actor_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="local_user", server_default="local_user"
    )
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("actor_type IN ('local_user', 'system')", name="ck_audit_actor_type"),
        CheckConstraint(
            "(review_package_id IS NULL AND review_sequence IS NULL) OR "
            "(review_package_id IS NOT NULL AND review_sequence >= 1)",
            name="ck_audit_review_sequence",
        ),
        Index("ix_audit_events_run_created_at", "run_id", "created_at", "id"),
        Index(
            "uq_audit_review_sequence",
            "review_package_id",
            "review_sequence",
            unique=True,
            postgresql_where=text("review_package_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    review_package_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_packages.id", ondelete="RESTRICT"),
    )
    review_sequence: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
