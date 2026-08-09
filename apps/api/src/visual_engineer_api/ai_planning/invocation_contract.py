import hashlib
from enum import StrEnum
from typing import Any

from visual_engineer_api.ai_planning.contracts import canonical_digest

INVOCATION_CONTRACT_VERSION = 1
REAL_PROVIDER_ADAPTER_VERSION = "httpx-json-plan-v1"
UPSTREAM_REQUEST_FINGERPRINT_HEX_LENGTH = 24


class InvocationClassification(StrEnum):
    FIXTURE = "fixture"
    MOCK = "mock"
    LIVE = "live"


class InvocationStatus(StrEnum):
    PREPARED = "prepared"
    DISPATCHING = "dispatching"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED_BEFORE_DISPATCH = "cancelled_before_dispatch"
    OUTCOME_UNKNOWN = "outcome_unknown"
    LEGACY_TIMEOUT = "timeout"
    LEGACY_CANCELLED = "cancelled"


class ReportedValueStatus(StrEnum):
    REPORTED = "reported"
    UNAVAILABLE = "unavailable"


class InvocationUsageStatus(StrEnum):
    SYNTHETIC_COMPLETE = "synthetic_complete"
    REPORTED_COMPLETE = "reported_complete"
    REPORTED_PARTIAL = "reported_partial"
    REPORTED_INVALID = "reported_invalid"
    UNAVAILABLE = "unavailable"


class InvocationBillingStatus(StrEnum):
    NOT_BILLABLE_FIXTURE = "not_billable_fixture"
    MOCK_NOT_BILLABLE = "mock_not_billable"
    LIVE_BILLING_UNKNOWN = "live_billing_unknown"
    LIVE_COST_REPORTED = "live_cost_reported"
    NOT_DISPATCHED = "not_dispatched"


class RequestDigestKind(StrEnum):
    LEGACY_GENERATION_REQUEST = "legacy_generation_request"
    OUTBOUND_DISPATCH = "outbound_dispatch"


class ResponseDigestKind(StrEnum):
    LEGACY_PROVIDER_RESPONSE = "legacy_provider_response"
    NORMALIZED_SAFE_RESPONSE = "normalized_safe_response"


class DispatchBoundaryStatus(StrEnum):
    LEGACY_UNAVAILABLE = "legacy_unavailable"
    NOT_DISPATCHED = "not_dispatched"
    DISPATCHED = "dispatched"


def upstream_request_fingerprint(value: str | None) -> str | None:
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[
        :UPSTREAM_REQUEST_FINGERPRINT_HEX_LENGTH
    ]


def normalized_response_digest(
    *,
    plan_payload: dict[str, Any],
    effective_model_status: ReportedValueStatus,
    effective_model_id: str | None,
    upstream_request_id_status: ReportedValueStatus,
    upstream_request_id: str | None,
    usage_status: InvocationUsageStatus,
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
) -> str:
    return canonical_digest(
        {
            "plan": plan_payload,
            "effective_model": {
                "status": effective_model_status.value,
                "value": effective_model_id,
            },
            "upstream_request_id": {
                "status": upstream_request_id_status.value,
                "value": upstream_request_id,
            },
            "usage": {
                "status": usage_status.value,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            },
        }
    )
