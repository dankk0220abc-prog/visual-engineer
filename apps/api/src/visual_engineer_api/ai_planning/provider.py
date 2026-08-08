import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from visual_engineer_api.ai_planning.contracts import (
    AIPlanGenerationRequest,
    ProviderCapabilityMetadata,
)


class ProviderErrorCategory(StrEnum):
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"
    PROVIDER_DISABLED = "provider_disabled"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    MODEL_UNAVAILABLE = "model_unavailable"
    UPSTREAM_SERVER_ERROR = "upstream_server_error"
    REQUEST_REJECTED = "request_rejected"
    BUDGET_EXCEEDED = "budget_exceeded"
    TRANSPORT_ERROR = "transport_error"
    STRUCTURED_OUTPUT_INVALID = "structured_output_invalid"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"
    POLICY_DENIED = "policy_denied"
    INTERNAL = "internal"


class ProviderError(Exception):
    def __init__(
        self,
        category: ProviderErrorCategory,
        code: str,
        public_message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(public_message)
        self.category = category
        self.code = code
        self.public_message = public_message
        self.retryable = retryable


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise ProviderError(
                ProviderErrorCategory.CANCELLED,
                "provider_cancelled",
                "Provider generation was cancelled",
            )


class ProviderUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    cost_estimate_microunits: int = Field(ge=0)
    cost_basis: Literal["synthetic_not_billable"]

    @model_validator(mode="after")
    def validate_total_and_cost(self) -> "ProviderUsage":
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total tokens must equal input plus output tokens")
        if self.cost_estimate_microunits != 0:
            raise ValueError("fixture Provider cost must remain zero")
        return self


class ProviderInvocationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    response_payload: dict[str, Any]
    usage: ProviderUsage
    latency_ms: float = Field(ge=0)


class PlanningProvider(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilityMetadata: ...

    @abstractmethod
    def generate(
        self, request: AIPlanGenerationRequest, cancellation: CancellationToken
    ) -> ProviderInvocationResult: ...


@dataclass(frozen=True)
class ProviderAttempt:
    attempt_number: int
    result: ProviderInvocationResult | None
    error: ProviderError | None
    observed_latency_ms: float


@dataclass(frozen=True)
class ProviderRun:
    attempts: list[ProviderAttempt]
    result: ProviderInvocationResult | None
    error: ProviderError | None


def invoke_provider(
    provider: PlanningProvider,
    request: AIPlanGenerationRequest,
    cancellation: CancellationToken,
    *,
    timeout_seconds: float,
    max_attempts: int,
) -> ProviderRun:
    attempts: list[ProviderAttempt] = []
    final_error: ProviderError | None = None
    for attempt_number in range(1, max_attempts + 1):
        try:
            cancellation.raise_if_cancelled()
        except ProviderError as cancellation_error:
            attempts.append(
                ProviderAttempt(
                    attempt_number=attempt_number,
                    result=None,
                    error=cancellation_error,
                    observed_latency_ms=0.0,
                )
            )
            return ProviderRun(attempts=attempts, result=None, error=cancellation_error)
        started = time.perf_counter()
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai-plan-provider")
        future = executor.submit(provider.generate, request, cancellation)
        try:
            result = future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            cancellation.cancel()
            future.cancel()
            error = ProviderError(
                ProviderErrorCategory.TIMEOUT,
                "provider_timeout",
                "Provider generation exceeded its time limit",
                retryable=True,
            )
        except ProviderError as exc:
            error = exc
        except Exception:
            error = ProviderError(
                ProviderErrorCategory.INTERNAL,
                "provider_internal_error",
                "Provider generation failed safely",
            )
        else:
            attempts.append(
                ProviderAttempt(
                    attempt_number=attempt_number,
                    result=result,
                    error=None,
                    observed_latency_ms=round((time.perf_counter() - started) * 1000, 3),
                )
            )
            return ProviderRun(attempts=attempts, result=result, error=None)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        final_error = error
        attempts.append(
            ProviderAttempt(
                attempt_number=attempt_number,
                result=None,
                error=error,
                observed_latency_ms=round((time.perf_counter() - started) * 1000, 3),
            )
        )
        if not error.retryable or attempt_number >= max_attempts or cancellation.cancelled:
            break
    return ProviderRun(attempts=attempts, result=None, error=final_error)
