import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select, text
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


def test_stale_dispatch_reconciliation_marks_unknown_without_retry_or_fake_latency(
    db_session: Session,
) -> None:
    lifecycle, timing, _ = _prepare_lifecycle(
        db_session,
        classification=InvocationClassification.MOCK,
    )
    lifecycle.mark_dispatching(timing)
    recovered = lifecycle.reconcile_stale_dispatching(
        stale_before=datetime.now(UTC) + timedelta(seconds=1)
    )
    invocation = _stored_invocation(db_session)
    assert recovered == [invocation.id]
    assert invocation.status == "outcome_unknown"
    assert invocation.error_code == "provider_dispatch_stale_recovered"
    assert invocation.provider_elapsed_ms is None
    assert invocation.client_total_elapsed_ms is None
    assert db_session.scalar(text("SELECT count(*) FROM ai_provider_invocations")) == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"attempt_number": 0},
        {"provider_id": "outside-closed-registry"},
        {"classification": "fixture", "billing_status": "live_billing_unknown"},
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
    assert invocation.usage_status == "reported_complete"
    assert invocation.billing_status == "mock_not_billable"
    assert invocation.effective_model_id == ZhipuAdapter.model_id
    assert invocation.upstream_request_id == "mock-upstream-request-001"
    assert stored_request is not None and stored_request.response_payload is not None
    safe_response = AIPlanningService(
        db_session,
        settings=Settings(
            _env_file=None,
            zhipu_api_key="",
            qwen_api_key="",
            deepseek_api_key="",
            doubao_api_key="",
            kimi_api_key="",
        ),
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
            "reported_complete",
            (2, 3, 5),
        ),
        ({"prompt_tokens": 2}, "reported_partial", (2, None, None)),
        (
            {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 9},
            "reported_invalid",
            (2, 3, 9),
        ),
        ({}, "unavailable", (None, None, None)),
        ({"prompt_tokens": -1}, "reported_invalid", (None, None, None)),
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
