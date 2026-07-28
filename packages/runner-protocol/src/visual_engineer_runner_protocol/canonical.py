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
