#!/usr/bin/env python3
"""Build the deterministic manifest for provider-foundation screenshot evidence."""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIRECTORY = REPOSITORY_ROOT / "docs/evidence/provider-foundation"
MANIFEST_PATH = EVIDENCE_DIRECTORY / "manifest.json"
SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "scenario_id": "provider-registry-desktop-en",
        "locale": "en-US",
        "route": "/providers",
        "viewport": {"width": 1440, "height": 1000},
    },
    {
        "scenario_id": "provider-registry-mobile-zh",
        "locale": "zh-CN",
        "route": "/providers",
        "viewport": {"width": 390, "height": 844},
    },
    {
        "scenario_id": "provider-selector-desktop-zh",
        "locale": "zh-CN",
        "route": "/runs/{synthetic-run-id}",
        "viewport": {"width": 1440, "height": 1000},
    },
    {
        "scenario_id": "provider-selector-mobile-en",
        "locale": "en-US",
        "route": "/runs/{synthetic-run-id}",
        "viewport": {"width": 390, "height": 844},
    },
    {
        "scenario_id": "provider-unconfigured-error-desktop-zh",
        "locale": "zh-CN",
        "route": "/runs/{synthetic-run-id}",
        "viewport": {"width": 1440, "height": 1000},
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def captured_at(path: Path) -> str:
    return (
        datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def committed_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    revision = result.stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("Git HEAD is not a full commit SHA")
    return revision


def require_capture_record(scenario_id: str) -> Path:
    record_path = EVIDENCE_DIRECTORY / f"{scenario_id}.capture-safety.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    expected = {
        "rule_id": "VE_PROVIDER_EVIDENCE_SECRET_LEAK",
        "checked_value_count": 0,
        "result": "passed",
        "error_category": None,
    }
    if record != expected:
        raise ValueError(f"Capture safety record {record_path.name} is invalid")
    return record_path


def build_manifest(scan_status: str) -> dict[str, Any]:
    revision = committed_head()
    screenshots: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        scenario_id = str(scenario["scenario_id"])
        image_path = EVIDENCE_DIRECTORY / f"{scenario_id}.png"
        if not image_path.is_file():
            raise FileNotFoundError(
                f"Missing screenshot: {image_path.relative_to(REPOSITORY_ROOT)}"
            )
        record_path = require_capture_record(scenario_id)
        screenshots.append(
            {
                **scenario,
                "commit_sha": revision,
                "image_relative_path": image_path.relative_to(REPOSITORY_ROOT).as_posix(),
                "image_sha256": sha256(image_path),
                "classification": "fixture_mock_not_live",
                "captured_timestamp": captured_at(image_path),
                "redaction_scan_status": scan_status,
                "capture_scan_relative_path": record_path.relative_to(REPOSITORY_ROOT).as_posix(),
            }
        )
    return {
        "schema_version": 1,
        "generated_timestamp": datetime.now(tz=UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "classification_notice": "Fixture / Mock Evidence - Not a live-provider call",
        "live_provider_calls_performed": False,
        "screenshots": screenshots,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--redaction-scan-status",
        choices=("pending", "passed"),
        default="pending",
    )
    args = parser.parse_args()
    manifest = build_manifest(args.redaction_scan_status)
    EVIDENCE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    temporary_path = MANIFEST_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n",
        encoding="utf-8",
    )
    temporary_path.replace(MANIFEST_PATH)
    print(
        "PROVIDER_EVIDENCE_MANIFEST "
        f"status=PASS screenshots={len(manifest['screenshots'])} "
        f"path={MANIFEST_PATH.relative_to(REPOSITORY_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
