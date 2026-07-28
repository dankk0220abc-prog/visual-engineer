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
        head = self._read_source_file(git_directory / "HEAD", max_bytes=1024).decode(
            "ascii", "strict"
        )
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
    ) -> Path:
        _require_fresh_permit(permit_expires_at)
        metadata = self.inspect_source(repository)
        if metadata.current_revision != source_revision:
            raise GitOperationError(FailureCode.SOURCE_REVISION_MISMATCH)
        mirror = self.mirror_path(opaque_handle)
        if mirror.exists():
            if mirror.is_symlink() or not mirror.is_dir():
                raise GitOperationError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)
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
        else:
            mirror.mkdir(mode=0o700)
            self._run(
                ["-C", os.fspath(mirror), "init", "--bare"],
                failure=FailureCode.REPOSITORY_UNAVAILABLE,
                permit_expires_at=permit_expires_at,
            )
        _require_fresh_permit(permit_expires_at)
        self._write_managed_config(mirror)
        self._copy_source_objects(
            self._source_git_directory(self._validate_source_path(repository.path)),
            mirror / "objects",
            permit_expires_at=permit_expires_at,
        )
        self._run(
            ["-C", os.fspath(mirror), "cat-file", "-e", f"{source_revision}^{{commit}}"],
            failure=FailureCode.SOURCE_REVISION_MISMATCH,
            permit_expires_at=permit_expires_at,
        )
        self._run(
            [
                "-C",
                os.fspath(mirror),
                "update-ref",
                "refs/visual-engineer/source-head",
                source_revision,
            ],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
            permit_expires_at=permit_expires_at,
        )
        return mirror

    def create_detached_worktree(
        self,
        mirror: Path,
        workspace_id: uuid.UUID,
        source_revision: str,
        *,
        permit_expires_at: datetime,
    ) -> Path:
        _require_fresh_permit(permit_expires_at)
        workspace = self.workspace_path(workspace_id)
        if workspace.exists():
            raise GitOperationError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)
        self._run(
            ["-C", os.fspath(mirror), "worktree", "prune", "--expire=now"],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
            permit_expires_at=permit_expires_at,
        )
        self._run(
            [
                "-C",
                os.fspath(mirror),
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
            raise GitOperationError(FailureCode.SOURCE_REVISION_MISMATCH)
        os.chmod(workspace, 0o700)
        return workspace

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
            for raw_line in packed.splitlines():
                if not raw_line or raw_line.startswith((b"#", b"^")):
                    continue
                object_id, separator, candidate = raw_line.partition(b" ")
                if separator and candidate.decode("ascii", "strict") == reference:
                    value = object_id.decode("ascii", "strict")
                    break
            if not value:
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from None
        except OSError as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        else:
            value = self._read_source_file(loose, max_bytes=1024).decode("ascii", "strict").strip()
        _require_object_id(value)
        return value

    def _write_managed_config(self, mirror: Path) -> None:
        config = mirror / "config"
        payload = (
            b"[core]\n"
            b"\trepositoryformatversion = 0\n"
            b"\tfilemode = true\n"
            b"\tbare = true\n"
            b"\tlogallrefupdates = false\n"
        )
        temporary = mirror / f".config-{uuid.uuid4().hex}.tmp"
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
            os.replace(temporary, config)
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        for alternate in (
            mirror / "objects" / "info" / "alternates",
            mirror / "objects" / "info" / "http-alternates",
        ):
            if alternate.exists() or alternate.is_symlink():
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)

    def _copy_source_objects(
        self,
        source_git: Path,
        destination: Path,
        *,
        permit_expires_at: datetime,
    ) -> None:
        _require_fresh_permit(permit_expires_at)
        source_objects = source_git / "objects"
        for alternate in (
            source_objects / "info" / "alternates",
            source_objects / "info" / "http-alternates",
        ):
            if alternate.exists() or alternate.is_symlink():
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
        try:
            source_metadata = os.lstat(source_objects)
        except OSError as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if not stat.S_ISDIR(source_metadata.st_mode) or stat.S_ISLNK(source_metadata.st_mode):
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
        destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        file_count, total_bytes = self._object_storage_usage(destination)
        if (
            file_count > self._settings.mirror_max_object_files
            or total_bytes > self._settings.mirror_max_object_bytes
        ):
            raise GitOperationError(FailureCode.MIRROR_BUDGET_EXCEEDED)
        try:
            first_level = list(os.scandir(source_objects))
        except OSError as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        for entry in sorted(first_level, key=lambda item: item.name):
            _require_fresh_permit(permit_expires_at)
            if entry.name == "info":
                continue
            if entry.name == "pack":
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
                source_files = list(os.scandir(entry.path))
                destination_directory = destination / "pack"
            elif len(entry.name) == 2 and all(
                character in "0123456789abcdef" for character in entry.name
            ):
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
                source_files = list(os.scandir(entry.path))
                destination_directory = destination / entry.name
            else:
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
            destination_directory.mkdir(mode=0o700, exist_ok=True)
            for source_file in sorted(source_files, key=lambda item: item.name):
                _require_fresh_permit(permit_expires_at)
                if source_file.is_symlink() or not source_file.is_file(follow_symlinks=False):
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
                destination_file = destination_directory / source_file.name
                try:
                    destination_metadata = os.lstat(destination_file)
                except FileNotFoundError:
                    existing_bytes = 0
                    file_count += 1
                except OSError as exc:
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
                else:
                    if (
                        not stat.S_ISREG(destination_metadata.st_mode)
                        or stat.S_ISLNK(destination_metadata.st_mode)
                        or destination_metadata.st_nlink != 1
                    ):
                        raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                    existing_bytes = destination_metadata.st_size
                if file_count > self._settings.mirror_max_object_files:
                    raise GitOperationError(FailureCode.MIRROR_BUDGET_EXCEEDED)
                copied_bytes = self._copy_object_file(
                    Path(source_file.path),
                    destination_file,
                    max_bytes=(
                        self._settings.mirror_max_object_bytes - total_bytes + existing_bytes
                    ),
                    permit_expires_at=permit_expires_at,
                )
                total_bytes = total_bytes - existing_bytes + copied_bytes

    def _object_storage_usage(self, objects: Path) -> tuple[int, int]:
        file_count = 0
        total_bytes = 0
        try:
            first_level = list(os.scandir(objects))
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        for entry in first_level:
            if entry.name == "info":
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                try:
                    with os.scandir(entry.path) as iterator:
                        if next(iterator, None) is not None:
                            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                except OSError as exc:
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
                continue
            if entry.name != "pack" and not (
                len(entry.name) == 2
                and all(character in "0123456789abcdef" for character in entry.name)
            ):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
            try:
                object_files = list(os.scandir(entry.path))
            except OSError as exc:
                raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
            for object_file in object_files:
                if object_file.is_symlink() or not object_file.is_file(follow_symlinks=False):
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                metadata = object_file.stat(follow_symlinks=False)
                if metadata.st_nlink != 1:
                    raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                file_count += 1
                total_bytes += metadata.st_size
        return file_count, total_bytes

    def _copy_object_file(
        self,
        source: Path,
        destination: Path,
        *,
        max_bytes: int,
        permit_expires_at: datetime,
    ) -> int:
        _require_fresh_permit(permit_expires_at)
        try:
            source_descriptor = os.open(
                source,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}.tmp"
        destination_descriptor: int | None = None
        try:
            before = os.fstat(source_descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
            if before.st_size > max_bytes:
                raise GitOperationError(FailureCode.MIRROR_BUDGET_EXCEEDED)
            destination_descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            copied = 0
            while copied < before.st_size:
                _require_fresh_permit(permit_expires_at)
                chunk = os.read(source_descriptor, min(1024 * 1024, before.st_size - copied))
                if not chunk:
                    raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
                view = memoryview(chunk)
                while view:
                    written = os.write(destination_descriptor, view)
                    if written <= 0:
                        raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
                    view = view[written:]
                copied += len(chunk)
            after = os.fstat(source_descriptor)
            if (
                before.st_dev != after.st_dev
                or before.st_ino != after.st_ino
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
            ):
                raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)
            os.fsync(destination_descriptor)
            os.close(destination_descriptor)
            destination_descriptor = None
            _require_fresh_permit(permit_expires_at)
            os.replace(temporary, destination)
            return copied
        except OSError as exc:
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        finally:
            os.close(source_descriptor)
            if destination_descriptor is not None:
                os.close(destination_descriptor)
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

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
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
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
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        stdout = bytearray()
        total = 0
        deadline = time.monotonic() + timeout_seconds
        try:
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._terminate_process(process)
                    raise GitOperationError(timeout_failure)
                events = selector.select(min(remaining, 0.25))
                if not events and process.poll() is not None:
                    events = [
                        (key, selectors.EVENT_READ) for key in list(selector.get_map().values())
                    ]
                for key, _ in events:
                    chunk = os.read(key.fd, 64 * 1024)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    total += len(chunk)
                    if total > self._settings.git_max_output_bytes:
                        self._terminate_process(process)
                        raise GitOperationError(FailureCode.GIT_OUTPUT_LIMIT_EXCEEDED)
                    if key.data == "stdout":
                        stdout.extend(chunk)
            return bytes(stdout), process.wait(timeout=1)
        except subprocess.TimeoutExpired as exc:
            self._terminate_process(process)
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        finally:
            selector.close()
            process.stdout.close()
            process.stderr.close()

    @staticmethod
    def _terminate_process(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            process.kill()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass


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
    if not value.startswith("refs/heads/") or len(value.encode("ascii", "ignore")) > 300:
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
