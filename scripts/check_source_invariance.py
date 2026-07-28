from __future__ import annotations

import hashlib
import json
import os
import shlex
import stat
import subprocess
import tempfile
import threading
import uuid
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from visual_engineer_runner.config import LocalRepositoryConfig, RunnerSettings
from visual_engineer_runner.workspace_manager import WorkspaceManager
from visual_engineer_runner_protocol import (
    ExecutionGrantPolicy,
    SideEffectPermit,
    WorkspaceDiffJobSpec,
    WorkspaceDiscardJobSpec,
    WorkspaceJobSpec,
    WorkspaceOperation,
    WorkspacePrepareJobSpec,
    WorkspaceRollbackJobSpec,
    WorkspaceWriteMode,
    WorkspaceWriteTextJobSpec,
    compute_execution_grant_policy_hash,
    compute_side_effect_job_digest,
    compute_side_effect_permit_digest,
    side_effect_job_binding,
)

_HANDLE = "source-invariance-fixture-v1"
_RUNNER_ID = uuid.UUID("7c74c9a1-cd77-5384-bf61-b485f69be1a6")
_EXPECTED_STATUS = b" M sandbox/tracked.txt\x00?? sandbox/untracked.txt\x00"


def _run_git(repository: Path, *arguments: str) -> bytes:
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": os.fspath(repository.parent),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    completed = subprocess.run(
        ["git", "-C", os.fspath(repository), *arguments],
        check=True,
        capture_output=True,
        env=environment,
    )
    return completed.stdout


def _write_probe(path: Path, marker: Path) -> None:
    path.write_text(
        f"#!/bin/sh\ntouch {shlex.quote(os.fspath(marker))}\nexit 1\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


def _create_fixture(root: Path) -> tuple[Path, str, bytes, list[str], list[str], Path]:
    source = root / "source"
    submodule = root / "submodule-origin"
    marker_root = root / "extension-markers"
    source.mkdir()
    submodule.mkdir()
    marker_root.mkdir()

    _run_git(submodule, "init", "-b", "main")
    _run_git(submodule, "config", "user.name", "Source Invariance Fixture")
    _run_git(submodule, "config", "user.email", "fixture@example.invalid")
    (submodule / "README.md").write_text("nested fixture\n", encoding="utf-8")
    _run_git(submodule, "add", "README.md")
    _run_git(submodule, "commit", "-m", "nested fixture")

    _run_git(source, "init", "-b", "main")
    _run_git(source, "config", "user.name", "Source Invariance Fixture")
    _run_git(source, "config", "user.email", "fixture@example.invalid")
    (source / "sandbox").mkdir()
    (source / "sandbox" / "tracked.txt").write_text("committed\n", encoding="utf-8")
    (source / "sandbox" / "filter.txt").write_text("filter fixture\n", encoding="utf-8")
    (source / "sandbox" / "lfs.bin").write_text("lfs fixture\n", encoding="utf-8")
    (source / ".gitattributes").write_text(
        "sandbox/filter.txt filter=visual-engineer-probe diff=visual-engineer-probe\n"
        "sandbox/lfs.bin filter=lfs diff=lfs merge=lfs -text\n",
        encoding="utf-8",
    )
    (source / ".gitignore").write_text("sandbox/ignored.txt\n", encoding="utf-8")
    _run_git(
        source,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        os.fspath(submodule),
        "vendor/submodule",
    )
    _run_git(source, "add", ".gitattributes", ".gitignore", "sandbox")
    _run_git(source, "commit", "-m", "source invariance fixture")
    revision = _run_git(source, "rev-parse", "HEAD").decode("ascii").strip()
    tracked_paths = _run_git(source, "ls-files", "-z").decode("utf-8").split("\0")
    tracked_paths = [path for path in tracked_paths if path]

    (source / "sandbox" / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    (source / "sandbox" / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    (source / "sandbox" / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    actual_status = _run_git(
        source,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=no",
        "--no-renames",
    )
    if actual_status != _EXPECTED_STATUS:
        raise RuntimeError(f"Unexpected synthetic status fixture: {actual_status!r}")

    helpers: dict[str, Path] = {}
    for name in (
        "credential",
        "diff",
        "filter-clean",
        "filter-smudge",
        "fsmonitor",
        "lfs-smudge",
        "submodule-update",
    ):
        helper = root / f"probe-{name}.sh"
        _write_probe(helper, marker_root / name)
        helpers[name] = helper
    hook = source / ".git" / "hooks" / "post-checkout"
    _write_probe(hook, marker_root / "post-checkout")
    with (source / ".git" / "config").open("a", encoding="utf-8") as config:
        config.write(
            "\n[core]\n"
            f"\tfsmonitor = {helpers['fsmonitor']}\n"
            "[credential]\n"
            f"\thelper = !{helpers['credential']}\n"
            '[diff "visual-engineer-probe"]\n'
            f"\tcommand = {helpers['diff']}\n"
            '[filter "visual-engineer-probe"]\n'
            f"\tclean = {helpers['filter-clean']}\n"
            f"\tsmudge = {helpers['filter-smudge']}\n"
            "\trequired = true\n"
            '[filter "lfs"]\n'
            f"\tsmudge = {helpers['lfs-smudge']}\n"
            "\trequired = true\n"
            '[submodule "vendor/submodule"]\n'
            f"\tupdate = !{helpers['submodule-update']}\n"
            '[url "https://network.invalid/"]\n'
            "\tinsteadOf = source-invariance-network:\n"
        )

    return (
        source,
        revision,
        actual_status,
        tracked_paths,
        ["sandbox/untracked.txt", "sandbox/ignored.txt"],
        marker_root,
    )


def _entry(path: Path) -> dict[str, Any]:
    metadata = os.lstat(path)
    value: dict[str, Any] = {
        "mode": metadata.st_mode,
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "nlink": metadata.st_nlink,
        "size": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
        "ctime_ns": metadata.st_ctime_ns,
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
    }
    if stat.S_ISREG(metadata.st_mode):
        value["kind"] = "file"
        value["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif stat.S_ISDIR(metadata.st_mode):
        value["kind"] = "directory"
    elif stat.S_ISLNK(metadata.st_mode):
        value["kind"] = "symlink"
        value["target"] = os.readlink(path)
    else:
        value["kind"] = "special"
    return value


def _manifest(root: Path) -> dict[str, dict[str, Any]]:
    result = {".": _entry(root)}

    def walk(directory: Path) -> None:
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda item: os.fsencode(item.name))
        for directory_entry in entries:
            path = Path(directory_entry.path)
            relative_path = path.relative_to(root).as_posix()
            result[relative_path] = _entry(path)
            if directory_entry.is_dir(follow_symlinks=False):
                walk(path)

    walk(root)
    return result


def _hash_paths(root: Path, paths: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative_path in paths:
        path = root / relative_path
        metadata = os.lstat(path)
        if stat.S_ISREG(metadata.st_mode):
            result[relative_path] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif stat.S_ISDIR(metadata.st_mode):
            result[relative_path] = "gitlink-directory"
        else:
            result[relative_path] = f"mode:{metadata.st_mode}"
    return result


def _direct_git_state(source: Path) -> dict[str, Any]:
    git_directory = source / ".git"
    head = (git_directory / "HEAD").read_bytes()
    reference = head.decode("ascii").strip().removeprefix("ref: ")
    reference_path = git_directory.joinpath(*reference.split("/"))
    refs = {
        path.relative_to(git_directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((git_directory / "refs").rglob("*"))
        if path.is_file() and not path.is_symlink()
    }
    object_inventory = {
        path.relative_to(git_directory / "objects").as_posix(): {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "device": path.stat(follow_symlinks=False).st_dev,
            "inode": path.stat(follow_symlinks=False).st_ino,
        }
        for path in sorted((git_directory / "objects").rglob("*"))
        if path.is_file() and not path.is_symlink()
    }
    return {
        "head": head,
        "branch": reference,
        "revision": reference_path.read_bytes(),
        "refs": refs,
        "config": (git_directory / "config").read_bytes(),
        "hooks": _manifest(git_directory / "hooks"),
        "index": (git_directory / "index").read_bytes(),
        "objects": object_inventory,
    }


def _known_status(source: Path) -> bytes:
    if (source / "sandbox" / "tracked.txt").read_bytes() != b"dirty\n":
        raise RuntimeError("Synthetic tracked dirty state changed")
    if (source / "sandbox" / "untracked.txt").read_bytes() != b"untracked\n":
        raise RuntimeError("Synthetic untracked state changed")
    if (source / "sandbox" / "ignored.txt").read_bytes() != b"ignored\n":
        raise RuntimeError("Synthetic ignored state changed")
    return _EXPECTED_STATUS


def _grant(revision: str) -> ExecutionGrantPolicy:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "run_id": uuid.uuid4(),
        "plan_id": uuid.uuid4(),
        "repository_handle_id": uuid.uuid4(),
        "repository_opaque_handle": _HANDLE,
        "source_revision": revision,
        "snapshot_fingerprint": hashlib.sha256(b"source-invariance").hexdigest(),
        "allowed_operations": list(WorkspaceOperation),
        "allowed_paths": ["sandbox/**"],
        "denied_paths": [".git", ".git/**", ".env", ".env.*", "**/.env", "**/.env.*"],
        "max_files_changed": 8,
        "max_total_write_bytes": 128 * 1024,
        "max_single_file_bytes": 32 * 1024,
        "max_diff_bytes": 32 * 1024,
        "workspace_ttl_seconds": 20 * 60,
        "expires_at": datetime.now(UTC) + timedelta(minutes=10),
        "policy_hash": "0" * 64,
    }
    draft = ExecutionGrantPolicy.model_validate(values)
    values["policy_hash"] = compute_execution_grant_policy_hash(draft)
    return ExecutionGrantPolicy.model_validate(values)


def _permit(
    manager: WorkspaceManager,
    spec: WorkspaceJobSpec,
    operation_id: uuid.UUID,
) -> SideEffectPermit:
    binding = side_effect_job_binding(spec)
    expected_current = binding["expected_current"]
    if expected_current is None:
        registry = manager._load_registry(spec.workspace_id)
        if registry is None:
            raise RuntimeError("Synthetic registry is unavailable")
        expected_current = registry.current_tree_hash
    now = datetime.now(UTC)
    values: dict[str, Any] = {
        "id": uuid.uuid5(operation_id, "source-invariance-permit"),
        "sequence": 1,
        "runner_id": _RUNNER_ID,
        "job_id": operation_id,
        "attempt_id": uuid.uuid5(operation_id, "source-invariance-attempt"),
        "lease_id": uuid.uuid5(operation_id, "source-invariance-lease"),
        "grant_id": spec.execution_grant.id,
        "workspace_id": spec.workspace_id,
        "repository_handle_id": spec.execution_grant.repository_handle_id,
        "operation": binding["operation"],
        "relative_path": binding["relative_path"],
        "expected_current": expected_current,
        "proposed_digest": binding["proposed_digest"],
        "job_digest": compute_side_effect_job_digest(spec),
        "operation_digest": "0" * 64,
        "policy_hash": spec.execution_grant.policy_hash,
        "source_revision": spec.execution_grant.source_revision,
        "issued_at": now,
        "consumed_at": now,
        "expires_at": now + timedelta(seconds=60),
        "state": "consumed",
    }
    values["operation_digest"] = compute_side_effect_permit_digest(values)
    return SideEffectPermit.model_validate(values)


def _execute(manager: WorkspaceManager, spec: WorkspaceJobSpec) -> Any:
    operation_id = uuid.uuid4()
    side_effect_permit = None
    if isinstance(
        spec,
        (
            WorkspacePrepareJobSpec,
            WorkspaceWriteTextJobSpec,
            WorkspaceRollbackJobSpec,
            WorkspaceDiscardJobSpec,
        ),
    ):
        side_effect_permit = _permit(manager, spec, operation_id)
    return manager.execute(
        spec,
        operation_id=operation_id,
        cancel_event=threading.Event(),
        side_effect_permit=side_effect_permit,
    )


def _assert_independent_objects(
    source: Path,
    mirror: Path,
    source_state: dict[str, Any],
) -> None:
    checked = 0
    for relative_path, source_object in source_state["objects"].items():
        mirror_object = mirror / "objects" / relative_path
        if not mirror_object.is_file():
            continue
        mirror_metadata = mirror_object.stat(follow_symlinks=False)
        if (
            mirror_metadata.st_dev == source_object["device"]
            and mirror_metadata.st_ino == source_object["inode"]
        ):
            raise RuntimeError("Runner mirror aliases a source Git object inode")
        source_path = source / ".git" / "objects" / relative_path
        if zlib.decompress(mirror_object.read_bytes()) != zlib.decompress(source_path.read_bytes()):
            raise RuntimeError("Runner mirror object differs from the source object")
        checked += 1
        if checked == 8:
            break
    if checked == 0:
        raise RuntimeError(f"No independent mirror objects found for {source.name}")
    for alternate in (
        mirror / "objects" / "info" / "alternates",
        mirror / "objects" / "info" / "http-alternates",
    ):
        if alternate.exists() or alternate.is_symlink():
            raise RuntimeError("Runner mirror contains a prohibited object alternate")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="visualengineer-source-invariance-") as temporary:
        root = Path(temporary)
        (
            source,
            revision,
            status_before,
            tracked_paths,
            untracked_paths,
            marker_root,
        ) = _create_fixture(root)
        manifest_before = _manifest(source)
        git_before = _direct_git_state(source)
        tracked_before = _hash_paths(source, tracked_paths)
        untracked_before = _hash_paths(source, untracked_paths)

        state = root / "runner-state"
        settings = RunnerSettings(
            credential_path=state / "credentials" / "credential.json",
            repository_handles={
                _HANDLE: LocalRepositoryConfig(
                    path=source,
                    display_name="Source Invariance Synthetic Fixture",
                )
            },
            mirror_root=state / "mirrors",
            workspace_root=state / "workspaces",
            registry_root=state / "registry",
            require_source_read_only=False,
        )
        manager = WorkspaceManager(settings)
        registrations = manager.registration_requests(_RUNNER_ID)
        if len(registrations) != 1 or registrations[0].current_revision != revision:
            raise RuntimeError("Synthetic source registration did not preserve HEAD")

        grant = _grant(revision)
        workspace_id = uuid.uuid4()
        _execute(
            manager,
            WorkspacePrepareJobSpec(workspace_id=workspace_id, execution_grant=grant),
        )
        workspace = settings.workspace_root / f"workspace-{workspace_id.hex}"
        _execute(
            manager,
            WorkspaceWriteTextJobSpec(
                workspace_id=workspace_id,
                execution_grant=grant,
                mode=WorkspaceWriteMode.REPLACE,
                relative_path="sandbox/tracked.txt",
                content="isolated replacement\n",
                expected_sha256=hashlib.sha256(b"committed\n").hexdigest(),
            ),
        )
        _execute(
            manager,
            WorkspaceDiffJobSpec(workspace_id=workspace_id, execution_grant=grant),
        )
        _execute(
            manager,
            WorkspaceRollbackJobSpec(workspace_id=workspace_id, execution_grant=grant),
        )
        mirror = manager._git.mirror_path(_HANDLE)
        _assert_independent_objects(source, mirror, git_before)
        _execute(
            manager,
            WorkspaceDiscardJobSpec(workspace_id=workspace_id, execution_grant=grant),
        )
        if workspace.exists() or workspace.is_symlink():
            raise RuntimeError("Synthetic isolated workspace survived discard")

        manifest_after = _manifest(source)
        git_after = _direct_git_state(source)
        tracked_after = _hash_paths(source, tracked_paths)
        untracked_after = _hash_paths(source, untracked_paths)
        status_after = _known_status(source)
        if any(marker_root.iterdir()):
            raise RuntimeError("A source-controlled Git extension executed")
        if manifest_after != manifest_before:
            changed = sorted(
                set(manifest_before) ^ set(manifest_after)
                | {
                    path
                    for path in set(manifest_before) & set(manifest_after)
                    if manifest_before[path] != manifest_after[path]
                }
            )
            raise RuntimeError(f"Source manifest changed: {changed[:20]}")
        if git_after != git_before:
            raise RuntimeError(
                "Source Git branch, HEAD, refs, config, hooks, index, or objects changed"
            )
        if tracked_after != tracked_before or untracked_after != untracked_before:
            raise RuntimeError("Source tracked or untracked content hashes changed")
        if status_after != status_before:
            raise RuntimeError("Source status porcelain changed")

        print(
            json.dumps(
                {
                    "branch": "main",
                    "extension_markers": 0,
                    "source_entries_compared": len(manifest_before),
                    "source_git_objects_compared": len(git_before["objects"]),
                    "source_status_records": 2,
                    "status": "PASS",
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
