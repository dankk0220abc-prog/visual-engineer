import asyncio
import inspect
import json
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from visual_engineer_api.ai_planning.contracts import AIPlanContract, canonical_digest
from visual_engineer_api.ai_planning.evaluator import evaluate_plan
from visual_engineer_api.ai_planning.fake_provider import DeterministicFixtureProvider
from visual_engineer_api.ai_planning.invocation_contract import InvocationStatus
from visual_engineer_api.ai_planning.provider import CancellationToken
from visual_engineer_api.ai_planning.provider_registry import ProviderId, ProviderRegistry
from visual_engineer_api.ai_planning.real_provider_adapters import ZhipuAdapter
from visual_engineer_api.ai_planning.zhipu_live_canary import (
    LIVE_CANARY_EVAL_IDS,
    ZHIPU_LIVE_CANARY_ENDPOINT,
    ZHIPU_LIVE_CANARY_MAXIMUM_OUTPUT_TOKENS,
    ZHIPU_LIVE_CANARY_MAXIMUM_RESPONSE_BYTES,
    ZHIPU_LIVE_CANARY_MODEL_ID,
    ZHIPU_LIVE_CANARY_PROVIDER_METADATA,
    ZHIPU_LIVE_CANARY_SCENARIO_ID,
    ZhipuLiveCanaryPlanContent,
    build_zhipu_live_canary_dispatch,
)
from visual_engineer_api.cli import zhipu_live_canary as canary_cli
from visual_engineer_api.core.config import Settings
from visual_engineer_api.models.ai_planning import (
    AIEvalResult,
    AIPlanDecision,
    AIPlanRequest,
    AIProviderInvocation,
)
from visual_engineer_api.models.delivery import DeliveryAuthorization
from visual_engineer_api.models.review import ReviewDecision
from visual_engineer_api.models.run import ApprovalDecision, Plan
from visual_engineer_api.models.runner import RunnerJob
from visual_engineer_api.models.workspace import ExecutionGrant, Workspace
from visual_engineer_api.services import zhipu_live_canary as canary_service
from visual_engineer_api.services.zhipu_live_canary import (
    LIVE_VALIDATION_AUTHORIZATION_ENV,
    USER_SECRET_PROVISION_REQUIRED,
    ZHIPU_API_KEY_ENV,
    ZHIPU_LIVE_CANARY_POLICY,
    UserSecretProvisionRequired,
    ZhipuLiveCanaryResult,
    ZhipuLiveCanaryService,
)

_REAL_PROVIDER_ENV = (
    "ZHIPU_API_KEY",
    "QWEN_API_KEY",
    "DEEPSEEK_API_KEY",
    "DOUBAO_API_KEY",
    "KIMI_API_KEY",
)
_AUTHORITY_MODELS = (
    Plan,
    ApprovalDecision,
    AIPlanDecision,
    ExecutionGrant,
    ReviewDecision,
    DeliveryAuthorization,
    RunnerJob,
    Workspace,
)


@pytest.fixture(autouse=True)
def _clear_real_provider_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (*_REAL_PROVIDER_ENV, LIVE_VALIDATION_AUTHORIZATION_ENV):
        monkeypatch.delenv(name, raising=False)


def _synthetic_credential() -> str:
    return "synthetic-zhipu-live-canary-credential-only"


def _valid_content() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "implementation_summary": (
            "Create a compact task card with clear hierarchy and two explicit actions."
        ),
        "accessibility_notes": [
            "Use native buttons with visible focus and an unambiguous keyboard order."
        ],
        "responsive_notes": ["Stack or wrap actions without overflow at the 390 px viewport."],
        "validation_notes": ["Verify keyboard access, focus visibility, and narrow layout."],
        "assumptions": ["The task title and status are already available as typed data."],
        "risks": [
            {
                "risk_id": "canary-action-density",
                "severity": "medium",
                "summary": "Two actions may become crowded on a narrow viewport.",
                "mitigation": "Allow the action row to wrap while preserving focus order.",
            }
        ],
        "unresolved_questions": [],
    }


def _provider_payload(content: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "choices": [{"message": {"content": json.dumps(content or _valid_content())}}],
        "model": ZHIPU_LIVE_CANARY_MODEL_ID,
        "request_id": "synthetic-upstream-request-id",
        "usage": {"prompt_tokens": 23, "completion_tokens": 17, "total_tokens": 40},
    }


def _authority_counts(session: Session) -> tuple[int, ...]:
    return tuple(
        int(session.scalar(select(func.count()).select_from(model)) or 0)
        for model in _AUTHORITY_MODELS
    )


async def _invoke_with_mock(
    session: Session,
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    cancellation: CancellationToken | None = None,
    after_normalize: Callable[[], None] | None = None,
) -> ZhipuLiveCanaryResult:
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = ZhipuAdapter(
            SecretStr(_synthetic_credential()),
            _test_client=client,
            _test_after_normalize=after_normalize,
        )
        service = ZhipuLiveCanaryService(
            session,
            adapter=adapter,
            _allow_mock_transport=True,
        )
        return await service.run(_test_cancellation=cancellation)


def _patch_safe_production_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(canary_service, "verify_repository_contract", lambda: None)
    monkeypatch.setattr(canary_service, "verify_database_contract", lambda: None)
    monkeypatch.setattr(canary_service, "verify_pre_live_safety_contract", lambda: None)


def test_fixed_scenario_and_outbound_contract_are_stable_and_secret_free() -> None:
    dispatch = build_zhipu_live_canary_dispatch()
    repeated = build_zhipu_live_canary_dispatch()
    adapter = ZhipuAdapter(SecretStr(_synthetic_credential()))
    body = adapter.request_body(dispatch, ZHIPU_LIVE_CANARY_POLICY)

    assert dispatch == repeated
    assert dispatch.scenario_id == ZHIPU_LIVE_CANARY_SCENARIO_ID
    assert dispatch.scenario_version == 1
    assert dispatch.requirement_was_redacted is False
    assert dispatch.malicious_instruction_signals == []
    assert body["model"] == ZHIPU_LIVE_CANARY_MODEL_ID
    assert body["max_tokens"] == ZHIPU_LIVE_CANARY_MAXIMUM_OUTPUT_TOKENS == 1024
    assert body["response_format"] == {"type": "json_object"}
    assert body["stream"] is False
    assert body["thinking"] == {"type": "disabled"}
    assert adapter.endpoint == ZHIPU_LIVE_CANARY_ENDPOINT
    assert _synthetic_credential() not in json.dumps(body)
    assert "Authorization" not in json.dumps(body)
    assert ZHIPU_LIVE_CANARY_POLICY.maximum_retries == 0
    assert ZHIPU_LIVE_CANARY_POLICY.concurrency_limit == 1
    assert len(json.dumps(_valid_content())) < 4096


def test_success_persists_live_invocation_typed_plan_and_evals_only(
    db_session: Session,
) -> None:
    request_count = 0
    sent_body: dict[str, Any] | None = None
    authority_before = _authority_counts(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count, sent_body
        request_count += 1
        sent_body = json.loads(request.content)
        assert request.url == ZHIPU_LIVE_CANARY_ENDPOINT
        return httpx.Response(200, json=_provider_payload())

    result = asyncio.run(_invoke_with_mock(db_session, handler))
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)
    ai_request = db_session.get(AIPlanRequest, result.ai_plan_request_id)

    assert request_count == 1
    assert sent_body is not None
    assert result.status == InvocationStatus.SUCCEEDED
    assert invocation is not None
    assert invocation.classification == "live"
    assert invocation.status == "succeeded"
    assert invocation.provider_id == "zhipu"
    assert invocation.requested_model_id == ZHIPU_LIVE_CANARY_MODEL_ID
    assert invocation.request_digest == canonical_digest(sent_body)
    assert invocation.usage_status == "reported_complete"
    assert invocation.billing_status == "live_billing_unknown"
    assert invocation.cost_amount is None
    assert invocation.cost_currency is None
    assert ai_request is not None
    assert ai_request.status == "generated"
    assert ai_request.response_payload is not None
    assert ai_request.response_payload["provider"]["provider_id"] == "zhipu"
    assert ai_request.response_payload["authority_boundary"] == {
        "provider_can_approve": False,
        "execution_grant_issued": False,
        "review_approval_issued": False,
        "delivery_authorization_issued": False,
        "git_or_deployment_authority": False,
    }
    eval_ids = tuple(
        db_session.scalars(
            select(AIEvalResult.eval_id)
            .where(AIEvalResult.ai_plan_request_id == ai_request.id)
            .order_by(AIEvalResult.created_at, AIEvalResult.eval_id)
        )
    )
    assert set(eval_ids) == set(LIVE_CANARY_EVAL_IDS)
    assert _authority_counts(db_session) == authority_before
    assert db_session.scalar(select(func.count()).select_from(Plan)) == 0

    persisted = json.dumps(
        {
            "request": ai_request.request_payload,
            "response": ai_request.response_payload,
            "invocation": {
                column.name: getattr(invocation, column.name)
                for column in AIProviderInvocation.__table__.columns
                if column.name not in {"created_at", "dispatch_started_at", "completed_at"}
            },
        },
        default=str,
    )
    assert _synthetic_credential() not in persisted
    assert "Authorization" not in persisted


def test_invalid_typed_content_is_failed_with_no_plan_or_eval(db_session: Session) -> None:
    request_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json=_provider_payload({"schema_version": 1}))

    result = asyncio.run(_invoke_with_mock(db_session, handler))
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)
    ai_request = db_session.get(AIPlanRequest, result.ai_plan_request_id)

    assert request_count == 1
    assert result.status == InvocationStatus.FAILED
    assert invocation is not None and invocation.error_code == "provider_schema_invalid"
    assert ai_request is not None and ai_request.status == "failed"
    assert ai_request.response_payload is None
    assert db_session.scalar(select(func.count()).select_from(AIEvalResult)) == 0
    assert db_session.scalar(select(func.count()).select_from(Plan)) == 0


@pytest.mark.parametrize(
    ("kind", "expected_status", "expected_category"),
    [
        ("401", "failed", "authentication_failed"),
        ("403", "failed", "authentication_failed"),
        ("429", "failed", "rate_limited"),
        ("503", "failed", "upstream_server_error"),
        ("malformed", "failed", "structured_output_invalid"),
        ("oversize", "failed", "budget_exceeded"),
        ("timeout", "outcome_unknown", "timeout"),
        ("transport", "outcome_unknown", "transport_error"),
    ],
)
def test_error_matrix_is_single_request_with_reviewed_terminal_semantics(
    db_session: Session,
    kind: str,
    expected_status: str,
    expected_category: str,
) -> None:
    request_count = 0
    authority_before = _authority_counts(db_session)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if kind.isdigit():
            return httpx.Response(int(kind), text=f"raw {_synthetic_credential()}")
        if kind == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        if kind == "transport":
            raise httpx.ConnectError("synthetic transport ambiguity", request=request)
        if kind == "malformed":
            return httpx.Response(200, json={"choices": []})
        return httpx.Response(
            200,
            content=b"x" * (ZHIPU_LIVE_CANARY_MAXIMUM_RESPONSE_BYTES + 1),
        )

    result = asyncio.run(_invoke_with_mock(db_session, handler))
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)
    ai_request = db_session.get(AIPlanRequest, result.ai_plan_request_id)

    assert request_count == 1
    assert result.status.value == expected_status
    assert invocation is not None
    assert invocation.status == expected_status
    assert invocation.error_category == expected_category
    assert invocation.response_digest is None
    assert ai_request is not None and ai_request.response_payload is None
    assert _authority_counts(db_session) == authority_before
    assert _synthetic_credential() not in json.dumps(
        {"error_category": invocation.error_category, "error_code": invocation.error_code}
    )


def test_pre_dispatch_cancellation_sends_zero_requests(db_session: Session) -> None:
    request_count = 0
    cancellation = CancellationToken()
    cancellation.cancel()

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(500)

    result = asyncio.run(_invoke_with_mock(db_session, handler, cancellation=cancellation))
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)

    assert request_count == 0
    assert result.status == InvocationStatus.CANCELLED_BEFORE_DISPATCH
    assert invocation is not None
    assert invocation.dispatch_started_at is None
    assert invocation.billing_status == "not_dispatched"


def test_post_dispatch_cancellation_is_outcome_unknown(db_session: Session) -> None:
    request_count = 0
    cancellation = CancellationToken()

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json=_provider_payload())

    result = asyncio.run(
        _invoke_with_mock(
            db_session,
            handler,
            cancellation=cancellation,
            after_normalize=cancellation.cancel,
        )
    )

    assert request_count == 1
    assert result.status == InvocationStatus.OUTCOME_UNKNOWN
    assert result.error_code == "provider_cancelled"


def test_preflight_is_secret_blind_read_only_and_network_free(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(canary_service, "verify_repository_contract", lambda: None)
    secret_read = False
    adapter_created = False

    def forbidden_secret_read() -> Settings:
        nonlocal secret_read
        secret_read = True
        raise AssertionError

    def forbidden_adapter(*_: Any, **__: Any) -> None:
        nonlocal adapter_created
        adapter_created = True
        raise AssertionError

    monkeypatch.setattr(canary_service, "_load_authorized_runtime_settings", forbidden_secret_read)
    monkeypatch.setattr(ZhipuAdapter, "__init__", forbidden_adapter)
    count_before = db_session.scalar(text("SELECT count(*) FROM ai_plan_requests"))

    result = canary_cli.main(["preflight"])
    output = capsys.readouterr()

    assert result == 0
    assert USER_SECRET_PROVISION_REQUIRED in output.out
    assert f"secret_variable={ZHIPU_API_KEY_ENV}" in output.out
    assert secret_read is False
    assert adapter_created is False
    assert db_session.scalar(text("SELECT count(*) FROM ai_plan_requests")) == count_before


@pytest.mark.parametrize("authorization", [None, "", "0", "true", "yes", "2"])
def test_authorization_fails_before_secret_read(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    authorization: str | None,
) -> None:
    _patch_safe_production_gates(monkeypatch)
    if authorization is not None:
        monkeypatch.setenv(LIVE_VALIDATION_AUTHORIZATION_ENV, authorization)
    secret_read = False

    def forbidden_secret_read() -> Settings:
        nonlocal secret_read
        secret_read = True
        raise AssertionError

    monkeypatch.setattr(canary_service, "_load_authorized_runtime_settings", forbidden_secret_read)

    result = canary_cli.main(["run"])
    output = capsys.readouterr()

    assert result == 1
    assert "LIVE_VALIDATION_AUTHORIZATION_REQUIRED" in output.err
    assert secret_read is False


def test_authorized_missing_key_stops_before_adapter_or_database_write(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_safe_production_gates(monkeypatch)
    monkeypatch.setenv(LIVE_VALIDATION_AUTHORIZATION_ENV, "1")
    adapter_created = False

    def forbidden_adapter(*_: Any, **__: Any) -> None:
        nonlocal adapter_created
        adapter_created = True
        raise AssertionError

    monkeypatch.setattr(ZhipuAdapter, "__init__", forbidden_adapter)
    count_before = db_session.scalar(text("SELECT count(*) FROM ai_plan_requests"))

    result = canary_cli.main(["run"])
    output = capsys.readouterr()

    assert result == 1
    assert USER_SECRET_PROVISION_REQUIRED in output.out
    assert adapter_created is False
    assert db_session.scalar(text("SELECT count(*) FROM ai_plan_requests")) == count_before


def test_production_factory_enforces_gate_order_before_secret_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setenv(LIVE_VALIDATION_AUTHORIZATION_ENV, "1")
    monkeypatch.setattr(
        canary_service, "verify_repository_contract", lambda: events.append("repository")
    )
    monkeypatch.setattr(
        canary_service, "verify_database_contract", lambda: events.append("database")
    )
    monkeypatch.setattr(
        canary_service,
        "require_live_validation_authorization",
        lambda: events.append("authorization"),
    )
    monkeypatch.setattr(
        canary_service,
        "verify_pre_live_safety_contract",
        lambda: events.append("safety"),
    )

    def stop_at_secret() -> Settings:
        events.append("secret")
        raise UserSecretProvisionRequired()

    monkeypatch.setattr(canary_service, "_load_authorized_runtime_settings", stop_at_secret)

    with pytest.raises(UserSecretProvisionRequired):
        with canary_service.production_zhipu_live_canary_service():
            pass

    assert events == ["repository", "database", "authorization", "safety", "secret"]


def test_production_factory_has_no_injection_parameters_and_builds_real_transport(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_safe_production_gates(monkeypatch)
    monkeypatch.setenv(LIVE_VALIDATION_AUTHORIZATION_ENV, "1")
    monkeypatch.setenv(ZHIPU_API_KEY_ENV, _synthetic_credential())

    assert inspect.signature(canary_service.production_zhipu_live_canary_service).parameters == {}
    forbidden_settings = {"transport", "endpoint", "model", "headers", "maximum_output_tokens"}
    assert forbidden_settings.isdisjoint(Settings.model_fields)

    with canary_service.production_zhipu_live_canary_service() as service:
        assert service._adapter.provider_id == ProviderId.ZHIPU
        assert service._adapter.uses_injected_mock_transport is False

    with pytest.raises(TypeError):
        canary_service.production_zhipu_live_canary_service(  # type: ignore[call-arg]
            httpx.MockTransport(lambda _: httpx.Response(200))
        )


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["run", "--provider", "qwen"],
        ["run", "--model", "other"],
        ["run", "--endpoint", "https://example.invalid"],
        ["run", "--prompt", "free text"],
        ["run", "--header", "X-Test:value"],
        ["run", "--repo", "/tmp/example"],
        ["run", "--output", "/tmp/output"],
        ["run", "--max-tokens", "4096"],
    ],
)
def test_cli_rejects_every_arbitrary_contract_override(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
) -> None:
    def forbidden_factory() -> Generator[ZhipuLiveCanaryService, None, None]:
        raise AssertionError
        yield  # pragma: no cover

    monkeypatch.setattr(canary_cli, "production_zhipu_live_canary_service", forbidden_factory)

    assert canary_cli.main(arguments) == 2
    assert "usage: zhipu-live-canary {preflight|run}" in capsys.readouterr().err


def test_cli_safe_output_and_settings_repr_never_expose_synthetic_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    synthetic = _synthetic_credential()
    monkeypatch.setenv(ZHIPU_API_KEY_ENV, synthetic)
    result = ZhipuLiveCanaryResult(
        ai_plan_request_id=uuid.uuid4(),
        invocation_id=uuid.uuid4(),
        status=InvocationStatus.SUCCEEDED,
        provider_id="zhipu",
        requested_model_id=ZHIPU_LIVE_CANARY_MODEL_ID,
        effective_model_status="reported",
        upstream_request_id_status="reported",
        upstream_request_fingerprint="abc123def456",
        usage_status="reported_complete",
        input_tokens=23,
        output_tokens=17,
        total_tokens=40,
        queue_wait_ms=1,
        provider_elapsed_ms=2,
        client_total_elapsed_ms=3,
        billing_status="live_billing_unknown",
        error_code=None,
    )

    class FakeService:
        async def run(self) -> ZhipuLiveCanaryResult:
            return result

    @contextmanager
    def fake_factory() -> Generator[FakeService, None, None]:
        yield FakeService()

    monkeypatch.setattr(canary_cli, "production_zhipu_live_canary_service", fake_factory)

    assert canary_cli.main(["run"]) == 0
    output = capsys.readouterr()
    settings = Settings(
        _env_file=None,
        zhipu_api_key=synthetic,
        qwen_api_key="",
        deepseek_api_key="",
        doubao_api_key="",
        kimi_api_key="",
        runner_bootstrap_token="",
    )
    combined = output.out + output.err + repr(settings)
    assert synthetic not in combined
    assert "synthetic-upstream-request-id" not in combined
    assert "LIVE ZHIPU CANARY — ONE EXTERNAL REQUEST MAY BE SENT" in output.out
    assert "billing_status=live_billing_unknown" in output.out


def test_product_registry_keeps_every_real_provider_disabled() -> None:
    assert ProviderRegistry.is_enabled(ProviderId.DETERMINISTIC_FIXTURE) is True
    for provider_id in (
        ProviderId.ZHIPU,
        ProviderId.QWEN,
        ProviderId.DEEPSEEK,
        ProviderId.DOUBAO,
        ProviderId.KIMI,
    ):
        assert ProviderRegistry.is_enabled(provider_id) is False


def test_ordinary_fixture_eval_rejects_live_capability_metadata() -> None:
    request = build_zhipu_live_canary_dispatch()
    provider = DeterministicFixtureProvider()
    generated = provider.generate(request, CancellationToken()).response_payload
    values = AIPlanContract.model_validate(generated).model_dump(
        mode="json", exclude={"deterministic_digest"}
    )
    values["provider"] = ZHIPU_LIVE_CANARY_PROVIDER_METADATA.model_dump(mode="json")
    values["deterministic_digest"] = canonical_digest(values)
    tampered = AIPlanContract.model_validate(values)
    results = evaluate_plan(
        request,
        tampered,
        {
            "template_id": request.prompt.template_id,
            "version": request.prompt.version,
            "digest": request.prompt.digest,
        },
        provider,
        expected_source_revision=request.repository.source_revision,
        expected_snapshot_fingerprint=request.repository.snapshot_fingerprint,
    )

    binding = next(item for item in results if item.eval_id == "generation_binding_integrity")
    assert binding.passed is False
    assert binding.evidence["provider_capability_binding_matches"] is False


def test_plan_content_schema_rejects_extra_fields_and_unbounded_text() -> None:
    with pytest.raises(ValidationError):
        ZhipuLiveCanaryPlanContent.model_validate({**_valid_content(), "prompt": "arbitrary"})
    with pytest.raises(ValueError):
        ZhipuLiveCanaryPlanContent.model_validate(
            {**_valid_content(), "accessibility_notes": ["x" * 501]}
        ).bounded()
