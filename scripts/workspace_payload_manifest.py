import argparse
import hashlib
import json
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "visualengineer-workspace-payload-manifest-v1"
EMPTY_CONTENT_DIGEST = hashlib.sha256(b"").hexdigest()
DIAGNOSTIC_ENTRY_LIMIT = 20


class UnsupportedWorkspaceEntryError(ValueError):
    """Raised when a workspace entry is not a directory, file, or symlink."""


class WorkspaceSnapshotChangedError(RuntimeError):
    """Raised when the workspace changes while a manifest is being built."""


@dataclass(frozen=True)
class _Snapshot:
    manifest: dict[str, Any]
    metadata: dict[str, tuple[int, int, int, int, int, int]]


def _entry_type(mode: int) -> str:
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISCHR(mode):
        return "character-device"
    if stat.S_ISBLK(mode):
        return "block-device"
    return "unknown"


def _metadata_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _snapshot_changed(relative_path: str, stage: str, reason: str) -> WorkspaceSnapshotChangedError:
    return WorkspaceSnapshotChangedError(
        f"Workspace snapshot changed: path={relative_path!r}; stage={stage}; reason={reason}"
    )


def _require_same_metadata(
    expected: os.stat_result,
    actual: os.stat_result,
    relative_path: str,
    stage: str,
) -> None:
    if _metadata_signature(expected) != _metadata_signature(actual):
        raise _snapshot_changed(relative_path, stage, "metadata-mismatch")


def _lstat(
    name: bytes | Path,
    directory_descriptor: int | None,
    relative_path: str,
    stage: str,
) -> os.stat_result:
    try:
        if directory_descriptor is None:
            return os.lstat(name)
        return os.lstat(name, dir_fd=directory_descriptor)
    except OSError:
        raise _snapshot_changed(relative_path, stage, "lstat-failed") from None


def _fstat(descriptor: int, relative_path: str, stage: str) -> os.stat_result:
    try:
        return os.fstat(descriptor)
    except OSError:
        raise _snapshot_changed(relative_path, stage, "fstat-failed") from None


def _directory_entry_names(
    descriptor: int, relative_path: str, exclude_top_level_git: bool
) -> tuple[bytes, ...]:
    try:
        with os.scandir(descriptor) as scanner:
            names = [os.fsencode(entry.name) for entry in scanner]
    except OSError:
        raise _snapshot_changed(relative_path, "directory-scan", "scandir-failed") from None
    if exclude_top_level_git:
        names = [name for name in names if name != b".git"]
    return tuple(sorted(names))


def _relative_child(relative_directory: str, name: bytes) -> str:
    decoded_name = os.fsdecode(name)
    if relative_directory == ".":
        return decoded_name
    return f"{relative_directory}/{decoded_name}"


def _file_digest(
    directory_descriptor: int,
    name: bytes,
    relative_path: str,
    pre_metadata: os.stat_result,
) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_descriptor)
    except OSError:
        raise _snapshot_changed(relative_path, "file-open", "open-failed") from None
    try:
        descriptor_pre = _fstat(descriptor, relative_path, "file-descriptor-pre")
        _require_same_metadata(pre_metadata, descriptor_pre, relative_path, "file-descriptor-pre")
        if not stat.S_ISREG(descriptor_pre.st_mode):
            raise _snapshot_changed(relative_path, "file-descriptor-pre", "type-mismatch")

        digest = hashlib.sha256()
        try:
            while block := os.read(descriptor, 64 * 1024):
                digest.update(block)
        except OSError:
            raise _snapshot_changed(relative_path, "file-read", "read-failed") from None

        descriptor_post = _fstat(descriptor, relative_path, "file-descriptor-post")
        _require_same_metadata(
            descriptor_pre, descriptor_post, relative_path, "file-descriptor-post"
        )
    finally:
        os.close(descriptor)

    pathname_post = _lstat(name, directory_descriptor, relative_path, "file-pathname-post")
    _require_same_metadata(pre_metadata, pathname_post, relative_path, "file-pathname-post")
    return digest.hexdigest()


def _logical_size(entry_type: str, metadata: os.stat_result, symlink_target: bytes | None) -> int:
    if entry_type == "file":
        return metadata.st_size
    if entry_type == "symlink":
        assert symlink_target is not None
        return len(symlink_target)
    return 0


def _scan_directory(
    directory_descriptor: int,
    relative_directory: str,
    directory_pre: os.stat_result,
    entries: list[dict[str, Any]],
    metadata_by_path: dict[str, tuple[int, int, int, int, int, int]],
    *,
    is_root: bool,
) -> None:
    descriptor_pre = _fstat(directory_descriptor, relative_directory, "directory-descriptor-pre")
    _require_same_metadata(
        directory_pre, descriptor_pre, relative_directory, "directory-descriptor-pre"
    )
    if not stat.S_ISDIR(descriptor_pre.st_mode):
        raise _snapshot_changed(relative_directory, "directory-descriptor-pre", "type-mismatch")
    metadata_by_path[relative_directory] = _metadata_signature(descriptor_pre)

    initial_names = _directory_entry_names(directory_descriptor, relative_directory, is_root)
    for name in initial_names:
        relative_path = _relative_child(relative_directory, name)
        entry_pre = _lstat(name, directory_descriptor, relative_path, "entry-pre")
        entry_type = _entry_type(entry_pre.st_mode)
        if entry_type not in {"directory", "file", "symlink"}:
            raise UnsupportedWorkspaceEntryError(
                "Unsupported workspace entry: "
                f"path={relative_path!r}; type={entry_type}; "
                f"mode={stat.S_IFMT(entry_pre.st_mode):#o}; stage=entry-classification"
            )

        symlink_target: bytes | None = None
        entry: dict[str, Any] = {
            "type": entry_type,
            "mode": f"{stat.S_IMODE(entry_pre.st_mode):04o}",
            "path": relative_path,
            "size": 0,
        }
        if entry_type == "file":
            entry["size"] = _logical_size(entry_type, entry_pre, None)
            entry["content_sha256"] = _file_digest(
                directory_descriptor, name, relative_path, entry_pre
            )
            metadata_by_path[relative_path] = _metadata_signature(entry_pre)
        elif entry_type == "symlink":
            try:
                target = os.readlink(name, dir_fd=directory_descriptor)
            except OSError:
                raise _snapshot_changed(
                    relative_path, "symlink-readlink", "readlink-failed"
                ) from None
            symlink_target = os.fsencode(target)
            symlink_post = _lstat(
                name, directory_descriptor, relative_path, "symlink-pathname-post"
            )
            _require_same_metadata(entry_pre, symlink_post, relative_path, "symlink-pathname-post")
            entry["size"] = _logical_size(entry_type, entry_pre, symlink_target)
            entry["symlink_target"] = os.fsdecode(symlink_target)
            metadata_by_path[relative_path] = _metadata_signature(entry_pre)
        else:
            entry["content_sha256"] = EMPTY_CONTENT_DIGEST

        entries.append(entry)
        if entry_type == "directory":
            flags = (
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_DIRECTORY", 0)
            )
            try:
                child_descriptor = os.open(name, flags, dir_fd=directory_descriptor)
            except OSError:
                raise _snapshot_changed(relative_path, "directory-open", "open-failed") from None
            try:
                _scan_directory(
                    child_descriptor,
                    relative_path,
                    entry_pre,
                    entries,
                    metadata_by_path,
                    is_root=False,
                )
            finally:
                os.close(child_descriptor)
            directory_path_post = _lstat(
                name, directory_descriptor, relative_path, "directory-pathname-post"
            )
            _require_same_metadata(
                entry_pre, directory_path_post, relative_path, "directory-pathname-post"
            )

    final_names = _directory_entry_names(directory_descriptor, relative_directory, is_root)
    if initial_names != final_names:
        raise _snapshot_changed(relative_directory, "directory-entry-rescan", "entry-set-mismatch")
    descriptor_post = _fstat(directory_descriptor, relative_directory, "directory-descriptor-post")
    _require_same_metadata(
        descriptor_pre, descriptor_post, relative_directory, "directory-descriptor-post"
    )


def _build_snapshot(resolved_root: Path) -> _Snapshot:
    root_pre = _lstat(resolved_root, None, ".", "root-pre")
    if not stat.S_ISDIR(root_pre.st_mode):
        raise ValueError("Workspace payload manifest root must be a directory")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_DIRECTORY", 0)
    )
    try:
        root_descriptor = os.open(resolved_root, flags)
    except OSError:
        raise _snapshot_changed(".", "root-open", "open-failed") from None
    entries: list[dict[str, Any]] = []
    metadata_by_path: dict[str, tuple[int, int, int, int, int, int]] = {}
    try:
        _scan_directory(
            root_descriptor,
            ".",
            root_pre,
            entries,
            metadata_by_path,
            is_root=True,
        )
    finally:
        os.close(root_descriptor)
    root_post = _lstat(resolved_root, None, ".", "root-post")
    _require_same_metadata(root_pre, root_post, ".", "root-post")

    entries.sort(key=lambda entry: os.fsencode(entry["path"]))
    return _Snapshot(
        manifest={"schema": SCHEMA, "entries": entries},
        metadata=metadata_by_path,
    )


def build_manifest(root: Path) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    first = _build_snapshot(resolved_root)
    second = _build_snapshot(resolved_root)
    if (
        canonical_manifest_bytes(first.manifest) != canonical_manifest_bytes(second.manifest)
        or first.metadata != second.metadata
    ):
        raise _snapshot_changed(".", "global-snapshot-compare", "snapshot-mismatch")
    return first.manifest


def canonical_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (
        json.dumps(manifest, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        + b"\n"
    )


def write_manifest(root: Path, output: Path) -> None:
    resolved_root = root.resolve(strict=True)
    resolved_output_parent = output.parent.resolve(strict=True)
    resolved_output = resolved_output_parent / output.name
    if resolved_output == resolved_root or resolved_root in resolved_output.parents:
        raise ValueError("Workspace payload manifest output must be outside the workspace root")

    payload = canonical_manifest_bytes(build_manifest(resolved_root))
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=resolved_output_parent,
            prefix=f".{output.name}.",
            delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary_path, resolved_output)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or not isinstance(manifest.get("entries"), list):
        raise ValueError("Unsupported workspace payload manifest")
    seen_paths: set[str] = set()
    for entry in manifest["entries"]:
        relative_path = entry.get("path")
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or relative_path.startswith("/")
            or relative_path in seen_paths
        ):
            raise ValueError("Workspace payload manifest contains an invalid path")
        seen_paths.add(relative_path)
    return manifest


def manifest_digest(path: Path) -> str:
    payload = path.read_bytes()
    load_manifest(path)
    return hashlib.sha256(payload).hexdigest()


def manifest_differences(
    expected: dict[str, Any], actual: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[tuple[dict[str, Any], dict[str, Any]]]]:
    expected_by_path = {entry["path"]: entry for entry in expected["entries"]}
    actual_by_path = {entry["path"]: entry for entry in actual["entries"]}
    added_paths = sorted(actual_by_path.keys() - expected_by_path.keys(), key=os.fsencode)
    removed_paths = sorted(expected_by_path.keys() - actual_by_path.keys(), key=os.fsencode)
    common_paths = sorted(expected_by_path.keys() & actual_by_path.keys(), key=os.fsencode)
    added = [actual_by_path[path] for path in added_paths]
    removed = [expected_by_path[path] for path in removed_paths]
    changed = [
        (expected_by_path[path], actual_by_path[path])
        for path in common_paths
        if expected_by_path[path] != actual_by_path[path]
    ]
    return added, removed, changed


def _diagnostic_entry(entry: dict[str, Any]) -> dict[str, Any]:
    diagnostic = {
        "path": entry["path"],
        "type": entry["type"],
        "mode": entry["mode"],
        "size": entry["size"],
    }
    if entry["type"] == "symlink":
        target_bytes = os.fsencode(entry["symlink_target"])
        diagnostic["symlink_target_type"] = "bytes"
        diagnostic["symlink_target_byte_length"] = len(target_bytes)
        diagnostic["symlink_target_sha256"] = hashlib.sha256(target_bytes).hexdigest()
    else:
        diagnostic["content_sha256"] = entry["content_sha256"]
    return diagnostic


def print_mismatch(
    expected_path: Path,
    actual_path: Path,
    check_name: str,
    workspace_root: Path,
) -> bool:
    expected = load_manifest(expected_path)
    actual = load_manifest(actual_path)
    expected_digest = manifest_digest(expected_path)
    actual_digest = manifest_digest(actual_path)
    if expected_digest == actual_digest:
        return False

    added, removed, changed = manifest_differences(expected, actual)
    diagnostic_total_count = len(added) + len(removed) + len(changed)
    summary = {
        "check": check_name,
        "expected_digest": expected_digest,
        "actual_digest": actual_digest,
        "workspace_root": str(workspace_root.resolve(strict=True)),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "diagnostic_limit": DIAGNOSTIC_ENTRY_LIMIT,
        "diagnostic_total_count": diagnostic_total_count,
        "diagnostic_omitted_count": max(0, diagnostic_total_count - DIAGNOSTIC_ENTRY_LIMIT),
    }
    print(
        "E2E_WORKSPACE_MANIFEST_MISMATCH " + json.dumps(summary, ensure_ascii=True, sort_keys=True)
    )
    diagnostics: list[tuple[str, dict[str, Any]]] = []
    diagnostics.extend(("ADDED", _diagnostic_entry(entry)) for entry in added)
    diagnostics.extend(("REMOVED", _diagnostic_entry(entry)) for entry in removed)
    for old_entry, new_entry in changed:
        diagnostics.append(
            (
                "CHANGED",
                {
                    "path": old_entry["path"],
                    "old": {
                        key: value
                        for key, value in _diagnostic_entry(old_entry).items()
                        if key != "path"
                    },
                    "new": {
                        key: value
                        for key, value in _diagnostic_entry(new_entry).items()
                        if key != "path"
                    },
                },
            )
        )
    for label, diagnostic in diagnostics[:DIAGNOSTIC_ENTRY_LIMIT]:
        print(
            f"E2E_WORKSPACE_MANIFEST_{label} "
            + json.dumps(diagnostic, ensure_ascii=True, sort_keys=True)
        )
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("root", type=Path)
    write_parser.add_argument("output", type=Path)

    digest_parser = subparsers.add_parser("digest")
    digest_parser.add_argument("manifest", type=Path)

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("expected", type=Path)
    compare_parser.add_argument("actual", type=Path)
    compare_parser.add_argument("--check-name", required=True)
    compare_parser.add_argument("--workspace-root", required=True, type=Path)

    arguments = parser.parse_args()
    if arguments.command == "write":
        write_manifest(arguments.root, arguments.output)
    elif arguments.command == "digest":
        print(manifest_digest(arguments.manifest))
    elif print_mismatch(
        arguments.expected,
        arguments.actual,
        arguments.check_name,
        arguments.workspace_root,
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
