import uuid
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

BoundedText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
BoundedListText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class RunStatus(StrEnum):
    CREATED = "created"
    SNAPSHOTTING = "snapshotting"
    SNAPSHOT_READY = "snapshot_ready"
    PLAN_READY = "plan_ready"
    AWAITING_PLAN_APPROVAL = "awaiting_plan_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PermissionLevel(StrEnum):
    READ_ONLY = "read_only"


class SnapshotMode(StrEnum):
    GIT_HEAD = "git_head"


class DeliveryPackage(StrEnum):
    DESIGN_IMPLEMENTATION = "design_implementation"
    DESIGN_SYSTEM_MIGRATION = "design_system_migration"
    FRONTEND_QUALITY_REMEDIATION = "frontend_quality_remediation"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class DecisionKind(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permission_level: Literal["read_only"] = "read_only"
    snapshot_mode: Literal["git_head"] = "git_head"


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    status: RunStatus
    permission_level: PermissionLevel
    snapshot_mode: SnapshotMode
    version: int
    trace_id: uuid.UUID
    current_plan_version: int | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class RunListResponse(BaseModel):
    items: list[RunResponse]
    total: int


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    source_revision: str
    branch_name: str
    repository_is_dirty: bool
    dirty_path_count: int
    dirty_paths: list[dict[str, Any]]
    scanner_version: str
    scan_policy_version: str
    fingerprint: str
    tracked_file_count: int
    selected_file_count: int
    skipped_file_count: int
    total_selected_bytes: int
    tech_stack: dict[str, Any]
    package_manager: str | None
    available_scripts: list[dict[str, Any]]
    test_surfaces: list[dict[str, Any]]
    design_system_signals: list[dict[str, Any]]
    repository_instructions: list[dict[str, Any]]
    safety_findings: list[dict[str, Any]]
    manifest: list[dict[str, Any]]
    created_at: datetime


class PackageScriptValidationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["package_script"]
    workspace: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    script: Annotated[str, StringConstraints(min_length=1, max_length=120)]


class MakeTargetValidationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["make_target"]
    target: Annotated[str, StringConstraints(min_length=1, max_length=80)]


class BrowserValidationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["browser_check"]
    check: Literal["responsive", "accessibility", "visual_review"]
    viewport: Literal["desktop", "narrow", "both"]


class RepositoryStatusValidationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["repository_status_check"]
    expected: Literal["approved_scope_only"]


ValidationStep = Annotated[
    PackageScriptValidationStep
    | MakeTargetValidationStep
    | BrowserValidationStep
    | RepositoryStatusValidationStep,
    Field(discriminator="kind"),
]


class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_package: DeliveryPackage


class PlanRevisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_summary: BoundedText | None = None
    proposed_change_scope: list[BoundedListText] | None = Field(
        default=None, min_length=1, max_length=50
    )
    explicit_non_goals: list[BoundedListText] | None = Field(
        default=None, min_length=1, max_length=50
    )
    assumptions: list[BoundedListText] | None = Field(default=None, max_length=50)
    acceptance_criteria: list[BoundedListText] | None = Field(
        default=None, min_length=1, max_length=50
    )
    evidence_requirements: list[BoundedListText] | None = Field(
        default=None, min_length=1, max_length=50
    )
    stop_conditions: list[BoundedListText] | None = Field(default=None, min_length=1, max_length=50)

    @model_validator(mode="after")
    def require_a_change(self) -> "PlanRevisionCreate":
        if all(value is None for value in self.model_dump().values()):
            raise ValueError("at least one editable field is required")
        return self

    @field_validator("*")
    @classmethod
    def reject_nul(cls, value: Any) -> Any:
        values = value if isinstance(value, list) else [value]
        if any(isinstance(item, str) and "\x00" in item for item in values):
            raise ValueError("NUL characters are not allowed")
        return value


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    version: int
    status: PlanStatus
    source: Literal["deterministic_policy"]
    snapshot_fingerprint: str
    delivery_package: DeliveryPackage
    objective_summary: str
    repository_context_summary: str
    assumptions: list[str]
    proposed_change_scope: list[str]
    explicit_non_goals: list[str]
    risk_items: list[str]
    acceptance_criteria: list[str]
    evidence_requirements: list[str]
    stop_conditions: list[str]
    validation_steps: list[ValidationStep]
    required_future_permission_level: str
    execution_available: Literal[False]
    content_hash: str
    created_at: datetime


class PlanListResponse(BaseModel):
    items: list[PlanResponse]
    total: int


class PlanDecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DecisionKind
    comment: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "PlanDecisionCreate":
        if self.decision == DecisionKind.REJECT and not self.comment:
            raise ValueError("a non-blank rejection reason is required")
        if self.comment is not None and "\x00" in self.comment:
            raise ValueError("NUL characters are not allowed")
        return self


class ApprovalDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    plan_id: uuid.UUID
    decision: DecisionKind
    comment: str | None
    actor_type: Literal["local_user"]
    request_id: str
    created_at: datetime


class RunCancelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None

    @field_validator("reason")
    @classmethod
    def reject_reason_nul(cls, value: str | None) -> str | None:
        if value is not None and "\x00" in value:
            raise ValueError("NUL characters are not allowed")
        return value


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    run_id: uuid.UUID
    event_type: str
    actor_type: Literal["local_user", "system"]
    request_id: str
    metadata: dict[str, Any] = Field(validation_alias="details")
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
