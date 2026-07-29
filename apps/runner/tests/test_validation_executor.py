from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from visual_engineer_runner.validation_executor import (
    _CANCELLED_EXIT,
    _TIMEOUT_EXIT,
    ValidationExecutionError,
    ValidationExecutor,
)
from visual_engineer_runner.validation_worker import _run_profile
from visual_engineer_runner_protocol import FailureCode


def _process(source: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", source],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
    )


def test_collect_caps_both_streams_without_deadlock() -> None:
    process = _process("import os;os.write(1, b'a' * 8192);os.write(2, b'b' * 8192)")
    result = ValidationExecutor._collect(
        process,
        timeout_seconds=5,
        output_limit=1024,
        cancel_event=threading.Event(),
    )

    exit_code, stdout, stderr, stdout_truncated, stderr_truncated, timed_out, cancelled = result
    assert exit_code == 0
    assert len(stdout) + len(stderr) == 1024
    assert set(stdout) <= {ord("a")}
    assert set(stderr) <= {ord("b")}
    assert stdout_truncated is True
    assert stderr_truncated is True
    assert timed_out is False
    assert cancelled is False


def test_collect_timeout_terminates_and_reaps_the_process_group() -> None:
    process = _process("import time; time.sleep(30)")
    result = ValidationExecutor._collect(
        process,
        timeout_seconds=1,
        output_limit=1024,
        cancel_event=threading.Event(),
    )

    assert result[0] == _TIMEOUT_EXIT
    assert result[5] is True
    assert result[6] is False
    with pytest.raises(ProcessLookupError):
        os.killpg(process.pid, 0)


def test_collect_cancel_terminates_and_reaps_the_process_group() -> None:
    process = _process("import time; time.sleep(30)")
    cancel = threading.Event()
    cancel.set()
    result = ValidationExecutor._collect(
        process,
        timeout_seconds=5,
        output_limit=1024,
        cancel_event=cancel,
    )

    assert result[0] == _CANCELLED_EXIT
    assert result[5] is False
    assert result[6] is True
    with pytest.raises(ProcessLookupError):
        os.killpg(process.pid, 0)


def test_cleanup_removes_only_the_exact_disposable_root(tmp_path: Path) -> None:
    sibling = tmp_path / "sibling"
    sibling.mkdir()
    marker = sibling / "preserve.txt"
    marker.write_text("preserve\n", encoding="utf-8")
    root = tmp_path / "validation-exact"
    nested = root / "input" / "sandbox"
    nested.mkdir(parents=True)
    (nested / "original.txt").write_text("fixture\n", encoding="utf-8")

    ValidationExecutor._cleanup_sandbox(root)

    assert not root.exists()
    assert marker.read_text(encoding="utf-8") == "preserve\n"


def test_cleanup_rejects_a_symlink_root_without_following_it(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    marker = target / "preserve.txt"
    marker.write_text("preserve\n", encoding="utf-8")
    root = tmp_path / "validation-link"
    root.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValidationExecutionError) as raised:
        ValidationExecutor._cleanup_sandbox(root)

    assert raised.value.code == FailureCode.VALIDATION_CLEANUP_FAILED
    assert marker.read_text(encoding="utf-8") == "preserve\n"


def test_fixed_profiles_select_only_system_owned_contract_and_manifest_modes(
    tmp_path: Path,
) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    fixture = sandbox / "original.txt"
    fixture.write_bytes(b"Original fixture text.\n")
    fixture_descriptor = os.open(fixture, os.O_RDONLY | os.O_NOFOLLOW)
    sandbox_descriptor = os.open(
        sandbox,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    try:
        assert (
            _run_profile(
                "fixture-python-stdlib-v1",
                fixture_descriptor,
                sandbox_descriptor,
            )
            == 0
        )
        assert (
            _run_profile(
                "fixture-python-manifest-v1",
                fixture_descriptor,
                sandbox_descriptor,
            )
            == 0
        )
        assert _run_profile("unknown-profile", fixture_descriptor, sandbox_descriptor) == 70
        (sandbox / "injected.txt").write_text("forbidden\n", encoding="utf-8")
        assert (
            _run_profile(
                "fixture-python-manifest-v1",
                fixture_descriptor,
                sandbox_descriptor,
            )
            == 1
        )
    finally:
        os.close(fixture_descriptor)
        os.close(sandbox_descriptor)
