from __future__ import annotations

import difflib
import hashlib
import os
import selectors
import signal
import stat
import subprocess
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from visual_engineer_runner.config import LocalRepositoryConfig, RunnerSettings
from visual_engineer_runner.git_object_store import (
    CheckoutManifestEntry,
    ObjectLimits,
    SourceObjectClosure,
    SourceObjectError,
)
from visual_engineer_runner_protocol import FailureCode, SourceStatus, WorkspaceStatusCode


class GitOperationError(Exception):
    def __init__(self, code: FailureCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True)
class RepositoryMetadata:
    current_revision: str
    current_branch: str | None
    source_is_dirty: bool
    dirty_path_count: int
    source_status: SourceStatus


@dataclass(frozen=True)
class GitStatusEntry:
    relative_path: str
    status: WorkspaceStatusCode


@dataclass(frozen=True)
class PreparedMirror:
    path: Path
    source_revision: str
    checkout_manifest: tuple[CheckoutManifestEntry, ...]
    manifest_digest: str


@dataclass(frozen=True)
class CheckoutProof:
    workspace: Path
    expected_manifest_digest: str
    actual_manifest_digest: str
    entry_count: int


@dataclass(frozen=True)
class _WorkspaceEntrySnapshot:
    device: int
    inode: int
    mode: int
    links: int
    size: int
    modified_ns: int

    @classmethod
    def from_stat(cls, metadata: os.stat_result) -> _WorkspaceEntrySnapshot:
        return cls(
            device=metadata.st_dev,
            inode=metadata.st_ino,
            mode=metadata.st_mode,
            links=metadata.st_nlink,
            size=metadata.st_size,
            modified_ns=metadata.st_mtime_ns,
        )


class GitOperations:
    """The Runner's only subprocess boundary.

    Every invocation uses a fixed Git executable, argument arrays, a sanitized
    environment, disabled hooks/credentials/external helpers, and a timeout.
    Source paths come only from Runner-local configuration.
    """

    def __init__(self, settings: RunnerSettings) -> None:
        self._settings = settings
        self._state_roots = (
            settings.mirror_root,
            settings.workspace_root,
            settings.registry_root,
        )
        for root in self._state_roots:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            if root.is_symlink() or not root.is_dir():
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            os.chmod(root, 0o700)
        for repository in settings.repository_handles.values():
            self._validate_source_path(repository.path)

    def inspect_source(self, repository: LocalRepositoryConfig) -> RepositoryMetadata:
        source = self._validate_source_path(repository.path)
        if self._settings.require_source_read_only:
            flags = os.statvfs(source).f_flag
            if not flags & getattr(os, "ST_RDONLY", 1):
                raise GitOperationError(FailureCode.SOURCE_NOT_READ_ONLY)

        git_directory = self._source_git_directory(source)
        try:
            head = self._read_source_file(git_directory / "HEAD", max_bytes=1024).decode(
                "ascii", "strict"
            )
        except UnicodeDecodeError as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        head = head.strip()
        branch: str | None = None
        if head.startswith("ref: "):
            reference = head.removeprefix("ref: ")
            if not _valid_source_reference(reference):
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
            branch = reference.removeprefix("refs/heads/")
            revision = self._read_source_reference(git_directory, reference)
        else:
            revision = head
        _require_object_id(revision)
        return RepositoryMetadata(
            current_revision=revision,
            current_branch=branch,
            # Reading dirty or untracked source content would cross the Phase 4
            # boundary. Report a conservative, explicit unknown sentinel.
            source_is_dirty=True,
            dirty_path_count=10_000,
            source_status=SourceStatus.UNKNOWN,
        )

    def mirror_path(self, opaque_handle: str) -> Path:
        digest = hashlib.sha256(opaque_handle.encode("utf-8")).hexdigest()
        return self._settings.mirror_root / f"mirror-{digest}"

    def workspace_path(self, workspace_id: uuid.UUID) -> Path:
        return self._settings.workspace_root / f"workspace-{workspace_id.hex}"

    def prepare_mirror(
        self,
        opaque_handle: str,
        repository: LocalRepositoryConfig,
        source_revision: str,
        *,
        permit_expires_at: datetime,
    ) -> PreparedMirror:
        _require_fresh_permit(permit_expires_at)
        metadata = self.inspect_source(repository)
        if metadata.current_revision != source_revision:
            raise GitOperationError(FailureCode.SOURCE_REVISION_MISMATCH)
        mirror = self.mirror_path(opaque_handle)
        created_mirror = False
        if mirror.exists() or mirror.is_symlink():
            if mirror.is_symlink() or not mirror.is_dir():
                raise GitOperationError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)
            self._validate_managed_mirror(
                mirror,
                object_id_hex_length=len(source_revision),
                source_revision=source_revision,
            )
            bare = (
                self._run(
                    ["-C", os.fspath(mirror), "rev-parse", "--is-bare-repository"],
                    failure=FailureCode.WORKSPACE_STATE_INVALID,
                    permit_expires_at=permit_expires_at,
                )
                .decode("ascii", "strict")
                .strip()
            )
            if bare != "true":
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            object_format = (
                self._run(
                    ["-C", os.fspath(mirror), "rev-parse", "--show-object-format"],
                    failure=FailureCode.WORKSPACE_STATE_INVALID,
                    permit_expires_at=permit_expires_at,
                )
                .decode("ascii", "strict")
                .strip()
            )
            if object_format != _object_format(len(source_revision)):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        else:
            mirror.mkdir(mode=0o700)
            created_mirror = True
            self._run(
                [
                    "-C",
                    os.fspath(mirror),
                    "init",
                    "--bare",
                    "--template=",
                    f"--object-format={_object_format(len(source_revision))}",
                ],
                failure=FailureCode.REPOSITORY_UNAVAILABLE,
                permit_expires_at=permit_expires_at,
            )
            self._write_managed_config(mirror, object_id_hex_length=len(source_revision))
        _require_fresh_permit(permit_expires_at)
        checkout_manifest = self._copy_source_objects(
            self._source_git_directory(self._validate_source_path(repository.path)),
            mirror / "objects",
            source_revision=source_revision,
            permit_expires_at=permit_expires_at,
        )
        if self.inspect_source(repository) != metadata:
            raise GitOperationError(FailureCode.SOURCE_REVISION_MISMATCH)
        if created_mirror:
            self._write_detached_head(mirror, source_revision)
        self._validate_managed_mirror(
            mirror,
            object_id_hex_length=len(source_revision),
            source_revision=source_revision,
        )
        self._run(
            ["-C", os.fspath(mirror), "cat-file", "-e", f"{source_revision}^{{commit}}"],
            failure=FailureCode.SOURCE_REVISION_MISMATCH,
            permit_expires_at=permit_expires_at,
        )
        return PreparedMirror(
            path=mirror,
            source_revision=source_revision,
            checkout_manifest=checkout_manifest,
            manifest_digest=_manifest_digest(checkout_manifest),
        )

    def create_detached_worktree(
        self,
        mirror: PreparedMirror,
        workspace_id: uuid.UUID,
        source_revision: str,
        *,
        permit_expires_at: datetime,
    ) -> CheckoutProof:
        _require_fresh_permit(permit_expires_at)
        if mirror.source_revision != source_revision:
            raise GitOperationError(FailureCode.SOURCE_REVISION_MISMATCH)
        workspace = self.workspace_path(workspace_id)
        if workspace.exists():
            raise GitOperationError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)
        self._run(
            ["-C", os.fspath(mirror.path), "worktree", "prune", "--expire=now"],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
            permit_expires_at=permit_expires_at,
        )
        self._run(
            [
                "-C",
                os.fspath(mirror.path),
                "worktree",
                "add",
                "--detach",
                "--force",
                os.fspath(workspace),
                source_revision,
            ],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
            permit_expires_at=permit_expires_at,
        )
        actual = (
            self._run(
                ["-C", os.fspath(workspace), "rev-parse", "--verify", "HEAD^{commit}"],
                failure=FailureCode.WORKSPACE_STATE_INVALID,
                permit_expires_at=permit_expires_at,
            )
            .decode("ascii", "strict")
            .strip()
        )
        _require_fresh_permit(permit_expires_at)
        if actual != source_revision:
            self._quarantine_workspace(workspace, workspace_id)
            raise GitOperationError(FailureCode.SOURCE_REVISION_MISMATCH)
        try:
            actual_manifest = self._workspace_checkout_manifest(
                workspace,
                expected_manifest=mirror.checkout_manifest,
            )
        except GitOperationError:
            self._quarantine_workspace(workspace, workspace_id)
            raise
        actual_manifest_digest = _manifest_digest(actual_manifest)
        if (
            actual_manifest != mirror.checkout_manifest
            or actual_manifest_digest != mirror.manifest_digest
        ):
            self._quarantine_workspace(workspace, workspace_id)
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        os.chmod(workspace, 0o700)
        return CheckoutProof(
            workspace=workspace,
            expected_manifest_digest=mirror.manifest_digest,
            actual_manifest_digest=actual_manifest_digest,
            entry_count=len(actual_manifest),
        )

    def status(self, workspace: Path, source_revision: str) -> list[GitStatusEntry]:
        self._require_workspace(workspace)
        actual = (
            self._run(
                ["-C", os.fspath(workspace), "rev-parse", "--verify", "HEAD^{commit}"],
                failure=FailureCode.WORKSPACE_STATE_INVALID,
            )
            .decode("ascii", "strict")
            .strip()
        )
        if actual != source_revision:
            raise GitOperationError(FailureCode.SOURCE_REVISION_MISMATCH)
        raw = self._run(
            [
                "-C",
                os.fspath(workspace),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignored=no",
                "--no-renames",
            ],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
        )
        entries: list[GitStatusEntry] = []
        for record in raw.split(b"\0"):
            if not record:
                continue
            try:
                text = record.decode("utf-8", "strict")
            except UnicodeDecodeError as exc:
                raise GitOperationError(FailureCode.PATH_INVALID) from exc
            if len(text) < 4 or text[2] != " ":
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            relative_path = _validated_git_path(text[3:])
            entries.append(
                GitStatusEntry(
                    relative_path=relative_path,
                    status=_status_code(text[:2]),
                )
            )
        entries.sort(key=lambda item: item.relative_path)
        return entries

    def discard_inventory(self, workspace: Path, source_revision: str) -> list[GitStatusEntry]:
        self._require_workspace(workspace)
        raw = self._run(
            [
                "-C",
                os.fspath(workspace),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignored=matching",
                "--no-renames",
            ],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
        )
        entries: list[GitStatusEntry] = []
        for record in raw.split(b"\0"):
            if not record:
                continue
            try:
                text = record.decode("utf-8", "strict")
            except UnicodeDecodeError as exc:
                raise GitOperationError(FailureCode.PATH_INVALID) from exc
            if len(text) < 4 or text[2] != " ":
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            entries.append(
                GitStatusEntry(
                    relative_path=_validated_git_path(text[3:].removesuffix("/")),
                    status=_status_code(text[:2]),
                )
            )
        entries.sort(key=lambda item: item.relative_path)
        return entries

    def diff(
        self,
        workspace: Path,
        source_revision: str,
        entries: Iterable[GitStatusEntry],
        *,
        read_untracked_text: Callable[[str], str],
        max_bytes: int,
    ) -> str:
        selected = list(entries)
        tracked_paths = [
            item.relative_path for item in selected if item.status != WorkspaceStatusCode.UNTRACKED
        ]
        chunks: list[str] = []
        if tracked_paths:
            raw = self._run(
                [
                    "-C",
                    os.fspath(workspace),
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--no-renames",
                    "--src-prefix=a/",
                    "--dst-prefix=b/",
                    source_revision,
                    "--",
                    *tracked_paths,
                ],
                failure=FailureCode.WORKSPACE_STATE_INVALID,
            )
            try:
                tracked_diff = raw.decode("utf-8", "strict")
            except UnicodeDecodeError as exc:
                raise GitOperationError(FailureCode.BINARY_DENIED) from exc
            if "Binary files " in tracked_diff or "GIT binary patch" in tracked_diff:
                raise GitOperationError(FailureCode.BINARY_DENIED)
            chunks.append(tracked_diff)
        for item in selected:
            if item.status != WorkspaceStatusCode.UNTRACKED:
                continue
            content = read_untracked_text(item.relative_path)
            lines = content.splitlines(keepends=True)
            chunks.append(
                "".join(
                    difflib.unified_diff(
                        [],
                        lines,
                        fromfile=f"a/{item.relative_path}",
                        tofile=f"b/{item.relative_path}",
                        lineterm="\n",
                    )
                )
            )
        result = "".join(chunks)
        if len(result.encode("utf-8")) > max_bytes:
            raise GitOperationError(FailureCode.DIFF_BUDGET_EXCEEDED)
        return result

    def restore_tracked(
        self,
        workspace: Path,
        source_revision: str,
        relative_paths: list[str],
        *,
        permit_expires_at: datetime,
    ) -> None:
        if not relative_paths:
            return
        for path in relative_paths:
            _validated_git_path(path)
        self._run(
            [
                "-C",
                os.fspath(workspace),
                "restore",
                f"--source={source_revision}",
                "--staged",
                "--worktree",
                "--",
                *relative_paths,
            ],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
            permit_expires_at=permit_expires_at,
        )

    def discard_worktree(
        self,
        mirror: Path,
        workspace: Path,
        *,
        permit_expires_at: datetime,
    ) -> None:
        self._require_workspace(workspace)
        self._run(
            [
                "-C",
                os.fspath(mirror),
                "worktree",
                "remove",
                "--force",
                os.fspath(workspace),
            ],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
            permit_expires_at=permit_expires_at,
        )
        if workspace.exists():
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        self._run(
            ["-C", os.fspath(mirror), "worktree", "prune", "--expire=now"],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
            permit_expires_at=permit_expires_at,
        )

    def _validate_source_path(self, candidate: Path) -> Path:
        if not candidate.is_absolute() or candidate == Path("/"):
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
        try:
            source = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if candidate.is_symlink() or not source.is_dir():
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
        for root in self._state_roots:
            resolved_root = root.resolve(strict=True)
            if source == resolved_root or source.is_relative_to(resolved_root):
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
            if resolved_root.is_relative_to(source):
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
        return source

    def _source_git_directory(self, source: Path) -> Path:
        git_directory = source / ".git"
        try:
            metadata = os.lstat(git_directory)
        except OSError as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
        return git_directory

    def _read_source_file(self, path: Path, *, max_bytes: int) -> bytes:
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
            payload = bytearray()
            while len(payload) <= max_bytes:
                chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
            after = os.fstat(descriptor)
            if (
                len(payload) > max_bytes
                or before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
            ):
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
            return bytes(payload)
        finally:
            os.close(descriptor)

    def _read_source_reference(self, git_directory: Path, reference: str) -> str:
        components = reference.split("/")
        parent = git_directory
        try:
            for component in components[:-1]:
                parent /= component
                parent_metadata = os.lstat(parent)
                if not stat.S_ISDIR(parent_metadata.st_mode) or stat.S_ISLNK(
                    parent_metadata.st_mode
                ):
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
            loose = parent / components[-1]
            os.lstat(loose)
        except FileNotFoundError:
            packed_path = git_directory / "packed-refs"
            packed = self._read_source_file(packed_path, max_bytes=8 * 1024 * 1024)
            value = ""
            seen_references: set[str] = set()
            object_id_length: int | None = None
            previous_was_reference = False
            for raw_line in packed.splitlines():
                if not raw_line or raw_line.startswith(b"#"):
                    previous_was_reference = False
                    continue
                if raw_line.startswith(b"^"):
                    try:
                        peeled = raw_line[1:].decode("ascii", "strict")
                    except UnicodeDecodeError as exc:
                        raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
                    if not previous_was_reference:
                        raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from None
                    _require_object_id(peeled)
                    if object_id_length is not None and len(peeled) != object_id_length:
                        raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from None
                    previous_was_reference = False
                    continue
                fields = raw_line.split(b" ")
                if len(fields) != 2:
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from None
                try:
                    object_id = fields[0].decode("ascii", "strict")
                    candidate = fields[1].decode("ascii", "strict")
                except UnicodeDecodeError as exc:
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
                _require_object_id(object_id)
                if not _valid_packed_reference(candidate) or candidate in seen_references:
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from None
                if object_id_length is None:
                    object_id_length = len(object_id)
                elif len(object_id) != object_id_length:
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from None
                seen_references.add(candidate)
                previous_was_reference = True
                if candidate == reference:
                    value = object_id
            if not value:
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from None
        except OSError as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        else:
            try:
                value = (
                    self._read_source_file(loose, max_bytes=1024).decode("ascii", "strict").strip()
                )
            except UnicodeDecodeError as exc:
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        _require_object_id(value)
        return value

    def _write_detached_head(self, mirror: Path, source_revision: str) -> None:
        _require_object_id(source_revision)
        self._write_managed_file(
            mirror,
            "HEAD",
            (source_revision + "\n").encode("ascii"),
        )

    def _write_managed_config(self, mirror: Path, *, object_id_hex_length: int) -> None:
        self._write_managed_file(
            mirror,
            "config",
            _managed_config_payload(object_id_hex_length),
        )
        for forbidden in (
            mirror / "objects" / "info" / "alternates",
            mirror / "objects" / "info" / "http-alternates",
            mirror / "info",
            mirror / "hooks",
            mirror / "logs",
            mirror / "shallow",
            mirror / "packed-refs",
            mirror / "refs" / "replace",
        ):
            if forbidden.exists() or forbidden.is_symlink():
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)

    def _write_managed_file(self, root: Path, name: str, payload: bytes) -> None:
        destination = root / name
        temporary = root / f".{name.lower()}-{uuid.uuid4().hex}.tmp"
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            try:
                os.write(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.replace(temporary, destination)
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def _validate_managed_mirror(
        self,
        mirror: Path,
        *,
        object_id_hex_length: int,
        source_revision: str,
    ) -> None:
        self._validate_managed_config(
            mirror,
            object_id_hex_length=object_id_hex_length,
        )
        self._validate_managed_head(mirror, source_revision)
        required = {"HEAD", "config", "objects", "refs"}
        allowed = required | {"worktrees"}
        try:
            with os.scandir(mirror) as entries:
                found = {entry.name for entry in entries}
            if not required.issubset(found) or not found.issubset(allowed):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            for name in ("objects", "refs", "worktrees"):
                path = mirror / name
                if name == "worktrees" and name not in found:
                    continue
                metadata = os.lstat(path)
                if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        except GitOperationError:
            raise
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        self._validate_empty_ref_namespace(mirror / "refs")

    def _validate_managed_head(self, mirror: Path, source_revision: str) -> None:
        expected = (source_revision + "\n").encode("ascii")
        path = mirror / "HEAD"
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_size != len(expected)
            ):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            payload = os.read(descriptor, len(expected) + 1)
            after = os.fstat(descriptor)
            if payload != expected or _WorkspaceEntrySnapshot.from_stat(
                before
            ) != _WorkspaceEntrySnapshot.from_stat(after):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        finally:
            os.close(descriptor)

    def _validate_empty_ref_namespace(self, refs: Path) -> None:
        try:
            with os.scandir(refs) as entries:
                found = {entry.name for entry in entries}
            if found != {"heads", "tags"}:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            for name in sorted(found):
                path = refs / name
                metadata = os.lstat(path)
                if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                with os.scandir(path) as entries:
                    if next(entries, None) is not None:
                        raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        except GitOperationError:
            raise
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc

    def _validate_managed_config(
        self,
        mirror: Path,
        *,
        object_id_hex_length: int,
    ) -> None:
        config = mirror / "config"
        try:
            descriptor = os.open(
                config,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            before = os.fstat(descriptor)
            expected = _managed_config_payload(object_id_hex_length)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != 0o600
                or before.st_size != len(expected)
            ):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            payload = bytearray()
            while len(payload) < before.st_size:
                chunk = os.read(descriptor, before.st_size - len(payload))
                if not chunk:
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                payload.extend(chunk)
            after = os.fstat(descriptor)
            if (
                bytes(payload) != expected
                or before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
            ):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        finally:
            os.close(descriptor)
        for forbidden in (
            mirror / "objects" / "info" / "alternates",
            mirror / "objects" / "info" / "http-alternates",
            mirror / "info",
            mirror / "hooks",
            mirror / "logs",
            mirror / "shallow",
            mirror / "packed-refs",
            mirror / "refs" / "replace",
        ):
            if forbidden.exists() or forbidden.is_symlink():
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)

    def _copy_source_objects(
        self,
        source_git: Path,
        destination: Path,
        *,
        source_revision: str,
        permit_expires_at: datetime,
    ) -> tuple[CheckoutManifestEntry, ...]:
        try:
            reader = SourceObjectClosure(
                source_git,
                object_id_hex_length=len(source_revision),
                limits=ObjectLimits(
                    max_objects=self._settings.mirror_max_object_files,
                    max_bytes=self._settings.mirror_max_object_bytes,
                    max_single_object_bytes=self._settings.mirror_max_single_object_bytes,
                    max_pack_files=self._settings.mirror_max_pack_files,
                    max_delta_depth=self._settings.mirror_max_delta_depth,
                    max_tree_depth=self._settings.mirror_max_tree_depth,
                    max_tree_entries=self._settings.mirror_max_tree_entries,
                    max_references=self._settings.mirror_max_object_references,
                    max_graph_depth=self._settings.mirror_max_graph_depth,
                ),
            )

            def require_fresh() -> None:
                _require_fresh_permit(permit_expires_at)

            closure = reader.collect(source_revision, require_fresh=require_fresh)
            checkout_manifest = reader.checkout_manifest(
                source_revision,
                require_fresh=require_fresh,
            )
            reader.materialize(
                destination,
                closure,
                require_fresh=require_fresh,
            )
            return checkout_manifest
        except SourceObjectError as exc:
            raise GitOperationError(exc.code) from exc

    def _workspace_checkout_manifest(
        self,
        workspace: Path,
        *,
        expected_manifest: tuple[CheckoutManifestEntry, ...],
    ) -> tuple[CheckoutManifestEntry, ...]:
        expected_gitlinks = {
            entry.relative_path for entry in expected_manifest if entry.entry_type == "gitlink"
        }
        total_bytes = [0]
        entry_count = [0]
        try:
            root = os.open(
                workspace,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            entries = self._scan_workspace_directory(
                root,
                prefix=b"",
                expected_gitlinks=expected_gitlinks,
                total_bytes=total_bytes,
                entry_count=entry_count,
            )
        finally:
            os.close(root)
        return tuple(sorted(entries, key=lambda entry: entry.relative_path))

    def _scan_workspace_directory(
        self,
        directory: int,
        *,
        prefix: bytes,
        expected_gitlinks: set[bytes],
        total_bytes: list[int],
        entry_count: list[int],
    ) -> list[CheckoutManifestEntry]:
        before_directory = _WorkspaceEntrySnapshot.from_stat(os.fstat(directory))
        try:
            names = sorted(os.fsencode(name) for name in os.listdir(directory))
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        if not prefix:
            if b".git" not in names:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            self._validate_workspace_git_file(directory)
            names.remove(b".git")
        entries: list[CheckoutManifestEntry] = []
        for name in names:
            if not name or name in {b".", b".."} or b"/" in name or name.lower() == b".git":
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            relative_path = name if not prefix else prefix + b"/" + name
            try:
                metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
            except OSError as exc:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
            before = _WorkspaceEntrySnapshot.from_stat(metadata)
            entry_count[0] += 1
            if entry_count[0] > self._settings.mirror_max_tree_entries:
                raise GitOperationError(FailureCode.MIRROR_BUDGET_EXCEEDED)
            if stat.S_ISDIR(metadata.st_mode):
                try:
                    child = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                        dir_fd=directory,
                    )
                except OSError as exc:
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
                try:
                    if relative_path in expected_gitlinks:
                        if os.listdir(child):
                            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                        if before != _WorkspaceEntrySnapshot.from_stat(os.fstat(child)):
                            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                        entries.append(
                            CheckoutManifestEntry(
                                relative_path=relative_path,
                                entry_type="gitlink",
                                mode=0o160000,
                                size=0,
                                sha256=hashlib.sha256(b"").hexdigest(),
                            )
                        )
                    else:
                        children = self._scan_workspace_directory(
                            child,
                            prefix=relative_path,
                            expected_gitlinks=expected_gitlinks,
                            total_bytes=total_bytes,
                            entry_count=entry_count,
                        )
                        entries.append(
                            CheckoutManifestEntry(
                                relative_path=relative_path,
                                entry_type="directory",
                                mode=0o040000,
                                size=0,
                                sha256=None,
                            )
                        )
                        entries.extend(children)
                finally:
                    os.close(child)
            elif stat.S_ISLNK(metadata.st_mode):
                try:
                    target = os.readlink(name, dir_fd=directory)
                    after = os.stat(name, dir_fd=directory, follow_symlinks=False)
                except OSError as exc:
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
                target_bytes = os.fsencode(target)
                if (
                    before != _WorkspaceEntrySnapshot.from_stat(after)
                    or len(target_bytes) > self._settings.mirror_max_single_object_bytes
                ):
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                total_bytes[0] += len(target_bytes)
                if total_bytes[0] > self._settings.mirror_max_object_bytes:
                    raise GitOperationError(FailureCode.MIRROR_BUDGET_EXCEEDED)
                entries.append(
                    CheckoutManifestEntry(
                        relative_path=relative_path,
                        entry_type="symlink",
                        mode=0o120000,
                        size=len(target_bytes),
                        sha256=hashlib.sha256(target_bytes).hexdigest(),
                    )
                )
            elif stat.S_ISREG(metadata.st_mode):
                if metadata.st_nlink != 1:
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                content_digest = self._hash_workspace_file(
                    directory,
                    name,
                    before=before,
                    total_bytes=total_bytes,
                )
                entries.append(
                    CheckoutManifestEntry(
                        relative_path=relative_path,
                        entry_type="regular",
                        mode=0o100755 if metadata.st_mode & 0o111 else 0o100644,
                        size=metadata.st_size,
                        sha256=content_digest,
                    )
                )
            else:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            try:
                after_entry = os.stat(name, dir_fd=directory, follow_symlinks=False)
            except OSError as exc:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
            if before != _WorkspaceEntrySnapshot.from_stat(after_entry):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        try:
            after_names = sorted(os.fsencode(name) for name in os.listdir(directory))
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        if not prefix:
            try:
                after_names.remove(b".git")
            except ValueError as exc:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        if names != after_names or before_directory != _WorkspaceEntrySnapshot.from_stat(
            os.fstat(directory)
        ):
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        return entries

    def _validate_workspace_git_file(self, root: int) -> None:
        try:
            metadata = os.stat(b".git", dir_fd=root, follow_symlinks=False)
            descriptor = os.open(
                b".git",
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=root,
            )
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            before = _WorkspaceEntrySnapshot.from_stat(os.fstat(descriptor))
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or before != _WorkspaceEntrySnapshot.from_stat(metadata)
                or metadata.st_size > 4096
            ):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            payload = os.read(descriptor, 4097)
            after = _WorkspaceEntrySnapshot.from_stat(os.fstat(descriptor))
            if (
                len(payload) != metadata.st_size
                or before != after
                or not payload.startswith(b"gitdir: ")
                or not payload.endswith(b"\n")
            ):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        finally:
            os.close(descriptor)

    def _hash_workspace_file(
        self,
        directory: int,
        name: bytes,
        *,
        before: _WorkspaceEntrySnapshot,
        total_bytes: list[int],
    ) -> str:
        if before.size > self._settings.mirror_max_single_object_bytes:
            raise GitOperationError(FailureCode.MIRROR_BUDGET_EXCEEDED)
        total_bytes[0] += before.size
        if total_bytes[0] > self._settings.mirror_max_object_bytes:
            raise GitOperationError(FailureCode.MIRROR_BUDGET_EXCEEDED)
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=directory,
            )
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            opened = _WorkspaceEntrySnapshot.from_stat(os.fstat(descriptor))
            if opened != before or not stat.S_ISREG(opened.mode) or opened.links != 1:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            digest = hashlib.sha256()
            remaining = before.size
            while remaining:
                chunk = os.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                digest.update(chunk)
                remaining -= len(chunk)
            if os.read(descriptor, 1):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            if opened != _WorkspaceEntrySnapshot.from_stat(os.fstat(descriptor)):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            return digest.hexdigest()
        finally:
            os.close(descriptor)

    def _quarantine_workspace(self, workspace: Path, workspace_id: uuid.UUID) -> Path:
        source_name = workspace.name
        quarantine_name = f"quarantine-workspace-{workspace_id.hex}-{uuid.uuid4().hex}"
        try:
            root = os.open(
                self._settings.workspace_root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            os.stat(source_name, dir_fd=root, follow_symlinks=False)
            try:
                os.stat(quarantine_name, dir_fd=root, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            os.rename(
                source_name,
                quarantine_name,
                src_dir_fd=root,
                dst_dir_fd=root,
            )
            os.fsync(root)
        except GitOperationError:
            raise
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        finally:
            os.close(root)
        return self._settings.workspace_root / quarantine_name

    def _require_workspace(self, workspace: Path) -> None:
        expected_parent = self._settings.workspace_root.resolve(strict=True)
        try:
            actual = workspace.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GitOperationError(FailureCode.WORKSPACE_NOT_FOUND) from exc
        if (
            workspace.is_symlink()
            or actual.parent != expected_parent
            or not actual.name.startswith("workspace-")
            or not actual.is_dir()
        ):
            raise GitOperationError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)

    def _run(
        self,
        arguments: list[str],
        *,
        failure: FailureCode,
        allowed_returncodes: frozenset[int] = frozenset({0}),
        permit_expires_at: datetime | None = None,
    ) -> bytes:
        if any("\x00" in argument for argument in arguments):
            raise GitOperationError(FailureCode.PATH_INVALID)
        command = [
            "git",
            "--no-replace-objects",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
            "-c",
            "gc.auto=0",
            "-c",
            "maintenance.auto=false",
            "-c",
            "credential.helper=",
            "-c",
            "diff.external=",
            "-c",
            "core.attributesFile=/dev/null",
            "-c",
            "filter.lfs.smudge=",
            "-c",
            "filter.lfs.required=false",
            "-c",
            "protocol.allow=never",
            "-c",
            "submodule.recurse=false",
            "-c",
            "fetch.fsckObjects=true",
            "-c",
            "transfer.fsckObjects=true",
            *arguments,
        ]
        environment = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/nonexistent",
            "XDG_CONFIG_HOME": "/nonexistent",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_PROTOCOL_FROM_USER": "0",
            "GIT_ASKPASS": "/bin/false",
            "SSH_ASKPASS": "/bin/false",
            "GIT_SSH": "/bin/false",
            "GIT_SSH_COMMAND": "/bin/false",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        process: subprocess.Popen[bytes] | None = None
        timeout_seconds = self._settings.git_timeout_seconds
        timeout_failure = FailureCode.WORKSPACE_STATE_INVALID
        if permit_expires_at is not None:
            permit_seconds = (permit_expires_at - datetime.now(UTC)).total_seconds()
            if permit_seconds <= 0:
                raise GitOperationError(FailureCode.SIDE_EFFECT_PERMIT_EXPIRED)
            if permit_seconds < timeout_seconds:
                timeout_seconds = permit_seconds
                timeout_failure = FailureCode.SIDE_EFFECT_PERMIT_EXPIRED
        try:
            process = subprocess.Popen(
                command,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                start_new_session=True,
            )
            stdout, returncode = self._collect_bounded_output(
                process,
                timeout_seconds=timeout_seconds,
                timeout_failure=timeout_failure,
            )
        except OSError as exc:
            raise GitOperationError(failure) from exc
        if returncode not in allowed_returncodes:
            raise GitOperationError(failure)
        return stdout

    def _collect_bounded_output(
        self,
        process: subprocess.Popen[bytes],
        *,
        timeout_seconds: float,
        timeout_failure: FailureCode,
    ) -> tuple[bytes, int]:
        if process.stdout is None or process.stderr is None:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        selector = selectors.DefaultSelector()
        os.set_blocking(process.stdout.fileno(), False)
        os.set_blocking(process.stderr.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        stdout = bytearray()
        total = 0
        deadline = time.monotonic() + timeout_seconds
        process_group_id = process.pid
        try:
            while True:
                returncode = process.poll()
                group_alive = self._process_group_alive(process_group_id)
                if not selector.get_map() and returncode is not None and not group_alive:
                    return bytes(stdout), returncode
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._terminate_process_group(process, process_group_id)
                    raise GitOperationError(timeout_failure)
                if selector.get_map():
                    events = selector.select(min(remaining, 0.05))
                else:
                    time.sleep(min(remaining, 0.01))
                    events = []
                for key, _ in events:
                    while True:
                        try:
                            chunk = os.read(key.fd, 64 * 1024)
                        except BlockingIOError:
                            break
                        if not chunk:
                            selector.unregister(key.fileobj)
                            break
                        total += len(chunk)
                        if total > self._settings.git_max_output_bytes:
                            self._terminate_process_group(process, process_group_id)
                            raise GitOperationError(FailureCode.GIT_OUTPUT_LIMIT_EXCEEDED)
                        if key.data == "stdout":
                            stdout.extend(chunk)
        finally:
            selector.close()
            process.stdout.close()
            process.stderr.close()

    def _terminate_process_group(
        self,
        process: subprocess.Popen[bytes],
        process_group_id: int,
    ) -> None:
        process.poll()
        if self._process_group_alive(process_group_id):
            try:
                os.killpg(process_group_id, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except OSError as exc:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        grace_deadline = time.monotonic() + self._settings.git_termination_grace_seconds
        while time.monotonic() < grace_deadline:
            process.poll()
            if not self._process_group_alive(process_group_id):
                break
            time.sleep(0.01)
        if self._process_group_alive(process_group_id):
            try:
                os.killpg(process_group_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as exc:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        kill_deadline = time.monotonic() + self._settings.git_termination_grace_seconds
        while time.monotonic() < kill_deadline:
            process.poll()
            if not self._process_group_alive(process_group_id):
                break
            time.sleep(0.01)
        if self._process_group_alive(process_group_id):
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        try:
            process.wait(timeout=self._settings.git_termination_grace_seconds)
        except subprocess.TimeoutExpired as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc

    @staticmethod
    def _process_group_alive(process_group_id: int) -> bool:
        try:
            os.killpg(process_group_id, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # Darwin reports EPERM for a just-reaped, now-empty high-numbered
            # process group. A live descendant created by this same-UID group
            # remains signalable and returns success here.
            return False
        return True


def _validated_git_path(value: str) -> str:
    path = PurePosixPath(value)
    components = value.split("/")
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or path.is_absolute()
        or len(value.encode("utf-8")) > 512
        or len(components) > 32
        or any(
            not component
            or component in {".", ".."}
            or any(ord(character) < 32 or ord(character) == 127 for character in component)
            for component in components
        )
    ):
        raise GitOperationError(FailureCode.PATH_INVALID)
    return value


def _require_fresh_permit(expires_at: datetime) -> None:
    if expires_at <= datetime.now(UTC):
        raise GitOperationError(FailureCode.SIDE_EFFECT_PERMIT_EXPIRED)


def _status_code(code: str) -> WorkspaceStatusCode:
    if code == "!!":
        return WorkspaceStatusCode.IGNORED
    if code == "??":
        return WorkspaceStatusCode.UNTRACKED
    if "R" in code:
        return WorkspaceStatusCode.RENAMED
    if "C" in code:
        return WorkspaceStatusCode.COPIED
    if "A" in code:
        return WorkspaceStatusCode.ADDED
    if "D" in code:
        return WorkspaceStatusCode.DELETED
    if "T" in code:
        return WorkspaceStatusCode.TYPE_CHANGED
    if "M" in code:
        return WorkspaceStatusCode.MODIFIED
    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)


def _valid_source_reference(value: str) -> bool:
    return value.startswith("refs/heads/") and _valid_packed_reference(value)


def _valid_packed_reference(value: str) -> bool:
    if not value.startswith("refs/") or len(value.encode("ascii", "ignore")) > 300:
        return False
    components = value.split("/")
    return all(
        component
        and component not in {".", ".."}
        and not component.startswith(".")
        and not component.endswith((".", ".lock"))
        and ".." not in component
        and "@{" not in component
        and all(character.isalnum() or character in "._-" for character in component)
        for component in components
    )


def _require_object_id(value: str) -> None:
    if len(value) not in {40, 64} or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)


def _object_format(object_id_hex_length: int) -> str:
    if object_id_hex_length == 40:
        return "sha1"
    if object_id_hex_length == 64:
        return "sha256"
    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)


def _managed_config_payload(object_id_hex_length: int) -> bytes:
    object_format = _object_format(object_id_hex_length)
    lines = [
        "[core]",
        f"\trepositoryformatversion = {1 if object_format == 'sha256' else 0}",
        "\tfilemode = true",
        "\tbare = true",
        "\tlogallrefupdates = false",
        "[gc]",
        "\tauto = 0",
        "[maintenance]",
        "\tauto = false",
    ]
    if object_format == "sha256":
        lines.extend(("[extensions]", "\tobjectFormat = sha256"))
    return ("\n".join(lines) + "\n").encode("ascii")


def _manifest_digest(entries: tuple[CheckoutManifestEntry, ...]) -> str:
    digest = hashlib.sha256()
    digest.update(b"visual-engineer-checkout-manifest-v1\0")
    for entry in entries:
        entry_type = entry.entry_type.encode("ascii")
        content_digest = (entry.sha256 or "").encode("ascii")
        for payload in (
            entry.relative_path,
            entry_type,
            f"{entry.mode:o}".encode("ascii"),
            str(entry.size).encode("ascii"),
            content_digest,
        ):
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
    return digest.hexdigest()
