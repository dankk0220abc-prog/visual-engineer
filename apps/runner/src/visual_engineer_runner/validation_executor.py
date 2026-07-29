from __future__ import annotations

import hashlib
import os
import re
import selectors
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.safe_fs import SafeWorkspaceFilesystem
from visual_engineer_runner_protocol import (
    FailureCode,
    SideEffectPermit,
    ValidationExecuteJobSpec,
    ValidationExecutionResult,
    compute_validation_artifact_manifest_digest,
    compute_validation_evidence_digest,
    validation_profile,
    validation_result_binding,
)

_FIXTURE_PATH = "sandbox/original.txt"
_SANDBOX_FAILURE_EXIT = 70
_TIMEOUT_EXIT = 124
_CANCELLED_EXIT = 130
_TERMINATION_GRACE_SECONDS = 0.5
_SENSITIVE_OUTPUT = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|"
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:(?:token|secret|password|authorization)\s*[:=]\s*\S{8,}))"
)


class ValidationExecutionError(Exception):
    def __init__(self, code: FailureCode) -> None:
        super().__init__(code.value)
        self.code = code


class ValidationExecutor:
    def __init__(self, settings: RunnerSettings) -> None:
        self._settings = settings

    def execute(
        self,
        spec: ValidationExecuteJobSpec,
        *,
        cancel_event: threading.Event,
        side_effect_permit: SideEffectPermit,
        filesystem: SafeWorkspaceFilesystem,
        canonical_workspace: Path,
    ) -> ValidationExecutionResult:
        profile = validation_profile(spec.profile_id)
        if profile is None or profile.version != spec.profile_version:
            raise ValidationExecutionError(FailureCode.VALIDATION_PROFILE_DENIED)
        if (
            spec.timeout_seconds != profile.timeout_seconds
            or spec.max_output_bytes != profile.max_output_bytes
            or spec.max_artifact_bytes != profile.max_artifact_bytes
            or spec.max_artifact_count != profile.max_artifact_count
            or spec.execution_grant.validation_cpu_seconds != profile.cpu_seconds
            or spec.execution_grant.validation_memory_bytes != profile.memory_bytes
            or spec.execution_grant.validation_pid_limit != profile.pid_limit
            or spec.execution_grant.validation_fd_limit != profile.fd_limit
        ):
            raise ValidationExecutionError(FailureCode.VALIDATION_PROFILE_DENIED)

        root = self._create_sandbox(spec.validation_run_id)
        started_at = datetime.now(UTC)
        started = time.monotonic()
        process: subprocess.Popen[bytes] | None = None
        try:
            roots = self._materialize(root, filesystem)
            environment = {
                "HOME": str(roots["home"]),
                "LANG": "C.UTF-8",
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "TMPDIR": str(roots["tmp"]),
                "XDG_CACHE_HOME": str(roots["home"] / ".cache"),
            }
            if tuple(
                sorted(
                    (
                        key,
                        (
                            "<validation-home-root>"
                            if value == str(roots["home"])
                            else "<validation-tmp-root>"
                            if value == str(roots["tmp"])
                            else "<validation-home-root>/.cache"
                            if value == str(roots["home"] / ".cache")
                            else value
                        ),
                    )
                    for key, value in environment.items()
                )
            ) != tuple(sorted(profile.fixed_environment)):
                raise ValidationExecutionError(FailureCode.VALIDATION_PROFILE_DENIED)
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    str(Path(__file__).with_name("validation_worker.py")),
                    str(roots["input"]),
                    str(roots["scratch"]),
                    str(roots["output"]),
                    str(roots["home"]),
                    str(roots["tmp"]),
                    str(canonical_workspace),
                    str(profile.cpu_seconds),
                    str(profile.memory_bytes),
                    str(profile.pid_limit),
                    str(profile.fd_limit),
                    str(profile.max_output_bytes),
                ],
                cwd=roots["input"],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                close_fds=True,
                start_new_session=True,
            )
            (
                exit_code,
                stdout_bytes,
                stderr_bytes,
                stdout_truncated,
                stderr_truncated,
                timed_out,
                cancelled,
            ) = self._collect(
                process,
                timeout_seconds=profile.timeout_seconds,
                output_limit=profile.max_output_bytes,
                cancel_event=cancel_event,
            )
            process = None
            if exit_code == _SANDBOX_FAILURE_EXIT:
                raise ValidationExecutionError(FailureCode.VALIDATION_SANDBOX_UNAVAILABLE)
            if self._artifact_inventory(roots["output"]) != (0, 0):
                raise ValidationExecutionError(FailureCode.VALIDATION_ARTIFACT_LIMIT_EXCEEDED)
            stdout, stdout_redactions = self._sanitize_output(
                stdout_bytes,
                root=root,
                canonical_workspace=canonical_workspace,
            )
            stderr, stderr_redactions = self._sanitize_output(
                stderr_bytes,
                root=root,
                canonical_workspace=canonical_workspace,
            )
            completed_at = datetime.now(UTC)
        except ValidationExecutionError:
            if process is not None:
                self._terminate_process_group(process)
            raise
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            if process is not None:
                self._terminate_process_group(process)
            raise ValidationExecutionError(FailureCode.VALIDATION_SANDBOX_UNAVAILABLE) from exc
        finally:
            self._cleanup_sandbox(root)

        artifacts: list[dict[str, object]] = []
        artifact_manifest_digest = compute_validation_artifact_manifest_digest(artifacts)
        result_binding = validation_result_binding(spec, side_effect_permit)
        result = ValidationExecutionResult(
            **result_binding,
            validation_run_id=spec.validation_run_id,
            workspace_id=spec.workspace_id,
            checkpoint_id=spec.checkpoint_id,
            checkpoint_fingerprint=spec.checkpoint_fingerprint,
            profile_id=profile.profile_id,
            profile_version=profile.version,
            fixed_argv=list(profile.safe_argv),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round((time.monotonic() - started) * 1000, 3),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            redaction_count=stdout_redactions + stderr_redactions,
            timed_out=timed_out,
            cancelled=cancelled,
            network_isolated=True,
            filesystem_isolated=True,
            sandbox_cleaned=True,
            artifact_count=0,
            artifact_bytes=0,
            artifacts=[],
            artifact_manifest_digest=artifact_manifest_digest,
            side_effect_permit_id=side_effect_permit.id,
        )
        result.evidence_digest = compute_validation_evidence_digest(result)
        return result

    def _create_sandbox(self, validation_run_id: uuid.UUID) -> Path:
        self._require_safe_validation_root()
        root = self._settings.validation_root / f"validation-{validation_run_id.hex}"
        try:
            os.mkdir(root, mode=0o700)
        except FileExistsError as exc:
            raise ValidationExecutionError(FailureCode.VALIDATION_SANDBOX_DENIED) from exc
        except OSError as exc:
            raise ValidationExecutionError(FailureCode.VALIDATION_SANDBOX_UNAVAILABLE) from exc
        return root

    def _require_safe_validation_root(self) -> None:
        root = self._settings.validation_root
        try:
            descriptor = os.open(
                root,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as exc:
            raise ValidationExecutionError(FailureCode.VALIDATION_SANDBOX_UNAVAILABLE) from exc
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISDIR(metadata.st_mode):
                raise ValidationExecutionError(FailureCode.VALIDATION_SANDBOX_DENIED)
        finally:
            os.close(descriptor)

    @staticmethod
    def _materialize(
        root: Path,
        filesystem: SafeWorkspaceFilesystem,
    ) -> dict[str, Path]:
        roots = {name: root / name for name in ("input", "scratch", "output", "home", "tmp")}
        for path in roots.values():
            os.mkdir(path, mode=0o700)
        sandbox = roots["input"] / "sandbox"
        os.mkdir(sandbox, mode=0o700)
        source = filesystem.read_text(_FIXTURE_PATH, 4096)
        target = sandbox / "original.txt"
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o400,
        )
        try:
            data = source.content.encode("utf-8")
            if hashlib.sha256(data).hexdigest() != source.sha256:
                raise ValidationExecutionError(FailureCode.VALIDATION_CHECKPOINT_MISMATCH)
            written = 0
            while written < len(data):
                written += os.write(descriptor, data[written:])
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return roots

    @staticmethod
    def _collect(
        process: subprocess.Popen[bytes],
        *,
        timeout_seconds: float,
        output_limit: int,
        cancel_event: threading.Event,
    ) -> tuple[int, bytes, bytes, bool, bool, bool, bool]:
        if process.stdout is None or process.stderr is None:
            raise ValidationExecutionError(FailureCode.VALIDATION_SANDBOX_UNAVAILABLE)
        selector = selectors.DefaultSelector()
        stdout_descriptor = process.stdout.fileno()
        stderr_descriptor = process.stderr.fileno()
        streams = {
            stdout_descriptor: ("stdout", bytearray()),
            stderr_descriptor: ("stderr", bytearray()),
        }
        for descriptor in streams:
            os.set_blocking(descriptor, False)
            selector.register(descriptor, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout_seconds
        process_group_id = process.pid
        timed_out = False
        cancelled = False
        truncated = {"stdout": False, "stderr": False}
        terminated = False
        try:
            while True:
                return_code = process.poll()
                group_alive = ValidationExecutor._process_group_alive(process_group_id)
                if not selector.get_map() and return_code is not None and not group_alive:
                    break
                if not terminated and cancel_event.is_set():
                    cancelled = True
                    terminated = True
                    ValidationExecutor._terminate_process_group(process)
                elif not terminated and time.monotonic() >= deadline:
                    timed_out = True
                    terminated = True
                    ValidationExecutor._terminate_process_group(process)
                if selector.get_map():
                    events = selector.select(timeout=0.05)
                else:
                    time.sleep(0.01)
                    events = []
                for key, _ in events:
                    descriptor = int(key.fd)
                    try:
                        chunk = os.read(descriptor, 4096)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(descriptor)
                        continue
                    stream_name, buffer = streams[descriptor]
                    retained = sum(len(stream_buffer) for _, stream_buffer in streams.values())
                    remaining = output_limit - retained
                    if remaining > 0:
                        buffer.extend(chunk[:remaining])
                    if len(chunk) > max(remaining, 0):
                        truncated[stream_name] = True
            exit_code = process.wait()
            ValidationExecutor._ensure_process_group_absent(process_group_id)
        finally:
            selector.close()
            process.stdout.close()
            process.stderr.close()
        if timed_out:
            exit_code = _TIMEOUT_EXIT
        elif cancelled:
            exit_code = _CANCELLED_EXIT
        return (
            exit_code,
            bytes(streams[stdout_descriptor][1]),
            bytes(streams[stderr_descriptor][1]),
            truncated["stdout"],
            truncated["stderr"],
            timed_out,
            cancelled,
        )

    @staticmethod
    def _signal_process_group(process: subprocess.Popen[bytes], signal_number: int) -> None:
        try:
            os.killpg(process.pid, signal_number)
        except ProcessLookupError:
            return
        except OSError as exc:
            raise ValidationExecutionError(FailureCode.VALIDATION_PROCESS_REMAINED) from exc

    @staticmethod
    def _ensure_process_group_absent(process_group_id: int) -> None:
        if ValidationExecutor._process_group_alive(process_group_id):
            raise ValidationExecutionError(FailureCode.VALIDATION_PROCESS_REMAINED)

    @staticmethod
    def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
        process.poll()
        if ValidationExecutor._process_group_alive(process.pid):
            ValidationExecutor._signal_process_group(process, signal.SIGTERM)
        grace_deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
        while time.monotonic() < grace_deadline:
            process.poll()
            if not ValidationExecutor._process_group_alive(process.pid):
                break
            time.sleep(0.01)
        if ValidationExecutor._process_group_alive(process.pid):
            ValidationExecutor._signal_process_group(process, signal.SIGKILL)
        kill_deadline = time.monotonic() + _TERMINATION_GRACE_SECONDS
        while time.monotonic() < kill_deadline:
            process.poll()
            if not ValidationExecutor._process_group_alive(process.pid):
                break
            time.sleep(0.01)
        ValidationExecutor._ensure_process_group_absent(process.pid)
        try:
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise ValidationExecutionError(FailureCode.VALIDATION_PROCESS_REMAINED) from exc

    @staticmethod
    def _process_group_alive(process_group_id: int) -> bool:
        try:
            os.killpg(process_group_id, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # Darwin can report EPERM for a just-reaped empty process group.
            # A live same-UID descendant remains signalable and returns success.
            return False
        return True

    @staticmethod
    def _artifact_inventory(output_root: Path) -> tuple[int, int]:
        descriptor = os.open(
            output_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        )
        try:
            count = 0
            total = 0
            with os.scandir(descriptor) as entries:
                for entry in entries:
                    metadata = entry.stat(follow_symlinks=False)
                    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                        raise ValidationExecutionError(
                            FailureCode.VALIDATION_ARTIFACT_LIMIT_EXCEEDED
                        )
                    count += 1
                    total += metadata.st_size
            return count, total
        finally:
            os.close(descriptor)

    @staticmethod
    def _sanitize_output(
        value: bytes,
        *,
        root: Path,
        canonical_workspace: Path,
    ) -> tuple[str, int]:
        text = value.decode("utf-8", "replace")
        redactions = 0
        for sensitive_path in (str(root), str(canonical_workspace)):
            occurrences = text.count(sensitive_path)
            if occurrences:
                text = text.replace(sensitive_path, "<redacted-path>")
                redactions += occurrences
        text, secret_redactions = _SENSITIVE_OUTPUT.subn("<redacted-secret>", text)
        return text, redactions + secret_redactions

    @staticmethod
    def _cleanup_sandbox(root: Path) -> None:
        if not root.exists() and not root.is_symlink():
            return
        try:
            root_metadata = root.lstat()
            if not stat.S_ISDIR(root_metadata.st_mode) or stat.S_ISLNK(root_metadata.st_mode):
                raise ValidationExecutionError(FailureCode.VALIDATION_CLEANUP_FAILED)
            for current, directory_names, file_names in os.walk(root, topdown=False):
                current_path = Path(current)
                for name in file_names:
                    path = current_path / name
                    metadata = path.lstat()
                    if stat.S_ISDIR(metadata.st_mode):
                        raise ValidationExecutionError(FailureCode.VALIDATION_CLEANUP_FAILED)
                    path.unlink()
                for name in directory_names:
                    path = current_path / name
                    metadata = path.lstat()
                    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                        raise ValidationExecutionError(FailureCode.VALIDATION_CLEANUP_FAILED)
                    path.rmdir()
            root.rmdir()
        except ValidationExecutionError:
            raise
        except OSError as exc:
            raise ValidationExecutionError(FailureCode.VALIDATION_CLEANUP_FAILED) from exc
