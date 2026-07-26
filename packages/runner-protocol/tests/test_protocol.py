import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from visual_engineer_runner_protocol import (
    Capability,
    ControlledWaitJobSpec,
    DiagnosticResult,
    PermissionEnvelope,
    compute_permission_policy_hash,
    permission_policy_hash_matches,
    validate_result_payload,
    validate_safe_error_message,
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
