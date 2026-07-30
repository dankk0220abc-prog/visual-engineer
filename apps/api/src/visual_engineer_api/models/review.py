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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from visual_engineer_api.db.base import Base


class ReviewPackage(Base):
    __tablename__ = "review_packages"
    __table_args__ = (
        UniqueConstraint(
            "suite_result_id",
            "freshness_generation",
            name="uq_review_packages_result_generation",
        ),
        UniqueConstraint("idempotency_key", name="uq_review_packages_idempotency"),
        CheckConstraint(
            "schema_version IN (1, 2)",
            name="ck_review_packages_schema_version",
        ),
        CheckConstraint(
            "package_version >= 1 AND freshness_generation >= 1",
            name="ck_review_packages_versions",
        ),
        CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$' "
            "AND evidence_manifest_digest ~ '^[0-9a-f]{64}$' "
            "AND suite_result_digest ~ '^[0-9a-f]{64}$' "
            "AND suite_policy_digest ~ '^[0-9a-f]{64}$' "
            "AND checkpoint_diff_hash ~ '^[0-9a-f]{64}$' "
            "AND blocker_summary_digest ~ '^[0-9a-f]{64}$' "
            "AND checkpoint_fingerprint ~ '^[0-9a-f]{64}$' "
            "AND idempotency_request_hash ~ '^[0-9a-f]{64}$'",
            name="ck_review_packages_digests",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence_manifest) = 'object' "
            "AND jsonb_array_length(evidence_manifest -> 'entries') = 2",
            name="ck_review_packages_manifest",
        ),
        CheckConstraint(
            "jsonb_typeof(blocker_summary) = 'object' "
            "AND critical_count >= 0 AND high_count >= 0 "
            "AND blocking_medium_count >= 0",
            name="ck_review_packages_blocker_summary",
        ),
        CheckConstraint(
            "git_authorization = false AND deployment_authorization = false",
            name="ck_review_packages_no_delivery_authority",
        ),
        Index("ix_review_packages_run_created", "run_id", "created_at"),
        Index("ix_review_packages_workspace_created", "workspace_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schema_version: Mapped[int] = mapped_column(nullable=False, default=2)
    package_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    freshness_state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_freshness_states.id", ondelete="RESTRICT"),
        nullable=False,
    )
    freshness_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
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
    suite_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_suite_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    suite_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("validation_suite_results.id", ondelete="RESTRICT"),
        nullable=False,
    )
    execution_grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("execution_grants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    suite_policy_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    suite_result_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evidence_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    blocker_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    blocker_summary_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    blocker_source: Mapped[str] = mapped_column(String(64), nullable=False)
    blocker_source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocking_medium_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    package_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    git_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployment_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReviewPackageInvalidation(Base):
    __tablename__ = "review_package_invalidations"
    __table_args__ = (
        UniqueConstraint("review_package_id", name="uq_review_invalidations_package"),
        CheckConstraint(
            "reason_code IN ('workspace_changed', 'checkpoint_superseded', "
            "'source_revision_changed', 'suite_result_superseded', "
            "'evidence_integrity_failed', 'validation_facts_changed', "
            "'policy_changed', 'grant_lineage_changed', "
            "'blocker_summary_changed', 'remediation_generation_required')",
            name="ck_review_invalidations_reason",
        ),
        CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$'",
            name="ck_review_invalidations_digest",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    package_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_value: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    __table_args__ = (
        UniqueConstraint("review_package_id", name="uq_review_decisions_package"),
        UniqueConstraint("idempotency_key", name="uq_review_decisions_idempotency"),
        CheckConstraint(
            "decision IN ('approve', 'reject')",
            name="ck_review_decisions_decision",
        ),
        CheckConstraint(
            "actor_type = 'local_user'",
            name="ck_review_decisions_actor",
        ),
        CheckConstraint(
            "decision <> 'reject' OR (reason IS NOT NULL AND char_length(trim(reason)) > 0)",
            name="ck_review_decisions_reject_reason",
        ),
        CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$' "
            "AND policy_digest ~ '^[0-9a-f]{64}$' "
            "AND idempotency_request_hash ~ '^[0-9a-f]{64}$' "
            "AND decision_digest ~ '^[0-9a-f]{64}$'",
            name="ck_review_decisions_digest",
        ),
        CheckConstraint(
            "package_version >= 1 AND expected_generation >= 1",
            name="ck_review_decisions_versions",
        ),
        CheckConstraint(
            "git_authorization = false AND deployment_authorization = false",
            name="ck_review_decisions_no_delivery_authority",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    package_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    package_version: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(2000))
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="local_user")
    request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    git_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployment_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReleaseReadinessVerdict(Base):
    __tablename__ = "release_readiness_verdicts"
    __table_args__ = (
        UniqueConstraint("review_package_id", name="uq_readiness_verdicts_package"),
        UniqueConstraint("review_decision_id", name="uq_readiness_verdicts_decision"),
        CheckConstraint(
            "verdict IN ('ready', 'not_ready')",
            name="ck_readiness_verdicts_verdict",
        ),
        CheckConstraint(
            "package_digest ~ '^[0-9a-f]{64}$' "
            "AND decision_digest ~ '^[0-9a-f]{64}$' "
            "AND evidence_manifest_digest ~ '^[0-9a-f]{64}$' "
            "AND suite_result_digest ~ '^[0-9a-f]{64}$' "
            "AND policy_digest ~ '^[0-9a-f]{64}$' "
            "AND blocker_summary_digest ~ '^[0-9a-f]{64}$' "
            "AND verdict_digest ~ '^[0-9a-f]{64}$'",
            name="ck_readiness_verdicts_digests",
        ),
        CheckConstraint(
            "package_version >= 1 AND freshness_generation >= 1 "
            "AND critical_count >= 0 AND high_count >= 0 "
            "AND blocking_medium_count >= 0",
            name="ck_readiness_verdicts_versions_blockers",
        ),
        CheckConstraint(
            "jsonb_typeof(reason_codes) = 'array' "
            "AND jsonb_array_length(reason_codes) BETWEEN 1 AND 8",
            name="ck_readiness_verdicts_reasons",
        ),
        CheckConstraint(
            "git_authorization = false AND deployment_authorization = false",
            name="ck_readiness_verdicts_no_delivery_authority",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    package_version: Mapped[int] = mapped_column(Integer, nullable=False)
    freshness_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    package_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_manifest_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    suite_result_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    blocker_summary_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False)
    blocking_medium_count: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    verdict_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    git_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deployment_authorization: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReviewFreshnessState(Base):
    __tablename__ = "review_freshness_states"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "workspace_id",
            "checkpoint_id",
            name="uq_review_freshness_scope",
        ),
        CheckConstraint(
            "generation >= 1",
            name="ck_review_freshness_generation",
        ),
        Index(
            "ix_review_freshness_workspace",
            "workspace_id",
            "checkpoint_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_change_kind: Mapped[str] = mapped_column(
        String(64), nullable=False, default="scope_initialized"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ReviewBlockerFinding(Base):
    __tablename__ = "review_blocker_findings"
    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "workspace_id",
            "checkpoint_id",
            "finding_key",
            "finding_version",
            name="uq_review_blocker_finding_version",
        ),
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_review_blocker_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'closed')",
            name="ck_review_blocker_status",
        ),
        CheckConstraint(
            "(severity IN ('critical', 'high') AND blocking = true) "
            "OR severity IN ('medium', 'low')",
            name="ck_review_blocker_critical_high",
        ),
        CheckConstraint(
            "finding_version >= 1 AND source_version >= 1",
            name="ck_review_blocker_versions",
        ),
        CheckConstraint(
            "evidence_digest ~ '^[0-9a-f]{64}$' "
            "AND policy_digest ~ '^[0-9a-f]{64}$' "
            "AND finding_digest ~ '^[0-9a-f]{64}$'",
            name="ck_review_blocker_digests",
        ),
        Index(
            "ix_review_blockers_scope",
            "plan_id",
            "workspace_id",
            "checkpoint_id",
            "finding_key",
            "finding_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_checkpoints.id", ondelete="RESTRICT"),
        nullable=False,
    )
    finding_key: Mapped[str] = mapped_column(String(128), nullable=False)
    finding_version: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default="governed-review-security-findings"
    )
    source_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
