from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from visual_engineer_api.core.config import Settings

SCANNER_VERSION = "1.0.0"
SCAN_POLICY_VERSION = "phase2-v1"

_SENSITIVE_EXACT_NAMES = {
    ".env",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "auth.json",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
_SENSITIVE_SUFFIXES = {
    ".cer",
    ".crt",
    ".der",
    ".jks",
    ".key",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
}
_SENSITIVE_NAME_PARTS = (
    "access-token",
    "access_token",
    "auth-cookie",
    "auth_cookie",
    "cloud-credential",
    "cloud_credential",
    "private-key",
    "private_key",
    "registry-token",
    "registry_token",
    "service-account",
    "service_account",
)
_IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
    "playwright-report",
    "test-results",
    "vendor",
}
_KNOWN_BINARY_SUFFIXES = {
    ".7z",
    ".a",
    ".avi",
    ".bin",
    ".class",
    ".dylib",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".o",
    ".otf",
    ".pdf",
    ".png",
    ".pyc",
    ".so",
    ".tar",
    ".ttf",
    ".wav",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}
_LOCKFILES = {
    "bun.lock",
    "bun.lockb",
    "cargo.lock",
    "composer.lock",
    "gemfile.lock",
    "go.sum",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}
_EXACT_SELECTION_NAMES = {
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.yaml",
    "agents.md",
    "alembic.ini",
    "biome.json",
    "composer.json",
    "deno.json",
    "dockerfile",
    "gemfile",
    "go.mod",
    "makefile",
    "mypy.ini",
    "package.json",
    "plans.md",
    "pnpm-workspace.yaml",
    "pyproject.toml",
    "pytest.ini",
    "ruff.toml",
    "tsconfig.json",
    "turbo.json",
}
_CONFIG_PREFIXES = (
    "compose.",
    "docker-compose.",
    "eslint.config.",
    "jest.config.",
    "next.config.",
    "playwright.config.",
    "postcss.config.",
    "prettier.config.",
    "storybook.",
    "tailwind.config.",
    "tsconfig.",
    "vite.config.",
    "vitest.config.",
)
_TEXT_CONFIG_SUFFIXES = {
    ".cjs",
    ".conf",
    ".ini",
    ".js",
    ".json",
    ".mjs",
    ".toml",
    ".ts",
    ".yaml",
    ".yml",
}
_INSTRUCTION_NAMES = {"agents.md", "claude.md", "copilot-instructions.md", "plans.md"}

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    ("private_key_material", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("openai_token", re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws_access_key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
)
_PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|override)\b.{0,80}\b(previous|system|developer)\b", re.I | re.S
        ),
    ),
    (
        "secret_access_request",
        re.compile(
            r"\b(read|print|exfiltrate|upload)\b.{0,80}\b(\.env|secret|credential|token)\b",
            re.I | re.S,
        ),
    ),
    (
        "permission_escalation_request",
        re.compile(
            r"\b(disable|bypass|elevate|modify)\b.{0,80}\b(test|approval|permission|policy)\b",
            re.I | re.S,
        ),
    ),
    (
        "unauthorized_delivery_request",
        re.compile(
            r"\b(push|merge|deploy)\b.{0,80}\b(main|production|without approval)\b", re.I | re.S
        ),
    ),
)


class RepositoryScanError(Exception):
    """A stable, non-sensitive repository scan failure."""

    def __init__(self, code: str, public_message: str) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message


@dataclass(frozen=True)
class TreeEntry:
    mode: str
    object_type: str
    object_id: str
    size: int | None
    path: str


@dataclass(frozen=True)
class ScanResult:
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

    def model_values(self) -> dict[str, Any]:
        return asdict(self)


class _GitReader:
    def __init__(self, repository: Path, timeout_seconds: float) -> None:
        self._repository = repository
        self._deadline = time.monotonic() + timeout_seconds

    def run(self, arguments: list[str], *, allow_not_found: bool = False) -> bytes:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise RepositoryScanError(
                "repository_scan_timeout", "Repository scan exceeded its time limit"
            )

        command = [
            "git",
            "--no-optional-locks",
            "-c",
            f"safe.directory={self._repository}",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.attributesfile=/dev/null",
            "-c",
            "protocol.allow=never",
            *arguments,
        ]
        environment = {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "Never",
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        }
        try:
            completed = subprocess.run(
                command,
                cwd=self._repository,
                env=environment,
                check=False,
                capture_output=True,
                timeout=remaining,
            )
        except FileNotFoundError as exc:
            raise RepositoryScanError(
                "git_unavailable", "Git is not available to the repository scanner"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RepositoryScanError(
                "repository_scan_timeout", "Repository scan exceeded its time limit"
            ) from exc

        if completed.returncode != 0:
            if allow_not_found:
                return b""
            raise RepositoryScanError(
                "repository_git_read_failed", "Committed repository metadata could not be read"
            )
        return completed.stdout


class RepositoryScanner:
    """Read a bounded repository profile exclusively from committed Git objects."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def scan(self, locator: str) -> ScanResult:
        repository = self._validate_repository_path(locator)
        git = _GitReader(repository, self._settings.repository_scan_timeout_seconds)
        self._verify_git_root(repository, git)

        source_revision = self._decode_scalar(
            git.run(["rev-parse", "--verify", "HEAD^{commit}"]),
            code="repository_head_unavailable",
        )
        branch_output = git.run(
            ["symbolic-ref", "--quiet", "--short", "HEAD"], allow_not_found=True
        )
        branch_name = branch_output.decode("utf-8", "replace").strip() or "(detached HEAD)"
        dirty_paths, dirty_path_count = self._read_dirty_paths(git)
        entries = self._read_tree(git)

        if len(entries) > self._settings.repository_scan_max_files:
            raise RepositoryScanError(
                "repository_file_budget_exceeded",
                "Repository exceeds the configured tracked-file budget",
            )

        (
            manifest,
            selected_content,
            selected_entries,
            safety_findings,
            total_selected_bytes,
        ) = self._select_and_read(git, entries)
        extracted = self._extract_facts(
            entries, selected_content, selected_entries, safety_findings
        )

        fingerprint_payload = {
            "source_revision": source_revision,
            "scanner_version": SCANNER_VERSION,
            "scan_policy_version": SCAN_POLICY_VERSION,
            "selected_files": [
                {
                    "path": entry.path,
                    "object_id": entry.object_id,
                    "content_sha256": hashlib.sha256(selected_content[entry.path]).hexdigest(),
                }
                for entry in sorted(selected_entries, key=lambda item: item.path)
                if entry.path in selected_content
            ],
            "tech_stack": extracted["tech_stack"],
            "package_manager": extracted["package_manager"],
            "available_scripts": extracted["available_scripts"],
            "test_surfaces": extracted["test_surfaces"],
            "design_system_signals": extracted["design_system_signals"],
            "repository_instructions": extracted["repository_instructions"],
            "safety_findings": sorted(
                safety_findings,
                key=lambda item: (
                    str(item.get("relative_path", "")),
                    str(item.get("rule_type", "")),
                ),
            ),
            "manifest": [
                {
                    key: value
                    for key, value in item.items()
                    if key not in {"selected", "skip_reason"}
                }
                for item in manifest
            ],
        }
        fingerprint = hashlib.sha256(_canonical_json(fingerprint_payload)).hexdigest()
        selected_count = len(selected_content)

        return ScanResult(
            source_revision=source_revision,
            branch_name=branch_name,
            repository_is_dirty=dirty_path_count > 0,
            dirty_path_count=dirty_path_count,
            dirty_paths=dirty_paths,
            scanner_version=SCANNER_VERSION,
            scan_policy_version=SCAN_POLICY_VERSION,
            fingerprint=fingerprint,
            tracked_file_count=len(entries),
            selected_file_count=selected_count,
            skipped_file_count=max(0, len(entries) - selected_count),
            total_selected_bytes=total_selected_bytes,
            tech_stack=extracted["tech_stack"],
            package_manager=extracted["package_manager"],
            available_scripts=extracted["available_scripts"],
            test_surfaces=extracted["test_surfaces"],
            design_system_signals=extracted["design_system_signals"],
            repository_instructions=extracted["repository_instructions"],
            safety_findings=sorted(
                safety_findings,
                key=lambda item: (
                    str(item.get("relative_path", "")),
                    str(item.get("rule_type", "")),
                ),
            ),
            manifest=manifest,
        )

    def _validate_repository_path(self, locator: str) -> Path:
        if not locator or "\x00" in locator:
            raise RepositoryScanError("repository_path_invalid", "Repository path is invalid")
        expanded = Path(locator).expanduser()
        if not expanded.is_absolute():
            raise RepositoryScanError("repository_path_invalid", "Repository path must be absolute")
        try:
            if expanded.is_symlink():
                raise RepositoryScanError(
                    "repository_symlink_root_denied",
                    "Repository root cannot be a symbolic link",
                )
            repository = expanded.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise RepositoryScanError(
                "repository_not_found", "Repository directory was not found"
            ) from exc
        if not repository.is_dir():
            raise RepositoryScanError(
                "repository_not_directory", "Repository path must be a directory"
            )

        if not any(
            repository == root or root in repository.parents
            for root in self._settings.repository_roots
        ):
            raise RepositoryScanError(
                "repository_outside_allowlist",
                "Repository path is outside the configured read-only roots",
            )

        git_metadata = repository / ".git"
        if git_metadata.is_symlink() or not git_metadata.is_dir():
            raise RepositoryScanError(
                "repository_git_boundary_invalid",
                "Repository must have local non-symlink Git metadata",
            )
        return repository

    @staticmethod
    def _verify_git_root(repository: Path, git: _GitReader) -> None:
        inside = git.run(["rev-parse", "--is-inside-work-tree"]).decode("ascii", "replace").strip()
        if inside != "true":
            raise RepositoryScanError(
                "repository_not_git", "Repository path is not a Git working tree"
            )
        root_text = git.run(["rev-parse", "--show-toplevel"]).decode("utf-8", "replace").strip()
        try:
            root = Path(root_text).resolve(strict=True)
        except OSError as exc:
            raise RepositoryScanError(
                "repository_git_boundary_invalid", "Git repository boundary is invalid"
            ) from exc
        if root != repository:
            raise RepositoryScanError(
                "repository_git_root_mismatch",
                "Repository locator must identify the exact Git root",
            )

    def _read_dirty_paths(self, git: _GitReader) -> tuple[list[dict[str, Any]], int]:
        output = git.run(
            [
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--no-renames",
            ]
        )
        records = [record for record in output.split(b"\0") if record]
        paths: list[dict[str, Any]] = []
        for record in records[: self._settings.repository_dirty_path_limit]:
            if len(record) < 4:
                continue
            status_code = record[:2].decode("ascii", "replace")
            relative_path = record[3:].decode("utf-8", "replace")
            paths.append(
                {
                    "relative_path": _safe_relative_path(relative_path),
                    "status": status_code,
                    "untracked": status_code == "??",
                }
            )
        return paths, len(records)

    @staticmethod
    def _read_tree(git: _GitReader) -> list[TreeEntry]:
        output = git.run(["ls-tree", "-rlz", "--full-tree", "HEAD"])
        entries: list[TreeEntry] = []
        for raw_record in output.split(b"\0"):
            if not raw_record:
                continue
            try:
                raw_metadata, raw_path = raw_record.split(b"\t", 1)
                metadata = raw_metadata.split()
                mode = metadata[0].decode("ascii")
                object_type = metadata[1].decode("ascii")
                object_id = metadata[2].decode("ascii")
                size = None if metadata[3] == b"-" else int(metadata[3])
                path = raw_path.decode("utf-8", "replace")
            except (IndexError, UnicodeDecodeError, ValueError) as exc:
                raise RepositoryScanError(
                    "repository_tree_invalid", "Committed repository tree is invalid"
                ) from exc
            safe_path = _safe_relative_path(path)
            entries.append(
                TreeEntry(
                    mode=mode,
                    object_type=object_type,
                    object_id=object_id,
                    size=size,
                    path=safe_path,
                )
            )
        return sorted(entries, key=lambda item: item.path)

    def _select_and_read(
        self, git: _GitReader, entries: list[TreeEntry]
    ) -> tuple[
        list[dict[str, Any]],
        dict[str, bytes],
        list[TreeEntry],
        list[dict[str, Any]],
        int,
    ]:
        safety_findings: list[dict[str, Any]] = []
        manifest: list[dict[str, Any]] = []
        candidates: list[TreeEntry] = []
        manifest_by_path: dict[str, dict[str, Any]] = {}

        for entry in entries:
            path = PurePosixPath(entry.path)
            entry_type = _entry_type(entry)
            item: dict[str, Any] = {
                "relative_path": entry.path,
                "entry_type": entry_type,
                "object_id": entry.object_id,
                "size": entry.size,
                "selected": False,
            }
            manifest.append(item)
            manifest_by_path[entry.path] = item

            if entry_type == "submodule":
                item["skip_reason"] = "submodule"
                safety_findings.append(
                    _finding(
                        entry.path,
                        "submodule_not_initialized",
                        True,
                        "Gitlink recorded without initialization or network access",
                    )
                )
                continue
            if entry_type == "symlink":
                if entry.size is None or entry.size > self._settings.repository_scan_max_file_bytes:
                    item["symlink_target_kind"] = "metadata_budget_exceeded"
                    item["skip_reason"] = "symlink_not_followed"
                    safety_findings.append(
                        _finding(
                            entry.path,
                            "symlink_metadata_budget_exceeded",
                            True,
                            (
                                "Symbolic link target metadata exceeded the byte budget "
                                "and was not read"
                            ),
                        )
                    )
                    continue
                target = git.run(["cat-file", "blob", entry.object_id])
                item["symlink_target_hash"] = hashlib.sha256(target).hexdigest()
                item["symlink_target_kind"] = _symlink_target_kind(target)
                item["skip_reason"] = "symlink_not_followed"
                safety_findings.append(
                    _finding(
                        entry.path,
                        "symlink_not_followed",
                        True,
                        "Symbolic link metadata recorded without following its target",
                    )
                )
                continue
            if _has_ignored_directory(path):
                item["skip_reason"] = "ignored_directory"
                if "node_modules" in path.parts:
                    safety_findings.append(
                        _finding(
                            entry.path,
                            "dependency_tree_skipped",
                            True,
                            "Dependency directory content was not selected",
                        )
                    )
                continue
            sensitive_rule = _sensitive_rule(path)
            if sensitive_rule is not None:
                item.pop("object_id", None)
                item.pop("size", None)
                item["skip_reason"] = "sensitive_path"
                safety_findings.append(
                    _finding(
                        entry.path,
                        sensitive_rule,
                        True,
                        "Sensitive file path detected; content was not read",
                    )
                )
                continue
            if path.suffix.lower() in _KNOWN_BINARY_SUFFIXES:
                item["skip_reason"] = "known_binary"
                safety_findings.append(
                    _finding(
                        entry.path,
                        "binary_file_skipped",
                        True,
                        "Known binary file type was not read",
                    )
                )
                continue
            if path.name.lower() in _LOCKFILES:
                item["skip_reason"] = "lockfile_metadata_only"
                continue
            if _is_selected_candidate(path):
                candidates.append(entry)
            else:
                item["skip_reason"] = "not_selected_by_policy"

        candidates.sort(
            key=lambda entry: (_selection_priority(PurePosixPath(entry.path)), entry.path)
        )
        if len(candidates) > self._settings.repository_scan_max_selected_files:
            safety_findings.append(
                _finding(
                    "",
                    "selected_file_budget_truncated",
                    True,
                    "Candidate selection exceeded the configured file budget",
                )
            )
        candidates = candidates[: self._settings.repository_scan_max_selected_files]

        selected_content: dict[str, bytes] = {}
        selected_entries: list[TreeEntry] = []
        total_selected_bytes = 0
        for entry in candidates:
            item = manifest_by_path[entry.path]
            if (
                entry.size is not None
                and entry.size > self._settings.repository_scan_max_file_bytes
            ):
                item["skip_reason"] = "file_byte_budget"
                safety_findings.append(
                    _finding(
                        entry.path,
                        "file_byte_budget_exceeded",
                        True,
                        "Selected candidate exceeded the per-file byte budget",
                    )
                )
                continue
            content = git.run(["cat-file", "blob", entry.object_id])
            if len(content) > self._settings.repository_scan_max_file_bytes:
                item["skip_reason"] = "file_byte_budget"
                safety_findings.append(
                    _finding(
                        entry.path,
                        "file_byte_budget_exceeded",
                        True,
                        "Selected candidate exceeded the per-file byte budget",
                    )
                )
                continue
            if total_selected_bytes + len(content) > self._settings.repository_scan_max_total_bytes:
                item["skip_reason"] = "total_byte_budget"
                safety_findings.append(
                    _finding(
                        entry.path,
                        "total_byte_budget_exceeded",
                        True,
                        "Selected content was truncated at the configured total byte budget",
                    )
                )
                continue
            if _looks_binary(content):
                item["skip_reason"] = "binary_content"
                safety_findings.append(
                    _finding(
                        entry.path,
                        "binary_content_skipped",
                        True,
                        "Binary content was not parsed or persisted",
                    )
                )
                continue
            secret_rule = _secret_content_rule(content)
            if secret_rule is not None:
                item.pop("object_id", None)
                item.pop("size", None)
                item["skip_reason"] = "secret_content"
                safety_findings.append(
                    _finding(
                        entry.path,
                        secret_rule,
                        True,
                        "Potential secret material was detected and excluded",
                    )
                )
                continue
            if content.startswith(b"version https://git-lfs.github.com/spec/v1"):
                item["skip_reason"] = "git_lfs_pointer"
                safety_findings.append(
                    _finding(
                        entry.path,
                        "git_lfs_pointer_not_fetched",
                        True,
                        "Git LFS pointer recorded without fetching external content",
                    )
                )
                continue

            item["selected"] = True
            item.pop("skip_reason", None)
            item["content_sha256"] = hashlib.sha256(content).hexdigest()
            selected_content[entry.path] = content
            selected_entries.append(entry)
            total_selected_bytes += len(content)

        return (
            manifest,
            selected_content,
            selected_entries,
            _deduplicate_findings(safety_findings),
            total_selected_bytes,
        )

    @staticmethod
    def _extract_facts(
        entries: list[TreeEntry],
        selected_content: dict[str, bytes],
        selected_entries: list[TreeEntry],
        safety_findings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        package_manager = _detect_package_manager(entries)
        languages = _detect_languages(entries)
        frameworks: set[str] = set()
        available_scripts: list[dict[str, Any]] = []

        for entry in selected_entries:
            content = selected_content[entry.path]
            path = PurePosixPath(entry.path)
            if path.name == "package.json":
                package_data = _safe_json_object(content)
                dependency_names = _package_dependency_names(package_data)
                frameworks.update(_frameworks_from_dependencies(dependency_names))
                workspace = str(path.parent)
                if workspace == ".":
                    workspace = "."
                scripts = package_data.get("scripts")
                if isinstance(scripts, dict):
                    for name in sorted(str(key) for key in scripts if _safe_identifier(str(key))):
                        available_scripts.append(
                            {"kind": "package_script", "workspace": workspace, "script": name}
                        )
            elif path.name == "pyproject.toml":
                pyproject = _safe_toml_object(content)
                dependencies = _python_dependencies(pyproject)
                frameworks.update(_frameworks_from_dependencies(dependencies))
            elif path.name.lower() == "makefile":
                text = content.decode("utf-8", "replace")
                for target in _make_targets(text):
                    available_scripts.append({"kind": "make_target", "target": target})

        repository_instructions: list[dict[str, Any]] = []
        for entry in selected_entries:
            path = PurePosixPath(entry.path)
            if not _is_instruction_path(path):
                continue
            content = selected_content[entry.path]
            text = content.decode("utf-8", "replace")
            risk_rules = [
                rule_name
                for rule_name, pattern in _PROMPT_INJECTION_PATTERNS
                if pattern.search(text)
            ]
            risk_label = "prompt_injection_risk" if risk_rules else "untrusted_content"
            repository_instructions.append(
                {
                    "relative_path": entry.path,
                    "blob_object_id": entry.object_id,
                    "content_sha256": hashlib.sha256(content).hexdigest(),
                    "source": "git_head_blob",
                    "provenance": "untrusted_repository_content",
                    "risk_label": risk_label,
                    "risk_rules": sorted(risk_rules),
                }
            )
            for rule_name in risk_rules:
                safety_findings.append(
                    _finding(
                        entry.path,
                        f"prompt_injection_{rule_name}",
                        True,
                        "Untrusted repository instruction was classified but not followed",
                    )
                )

        test_surfaces = _test_surfaces(entries)
        design_signals = _design_system_signals(entries)
        return {
            "tech_stack": {
                "languages": languages,
                "frameworks": sorted(frameworks),
                "provenance": "committed_head_structured_extraction",
            },
            "package_manager": package_manager,
            "available_scripts": _unique_dicts(available_scripts),
            "test_surfaces": test_surfaces,
            "design_system_signals": design_signals,
            "repository_instructions": repository_instructions,
        }

    @staticmethod
    def _decode_scalar(value: bytes, *, code: str) -> str:
        decoded = value.decode("ascii", "replace").strip()
        if not decoded:
            raise RepositoryScanError(code, "Committed repository revision is unavailable")
        return decoded


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _safe_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or not value or "\x00" in value or ".." in path.parts:
        raise RepositoryScanError(
            "repository_tree_path_invalid", "Repository contains an invalid relative path"
        )
    return path.as_posix()


def _entry_type(entry: TreeEntry) -> str:
    if entry.mode == "160000" or entry.object_type == "commit":
        return "submodule"
    if entry.mode == "120000":
        return "symlink"
    return "file"


def _finding(relative_path: str, rule_type: str, blocked: bool, summary: str) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "rule_type": rule_type,
        "blocked": blocked,
        "summary": summary,
    }


def _deduplicate_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (str(finding.get("relative_path", "")), str(finding.get("rule_type", "")))
        deduplicated[key] = finding
    return list(deduplicated.values())


def _has_ignored_directory(path: PurePosixPath) -> bool:
    return any(part.lower() in _IGNORED_DIRECTORY_NAMES for part in path.parts[:-1])


def _sensitive_rule(path: PurePosixPath) -> str | None:
    name = path.name.lower()
    if name == ".env.example" or name == ".env.sample":
        return None
    if name == ".env" or name.startswith(".env."):
        return "environment_file"
    if name in _SENSITIVE_EXACT_NAMES:
        return "credential_file"
    if path.suffix.lower() in _SENSITIVE_SUFFIXES:
        return "key_or_certificate_file"
    if any(part in name for part in _SENSITIVE_NAME_PARTS):
        return "credential_file"
    return None


def _is_selected_candidate(path: PurePosixPath) -> bool:
    name = path.name.lower()
    if name in _EXACT_SELECTION_NAMES:
        return True
    if name.startswith(("readme", "requirements")):
        return True
    if any(name.startswith(prefix) for prefix in _CONFIG_PREFIXES):
        return path.suffix.lower() in _TEXT_CONFIG_SUFFIXES
    if len(path.parts) >= 3 and path.parts[0:2] == (".github", "workflows"):
        return path.suffix.lower() in {".yaml", ".yml"}
    if ".storybook" in path.parts and name in {"main.js", "main.ts", "preview.js", "preview.ts"}:
        return True
    return False


def _selection_priority(path: PurePosixPath) -> int:
    name = path.name.lower()
    if name in {"package.json", "pyproject.toml", "go.mod", "composer.json", "gemfile"}:
        return 0
    if name in _INSTRUCTION_NAMES or name.startswith("readme"):
        return 1
    if "test" in name or "playwright" in name or "vitest" in name or "jest" in name:
        return 2
    return 3


def _looks_binary(content: bytes) -> bool:
    if b"\0" in content:
        return True
    sample = content[:4096]
    if not sample:
        return False
    control = sum(byte < 9 or (13 < byte < 32) for byte in sample)
    return control / len(sample) > 0.05


def _secret_content_rule(content: bytes) -> str | None:
    for rule_name, pattern in _SECRET_PATTERNS:
        if pattern.search(content):
            return rule_name
    return None


def _symlink_target_kind(content: bytes) -> str:
    target = content.decode("utf-8", "replace").strip()
    if not target:
        return "empty"
    path = PurePosixPath(target)
    if path.is_absolute():
        return "absolute"
    if ".." in path.parts:
        return "escapes_repository"
    return "relative_in_repository"


def _detect_package_manager(entries: list[TreeEntry]) -> str | None:
    names = {PurePosixPath(entry.path).name.lower() for entry in entries}
    for filename, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
        ("bun.lock", "bun"),
        ("bun.lockb", "bun"),
        ("uv.lock", "uv"),
        ("poetry.lock", "poetry"),
        ("cargo.lock", "cargo"),
        ("go.sum", "go"),
    ):
        if filename in names:
            return manager
    return None


def _detect_languages(entries: list[TreeEntry]) -> list[str]:
    suffix_map = {
        ".css": "CSS",
        ".go": "Go",
        ".html": "HTML",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".py": "Python",
        ".rb": "Ruby",
        ".rs": "Rust",
        ".scss": "SCSS",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".vue": "Vue",
    }
    languages = {
        suffix_map[suffix]
        for entry in entries
        if (suffix := PurePosixPath(entry.path).suffix.lower()) in suffix_map
    }
    return sorted(languages)


def _safe_json_object(content: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_toml_object(content: bytes) -> dict[str, Any]:
    try:
        parsed = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _package_dependency_names(package_data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        value = package_data.get(key)
        if isinstance(value, dict):
            names.update(str(name).lower() for name in value)
    return names


def _python_dependencies(pyproject: dict[str, Any]) -> set[str]:
    project = pyproject.get("project")
    if not isinstance(project, dict):
        return set()
    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list):
        return set()
    return {re.split(r"[\s\[<>=!~;]", str(item).lower(), maxsplit=1)[0] for item in dependencies}


def _frameworks_from_dependencies(dependencies: set[str]) -> set[str]:
    known = {
        "@angular/core": "Angular",
        "@playwright/test": "Playwright",
        "@storybook/react": "Storybook",
        "@testing-library/react": "Testing Library",
        "django": "Django",
        "fastapi": "FastAPI",
        "flask": "Flask",
        "jest": "Jest",
        "next": "Next.js",
        "nuxt": "Nuxt",
        "playwright": "Playwright",
        "pytest": "pytest",
        "react": "React",
        "svelte": "Svelte",
        "tailwindcss": "Tailwind CSS",
        "vite": "Vite",
        "vitest": "Vitest",
        "vue": "Vue",
    }
    return {label for name, label in known.items() if name in dependencies}


def _make_targets(text: str) -> list[str]:
    targets: set[str] = set()
    for line in text.splitlines():
        if line.startswith(("\t", " ", ".", "#")) or ":" not in line:
            continue
        target = line.split(":", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", target):
            targets.add(target)
    return sorted(targets)


def _safe_identifier(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_:@./-]{0,119}", value))


def _is_instruction_path(path: PurePosixPath) -> bool:
    name = path.name.lower()
    return name in _INSTRUCTION_NAMES or name.startswith("readme")


def _test_surfaces(entries: list[TreeEntry]) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    for entry in entries:
        path = PurePosixPath(entry.path)
        lowered = entry.path.lower()
        if any(
            marker in lowered
            for marker in (
                "/__tests__/",
                "/e2e/",
                "/tests/",
                ".spec.",
                ".test.",
                "playwright.config",
                "pytest.ini",
                "vitest.config",
                "jest.config",
            )
        ) or lowered.startswith(("tests/", "e2e/")):
            kind = (
                "configuration"
                if "config" in path.name.lower() or path.name == "pytest.ini"
                else "test_path"
            )
            surfaces.append({"kind": kind, "relative_path": entry.path})
    return surfaces[:100]


def _design_system_signals(entries: list[TreeEntry]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for entry in entries:
        lowered = entry.path.lower()
        signal: str | None = None
        if any(marker in lowered for marker in ("design-token", "design_token", "/tokens/")):
            signal = "design_tokens"
        elif any(marker in lowered for marker in ("/components/ui/", "/ui/components/")):
            signal = "ui_component_library"
        elif ".storybook/" in lowered or "storybook." in lowered:
            signal = "storybook"
        elif any(marker in lowered for marker in ("tailwind.config", "/theme.", "/themes/")):
            signal = "theme_configuration"
        if signal is not None:
            signals.append({"kind": signal, "relative_path": entry.path})
    return signals[:100]


def _unique_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[bytes] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = _canonical_json(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
