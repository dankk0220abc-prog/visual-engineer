import json
import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from conftest import alembic_config


def _insert_request(connection: object) -> tuple[uuid.UUID, uuid.UUID]:
    execute = connection.execute  # type: ignore[attr-defined]
    task_id = uuid.uuid4()
    run_id = uuid.uuid4()
    request_id = uuid.uuid4()
    execute(
        text(
            """
            INSERT INTO tasks (
                id, title, objective, repository_kind, repository_display_name,
                repository_locator, status, version, idempotency_key,
                idempotency_request_hash
            ) VALUES (
                :id, 'Migration fixture', 'Migration fixture objective', 'local_path',
                'Fixture', '/fixture', 'draft', 1, :key, :digest
            )
            """
        ),
        {"id": task_id, "key": f"task-{task_id}", "digest": "1" * 64},
    )
    execute(
        text(
            """
            INSERT INTO runs (
                id, task_id, status, permission_level, snapshot_mode, version, trace_id
            ) VALUES (
                :id, :task_id, 'created', 'read_only', 'git_head', 1, :trace_id
            )
            """
        ),
        {"id": run_id, "task_id": task_id, "trace_id": uuid.uuid4()},
    )
    provider_metadata = json.dumps(
        {
            "provider_id": "deterministic-fixture",
            "implementation_version": "fixture-provider-v1",
            "model_label": "fixture-planner-v1",
        }
    )
    execute(
        text(
            """
            INSERT INTO ai_plan_requests (
                id, run_id, status, delivery_package, source_revision,
                snapshot_fingerprint, prompt_template_id, prompt_version, prompt_digest,
                prompt_payload, provider_id, provider_metadata, request_payload,
                request_digest, response_payload, deterministic_digest, context_manifest,
                context_digest, context_bytes, context_reference_count,
                context_excluded_count, redaction_record, retry_count, error_category,
                error_code, error_message, idempotency_key, idempotency_request_hash,
                handoff_plan_id
            ) VALUES (
                :id, :run_id, 'requested', 'frontend_quality_remediation', :revision,
                :snapshot, 'governed-plan-v1', 'prompt-v1', :prompt_digest,
                CAST('{}' AS jsonb), 'deterministic-fixture',
                CAST(:provider_metadata AS jsonb), CAST('{}' AS jsonb), :request_digest,
                NULL, NULL, CAST('[{}]' AS jsonb), :context_digest, 2, 1, 0,
                CAST('[]' AS jsonb), 0, NULL, NULL, NULL, :key, :idempotency_digest, NULL
            )
            """
        ),
        {
            "id": request_id,
            "run_id": run_id,
            "revision": "a" * 40,
            "snapshot": "b" * 64,
            "prompt_digest": "c" * 64,
            "provider_metadata": provider_metadata,
            "request_digest": "d" * 64,
            "context_digest": "e" * 64,
            "key": f"request-{request_id}",
            "idempotency_digest": "f" * 64,
        },
    )
    return request_id, run_id


def _truncate_invocation_fixture(connection: object) -> None:
    connection.execute(  # type: ignore[attr-defined]
        text("TRUNCATE TABLE ai_provider_invocations, ai_plan_requests, runs, tasks CASCADE")
    )


def test_provider_invocation_fixture_history_backfill_and_round_trip(
    database_url: str,
) -> None:
    config = alembic_config()
    engine = create_engine(database_url)
    if "ai_provider_invocations" in inspect(engine).get_table_names():
        with engine.begin() as connection:
            _truncate_invocation_fixture(connection)
    command.downgrade(config, "base")
    command.upgrade(config, "20260801_0015")
    invocation_id = uuid.uuid4()
    with engine.begin() as connection:
        request_id, _ = _insert_request(connection)
        connection.execute(
            text(
                """
                INSERT INTO ai_provider_traces (
                    id, ai_plan_request_id, attempt_number, status, provider_id,
                    provider_metadata, request_digest, response_digest, latency_ms,
                    input_tokens, output_tokens, total_tokens,
                    cost_estimate_microunits, cost_basis, error_category, error_code,
                    retryable, redactions
                ) VALUES (
                    :id, :request_id, 1, 'succeeded', 'deterministic-fixture',
                    CAST(:metadata AS jsonb), :request_digest, :response_digest, 7.4,
                    11, 7, 18, 0, 'synthetic_not_billable', NULL, NULL, false,
                    CAST('[]' AS jsonb)
                )
                """
            ),
            {
                "id": invocation_id,
                "request_id": request_id,
                "metadata": json.dumps(
                    {
                        "implementation_version": "fixture-provider-v1",
                        "model_label": "fixture-planner-v1",
                    }
                ),
                "request_digest": "2" * 64,
                "response_digest": "3" * 64,
            },
        )

    command.upgrade(config, "head")
    assert "ai_provider_traces" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        row = (
            connection.execute(
                text(
                    """
                SELECT id, classification, status, contract_version, adapter_version,
                    requested_model_id, effective_model_status,
                    upstream_request_id_status, usage_status, input_tokens, output_tokens,
                    total_tokens, queue_wait_ms, provider_elapsed_ms,
                    client_total_elapsed_ms, billing_status, cost_amount, cost_currency
                FROM ai_provider_invocations WHERE id = :id
                """
                ),
                {"id": invocation_id},
            )
            .mappings()
            .one()
        )
    assert row == {
        "id": invocation_id,
        "classification": "fixture",
        "status": "succeeded",
        "contract_version": 1,
        "adapter_version": "fixture-provider-v1",
        "requested_model_id": "fixture-planner-v1",
        "effective_model_status": "unavailable",
        "upstream_request_id_status": "unavailable",
        "usage_status": "synthetic_complete",
        "input_tokens": 11,
        "output_tokens": 7,
        "total_tokens": 18,
        "queue_wait_ms": 0,
        "provider_elapsed_ms": 7,
        "client_total_elapsed_ms": 7,
        "billing_status": "not_billable_fixture",
        "cost_amount": None,
        "cost_currency": None,
    }

    command.downgrade(config, "20260801_0015")
    assert "ai_provider_invocations" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        legacy = connection.execute(
            text("SELECT status, total_tokens, latency_ms FROM ai_provider_traces WHERE id = :id"),
            {"id": invocation_id},
        ).one()
    assert legacy.status == "succeeded"
    assert legacy.total_tokens == 18
    assert legacy.latency_ms == 7.0
    command.upgrade(config, "head")
    engine.dispose()


@pytest.mark.parametrize("blocker", ["live", "mock", "outcome_unknown"])
def test_provider_invocation_downgrade_rejects_lossy_audit_semantics(
    database_url: str,
    blocker: str,
) -> None:
    config = alembic_config()
    engine = create_engine(database_url)
    command.upgrade(config, "head")
    with engine.begin() as connection:
        _truncate_invocation_fixture(connection)
        request_id, _ = _insert_request(connection)
        classification = blocker if blocker in {"live", "mock"} else "fixture"
        billing = {
            "live": "live_billing_unknown",
            "mock": "mock_not_billable",
            "outcome_unknown": "not_billable_fixture",
        }[blocker]
        provider_id = "zhipu" if blocker in {"live", "mock"} else "deterministic-fixture"
        invocation_id = uuid.uuid4()
        connection.execute(
            text(
                """
                INSERT INTO ai_provider_invocations (
                    id, ai_plan_request_id, attempt_number, contract_version,
                    classification, status, provider_id, provider_metadata,
                    adapter_version, requested_model_id, effective_model_status,
                    effective_model_id, upstream_request_id_status, upstream_request_id,
                    request_digest, response_digest, usage_status, input_tokens,
                    output_tokens, total_tokens, queue_wait_ms, provider_elapsed_ms,
                    client_total_elapsed_ms, billing_status, cost_amount, cost_currency,
                    error_category, error_code, redactions, dispatch_started_at, completed_at
                ) VALUES (
                    :id, :request_id, 1, 1, :classification, 'prepared', :provider_id,
                    CAST('{}' AS jsonb), 'adapter-v1', 'model-v1', 'unavailable', NULL,
                    'unavailable', NULL, :request_digest, NULL, 'unavailable', NULL,
                    NULL, NULL, NULL, NULL, NULL, :billing, NULL, NULL, NULL, NULL,
                    CAST('[]' AS jsonb), NULL, NULL
                )
                """
            ),
            {
                "id": invocation_id,
                "request_id": request_id,
                "classification": classification,
                "provider_id": provider_id,
                "request_digest": "4" * 64,
                "billing": billing,
            },
        )
        if blocker == "outcome_unknown":
            connection.execute(
                text(
                    """
                    UPDATE ai_provider_invocations
                    SET status = 'dispatching', dispatch_started_at = now(), queue_wait_ms = 0
                    WHERE id = :id
                    """
                ),
                {"id": invocation_id},
            )
            connection.execute(
                text(
                    """
                    UPDATE ai_provider_invocations
                    SET status = 'outcome_unknown', completed_at = now(),
                        error_category = 'transport_error',
                        error_code = 'provider_dispatch_stale_recovered'
                    WHERE id = :id
                    """
                ),
                {"id": invocation_id},
            )

    with pytest.raises(
        DBAPIError,
        match="downgrade would lose provider invocation audit semantics",
    ):
        command.downgrade(config, "20260801_0015")
    with engine.begin() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "20260809_0016"
        )
        _truncate_invocation_fixture(connection)
    engine.dispose()
