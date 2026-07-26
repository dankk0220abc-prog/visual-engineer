import subprocess
from pathlib import Path

import pytest

from repository_fixture import (
    committed_blob_hash,
    create_adversarial_repository,
    run_git,
)
from visual_engineer_api.core.config import Settings
from visual_engineer_api.repository_intelligence import (
    RepositoryScanError,
    RepositoryScanner,
)


def scanner(
    root: Path,
    *,
    repository_scan_max_files: int = 5000,
    repository_scan_max_total_bytes: int = 16 * 1024,
) -> RepositoryScanner:
    return RepositoryScanner(
        Settings(
            read_only_repository_roots=str(root),
            repository_scan_max_files=repository_scan_max_files,
            repository_scan_max_file_bytes=1024,
            repository_scan_max_total_bytes=repository_scan_max_total_bytes,
        )
    )


def test_scanner_reads_only_committed_objects_and_classifies_adversarial_content(
    tmp_path: Path,
) -> None:
    repository = create_adversarial_repository(tmp_path)
    before_status = run_git(repository, "status", "--porcelain=v1", "-uall")
    before_head = run_git(repository, "rev-parse", "HEAD")
    committed_dirty_hash = committed_blob_hash(repository, "src/dirty.txt")
    committed_package_hash = committed_blob_hash(repository, "package.json")

    result = scanner(tmp_path).scan(str(repository))

    assert result.source_revision == before_head
    assert result.branch_name == "main"
    assert result.repository_is_dirty is True
    assert result.dirty_path_count >= 2
    assert any(item["untracked"] for item in result.dirty_paths)
    assert result.package_manager == "pnpm"
    assert {"React", "Vite", "Vitest"}.issubset(result.tech_stack["frameworks"])
    assert any(
        item["kind"] == "package_script" and item["script"] == "preinstall"
        for item in result.available_scripts
    )
    assert not (repository / "lifecycle-ran").exists()
    assert not (repository / "dependency-ran").exists()
    assert not (repository / "dirty-lifecycle-ran").exists()

    rules = {item["rule_type"] for item in result.safety_findings}
    assert "environment_file" in rules
    assert "key_or_certificate_file" in rules
    assert "openai_token" in rules
    assert "symlink_not_followed" in rules
    assert "submodule_not_initialized" in rules
    assert "git_lfs_pointer_not_fetched" in rules
    assert "dependency_tree_skipped" in rules
    assert "file_byte_budget_exceeded" in rules
    assert "binary_content_skipped" in rules
    assert any(rule.startswith("prompt_injection_") for rule in rules)
    assert all(
        item["provenance"] == "untrusted_repository_content"
        for item in result.repository_instructions
    )

    manifest = {item["relative_path"]: item for item in result.manifest}
    assert manifest["escape-link"]["entry_type"] == "symlink"
    assert manifest["escape-link"]["selected"] is False
    assert manifest["escape-link"]["symlink_target_kind"] == "absolute"
    assert manifest[".env"]["skip_reason"] == "sensitive_path"
    assert "object_id" not in manifest[".env"]
    assert "size" not in manifest[".env"]
    assert manifest["fixture-private.key"]["skip_reason"] == "sensitive_path"
    assert "object_id" not in manifest["fixture-private.key"]
    assert "size" not in manifest["fixture-private.key"]
    assert manifest["README-secret.md"]["skip_reason"] == "secret_content"
    assert "object_id" not in manifest["README-secret.md"]
    assert "size" not in manifest["README-secret.md"]
    assert manifest["package.json"]["content_sha256"] == committed_package_hash
    assert (
        manifest["src/dirty.txt"]["content_sha256"] == committed_dirty_hash
        if manifest["src/dirty.txt"]["selected"]
        else True
    )

    serialized = repr(result.model_values())
    assert "fixture-not-a-secret" not in serialized
    assert "dirty-worktree-content-must-not-be-read" not in serialized
    assert "worktree-only-marker" not in serialized
    assert "untracked-content-must-not-be-read" not in serialized
    assert "outside-symlink-content-must-not-be-read" not in serialized
    assert "sk-" + ("A" * 24) not in serialized
    assert run_git(repository, "rev-parse", "HEAD") == before_head
    assert run_git(repository, "status", "--porcelain=v1", "-uall") == before_status


def test_fingerprint_is_stable_for_same_head_despite_worktree_content_changes(
    tmp_path: Path,
) -> None:
    repository = create_adversarial_repository(tmp_path)
    first = scanner(tmp_path).scan(str(repository))

    (repository / "src/dirty.txt").write_text("different dirty bytes\n", encoding="utf-8")
    (repository / "untracked.txt").write_text("different untracked bytes\n", encoding="utf-8")
    second = scanner(tmp_path).scan(str(repository))

    assert second.fingerprint == first.fingerprint
    assert second.source_revision == first.source_revision


def test_scanner_rejects_traversal_outside_allowlist_and_symlink_root(
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    repository = create_adversarial_repository(allowed)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_repository = create_adversarial_repository(outside)

    with pytest.raises(RepositoryScanError) as traversal:
        scanner(allowed).scan(str(allowed / ".." / "outside" / outside_repository.name))
    assert traversal.value.code == "repository_outside_allowlist"

    link = allowed / "repository-link"
    link.symlink_to(repository)
    with pytest.raises(RepositoryScanError) as symlink:
        scanner(allowed).scan(str(link))
    assert symlink.value.code == "repository_symlink_root_denied"

    with pytest.raises(RepositoryScanError) as network:
        scanner(allowed).scan("https://example.invalid/repository.git")
    assert network.value.code == "repository_path_invalid"


def test_scanner_fails_closed_on_file_budget(tmp_path: Path) -> None:
    repository = create_adversarial_repository(tmp_path)
    with pytest.raises(RepositoryScanError) as error:
        scanner(tmp_path, repository_scan_max_files=1).scan(str(repository))
    assert error.value.code == "repository_file_budget_exceeded"


def test_scanner_truncates_at_total_selected_byte_budget(tmp_path: Path) -> None:
    repository = create_adversarial_repository(tmp_path)
    (repository / "README-a.md").write_text("a" * 700, encoding="utf-8")
    (repository / "README-b.md").write_text("b" * 700, encoding="utf-8")
    run_git(repository, "add", "README-a.md", "README-b.md")
    run_git(repository, "commit", "-m", "fixture: add total-budget candidates")

    result = scanner(tmp_path, repository_scan_max_total_bytes=1024).scan(str(repository))

    assert result.total_selected_bytes <= 1024
    assert any(
        finding["rule_type"] == "total_byte_budget_exceeded" for finding in result.safety_findings
    )


def test_scanner_bounds_symlink_target_metadata(tmp_path: Path) -> None:
    repository = create_adversarial_repository(tmp_path)
    payload = repository / "oversized-symlink-target"
    payload.write_text("x" * 2048, encoding="utf-8")
    object_id = run_git(repository, "hash-object", "-w", payload.name)
    payload.unlink()
    run_git(
        repository,
        "update-index",
        "--add",
        "--cacheinfo",
        f"120000,{object_id},oversized-link",
    )
    run_git(repository, "commit", "-m", "fixture: add oversized symlink metadata")

    result = scanner(tmp_path).scan(str(repository))

    manifest = {item["relative_path"]: item for item in result.manifest}
    assert manifest["oversized-link"]["symlink_target_kind"] == "metadata_budget_exceeded"
    assert "symlink_target_hash" not in manifest["oversized-link"]
    assert any(
        finding["rule_type"] == "symlink_metadata_budget_exceeded"
        for finding in result.safety_findings
    )


def test_scanner_returns_stable_timeout_without_internal_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = create_adversarial_repository(tmp_path)

    def expire(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(cmd=["git"], timeout=0.1)

    monkeypatch.setattr(subprocess, "run", expire)
    with pytest.raises(RepositoryScanError) as error:
        scanner(tmp_path).scan(str(repository))
    assert error.value.code == "repository_scan_timeout"
    assert str(tmp_path) not in error.value.public_message
