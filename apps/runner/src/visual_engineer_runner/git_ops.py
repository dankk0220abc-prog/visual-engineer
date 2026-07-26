from __future__ import annotations

import difflib
import hashlib
import os
import subprocess
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from visual_engineer_runner.config import LocalRepositoryConfig, RunnerSettings
from visual_engineer_runner_protocol import FailureCode, WorkspaceStatusCode


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

        top_level = (
            self._run(
                ["-C", os.fspath(source), "rev-parse", "--show-toplevel"],
                failure=FailureCode.REPOSITORY_UNAVAILABLE,
            )
            .decode("utf-8", "strict")
            .strip()
        )
        try:
            reported_root = Path(top_level).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE) from exc
        if reported_root != source:
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)

        revision = (
            self._run(
                ["-C", os.fspath(source), "rev-parse", "--verify", "HEAD^{commit}"],
                failure=FailureCode.REPOSITORY_UNAVAILABLE,
            )
            .decode("ascii", "strict")
            .strip()
        )
        if len(revision) not in {40, 64} or any(
            character not in "0123456789abcdef" for character in revision
        ):
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)

        branch_output = self._run(
            ["-C", os.fspath(source), "symbolic-ref", "--quiet", "--short", "HEAD"],
            failure=FailureCode.REPOSITORY_UNAVAILABLE,
            allowed_returncodes=frozenset({0, 1}),
        )
        branch = branch_output.decode("utf-8", "strict").strip() or None
        if branch is not None and (
            len(branch.encode("utf-8")) > 255
            or any(ord(character) < 32 or ord(character) == 127 for character in branch)
        ):
            raise GitOperationError(FailureCode.REPOSITORY_UNAVAILABLE)

        status_output = self._run(
            [
                "-C",
                os.fspath(source),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--ignored=no",
                "--no-renames",
            ],
            failure=FailureCode.REPOSITORY_UNAVAILABLE,
        )
        dirty_count = len([item for item in status_output.split(b"\0") if item])
        if dirty_count > 10_000:
            dirty_count = 10_000
        return RepositoryMetadata(
            current_revision=revision,
            current_branch=branch,
            source_is_dirty=bool(status_output),
            dirty_path_count=dirty_count,
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
    ) -> Path:
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
            )
        self._run(
            [
                "-C",
                os.fspath(mirror),
                "fetch",
                "--no-tags",
                "--prune",
                "--force",
                os.fspath(repository.path),
                "+HEAD:refs/visual-engineer/source-head",
                "+refs/heads/*:refs/heads/*",
            ],
            failure=FailureCode.REPOSITORY_UNAVAILABLE,
        )
        self._run(
            ["-C", os.fspath(mirror), "cat-file", "-e", f"{source_revision}^{{commit}}"],
            failure=FailureCode.SOURCE_REVISION_MISMATCH,
        )
        return mirror

    def create_detached_worktree(
        self,
        mirror: Path,
        workspace_id: uuid.UUID,
        source_revision: str,
    ) -> Path:
        workspace = self.workspace_path(workspace_id)
        if workspace.exists():
            raise GitOperationError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)
        self._run(
            ["-C", os.fspath(mirror), "worktree", "prune", "--expire=now"],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
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
        )
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
        )

    def discard_worktree(self, mirror: Path, workspace: Path) -> None:
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
        )
        if workspace.exists():
            raise GitOperationError(FailureCode.WORKSPACE_STATE_INVALID)
        self._run(
            ["-C", os.fspath(mirror), "worktree", "prune", "--expire=now"],
            failure=FailureCode.WORKSPACE_STATE_INVALID,
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
    ) -> bytes:
        if any("\x00" in argument for argument in arguments):
            raise GitOperationError(FailureCode.PATH_INVALID)
        command = [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
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
            "protocol.file.allow=always",
            *arguments,
        ]
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": "/nonexistent",
            "XDG_CONFIG_HOME": "/nonexistent",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_LFS_SKIP_SMUDGE": "1",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
        try:
            completed = subprocess.run(
                command,
                env=environment,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=self._settings.git_timeout_seconds,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GitOperationError(failure) from exc
        if completed.returncode not in allowed_returncodes:
            raise GitOperationError(failure)
        return completed.stdout


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


def _status_code(code: str) -> WorkspaceStatusCode:
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
