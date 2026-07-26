import json
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATASETS = sorted((REPOSITORY_ROOT / "evals/datasets").glob("*.jsonl"))


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
