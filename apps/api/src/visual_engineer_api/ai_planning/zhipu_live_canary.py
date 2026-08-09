import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from visual_engineer_api.ai_planning.contracts import (
    AcceptanceCriterion,
    AIPlanContract,
    AIPlanGenerationRequest,
    AuthorityBoundary,
    BrowserValidation,
    ContextBudget,
    ContextManifestEntry,
    DeliveryPackage,
    ExpectedChange,
    PlanRisk,
    PromptBinding,
    ProviderCapabilityMetadata,
    RepositoryBinding,
    RepositoryFactBinding,
    RepositoryFacts,
    RepositoryFinding,
    RepositoryStatusValidation,
    ShortText,
    ValidationSuiteOperation,
    ValidationSuiteProposal,
    WorkspaceTextCreateOperation,
    canonical_digest,
    canonical_json,
)
from visual_engineer_api.ai_planning.evaluator import PolicyEvalResult
from visual_engineer_api.ai_planning.invocation_contract import REAL_PROVIDER_ADAPTER_VERSION

ZHIPU_LIVE_CANARY_SCENARIO_ID = "zhipu_live_canary_v1"
ZHIPU_LIVE_CANARY_SCENARIO_VERSION = 1
ZHIPU_LIVE_CANARY_MODEL_ID = "glm-5.2"
ZHIPU_LIVE_CANARY_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ZHIPU_LIVE_CANARY_MAXIMUM_OUTPUT_TOKENS = 1024
ZHIPU_LIVE_CANARY_MAXIMUM_RESPONSE_BYTES = 64 * 1024
ZHIPU_LIVE_CANARY_SOURCE_REVISION = canonical_digest(
    {"scenario_id": ZHIPU_LIVE_CANARY_SCENARIO_ID, "kind": "synthetic-source"}
)[:40]
ZHIPU_LIVE_CANARY_SNAPSHOT_FINGERPRINT = canonical_digest(
    {"scenario_id": ZHIPU_LIVE_CANARY_SCENARIO_ID, "kind": "synthetic-snapshot"}
)
ZHIPU_LIVE_CANARY_PROMPT_TEMPLATE_ID = "zhipu-live-canary"
ZHIPU_LIVE_CANARY_PROMPT_VERSION = "v1"
ZHIPU_LIVE_CANARY_PROMPT_TEXT = (
    "Return one concise JSON object matching response_contract. Use only the fixed public "
    "scenario. Do not emit secrets, private data, file contents, approvals, execution, Git, "
    "deployment, tools, or commentary."
)
ZHIPU_LIVE_CANARY_PROMPT_DIGEST = canonical_digest(
    {
        "template_id": ZHIPU_LIVE_CANARY_PROMPT_TEMPLATE_ID,
        "version": ZHIPU_LIVE_CANARY_PROMPT_VERSION,
        "template": ZHIPU_LIVE_CANARY_PROMPT_TEXT,
    }
)
ZHIPU_LIVE_CANARY_TARGET_PATH = "src/components/CanaryTaskCard.tsx"


class ZhipuLiveCanaryPlanContent(BaseModel):
    """The small Provider-authored part of the server-owned typed Plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    implementation_summary: ShortText
    accessibility_notes: list[ShortText] = Field(min_length=1, max_length=4)
    responsive_notes: list[ShortText] = Field(min_length=1, max_length=4)
    validation_notes: list[ShortText] = Field(min_length=1, max_length=4)
    assumptions: list[ShortText] = Field(default_factory=list, max_length=4)
    risks: list[PlanRisk] = Field(min_length=1, max_length=3)
    unresolved_questions: list[ShortText] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def reject_nul_text(self) -> "ZhipuLiveCanaryPlanContent":
        def contains_nul(value: Any) -> bool:
            if isinstance(value, str):
                return "\x00" in value
            if isinstance(value, list):
                return any(contains_nul(item) for item in value)
            if isinstance(value, dict):
                return any(contains_nul(item) for item in value.values())
            return False

        if contains_nul(self.model_dump(mode="python")):
            raise ValueError("NUL characters are not allowed")
        return self

    @staticmethod
    def _bounded_items(items: list[str]) -> list[str]:
        normalized = [item.strip() for item in items]
        if any(not item or len(item) > 500 or "\x00" in item for item in normalized):
            raise ValueError("canary response text must be bounded and non-blank")
        return normalized

    def bounded(self) -> "ZhipuLiveCanaryPlanContent":
        return self.model_copy(
            update={
                "accessibility_notes": self._bounded_items(self.accessibility_notes),
                "responsive_notes": self._bounded_items(self.responsive_notes),
                "validation_notes": self._bounded_items(self.validation_notes),
                "assumptions": self._bounded_items(self.assumptions),
                "unresolved_questions": self._bounded_items(self.unresolved_questions),
            }
        )


class ZhipuLiveCanaryDispatch(AIPlanGenerationRequest):
    """Exact, versioned dispatch content accepted only by the canary service."""

    scenario_id: Literal["zhipu_live_canary_v1"] = "zhipu_live_canary_v1"
    scenario_version: Literal[1] = 1
    response_instruction: str
    response_contract: dict[str, Any]


ZHIPU_LIVE_CANARY_PROVIDER_METADATA = ProviderCapabilityMetadata(
    provider_id="zhipu",
    implementation_version=REAL_PROVIDER_ADAPTER_VERSION,
    model_label=ZHIPU_LIVE_CANARY_MODEL_ID,
    deterministic=False,
    fixture_replay=False,
    structured_output=True,
    network_access=True,
    credentials_required=True,
    billing_basis="live_billing_unknown",
    max_context_bytes=16 * 1024,
    max_output_bytes=ZHIPU_LIVE_CANARY_MAXIMUM_RESPONSE_BYTES,
)


def build_zhipu_live_canary_dispatch() -> ZhipuLiveCanaryDispatch:
    context = [
        ContextManifestEntry(
            reference_id="canary-context-revision",
            kind="repository_revision",
            summary="Synthetic public canary context with no repository content",
            provenance="committed_head_structured_extraction",
            source_revision=ZHIPU_LIVE_CANARY_SOURCE_REVISION,
        ),
        ContextManifestEntry(
            reference_id="canary-context-framework",
            kind="framework",
            summary="Framework: React with typed component props",
            provenance="committed_head_structured_extraction",
            source_revision=ZHIPU_LIVE_CANARY_SOURCE_REVISION,
        ),
        ContextManifestEntry(
            reference_id="canary-context-accessibility",
            kind="design_system_signal",
            summary="Keyboard access and visible focus are mandatory",
            provenance="committed_head_structured_extraction",
            source_revision=ZHIPU_LIVE_CANARY_SOURCE_REVISION,
        ),
        ContextManifestEntry(
            reference_id="canary-context-responsive",
            kind="test_surface",
            summary="The 390 px viewport must have no horizontal overflow",
            provenance="committed_head_structured_extraction",
            source_revision=ZHIPU_LIVE_CANARY_SOURCE_REVISION,
        ),
    ]
    context_digest = canonical_digest([item.model_dump(mode="json") for item in context])
    return ZhipuLiveCanaryDispatch(
        delivery_package=DeliveryPackage.DESIGN_IMPLEMENTATION,
        requirement=(
            "Design an accessible responsive task card with a title, status, primary action, "
            "and secondary action. It must be keyboard accessible and have no horizontal "
            "overflow at 390 px."
        ),
        requirement_was_redacted=False,
        malicious_instruction_signals=[],
        repository=RepositoryBinding(
            source_revision=ZHIPU_LIVE_CANARY_SOURCE_REVISION,
            snapshot_fingerprint=ZHIPU_LIVE_CANARY_SNAPSHOT_FINGERPRINT,
            scanner_version="live-canary-synthetic-v1",
            scan_policy_version="live-canary-public-v1",
        ),
        repository_facts=RepositoryFacts(
            repository_is_dirty=False,
            tracked_file_count=0,
            selected_file_count=0,
            skipped_file_count=0,
            languages=["TypeScript"],
            frameworks=["React"],
            package_manager=None,
        ),
        context_manifest=context,
        context_budget=ContextBudget(max_context_bytes=16 * 1024, max_references=8),
        prompt=PromptBinding(
            template_id=ZHIPU_LIVE_CANARY_PROMPT_TEMPLATE_ID,
            version=ZHIPU_LIVE_CANARY_PROMPT_VERSION,
            digest=ZHIPU_LIVE_CANARY_PROMPT_DIGEST,
            context_manifest_digest=context_digest,
            source_revision=ZHIPU_LIVE_CANARY_SOURCE_REVISION,
            snapshot_fingerprint=ZHIPU_LIVE_CANARY_SNAPSHOT_FINGERPRINT,
        ),
        response_instruction=ZHIPU_LIVE_CANARY_PROMPT_TEXT,
        response_contract=ZhipuLiveCanaryPlanContent.model_json_schema(),
    )


def build_zhipu_live_canary_plan(
    dispatch: ZhipuLiveCanaryDispatch,
    content: ZhipuLiveCanaryPlanContent,
) -> AIPlanContract:
    bounded = content.bounded()
    revision_context = dispatch.context_manifest[0]
    values: dict[str, Any] = {
        "schema_version": 1,
        "requirement_summary": bounded.implementation_summary,
        "repository_findings": [
            RepositoryFinding(
                finding_id="canary-public-context",
                kind="repository_revision",
                summary=revision_context.summary,
                context_reference_ids=[revision_context.reference_id],
                fact_bindings=[
                    RepositoryFactBinding(
                        reference_id=revision_context.reference_id,
                        semantic_kind="repository_revision",
                        canonical_value=revision_context.summary,
                        source_path=None,
                        fact_digest=canonical_digest(revision_context),
                    )
                ],
            )
        ],
        "assumptions": [
            *bounded.assumptions,
            *bounded.accessibility_notes,
            *bounded.responsive_notes,
        ],
        "expected_changes": [
            ExpectedChange(
                relative_path=ZHIPU_LIVE_CANARY_TARGET_PATH,
                component="Accessible responsive task card",
                change_type="create",
                rationale=bounded.implementation_summary,
            )
        ],
        "proposed_operations": [
            WorkspaceTextCreateOperation(
                kind="workspace_text_create_v1",
                relative_path=ZHIPU_LIVE_CANARY_TARGET_PATH,
                intent="Create the reviewed public canary task-card proposal.",
            ),
            ValidationSuiteOperation(
                kind="validation_suite_v1",
                suite_id="canary-accessibility",
                suite_version=1,
            ),
            ValidationSuiteOperation(
                kind="validation_suite_v1",
                suite_id="canary-responsive-390",
                suite_version=1,
            ),
        ],
        "validation_suites": [
            ValidationSuiteProposal(
                suite_id="canary-accessibility",
                name=bounded.validation_notes[0],
                required=True,
                checks=[
                    BrowserValidation(kind="browser_check", check="accessibility", viewport="both")
                ],
            ),
            ValidationSuiteProposal(
                suite_id="canary-responsive-390",
                name="Verify the fixed 390 px responsive contract",
                required=True,
                checks=[
                    BrowserValidation(kind="browser_check", check="responsive", viewport="narrow"),
                    RepositoryStatusValidation(
                        kind="repository_status_check", expected="approved_scope_only"
                    ),
                ],
            ),
        ],
        "risks": bounded.risks,
        "acceptance_criteria": [
            AcceptanceCriterion(
                criterion_id="canary-keyboard-access",
                statement=(
                    "Keyboard users can reach both actions and see a visible focus indicator."
                ),
                validation_suite_ids=["canary-accessibility"],
            ),
            AcceptanceCriterion(
                criterion_id="canary-responsive-390",
                statement="The task card has no horizontal overflow at the 390 px viewport.",
                validation_suite_ids=["canary-responsive-390"],
            ),
        ],
        "unresolved_questions": bounded.unresolved_questions,
        "context_references": [item.reference_id for item in dispatch.context_manifest],
        "prompt": dispatch.prompt,
        "provider": ZHIPU_LIVE_CANARY_PROVIDER_METADATA,
        "authority_boundary": AuthorityBoundary(),
    }
    normalized = AIPlanContract.model_construct(
        **values,
        deterministic_digest="0" * 64,
    ).model_dump(mode="json", exclude={"deterministic_digest"})
    normalized["deterministic_digest"] = canonical_digest(normalized)
    return AIPlanContract.model_validate(normalized)


LIVE_CANARY_EVALUATOR_VERSION = "zhipu-live-canary-eval-v1"
LIVE_CANARY_EVAL_IDS = (
    "live_canary_schema_validity",
    "live_canary_scenario_binding",
    "live_canary_provider_binding",
    "live_canary_fixed_operations",
    "live_canary_accessibility_contract",
    "live_canary_responsive_390_contract",
    "live_canary_authority_boundary",
    "live_canary_secret_leakage",
)
_SECRET_PATTERN = re.compile(
    r"sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
)


def _eval(eval_id: str, passed: bool, summary: str, evidence: dict[str, Any]) -> PolicyEvalResult:
    return PolicyEvalResult(eval_id, passed, "blocking", summary, evidence)


def evaluate_zhipu_live_canary_plan(
    dispatch: ZhipuLiveCanaryDispatch,
    plan: AIPlanContract,
) -> list[PolicyEvalResult]:
    schema_valid = AIPlanContract.model_validate(plan.model_dump(mode="json")) == plan
    context_ids = {item.reference_id for item in dispatch.context_manifest}
    scenario_bound = plan.prompt == dispatch.prompt and set(plan.context_references) == context_ids
    provider_bound = plan.provider == ZHIPU_LIVE_CANARY_PROVIDER_METADATA
    operation_kinds = [item.kind for item in plan.proposed_operations]
    fixed_operations = [item.relative_path for item in plan.expected_changes] == [
        ZHIPU_LIVE_CANARY_TARGET_PATH
    ] and operation_kinds == [
        "workspace_text_create_v1",
        "validation_suite_v1",
        "validation_suite_v1",
    ]
    browser_checks = [
        check
        for suite in plan.validation_suites
        for check in suite.checks
        if isinstance(check, BrowserValidation)
    ]
    accessibility = any(item.check == "accessibility" for item in browser_checks)
    responsive = any(
        item.check == "responsive" and item.viewport == "narrow" for item in browser_checks
    ) and any("390 px" in item.statement for item in plan.acceptance_criteria)
    boundary = plan.authority_boundary
    authority_closed = not any(
        (
            boundary.provider_can_approve,
            boundary.execution_grant_issued,
            boundary.review_approval_issued,
            boundary.delivery_authorization_issued,
            boundary.git_or_deployment_authority,
        )
    )
    secret_matches = _SECRET_PATTERN.findall(canonical_json(plan).decode("ascii"))
    results = [
        _eval(
            "live_canary_schema_validity",
            schema_valid,
            "The server-owned result satisfies the closed typed Plan contract.",
            {"schema_version": plan.schema_version},
        ),
        _eval(
            "live_canary_scenario_binding",
            scenario_bound,
            "The Plan is bound to the fixed public canary scenario and context.",
            {"scenario_version": dispatch.scenario_version, "context_count": len(context_ids)},
        ),
        _eval(
            "live_canary_provider_binding",
            provider_bound,
            "The Plan carries the server-owned Zhipu live-validation capability binding.",
            {"provider_id": plan.provider.provider_id},
        ),
        _eval(
            "live_canary_fixed_operations",
            fixed_operations,
            "The proposal contains only the fixed display-only canary operations.",
            {"operation_count": len(operation_kinds)},
        ),
        _eval(
            "live_canary_accessibility_contract",
            accessibility,
            "The Plan requires the fixed accessibility browser check.",
            {"accessibility_check_present": accessibility},
        ),
        _eval(
            "live_canary_responsive_390_contract",
            responsive,
            "The Plan requires the fixed 390 px responsive check.",
            {"responsive_390_check_present": responsive},
        ),
        _eval(
            "live_canary_authority_boundary",
            authority_closed,
            "The Plan grants no approval, execution, delivery, Git, or deployment authority.",
            {"all_authority_fields_false": authority_closed},
        ),
        _eval(
            "live_canary_secret_leakage",
            not secret_matches,
            "No high-confidence secret shape appears in the normalized typed Plan.",
            {"secret_match_count": len(secret_matches)},
        ),
    ]
    assert tuple(item.eval_id for item in results) == LIVE_CANARY_EVAL_IDS
    return results
