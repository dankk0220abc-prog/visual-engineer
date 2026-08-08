import asyncio
import inspect
import ipaddress
import json
import ssl
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine
from typing import Any, ClassVar, Literal
from urllib.parse import urlsplit

import certifi
import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import visual_engineer_api.ai_planning.real_provider_adapters as provider_adapters
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
    PROVIDER_MAXIMUM_OUTPUT_TOKENS,
    REAL_PROVIDER_ADAPTERS,
    DeepSeekAdapter,
    ProviderAdapterResult,
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


def _run[T](coroutine: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coroutine)


def _invoke_with_transport(
    adapter_type: type[RealProviderAdapter],
    handler: (
        Callable[[httpx.Request], httpx.Response]
        | Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]
    ),
    *,
    credential: str | None = None,
    cancellation: CancellationToken | None = None,
    policy: ProviderCallPolicy | None = None,
    follow_redirects: bool = False,
) -> ProviderAdapterResult:
    async def invoke() -> ProviderAdapterResult:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            follow_redirects=follow_redirects,
        ) as client:
            adapter = adapter_type(
                SecretStr(credential or _synthetic_credential()),
                _test_client=client,
            )
            return await adapter.invoke(
                _generation_request(),
                cancellation or CancellationToken(),
                policy=policy,
            )

    return _run(invoke())


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

    result = _invoke_with_transport(
        adapter_type,
        handler,
        credential=credential,
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

    with pytest.raises(ProviderError) as caught:
        _invoke_with_transport(DeepSeekAdapter, handler, credential=credential)

    assert caught.value.category == category
    assert caught.value.code == code
    assert credential not in str(caught.value)


def test_malformed_response_maps_to_structured_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    with pytest.raises(ProviderError) as caught:
        _invoke_with_transport(DeepSeekAdapter, handler)

    assert caught.value.category == ProviderErrorCategory.STRUCTURED_OUTPUT_INVALID
    assert caught.value.code == "provider_structured_output_invalid"


def test_transport_assertion_does_not_leak_secret_or_fragments() -> None:
    credential = _synthetic_credential()

    def handler(_: httpx.Request) -> httpx.Response:
        raise AssertionError(
            f"header contained {credential}, prefix={credential[:9]}, suffix={credential[-9:]}"
        )

    with pytest.raises(ProviderError) as caught:
        _invoke_with_transport(DeepSeekAdapter, handler, credential=credential)

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
    with pytest.raises(ProviderError) as caught:
        _invoke_with_transport(DeepSeekAdapter, handler, cancellation=cancellation)

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

    with pytest.raises(ProviderError) as caught:
        _invoke_with_transport(DeepSeekAdapter, handler, credential=credential)

    assert call_count == 1
    assert caught.value.category == ProviderErrorCategory.TIMEOUT
    assert caught.value.code == "provider_timeout"
    assert caught.value.retryable is False
    assert credential not in str(caught.value)
    assert caught.value.__cause__ is None


def test_response_byte_budget_stops_stream_before_normalization() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 4097)

    with pytest.raises(ProviderError) as caught:
        _invoke_with_transport(
            DeepSeekAdapter,
            handler,
            policy=ProviderCallPolicy(maximum_response_bytes=4096),
        )

    assert caught.value.category == ProviderErrorCategory.BUDGET_EXCEEDED
    assert caught.value.code == "provider_response_budget_exceeded"


def _mock_success_response(*, stream: httpx.AsyncByteStream | None = None) -> httpx.Response:
    payload = {
        "id": "mock-request",
        "model": DeepSeekAdapter.model_id,
        "choices": [{"message": {"content": json.dumps({"schema_version": 1})}}],
        "usage": {},
    }
    if stream is not None:
        return httpx.Response(200, stream=stream)
    return httpx.Response(200, json=payload)


def _mock_success_bytes() -> bytes:
    return json.dumps(
        {
            "id": "mock-request",
            "model": DeepSeekAdapter.model_id,
            "choices": [{"message": {"content": json.dumps({"schema_version": 1})}}],
            "usage": {},
        }
    ).encode()


class _ManualDeadlineClock:
    def __init__(self) -> None:
        self.current = 0.0
        self.changed = asyncio.Event()

    def monotonic(self) -> float:
        return self.current

    async def wait_until(self, deadline_at: float) -> None:
        while self.current < deadline_at:
            await self.changed.wait()
            self.changed.clear()

    def expire(self) -> None:
        self.current += 1000.0
        self.changed.set()


class _ObservableSemaphore(asyncio.Semaphore):
    def __init__(self, value: int) -> None:
        super().__init__(value)
        self.acquire_entered = asyncio.Event()
        self.release_count = 0

    async def acquire(self) -> Literal[True]:
        self.acquire_entered.set()
        return await super().acquire()

    def release(self) -> None:
        self.release_count += 1
        super().release()


class _AcquireReturnBarrierAdapter(DeepSeekAdapter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.acquire_operation_completed = asyncio.Event()
        self.release_acquire_return = asyncio.Event()
        self._controlled_await_count = 0

    async def _await_controlled(
        self,
        operation: Awaitable[Any],
        *,
        cancellation: CancellationToken,
        cancellation_event: asyncio.Event,
        deadline_at: float,
        response: httpx.Response | None = None,
    ) -> Any:
        result = await super()._await_controlled(
            operation,
            cancellation=cancellation,
            cancellation_event=cancellation_event,
            deadline_at=deadline_at,
            response=response,
        )
        self._controlled_await_count += 1
        if self._controlled_await_count == 1:
            self.acquire_operation_completed.set()
            await self.release_acquire_return.wait()
        return result


class _ControlledAsyncStream(httpx.AsyncByteStream):
    def __init__(
        self,
        chunks: list[bytes],
        *,
        block_before_index: int | None = None,
        expire_after_last: Callable[[], None] | None = None,
        cancel_after_last: Callable[[], None] | None = None,
    ) -> None:
        self.chunks = chunks
        self.block_before_index = block_before_index
        self.expire_after_last = expire_after_last
        self.cancel_after_last = cancel_after_last
        self.chunk_waiting = asyncio.Event()
        self.release_chunk = asyncio.Event()
        self.closed = asyncio.Event()
        self.requested_chunks = 0
        self.yielded_chunks = 0
        self.close_count = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for index, chunk in enumerate(self.chunks):
            self.requested_chunks += 1
            if index == self.block_before_index:
                self.chunk_waiting.set()
                await self.release_chunk.wait()
            self.yielded_chunks += 1
            yield chunk
        if self.expire_after_last is not None:
            self.expire_after_last()
        if self.cancel_after_last is not None:
            self.cancel_after_last()

    async def aclose(self) -> None:
        self.close_count += 1
        self.closed.set()


async def _provider_error(awaitable: Awaitable[ProviderAdapterResult]) -> ProviderError:
    try:
        await awaitable
    except ProviderError as error:
        return error
    raise AssertionError("Provider invocation unexpectedly succeeded")


async def _assert_exact_single_permit_capacity(semaphore: _ObservableSemaphore) -> None:
    assert await semaphore.acquire() is True
    second_acquire_entered = asyncio.Event()
    semaphore.acquire_entered = second_acquire_entered
    second_acquire = asyncio.create_task(semaphore.acquire())
    await second_acquire_entered.wait()
    assert second_acquire.done() is False
    semaphore.release()
    assert await second_acquire is True
    semaphore.release()


def _pending_tasks() -> set[asyncio.Task[Any]]:
    current = asyncio.current_task()
    return {task for task in asyncio.all_tasks() if task is not current and not task.done()}


def test_outer_cancellation_after_completed_acquire_releases_exactly_once() -> None:
    async def scenario() -> None:
        semaphore = _ObservableSemaphore(1)
        call_count = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return _mock_success_response()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = _AcquireReturnBarrierAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_semaphore=semaphore,
            )
            invocation = asyncio.create_task(
                adapter.invoke(_generation_request(), CancellationToken())
            )
            await adapter.acquire_operation_completed.wait()
            assert semaphore.locked() is True
            invocation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await invocation

            assert semaphore.release_count == 1
            assert semaphore.locked() is False
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
            assert call_count == 1
            assert semaphore.release_count == 2
            await _assert_exact_single_permit_capacity(semaphore)
            assert _pending_tasks() == set()

    _run(scenario())


@pytest.mark.parametrize("competition", ["deadline", "token"])
def test_outer_cancellation_before_acquire_wins_control_competition(
    competition: str,
) -> None:
    async def scenario() -> None:
        clock = _ManualDeadlineClock()
        semaphore = _ObservableSemaphore(0)

        def handler(_: httpx.Request) -> httpx.Response:
            return _mock_success_response()

        cancellation = CancellationToken()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_clock=clock,
                _test_semaphore=semaphore,
            )
            invocation = asyncio.create_task(adapter.invoke(_generation_request(), cancellation))
            await semaphore.acquire_entered.wait()
            if competition == "deadline":
                clock.expire()
            else:
                cancellation.cancel()
            invocation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await invocation

            assert semaphore.release_count == 0
            semaphore.release()
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
            assert semaphore.release_count == 2
            await _assert_exact_single_permit_capacity(semaphore)
            assert _pending_tasks() == set()

    _run(scenario())


def test_outer_cancellation_during_provider_request_releases_slot() -> None:
    async def scenario() -> None:
        semaphore = _ObservableSemaphore(1)
        request_entered = asyncio.Event()
        request_cancelled = asyncio.Event()
        block_request = asyncio.Event()
        call_count = 0

        async def handler(_: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return _mock_success_response()
            request_entered.set()
            try:
                await block_request.wait()
            finally:
                request_cancelled.set()
            return _mock_success_response()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_semaphore=semaphore,
            )
            invocation = asyncio.create_task(
                adapter.invoke(_generation_request(), CancellationToken())
            )
            await request_entered.wait()
            invocation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await invocation
            assert request_cancelled.is_set()
            assert semaphore.release_count == 1
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
            assert semaphore.release_count == 2
            await _assert_exact_single_permit_capacity(semaphore)
            assert _pending_tasks() == set()

    _run(scenario())


def test_outer_cancellation_during_body_read_closes_and_releases_slot() -> None:
    async def scenario() -> None:
        semaphore = _ObservableSemaphore(1)
        payload = _mock_success_bytes()
        stream = _ControlledAsyncStream(
            [payload[:10], payload[10:]],
            block_before_index=1,
        )
        call_count = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return (
                _mock_success_response(stream=stream)
                if call_count == 1
                else _mock_success_response()
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_semaphore=semaphore,
            )
            invocation = asyncio.create_task(
                adapter.invoke(_generation_request(), CancellationToken())
            )
            await stream.chunk_waiting.wait()
            invocation.cancel()
            with pytest.raises(asyncio.CancelledError):
                await invocation
            assert stream.closed.is_set()
            assert semaphore.release_count == 1
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
            assert semaphore.release_count == 2
            await _assert_exact_single_permit_capacity(semaphore)
            assert _pending_tasks() == set()

    _run(scenario())


def test_repeated_outer_cancellation_cannot_interrupt_request_cleanup() -> None:
    async def scenario() -> None:
        semaphore = _ObservableSemaphore(1)
        request_entered = asyncio.Event()
        cleanup_entered = asyncio.Event()
        release_cleanup = asyncio.Event()
        cleanup_completed = asyncio.Event()
        call_count = 0

        async def handler(_: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return _mock_success_response()
            request_entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleanup_entered.set()
                await release_cleanup.wait()
                cleanup_completed.set()
            return _mock_success_response()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_semaphore=semaphore,
            )
            invocation = asyncio.create_task(
                adapter.invoke(_generation_request(), CancellationToken())
            )
            await request_entered.wait()
            invocation.cancel()
            await cleanup_entered.wait()
            invocation.cancel()
            release_cleanup.set()
            with pytest.raises(asyncio.CancelledError):
                await invocation

            assert cleanup_completed.is_set()
            assert semaphore.release_count == 1
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
            assert semaphore.release_count == 2
            await _assert_exact_single_permit_capacity(semaphore)
            assert _pending_tasks() == set()

    _run(scenario())


def test_provider_failure_releases_exactly_one_permit_for_next_request() -> None:
    async def scenario() -> None:
        semaphore = _ObservableSemaphore(1)
        call_count = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(503)
            return _mock_success_response()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_semaphore=semaphore,
            )
            error = await _provider_error(
                adapter.invoke(_generation_request(), CancellationToken())
            )
            assert error.category == ProviderErrorCategory.UPSTREAM_SERVER_ERROR
            assert semaphore.release_count == 1
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
            assert call_count == 2
            assert semaphore.release_count == 2
            await _assert_exact_single_permit_capacity(semaphore)
            assert _pending_tasks() == set()

    _run(scenario())


@pytest.mark.parametrize(("block_before_index", "expected_yielded"), [(1, 1), (2, 2)])
def test_cancellation_interrupts_response_chunks_without_consuming_the_stream(
    block_before_index: int,
    expected_yielded: int,
) -> None:
    async def scenario() -> None:
        payload = _mock_success_bytes()
        stream = _ControlledAsyncStream(
            [payload[:10], payload[10:20], payload[20:30], payload[30:]],
            block_before_index=block_before_index,
        )
        call_count = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return (
                _mock_success_response(stream=stream)
                if call_count == 1
                else _mock_success_response()
            )

        cancellation = CancellationToken()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
            )
            invocation = asyncio.create_task(adapter.invoke(_generation_request(), cancellation))
            await stream.chunk_waiting.wait()
            cancellation.cancel()
            error = await _provider_error(invocation)
            assert error.category == ProviderErrorCategory.CANCELLED
            assert error.code == "provider_cancelled"
            assert stream.yielded_chunks == expected_yielded
            assert stream.requested_chunks == expected_yielded + 1
            assert stream.requested_chunks < len(stream.chunks)
            assert stream.closed.is_set()
            assert stream.close_count >= 1
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
        assert call_count == 2

    _run(scenario())


def test_cancellation_interrupts_waiting_for_response_headers_without_retry() -> None:
    async def scenario() -> None:
        headers_entered = asyncio.Event()
        headers_cancelled = asyncio.Event()
        release_headers = asyncio.Event()
        call_count = 0

        async def handler(_: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return _mock_success_response()
            headers_entered.set()
            try:
                await release_headers.wait()
            finally:
                headers_cancelled.set()
            return _mock_success_response()

        cancellation = CancellationToken()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
            )
            invocation = asyncio.create_task(adapter.invoke(_generation_request(), cancellation))
            await headers_entered.wait()
            cancellation.cancel()
            error = await _provider_error(invocation)
            assert error.category == ProviderErrorCategory.CANCELLED
            assert headers_cancelled.is_set()
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
        assert call_count == 2

    _run(scenario())


@pytest.mark.parametrize("expiry", [False, True], ids=["cancellation", "deadline"])
def test_waiting_for_semaphore_is_cancellable_and_deadline_bounded(expiry: bool) -> None:
    async def scenario() -> None:
        clock = _ManualDeadlineClock()
        semaphore = _ObservableSemaphore(0)

        def handler(_: httpx.Request) -> httpx.Response:
            return _mock_success_response()

        cancellation = CancellationToken()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_clock=clock,
                _test_semaphore=semaphore,
            )
            invocation = asyncio.create_task(adapter.invoke(_generation_request(), cancellation))
            await semaphore.acquire_entered.wait()
            if expiry:
                clock.expire()
            else:
                cancellation.cancel()
            error = await _provider_error(invocation)
            assert error.category == (
                ProviderErrorCategory.TIMEOUT if expiry else ProviderErrorCategory.CANCELLED
            )
            assert error.code == (
                "provider_total_deadline_exceeded" if expiry else "provider_cancelled"
            )
            semaphore.release()
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
            assert semaphore.locked() is False

    _run(scenario())


def test_total_deadline_interrupts_response_body_closes_and_releases_slot() -> None:
    async def scenario() -> None:
        clock = _ManualDeadlineClock()
        payload = _mock_success_bytes()
        stream = _ControlledAsyncStream(
            [payload[:10], payload[10:20], payload[20:]],
            block_before_index=1,
        )
        call_count = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return (
                _mock_success_response(stream=stream)
                if call_count == 1
                else _mock_success_response()
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_clock=clock,
            )
            invocation = asyncio.create_task(
                adapter.invoke(_generation_request(), CancellationToken())
            )
            await stream.chunk_waiting.wait()
            clock.expire()
            error = await _provider_error(invocation)
            assert error.category == ProviderErrorCategory.TIMEOUT
            assert error.code == "provider_total_deadline_exceeded"
            assert stream.yielded_chunks == 1
            assert stream.requested_chunks == 2
            assert stream.requested_chunks < len(stream.chunks)
            assert stream.closed.is_set()
            assert stream.close_count >= 1
            result = await adapter.invoke(_generation_request(), CancellationToken())
            assert result.response_payload == {"schema_version": 1}
            assert adapter._concurrency.locked() is False
        assert call_count == 2

    _run(scenario())


@pytest.mark.parametrize("stop_kind", ["deadline", "cancellation"])
def test_stop_after_last_chunk_discards_body_before_normalization(stop_kind: str) -> None:
    async def scenario() -> None:
        clock = _ManualDeadlineClock()
        cancellation = CancellationToken()
        normalize_count = 0

        def after_normalize() -> None:
            nonlocal normalize_count
            normalize_count += 1

        stream = _ControlledAsyncStream(
            [_mock_success_bytes()],
            expire_after_last=clock.expire if stop_kind == "deadline" else None,
            cancel_after_last=cancellation.cancel if stop_kind == "cancellation" else None,
        )

        def handler(_: httpx.Request) -> httpx.Response:
            return _mock_success_response(stream=stream)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_clock=clock,
                _test_after_normalize=after_normalize,
            )
            error = await _provider_error(adapter.invoke(_generation_request(), cancellation))
        assert error.category == (
            ProviderErrorCategory.TIMEOUT
            if stop_kind == "deadline"
            else ProviderErrorCategory.CANCELLED
        )
        assert normalize_count == 0
        assert stream.closed.is_set()

    _run(scenario())


@pytest.mark.parametrize("stop_kind", ["deadline", "cancellation"])
def test_stop_after_normalization_discards_normalized_result(stop_kind: str) -> None:
    async def scenario() -> None:
        clock = _ManualDeadlineClock()
        cancellation = CancellationToken()
        normalized = asyncio.Event()

        def after_normalize() -> None:
            normalized.set()
            if stop_kind == "deadline":
                clock.expire()
            else:
                cancellation.cancel()

        def handler(_: httpx.Request) -> httpx.Response:
            return _mock_success_response()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = DeepSeekAdapter(
                SecretStr(_synthetic_credential()),
                _test_client=client,
                _test_clock=clock,
                _test_after_normalize=after_normalize,
            )
            error = await _provider_error(adapter.invoke(_generation_request(), cancellation))
        assert normalized.is_set()
        assert error.category == (
            ProviderErrorCategory.TIMEOUT
            if stop_kind == "deadline"
            else ProviderErrorCategory.CANCELLED
        )

    _run(scenario())


def test_output_token_contract_allows_4096_and_rejects_4097() -> None:
    policy = ProviderCallPolicy(maximum_output_tokens=PROVIDER_MAXIMUM_OUTPUT_TOKENS)
    body = DeepSeekAdapter(SecretStr(_synthetic_credential())).request_body(
        _generation_request(), policy
    )

    assert body["max_tokens"] == 4096
    schema = ProviderCallPolicy.model_json_schema()["properties"]["maximum_output_tokens"]
    assert schema["maximum"] == 4096
    with pytest.raises(ValueError):
        ProviderCallPolicy(maximum_output_tokens=4097)


def test_production_client_factory_ignores_proxy_and_tls_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in {
        "HTTP_PROXY": "http://127.0.0.1:1",
        "HTTPS_PROXY": "http://127.0.0.1:2",
        "ALL_PROXY": "socks5://127.0.0.1:3",
        "NO_PROXY": "*",
        "SSL_CERT_FILE": "/tmp/attacker-ca.pem",
        "SSL_CERT_DIR": "/tmp/attacker-ca-directory",
        "SSLKEYLOGFILE": "/tmp/synthetic-provider-tls-keylog",
    }.items():
        monkeypatch.setenv(name, value)

    observed_client: dict[str, Any] = {}
    original_client = httpx.AsyncClient

    def reject_default_context(*args: Any, **kwargs: Any) -> ssl.SSLContext:
        raise AssertionError("production TLS must not call ssl.create_default_context")

    def capture_client(**kwargs: Any) -> httpx.AsyncClient:
        observed_client.update(kwargs)
        return original_client(
            transport=httpx.MockTransport(lambda _: _mock_success_response()), **kwargs
        )

    monkeypatch.setattr(ssl, "create_default_context", reject_default_context)
    monkeypatch.setattr(httpx, "AsyncClient", capture_client)
    client = provider_adapters._create_production_client()
    _run(client.aclose())

    assert inspect.signature(provider_adapters._create_production_client).parameters == {}
    assert observed_client["trust_env"] is False
    assert observed_client["follow_redirects"] is False
    assert "proxy" not in observed_client
    assert "mounts" not in observed_client
    context = observed_client["verify"]
    assert isinstance(context, ssl.SSLContext)
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.keylog_filename is None


def test_provider_tls_context_loads_only_certifi_with_protocol_tls_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}

    class FakeTLSContext:
        check_hostname = False
        verify_mode = ssl.CERT_NONE
        keylog_filename = None

        def load_verify_locations(self, *, cafile: str) -> None:
            observed["cafile"] = cafile

    def capture_context(protocol: Any) -> FakeTLSContext:
        observed["protocol"] = protocol
        return FakeTLSContext()

    def reject_default_context(*args: Any, **kwargs: Any) -> ssl.SSLContext:
        raise AssertionError("production TLS must not call ssl.create_default_context")

    monkeypatch.setenv("SSLKEYLOGFILE", "/tmp/synthetic-provider-tls-keylog")
    monkeypatch.setattr(ssl, "SSLContext", capture_context)
    monkeypatch.setattr(ssl, "create_default_context", reject_default_context)
    context = provider_adapters._provider_tls_context()

    assert observed == {
        "protocol": ssl.PROTOCOL_TLS_CLIENT,
        "cafile": certifi.where(),
    }
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.keylog_filename is None


def test_mock_transport_is_test_only_and_redirects_do_not_forward_authorization() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(307, headers={"Location": "http://127.0.0.1/private"})

    with pytest.raises(ProviderError) as caught:
        _invoke_with_transport(DeepSeekAdapter, handler, follow_redirects=False)

    assert caught.value.category == ProviderErrorCategory.TRANSPORT_ERROR
    assert len(requests) == 1
    assert requests[0].headers["Authorization"].startswith("Bearer ")
    assert (
        "transport" not in inspect.signature(provider_adapters._create_production_client).parameters
    )
    with pytest.raises(ValueError):
        ProviderCallPolicy.model_validate({"transport": "attacker-controlled"})


def test_allowlisted_endpoints_exclude_local_file_and_private_networks() -> None:
    for adapter_type in REAL_PROVIDER_ADAPTERS.values():
        parsed = urlsplit(adapter_type.endpoint)
        assert parsed.scheme == "https"
        hostname = parsed.hostname
        assert hostname not in {None, "localhost"}
        assert hostname is not None
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            continue
        assert address.is_global


def test_arbitrary_endpoint_and_retry_configuration_are_rejected() -> None:
    class ArbitraryEndpointAdapter(RealProviderAdapter):
        provider_id = ProviderId.ZHIPU
        model_id = "attacker-controlled-model"
        endpoint = "https://example.invalid/chat/completions"

    with pytest.raises(RuntimeError, match="outside the built-in allowlist"):
        ArbitraryEndpointAdapter(SecretStr(_synthetic_credential()))
    with pytest.raises(ValueError):
        ProviderCallPolicy.model_validate({"maximum_retries": 1})

    class OutputOverrideAdapter(RealProviderAdapter):
        provider_id = ProviderId.ZHIPU
        model_id = "fixed-model"
        endpoint = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        request_overrides: ClassVar[dict[str, Any]] = {"max_tokens": 32_768}

    with pytest.raises(RuntimeError, match="protected fields"):
        OutputOverrideAdapter(SecretStr(_synthetic_credential()))
