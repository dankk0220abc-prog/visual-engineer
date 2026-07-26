import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "apps/api/src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "packages/runner-protocol/src"))

from visual_engineer_api.main import app  # noqa: E402


def main() -> None:
    destination = REPOSITORY_ROOT / "packages/api-contract/openapi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
