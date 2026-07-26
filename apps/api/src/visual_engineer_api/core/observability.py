import json
import logging
import uuid
from typing import Any

from visual_engineer_api.models.run import Run

logger = logging.getLogger("visual_engineer_api.governance")


def log_governance_event(
    event_type: str,
    run: Run,
    *,
    request_id: str,
    duration_ms: float | None = None,
    snapshot_id: uuid.UUID | None = None,
    plan_version: int | None = None,
    policy_denial_reason_code: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "governance_event",
        "event_type": event_type,
        "request_id": request_id,
        "trace_id": str(run.trace_id),
        "run_id": str(run.id),
    }
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 2)
    if snapshot_id is not None:
        payload["snapshot_id"] = str(snapshot_id)
    if plan_version is not None:
        payload["plan_version"] = plan_version
    if policy_denial_reason_code is not None:
        payload["policy_denial_reason_code"] = policy_denial_reason_code
    logger.info(json.dumps(payload, separators=(",", ":"), sort_keys=True))
