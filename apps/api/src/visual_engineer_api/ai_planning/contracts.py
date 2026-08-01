import hashlib
import json
import re
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

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=120,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    ),
]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Revision = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40,64}$")]


def canonical_json(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def validate_relative_path(value: str) -> str:
    if (
        not value
        or "\x00" in value
        or value.startswith("/")
        or "\\" in value
        or len(value.encode("utf-8")) > 512
    ):
        raise ValueError("a bounded relative POSIX path is required")
    parts = value.split("/")
    if len(parts) > 32 or any(
        not part
        or part in {".", ".."}
        or any(ord(character) < 32 or ord(character) == 127 for character in part)
        or any(character in part for character in "*?[")
        for part in parts
    ):
        raise ValueError("relative path contains an invalid component")
    return value


class DeliveryPackage(StrEnum):
    DESIGN_IMPLEMENTATION = "design_implementation"
    DESIGN_SYSTEM_MIGRATION = "design_system_migration"
    FRONTEND_QUALITY_REMEDIATION = "frontend_quality_remediation"


class ProviderCapabilityMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: Identifier
    implementation_version: Identifier
    model_label: Identifier
    deterministic: Literal[True]
    fixture_replay: Literal[True]
    structured_output: Literal[True]
    network_access: Literal[False]
    credentials_required: Literal[False]
    billing_basis: Literal["synthetic_not_billable"]
    max_context_bytes: int = Field(ge=1024, le=256 * 1024)
    max_output_bytes: int = Field(ge=1024, le=256 * 1024)


class ContextBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_context_bytes: int = Field(ge=1024, le=256 * 1024)
    max_references: int = Field(ge=1, le=500)


class ContextManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_id: Identifier
    kind: Literal[
        "repository_revision",
        "language",
        "framework",
        "package_manager",
        "repository_file",
        "repository_instruction",
        "test_surface",
        "design_system_signal",
        "available_validation",
    ]
    summary: ShortText
    provenance: Literal["committed_head_structured_extraction", "git_head_manifest"]
    relative_path: str | None = None
    content_sha256: Digest | None = None
    source_revision: Revision

    @field_validator("relative_path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        return validate_relative_path(value) if value is not None else None


class RepositoryBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_revision: Revision
    snapshot_fingerprint: Digest
    scanner_version: Identifier
    scan_policy_version: Identifier


class PromptBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    template_id: Identifier
    version: Identifier
    digest: Digest
    context_manifest_digest: Digest
    source_revision: Revision
    snapshot_fingerprint: Digest


class RepositoryFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_is_dirty: bool = False
    tracked_file_count: int = Field(default=0, ge=0)
    selected_file_count: int = Field(default=0, ge=0)
    skipped_file_count: int = Field(default=0, ge=0)
    languages: list[ShortText] = Field(default_factory=list, max_length=50)
    frameworks: list[ShortText] = Field(default_factory=list, max_length=50)
    package_manager: ShortText | None = None
    safety_finding_rule_counts: dict[Identifier, int] = Field(default_factory=dict)

    @field_validator("safety_finding_rule_counts")
    @classmethod
    def validate_rule_counts(cls, value: dict[str, int]) -> dict[str, int]:
        if len(value) > 100 or any(count < 0 for count in value.values()):
            raise ValueError("safety finding counts must be bounded and non-negative")
        return value


class AIPlanGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_version: Literal[1] = 1
    delivery_package: DeliveryPackage
    requirement: LongText
    requirement_was_redacted: bool
    malicious_instruction_signals: list[Identifier] = Field(max_length=20)
    repository: RepositoryBinding
    repository_facts: RepositoryFacts
    context_manifest: list[ContextManifestEntry] = Field(min_length=1, max_length=500)
    context_budget: ContextBudget
    prompt: PromptBinding
    authority_ceiling: Literal["plan_proposal_only"] = "plan_proposal_only"

    @field_validator("requirement")
    @classmethod
    def reject_nul(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("NUL characters are not allowed")
        return value

    @model_validator(mode="after")
    def unique_context_references(self) -> "AIPlanGenerationRequest":
        identifiers = [item.reference_id for item in self.context_manifest]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("context reference IDs must be unique")
        return self


RepositoryFactKind = Literal[
    "repository_revision",
    "language",
    "framework",
    "package_manager",
    "test_surface",
    "design_system_signal",
    "instruction_risk",
]


class RepositoryFactBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reference_id: Identifier
    semantic_kind: RepositoryFactKind
    canonical_value: ShortText
    source_path: str | None = None
    fact_digest: Digest

    @field_validator("source_path")
    @classmethod
    def validate_optional_path(cls, value: str | None) -> str | None:
        return validate_relative_path(value) if value is not None else None


class RepositoryFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_id: Identifier
    kind: RepositoryFactKind
    summary: ShortText
    context_reference_ids: list[Identifier] = Field(min_length=1, max_length=20)
    fact_bindings: list[RepositoryFactBinding] = Field(min_length=1, max_length=20)


class ExpectedChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str
    component: ShortText
    change_type: Literal["create", "modify"]
    rationale: ShortText

    _path = field_validator("relative_path")(validate_relative_path)


class WorkspaceTextCreateOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["workspace_text_create_v1"]
    relative_path: str
    intent: ShortText

    _path = field_validator("relative_path")(validate_relative_path)


class WorkspaceTextReplaceOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["workspace_text_replace_v1"]
    relative_path: str
    intent: ShortText
    expected_content_sha256: Digest

    _path = field_validator("relative_path")(validate_relative_path)


class ValidationSuiteOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["validation_suite_v1"]
    suite_id: Identifier
    suite_version: int = Field(ge=1, le=1000)


ProposedOperation = Annotated[
    WorkspaceTextCreateOperation | WorkspaceTextReplaceOperation | ValidationSuiteOperation,
    Field(discriminator="kind"),
]


class PackageScriptValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["package_script"]
    workspace: ShortText
    script: Identifier


class MakeTargetValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["make_target"]
    target: Identifier


class BrowserValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["browser_check"]
    check: Literal["responsive", "accessibility", "visual_review"]
    viewport: Literal["desktop", "narrow", "both"]


class RepositoryStatusValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["repository_status_check"]
    expected: Literal["approved_scope_only"]


ValidationCheck = Annotated[
    PackageScriptValidation | MakeTargetValidation | BrowserValidation | RepositoryStatusValidation,
    Field(discriminator="kind"),
]


class ValidationSuiteProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    suite_id: Identifier
    name: ShortText
    required: Literal[True]
    checks: list[ValidationCheck] = Field(min_length=1, max_length=30)


class PlanRisk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_id: Identifier
    severity: Literal["low", "medium", "high"]
    summary: ShortText
    mitigation: ShortText


class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: Identifier
    statement: ShortText
    validation_suite_ids: list[Identifier] = Field(min_length=1, max_length=20)


class AuthorityBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_can_approve: Literal[False] = False
    execution_grant_issued: Literal[False] = False
    review_approval_issued: Literal[False] = False
    delivery_authorization_issued: Literal[False] = False
    git_or_deployment_authority: Literal[False] = False


class AIPlanContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    requirement_summary: LongText
    repository_findings: list[RepositoryFinding] = Field(min_length=1, max_length=50)
    assumptions: list[ShortText] = Field(max_length=50)
    expected_changes: list[ExpectedChange] = Field(min_length=1, max_length=50)
    proposed_operations: list[ProposedOperation] = Field(min_length=1, max_length=50)
    validation_suites: list[ValidationSuiteProposal] = Field(min_length=1, max_length=20)
    risks: list[PlanRisk] = Field(min_length=1, max_length=50)
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1, max_length=50)
    unresolved_questions: list[ShortText] = Field(max_length=50)
    context_references: list[Identifier] = Field(min_length=1, max_length=500)
    prompt: PromptBinding
    provider: ProviderCapabilityMetadata
    authority_boundary: AuthorityBoundary
    deterministic_digest: Digest

    @model_validator(mode="after")
    def validate_internal_links_and_digest(self) -> "AIPlanContract":
        suite_ids = {suite.suite_id for suite in self.validation_suites}
        if any(
            not set(criterion.validation_suite_ids).issubset(suite_ids)
            for criterion in self.acceptance_criteria
        ):
            raise ValueError("acceptance criteria reference an unknown validation suite")
        operation_paths = {
            operation.relative_path
            for operation in self.proposed_operations
            if isinstance(operation, (WorkspaceTextCreateOperation, WorkspaceTextReplaceOperation))
        }
        if not {change.relative_path for change in self.expected_changes}.issubset(operation_paths):
            raise ValueError("every expected change must have a typed operation")
        values = self.model_dump(mode="json", exclude={"deterministic_digest"})
        if canonical_digest(values) != self.deterministic_digest:
            raise ValueError("deterministic digest does not match the typed contract")
        return self


_SENSITIVE_PATH = re.compile(
    r"(?i)(?:^|/)(?:\.env(?:\.|$)|[^/]*(?:credential|secret|token)[^/]*|"
    r"[^/]*\.(?:key|pem|crt|cer|p12|pfx))"
)


def is_sensitive_path(value: str) -> bool:
    return _SENSITIVE_PATH.search(value) is not None
