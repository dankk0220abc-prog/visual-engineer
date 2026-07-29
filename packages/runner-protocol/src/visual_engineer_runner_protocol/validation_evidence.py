from typing import Any

from visual_engineer_runner_protocol.canonical import (
    compute_validation_environment_digest,
    compute_validation_execution_envelope_digest,
    compute_validation_fencing_token,
    compute_validation_fixed_argv_digest,
)
from visual_engineer_runner_protocol.models import (
    SideEffectPermit,
    ValidationExecuteJobSpec,
    WorkspaceOperation,
)
from visual_engineer_runner_protocol.profiles import validation_profile


def validation_result_binding(
    spec: ValidationExecuteJobSpec,
    permit: SideEffectPermit,
) -> dict[str, Any]:
    profile = validation_profile(spec.profile_id)
    if profile is None or profile.version != spec.profile_version:
        raise ValueError("validation Profile is unavailable")
    fixed_argv_digest = compute_validation_fixed_argv_digest(profile.safe_argv)
    fixed_environment_digest = compute_validation_environment_digest(profile.fixed_environment)
    fencing_token = compute_validation_fencing_token(
        {
            "runner_id": permit.runner_id,
            "job_id": permit.job_id,
            "attempt_id": permit.attempt_id,
            "lease_id": permit.lease_id,
            "permit_id": permit.id,
            "permit_sequence": permit.sequence,
            "permit_operation_digest": permit.operation_digest,
            "permit_expires_at": permit.expires_at,
        }
    )
    execution_envelope_digest = compute_validation_execution_envelope_digest(
        {
            "envelope_version": 1,
            "result_schema_version": spec.result_schema_version,
            "runner_id": permit.runner_id,
            "job_id": permit.job_id,
            "validation_run_id": spec.validation_run_id,
            "validation_step_id": spec.validation_step_id,
            "attempt_id": permit.attempt_id,
            "lease_id": permit.lease_id,
            "grant_id": spec.execution_grant.id,
            "grant_policy_hash": spec.execution_grant.policy_hash,
            "profile_id": spec.profile_id,
            "profile_version": spec.profile_version,
            "source_revision": spec.execution_grant.source_revision,
            "checkpoint_id": spec.checkpoint_id,
            "checkpoint_fingerprint": spec.checkpoint_fingerprint,
            "validation_policy_digest": spec.validation_policy_digest,
            "fixed_operation": WorkspaceOperation.VALIDATE,
            "fixed_argv_digest": fixed_argv_digest,
            "fixed_cwd": profile.fixed_cwd,
            "fixed_environment_digest": fixed_environment_digest,
            "budgets": {
                "timeout_seconds": spec.timeout_seconds,
                "max_output_bytes": spec.max_output_bytes,
                "max_artifact_bytes": spec.max_artifact_bytes,
                "max_artifact_count": spec.max_artifact_count,
            },
            "permit": {
                "id": permit.id,
                "sequence": permit.sequence,
                "operation_digest": permit.operation_digest,
                "expires_at": permit.expires_at,
            },
            "fencing_token": fencing_token,
        }
    )
    return {
        "result_schema_version": spec.result_schema_version,
        "validation_step_id": spec.validation_step_id,
        "source_revision": spec.execution_grant.source_revision,
        "policy_digest": spec.validation_policy_digest,
        "fixed_operation": WorkspaceOperation.VALIDATE,
        "fixed_argv_digest": fixed_argv_digest,
        "fixed_cwd": profile.fixed_cwd,
        "fixed_environment_digest": fixed_environment_digest,
        "side_effect_permit_sequence": permit.sequence,
        "side_effect_permit_digest": permit.operation_digest,
        "fencing_token": fencing_token,
        "execution_envelope_digest": execution_envelope_digest,
    }
