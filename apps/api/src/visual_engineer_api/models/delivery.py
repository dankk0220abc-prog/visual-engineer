import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class DeliveryAuthorization(Base):
    __tablename__ = "delivery_authorizations"
    __table_args__ = (
        UniqueConstraint("review_package_id", name="uq_delivery_authorizations_package"),
        UniqueConstraint("branch_ref", name="uq_delivery_authorizations_branch_ref"),
        UniqueConstraint("idempotency_key", name="uq_delivery_authorizations_idempotency"),
        CheckConstraint("authorization_version = 1", name="ck_delivery_authorizations_version"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'dispatched', "
            "'succeeded', 'failed', 'cancelled', 'stale')",
            name="ck_delivery_authorizations_status",
        ),
        CheckConstraint(
            "freshness_generation >= 1",
            name="ck_delivery_authorizations_generation",
        ),
        CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$' "
            "AND decision_digest ~ '^[0-9a-f]{64}$' "
            "AND readiness_digest ~ '^[0-9a-f]{64}$' "
            "AND checkpoint_fingerprint ~ '^[0-9a-f]{64}$' "
            "AND checkpoint_diff_hash ~ '^[0-9a-f]{64}$' "
            "AND policy_hash ~ '^[0-9a-f]{64}$' "
            "AND idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_delivery_authorizations_digests",
        ),
        CheckConstraint(
            "branch_ref ~ '^refs/heads/visual-engineer/[0-9a-f]{32}$'",
            name="ck_delivery_authorizations_branch",
        ),
        CheckConstraint(
            "commit_message ~ '^VisualEngineer: governed local delivery [0-9a-f]{8}$'",
            name="ck_delivery_authorizations_message",
        ),
        CheckConstraint(
            "local_git_commit_access = true "
            "AND remote_access = false AND push_access = false "
            "AND pull_request_access = false AND tag_access = false "
            "AND deployment_access = false "
            "AND source_repository_write_access = false",
            name="ck_delivery_authorizations_local_only",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="ck_delivery_authorizations_expiry",
        ),
        CheckConstraint(
            "(status = 'pending' AND decided_at IS NULL) OR "
            "(status <> 'pending' AND decided_at IS NOT NULL)",
            name="ck_delivery_authorizations_decision_time",
        ),
        CheckConstraint(
            "(status IN ('dispatched', 'succeeded', 'failed', 'cancelled') "
            "AND dispatched_at IS NOT NULL) OR "
            "(status NOT IN ('dispatched', 'succeeded', 'failed', 'cancelled') "
            "AND dispatched_at IS NULL)",
            name="ck_delivery_authorizations_dispatch_time",
        ),
        CheckConstraint(
            "(status IN ('rejected', 'succeeded', 'failed', 'cancelled', 'stale') "
            "AND terminal_at IS NOT NULL) OR "
            "(status NOT IN ('rejected', 'succeeded', 'failed', 'cancelled', 'stale') "
            "AND terminal_at IS NULL)",
            name="ck_delivery_authorizations_terminal_time",
        ),
        Index("ix_delivery_authorizations_status_created", "status", "created_at"),
        Index("ix_delivery_authorizations_workspace", "workspace_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    authorization_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    review_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    review_decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_decisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    readiness_verdict_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("release_readiness_verdicts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    freshness_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    package_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    readiness_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_grants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    checkpoint_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_diff_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    repository_handle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repository_handles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    branch_ref: Mapped[str] = mapped_column(String(96), nullable=False)
    commit_message: Mapped[str] = mapped_column(String(160), nullable=False)
    local_git_commit_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remote_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    push_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pull_request_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tag_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployment_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_repository_write_access: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))


class DeliveryAuthorizationDecision(Base):
    __tablename__ = "delivery_authorization_decisions"
    __table_args__ = (
        UniqueConstraint(
            "delivery_authorization_id",
            name="uq_delivery_authorization_decisions_authorization",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_delivery_authorization_decisions_idempotency",
        ),
        CheckConstraint(
            "decision IN ('approve', 'reject')",
            name="ck_delivery_authorization_decisions_decision",
        ),
        CheckConstraint(
            "actor_type = 'local_user'",
            name="ck_delivery_authorization_decisions_actor",
        ),
        CheckConstraint(
            "decision <> 'reject' OR (reason IS NOT NULL AND char_length(trim(reason)) > 0)",
            name="ck_delivery_authorization_decisions_reason",
        ),
        CheckConstraint(
            "authorization_policy_hash ~ '^[0-9a-f]{64}$' "
            "AND idempotency_request_hash ~ '^[0-9a-f]{64}$' "
            "AND decision_digest ~ '^[0-9a-f]{64}$'",
            name="ck_delivery_authorization_decisions_digests",
        ),
        CheckConstraint(
            "(decision = 'approve' AND local_git_commit_authorized = true) OR "
            "(decision = 'reject' AND local_git_commit_authorized = false)",
            name="ck_delivery_authorization_decisions_authority",
        ),
        CheckConstraint(
            "remote_access = false AND push_access = false "
            "AND pull_request_access = false AND tag_access = false "
            "AND deployment_access = false",
            name="ck_delivery_authorization_decisions_no_remote",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_authorization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_authorizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    authorization_policy_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(2000))
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="local_user")
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    local_git_commit_authorized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    remote_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    push_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pull_request_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tag_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployment_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DeliveryDispatch(Base):
    __tablename__ = "delivery_dispatches"
    __table_args__ = (
        UniqueConstraint(
            "delivery_authorization_id",
            "attempt_number",
            name="uq_delivery_dispatches_authorization_attempt",
        ),
        UniqueConstraint("runner_job_id", name="uq_delivery_dispatches_job"),
        UniqueConstraint("idempotency_key", name="uq_delivery_dispatches_idempotency"),
        CheckConstraint(
            "attempt_number BETWEEN 1 AND 3",
            name="ck_delivery_dispatches_attempt",
        ),
        CheckConstraint(
            "(attempt_number = 1 AND retry_of_dispatch_id IS NULL) OR "
            "(attempt_number > 1 AND retry_of_dispatch_id IS NOT NULL)",
            name="ck_delivery_dispatches_retry_shape",
        ),
        CheckConstraint(
            "status IN ('dispatched', 'succeeded', 'failed', 'cancelled')",
            name="ck_delivery_dispatches_status",
        ),
        CheckConstraint(
            "manifest_digest ~ '^[0-9a-f]{64}$' "
            "AND confirmation_digest = manifest_digest "
            "AND idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_delivery_dispatches_digests",
        ),
        CheckConstraint(
            "manifest ->> 'manifest_version' = '1' "
            "AND manifest ->> 'manifest_digest' = manifest_digest "
            "AND manifest ->> 'local_git_commit_access' = 'true' "
            "AND manifest ->> 'remote_access' = 'false' "
            "AND manifest ->> 'push_access' = 'false' "
            "AND manifest ->> 'pull_request_access' = 'false' "
            "AND manifest ->> 'tag_access' = 'false' "
            "AND manifest ->> 'deployment_access' = 'false' "
            "AND manifest ->> 'source_repository_write_access' = 'false'",
            name="ck_delivery_dispatches_manifest_local_only",
        ),
        CheckConstraint(
            "(status = 'dispatched' AND terminal_at IS NULL) OR "
            "(status IN ('succeeded', 'failed', 'cancelled') AND terminal_at IS NOT NULL)",
            name="ck_delivery_dispatches_terminal_time",
        ),
        Index(
            "uq_delivery_dispatches_active_authorization",
            "delivery_authorization_id",
            unique=True,
            postgresql_where=text("status = 'dispatched'"),
        ),
        Index(
            "ix_delivery_dispatches_authorization_created",
            "delivery_authorization_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_authorization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_authorizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_of_dispatch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_dispatches.id", ondelete="RESTRICT"),
    )
    runner_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runner_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    manifest: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmation_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="dispatched")
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    terminal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LocalDelivery(Base):
    __tablename__ = "local_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "delivery_authorization_id",
            name="uq_local_deliveries_authorization",
        ),
        UniqueConstraint("runner_job_id", name="uq_local_deliveries_job"),
        UniqueConstraint("branch_ref", name="uq_local_deliveries_branch_ref"),
        CheckConstraint(
            "commit_oid ~ '^[0-9a-f]{40,64}$' "
            "AND tree_oid ~ '^[0-9a-f]{40,64}$' "
            "AND parent_oid ~ '^[0-9a-f]{40,64}$' "
            "AND checkpoint_fingerprint ~ '^[0-9a-f]{64}$' "
            "AND checkpoint_diff_hash ~ '^[0-9a-f]{64}$' "
            "AND result_digest ~ '^[0-9a-f]{64}$'",
            name="ck_local_deliveries_digests",
        ),
        CheckConstraint(
            "branch_ref ~ '^refs/heads/visual-engineer/[0-9a-f]{32}$'",
            name="ck_local_deliveries_branch",
        ),
        CheckConstraint(
            "remote_access = false AND pushed = false "
            "AND pull_request_created = false AND tagged = false "
            "AND deployed = false",
            name="ck_local_deliveries_no_remote",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_authorization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("delivery_authorizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    runner_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runner_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    runner_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runner_job_attempts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    side_effect_permit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("side_effect_permits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    checkpoint_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_diff_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    branch_ref: Mapped[str] = mapped_column(String(96), nullable=False)
    commit_oid: Mapped[str] = mapped_column(String(64), nullable=False)
    tree_oid: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_oid: Mapped[str] = mapped_column(String(64), nullable=False)
    result_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    remote_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pushed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pull_request_created: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
