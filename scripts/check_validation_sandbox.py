from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
WORKER = (
    REPOSITORY_ROOT / "apps" / "runner" / "src" / "visual_engineer_runner" / "validation_worker.py"
)
PASSING_INPUT = REPOSITORY_ROOT / "apps" / "runner" / "tests" / "fixtures" / "validation-input"
FAILING_INPUT = (
    REPOSITORY_ROOT / "apps" / "runner" / "tests" / "fixtures" / "validation-input-failing"
)
EXECUTOR_PROBE = REPOSITORY_ROOT / "scripts" / "validation_executor_probe.py"
RUNNER_SOURCE = REPOSITORY_ROOT / "apps" / "runner" / "src"
PROTOCOL_SOURCE = REPOSITORY_ROOT / "packages" / "runner-protocol" / "src"
IMAGE = os.environ.get("VALIDATION_RUNNER_IMAGE", "visualengineer-runner:latest")

EXPECTED_BOUNDARY_STDOUT = (
    "VE_VALIDATION_SANDBOX_FILESYSTEM_DENIED\nVE_VALIDATION_SANDBOX_NETWORK_DENIED\n"
)


def _docker_command(
    input_root: Path,
    *,
    profile_id: str,
    output_budget: int,
) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--read-only",
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--user",
        "10001:10001",
        "--memory",
        "192m",
        "--pids-limit",
        "16",
        "--mount",
        f"type=bind,src={WORKER},dst=/app/apps/runner/src/"
        "visual_engineer_runner/validation_worker.py,readonly",
        "--mount",
        f"type=bind,src={input_root},dst=/validation/input,readonly",
        "--tmpfs",
        "/validation/scratch:rw,noexec,nosuid,nodev,mode=0700,uid=10001,gid=10001",
        "--tmpfs",
        "/validation/output:rw,noexec,nosuid,nodev,mode=0700,uid=10001,gid=10001",
        "--tmpfs",
        "/validation/home:rw,noexec,nosuid,nodev,mode=0700,uid=10001,gid=10001",
        "--tmpfs",
        "/validation/tmp:rw,noexec,nosuid,nodev,mode=0700,uid=10001,gid=10001",
        "--tmpfs",
        "/canonical:rw,noexec,nosuid,nodev,mode=0700,uid=10001,gid=10001",
        "--entrypoint",
        "python",
        IMAGE,
        "-I",
        "-S",
        "/app/apps/runner/src/visual_engineer_runner/validation_worker.py",
        profile_id,
        "/validation/input",
        "/validation/scratch",
        "/validation/output",
        "/validation/home",
        "/validation/tmp",
        "/canonical",
        "5",
        str(128 * 1024 * 1024),
        "8",
        "64",
        str(output_budget),
    ]


def _run(
    input_root: Path,
    *,
    profile_id: str,
    output_budget: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _docker_command(
            input_root,
            profile_id=profile_id,
            output_budget=output_budget,
        ),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _run_executor_probe() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--read-only",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "10001:10001",
            "--memory",
            "192m",
            "--pids-limit",
            "16",
            "--mount",
            f"type=bind,src={RUNNER_SOURCE},dst=/app/apps/runner/src,readonly",
            "--mount",
            f"type=bind,src={PROTOCOL_SOURCE},dst=/app/packages/runner-protocol/src,readonly",
            "--mount",
            f"type=bind,src={EXECUTOR_PROBE},dst=/app/scripts/validation_executor_probe.py,"
            "readonly",
            "--tmpfs",
            "/validation-runs:rw,noexec,nosuid,nodev,mode=0700,uid=10001,gid=10001",
            "--tmpfs",
            "/canonical:rw,noexec,nosuid,nodev,mode=0700,uid=10001,gid=10001",
            "--entrypoint",
            "python",
            IMAGE,
            "/app/scripts/validation_executor_probe.py",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def main() -> int:
    for path in (
        WORKER,
        PASSING_INPUT,
        FAILING_INPUT,
        EXECUTOR_PROBE,
        RUNNER_SOURCE,
        PROTOCOL_SOURCE,
    ):
        resolved = path.resolve()
        if not resolved.is_relative_to(REPOSITORY_ROOT) or not resolved.exists():
            raise RuntimeError("Validation sandbox check path escaped or is missing")
    subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )

    profiles = (
        (
            "fixture-python-stdlib-v1",
            8192,
            "VE_VALIDATION_PROFILE_PASS\n",
            "VE_VALIDATION_PROFILE_CONTRACT_MISMATCH\n",
        ),
        (
            "fixture-python-manifest-v1",
            4096,
            "VE_VALIDATION_PROFILE_MANIFEST_PASS\n",
            "VE_VALIDATION_PROFILE_MANIFEST_MISMATCH\n",
        ),
    )
    for profile_id, output_budget, success_marker, failure_marker in profiles:
        passing = _run(
            PASSING_INPUT,
            profile_id=profile_id,
            output_budget=output_budget,
        )
        expected_success = EXPECTED_BOUNDARY_STDOUT + success_marker
        if passing.returncode != 0 or passing.stdout != expected_success or passing.stderr:
            raise RuntimeError(
                f"Validation sandbox {profile_id} success proof failed: "
                f"exit={passing.returncode} stdout={passing.stdout!r} "
                f"stderr={passing.stderr!r}"
            )

        failing = _run(
            FAILING_INPUT,
            profile_id=profile_id,
            output_budget=output_budget,
        )
        if (
            failing.returncode != 1
            or failing.stdout != EXPECTED_BOUNDARY_STDOUT
            or failing.stderr != failure_marker
        ):
            raise RuntimeError(
                f"Validation sandbox {profile_id} failure proof failed: "
                f"exit={failing.returncode} stdout={failing.stdout!r} "
                f"stderr={failing.stderr!r}"
            )

    executor_probe = _run_executor_probe()
    expected_probe = (
        "validation executor probe passed: materialize, fixed argv, "
        "Landlock, seccomp, pass/fail evidence, cleanup\n"
    )
    if (
        executor_probe.returncode != 0
        or executor_probe.stdout != expected_probe
        or executor_probe.stderr
    ):
        raise RuntimeError(
            "Validation Executor integration proof failed: "
            f"exit={executor_probe.returncode} stdout={executor_probe.stdout!r} "
            f"stderr={executor_probe.stderr!r}"
        )

    print(
        "validation sandbox check passed: Landlock filesystem denial, "
        "seccomp network denial, two fixed Profiles pass/fail, bounded exit codes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
