from __future__ import annotations

import uuid
from typing import Any, cast

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from test_phase5_validation_suites import _prepare_suite
from visual_engineer_api.models.validation import (
    ValidationRun,
    ValidationSuiteRun,
)


def test_p5_suites_aud_001_same_grant_cannot_create_a_second_suite_attempt(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """A Suite Grant is single-attempt authority; retry requires a fresh Grant."""

    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    grant_id = uuid.UUID(context.grant_id)
    suite_count_before = int(
        db_session.scalar(
            select(func.count(ValidationSuiteRun.id)).where(
                ValidationSuiteRun.execution_grant_id == grant_id
            )
        )
        or 0
    )
    child_count_before = int(
        db_session.scalar(
            select(func.count(ValidationRun.id)).where(ValidationRun.execution_grant_id == grant_id)
        )
        or 0
    )

    duplicate = client.post(
        "/api/v1/validation-suite-runs",
        headers={"Idempotency-Key": f"audit-second-suite-{uuid.uuid4()}"},
        json={
            "execution_grant_id": context.grant_id,
            "suite_id": "fixture-integrity-suite-v1",
            "suite_version": 1,
        },
    )

    suite_count_after = int(
        db_session.scalar(
            select(func.count(ValidationSuiteRun.id)).where(
                ValidationSuiteRun.execution_grant_id == grant_id
            )
        )
        or 0
    )
    child_count_after = int(
        db_session.scalar(
            select(func.count(ValidationRun.id)).where(ValidationRun.execution_grant_id == grant_id)
        )
        or 0
    )
    observed = (
        duplicate.status_code,
        suite_count_before,
        suite_count_after,
        child_count_before,
        child_count_after,
    )
    assert duplicate.status_code in {409, 422} and (
        suite_count_after,
        child_count_after,
    ) == (
        suite_count_before,
        child_count_before,
    ), f"same Grant created another Suite attempt: {observed}"


def test_p5_suites_aud_002_missing_evidence_cannot_be_promoted_to_suite_success(
    client: TestClient,
    db_session: Session,
    runner_bootstrap_token: str,
) -> None:
    """Persisted step summaries cannot substitute for ordered current-run Evidence."""

    context = _prepare_suite(client, db_session, runner_bootstrap_token)
    try:
        db_session.execute(
            text(
                "UPDATE validation_suite_step_runs "
                "SET state = 'succeeded', completed_at = now(), duration_ms = 0, "
                "exit_code = 0, cleanup_succeeded = true "
                "WHERE suite_run_id = :suite_run_id"
            ),
            {"suite_run_id": context.suite_run["id"]},
        )
        db_session.commit()
    except DBAPIError:
        db_session.rollback()
        return

    synchronized = client.get(f"/api/v1/validation-suite-runs/{context.suite_run['id']}")
    payload = cast(dict[str, Any], synchronized.json()) if synchronized.status_code == 200 else {}
    result = payload.get("result")
    result_payload = cast(dict[str, Any], result) if isinstance(result, dict) else {}
    evidence = result_payload.get("evidence_references")
    observed = (
        synchronized.status_code,
        payload.get("state"),
        result_payload.get("verdict"),
        len(evidence) if isinstance(evidence, list) else None,
    )
    assert observed != (
        200,
        "succeeded",
        "succeeded",
        0,
    ), f"missing Evidence was accepted as successful aggregate proof: {observed}"
