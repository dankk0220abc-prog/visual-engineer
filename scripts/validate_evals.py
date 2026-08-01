import json
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATASETS = sorted((REPOSITORY_ROOT / "evals/datasets").glob("*.jsonl"))
RUNNER_DATASET = "runner-protocol-v0.1.jsonl"
WORKSPACE_DATASET = "workspace-tools-v0.1.jsonl"
VALIDATION_SUITE_DATASET = "validation-suites-v0.1.jsonl"
REVIEW_READINESS_DATASET = "review-readiness-v0.1.jsonl"
GOVERNED_AI_DATASET = "governed-ai-planning-v0.1.jsonl"
RUNNER_FAILURE_CATEGORIES = {
    "authentication",
    "concurrency",
    "control_plane_unavailable",
    "lease_fencing",
    "none",
    "permission_boundary",
    "retry_exhausted",
    "secret_boundary",
    "state_transition",
}
WORKSPACE_FAILURE_CATEGORIES = {
    "atomicity",
    "budget",
    "cancellation",
    "content_conflict",
    "disposal",
    "evidence",
    "grant",
    "none",
    "path",
    "protocol",
    "rollback",
    "source_isolation",
    "stale_lease",
    "symlink",
}
VALIDATION_SUITE_FAILURE_CATEGORIES = {
    "budget",
    "cancellation",
    "grant",
    "idempotency",
    "injection",
    "none",
    "recovery",
    "retry",
    "timeout",
}
REVIEW_READINESS_FAILURE_CATEGORIES = {
    "concurrency",
    "delivery_authority",
    "evidence",
    "idempotency",
    "immutability",
    "none",
    "stale",
}
GOVERNED_AI_FAILURE_CATEGORIES = {
    "acceptance",
    "approval",
    "binding",
    "budget",
    "grounding",
    "injection",
    "operation",
    "reference",
    "replay",
    "schema",
    "secret",
    "stale",
}


def validate_mapped_case(
    dataset: Path,
    line_number: int,
    value: dict[str, Any],
    *,
    dataset_version: str,
    failure_categories: set[str],
    label: str,
) -> None:
    required = {
        "case_id",
        "schema_version",
        "dataset_version",
        "category",
        "input",
        "expected",
        "failure_category",
        "test_mapping",
    }
    if not required.issubset(value):
        raise SystemExit(f"{dataset.name}:{line_number}: invalid {label} eval case shape")
    if value["schema_version"] != 1 or value["dataset_version"] != dataset_version:
        raise SystemExit(f"{dataset.name}:{line_number}: unsupported {label} eval version")
    if not isinstance(value["category"], str) or not isinstance(value["input"], dict):
        raise SystemExit(f"{dataset.name}:{line_number}: invalid {label} category or input")
    expected = value["expected"]
    if not isinstance(expected, dict) or not isinstance(expected.get("outcome"), str):
        raise SystemExit(f"{dataset.name}:{line_number}: {label} expected outcome is required")
    if value["failure_category"] not in failure_categories:
        raise SystemExit(f"{dataset.name}:{line_number}: unknown {label} failure category")
    mappings = value["test_mapping"]
    if not isinstance(mappings, list) or not mappings:
        raise SystemExit(f"{dataset.name}:{line_number}: {label} test mapping is required")
    for mapping in mappings:
        if not isinstance(mapping, str) or "::" not in mapping:
            raise SystemExit(f"{dataset.name}:{line_number}: invalid {label} test mapping")
        relative_path, function_name = mapping.split("::", 1)
        test_path = REPOSITORY_ROOT / relative_path
        if (
            not test_path.is_file()
            or not function_name.startswith("test_")
            or f"def {function_name}(" not in test_path.read_text(encoding="utf-8")
        ):
            raise SystemExit(f"{dataset.name}:{line_number}: unmapped {label} test {mapping}")


def main() -> None:
    seen: set[str] = set()
    count = 0
    for dataset in DATASETS:
        for line_number, line in enumerate(dataset.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            value: Any = json.loads(line)
            if not isinstance(value, dict):
                raise SystemExit(f"{dataset.name}:{line_number}: invalid eval case shape")
            if dataset.name == RUNNER_DATASET:
                validate_mapped_case(
                    dataset,
                    line_number,
                    value,
                    dataset_version="runner-protocol-v0.1",
                    failure_categories=RUNNER_FAILURE_CATEGORIES,
                    label="Runner",
                )
            elif dataset.name == WORKSPACE_DATASET:
                validate_mapped_case(
                    dataset,
                    line_number,
                    value,
                    dataset_version="workspace-tools-v0.1",
                    failure_categories=WORKSPACE_FAILURE_CATEGORIES,
                    label="Workspace",
                )
            elif dataset.name == VALIDATION_SUITE_DATASET:
                validate_mapped_case(
                    dataset,
                    line_number,
                    value,
                    dataset_version="validation-suites-v0.1",
                    failure_categories=VALIDATION_SUITE_FAILURE_CATEGORIES,
                    label="Validation Suite",
                )
            elif dataset.name == REVIEW_READINESS_DATASET:
                validate_mapped_case(
                    dataset,
                    line_number,
                    value,
                    dataset_version="review-readiness-v0.1",
                    failure_categories=REVIEW_READINESS_FAILURE_CATEGORIES,
                    label="Review Readiness",
                )
            elif dataset.name == GOVERNED_AI_DATASET:
                validate_mapped_case(
                    dataset,
                    line_number,
                    value,
                    dataset_version="governed-ai-planning-v0.1",
                    failure_categories=GOVERNED_AI_FAILURE_CATEGORIES,
                    label="Governed AI Planning",
                )
            if "case_id" in value:
                required = {"case_id", "category", "input", "expected"}
                case_id = value["case_id"]
            else:
                required = {"id", "kind"}
                case_id = value.get("id")
                if not any(key in value for key in ("request", "steps", "precondition")):
                    raise SystemExit(
                        f"{dataset.name}:{line_number}: Foundation case has no executable input"
                    )
                if value.get("kind") == "sequence":
                    steps = value.get("steps")
                    if (
                        not isinstance(steps, list)
                        or not steps
                        or any(
                            not isinstance(step, dict) or "expected" not in step for step in steps
                        )
                    ):
                        raise SystemExit(
                            f"{dataset.name}:{line_number}: invalid Foundation sequence"
                        )
                elif "expected" not in value:
                    raise SystemExit(
                        f"{dataset.name}:{line_number}: Foundation case has no expected result"
                    )
            if not required.issubset(value):
                raise SystemExit(f"{dataset.name}:{line_number}: invalid eval case shape")
            if not isinstance(case_id, str) or not case_id or case_id in seen:
                raise SystemExit(f"{dataset.name}:{line_number}: duplicate or invalid case_id")
            if any(key in value for key in ("agent_score", "result", "passed")):
                raise SystemExit(
                    f"{dataset.name}:{line_number}: datasets must not contain invented results"
                )
            seen.add(case_id)
            count += 1
    if count == 0:
        raise SystemExit("No eval cases found")
    print(f"Validated {count} deterministic eval cases across {len(DATASETS)} datasets.")


if __name__ == "__main__":
    main()
