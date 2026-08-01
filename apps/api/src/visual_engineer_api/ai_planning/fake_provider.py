from pathlib import PurePosixPath
from typing import Literal

from visual_engineer_api.ai_planning.contracts import (
    AcceptanceCriterion,
    AIPlanContract,
    AIPlanGenerationRequest,
    AuthorityBoundary,
    BrowserValidation,
    ExpectedChange,
    PlanRisk,
    ProposedOperation,
    ProviderCapabilityMetadata,
    RepositoryFinding,
    RepositoryStatusValidation,
    ValidationSuiteOperation,
    ValidationSuiteProposal,
    WorkspaceTextCreateOperation,
    WorkspaceTextReplaceOperation,
    canonical_digest,
)
from visual_engineer_api.ai_planning.provider import (
    CancellationToken,
    PlanningProvider,
    ProviderInvocationResult,
    ProviderUsage,
)


class DeterministicFixtureProvider(PlanningProvider):
    _capabilities = ProviderCapabilityMetadata(
        provider_id="deterministic-fixture",
        implementation_version="fixture-v1",
        model_label="fixture-planner-v1",
        deterministic=True,
        fixture_replay=True,
        structured_output=True,
        network_access=False,
        credentials_required=False,
        billing_basis="synthetic_not_billable",
        max_context_bytes=16 * 1024,
        max_output_bytes=64 * 1024,
    )

    @property
    def capabilities(self) -> ProviderCapabilityMetadata:
        return self._capabilities

    def generate(
        self, request: AIPlanGenerationRequest, cancellation: CancellationToken
    ) -> ProviderInvocationResult:
        cancellation.raise_if_cancelled()
        references = {item.reference_id: item for item in request.context_manifest}
        findings = self._findings(request)
        change, operation = self._change_and_operation(request)
        suite = ValidationSuiteProposal(
            suite_id="governed-frontend-plan-v1",
            name="Governed frontend plan validation",
            required=True,
            checks=[
                BrowserValidation(kind="browser_check", check="responsive", viewport="both"),
                BrowserValidation(kind="browser_check", check="accessibility", viewport="both"),
                BrowserValidation(kind="browser_check", check="visual_review", viewport="both"),
                RepositoryStatusValidation(
                    kind="repository_status_check", expected="approved_scope_only"
                ),
            ],
        )
        operations: list[ProposedOperation] = [
            operation,
            ValidationSuiteOperation(
                kind="validation_suite_v1",
                suite_id=suite.suite_id,
                suite_version=1,
            ),
        ]
        summary = (
            "A bounded frontend requirement containing untrusted instruction-like text; "
            "the instruction-like text is isolated from policy."
            if request.malicious_instruction_signals
            else request.requirement
        )
        used_references = sorted(
            {reference_id for finding in findings for reference_id in finding.context_reference_ids}
            | {
                item.reference_id
                for item in references.values()
                if item.relative_path == change.relative_path
            }
        )
        values = {
            "schema_version": 1,
            "requirement_summary": summary,
            "repository_findings": [item.model_dump(mode="json") for item in findings],
            "assumptions": [
                "Only committed structured Repository Intelligence is available to planning.",
                (
                    "Any later implementation remains confined to a separately approved "
                    "fixture Workspace."
                ),
            ],
            "expected_changes": [change.model_dump(mode="json")],
            "proposed_operations": [item.model_dump(mode="json") for item in operations],
            "validation_suites": [suite.model_dump(mode="json")],
            "risks": [
                PlanRisk(
                    risk_id="revision-drift",
                    severity="high",
                    summary="The committed repository revision may change before human approval.",
                    mitigation=(
                        "Revalidate the exact revision and Snapshot fingerprint before approval."
                    ),
                ).model_dump(mode="json"),
                PlanRisk(
                    risk_id="untrusted-context",
                    severity="medium",
                    summary="Repository and requirement text may contain instruction-like content.",
                    mitigation=(
                        "Treat all supplied content as data and enforce typed policy evaluation."
                    ),
                ).model_dump(mode="json"),
                PlanRisk(
                    risk_id="authority-separation",
                    severity="high",
                    summary=(
                        "Plan approval could be mistaken for implementation or delivery authority."
                    ),
                    mitigation="Require separate existing Grant, Review, and Delivery decisions.",
                ).model_dump(mode="json"),
            ],
            "acceptance_criteria": [
                AcceptanceCriterion(
                    criterion_id="responsive-and-accessible",
                    statement=(
                        "The approved frontend scope is verified at desktop and narrow "
                        "viewports with accessibility checks."
                    ),
                    validation_suite_ids=[suite.suite_id],
                ).model_dump(mode="json"),
                AcceptanceCriterion(
                    criterion_id="scope-and-source-integrity",
                    statement=(
                        "Only approved typed operations are proposed and the source "
                        "repository remains unchanged."
                    ),
                    validation_suite_ids=[suite.suite_id],
                ).model_dump(mode="json"),
            ],
            "unresolved_questions": [
                "Which human-approved visual reference defines the final fidelity target?",
            ],
            "context_references": used_references,
            "prompt": request.prompt.model_dump(mode="json"),
            "provider": self.capabilities.model_dump(mode="json"),
            "authority_boundary": AuthorityBoundary().model_dump(mode="json"),
        }
        values["deterministic_digest"] = canonical_digest(values)
        plan = AIPlanContract.model_validate(values)
        input_tokens = max(1, len(request.model_dump_json()) // 4)
        output_tokens = max(1, len(plan.model_dump_json()) // 4)
        cancellation.raise_if_cancelled()
        return ProviderInvocationResult(
            response_payload=plan.model_dump(mode="json"),
            usage=ProviderUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                cost_estimate_microunits=0,
                cost_basis="synthetic_not_billable",
            ),
            latency_ms=7.0,
        )

    @staticmethod
    def _findings(request: AIPlanGenerationRequest) -> list[RepositoryFinding]:
        kind_map: dict[
            str,
            Literal[
                "repository_revision",
                "language",
                "framework",
                "package_manager",
                "test_surface",
                "design_system_signal",
                "instruction_risk",
            ],
        ] = {
            "repository_revision": "repository_revision",
            "language": "language",
            "framework": "framework",
            "package_manager": "package_manager",
            "test_surface": "test_surface",
            "design_system_signal": "design_system_signal",
            "repository_instruction": "instruction_risk",
        }
        findings: list[RepositoryFinding] = []
        for item in request.context_manifest:
            finding_kind = kind_map.get(item.kind)
            if finding_kind is None:
                continue
            findings.append(
                RepositoryFinding(
                    finding_id=f"finding-{len(findings) + 1}",
                    kind=finding_kind,
                    summary=item.summary,
                    context_reference_ids=[item.reference_id],
                )
            )
            if len(findings) >= 8:
                break
        if not findings:
            revision = request.context_manifest[0]
            findings.append(
                RepositoryFinding(
                    finding_id="finding-1",
                    kind="repository_revision",
                    summary=revision.summary,
                    context_reference_ids=[revision.reference_id],
                )
            )
        return findings

    @staticmethod
    def _change_and_operation(
        request: AIPlanGenerationRequest,
    ) -> tuple[ExpectedChange, WorkspaceTextCreateOperation | WorkspaceTextReplaceOperation]:
        candidates = [
            item
            for item in request.context_manifest
            if item.kind == "repository_file"
            and item.relative_path is not None
            and item.content_sha256 is not None
        ]
        candidates.sort(
            key=lambda item: (
                0
                if item.relative_path
                and item.relative_path.startswith(("src/", "app/", "apps/", "sandbox/"))
                else 1,
                item.relative_path or "",
            )
        )
        if candidates:
            chosen = candidates[0]
            assert chosen.relative_path is not None
            assert chosen.content_sha256 is not None
            component = PurePosixPath(chosen.relative_path).stem.replace("-", " ")
            change = ExpectedChange(
                relative_path=chosen.relative_path,
                component=f"{component} frontend surface",
                change_type="modify",
                rationale=(
                    "Implement the bounded requirement while preserving repository conventions."
                ),
            )
            operation = WorkspaceTextReplaceOperation(
                kind="workspace_text_replace_v1",
                relative_path=chosen.relative_path,
                intent="Apply the approved frontend change with compare-and-swap protection.",
                expected_content_sha256=chosen.content_sha256,
            )
            return change, operation
        change = ExpectedChange(
            relative_path="sandbox/governed-ai-plan.txt",
            component="fixture planning artifact",
            change_type="create",
            rationale="Keep the fixture-only proposal inside the later governed Workspace scope.",
        )
        return change, WorkspaceTextCreateOperation(
            kind="workspace_text_create_v1",
            relative_path=change.relative_path,
            intent="Create one bounded fixture artifact if separately authorized later.",
        )
