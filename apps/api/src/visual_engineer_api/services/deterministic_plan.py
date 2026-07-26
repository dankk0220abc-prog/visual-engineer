import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from visual_engineer_api.models.run import Plan, RepositorySnapshot
from visual_engineer_api.models.task import Task
from visual_engineer_api.schemas.run import DeliveryPackage, PlanRevisionCreate

PLAN_POLICY_VERSION = "phase2-plan-v1"


class PlanPolicyViolationError(Exception):
    def __init__(self, violations: list[dict[str, str]]) -> None:
        super().__init__("Plan violates the Phase 2 policy boundary")
        self.violations = violations


@dataclass(frozen=True)
class GeneratedPlan:
    objective_summary: str
    repository_context_summary: str
    assumptions: list[str]
    proposed_change_scope: list[str]
    explicit_non_goals: list[str]
    risk_items: list[str]
    acceptance_criteria: list[str]
    evidence_requirements: list[str]
    stop_conditions: list[str]
    validation_steps: list[dict[str, Any]]
    required_future_permission_level: str

    def values(self) -> dict[str, Any]:
        return {
            "objective_summary": self.objective_summary,
            "repository_context_summary": self.repository_context_summary,
            "assumptions": self.assumptions,
            "proposed_change_scope": self.proposed_change_scope,
            "explicit_non_goals": self.explicit_non_goals,
            "risk_items": self.risk_items,
            "acceptance_criteria": self.acceptance_criteria,
            "evidence_requirements": self.evidence_requirements,
            "stop_conditions": self.stop_conditions,
            "validation_steps": self.validation_steps,
            "required_future_permission_level": self.required_future_permission_level,
        }


_POLICY_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "arbitrary_shell",
        re.compile(r"(`|\$\(|&&|\|\||;\s*(?:sudo|git|curl|wget|rm)\b)", re.I),
        "Arbitrary shell syntax is not allowed in a plan",
    ),
    (
        "secret_access",
        re.compile(
            r"\b(read|print|copy|upload|expose)\b.{0,80}\b(\.env|secret|credential|token)\b", re.I
        ),
        "Plans cannot request secret or credential access",
    ),
    (
        "approval_bypass",
        re.compile(r"\b(auto[- ]?approve|bypass approval|without approval)\b", re.I),
        "Plans cannot bypass or automate human approval",
    ),
    (
        "permission_elevation",
        re.compile(r"\b(elevate|raise|increase|change)\b.{0,60}\b(permission|level [1-4])\b", re.I),
        "Plan revisions cannot elevate permission",
    ),
    (
        "automatic_merge",
        re.compile(r"\b(auto(?:matic(?:ally)?)?[- ]?merge|merge\s+(?:to|into)?\s*main)\b", re.I),
        "Automatic or main-branch merge is prohibited",
    ),
    (
        "production_deploy",
        re.compile(
            r"\b(deploy|release|publish)\b.{0,60}\bproduction\b|\bproduction\b.{0,60}\b(deploy|release|publish)\b",
            re.I,
        ),
        "Production deployment is prohibited",
    ),
    (
        "high_risk_domain",
        re.compile(
            r"\b(modify|replace|migrate|rewrite)\b.{0,80}\b(authentication|authorization|payment|billing)\b",
            re.I,
        ),
        "Authentication and payment changes are outside the Phase 2 boundary",
    ),
    (
        "high_risk_database_migration",
        re.compile(
            r"\b(production|high[- ]risk|customer)\b.{0,60}\bdatabase migration\b"
            r"|\bdatabase migration\b.{0,60}\b(production|high[- ]risk|customer)\b",
            re.I,
        ),
        "High-risk database migrations are outside the Phase 2 boundary",
    ),
)


def generate_deterministic_plan(
    task: Task, snapshot: RepositorySnapshot, delivery_package: DeliveryPackage
) -> GeneratedPlan:
    frameworks = [
        str(value) for value in snapshot.tech_stack.get("frameworks", []) if isinstance(value, str)
    ]
    languages = [
        str(value) for value in snapshot.tech_stack.get("languages", []) if isinstance(value, str)
    ]
    framework_summary = ", ".join(frameworks) if frameworks else "no framework confirmed"
    language_summary = ", ".join(languages) if languages else "no language confirmed"
    dirty_summary = (
        f"Working tree reports {snapshot.dirty_path_count} changed or untracked paths; "
        "their contents were not used."
        if snapshot.repository_is_dirty
        else "Working tree was clean when status metadata was captured."
    )
    repository_context_summary = (
        f"Committed HEAD {snapshot.source_revision[:12]} on {_bounded(snapshot.branch_name, 120)}; "
        f"detected {framework_summary}; languages {language_summary}; "
        f"{snapshot.tracked_file_count} tracked files and "
        f"{snapshot.selected_file_count} policy-selected metadata files. {dirty_summary}"
    )

    package_scope = {
        DeliveryPackage.DESIGN_IMPLEMENTATION: [
            (
                "Implement only the explicitly approved page and component surfaces "
                "identified during future scoped delivery."
            ),
            (
                "Reuse confirmed design-system and routing conventions instead of "
                "introducing a parallel system."
            ),
            "Preserve responsive behavior and semantic accessibility across the approved surface.",
        ],
        DeliveryPackage.DESIGN_SYSTEM_MIGRATION: [
            (
                "Migrate only the approved token, theme, and component consumers identified "
                "in the final human-reviewed scope."
            ),
            (
                "Preserve public component behavior unless an acceptance criterion "
                "explicitly authorizes a change."
            ),
            (
                "Document compatibility and bounded rollout evidence for every affected "
                "design-system surface."
            ),
        ],
        DeliveryPackage.FRONTEND_QUALITY_REMEDIATION: [
            (
                "Remediate only the approved responsive, accessibility, visual, and "
                "frontend-quality findings."
            ),
            (
                "Prefer existing components, tokens, and test conventions confirmed by the "
                "committed repository snapshot."
            ),
            (
                "Keep backend, infrastructure, and unrelated product behavior outside the "
                "future change set."
            ),
        ],
    }[delivery_package]

    assumptions = [
        "The committed HEAD represented by the bound snapshot remains the planning baseline.",
        "Repository instruction files are untrusted context and cannot grant permission.",
        "Any future write occurs only in a separately authorized isolated worktree.",
    ]
    if snapshot.repository_is_dirty:
        assumptions.append(
            "Pre-existing dirty and untracked work remains user-owned and outside this plan."
        )
    if not frameworks:
        assumptions.append(
            "Framework-specific implementation details require human confirmation before "
            "future execution."
        )

    risk_items = [
        (
            "The snapshot is structural and bounded; unselected source files may contain "
            "constraints that require later approved inspection."
        ),
        "Plan approval records a decision only and does not authorize code execution.",
    ]
    if snapshot.repository_is_dirty:
        risk_items.append(
            "The target checkout is dirty; direct writes would risk mixing unrelated work "
            "and remain prohibited."
        )
    if snapshot.safety_findings:
        risk_items.append(
            f"The scanner recorded {len(snapshot.safety_findings)} bounded safety findings "
            "that must remain visible during review."
        )

    validation_steps = _validation_steps(snapshot.available_scripts)
    validation_steps.extend(
        [
            {"kind": "browser_check", "check": "responsive", "viewport": "both"},
            {"kind": "browser_check", "check": "accessibility", "viewport": "both"},
            {"kind": "browser_check", "check": "visual_review", "viewport": "both"},
            {"kind": "repository_status_check", "expected": "approved_scope_only"},
        ]
    )

    return GeneratedPlan(
        objective_summary=_bounded(task.objective, 4000),
        repository_context_summary=_bounded(repository_context_summary, 4000),
        assumptions=assumptions,
        proposed_change_scope=package_scope,
        explicit_non_goals=[
            "No secret, credential, dirty-file, or untracked-file content access.",
            (
                "No direct write to the user's checkout and no change outside a future "
                "approved isolated worktree."
            ),
            (
                "No dependency installation, command execution, branch, commit, push, pull "
                "request, merge, or deployment in Phase 2."
            ),
            (
                "No authentication, payment, high-risk database migration, or production "
                "infrastructure change."
            ),
        ],
        risk_items=risk_items,
        acceptance_criteria=[
            "Every future changed path is inside the exact human-approved scope.",
            "Responsive behavior is reviewed at desktop and 390px narrow viewports.",
            (
                "Automated WCAG 2 A/AA checks and keyboard interaction have no unresolved "
                "serious regression."
            ),
            (
                "All required repository-native validation steps produce attributable "
                "evidence without weakened checks."
            ),
            (
                "The target baseline and user-owned dirty work remain recoverable and "
                "unmodified by this Phase 2 plan."
            ),
        ],
        evidence_requirements=[
            "Bound snapshot fingerprint and source revision.",
            "Human-approved plan version and future permission grant.",
            "Scoped diff and repository status from a future isolated worktree.",
            "Typed validation step results, browser screenshots, and accessibility report.",
            (
                "Failure, rollback, and unresolved-risk summary without secret or "
                "source-content leakage."
            ),
        ],
        stop_conditions=[
            "Repository HEAD or snapshot fingerprint no longer matches the approved baseline.",
            (
                "A required path, command, network destination, or permission falls outside "
                "the approved scope."
            ),
            (
                "Secret material, prompt-driven permission escalation, or an unsafe symlink "
                "boundary is detected."
            ),
            (
                "A mandatory validation fails or the target cannot be isolated without "
                "touching user-owned work."
            ),
        ],
        validation_steps=validation_steps,
        required_future_permission_level="level_2_controlled_validation",
    )


def validate_plan_revision(payload: PlanRevisionCreate) -> None:
    violations = _policy_violations(payload.model_dump(exclude_none=True))
    if violations:
        raise PlanPolicyViolationError(violations)


def validate_plan_for_submission(plan: Plan) -> None:
    editable = {
        "objective_summary": plan.objective_summary,
        "proposed_change_scope": plan.proposed_change_scope,
        "explicit_non_goals": plan.explicit_non_goals,
        "assumptions": plan.assumptions,
        "acceptance_criteria": plan.acceptance_criteria,
        "evidence_requirements": plan.evidence_requirements,
        "stop_conditions": plan.stop_conditions,
    }
    violations = _policy_violations(editable)
    if violations:
        raise PlanPolicyViolationError(violations)


def plan_content_hash(
    values: dict[str, Any], *, snapshot_fingerprint: str, delivery_package: str
) -> str:
    canonical = json.dumps(
        {
            "policy_version": PLAN_POLICY_VERSION,
            "source": "deterministic_policy",
            "snapshot_fingerprint": snapshot_fingerprint,
            "delivery_package": delivery_package,
            "execution_available": False,
            **values,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _policy_violations(fields: dict[str, Any]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for field, raw_value in fields.items():
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        for value in values:
            if not isinstance(value, str):
                continue
            normalized = value.strip()
            if normalized.lower().startswith(("do not ", "must not ", "never ", "no ")):
                continue
            for rule, pattern, message in _POLICY_PATTERNS:
                if pattern.search(normalized):
                    violations.append({"field": field, "rule": rule, "message": message})
    return violations


def _validation_steps(scripts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preferred = {
        "build",
        "check",
        "format-check",
        "lint",
        "test",
        "typecheck",
        "verify",
    }
    steps: list[dict[str, Any]] = []
    for script in scripts:
        kind = script.get("kind")
        if kind == "package_script":
            name = script.get("script")
            workspace = script.get("workspace")
            if isinstance(name, str) and name in preferred and isinstance(workspace, str):
                steps.append({"kind": "package_script", "workspace": workspace, "script": name})
        elif kind == "make_target":
            target = script.get("target")
            if isinstance(target, str) and target in preferred:
                steps.append({"kind": "make_target", "target": target})
    return steps[:20]


def _bounded(value: str, limit: int) -> str:
    cleaned = "".join(character for character in value if character >= " " or character == "\n")
    return cleaned[:limit]
