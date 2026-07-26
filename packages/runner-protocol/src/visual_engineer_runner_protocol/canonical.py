import hashlib
import hmac
import json
from typing import Any

from pydantic import BaseModel


def canonical_json_bytes(value: BaseModel | dict[str, Any]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
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
