import asyncio
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from visual_engineer_api.ai_planning.contracts import (
    AIPlanGenerationRequest,
    ContextBudget,
    ContextManifestEntry,
    DeliveryPackage,
    PromptBinding,
    RepositoryBinding,
    RepositoryFacts,
    canonical_digest,
)
from visual_engineer_api.ai_planning.fake_provider import DeterministicFixtureProvider
from visual_engineer_api.ai_planning.invocation_contract import (
    InvocationBillingStatus,
    InvocationClassification,
    InvocationStatus,
    InvocationUsageStatus,
    ReportedValueStatus,
    upstream_request_fingerprint,
)
from visual_engineer_api.ai_planning.provider import (
    CancellationToken,
    ProviderError,
    ProviderErrorCategory,
)
from visual_engineer_api.ai_planning.real_provider_adapters import (
    PROVIDER_MAXIMUM_TOTAL_DEADLINE_SECONDS,
    ProviderCallPolicy,
    ZhipuAdapter,
)
from visual_engineer_api.core.config import Settings
from visual_engineer_api.models.ai_planning import AIPlanRequest, AIProviderInvocation
from visual_engineer_api.models.run import Run
from visual_engineer_api.models.task import Task
from visual_engineer_api.services.ai_planning import AIPlanningService
from visual_engineer_api.services.provider_invocations import (
    ProviderInvocationLifecycle,
    invoke_mocked_adapter_contract,
    minimum_stale_dispatch_age,
    reported_usage_status,
)


class _ManualClock:
    def __init__(self) -> None:
        self.current = 100.0

    def monotonic(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


def _generation_request(*, requirement: str = "Produce a governed fixture Plan.") -> Any:
    revision = "a" * 40
    snapshot = "b" * 64
    return AIPlanGenerationRequest(
        delivery_package=DeliveryPackage.FRONTEND_QUALITY_REMEDIATION,
        requirement=requirement,
        requirement_was_redacted=False,
        malicious_instruction_signals=[],
        repository=RepositoryBinding(
            source_revision=revision,
            snapshot_fingerprint=snapshot,
            scanner_version="scanner-v1",
            scan_policy_version="policy-v1",
        ),
        repository_facts=RepositoryFacts(
            repository_is_dirty=False,
            tracked_file_count=1,
            selected_file_count=1,
            skipped_file_count=0,
            languages=["TypeScript"],
            frameworks=["Next.js"],
            package_manager="pnpm",
        ),
        context_manifest=[
            ContextManifestEntry(
                reference_id="ctx-0001",
                kind="repository_revision",
                summary="Bound committed revision",
                provenance="committed_head_structured_extraction",
                source_revision=revision,
            )
        ],
        context_budget=ContextBudget(max_context_bytes=16_384, max_references=64),
        prompt=PromptBinding(
            template_id="governed-plan-v1",
            version="prompt-v1",
            digest="c" * 64,
            context_manifest_digest="d" * 64,
            source_revision=revision,
            snapshot_fingerprint=snapshot,
        ),
    )


def _create_request(session: Session, request: AIPlanGenerationRequest) -> AIPlanRequest:
    task = Task(
        title="Provider invocation fixture",
        objective="Verify Provider invocation audit without live transport.",
        repository_kind="local_path",
        repository_display_name="Fixture",
        repository_locator="/fixture",
        status="draft",
        version=1,
        idempotency_key=f"task-{uuid.uuid4()}",
        idempotency_request_hash="1" * 64,
    )
    session.add(task)
    session.flush()
    run = Run(
        task_id=task.id,
        status="created",
        permission_level="read_only",
        snapshot_mode="git_head",
        version=1,
        trace_id=uuid.uuid4(),
    )
    session.add(run)
    session.flush()
    request_values = request.model_dump(mode="json")
    ai_request = AIPlanRequest(
        run_id=run.id,
        status="requested",
        delivery_package=request.delivery_package.value,
        source_revision=request.repository.source_revision,
        snapshot_fingerprint=request.repository.snapshot_fingerprint,
        prompt_template_id=request.prompt.template_id,
        prompt_version=request.prompt.version,
        prompt_digest=request.prompt.digest,
        prompt_payload=request.prompt.model_dump(mode="json"),
        provider_id="zhipu",
        provider_metadata=DeterministicFixtureProvider().capabilities.model_dump(mode="json"),
        request_payload=request_values,
        request_digest=canonical_digest(request_values),
        response_payload=None,
        deterministic_digest=None,
        context_manifest=[item.model_dump(mode="json") for item in request.context_manifest],
        context_digest=canonical_digest(
            [item.model_dump(mode="json") for item in request.context_manifest]
        ),
        context_bytes=1,
        context_reference_count=1,
        context_excluded_count=0,
        redaction_record=[],
        retry_count=0,
        error_category=None,
        error_code=None,
        error_message=None,
        idempotency_key=f"request-{uuid.uuid4()}",
        idempotency_request_hash="2" * 64,
        handoff_plan_id=None,
    )
    session.add(ai_request)
    session.commit()
    return ai_request


def _prepare_lifecycle(
    session: Session,
    *,
    classification: InvocationClassification = InvocationClassification.FIXTURE,
    clock: _ManualClock | None = None,
) -> tuple[ProviderInvocationLifecycle, Any, AIPlanRequest]:
    request = _generation_request()
    ai_request = _create_request(session, request)
    lifecycle = ProviderInvocationLifecycle(session, clock=clock)
    timing = lifecycle.prepare(
        ai_plan_request_id=ai_request.id,
        attempt_number=1,
        classification=classification,
        provider_id=(
            "deterministic-fixture"
            if classification == InvocationClassification.FIXTURE
            else "zhipu"
        ),
        provider_metadata={"mock_contract": classification.value},
        adapter_version="adapter-v1",
        requested_model_id="model-v1",
        request_digest="3" * 64,
        redactions=[],
    )
    return lifecycle, timing, ai_request


def _stored_invocation(session: Session) -> AIProviderInvocation:
    return session.scalar(select(AIProviderInvocation))  # type: ignore[return-value]


def _direct_prepared_invocation(
    session: Session,
    *,
    created_at: datetime,
) -> AIProviderInvocation:
    ai_request = _create_request(session, _generation_request())
    invocation = AIProviderInvocation(
        ai_plan_request_id=ai_request.id,
        attempt_number=1,
        contract_version=1,
        classification="mock",
        status="prepared",
        provider_id="zhipu",
        provider_metadata={"mock_contract": True},
        adapter_version="adapter-v1",
        requested_model_id="model-v1",
        effective_model_status="unavailable",
        effective_model_id=None,
        upstream_request_id_status="unavailable",
        upstream_request_id=None,
        request_digest="3" * 64,
        response_digest=None,
        usage_status="unavailable",
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        queue_wait_ms=None,
        provider_elapsed_ms=None,
        client_total_elapsed_ms=None,
        billing_status="mock_not_billable",
        cost_amount=None,
        cost_currency=None,
        error_category=None,
        error_code=None,
        redactions=[],
        created_at=created_at,
        dispatch_started_at=None,
        completed_at=None,
    )
    session.add(invocation)
    session.commit()
    return invocation


_TEMPORAL_BILLING_CONSTRAINT = "ck_ai_provider_invocations_v1_temporal_billing"


def _insert_live_prepared_direct_sql(
    session: Session,
    *,
    billing_status: str = "live_billing_unknown",
    cost_amount: Decimal | None = None,
    cost_currency: str | None = None,
) -> uuid.UUID:
    ai_request = _create_request(session, _generation_request())
    invocation_id = uuid.uuid4()
    session.execute(
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
                :id, :request_id, 1, 1, 'live', 'prepared', 'zhipu',
                CAST('{"direct_sql_temporal_billing": true}' AS jsonb),
                'adapter-v1', 'model-v1', 'unavailable', NULL, 'unavailable', NULL,
                :request_digest, NULL, 'unavailable', NULL, NULL, NULL, NULL, NULL,
                NULL, :billing_status, :cost_amount, :cost_currency, NULL, NULL,
                CAST('[]' AS jsonb), NULL, NULL
            )
            """
        ),
        {
            "id": invocation_id,
            "request_id": ai_request.id,
            "request_digest": "7" * 64,
            "billing_status": billing_status,
            "cost_amount": cost_amount,
            "cost_currency": cost_currency,
        },
    )
    session.commit()
    return invocation_id


def _mark_dispatching_direct_sql(session: Session, invocation_id: uuid.UUID) -> None:
    session.execute(
        text(
            "UPDATE ai_provider_invocations SET status = 'dispatching', "
            "dispatch_started_at = now(), queue_wait_ms = 1 WHERE id = :id"
        ),
        {"id": invocation_id},
    )
    session.commit()


def _assert_temporal_billing_constraint(error: DBAPIError) -> None:
    diagnostic = getattr(error.orig, "diag", None)
    assert getattr(diagnostic, "constraint_name", None) == _TEMPORAL_BILLING_CONSTRAINT


def test_invocation_lifecycle_uses_integer_monotonic_latency_and_is_terminally_immutable(
    db_session: Session,
) -> None:
    clock = _ManualClock()
    lifecycle, timing, _ = _prepare_lifecycle(db_session, clock=clock)
    prepared = _stored_invocation(db_session)
    assert prepared.status == "prepared"
    assert prepared.dispatch_started_at is None

    clock.advance(0.025)
    lifecycle.mark_dispatching(timing)
    dispatching = _stored_invocation(db_session)
    assert dispatching.status == "dispatching"
    assert dispatching.queue_wait_ms == 25

    clock.advance(0.125)
    lifecycle.succeed(
        timing,
        response_digest="4" * 64,
        effective_model_status=ReportedValueStatus.REPORTED,
        effective_model_id="model-v1",
        upstream_request_id_status=ReportedValueStatus.UNAVAILABLE,
        upstream_request_id=None,
        usage_status=InvocationUsageStatus.SYNTHETIC_COMPLETE,
        input_tokens=11,
        output_tokens=7,
        total_tokens=18,
    )
    succeeded = _stored_invocation(db_session)
    assert succeeded.status == "succeeded"
    assert succeeded.provider_elapsed_ms == 125
    assert succeeded.client_total_elapsed_ms == 150
    assert isinstance(succeeded.provider_elapsed_ms, int)

    for statement in (
        "UPDATE ai_provider_invocations SET adapter_version = 'changed' WHERE id = :id",
        "UPDATE ai_provider_invocations SET status = 'failed', response_digest = NULL, "
        "error_category = 'internal', error_code = 'changed' WHERE id = :id",
        "DELETE FROM ai_provider_invocations WHERE id = :id",
    ):
        with pytest.raises(DBAPIError):
            db_session.execute(text(statement), {"id": succeeded.id})
            db_session.commit()
        db_session.rollback()


def test_database_rejects_illegal_transition_and_prepared_identity_mutation(
    db_session: Session,
) -> None:
    _, _, _ = _prepare_lifecycle(db_session)
    invocation_id = _stored_invocation(db_session).id
    statements = (
        'UPDATE ai_provider_invocations SET redactions = \'[{"rule": "changed"}]\'::jsonb '
        "WHERE id = :id",
        "UPDATE ai_provider_invocations SET status = 'succeeded', "
        "dispatch_started_at = now(), completed_at = now(), queue_wait_ms = 0, "
        "provider_elapsed_ms = 0, client_total_elapsed_ms = 0, response_digest = :digest, "
        "effective_model_status = 'reported', effective_model_id = requested_model_id, "
        "usage_status = 'synthetic_complete', input_tokens = 0, output_tokens = 0, "
        "total_tokens = 0 WHERE id = :id",
        "UPDATE ai_provider_invocations SET status = 'failed', "
        "dispatch_started_at = now(), completed_at = now(), queue_wait_ms = 0, "
        "provider_elapsed_ms = 0, client_total_elapsed_ms = 0, "
        "error_category = 'internal', error_code = 'forged_dispatch' WHERE id = :id",
    )
    for statement in statements:
        with pytest.raises(DBAPIError):
            db_session.execute(text(statement), {"id": invocation_id, "digest": "4" * 64})
            db_session.commit()
        db_session.rollback()


@pytest.mark.parametrize(
    "injected_fact",
    [
        "adapter_version = 'changed-in-terminal-update'",
        "response_digest = repeat('a', 64)",
        "effective_model_status = 'reported', effective_model_id = 'forged-model'",
        "upstream_request_id_status = 'reported', upstream_request_id = 'forged-request'",
        "usage_status = 'reported_complete', input_tokens = 1, output_tokens = 2, total_tokens = 3",
    ],
)
def test_database_rejects_pre_dispatch_terminal_fact_injection_in_same_update(
    db_session: Session,
    injected_fact: str,
) -> None:
    _, _, _ = _prepare_lifecycle(
        db_session,
        classification=InvocationClassification.LIVE,
    )
    invocation_id = _stored_invocation(db_session).id
    with pytest.raises(DBAPIError):
        db_session.execute(
            text(
                "UPDATE ai_provider_invocations SET status = 'cancelled_before_dispatch', "
                "completed_at = now(), client_total_elapsed_ms = 0, "
                "billing_status = 'not_dispatched', error_category = 'cancelled', "
                f"error_code = 'provider_cancelled', {injected_fact} WHERE id = :id"
            ),
            {"id": invocation_id},
        )
        db_session.commit()
    db_session.rollback()


def test_database_rejects_prepared_live_reported_cost_insert(
    db_session: Session,
) -> None:
    with pytest.raises(DBAPIError) as error:
        _insert_live_prepared_direct_sql(
            db_session,
            billing_status="live_cost_reported",
            cost_amount=Decimal("0.12500000"),
            cost_currency="USD",
        )
    db_session.rollback()
    _assert_temporal_billing_constraint(error.value)


def test_database_rejects_prepared_to_dispatching_reported_cost_in_same_update(
    db_session: Session,
) -> None:
    invocation_id = _insert_live_prepared_direct_sql(db_session)
    with pytest.raises(DBAPIError) as error:
        db_session.execute(
            text(
                "UPDATE ai_provider_invocations SET status = 'dispatching', "
                "dispatch_started_at = now(), queue_wait_ms = 1, "
                "billing_status = 'live_cost_reported', cost_amount = :cost_amount, "
                "cost_currency = 'USD' WHERE id = :id"
            ),
            {"id": invocation_id, "cost_amount": Decimal("0.12500000")},
        )
        db_session.commit()
    db_session.rollback()
    _assert_temporal_billing_constraint(error.value)


@pytest.mark.parametrize(
    ("status", "error_category", "error_code"),
    [
        ("failed", "internal", "pre_dispatch_failed"),
        ("cancelled_before_dispatch", "cancelled", "provider_cancelled"),
    ],
)
def test_database_rejects_pre_dispatch_terminal_reported_cost_without_duplicate_assignment(
    db_session: Session,
    status: str,
    error_category: str,
    error_code: str,
) -> None:
    invocation_id = _insert_live_prepared_direct_sql(db_session)
    with pytest.raises(DBAPIError) as error:
        db_session.execute(
            text(
                "UPDATE ai_provider_invocations SET status = :status, completed_at = now(), "
                "client_total_elapsed_ms = 1, billing_status = 'live_cost_reported', "
                "cost_amount = :cost_amount, cost_currency = 'USD', "
                "error_category = :error_category, error_code = :error_code WHERE id = :id"
            ),
            {
                "id": invocation_id,
                "status": status,
                "cost_amount": Decimal("0.12500000"),
                "error_category": error_category,
                "error_code": error_code,
            },
        )
        db_session.commit()
    db_session.rollback()
    assert getattr(error.value.orig, "sqlstate", None) == "55000"
    assert "Provider invocation mutation is forbidden" in str(error.value.orig)


@pytest.mark.parametrize("status", ["failed", "outcome_unknown"])
def test_database_rejects_dispatched_non_success_terminal_reported_cost(
    db_session: Session,
    status: str,
) -> None:
    invocation_id = _insert_live_prepared_direct_sql(db_session)
    _mark_dispatching_direct_sql(db_session, invocation_id)
    with pytest.raises(DBAPIError) as error:
        db_session.execute(
            text(
                "UPDATE ai_provider_invocations SET status = :status, completed_at = now(), "
                "provider_elapsed_ms = 1, client_total_elapsed_ms = 2, "
                "billing_status = 'live_cost_reported', cost_amount = :cost_amount, "
                "cost_currency = 'USD', error_category = 'transport_error', "
                "error_code = :error_code WHERE id = :id"
            ),
            {
                "id": invocation_id,
                "status": status,
                "cost_amount": Decimal("0.12500000"),
                "error_code": f"provider_{status}",
            },
        )
        db_session.commit()
    db_session.rollback()
    _assert_temporal_billing_constraint(error.value)


@pytest.mark.parametrize(
    ("billing_status", "cost_amount", "cost_currency"),
    [
        ("live_billing_unknown", None, None),
        ("live_cost_reported", Decimal("0.12500000"), "USD"),
    ],
)
def test_database_accepts_only_terminal_succeeded_live_billing_facts(
    db_session: Session,
    billing_status: str,
    cost_amount: Decimal | None,
    cost_currency: str | None,
) -> None:
    invocation_id = _insert_live_prepared_direct_sql(db_session)
    _mark_dispatching_direct_sql(db_session, invocation_id)
    db_session.execute(
        text(
            "UPDATE ai_provider_invocations SET status = 'succeeded', completed_at = now(), "
            "provider_elapsed_ms = 1, client_total_elapsed_ms = 2, "
            "response_digest = :response_digest, billing_status = :billing_status, "
            "cost_amount = :cost_amount, cost_currency = :cost_currency WHERE id = :id"
        ),
        {
            "id": invocation_id,
            "response_digest": "8" * 64,
            "billing_status": billing_status,
            "cost_amount": cost_amount,
            "cost_currency": cost_currency,
        },
    )
    db_session.commit()
    stored = (
        db_session.execute(
            text(
                "SELECT status, billing_status, cost_amount, cost_currency "
                "FROM ai_provider_invocations WHERE id = :id"
            ),
            {"id": invocation_id},
        )
        .mappings()
        .one()
    )
    assert stored["status"] == "succeeded"
    assert stored["billing_status"] == billing_status
    assert stored["cost_amount"] == cost_amount
    assert stored["cost_currency"] == cost_currency


@pytest.mark.parametrize(
    ("billing_status", "cost_amount", "cost_currency"),
    [
        pytest.param("live_cost_reported", None, "USD", id="reported-missing-amount"),
        pytest.param(
            "live_cost_reported",
            Decimal("0.12500000"),
            None,
            id="reported-missing-currency",
        ),
        pytest.param(
            "live_billing_unknown",
            Decimal("0.12500000"),
            None,
            id="nonreported-injected-amount",
        ),
        pytest.param(
            "live_billing_unknown",
            None,
            "USD",
            id="nonreported-injected-currency",
        ),
    ],
)
def test_database_rejects_incomplete_or_nonreported_cost_values(
    db_session: Session,
    billing_status: str,
    cost_amount: Decimal | None,
    cost_currency: str | None,
) -> None:
    invocation_id = _insert_live_prepared_direct_sql(db_session)
    _mark_dispatching_direct_sql(db_session, invocation_id)
    with pytest.raises(DBAPIError) as error:
        db_session.execute(
            text(
                "UPDATE ai_provider_invocations SET status = 'succeeded', "
                "completed_at = now(), provider_elapsed_ms = 1, client_total_elapsed_ms = 2, "
                "response_digest = :response_digest, billing_status = :billing_status, "
                "cost_amount = :cost_amount, cost_currency = :cost_currency WHERE id = :id"
            ),
            {
                "id": invocation_id,
                "response_digest": "9" * 64,
                "billing_status": billing_status,
                "cost_amount": cost_amount,
                "cost_currency": cost_currency,
            },
        )
        db_session.commit()
    db_session.rollback()
    _assert_temporal_billing_constraint(error.value)


@pytest.mark.parametrize(
    "classification",
    [
        InvocationClassification.FIXTURE,
        InvocationClassification.MOCK,
        InvocationClassification.LIVE,
    ],
)
def test_pre_dispatch_terminal_contract_is_consistent_for_every_classification(
    db_session: Session,
    classification: InvocationClassification,
) -> None:
    lifecycle, timing, _ = _prepare_lifecycle(db_session, classification=classification)
    lifecycle.fail(
        timing,
        ProviderError(
            ProviderErrorCategory.CANCELLED,
            "provider_cancelled",
            "Provider generation was cancelled",
        ),
    )
    invocation = _stored_invocation(db_session)
    assert invocation.status == "cancelled_before_dispatch"
    assert invocation.dispatch_started_at is None
    assert invocation.response_digest is None
    assert invocation.effective_model_status == "unavailable"
    assert invocation.effective_model_id is None
    assert invocation.upstream_request_id_status == "unavailable"
    assert invocation.upstream_request_id is None
    assert invocation.usage_status == "unavailable"
    assert invocation.input_tokens is None
    assert invocation.output_tokens is None
    assert invocation.total_tokens is None
    assert invocation.provider_elapsed_ms is None
    assert invocation.billing_status == "not_dispatched"
    assert invocation.cost_amount is None
    assert invocation.cost_currency is None


def test_pre_dispatch_cancellation_has_no_dispatch_or_governance_side_effect(
    db_session: Session,
) -> None:
    lifecycle, timing, _ = _prepare_lifecycle(
        db_session,
        classification=InvocationClassification.MOCK,
    )
    status = lifecycle.fail(
        timing,
        ProviderError(
            ProviderErrorCategory.CANCELLED,
            "provider_cancelled",
            "Provider generation was cancelled",
        ),
    )
    invocation = _stored_invocation(db_session)
    assert status == InvocationStatus.CANCELLED_BEFORE_DISPATCH
    assert invocation.dispatch_started_at is None
    assert invocation.provider_elapsed_ms is None
    for table in (
        "plans",
        "ai_eval_results",
        "execution_grants",
        "review_decisions",
        "delivery_authorizations",
        "runner_jobs",
        "workspace_events",
    ):
        assert db_session.scalar(text(f"SELECT count(*) FROM {table}")) == 0


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        (ProviderErrorCategory.RATE_LIMITED, InvocationStatus.FAILED),
        (ProviderErrorCategory.UPSTREAM_SERVER_ERROR, InvocationStatus.FAILED),
        (ProviderErrorCategory.TIMEOUT, InvocationStatus.OUTCOME_UNKNOWN),
        (ProviderErrorCategory.TRANSPORT_ERROR, InvocationStatus.OUTCOME_UNKNOWN),
        (ProviderErrorCategory.CANCELLED, InvocationStatus.OUTCOME_UNKNOWN),
    ],
)
def test_post_dispatch_failure_classification_is_explicit(
    db_session: Session,
    category: ProviderErrorCategory,
    expected: InvocationStatus,
) -> None:
    lifecycle, timing, _ = _prepare_lifecycle(
        db_session,
        classification=InvocationClassification.MOCK,
    )
    lifecycle.mark_dispatching(timing)
    actual = lifecycle.fail(
        timing,
        ProviderError(category, f"provider_{category.value}", "Safe fixed error"),
    )
    invocation = _stored_invocation(db_session)
    assert actual == expected
    assert invocation.status == expected.value
    assert invocation.response_digest is None


def test_stale_dispatch_reconciliation_uses_dispatch_boundary_not_created_at(
    db_session: Session,
) -> None:
    invocation = _direct_prepared_invocation(
        db_session,
        created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.execute(
        text(
            "UPDATE ai_provider_invocations SET status = 'dispatching', "
            "dispatch_started_at = now(), queue_wait_ms = 0 WHERE id = :id"
        ),
        {"id": invocation.id},
    )
    db_session.commit()
    db_session.refresh(invocation)
    assert invocation.dispatch_started_at is not None
    lifecycle = ProviderInvocationLifecycle(db_session)
    fresh = lifecycle.reconcile_stale_dispatching(stale_before=invocation.dispatch_started_at)
    assert fresh == []
    recovered = lifecycle.reconcile_stale_dispatching(
        stale_before=invocation.dispatch_started_at + timedelta(microseconds=1)
    )
    assert recovered == [invocation.id]
    db_session.refresh(invocation)
    assert invocation.status == "outcome_unknown"
    assert invocation.error_code == "provider_dispatch_stale_recovered"
    assert invocation.provider_elapsed_ms is None
    assert invocation.client_total_elapsed_ms is None
    assert db_session.scalar(text("SELECT count(*) FROM ai_provider_invocations")) == 1
    assert db_session.scalar(text("SELECT count(*) FROM plans")) == 0


def test_recovery_threshold_rejects_active_deadline_and_accepts_safe_minimum(
    db_session: Session,
) -> None:
    lifecycle, timing, _ = _prepare_lifecycle(
        db_session,
        classification=InvocationClassification.MOCK,
    )
    lifecycle.mark_dispatching(timing)
    with pytest.raises(ValueError, match="maximum Provider deadline"):
        lifecycle.reconcile_older_than(timedelta(seconds=PROVIDER_MAXIMUM_TOTAL_DEADLINE_SECONDS))
    with pytest.raises(ValueError, match="maximum Provider deadline"):
        lifecycle.reconcile_older_than(minimum_stale_dispatch_age() - timedelta(microseconds=1))
    assert lifecycle.reconcile_older_than(minimum_stale_dispatch_age()) == []
    assert _stored_invocation(db_session).status == "dispatching"


def test_two_reconcilers_use_skip_locked_and_transition_once(db_session: Session) -> None:
    invocation = _direct_prepared_invocation(
        db_session,
        created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    dispatched_at = datetime.now(UTC) - minimum_stale_dispatch_age() - timedelta(seconds=1)
    db_session.execute(
        text(
            "UPDATE ai_provider_invocations SET status = 'dispatching', "
            "dispatch_started_at = :dispatched_at, queue_wait_ms = 0 WHERE id = :id"
        ),
        {"dispatched_at": dispatched_at, "id": invocation.id},
    )
    db_session.commit()

    bind = db_session.get_bind()
    engine_url = bind.url if isinstance(bind, Engine) else bind.engine.url
    engine = create_engine(engine_url)
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def capture_statement(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if "ai_provider_invocations" in statement and "FOR UPDATE" in statement:
            statements.append(statement)

    barrier = threading.Barrier(2)

    def reconcile() -> list[uuid.UUID]:
        with Session(engine) as session:
            barrier.wait()
            return ProviderInvocationLifecycle(session).reconcile_stale_dispatching(
                stale_before=datetime.now(UTC)
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: reconcile(), range(2)))
    engine.dispose()
    assert sum(result == [invocation.id] for result in results) == 1
    assert sum(result == [] for result in results) == 1
    assert any("SKIP LOCKED" in statement for statement in statements)
    db_session.expire_all()
    assert _stored_invocation(db_session).status == "outcome_unknown"
    assert db_session.scalar(text("SELECT count(*) FROM ai_provider_invocations")) == 1


def test_api_startup_runs_one_shot_provider_reconciliation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from visual_engineer_api import main as main_module

    calls = 0

    def reconcile_once() -> list[uuid.UUID]:
        nonlocal calls
        calls += 1
        return []

    monkeypatch.setattr(main_module, "reconcile_stale_provider_invocations", reconcile_once)
    with TestClient(main_module.create_app(), raise_server_exceptions=False):
        pass
    assert calls == 1


def test_api_startup_recovery_failure_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from visual_engineer_api import main as main_module

    def unavailable_database() -> list[uuid.UUID]:
        raise RuntimeError("bounded startup recovery failure")

    monkeypatch.setattr(
        main_module,
        "reconcile_stale_provider_invocations",
        unavailable_database,
    )
    with pytest.raises(RuntimeError, match="bounded startup recovery failure"):
        with TestClient(main_module.create_app(), raise_server_exceptions=False):
            pass


@pytest.mark.parametrize(
    "overrides",
    [
        {"attempt_number": 0},
        {"provider_id": "outside-closed-registry"},
        {"classification": "fixture", "billing_status": "live_billing_unknown"},
        {"billing_status": "not_dispatched"},
        {
            "classification": "fixture",
            "usage_status": "reported_complete",
            "input_tokens": 1,
            "output_tokens": 2,
            "total_tokens": 3,
        },
        {
            "classification": "mock",
            "provider_id": "zhipu",
            "billing_status": "mock_not_billable",
            "usage_status": "reported_complete",
            "input_tokens": 1,
            "output_tokens": 2,
            "total_tokens": 3,
        },
        {
            "classification": "live",
            "provider_id": "zhipu",
            "billing_status": "live_billing_unknown",
            "usage_status": "synthetic_complete",
            "input_tokens": 1,
            "output_tokens": 2,
            "total_tokens": 3,
        },
        {"contract_version": 0},
        {"effective_model_status": "reported", "effective_model_id": None},
        {"upstream_request_id_status": "reported", "upstream_request_id": None},
        {"request_digest": "not-a-digest"},
        {"usage_status": "synthetic_complete"},
        {
            "classification": "live",
            "billing_status": "live_cost_reported",
            "cost_amount": None,
            "cost_currency": "USD",
        },
    ],
)
def test_database_rejects_invalid_invocation_contract_combinations(
    db_session: Session,
    overrides: dict[str, Any],
) -> None:
    ai_request = _create_request(db_session, _generation_request())
    values: dict[str, Any] = {
        "ai_plan_request_id": ai_request.id,
        "attempt_number": 1,
        "contract_version": 1,
        "classification": "fixture",
        "status": "prepared",
        "provider_id": "deterministic-fixture",
        "provider_metadata": {},
        "adapter_version": "adapter-v1",
        "requested_model_id": "model-v1",
        "effective_model_status": "unavailable",
        "effective_model_id": None,
        "upstream_request_id_status": "unavailable",
        "upstream_request_id": None,
        "request_digest": "5" * 64,
        "response_digest": None,
        "usage_status": "unavailable",
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "queue_wait_ms": None,
        "provider_elapsed_ms": None,
        "client_total_elapsed_ms": None,
        "billing_status": "not_billable_fixture",
        "cost_amount": None,
        "cost_currency": None,
        "error_category": None,
        "error_code": None,
        "redactions": [],
        "dispatch_started_at": None,
        "completed_at": None,
        **overrides,
    }
    db_session.add(AIProviderInvocation(**values))
    with pytest.raises(DBAPIError):
        db_session.commit()
    db_session.rollback()


def test_live_billing_defaults_unknown_and_accepts_only_reported_decimal_currency(
    db_session: Session,
) -> None:
    lifecycle, timing, _ = _prepare_lifecycle(
        db_session,
        classification=InvocationClassification.LIVE,
    )
    prepared = _stored_invocation(db_session)
    assert prepared.billing_status == "live_billing_unknown"
    assert prepared.cost_amount is None
    lifecycle.mark_dispatching(timing)
    lifecycle.succeed(
        timing,
        response_digest="6" * 64,
        effective_model_status=ReportedValueStatus.REPORTED,
        effective_model_id="model-v1",
        upstream_request_id_status=ReportedValueStatus.REPORTED,
        upstream_request_id="reported-upstream-id",
        usage_status=InvocationUsageStatus.REPORTED_COMPLETE,
        input_tokens=1,
        output_tokens=2,
        total_tokens=3,
        billing_status=InvocationBillingStatus.LIVE_COST_REPORTED,
        cost_amount=Decimal("0.12500000"),
        cost_currency="USD",
    )
    succeeded = _stored_invocation(db_session)
    assert succeeded.billing_status == "live_cost_reported"
    assert succeeded.cost_amount == Decimal("0.12500000")
    assert succeeded.cost_currency == "USD"


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        ((1, 2, 3), InvocationUsageStatus.REPORTED_COMPLETE),
        ((1, None, None), InvocationUsageStatus.REPORTED_PARTIAL),
        ((1, 2, 9), InvocationUsageStatus.REPORTED_INVALID),
        ((None, None, None), InvocationUsageStatus.UNAVAILABLE),
    ],
)
def test_reported_usage_status_preserves_missing_and_invalid_semantics(
    tokens: tuple[int | None, int | None, int | None],
    expected: InvocationUsageStatus,
) -> None:
    assert reported_usage_status(*tokens) == expected


def _synthetic_credential() -> str:
    return "-".join(("synthetic", "mock", "credential", "only"))


def _mock_success_payload(
    request: AIPlanGenerationRequest,
    *,
    usage: dict[str, int] | None = None,
    include_model: bool = True,
    include_request_id: bool = True,
) -> dict[str, Any]:
    plan = DeterministicFixtureProvider().generate(request, CancellationToken()).response_payload
    payload: dict[str, Any] = {
        "choices": [{"message": {"content": json.dumps(plan)}}],
        "usage": usage or {},
    }
    if include_model:
        payload["model"] = ZhipuAdapter.model_id
    if include_request_id:
        payload["request_id"] = "mock-upstream-request-001"
    return payload


def test_mock_adapter_success_persists_safe_invocation_then_allows_plan_creation(
    db_session: Session,
) -> None:
    request = _generation_request()
    ai_request = _create_request(db_session, request)
    ai_request.status = "generating"
    db_session.commit()
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            200,
            json=_mock_success_payload(
                request,
                usage={"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            ),
        )

    async def scenario() -> Any:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ZhipuAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
            )

            def persist(plan: Any) -> None:
                stored = db_session.get(AIPlanRequest, ai_request.id)
                assert stored is not None
                stored.status = "generated"
                stored.response_payload = plan.model_dump(mode="json")
                stored.deterministic_digest = plan.deterministic_digest

            return await invoke_mocked_adapter_contract(
                db_session,
                ai_plan_request_id=ai_request.id,
                adapter=adapter,
                request=request,
                cancellation=CancellationToken(),
                provider_metadata={"mock_contract_not_live": True},
                redactions=[],
                on_validated_plan=persist,
            )

    outcome = asyncio.run(scenario())
    invocation = _stored_invocation(db_session)
    stored_request = db_session.get(AIPlanRequest, ai_request.id)
    assert outcome.status == InvocationStatus.SUCCEEDED
    assert outcome.plan is not None
    assert call_count == 1
    assert invocation.classification == "mock"
    assert invocation.status == "succeeded"
    assert invocation.usage_status == "synthetic_complete"
    assert invocation.billing_status == "mock_not_billable"
    assert invocation.effective_model_id == ZhipuAdapter.model_id
    assert invocation.upstream_request_id == "mock-upstream-request-001"
    assert stored_request is not None and stored_request.response_payload is not None
    safe_response = AIPlanningService(
        db_session,
        settings=Settings(_env_file=None),
    ).response(ai_request.id)
    assert safe_response is not None
    safe = safe_response.model_dump_json()
    assert "mock-upstream-request-001" not in safe
    fingerprint = upstream_request_fingerprint("mock-upstream-request-001")
    assert fingerprint is not None
    assert fingerprint in safe
    persisted = json.dumps(
        {
            column.name: getattr(invocation, column.name)
            for column in AIProviderInvocation.__table__.columns
            if column.name not in {"created_at", "dispatch_started_at", "completed_at"}
        },
        default=str,
    )
    assert _synthetic_credential() not in persisted
    assert "messages" not in persisted
    assert "Authorization" not in persisted


def test_live_mock_transport_success_defaults_to_billing_unknown(
    db_session: Session,
) -> None:
    request = _generation_request()
    ai_request = _create_request(db_session, request)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_mock_success_payload(
                request,
                usage={"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            ),
        )

    async def scenario() -> Any:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ZhipuAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
            )
            return await invoke_mocked_adapter_contract(
                db_session,
                ai_plan_request_id=ai_request.id,
                adapter=adapter,
                request=request,
                cancellation=CancellationToken(),
                provider_metadata={"mock_transport_live_classification": True},
                redactions=[],
                classification=InvocationClassification.LIVE,
            )

    outcome = asyncio.run(scenario())
    invocation = _stored_invocation(db_session)
    assert outcome.status == InvocationStatus.SUCCEEDED
    assert invocation.classification == "live"
    assert invocation.status == "succeeded"
    assert invocation.usage_status == "reported_complete"
    assert invocation.billing_status == "live_billing_unknown"
    assert invocation.cost_amount is None
    assert invocation.cost_currency is None


@pytest.mark.parametrize(
    ("kind", "expected_status", "expected_category"),
    [
        ("401", InvocationStatus.FAILED, ProviderErrorCategory.AUTHENTICATION_FAILED),
        ("403", InvocationStatus.FAILED, ProviderErrorCategory.AUTHENTICATION_FAILED),
        ("429", InvocationStatus.FAILED, ProviderErrorCategory.RATE_LIMITED),
        ("503", InvocationStatus.FAILED, ProviderErrorCategory.UPSTREAM_SERVER_ERROR),
        ("timeout", InvocationStatus.OUTCOME_UNKNOWN, ProviderErrorCategory.TIMEOUT),
        ("transport", InvocationStatus.OUTCOME_UNKNOWN, ProviderErrorCategory.TRANSPORT_ERROR),
        ("malformed", InvocationStatus.FAILED, ProviderErrorCategory.STRUCTURED_OUTPUT_INVALID),
        ("oversize", InvocationStatus.FAILED, ProviderErrorCategory.BUDGET_EXCEEDED),
    ],
)
def test_mock_adapter_failure_is_single_attempt_and_creates_no_plan_or_authority(
    db_session: Session,
    kind: str,
    expected_status: InvocationStatus,
    expected_category: ProviderErrorCategory,
) -> None:
    request = _generation_request()
    ai_request = _create_request(db_session, request)
    ai_request.status = "generating"
    db_session.commit()
    call_count = 0

    def handler(http_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if kind.isdigit():
            return httpx.Response(int(kind))
        if kind == "timeout":
            raise httpx.ReadTimeout("mock timeout", request=http_request)
        if kind == "transport":
            raise httpx.ConnectError("mock transport", request=http_request)
        if kind == "malformed":
            return httpx.Response(200, json={"choices": []})
        return httpx.Response(200, content=b"x" * 4097)

    async def scenario() -> Any:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ZhipuAdapter(SecretStr(_synthetic_credential()), _test_client=client)
            return await invoke_mocked_adapter_contract(
                db_session,
                ai_plan_request_id=ai_request.id,
                adapter=adapter,
                request=request,
                cancellation=CancellationToken(),
                provider_metadata={"mock_contract_not_live": True},
                redactions=[],
                policy=ProviderCallPolicy(maximum_response_bytes=4096),
            )

    outcome = asyncio.run(scenario())
    invocation = _stored_invocation(db_session)
    assert outcome.status == expected_status
    assert outcome.error is not None and outcome.error.category == expected_category
    assert call_count == 1
    assert invocation.response_digest is None
    assert db_session.get(AIPlanRequest, ai_request.id).response_payload is None  # type: ignore[union-attr]
    for table in (
        "plans",
        "ai_eval_results",
        "execution_grants",
        "review_decisions",
        "delivery_authorizations",
        "runner_jobs",
    ):
        assert db_session.scalar(text(f"SELECT count(*) FROM {table}")) == 0


def test_mock_adapter_pre_dispatch_cancel_sends_no_http_request(db_session: Session) -> None:
    request = _generation_request()
    ai_request = _create_request(db_session, request)
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(500)

    cancellation = CancellationToken()
    cancellation.cancel()

    async def scenario() -> Any:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ZhipuAdapter(SecretStr(_synthetic_credential()), _test_client=client)
            return await invoke_mocked_adapter_contract(
                db_session,
                ai_plan_request_id=ai_request.id,
                adapter=adapter,
                request=request,
                cancellation=cancellation,
                provider_metadata={"mock_contract_not_live": True},
                redactions=[],
            )

    outcome = asyncio.run(scenario())
    invocation = _stored_invocation(db_session)
    assert outcome.status == InvocationStatus.CANCELLED_BEFORE_DISPATCH
    assert call_count == 0
    assert invocation.dispatch_started_at is None


def test_mock_contract_executor_rejects_production_transport_before_preparing(
    db_session: Session,
) -> None:
    request = _generation_request()
    ai_request = _create_request(db_session, request)
    adapter = ZhipuAdapter(SecretStr(_synthetic_credential()))
    with pytest.raises(RuntimeError, match="injected transport"):
        asyncio.run(
            invoke_mocked_adapter_contract(
                db_session,
                ai_plan_request_id=ai_request.id,
                adapter=adapter,
                request=request,
                cancellation=CancellationToken(),
                provider_metadata={"mock_contract_not_live": True},
                redactions=[],
            )
        )
    assert db_session.scalar(text("SELECT count(*) FROM ai_provider_invocations")) == 0


def test_mock_contract_executor_rejects_injected_non_mock_transport(
    db_session: Session,
) -> None:
    request = _generation_request()
    ai_request = _create_request(db_session, request)

    async def scenario() -> None:
        async with httpx.AsyncClient() as client:
            adapter = ZhipuAdapter(SecretStr(_synthetic_credential()), _test_client=client)
            await invoke_mocked_adapter_contract(
                db_session,
                ai_plan_request_id=ai_request.id,
                adapter=adapter,
                request=request,
                cancellation=CancellationToken(),
                provider_metadata={"mock_contract_not_live": True},
                redactions=[],
            )

    with pytest.raises(RuntimeError, match="injected transport"):
        asyncio.run(scenario())
    assert db_session.scalar(text("SELECT count(*) FROM ai_provider_invocations")) == 0


@pytest.mark.parametrize(
    ("usage", "expected", "expected_tokens"),
    [
        (
            {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            "synthetic_complete",
            (2, 3, 5),
        ),
        ({"prompt_tokens": 2}, "unavailable", (None, None, None)),
        (
            {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 9},
            "unavailable",
            (None, None, None),
        ),
        ({}, "unavailable", (None, None, None)),
        ({"prompt_tokens": -1}, "unavailable", (None, None, None)),
    ],
)
def test_mock_adapter_usage_and_missing_identity_are_truthful(
    db_session: Session,
    usage: dict[str, int],
    expected: str,
    expected_tokens: tuple[int | None, int | None, int | None],
) -> None:
    request = _generation_request()
    ai_request = _create_request(db_session, request)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_mock_success_payload(
                request,
                usage=usage,
                include_model=False,
                include_request_id=False,
            ),
        )

    async def scenario() -> Any:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = ZhipuAdapter(SecretStr(_synthetic_credential()), _test_client=client)
            return await invoke_mocked_adapter_contract(
                db_session,
                ai_plan_request_id=ai_request.id,
                adapter=adapter,
                request=request,
                cancellation=CancellationToken(),
                provider_metadata={"mock_contract_not_live": True},
                redactions=[],
            )

    outcome = asyncio.run(scenario())
    invocation = _stored_invocation(db_session)
    assert outcome.status == InvocationStatus.SUCCEEDED
    assert invocation.usage_status == expected
    assert (
        invocation.input_tokens,
        invocation.output_tokens,
        invocation.total_tokens,
    ) == expected_tokens
    assert invocation.effective_model_status == "unavailable"
    assert invocation.effective_model_id is None
    assert invocation.upstream_request_id_status == "unavailable"
    assert invocation.upstream_request_id is None


def test_outbound_digest_covers_actual_safe_body_and_changes_with_dispatch_options() -> None:
    request = _generation_request()
    adapter = ZhipuAdapter(SecretStr(_synthetic_credential()))
    first = canonical_digest(
        adapter.request_body(request, ProviderCallPolicy(maximum_output_tokens=2048))
    )
    changed_tokens = canonical_digest(
        adapter.request_body(request, ProviderCallPolicy(maximum_output_tokens=4096))
    )
    changed_message = canonical_digest(
        adapter.request_body(
            _generation_request(requirement="A different governed fixture Plan."),
            ProviderCallPolicy(maximum_output_tokens=2048),
        )
    )
    assert len(first) == 64
    assert first != changed_tokens
    assert first != changed_message
    assert _synthetic_credential() not in json.dumps(
        adapter.request_body(request, ProviderCallPolicy())
    )
