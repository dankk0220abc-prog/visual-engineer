from __future__ import annotations

import hashlib
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.safe_fs import TextFile
from visual_engineer_runner.validation_executor import ValidationExecutor
from visual_engineer_runner_protocol import (
    ExecutionGrantPolicy,
    SideEffectPermit,
    ValidationExecuteJobSpec,
    WorkspaceOperation,
    compute_execution_grant_policy_hash,
    compute_side_effect_job_digest,
    compute_side_effect_permit_digest,
    side_effect_job_binding,
)

SOURCE_REVISION = "a" * 40
CHECKPOINT_FINGERPRINT = hashlib.sha256(b"executor-probe-checkpoint").hexdigest()


class _FixtureFilesystem:
    def __init__(self, content: str) -> None:
        self._content = content

    def read_text(self, relative_path: str, max_bytes: int) -> TextFile:
        if relative_path != "sandbox/original.txt" or max_bytes != 4096:
            raise RuntimeError("executor requested an unexpected Profile input")
        data = self._content.encode("utf-8")
        return TextFile(
            content=self._content,
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
        )


def _grant(workspace_id: uuid.UUID, checkpoint_id: uuid.UUID) -> ExecutionGrantPolicy:
    values = {
        "id": uuid.uuid4(),
        "task_id": uuid.uuid4(),
        "run_id": uuid.uuid4(),
        "plan_id": uuid.uuid4(),
        "repository_handle_id": uuid.uuid4(),
        "repository_opaque_handle": "validation-probe-repository",
        "source_revision": SOURCE_REVISION,
        "snapshot_fingerprint": hashlib.sha256(b"executor-probe-snapshot").hexdigest(),
        "allowed_operations": [WorkspaceOperation.VALIDATE],
        "allowed_paths": ["sandbox/**"],
        "denied_paths": [
            ".git",
            ".git/**",
            ".env",
            ".env.*",
            "**/.env",
            "**/.env.*",
            "**/*credential*",
            "**/*secret*",
            "**/*token*",
            "**/*.key",
            "**/*.pem",
        ],
        "max_files_changed": 1,
        "max_total_write_bytes": 4096,
        "max_single_file_bytes": 4096,
        "max_diff_bytes": 1,
        "workspace_ttl_seconds": 1200,
        "validation_workspace_id": workspace_id,
        "validation_checkpoint_id": checkpoint_id,
        "allowed_validation_profiles": [
            "fixture-python-stdlib-v1:v1",
            "fixture-python-manifest-v1:v1",
        ],
        "max_validation_runs": 4,
        "validation_timeout_seconds": 10,
        "validation_cpu_seconds": 5,
        "validation_memory_bytes": 128 * 1024 * 1024,
        "validation_pid_limit": 8,
        "validation_fd_limit": 64,
        "validation_output_bytes": 8192,
        "validation_artifact_bytes": 0,
        "validation_artifact_count": 0,
        "expires_at": datetime.now(UTC) + timedelta(minutes=5),
        "policy_hash": "0" * 64,
    }
    draft = ExecutionGrantPolicy.model_validate(values)
    values["policy_hash"] = compute_execution_grant_policy_hash(draft)
    return ExecutionGrantPolicy.model_validate(values)


def _spec(
    grant: ExecutionGrantPolicy,
    workspace_id: uuid.UUID,
    checkpoint_id: uuid.UUID,
    validation_run_id: uuid.UUID,
    profile_id: str,
) -> ValidationExecuteJobSpec:
    manifest = profile_id == "fixture-python-manifest-v1"
    return ValidationExecuteJobSpec(
        validation_run_id=validation_run_id,
        validation_step_id="fixture-manifest" if manifest else "fixture-contract",
        workspace_id=workspace_id,
        execution_grant=grant,
        profile_id=profile_id,
        checkpoint_id=checkpoint_id,
        checkpoint_fingerprint=CHECKPOINT_FINGERPRINT,
        timeout_seconds=10,
        max_output_bytes=4096 if manifest else 8192,
        max_artifact_bytes=0,
        max_artifact_count=0,
    )


def _permit(spec: ValidationExecuteJobSpec, job_id: uuid.UUID) -> SideEffectPermit:
    binding = side_effect_job_binding(spec)
    now = datetime.now(UTC)
    values = {
        "id": uuid.uuid4(),
        "sequence": 1,
        "runner_id": uuid.uuid4(),
        "job_id": job_id,
        "attempt_id": uuid.uuid4(),
        "lease_id": uuid.uuid4(),
        "grant_id": spec.execution_grant.id,
        "workspace_id": spec.workspace_id,
        "repository_handle_id": spec.execution_grant.repository_handle_id,
        "operation": WorkspaceOperation.VALIDATE,
        "relative_path": None,
        "expected_current": binding["expected_current"],
        "proposed_digest": binding["proposed_digest"],
        "job_digest": compute_side_effect_job_digest(spec),
        "operation_digest": "0" * 64,
        "policy_hash": spec.execution_grant.policy_hash,
        "source_revision": spec.execution_grant.source_revision,
        "issued_at": now,
        "consumed_at": now,
        "expires_at": now + timedelta(minutes=1),
    }
    draft = SideEffectPermit.model_validate(values)
    values["operation_digest"] = compute_side_effect_permit_digest(draft)
    return SideEffectPermit.model_validate(values)


def main() -> int:
    settings = RunnerSettings(
        credential_path=Path("/credentials/credentials.json"),
        ownership_key_path=Path("/credentials/ownership.key"),
        mirror_root=Path("/mirrors"),
        workspace_root=Path("/workspaces"),
        registry_root=Path("/registry"),
        validation_root=Path("/validation-runs"),
    )
    executor = ValidationExecutor(settings)
    workspace_id = uuid.uuid4()
    checkpoint_id = uuid.uuid4()
    grant = _grant(workspace_id, checkpoint_id)
    expected_outcomes = (
        ("fixture-python-stdlib-v1", "Original fixture text.\n", 0),
        ("fixture-python-stdlib-v1", "Changed fixture text.\n", 1),
        ("fixture-python-manifest-v1", "Original fixture text.\n", 0),
        ("fixture-python-manifest-v1", "Changed fixture text.\n", 1),
    )
    for profile_id, content, expected_exit in expected_outcomes:
        validation_run_id = uuid.uuid4()
        spec = _spec(
            grant,
            workspace_id,
            checkpoint_id,
            validation_run_id,
            profile_id,
        )
        result = executor.execute(
            spec,
            cancel_event=threading.Event(),
            side_effect_permit=_permit(spec, uuid.uuid4()),
            filesystem=_FixtureFilesystem(content),  # type: ignore[arg-type]
            canonical_workspace=Path("/canonical"),
        )
        if (
            result.exit_code != expected_exit
            or not result.network_isolated
            or not result.filesystem_isolated
            or not result.sandbox_cleaned
            or result.artifact_count != 0
            or "VE_VALIDATION_SANDBOX_FILESYSTEM_DENIED" not in result.stdout
            or "VE_VALIDATION_SANDBOX_NETWORK_DENIED" not in result.stdout
        ):
            raise RuntimeError("Validation Executor result violated the closed Profile contract")
    if any(Path("/validation-runs").iterdir()):
        raise RuntimeError("Validation Executor left disposable sandbox inventory")
    print(
        "validation executor probe passed: materialize, fixed argv, "
        "Landlock, seccomp, pass/fail evidence, cleanup"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
