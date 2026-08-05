#!/usr/bin/env python3
"""Fail closed when provider-foundation evidence contains credential material."""

import argparse
import json
import os
import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIRECTORY = REPOSITORY_ROOT / "docs/evidence/provider-foundation"
MANIFEST_PATH = EVIDENCE_DIRECTORY / "manifest.json"
SCENARIO_IDS = (
    "provider-registry-desktop-en",
    "provider-registry-mobile-zh",
    "provider-selector-desktop-zh",
    "provider-selector-mobile-en",
    "provider-unconfigured-error-desktop-zh",
)
PROVIDER_SECRET_NAMES = (
    "ZHIPU_API_KEY",
    "QWEN_API_KEY",
    "DEEPSEEK_API_KEY",
    "DOUBAO_API_KEY",
    "KIMI_API_KEY",
)
FORBIDDEN_PATTERNS = (
    (
        "synthetic-credential",
        re.compile(rb"synthetic[-_ ]?(?:api[-_ ]?)?(?:key|credential|token)", re.I),
    ),
    ("authorization", re.compile(rb"\bauthorization\b", re.I)),
    ("bearer", re.compile(rb"\bbearer\b", re.I)),
    ("home-absolute-path", re.compile(rb"/(?:Users|home)/[A-Za-z0-9._-]+/")),
    ("openai-shaped-key", re.compile(rb"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("aws-access-key", re.compile(rb"\bAKIA[A-Z0-9]{16}\b")),
    ("google-api-key", re.compile(rb"\bAIza[A-Za-z0-9_-]{20,}\b")),
    ("github-or-slack-token", re.compile(rb"\b(?:ghp|github_pat|xox[baprs])_[A-Za-z0-9_-]{12,}\b")),
    ("private-key", re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)


def fail(rule: str, path: Path) -> None:
    relative = path.relative_to(REPOSITORY_ROOT)
    raise ValueError(f"Evidence safety scan failed: rule={rule} file={relative}")


def validate_capture_record(scenario_id: str, record_path: Path) -> None:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    expected = {
        "scenario_id": scenario_id,
        "image_filename": f"{scenario_id}.png",
        "forbidden_pattern_scan": "passed",
        "provider_environment_value_scan": "passed",
        "classification": "fixture_mock_not_live",
    }
    for key, value in expected.items():
        if record.get(key) != value:
            fail(f"invalid-capture-record-{key}", record_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--images-only",
        action="store_true",
        help="Validate captured PNGs and capture-time scan records before manifest generation.",
    )
    args = parser.parse_args()
    artifacts: list[Path] = []
    for scenario_id in SCENARIO_IDS:
        image_path = EVIDENCE_DIRECTORY / f"{scenario_id}.png"
        record_path = EVIDENCE_DIRECTORY / f"{scenario_id}.capture-safety.json"
        if not image_path.is_file() or image_path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            fail("missing-or-invalid-png", image_path)
        if not record_path.is_file():
            fail("missing-capture-safety-record", record_path)
        validate_capture_record(scenario_id, record_path)
        artifacts.extend((image_path, record_path))

    if not args.images_only:
        if not MANIFEST_PATH.is_file():
            fail("missing-manifest", MANIFEST_PATH)
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if manifest.get("live_provider_calls_performed") is not False:
            fail("invalid-live-call-classification", MANIFEST_PATH)
        screenshots = manifest.get("screenshots")
        if not isinstance(screenshots, list) or len(screenshots) != len(SCENARIO_IDS):
            fail("invalid-manifest-screenshot-count", MANIFEST_PATH)
        if any(item.get("redaction_scan_status") != "passed" for item in screenshots):
            fail("manifest-redaction-status", MANIFEST_PATH)
        artifacts.append(MANIFEST_PATH)

    artifacts.extend(sorted(EVIDENCE_DIRECTORY.glob("*.md")))

    environment_values = [
        value.encode()
        for name in PROVIDER_SECRET_NAMES
        if (value := os.environ.get(name)) is not None and len(value) >= 8
    ]
    for artifact in artifacts:
        data = artifact.read_bytes()
        for rule, pattern in FORBIDDEN_PATTERNS:
            if pattern.search(data):
                fail(rule, artifact)
        if any(value in data for value in environment_values):
            fail("provider-environment-value", artifact)

    print(
        "PROVIDER_EVIDENCE_SAFETY_SCAN "
        f"status=PASS artifacts={len(artifacts)} capture_records={len(SCENARIO_IDS)} "
        f"provider_environment_values_checked={len(environment_values)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
