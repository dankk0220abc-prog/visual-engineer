import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

SCHEMA = "visualengineer-workspace-payload-manifest-v1"
EMPTY_CONTENT_DIGEST = hashlib.sha256(b"").hexdigest()


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


def _file_digest(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError(f"Manifest entry changed type while reading: {path.name!r}")
        digest = hashlib.sha256()
        while block := os.read(descriptor, 64 * 1024):
            digest.update(block)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _logical_size(entry_type: str, metadata: os.stat_result, symlink_target: str | None) -> int:
    if entry_type == "file":
        return metadata.st_size
    if entry_type == "symlink":
        assert symlink_target is not None
        return len(os.fsencode(symlink_target))
    return 0


def build_manifest(root: Path) -> dict[str, Any]:
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise ValueError("Workspace payload manifest root must be a directory")

    entries: list[dict[str, Any]] = []
    pending = [resolved_root]
    while pending:
        directory = pending.pop()
        children = list(os.scandir(directory))
        children.sort(key=lambda child: os.fsencode(child.name), reverse=True)
        for child in children:
            if directory == resolved_root and os.fsencode(child.name) == b".git":
                continue

            path = Path(child.path)
            relative_path = path.relative_to(resolved_root).as_posix()
            metadata = child.stat(follow_symlinks=False)
            entry_type = _entry_type(metadata.st_mode)
            symlink_target = os.readlink(path) if entry_type == "symlink" else None
            entry: dict[str, Any] = {
                "type": entry_type,
                "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                "path": relative_path,
                "size": _logical_size(entry_type, metadata, symlink_target),
            }
            if entry_type == "file":
                entry["content_sha256"] = _file_digest(path)
            elif entry_type == "symlink":
                entry["symlink_target"] = symlink_target
            else:
                entry["content_sha256"] = EMPTY_CONTENT_DIGEST
            entries.append(entry)
            if entry_type == "directory":
                pending.append(path)

    entries.sort(key=lambda entry: os.fsencode(entry["path"]))
    return {"schema": SCHEMA, "entries": entries}


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
        diagnostic["symlink_target"] = entry["symlink_target"]
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
    summary = {
        "check": check_name,
        "expected_digest": expected_digest,
        "actual_digest": actual_digest,
        "workspace_root": str(workspace_root.resolve(strict=True)),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
    }
    print(
        "E2E_WORKSPACE_MANIFEST_MISMATCH " + json.dumps(summary, ensure_ascii=True, sort_keys=True)
    )
    for entry in added:
        print(
            "E2E_WORKSPACE_MANIFEST_ADDED "
            + json.dumps(_diagnostic_entry(entry), ensure_ascii=True, sort_keys=True)
        )
    for entry in removed:
        print(
            "E2E_WORKSPACE_MANIFEST_REMOVED "
            + json.dumps(_diagnostic_entry(entry), ensure_ascii=True, sort_keys=True)
        )
    for old_entry, new_entry in changed:
        diagnostic = {
            "path": old_entry["path"],
            "old": {
                key: value for key, value in _diagnostic_entry(old_entry).items() if key != "path"
            },
            "new": {
                key: value for key, value in _diagnostic_entry(new_entry).items() if key != "path"
            },
        }
        print(
            "E2E_WORKSPACE_MANIFEST_CHANGED "
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
