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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from visual_engineer_api.db.base import Base


class RepositoryHandle(Base):
    __tablename__ = "repository_handles"
    __table_args__ = (
        UniqueConstraint("runner_id", "opaque_handle", name="uq_repository_handles_runner_opaque"),
        CheckConstraint("vcs_kind = 'git'", name="ck_repository_handles_vcs"),
        CheckConstraint(
            "status IN ('available', 'unavailable', 'revoked')",
            name="ck_repository_handles_status",
        ),
        CheckConstraint("dirty_path_count >= 0", name="ck_repository_handles_dirty_count"),
        CheckConstraint("source_status = 'unknown'", name="ck_repository_handles_source_status"),
        CheckConstraint("metadata_version = 1", name="ck_repository_handles_metadata_version"),
        Index("ix_repository_handles_runner_status", "runner_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    runner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runners.id", ondelete="RESTRICT"), nullable=False
    )
    opaque_handle: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    vcs_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="git")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="available")
    capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    current_revision: Mapped[str | None] = mapped_column(String(64))
    current_branch: Mapped[str | None] = mapped_column(String(255))
    source_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    source_is_dirty: Mapped[bool] = mapped_column(nullable=False, default=False)
    dirty_path_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExecutionGrant(Base):
    __tablename__ = "execution_grants"
    __table_args__ = (
        CheckConstraint("grant_version = 1", name="ck_execution_grants_version"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'revoke_requested', "
            "'revoked', 'expired')",
            name="ck_execution_grants_status",
        ),
        CheckConstraint("max_files_changed BETWEEN 1 AND 100", name="ck_grants_file_budget"),
        CheckConstraint(
            "max_total_write_bytes BETWEEN 1 AND 1048576",
            name="ck_grants_total_write_budget",
        ),
        CheckConstraint(
            "max_single_file_bytes BETWEEN 1 AND 32768 "
            "AND max_single_file_bytes <= max_total_write_bytes",
            name="ck_grants_single_file_budget",
        ),
        CheckConstraint(
            "max_diff_bytes BETWEEN 1 AND 32768",
            name="ck_grants_diff_budget",
        ),
        CheckConstraint(
            "workspace_ttl_seconds BETWEEN 60 AND 86400",
            name="ck_grants_workspace_ttl",
        ),
        CheckConstraint("network_policy = 'none'", name="ck_grants_network_none"),
        CheckConstraint("shell_access = false", name="ck_grants_shell_false"),
        CheckConstraint("git_delivery_access = false", name="ck_grants_delivery_false"),
        CheckConstraint(
            "source_repository_write_access = false",
            name="ck_grants_source_write_false",
        ),
        CheckConstraint(
            "("
            "validation_checkpoint_id IS NOT NULL "
            "AND validation_workspace_id IS NOT NULL "
            "AND allowed_operations = '[\"validate\"]'::jsonb "
            "AND jsonb_array_length(allowed_validation_profiles) BETWEEN 1 AND 4 "
            "AND max_validation_runs BETWEEN 1 AND 10 "
            "AND validation_timeout_seconds BETWEEN 1 AND 120 "
            "AND validation_cpu_seconds BETWEEN 1 AND 120 "
            "AND validation_memory_bytes BETWEEN 1048576 AND 1073741824 "
            "AND validation_pid_limit BETWEEN 1 AND 64 "
            "AND validation_fd_limit BETWEEN 1 AND 256 "
            "AND validation_output_bytes BETWEEN 256 AND 65536 "
            "AND validation_artifact_bytes BETWEEN 0 AND 1048576 "
            "AND validation_artifact_count BETWEEN 0 AND 20"
            ") OR ("
            "validation_checkpoint_id IS NULL "
            "AND validation_workspace_id IS NULL "
            "AND allowed_validation_profiles = '[]'::jsonb "
            "AND max_validation_runs = 0 "
            "AND validation_timeout_seconds = 0 "
            "AND validation_cpu_seconds = 0 "
            "AND validation_memory_bytes = 0 "
            "AND validation_pid_limit = 0 "
            "AND validation_fd_limit = 0 "
            "AND validation_output_bytes = 0 "
            "AND validation_artifact_bytes = 0 "
            "AND validation_artifact_count = 0"
            ")",
            name="ck_grants_validation_scope",
        ),
        CheckConstraint(
            "policy_hash ~ '^[0-9a-f]{64}$'",
            name="ck_grants_policy_hash",
        ),
        CheckConstraint(
            "("
            "jsonb_array_length(allowed_validation_suites) = 0 "
            "AND validation_suite_definition_digest IS NULL "
            "AND validation_suite_root_run_id IS NULL "
            "AND validation_suite_retry_of_run_id IS NULL "
            "AND validation_suite_attempt_number = 0 "
            "AND validation_suite_allowed_run_count = 0"
            ") OR ("
            "jsonb_array_length(allowed_validation_suites) = 1 "
            "AND validation_suite_definition_digest ~ '^[0-9a-f]{64}$' "
            "AND validation_suite_attempt_number BETWEEN 1 AND 5 "
            "AND validation_suite_allowed_run_count = 1 "
            "AND max_validation_runs = 2 "
            "AND ("
            "(validation_suite_attempt_number = 1 "
            "AND validation_suite_root_run_id IS NULL "
            "AND validation_suite_retry_of_run_id IS NULL) OR "
            "(validation_suite_attempt_number > 1 "
            "AND validation_suite_root_run_id IS NOT NULL "
            "AND validation_suite_retry_of_run_id IS NOT NULL)"
            ")"
            ")",
            name="ck_grants_validation_suite_lineage",
        ),
        CheckConstraint(
            "snapshot_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_grants_snapshot_fingerprint",
        ),
        CheckConstraint("expires_at > requested_at", name="ck_grants_expiry"),
        CheckConstraint(
            "(status = 'pending' AND decided_at IS NULL) OR "
            "(status <> 'pending' AND decided_at IS NOT NULL)",
            name="ck_grants_decided_at",
        ),
        CheckConstraint(
            "(status = 'revoke_requested' AND revocation_requested_at IS NOT NULL "
            "AND revoked_at IS NULL) OR "
            "(status = 'revoked' AND revocation_requested_at IS NOT NULL "
            "AND revoked_at IS NOT NULL) OR "
            "(status NOT IN ('revoke_requested', 'revoked') "
            "AND revocation_requested_at IS NULL AND revoked_at IS NULL)",
            name="ck_grants_revocation_lifecycle",
        ),
        Index("ix_execution_grants_status_expires", "status", "expires_at"),
        Index("ix_execution_grants_plan_created", "plan_id", "created_at"),
        Index(
            "uq_active_root_suite_grant",
            "plan_id",
            "validation_checkpoint_id",
            "validation_suite_definition_digest",
            unique=True,
            postgresql_where=text(
                "validation_suite_attempt_number = 1 AND status IN ('pending', 'approved')"
            ),
        ),
        Index(
            "uq_active_retry_suite_grant",
            "validation_suite_retry_of_run_id",
            unique=True,
            postgresql_where=text(
                "validation_suite_attempt_number > 1 AND status IN ('pending', 'approved')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grant_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="RESTRICT")
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT")
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    repository_handle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_handles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed_operations: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    allowed_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    denied_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    max_files_changed: Mapped[int] = mapped_column(Integer, nullable=False)
    max_total_write_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_single_file_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_diff_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    workspace_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    network_policy: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    shell_access: Mapped[bool] = mapped_column(nullable=False, default=False)
    git_delivery_access: Mapped[bool] = mapped_column(nullable=False, default=False)
    source_repository_write_access: Mapped[bool] = mapped_column(nullable=False, default=False)
    validation_workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT")
    )
    validation_checkpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspace_checkpoints.id", ondelete="RESTRICT")
    )
    allowed_validation_profiles: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    allowed_validation_suites: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    validation_suite_definition_digest: Mapped[str | None] = mapped_column(String(64))
    validation_suite_root_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "validation_suite_runs.id",
            name="fk_grants_validation_suite_root_run",
            ondelete="RESTRICT",
            use_alter=True,
        ),
    )
    validation_suite_retry_of_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "validation_suite_runs.id",
            name="fk_grants_validation_suite_retry_of_run",
            ondelete="RESTRICT",
            use_alter=True,
        ),
    )
    validation_suite_attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_suite_allowed_run_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    max_validation_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_cpu_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_memory_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_pid_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_fd_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_output_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_artifact_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_artifact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExecutionGrantDecision(Base):
    __tablename__ = "execution_grant_decisions"
    __table_args__ = (
        UniqueConstraint("grant_id", name="uq_execution_grant_decisions_grant"),
        CheckConstraint(
            "decision IN ('approve', 'reject')",
            name="ck_execution_grant_decisions_decision",
        ),
        CheckConstraint(
            "actor_type = 'local_user'",
            name="ck_execution_grant_decisions_actor",
        ),
        CheckConstraint(
            "decision <> 'reject' OR char_length(trim(reason)) > 0",
            name="ck_execution_grant_decisions_reject_reason",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_grants.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(2000))
    actor_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="local_user", server_default="local_user"
    )
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint(
            "state IN ('requested', 'preparing', 'ready', 'active', 'sealing', "
            "'sealed', 'rollback_requested', 'rolled_back', 'discard_requested', "
            "'discarded', 'failed', 'expired', 'recovery_required', 'quarantined')",
            name="ck_workspaces_state",
        ),
        CheckConstraint("changed_file_count >= 0", name="ck_workspaces_changed_count"),
        CheckConstraint("total_written_bytes >= 0", name="ck_workspaces_written_bytes"),
        CheckConstraint(
            "workspace_fingerprint IS NULL OR workspace_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_workspaces_fingerprint",
        ),
        CheckConstraint(
            "initial_tree_hash IS NULL OR initial_tree_hash ~ '^[0-9a-f]{64}$'",
            name="ck_workspaces_initial_tree_hash",
        ),
        CheckConstraint(
            "current_tree_hash IS NULL OR current_tree_hash ~ '^[0-9a-f]{64}$'",
            name="ck_workspaces_current_tree_hash",
        ),
        Index("ix_workspaces_grant_created", "grant_id", "created_at"),
        Index("ix_workspaces_runner_state", "runner_id", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_grants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    runner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runners.id", ondelete="RESTRICT"), nullable=False
    )
    repository_handle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_handles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="requested")
    workspace_fingerprint: Mapped[str | None] = mapped_column(String(64))
    initial_tree_hash: Mapped[str | None] = mapped_column(String(64))
    current_tree_hash: Mapped[str | None] = mapped_column(String(64))
    changed_file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_written_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    active_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runner_job_attempts.id", ondelete="SET NULL"),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))


class WorkspaceEvent(Base):
    __tablename__ = "workspace_events"
    __table_args__ = (
        UniqueConstraint("workspace_id", "sequence", name="uq_workspace_events_sequence"),
        CheckConstraint("sequence >= 1", name="ck_workspace_events_sequence"),
        CheckConstraint(
            "event_type IN ('grant_approved', 'workspace_requested', 'mirror_prepared', "
            "'workspace_prepared', 'tool_started', 'tool_succeeded', 'tool_denied', "
            "'checkpoint_created', 'diff_generated', 'rollback_requested', "
            "'rollback_completed', 'workspace_sealed', 'discard_requested', "
            "'workspace_discarded', 'workspace_expired', 'workspace_failed', "
            "'permit_acquired', 'permit_completed', 'permit_denied', "
            "'grant_revoke_requested', 'grant_revoke_effective', "
            "'recovery_required', 'workspace_quarantined')",
            name="ck_workspace_events_type",
        ),
        Index("ix_workspace_events_workspace_created", "workspace_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    runner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runners.id", ondelete="RESTRICT"), nullable=False
    )
    side_effect_permit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("side_effect_permits.id", ondelete="SET NULL"),
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorkspaceCheckpoint(Base):
    __tablename__ = "workspace_checkpoints"
    __table_args__ = (
        UniqueConstraint("workspace_id", "sequence", name="uq_workspace_checkpoints_sequence"),
        CheckConstraint("sequence >= 1", name="ck_workspace_checkpoints_sequence"),
        CheckConstraint(
            "tree_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_workspace_checkpoints_tree_fingerprint",
        ),
        CheckConstraint(
            "diff_hash ~ '^[0-9a-f]{64}$'",
            name="ck_workspace_checkpoints_diff_hash",
        ),
        CheckConstraint(
            "changed_file_count BETWEEN 0 AND 100",
            name="ck_workspace_checkpoints_changed_count",
        ),
        CheckConstraint(
            "total_diff_bytes BETWEEN 0 AND 32768",
            name="ck_workspace_checkpoints_diff_bytes",
        ),
        Index(
            "ix_workspace_checkpoints_workspace_created",
            "workspace_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    side_effect_permit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("side_effect_permits.id", ondelete="SET NULL"),
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    tree_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    diff_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    changed_file_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_diff_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    diff_artifact: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SideEffectPermit(Base):
    __tablename__ = "side_effect_permits"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "attempt_id",
            "job_digest",
            name="uq_side_effect_permits_attempt_job_digest",
        ),
        UniqueConstraint(
            "workspace_id",
            "sequence",
            name="uq_side_effect_permits_workspace_sequence",
        ),
        UniqueConstraint("operation_digest", name="uq_side_effect_permits_operation_digest"),
        CheckConstraint("sequence >= 1", name="ck_side_effect_permits_sequence"),
        CheckConstraint(
            "operation IN ('prepare', 'write_text', 'rollback', 'discard', 'validate')",
            name="ck_side_effect_permits_operation",
        ),
        CheckConstraint(
            "state IN ('consumed', 'completed', 'failed', 'cancelled', 'expired')",
            name="ck_side_effect_permits_state",
        ),
        CheckConstraint(
            "(operation = 'write_text' AND relative_path IS NOT NULL) OR "
            "(operation <> 'write_text' AND relative_path IS NULL)",
            name="ck_side_effect_permits_path_scope",
        ),
        CheckConstraint(
            "expected_current IN ('absent', 'workspace_absent') "
            "OR expected_current ~ '^[0-9a-f]{64}$'",
            name="ck_side_effect_permits_expected_current",
        ),
        CheckConstraint(
            "proposed_digest ~ '^[0-9a-f]{64}$' "
            "AND job_digest ~ '^[0-9a-f]{64}$' "
            "AND operation_digest ~ '^[0-9a-f]{64}$' "
            "AND policy_hash ~ '^[0-9a-f]{64}$' "
            "AND char_length(source_revision) IN (40, 64) "
            "AND source_revision ~ '^[0-9a-f]+$'",
            name="ck_side_effect_permits_digests",
        ),
        CheckConstraint(
            "relative_path IS NULL OR "
            "(relative_path !~ '(^/|(^|/)\\.\\.(/|$)|\\\\)' "
            "AND octet_length(relative_path) BETWEEN 1 AND 512)",
            name="ck_side_effect_permits_relative_path",
        ),
        CheckConstraint(
            "issued_at <= consumed_at AND consumed_at < expires_at",
            name="ck_side_effect_permits_window",
        ),
        CheckConstraint(
            "(state = 'consumed' AND terminal_at IS NULL) OR "
            "(state <> 'consumed' AND terminal_at IS NOT NULL)",
            name="ck_side_effect_permits_terminal",
        ),
        Index("ix_side_effect_permits_grant_state", "grant_id", "state"),
        Index("ix_side_effect_permits_state_expires", "state", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    runner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runners.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runner_jobs.id", ondelete="CASCADE"), nullable=False
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runner_job_attempts.id", ondelete="CASCADE"),
        nullable=False,
    )
    lease_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_grants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    repository_handle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_handles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    relative_path: Mapped[str | None] = mapped_column(String(512))
    expected_current: Mapped[str] = mapped_column(String(64), nullable=False)
    proposed_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    job_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    operation_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="consumed")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
