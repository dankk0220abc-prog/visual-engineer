import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from sqlalchemy.orm import Session

from visual_engineer_api.ai_planning.contracts import (
    AIPlanContract,
    AIPlanGenerationRequest,
    canonical_digest,
)
from visual_engineer_api.ai_planning.invocation_contract import (
    INVOCATION_CONTRACT_VERSION,
    InvocationBillingStatus,
    InvocationClassification,
    InvocationStatus,
    InvocationUsageStatus,
    ReportedValueStatus,
    normalized_response_digest,
)
from visual_engineer_api.ai_planning.provider import (
    CancellationToken,
    ProviderError,
    ProviderErrorCategory,
)
from visual_engineer_api.ai_planning.real_provider_adapters import (
    ProviderAdapterResult,
    ProviderCallPolicy,
    RealProviderAdapter,
)
from visual_engineer_api.models.ai_planning import AIProviderInvocation
from visual_engineer_api.repositories.ai_planning import AIPlanningRepository


class MonotonicClock(Protocol):
    def monotonic(self) -> float: ...


class SystemMonotonicClock:
    def monotonic(self) -> float:
        return time.monotonic()


@dataclass
class InvocationTiming:
    invocation_id: uuid.UUID
    client_started: float
    dispatch_started: float | None = None


@dataclass(frozen=True)
class AdapterInvocationOutcome:
    status: InvocationStatus
    result: ProviderAdapterResult | None
    plan: AIPlanContract | None
    error: ProviderError | None


def reported_usage_status(
    input_tokens: int | None,
    output_tokens: int | None,
    total_tokens: int | None,
) -> InvocationUsageStatus:
    values = (input_tokens, output_tokens, total_tokens)
    present = sum(value is not None for value in values)
    if present == 0:
        return InvocationUsageStatus.UNAVAILABLE
    if present == 3:
        assert input_tokens is not None
        assert output_tokens is not None
        assert total_tokens is not None
        return (
            InvocationUsageStatus.REPORTED_COMPLETE
            if total_tokens == input_tokens + output_tokens
            else InvocationUsageStatus.REPORTED_INVALID
        )
    if total_tokens is not None and (
        (input_tokens is not None and total_tokens < input_tokens)
        or (output_tokens is not None and total_tokens < output_tokens)
    ):
        return InvocationUsageStatus.REPORTED_INVALID
    return InvocationUsageStatus.REPORTED_PARTIAL


async def invoke_mocked_adapter_contract(
    session: Session,
    *,
    ai_plan_request_id: uuid.UUID,
    adapter: RealProviderAdapter,
    request: AIPlanGenerationRequest,
    cancellation: CancellationToken,
    provider_metadata: dict[str, object],
    redactions: list[dict[str, object]],
    policy: ProviderCallPolicy | None = None,
    classification: InvocationClassification = InvocationClassification.MOCK,
    on_validated_plan: Callable[[AIPlanContract], None] | None = None,
) -> AdapterInvocationOutcome:
    if not adapter.uses_injected_mock_transport:
        raise RuntimeError("mock contract invocation requires an injected transport")
    call_policy = policy or ProviderCallPolicy()
    lifecycle = ProviderInvocationLifecycle(session)
    timing = lifecycle.prepare(
        ai_plan_request_id=ai_plan_request_id,
        attempt_number=1,
        classification=classification,
        provider_id=adapter.provider_id.value,
        provider_metadata=provider_metadata,
        adapter_version=adapter.adapter_version,
        requested_model_id=adapter.model_id,
        request_digest=canonical_digest(adapter.request_body(request, call_policy)),
        redactions=redactions,
    )
    try:
        result = await adapter.invoke(
            request,
            cancellation,
            policy=call_policy,
            on_dispatch_ready=lambda: lifecycle.mark_dispatching(timing),
        )
    except ProviderError as error:
        status = lifecycle.fail(timing, error)
        return AdapterInvocationOutcome(status=status, result=None, plan=None, error=error)
    try:
        plan = AIPlanContract.model_validate(result.response_payload)
    except ValueError:
        schema_error = ProviderError(
            ProviderErrorCategory.INVALID_RESPONSE,
            "provider_schema_invalid",
            "Provider response did not match the AI Plan contract",
        )
        status = lifecycle.fail(timing, schema_error, force_definite=True)
        return AdapterInvocationOutcome(
            status=status,
            result=result,
            plan=None,
            error=schema_error,
        )

    usage_status = (
        InvocationUsageStatus.REPORTED_INVALID
        if result.usage.reported_invalid
        else reported_usage_status(
            result.usage.input_tokens,
            result.usage.output_tokens,
            result.usage.total_tokens,
        )
    )
    effective_status = (
        ReportedValueStatus.REPORTED
        if result.model_id is not None
        else ReportedValueStatus.UNAVAILABLE
    )
    upstream_status = (
        ReportedValueStatus.REPORTED
        if result.provider_request_id is not None
        else ReportedValueStatus.UNAVAILABLE
    )
    plan_payload = plan.model_dump(mode="json")
    response_digest = normalized_response_digest(
        plan_payload=plan_payload,
        effective_model_status=effective_status,
        effective_model_id=result.model_id,
        upstream_request_id_status=upstream_status,
        upstream_request_id=result.provider_request_id,
        usage_status=usage_status,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        total_tokens=result.usage.total_tokens,
    )
    lifecycle.succeed(
        timing,
        response_digest=response_digest,
        effective_model_status=effective_status,
        effective_model_id=result.model_id,
        upstream_request_id_status=upstream_status,
        upstream_request_id=result.provider_request_id,
        usage_status=usage_status,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        total_tokens=result.usage.total_tokens,
    )
    if on_validated_plan is not None:
        on_validated_plan(plan)
        session.commit()
    return AdapterInvocationOutcome(
        status=InvocationStatus.SUCCEEDED,
        result=result,
        plan=plan,
        error=None,
    )


class ProviderInvocationLifecycle:
    def __init__(
        self,
        session: Session,
        *,
        clock: MonotonicClock | None = None,
    ) -> None:
        self._session = session
        self._repository = AIPlanningRepository(session)
        self._clock = clock or SystemMonotonicClock()

    def prepare(
        self,
        *,
        ai_plan_request_id: uuid.UUID,
        attempt_number: int,
        classification: InvocationClassification,
        provider_id: str,
        provider_metadata: dict[str, object],
        adapter_version: str,
        requested_model_id: str,
        request_digest: str,
        redactions: list[dict[str, object]],
    ) -> InvocationTiming:
        client_started = self._clock.monotonic()
        billing_status = {
            InvocationClassification.FIXTURE: InvocationBillingStatus.NOT_BILLABLE_FIXTURE,
            InvocationClassification.MOCK: InvocationBillingStatus.MOCK_NOT_BILLABLE,
            InvocationClassification.LIVE: InvocationBillingStatus.LIVE_BILLING_UNKNOWN,
        }[classification]
        invocation = AIProviderInvocation(
            ai_plan_request_id=ai_plan_request_id,
            attempt_number=attempt_number,
            contract_version=INVOCATION_CONTRACT_VERSION,
            classification=classification.value,
            status=InvocationStatus.PREPARED.value,
            provider_id=provider_id,
            provider_metadata=provider_metadata,
            adapter_version=adapter_version,
            requested_model_id=requested_model_id,
            effective_model_status=ReportedValueStatus.UNAVAILABLE.value,
            effective_model_id=None,
            upstream_request_id_status=ReportedValueStatus.UNAVAILABLE.value,
            upstream_request_id=None,
            request_digest=request_digest,
            response_digest=None,
            usage_status=InvocationUsageStatus.UNAVAILABLE.value,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            queue_wait_ms=None,
            provider_elapsed_ms=None,
            client_total_elapsed_ms=None,
            billing_status=billing_status.value,
            cost_amount=None,
            cost_currency=None,
            error_category=None,
            error_code=None,
            redactions=redactions,
            dispatch_started_at=None,
            completed_at=None,
        )
        self._repository.add(invocation)
        self._session.commit()
        return InvocationTiming(invocation_id=invocation.id, client_started=client_started)

    def mark_dispatching(self, timing: InvocationTiming) -> None:
        invocation = self._require(timing.invocation_id)
        if invocation.status != InvocationStatus.PREPARED.value:
            raise RuntimeError("Provider invocation is not prepared")
        queue_acquired = self._clock.monotonic()
        invocation.status = InvocationStatus.DISPATCHING.value
        invocation.dispatch_started_at = datetime.now(UTC)
        invocation.queue_wait_ms = _elapsed_ms(timing.client_started, queue_acquired)
        self._session.commit()
        timing.dispatch_started = self._clock.monotonic()

    def succeed(
        self,
        timing: InvocationTiming,
        *,
        response_digest: str,
        effective_model_status: ReportedValueStatus,
        effective_model_id: str | None,
        upstream_request_id_status: ReportedValueStatus,
        upstream_request_id: str | None,
        usage_status: InvocationUsageStatus,
        input_tokens: int | None,
        output_tokens: int | None,
        total_tokens: int | None,
        billing_status: InvocationBillingStatus | None = None,
        cost_amount: Decimal | None = None,
        cost_currency: str | None = None,
    ) -> None:
        invocation = self._require(timing.invocation_id)
        if invocation.status != InvocationStatus.DISPATCHING.value:
            raise RuntimeError("Provider invocation did not cross the dispatch boundary")
        now = self._clock.monotonic()
        if timing.dispatch_started is None:
            raise RuntimeError("Provider dispatch timing is unavailable")
        invocation.status = InvocationStatus.SUCCEEDED.value
        invocation.response_digest = response_digest
        invocation.effective_model_status = effective_model_status.value
        invocation.effective_model_id = effective_model_id
        invocation.upstream_request_id_status = upstream_request_id_status.value
        invocation.upstream_request_id = upstream_request_id
        invocation.usage_status = usage_status.value
        invocation.input_tokens = input_tokens
        invocation.output_tokens = output_tokens
        invocation.total_tokens = total_tokens
        if billing_status is not None:
            invocation.billing_status = billing_status.value
            invocation.cost_amount = cost_amount
            invocation.cost_currency = cost_currency
        invocation.provider_elapsed_ms = _elapsed_ms(timing.dispatch_started, now)
        invocation.client_total_elapsed_ms = _elapsed_ms(timing.client_started, now)
        invocation.completed_at = datetime.now(UTC)
        self._session.commit()

    def fail(
        self,
        timing: InvocationTiming,
        error: ProviderError,
        *,
        force_definite: bool = False,
    ) -> InvocationStatus:
        invocation = self._require(timing.invocation_id)
        now = self._clock.monotonic()
        if invocation.status == InvocationStatus.PREPARED.value:
            status = (
                InvocationStatus.CANCELLED_BEFORE_DISPATCH
                if error.category == ProviderErrorCategory.CANCELLED
                else InvocationStatus.FAILED
            )
        elif invocation.status == InvocationStatus.DISPATCHING.value:
            ambiguous = error.category in {
                ProviderErrorCategory.TIMEOUT,
                ProviderErrorCategory.TRANSPORT_ERROR,
                ProviderErrorCategory.CANCELLED,
                ProviderErrorCategory.INTERNAL,
            }
            status = (
                InvocationStatus.OUTCOME_UNKNOWN
                if ambiguous and not force_definite
                else InvocationStatus.FAILED
            )
            if timing.dispatch_started is None:
                raise RuntimeError("Provider dispatch timing is unavailable")
            invocation.provider_elapsed_ms = _elapsed_ms(timing.dispatch_started, now)
        else:
            raise RuntimeError("Provider invocation is already terminal")
        invocation.status = status.value
        invocation.error_category = error.category.value
        invocation.error_code = error.code[:64]
        invocation.client_total_elapsed_ms = _elapsed_ms(timing.client_started, now)
        invocation.completed_at = datetime.now(UTC)
        self._session.commit()
        return status

    def reconcile_stale_dispatching(
        self,
        *,
        stale_before: datetime,
        limit: int = 100,
    ) -> list[uuid.UUID]:
        if stale_before.tzinfo is None:
            raise ValueError("stale cutoff must be timezone-aware")
        recovered: list[uuid.UUID] = []
        for invocation in self._repository.stale_dispatching(
            created_before=stale_before,
            limit=limit,
        ):
            invocation.status = InvocationStatus.OUTCOME_UNKNOWN.value
            invocation.error_category = ProviderErrorCategory.TRANSPORT_ERROR.value
            invocation.error_code = "provider_dispatch_stale_recovered"
            invocation.completed_at = datetime.now(UTC)
            recovered.append(invocation.id)
        self._session.commit()
        return recovered

    def reconcile_older_than(self, age: timedelta, *, limit: int = 100) -> list[uuid.UUID]:
        if age <= timedelta(0):
            raise ValueError("stale age must be positive")
        return self.reconcile_stale_dispatching(
            stale_before=datetime.now(UTC) - age,
            limit=limit,
        )

    def _require(self, invocation_id: uuid.UUID) -> AIProviderInvocation:
        invocation = self._repository.get_invocation(invocation_id, lock=True)
        if invocation is None:
            raise RuntimeError("Provider invocation is unavailable")
        return invocation


def _elapsed_ms(started: float, finished: float) -> int:
    return max(0, round((finished - started) * 1000))
