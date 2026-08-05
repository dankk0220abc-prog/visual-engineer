import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import visual_engineer_api.api.ai_planning as ai_planning_api
from visual_engineer_api.ai_planning.contracts import (
    AIPlanGenerationRequest,
    ContextBudget,
    ContextManifestEntry,
    DeliveryPackage,
    PromptBinding,
    RepositoryBinding,
    RepositoryFacts,
)
from visual_engineer_api.ai_planning.provider import (
    CancellationToken,
    ProviderError,
    ProviderErrorCategory,
)
from visual_engineer_api.ai_planning.provider_registry import (
    PROVIDER_DEFINITIONS,
    ProviderId,
    ProviderRegistry,
    ProviderStatusReason,
)
from visual_engineer_api.ai_planning.real_provider_adapters import (
    REAL_PROVIDER_ADAPTERS,
    DeepSeekAdapter,
    ProviderCallPolicy,
    RealProviderAdapter,
)
from visual_engineer_api.core.config import Settings


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "zhipu_api_key": "",
        "qwen_api_key": "",
        "deepseek_api_key": "",
        "doubao_api_key": "",
        "kimi_api_key": "",
        **overrides,
    }
    return Settings(_env_file=None, **values)


def _generation_request() -> AIPlanGenerationRequest:
    source_revision = "a" * 40
    snapshot_fingerprint = "b" * 64
    context_digest = "c" * 64
    return AIPlanGenerationRequest(
        delivery_package=DeliveryPackage.FRONTEND_QUALITY_REMEDIATION,
        requirement="Produce a bounded governed frontend quality remediation plan.",
        requirement_was_redacted=False,
        malicious_instruction_signals=[],
        repository=RepositoryBinding(
            source_revision=source_revision,
            snapshot_fingerprint=snapshot_fingerprint,
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
                source_revision=source_revision,
            )
        ],
        context_budget=ContextBudget(max_context_bytes=16_384, max_references=64),
        prompt=PromptBinding(
            template_id="governed-plan-v1",
            version="prompt-v1",
            digest="d" * 64,
            context_manifest_digest=context_digest,
            source_revision=source_revision,
            snapshot_fingerprint=snapshot_fingerprint,
        ),
    )


def _synthetic_credential() -> str:
    return "-".join(("synthetic", "credential", "contract", "only"))


def test_registry_is_closed_ordered_and_secret_safe() -> None:
    statuses = ProviderRegistry(_settings()).list()

    assert [item.provider_id for item in statuses] == [
        ProviderId.DETERMINISTIC_FIXTURE,
        ProviderId.ZHIPU,
        ProviderId.QWEN,
        ProviderId.DEEPSEEK,
        ProviderId.DOUBAO,
        ProviderId.KIMI,
    ]
    assert statuses[0].configured is True
    assert statuses[0].enabled is True
    assert statuses[0].reason_disabled is None
    assert all(item.configured is False for item in statuses[1:])
    assert all(item.enabled is False for item in statuses[1:])
    assert all(
        item.reason_disabled == ProviderStatusReason.MISSING_LOCAL_API_KEY for item in statuses[1:]
    )
    serialized = json.dumps([item.model_dump(mode="json") for item in statuses])
    assert "API_KEY" not in serialized
    assert "/Users/" not in serialized
    assert _synthetic_credential() not in serialized


def test_configured_real_provider_stays_disabled_until_live_validation() -> None:
    status = ProviderRegistry(_settings(zhipu_api_key=_synthetic_credential())).get(
        ProviderId.ZHIPU
    )

    assert status.configured is True
    assert status.enabled is False
    assert status.status_reason == ProviderStatusReason.LIVE_VALIDATION_NOT_PERFORMED
    assert status.reason_disabled == ProviderStatusReason.LIVE_VALIDATION_NOT_PERFORMED


def test_provider_discovery_api_matches_registry_without_secret_metadata(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ai_planning_api, "get_settings", _settings)

    response = client.get("/api/v1/ai-providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 6
    assert [item["provider_id"] for item in payload["items"]] == [
        item.provider_id.value for item in PROVIDER_DEFINITIONS
    ]
    serialized = response.text
    assert "API_KEY" not in serialized
    assert "Authorization" not in serialized
    assert "/Users/" not in serialized


@pytest.mark.parametrize(
    ("provider_id", "expected_override"),
    [
        (ProviderId.ZHIPU, ("thinking", {"type": "disabled"})),
        (ProviderId.QWEN, ("enable_thinking", False)),
        (ProviderId.DEEPSEEK, ("thinking", {"type": "disabled"})),
        (ProviderId.DOUBAO, ("thinking", {"type": "disabled"})),
        (ProviderId.KIMI, ("thinking", {"type": "disabled"})),
    ],
)
def test_real_adapters_map_requests_and_normalize_structured_responses(
    provider_id: ProviderId,
    expected_override: tuple[str, Any],
) -> None:
    adapter_type = REAL_PROVIDER_ADAPTERS[provider_id]
    credential = _synthetic_credential()
    observed: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["authorization"] = request.headers["Authorization"]
        observed["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "mock-request-001",
                "request_id": "mock-provider-request-001",
                "model": adapter_type.model_id,
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"schema_version": 1}),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 7,
                    "total_tokens": 18,
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = adapter_type(SecretStr(credential), client=client).invoke(
            _generation_request(),
            CancellationToken(),
            policy=ProviderCallPolicy(maximum_output_tokens=2048),
        )

    assert observed["url"] == adapter_type.endpoint
    assert observed["authorization"] == f"Bearer {credential}"
    body = observed["body"]
    assert body["model"] == adapter_type.model_id
    assert body["stream"] is False
    assert body["max_tokens"] == 2048
    assert body["response_format"] == {"type": "json_object"}
    assert body[expected_override[0]] == expected_override[1]
    assert "tools" not in body
    assert "base_url" not in body
    assert result.provider_id == provider_id
    assert result.model_id == adapter_type.model_id
    assert result.provider_request_id == "mock-provider-request-001"
    assert result.response_payload == {"schema_version": 1}
    assert result.usage.total_tokens == 18
    assert result.estimated_cost_microunits is None
    assert result.cost_basis == "not_configured"


@pytest.mark.parametrize(
    ("status_code", "category", "code"),
    [
        (401, ProviderErrorCategory.AUTHENTICATION_FAILED, "provider_authentication_failed"),
        (429, ProviderErrorCategory.RATE_LIMITED, "provider_rate_limited"),
        (404, ProviderErrorCategory.MODEL_UNAVAILABLE, "provider_model_unavailable"),
        (422, ProviderErrorCategory.REQUEST_REJECTED, "provider_request_rejected"),
        (503, ProviderErrorCategory.UPSTREAM_SERVER_ERROR, "provider_upstream_server_error"),
    ],
)
def test_adapter_maps_upstream_errors_without_returning_bodies(
    status_code: int,
    category: ProviderErrorCategory,
    code: str,
) -> None:
    credential = _synthetic_credential()

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={"error": {"message": f"upstream echoed {credential}"}},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = DeepSeekAdapter(SecretStr(credential), client=client)
        with pytest.raises(ProviderError) as caught:
            adapter.invoke(_generation_request(), CancellationToken())

    assert caught.value.category == category
    assert caught.value.code == code
    assert credential not in str(caught.value)


def test_malformed_response_maps_to_structured_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = DeepSeekAdapter(SecretStr(_synthetic_credential()), client=client)
        with pytest.raises(ProviderError) as caught:
            adapter.invoke(_generation_request(), CancellationToken())

    assert caught.value.category == ProviderErrorCategory.STRUCTURED_OUTPUT_INVALID
    assert caught.value.code == "provider_structured_output_invalid"


def test_transport_assertion_does_not_leak_secret_or_fragments() -> None:
    credential = _synthetic_credential()

    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError(
            f"header contained {credential}, prefix={credential[:9]}, suffix={credential[-9:]}"
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = DeepSeekAdapter(SecretStr(credential), client=client)
        with pytest.raises(ProviderError) as caught:
            adapter.invoke(_generation_request(), CancellationToken())

    assert caught.value.category == ProviderErrorCategory.TRANSPORT_ERROR
    assert caught.value.code == "provider_transport_error"
    public_error = str(caught.value)
    assert credential not in public_error
    assert credential[:9] not in public_error
    assert credential[-9:] not in public_error
    assert caught.value.__cause__ is None


def test_missing_secret_fails_before_transport_creation() -> None:
    adapter_type: Callable[..., RealProviderAdapter] = REAL_PROVIDER_ADAPTERS[ProviderId.ZHIPU]

    with pytest.raises(ProviderError) as caught:
        adapter_type(SecretStr(""))

    assert caught.value.category == ProviderErrorCategory.PROVIDER_NOT_CONFIGURED
    assert caught.value.code == "provider_not_configured"


def test_cancelled_request_fails_before_transport() -> None:
    transport_called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal transport_called
        transport_called = True
        return httpx.Response(500)

    cancellation = CancellationToken()
    cancellation.cancel()
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = DeepSeekAdapter(SecretStr(_synthetic_credential()), client=client)
        with pytest.raises(ProviderError) as caught:
            adapter.invoke(_generation_request(), cancellation)

    assert caught.value.category == ProviderErrorCategory.CANCELLED
    assert caught.value.code == "provider_cancelled"
    assert transport_called is False


def test_transport_timeout_is_sanitized_and_not_retryable() -> None:
    credential = _synthetic_credential()
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout(f"upstream echoed {credential}", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = DeepSeekAdapter(SecretStr(credential), client=client)
        with pytest.raises(ProviderError) as caught:
            adapter.invoke(_generation_request(), CancellationToken())

    assert call_count == 1
    assert caught.value.category == ProviderErrorCategory.TIMEOUT
    assert caught.value.code == "provider_timeout"
    assert caught.value.retryable is False
    assert credential not in str(caught.value)
    assert caught.value.__cause__ is None


def test_response_byte_budget_stops_stream_before_normalization() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 4097)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = DeepSeekAdapter(SecretStr(_synthetic_credential()), client=client)
        with pytest.raises(ProviderError) as caught:
            adapter.invoke(
                _generation_request(),
                CancellationToken(),
                policy=ProviderCallPolicy(maximum_response_bytes=4096),
            )

    assert caught.value.category == ProviderErrorCategory.BUDGET_EXCEEDED
    assert caught.value.code == "provider_response_budget_exceeded"


def test_adapter_concurrency_limit_fails_closed_without_queueing() -> None:
    request_entered = Event()
    release_request = Event()

    def handler(_: httpx.Request) -> httpx.Response:
        request_entered.set()
        if not release_request.wait(timeout=5):
            raise AssertionError("concurrency barrier was not released")
        return httpx.Response(
            200,
            json={
                "id": "mock-concurrency-request",
                "model": DeepSeekAdapter.model_id,
                "choices": [{"message": {"content": json.dumps({"schema_version": 1})}}],
                "usage": {},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        adapter = DeepSeekAdapter(SecretStr(_synthetic_credential()), client=client)
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(
                adapter.invoke,
                _generation_request(),
                CancellationToken(),
            )
            assert request_entered.wait(timeout=5)
            try:
                with pytest.raises(ProviderError) as caught:
                    adapter.invoke(_generation_request(), CancellationToken())
                assert caught.value.category == ProviderErrorCategory.BUDGET_EXCEEDED
                assert caught.value.code == "provider_concurrency_limit"
            finally:
                release_request.set()
            assert first.result(timeout=5).response_payload == {"schema_version": 1}


def test_arbitrary_endpoint_and_retry_configuration_are_rejected() -> None:
    class ArbitraryEndpointAdapter(RealProviderAdapter):
        provider_id = ProviderId.ZHIPU
        model_id = "attacker-controlled-model"
        endpoint = "https://example.invalid/chat/completions"

    with pytest.raises(RuntimeError, match="outside the built-in allowlist"):
        ArbitraryEndpointAdapter(SecretStr(_synthetic_credential()))
    with pytest.raises(ValueError):
        ProviderCallPolicy.model_validate({"maximum_retries": 1})
