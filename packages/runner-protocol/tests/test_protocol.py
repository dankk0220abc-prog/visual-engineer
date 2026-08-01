import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from visual_engineer_runner_protocol import (
    VALIDATION_PROFILE_CATALOG,
    VALIDATION_SUITE_CATALOG,
    Capability,
    ControlledWaitJobSpec,
    DeliveryAuthorizationPolicy,
    DiagnosticResult,
    PermissionEnvelope,
    SideEffectPermit,
    WorkspaceOperation,
    canonical_json_bytes,
    compute_delivery_authorization_policy_hash,
    compute_permission_policy_hash,
    compute_side_effect_permit_digest,
    permission_policy_hash_matches,
    side_effect_permit_digest_matches,
    validate_result_payload,
    validate_safe_error_message,
    validation_suite,
)


def envelope() -> PermissionEnvelope:
    now = datetime.now(UTC)
    values = {
        "id": uuid.uuid4(),
        "job_id": uuid.uuid4(),
        "allowed_capabilities": [Capability.SYSTEM_DIAGNOSTIC_V1],
        "max_runtime_seconds": 10,
        "lease_seconds": 6,
        "max_attempts": 2,
        "max_result_bytes": 8192,
        "issued_at": now,
        "expires_at": now + timedelta(minutes=5),
        "policy_hash": "0" * 64,
    }
    draft = PermissionEnvelope.model_validate(values)
    values["policy_hash"] = compute_permission_policy_hash(draft)
    return PermissionEnvelope.model_validate(values)


def diagnostic(**overrides: object) -> DiagnosticResult:
    started = datetime.now(UTC)
    values: dict[str, object] = {
        "runner_software_version": "0.3.0",
        "python_version": "3.12.13",
        "os_family": "linux",
        "architecture": "arm64",
        "capability_list": [Capability.SYSTEM_DIAGNOSTIC_V1],
        "started_at": started,
        "completed_at": started + timedelta(milliseconds=5),
        "duration_ms": 5.0,
    }
    values.update(overrides)
    return DiagnosticResult.model_validate(values)


def test_permission_envelope_hash_is_canonical_and_tamper_evident() -> None:
    value = envelope()
    assert permission_policy_hash_matches(value, value.policy_hash)

    tampered = value.model_copy(update={"shell_access": True})
    assert not permission_policy_hash_matches(tampered, value.policy_hash)
    reordered = value.model_dump(mode="json")
    reordered["allowed_capabilities"] = list(reversed(reordered["allowed_capabilities"]))
    assert compute_permission_policy_hash(reordered) == value.policy_hash


def test_permission_envelope_rejects_expiry_and_expanded_authority() -> None:
    value = envelope().model_dump()
    value["expires_at"] = value["issued_at"]
    with pytest.raises(ValidationError):
        PermissionEnvelope.model_validate(value)

    value = envelope().model_dump()
    value["repository_access"] = "read"
    with pytest.raises(ValidationError):
        PermissionEnvelope.model_validate(value)

    value = envelope().model_dump()
    value["shell_access"] = True
    with pytest.raises(ValidationError):
        PermissionEnvelope.model_validate(value)

    value = envelope().model_dump()
    value["network_policy"] = "public_internet"
    with pytest.raises(ValidationError):
        PermissionEnvelope.model_validate(value)


def test_closed_job_and_result_schemas_reject_extra_or_sensitive_data() -> None:
    with pytest.raises(ValidationError):
        ControlledWaitJobSpec.model_validate({"duration_ms": 50})
    with pytest.raises(ValidationError):
        ControlledWaitJobSpec.model_validate({"duration_ms": 500, "command": "sleep 1"})

    safe = diagnostic()
    validate_result_payload(safe, max_result_bytes=8192)
    secret_like = diagnostic(architecture="sk-" + "a" * 24)
    with pytest.raises(ValueError, match="sensitive"):
        validate_result_payload(secret_like, max_result_bytes=8192)
    with pytest.raises(ValueError, match="byte limit"):
        validate_result_payload(safe, max_result_bytes=10)
    with pytest.raises(ValidationError):
        DiagnosticResult.model_validate(
            {
                **safe.model_dump(mode="json"),
                "hostname": "local-runner",
                "username": "local-user",
            }
        )


def test_error_message_rejects_secrets_and_absolute_paths() -> None:
    assert validate_safe_error_message("  typed failure  ") == "typed failure"
    with pytest.raises(ValueError):
        validate_safe_error_message("failed at /Users/example/private/file.py")
    with pytest.raises(ValueError):
        validate_safe_error_message("token=dynamic-secret-value")


def test_validation_suite_catalog_is_closed_ordered_and_immutable() -> None:
    assert sorted(VALIDATION_PROFILE_CATALOG) == [
        "fixture-python-manifest-v1",
        "fixture-python-stdlib-v1",
    ]
    assert list(VALIDATION_SUITE_CATALOG) == ["fixture-integrity-suite-v1"]
    suite = validation_suite("fixture-integrity-suite-v1")
    assert suite is not None
    assert suite.reference == "fixture-integrity-suite-v1:v1"
    assert [step.sequence for step in suite.steps] == [1, 2]
    assert [step.step_id for step in suite.steps] == [
        "fixture-contract",
        "fixture-manifest",
    ]
    assert [step.profile_reference for step in suite.steps] == [
        "fixture-python-stdlib-v1:v1",
        "fixture-python-manifest-v1:v1",
    ]
    assert suite.failure_policy == "fail_fast"
    assert suite.total_output_bytes == 10_000
    assert len(suite.policy_digest) == 64
    assert validation_suite("unknown-suite") is None
    with pytest.raises(FrozenInstanceError):
        suite.version = 2  # type: ignore[misc]


def test_side_effect_permit_canonical_digest_is_stable_and_tamper_evident() -> None:
    issued_at = datetime(2026, 7, 28, 9, 0, tzinfo=UTC)
    values = {
        "id": uuid.UUID("0e590b10-b8de-5e57-bc87-c08c82bba2d3"),
        "sequence": 7,
        "runner_id": uuid.UUID("ebec720a-c9e6-578a-b339-0987df9d7f6c"),
        "job_id": uuid.UUID("2600a238-a6ce-5fa0-bb4e-ebd19c46ecaf"),
        "attempt_id": uuid.UUID("f16ee025-ad4f-5f23-81fb-0d084a542202"),
        "lease_id": uuid.UUID("23878c23-581f-5d90-9d7e-76b777cb0614"),
        "grant_id": uuid.UUID("1f270918-857f-5e25-b15a-0d8e870f284c"),
        "workspace_id": uuid.UUID("bb2b41d5-0f33-5a68-af87-13b3f36c9ad7"),
        "repository_handle_id": uuid.UUID("28c7257f-4e98-57e9-9065-296eda010ccd"),
        "operation": WorkspaceOperation.WRITE_TEXT,
        "relative_path": "sandbox/tracked.txt",
        "expected_current": "a" * 64,
        "proposed_digest": "b" * 64,
        "job_digest": "c" * 64,
        "operation_digest": "0" * 64,
        "policy_hash": "d" * 64,
        "source_revision": "e" * 40,
        "issued_at": issued_at,
        "consumed_at": issued_at,
        "expires_at": issued_at + timedelta(seconds=5),
        "state": "consumed",
    }
    digest = compute_side_effect_permit_digest(values)
    values["operation_digest"] = digest
    permit = SideEffectPermit.model_validate(values)

    assert side_effect_permit_digest_matches(permit, digest)
    reversed_values = dict(reversed(list(values.items())))
    assert compute_side_effect_permit_digest(reversed_values) == digest
    assert canonical_json_bytes(values) == canonical_json_bytes(reversed_values)
    assert not side_effect_permit_digest_matches(
        permit.model_copy(update={"relative_path": "sandbox/other.txt"}),
        digest,
    )
    assert not side_effect_permit_digest_matches(
        permit.model_copy(update={"expires_at": permit.expires_at + timedelta(seconds=30)}),
        digest,
    )

    with pytest.raises(ValidationError):
        SideEffectPermit.model_validate({**values, "unexpected": True})
    with pytest.raises(ValidationError):
        SideEffectPermit.model_validate(
            {
                **values,
                "consumed_at": values["expires_at"],
            }
        )


def test_delivery_authority_is_local_only_derived_and_tamper_evident() -> None:
    workspace_id = uuid.uuid4()
    authorization_id = uuid.uuid4()
    issued_at = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)
    values: dict[str, object] = {
        "id": authorization_id,
        "review_package_id": uuid.uuid4(),
        "review_decision_id": uuid.uuid4(),
        "readiness_verdict_id": uuid.uuid4(),
        "freshness_generation": 1,
        "package_digest": "1" * 64,
        "decision_digest": "2" * 64,
        "readiness_digest": "3" * 64,
        "workspace_id": workspace_id,
        "checkpoint_id": uuid.uuid4(),
        "checkpoint_fingerprint": "4" * 64,
        "checkpoint_diff_hash": "5" * 64,
        "repository_handle_id": uuid.uuid4(),
        "source_revision": "6" * 40,
        "branch_ref": f"refs/heads/visual-engineer/{workspace_id.hex}",
        "commit_message": (f"VisualEngineer: governed local delivery {authorization_id.hex[:8]}"),
        "commit_timestamp": issued_at,
        "expires_at": issued_at + timedelta(minutes=5),
        "policy_hash": "0" * 64,
    }
    draft = DeliveryAuthorizationPolicy.model_validate(values)
    values["policy_hash"] = compute_delivery_authorization_policy_hash(draft)
    policy = DeliveryAuthorizationPolicy.model_validate(values)

    assert compute_delivery_authorization_policy_hash(policy) == policy.policy_hash
    for field in (
        "remote_access",
        "push_access",
        "pull_request_access",
        "tag_access",
        "deployment_access",
        "source_repository_write_access",
    ):
        assert getattr(policy, field) is False
    assert policy.local_git_commit_access is True
    assert (
        compute_delivery_authorization_policy_hash(
            policy.model_copy(update={"checkpoint_diff_hash": "7" * 64})
        )
        != policy.policy_hash
    )

    with pytest.raises(ValidationError):
        DeliveryAuthorizationPolicy.model_validate({**values, "remote_access": True})
    with pytest.raises(ValidationError):
        DeliveryAuthorizationPolicy.model_validate(
            {**values, "branch_ref": "refs/heads/user-controlled"}
        )
    with pytest.raises(ValidationError):
        DeliveryAuthorizationPolicy.model_validate(
            {**values, "commit_message": "git push origin main"}
        )

    permit_values = {
        "id": uuid.uuid4(),
        "sequence": 1,
        "runner_id": uuid.uuid4(),
        "job_id": uuid.uuid4(),
        "attempt_id": uuid.uuid4(),
        "lease_id": uuid.uuid4(),
        "grant_id": uuid.uuid4(),
        "workspace_id": workspace_id,
        "repository_handle_id": policy.repository_handle_id,
        "operation": WorkspaceOperation.GIT_COMMIT,
        "expected_current": policy.checkpoint_fingerprint,
        "proposed_digest": "8" * 64,
        "job_digest": "9" * 64,
        "operation_digest": "a" * 64,
        "policy_hash": "b" * 64,
        "source_revision": policy.source_revision,
        "issued_at": issued_at,
        "consumed_at": issued_at,
        "expires_at": issued_at + timedelta(seconds=5),
        "state": "consumed",
    }
    with pytest.raises(ValidationError):
        SideEffectPermit.model_validate(permit_values)
    permit_values["delivery_authorization_id"] = authorization_id
    assert (
        SideEffectPermit.model_validate(permit_values).delivery_authorization_id == authorization_id
    )
