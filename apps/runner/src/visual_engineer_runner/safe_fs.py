from __future__ import annotations

import errno
import fnmatch
import hashlib
import os
import stat
import threading
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from visual_engineer_runner_protocol import (
    ExecutionGrantPolicy,
    FailureCode,
    WorkspaceEntry,
    WorkspaceEntryType,
    WorkspaceWriteMode,
)

MAX_RELATIVE_PATH_BYTES = 512
MAX_PATH_COMPONENTS = 32
_OPEN_BASE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)


class SafeFilesystemError(Exception):
    def __init__(self, code: FailureCode) -> None:
        super().__init__(code.value)
        self.code = code


@dataclass(frozen=True)
class TextFile:
    content: str
    sha256: str
    size: int


@dataclass(frozen=True)
class WriteOutcome:
    relative_path: str
    operation: WorkspaceWriteMode
    sha256: str
    size: int
    created: bool


def parse_relative_path(value: str) -> tuple[str, ...]:
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or "\x00" in value
        or len(value.encode("utf-8")) > MAX_RELATIVE_PATH_BYTES
    ):
        raise SafeFilesystemError(FailureCode.PATH_INVALID)
    components = value.split("/")
    if len(components) > MAX_PATH_COMPONENTS or any(
        not component
        or component in {".", ".."}
        or any(ord(character) < 32 or ord(character) == 127 for character in component)
        for component in components
    ):
        raise SafeFilesystemError(FailureCode.PATH_INVALID)
    return tuple(components)


class SafeWorkspaceFilesystem:
    def __init__(
        self,
        root: Path,
        grant: ExecutionGrantPolicy,
        *,
        cancel_event: threading.Event | None = None,
        commit_delay_ms: int = 0,
    ) -> None:
        if not root.is_absolute():
            raise SafeFilesystemError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)
        self._root = root
        self._grant = grant
        self._cancel_event = cancel_event or threading.Event()
        self._commit_delay_ms = commit_delay_ms
        try:
            descriptor = os.open(root, _OPEN_BASE | os.O_DIRECTORY)
        except OSError as exc:
            raise SafeFilesystemError(FailureCode.WORKSPACE_NOT_FOUND) from exc
        try:
            identity = os.fstat(descriptor)
            if not stat.S_ISDIR(identity.st_mode):
                raise SafeFilesystemError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)
            self.root_device = identity.st_dev
            self.root_inode = identity.st_ino
        finally:
            os.close(descriptor)

    def authorize(self, relative_path: str, *, directory: bool = False) -> tuple[str, ...]:
        components = parse_relative_path(relative_path)
        normalized = "/".join(components)
        folded = [component.casefold() for component in components]
        if ".git" in folded:
            raise SafeFilesystemError(FailureCode.PATH_DENIED)
        if _is_sensitive(folded):
            raise SafeFilesystemError(FailureCode.SENSITIVE_PATH_DENIED)
        if any(_controlled_glob_match(pattern, normalized) for pattern in self._grant.denied_paths):
            if _is_sensitive(folded):
                raise SafeFilesystemError(FailureCode.SENSITIVE_PATH_DENIED)
            raise SafeFilesystemError(FailureCode.PATH_DENIED)
        allowed = any(
            _controlled_glob_match(pattern, normalized)
            or (directory and _could_contain_allowed_path(pattern, normalized))
            for pattern in self._grant.allowed_paths
        )
        if not allowed:
            raise SafeFilesystemError(FailureCode.PATH_DENIED)
        return components

    def read_text(self, relative_path: str, max_bytes: int) -> TextFile:
        components = self.authorize(relative_path)
        maximum = min(max_bytes, self._grant.max_single_file_bytes)
        with self._parent_descriptor(components) as (parent, leaf):
            descriptor = self._open_regular_leaf(parent, leaf)
            try:
                return self._read_text_descriptor(descriptor, maximum)
            finally:
                os.close(descriptor)

    def list_directory(
        self,
        relative_directory: str,
        *,
        depth: int,
        max_entries: int,
    ) -> tuple[list[WorkspaceEntry], bool]:
        components = self.authorize(relative_directory, directory=True)
        entries: list[WorkspaceEntry] = []
        truncated = False
        with self._directory_descriptor(components) as directory:
            stack: list[tuple[int, str, int]] = [(os.dup(directory), relative_directory, 1)]
            try:
                while stack:
                    current, prefix, current_depth = stack.pop()
                    try:
                        names = sorted(os.listdir(current), reverse=True)
                        for name in names:
                            relative = f"{prefix}/{name}"
                            try:
                                self.authorize(relative, directory=True)
                            except SafeFilesystemError:
                                continue
                            if len(entries) >= max_entries:
                                truncated = True
                                break
                            try:
                                metadata = os.stat(name, dir_fd=current, follow_symlinks=False)
                            except OSError as exc:
                                raise _filesystem_error(exc) from exc
                            entry_type, digest = self._classify_entry(current, name, metadata)
                            entries.append(
                                WorkspaceEntry(
                                    relative_path=relative,
                                    entry_type=entry_type,
                                    size=metadata.st_size,
                                    sha256=digest,
                                )
                            )
                            if stat.S_ISDIR(metadata.st_mode) and current_depth < depth:
                                try:
                                    child = os.open(
                                        name,
                                        _OPEN_BASE | os.O_DIRECTORY,
                                        dir_fd=current,
                                    )
                                except OSError as exc:
                                    raise _filesystem_error(exc) from exc
                                stack.append((child, relative, current_depth + 1))
                        if truncated:
                            break
                    finally:
                        os.close(current)
            finally:
                for descriptor, _, _ in stack:
                    os.close(descriptor)
        entries.sort(key=lambda item: item.relative_path)
        return entries, truncated

    def write_text(
        self,
        relative_path: str,
        content: str,
        *,
        mode: WorkspaceWriteMode,
        expected_sha256: str | None,
        operation_id: uuid.UUID | None = None,
        recover_interrupted: bool = False,
        before_commit: Callable[[], None] | None = None,
    ) -> WriteOutcome:
        components = self.authorize(relative_path)
        encoded = content.encode("utf-8", "strict")
        if len(encoded) > self._grant.max_single_file_bytes:
            raise SafeFilesystemError(FailureCode.FILE_TOO_LARGE)
        if b"\x00" in encoded:
            raise SafeFilesystemError(FailureCode.BINARY_DENIED)
        with self._parent_descriptor(components) as (parent, leaf):
            desired_sha256 = hashlib.sha256(encoded).hexdigest()
            temporary = (
                f".visual-engineer-write-{operation_id.hex}.tmp"
                if operation_id is not None
                else f".visual-engineer-write-{uuid.uuid4().hex}.tmp"
            )
            if recover_interrupted:
                self._remove_interrupted_temporary(parent, temporary)
                recovered = self._recover_committed_write(
                    parent,
                    leaf,
                    relative_path=relative_path,
                    mode=mode,
                    desired_sha256=desired_sha256,
                    desired_size=len(encoded),
                )
                if recovered is not None:
                    return recovered

            expected_identity: tuple[int, int] | None = None
            if mode == WorkspaceWriteMode.CREATE:
                try:
                    os.stat(leaf, dir_fd=parent, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    raise _filesystem_error(exc) from exc
                else:
                    raise SafeFilesystemError(FailureCode.EXPECTED_ABSENT_CONFLICT)
            else:
                if expected_sha256 is None:
                    raise SafeFilesystemError(FailureCode.CONTENT_CONFLICT)
                existing = self._open_regular_leaf(parent, leaf)
                try:
                    metadata = os.fstat(existing)
                    current = self._read_text_descriptor(
                        existing,
                        self._grant.max_single_file_bytes,
                    )
                    if current.sha256 != expected_sha256:
                        raise SafeFilesystemError(FailureCode.CONTENT_CONFLICT)
                    expected_identity = (metadata.st_dev, metadata.st_ino)
                finally:
                    os.close(existing)

            descriptor: int | None = None
            temporary_exists = False
            try:
                descriptor = os.open(
                    temporary,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | os.O_NOFOLLOW
                    | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=parent,
                )
                temporary_exists = True
                view = memoryview(encoded)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise SafeFilesystemError(FailureCode.ATOMIC_WRITE_FAILED)
                    view = view[written:]
                os.fsync(descriptor)
                os.close(descriptor)
                descriptor = None

                if self._commit_delay_ms and self._cancel_event.wait(self._commit_delay_ms / 1000):
                    raise SafeFilesystemError(FailureCode.WORKSPACE_CANCELLED)
                if self._cancel_event.is_set():
                    raise SafeFilesystemError(FailureCode.WORKSPACE_CANCELLED)
                if before_commit is not None:
                    before_commit()
                if mode == WorkspaceWriteMode.CREATE:
                    try:
                        os.link(
                            temporary,
                            leaf,
                            src_dir_fd=parent,
                            dst_dir_fd=parent,
                            follow_symlinks=False,
                        )
                    except FileExistsError as exc:
                        raise SafeFilesystemError(FailureCode.EXPECTED_ABSENT_CONFLICT) from exc
                    os.unlink(temporary, dir_fd=parent)
                    temporary_exists = False
                else:
                    try:
                        current_metadata = os.stat(
                            leaf,
                            dir_fd=parent,
                            follow_symlinks=False,
                        )
                    except OSError as exc:
                        raise SafeFilesystemError(FailureCode.CONTENT_CONFLICT) from exc
                    if (
                        expected_identity is None
                        or not stat.S_ISREG(current_metadata.st_mode)
                        or current_metadata.st_nlink != 1
                        or (current_metadata.st_dev, current_metadata.st_ino) != expected_identity
                    ):
                        raise SafeFilesystemError(FailureCode.CONTENT_CONFLICT)
                    os.rename(
                        temporary,
                        leaf,
                        src_dir_fd=parent,
                        dst_dir_fd=parent,
                    )
                    temporary_exists = False
                os.fsync(parent)
                written_file = self._open_regular_leaf(parent, leaf)
                try:
                    verified = self._read_text_descriptor(
                        written_file,
                        self._grant.max_single_file_bytes,
                    )
                finally:
                    os.close(written_file)
                if verified.sha256 != desired_sha256 or verified.size != len(encoded):
                    raise SafeFilesystemError(FailureCode.ATOMIC_WRITE_FAILED)
                return WriteOutcome(
                    relative_path=relative_path,
                    operation=mode,
                    sha256=verified.sha256,
                    size=verified.size,
                    created=mode == WorkspaceWriteMode.CREATE,
                )
            except SafeFilesystemError:
                raise
            except OSError as exc:
                raise SafeFilesystemError(FailureCode.ATOMIC_WRITE_FAILED) from exc
            finally:
                if descriptor is not None:
                    os.close(descriptor)
                if temporary_exists:
                    try:
                        os.unlink(temporary, dir_fd=parent)
                        os.fsync(parent)
                    except FileNotFoundError:
                        pass

    def remove_created_file(
        self,
        relative_path: str,
        *,
        expected_sha256: str | None = None,
    ) -> bool:
        components = self.authorize(relative_path)
        with self._parent_descriptor(components) as (parent, leaf):
            try:
                metadata = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                return False
            except OSError as exc:
                raise _filesystem_error(exc) from exc
            if not stat.S_ISREG(metadata.st_mode):
                raise SafeFilesystemError(FailureCode.NOT_REGULAR_FILE)
            if metadata.st_nlink != 1:
                raise SafeFilesystemError(FailureCode.HARDLINK_DENIED)
            if expected_sha256 is not None:
                descriptor = self._open_regular_leaf(parent, leaf)
                try:
                    current = self._read_text_descriptor(
                        descriptor,
                        self._grant.max_single_file_bytes,
                    )
                finally:
                    os.close(descriptor)
                if current.sha256 != expected_sha256:
                    raise SafeFilesystemError(FailureCode.CONTENT_CONFLICT)
            try:
                os.unlink(leaf, dir_fd=parent)
                os.fsync(parent)
            except OSError as exc:
                raise _filesystem_error(exc) from exc
            return True

    def _remove_interrupted_temporary(self, parent: int, temporary: str) -> None:
        try:
            descriptor = os.open(temporary, _OPEN_BASE, dir_fd=parent)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise _filesystem_error(exc) from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise SafeFilesystemError(FailureCode.NOT_REGULAR_FILE)
            if metadata.st_nlink != 1:
                raise SafeFilesystemError(FailureCode.HARDLINK_DENIED)
        finally:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)
        except OSError as exc:
            raise SafeFilesystemError(FailureCode.ATOMIC_WRITE_FAILED) from exc

    def _recover_committed_write(
        self,
        parent: int,
        leaf: str,
        *,
        relative_path: str,
        mode: WorkspaceWriteMode,
        desired_sha256: str,
        desired_size: int,
    ) -> WriteOutcome | None:
        try:
            descriptor = self._open_regular_leaf(parent, leaf)
        except SafeFilesystemError as exc:
            if exc.code == FailureCode.WORKSPACE_NOT_FOUND:
                return None
            raise
        try:
            current = self._read_text_descriptor(
                descriptor,
                self._grant.max_single_file_bytes,
            )
        finally:
            os.close(descriptor)
        if current.sha256 != desired_sha256 or current.size != desired_size:
            return None
        return WriteOutcome(
            relative_path=relative_path,
            operation=mode,
            sha256=current.sha256,
            size=current.size,
            created=mode == WorkspaceWriteMode.CREATE,
        )

    def verify_root_identity(self, device: int, inode: int) -> None:
        try:
            descriptor = os.open(self._root, _OPEN_BASE | os.O_DIRECTORY)
        except OSError as exc:
            raise SafeFilesystemError(FailureCode.WORKSPACE_NOT_FOUND) from exc
        try:
            metadata = os.fstat(descriptor)
            if (metadata.st_dev, metadata.st_ino) != (device, inode):
                raise SafeFilesystemError(FailureCode.WORKSPACE_IDENTITY_MISMATCH)
        finally:
            os.close(descriptor)

    @contextmanager
    def _parent_descriptor(self, components: tuple[str, ...]) -> Iterator[tuple[int, str]]:
        if len(components) < 1:
            raise SafeFilesystemError(FailureCode.PATH_INVALID)
        with self._directory_descriptor(components[:-1]) as parent:
            yield parent, components[-1]

    @contextmanager
    def _directory_descriptor(self, components: tuple[str, ...]) -> Iterator[int]:
        descriptors: list[int] = []
        try:
            current = os.open(self._root, _OPEN_BASE | os.O_DIRECTORY)
            descriptors.append(current)
            for component in components:
                try:
                    current = os.open(
                        component,
                        _OPEN_BASE | os.O_DIRECTORY,
                        dir_fd=current,
                    )
                except OSError as exc:
                    raise _filesystem_error(exc) from exc
                descriptors.append(current)
            yield current
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def _open_regular_leaf(self, parent: int, leaf: str) -> int:
        try:
            initial = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
        except OSError as exc:
            raise _filesystem_error(exc) from exc
        if stat.S_ISLNK(initial.st_mode):
            raise SafeFilesystemError(FailureCode.SYMLINK_DENIED)
        if not stat.S_ISREG(initial.st_mode):
            raise SafeFilesystemError(FailureCode.NOT_REGULAR_FILE)
        if initial.st_nlink != 1:
            raise SafeFilesystemError(FailureCode.HARDLINK_DENIED)
        try:
            descriptor = os.open(leaf, _OPEN_BASE, dir_fd=parent)
        except OSError as exc:
            raise _filesystem_error(exc) from exc
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            os.close(descriptor)
            raise SafeFilesystemError(FailureCode.NOT_REGULAR_FILE)
        if metadata.st_nlink != 1:
            os.close(descriptor)
            raise SafeFilesystemError(FailureCode.HARDLINK_DENIED)
        if (metadata.st_dev, metadata.st_ino) != (initial.st_dev, initial.st_ino):
            os.close(descriptor)
            raise SafeFilesystemError(FailureCode.WORKSPACE_STATE_INVALID)
        return descriptor

    def _read_text_descriptor(self, descriptor: int, max_bytes: int) -> TextFile:
        metadata = os.fstat(descriptor)
        if metadata.st_size > max_bytes:
            raise SafeFilesystemError(FailureCode.FILE_TOO_LARGE)
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        value = b"".join(chunks)
        if len(value) > max_bytes:
            raise SafeFilesystemError(FailureCode.FILE_TOO_LARGE)
        if b"\x00" in value or any(byte < 32 and byte not in {9, 10, 13} for byte in value):
            raise SafeFilesystemError(FailureCode.BINARY_DENIED)
        try:
            content = value.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise SafeFilesystemError(FailureCode.INVALID_UTF8) from exc
        return TextFile(
            content=content,
            sha256=hashlib.sha256(value).hexdigest(),
            size=len(value),
        )

    def _classify_entry(
        self,
        parent: int,
        name: str,
        metadata: os.stat_result,
    ) -> tuple[WorkspaceEntryType, str | None]:
        if stat.S_ISLNK(metadata.st_mode):
            return WorkspaceEntryType.SYMLINK, None
        if stat.S_ISDIR(metadata.st_mode):
            return WorkspaceEntryType.DIRECTORY, None
        if not stat.S_ISREG(metadata.st_mode):
            return WorkspaceEntryType.SPECIAL, None
        if metadata.st_nlink != 1:
            return WorkspaceEntryType.SPECIAL, None
        if metadata.st_size > self._grant.max_single_file_bytes:
            return WorkspaceEntryType.BINARY, None
        try:
            descriptor = os.open(name, _OPEN_BASE, dir_fd=parent)
            try:
                text = self._read_text_descriptor(
                    descriptor,
                    self._grant.max_single_file_bytes,
                )
            finally:
                os.close(descriptor)
        except SafeFilesystemError:
            return WorkspaceEntryType.BINARY, None
        return WorkspaceEntryType.TEXT, text.sha256


def _filesystem_error(exc: OSError) -> SafeFilesystemError:
    if exc.errno in {errno.ELOOP, errno.EMLINK, errno.ENOTDIR}:
        return SafeFilesystemError(FailureCode.SYMLINK_DENIED)
    if exc.errno == errno.ENOENT:
        return SafeFilesystemError(FailureCode.WORKSPACE_NOT_FOUND)
    return SafeFilesystemError(FailureCode.WORKSPACE_STATE_INVALID)


def _is_sensitive(folded_components: list[str]) -> bool:
    for component in folded_components:
        if component == ".env" or component.startswith(".env."):
            return True
        if any(value in component for value in ("credential", "secret", "token")):
            return True
        if component in {"id_rsa", "id_ed25519"}:
            return True
        if component.endswith((".key", ".pem", ".crt", ".cer", ".p12", ".pfx")):
            return True
    return False


def _controlled_glob_match(pattern: str, value: str) -> bool:
    pattern_components = pattern.split("/")
    value_components = value.split("/")

    def match(pattern_index: int, value_index: int) -> bool:
        if pattern_index == len(pattern_components):
            return value_index == len(value_components)
        component = pattern_components[pattern_index]
        if component == "**":
            return match(pattern_index + 1, value_index) or (
                value_index < len(value_components) and match(pattern_index, value_index + 1)
            )
        return (
            value_index < len(value_components)
            and fnmatch.fnmatchcase(value_components[value_index], component)
            and match(pattern_index + 1, value_index + 1)
        )

    return match(0, 0)


def _could_contain_allowed_path(pattern: str, directory: str) -> bool:
    return pattern == directory or pattern.startswith(f"{directory}/")
