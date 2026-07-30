import hashlib
import hmac
import json
from typing import Any

from pydantic import BaseModel
from pydantic_core import to_jsonable_python


def canonical_json_bytes(value: BaseModel | dict[str, Any]) -> bytes:
    payload = (
        value.model_dump(mode="json") if isinstance(value, BaseModel) else to_jsonable_python(value)
    )
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def compute_permission_policy_hash(value: BaseModel | dict[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("policy_hash", None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def permission_policy_hash_matches(value: BaseModel | dict[str, Any], expected: str) -> bool:
    return hmac.compare_digest(compute_permission_policy_hash(value), expected)


def compute_execution_grant_policy_hash(value: BaseModel | dict[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("policy_hash", None)
    if not payload.get("allowed_validation_suites"):
        for field in (
            "allowed_validation_suites",
            "validation_suite_definition_digest",
            "validation_suite_root_run_id",
            "validation_suite_retry_of_run_id",
            "validation_suite_attempt_number",
            "validation_suite_allowed_run_count",
        ):
            payload.pop(field, None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def execution_grant_policy_hash_matches(value: BaseModel | dict[str, Any], expected: str) -> bool:
    return hmac.compare_digest(compute_execution_grant_policy_hash(value), expected)


def compute_side_effect_job_digest(value: BaseModel | dict[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def compute_side_effect_permit_digest(value: BaseModel | dict[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    for field in ("operation_digest", "idempotent_replay"):
        payload.pop(field, None)
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def side_effect_permit_digest_matches(value: BaseModel | dict[str, Any], expected: str) -> bool:
    return hmac.compare_digest(compute_side_effect_permit_digest(value), expected)


def _validation_digest(domain: str, value: BaseModel | dict[str, Any] | list[Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return hashlib.sha256(
        domain.encode("ascii") + b"\x00" + canonical_json_bytes({"value": payload})
    ).hexdigest()


def compute_validation_policy_digest(value: dict[str, Any]) -> str:
    return _validation_digest("visual-engineer.validation-policy.v1", value)


def compute_validation_fixed_argv_digest(value: list[str] | tuple[str, ...]) -> str:
    return _validation_digest("visual-engineer.validation-argv.v1", list(value))


def compute_validation_environment_digest(
    value: dict[str, str] | tuple[tuple[str, str], ...],
) -> str:
    environment = dict(value)
    return _validation_digest(
        "visual-engineer.validation-environment.v1",
        {"allowlist": sorted(environment), "values": environment},
    )


def compute_validation_artifact_manifest_digest(value: list[dict[str, Any]]) -> str:
    return _validation_digest("visual-engineer.validation-artifacts.v1", value)


def compute_validation_fencing_token(value: dict[str, Any]) -> str:
    return _validation_digest("visual-engineer.validation-fencing.v1", value)


def compute_validation_execution_envelope_digest(value: dict[str, Any]) -> str:
    return _validation_digest("visual-engineer.validation-execution-envelope.v1", value)


def compute_validation_evidence_digest(value: BaseModel | dict[str, Any]) -> str:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else dict(value)
    payload.pop("evidence_digest", None)
    return _validation_digest("visual-engineer.validation-evidence.v1", payload)
