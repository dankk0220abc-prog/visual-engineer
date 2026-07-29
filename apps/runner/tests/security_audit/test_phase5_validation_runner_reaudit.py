from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from visual_engineer_runner.validation_executor import _TIMEOUT_EXIT, ValidationExecutor


def _pid_is_absent(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


@pytest.mark.parametrize("iteration", range(2))
def test_reaudit_timeout_kills_multiple_descendants_after_output_closes(
    tmp_path: Path,
    iteration: int,
) -> None:
    """VE-P5-FSR-001: closed pipes cannot hide multiple live descendants."""

    ready_paths = [tmp_path / f"descendant-{iteration}-{index}.pid" for index in range(2)]
    survivor_paths = [tmp_path / f"descendant-{iteration}-{index}.survived" for index in range(2)]
    child_codes = [
        (
            "import os,pathlib,signal,time;"
            "os.close(1);os.close(2);"
            "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
            f"pathlib.Path({str(ready)!r}).write_text(str(os.getpid()));"
            "time.sleep(2);"
            f"pathlib.Path({str(survivor)!r}).touch()"
        )
        for ready, survivor in zip(ready_paths, survivor_paths, strict=True)
    ]
    parent_code = (
        "import pathlib,subprocess,sys,time\n"
        + "\n".join(
            f"subprocess.Popen([sys.executable,'-I','-S','-c',{code!r}])" for code in child_codes
        )
        + "\n"
        + f"paths={[str(path) for path in ready_paths]!r}\n"
        + "deadline=time.monotonic()+1\n"
        + "while not all(pathlib.Path(path).exists() for path in paths) "
        + "and time.monotonic()<deadline:\n"
        + "    time.sleep(0.01)\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", parent_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
    )
    started = time.monotonic()
    descendant_pids: list[int] = []
    try:
        deadline = time.monotonic() + 1
        while not all(path.exists() for path in ready_paths) and time.monotonic() < deadline:
            time.sleep(0.01)
        descendant_pids = [int(path.read_text()) for path in ready_paths]

        result = ValidationExecutor._collect(
            process,
            timeout_seconds=0.15,
            output_limit=1024,
            cancel_event=threading.Event(),
        )
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)

    assert time.monotonic() - started < 1.4
    assert result[0] == _TIMEOUT_EXIT
    assert result[1:5] == (b"", b"", False, False)
    assert result[5:] == (True, False)
    assert process.returncode is not None
    assert process.stdout is not None and process.stdout.closed
    assert process.stderr is not None and process.stderr.closed
    assert not ValidationExecutor._process_group_alive(process.pid)

    absence_deadline = time.monotonic() + 0.75
    while (
        not all(_pid_is_absent(pid) for pid in descendant_pids)
        and time.monotonic() < absence_deadline
    ):
        time.sleep(0.01)
    assert all(_pid_is_absent(pid) for pid in descendant_pids)
    time.sleep(0.2)
    assert not any(path.exists() for path in survivor_paths)


def test_reaudit_normal_command_collects_and_reaps_without_timeout() -> None:
    """VE-P5-FSR-001 control: a legal short command remains unaffected."""

    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-S",
            "-c",
            "import sys;sys.stdout.write('normal-out');sys.stderr.write('normal-err')",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
    )

    result = ValidationExecutor._collect(
        process,
        timeout_seconds=1,
        output_limit=1024,
        cancel_event=threading.Event(),
    )

    assert result == (0, b"normal-out", b"normal-err", False, False, False, False)
    assert process.returncode == 0
    assert process.stdout is not None and process.stdout.closed
    assert process.stderr is not None and process.stderr.closed
    assert not ValidationExecutor._process_group_alive(process.pid)
