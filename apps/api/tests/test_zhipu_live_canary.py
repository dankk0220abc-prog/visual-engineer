import asyncio
import errno
import gzip
import inspect
import json
import logging
import os
import socket
import ssl
import subprocess
import uuid
from collections import Counter
from collections.abc import AsyncIterator, Callable, Generator, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NoReturn

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from visual_engineer_api.ai_planning import real_provider_adapters
from visual_engineer_api.ai_planning.contracts import AIPlanContract, canonical_digest
from visual_engineer_api.ai_planning.evaluator import evaluate_plan
from visual_engineer_api.ai_planning.fake_provider import DeterministicFixtureProvider
from visual_engineer_api.ai_planning.invocation_contract import InvocationStatus
from visual_engineer_api.ai_planning.provider import (
    CancellationToken,
    ProviderError,
    ProviderErrorCategory,
    ProviderTransportPhase,
)
from visual_engineer_api.ai_planning.provider_registry import ProviderId, ProviderRegistry
from visual_engineer_api.ai_planning.real_provider_adapters import ZhipuAdapter
from visual_engineer_api.ai_planning.transport_observability import (
    classify_response_body_exception,
)
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
from visual_engineer_api.models.run import ApprovalDecision, Plan, RepositorySnapshot, Run
from visual_engineer_api.models.runner import RunnerJob
from visual_engineer_api.models.task import Task
from visual_engineer_api.models.workspace import ExecutionGrant, Workspace
from visual_engineer_api.services import zhipu_live_canary as canary_service
from visual_engineer_api.services.ai_planning import AIPlanningService
from visual_engineer_api.services.live_provider_evidence import (
    LiveProviderEvidenceService,
)
from visual_engineer_api.services.zhipu_live_canary import (
    LIVE_VALIDATION_AUTHORIZATION_ENV,
    USER_SECRET_PROVISION_REQUIRED,
    ZHIPU_API_KEY_ENV,
    ZHIPU_LIVE_CANARY_POLICY,
    CanaryDatabasePreflightConfig,
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
_CANARY_MUTATION_MODELS = (
    Task,
    Run,
    RepositorySnapshot,
    AIPlanRequest,
    AIProviderInvocation,
    AIEvalResult,
)


class _EnvironmentValueAccessProbe(Mapping[str, str]):
    def __init__(
        self,
        values: Mapping[str, str],
        *,
        allowed_provider_reads: frozenset[str] = frozenset(),
    ) -> None:
        self._values = dict(values)
        self._allowed_provider_reads = allowed_provider_reads
        self.value_reads: Counter[str] = Counter()
        self.existence_checks: Counter[str] = Counter()
        self.enumeration_attempts = 0

    def _record_value_read(self, key: str) -> None:
        self.value_reads[key] += 1
        if key in _REAL_PROVIDER_ENV and key not in self._allowed_provider_reads:
            raise AssertionError(f"PROVIDER_SECRET_VALUE_READ_BEFORE_AUTHORIZATION key={key}")

    def __getitem__(self, key: str) -> str:
        self._record_value_read(key)
        return self._values[key]

    def get(self, key: str, default: Any = None) -> Any:
        self._record_value_read(key)
        return self._values.get(key, default)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            self.existence_checks[key] += 1
        return key in self._values

    def __iter__(self) -> Iterator[str]:
        self.enumeration_attempts += 1
        raise AssertionError("PROCESS_ENVIRONMENT_ENUMERATION_FORBIDDEN")

    def __len__(self) -> int:
        return len(self._values)

    def items(self) -> Any:
        self.enumeration_attempts += 1
        raise AssertionError("PROCESS_ENVIRONMENT_VALUE_ENUMERATION_FORBIDDEN")

    def values(self) -> Any:
        self.enumeration_attempts += 1
        raise AssertionError("PROCESS_ENVIRONMENT_VALUE_ENUMERATION_FORBIDDEN")

    def copy(self) -> Any:
        self.enumeration_attempts += 1
        raise AssertionError("PROCESS_ENVIRONMENT_COPY_FORBIDDEN")


@pytest.fixture(autouse=True)
def _clear_real_provider_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (*_REAL_PROVIDER_ENV, LIVE_VALIDATION_AUTHORIZATION_ENV):
        monkeypatch.delenv(name, raising=False)


def _synthetic_credential() -> str:
    return "synthetic-zhipu-live-canary-credential-only"


def _synthetic_provider_environment() -> dict[str, str]:
    return {
        name: (
            _synthetic_credential()
            if name == ZHIPU_API_KEY_ENV
            else f"synthetic-{name.lower().replace('_', '-')}-credential-only"
        )
        for name in _REAL_PROVIDER_ENV
    }


def _base_probe_environment(database_url: str) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": os.environ.get("HOME", "/tmp"),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "DATABASE_URL": database_url,
        "RUNNER_BOOTSTRAP_TOKEN": "synthetic-unrelated-runner-credential-only",
        "UNRELATED_APPLICATION_SECRET": "synthetic-unrelated-application-secret-only",
    }


def _prepare_canary_repository(root: Path) -> None:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "check-secrets.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    git_environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(root),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    commands = (
        ("init", "--initial-branch=main"),
        ("add", "--", "scripts/check-secrets.sh"),
        (
            "-c",
            "user.name=VisualEngineer Test",
            "-c",
            "user.email=visualengineer-test@example.invalid",
            "commit",
            "-m",
            "test fixture",
        ),
        ("update-ref", "refs/remotes/origin/main", "HEAD"),
    )
    for arguments in commands:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            env=git_environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if completed.returncode != 0:
            pytest.fail(
                f"isolated_repository_setup_failed command={arguments[0]}",
                pytrace=False,
            )


def _canary_mutation_counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: int(session.scalar(select(func.count()).select_from(model)) or 0)
        for model in _CANARY_MUTATION_MODELS
    }


def _assert_provider_values_absent(
    text_value: str,
    provider_values: Mapping[str, str],
) -> None:
    for name, value in provider_values.items():
        if value in text_value:
            pytest.fail(f"PROVIDER_SECRET_DISCLOSURE key={name}", pytrace=False)


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


_SECRET_NEGATIVE_FRAGMENTS = (
    "fake-api-key-material",
    "Authorization: Bearer fake-bearer-material",
    "https://provider.invalid/private?token=fake-url-token",
    'request_body={"prompt":"private-fake-prompt"}',
    'response_body={"secret":"private-fake-response"}',
)


def _raise_transport_case(kind: str, request: httpx.Request) -> NoReturn:
    sensitive = " | ".join(_SECRET_NEGATIVE_FRAGMENTS)
    if kind == "dns":
        raise httpx.ConnectError(sensitive, request=request) from socket.gaierror(
            socket.EAI_NONAME, sensitive
        )
    if kind == "connection_refused":
        raise httpx.ConnectError(sensitive, request=request) from ConnectionRefusedError(
            errno.ECONNREFUSED, sensitive
        )
    if kind == "network_unreachable":
        raise httpx.ConnectError(sensitive, request=request) from OSError(
            errno.ENETUNREACH, sensitive
        )
    if kind == "tls_certificate":
        raise httpx.ConnectError(sensitive, request=request) from ssl.SSLCertVerificationError(
            1, sensitive
        )
    if kind == "tls_handshake":
        raise httpx.ConnectError(sensitive, request=request) from ssl.SSLError(1, sensitive)
    if kind == "connect_timeout":
        raise httpx.ConnectTimeout(sensitive, request=request)
    if kind == "read_timeout":
        raise httpx.ReadTimeout(sensitive, request=request)
    if kind == "total_deadline":
        raise ProviderError(
            ProviderErrorCategory.TIMEOUT,
            "provider_total_deadline_exceeded",
            "The selected Provider exceeded its total deadline",
            safe_phase=ProviderTransportPhase.TOTAL_DEADLINE,
        )
    if kind == "write_error":
        raise httpx.WriteError(sensitive, request=request)
    if kind == "read_interruption":
        raise httpx.ReadError(sensitive, request=request)
    if kind == "remote_protocol":
        raise httpx.RemoteProtocolError(sensitive, request=request)
    if kind == "local_protocol":
        raise httpx.LocalProtocolError(sensitive, request=request)
    if kind == "protocol":
        raise httpx.ProtocolError(sensitive, request=request)
    if kind == "generic_network":
        raise httpx.NetworkError(sensitive, request=request)
    raise RuntimeError(sensitive)


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


def _install_real_gate_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    root = tmp_path / "canary-repository"
    root.mkdir()
    _prepare_canary_repository(root)
    monkeypatch.setattr(canary_service, "repository_root", lambda: root)
    monkeypatch.chdir(root)
    return root


@contextmanager
def _probe_process_environment(
    environment: _EnvironmentValueAccessProbe,
) -> Generator[None, None, None]:
    original_environment = os.environ
    os.environ = environment  # type: ignore[assignment]  # noqa: B003
    try:
        yield
    finally:
        os.environ = original_environment  # noqa: B003


def test_git_environment_builder_reads_only_fixed_safe_allowlist() -> None:
    provider_values = _synthetic_provider_environment()
    values = {
        "PATH": "/safe/bin",
        "HOME": "/safe/home",
        "TMPDIR": "/safe/tmp",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "LC_CTYPE": "UTF-8",
        "RUNNER_BOOTSTRAP_TOKEN": "synthetic-unrelated-runner-credential-only",
        "UNRELATED_APPLICATION_SECRET": "synthetic-unrelated-application-secret-only",
        **provider_values,
    }
    environment = _EnvironmentValueAccessProbe(values)

    child_environment = canary_service._secret_blind_environment(environment)

    assert canary_service._REAL_PROVIDER_SECRET_ENV_NAMES == _REAL_PROVIDER_ENV
    assert set(child_environment) == {
        *canary_service._SECRET_BLIND_ENV_ALLOWLIST,
        *canary_service._FIXED_GIT_ENVIRONMENT,
    }
    assert child_environment["PATH"] == "/safe/bin"
    assert child_environment["GIT_CONFIG_GLOBAL"] == os.devnull
    assert "RUNNER_BOOTSTRAP_TOKEN" not in child_environment
    assert "UNRELATED_APPLICATION_SECRET" not in child_environment
    assert all(name not in child_environment for name in _REAL_PROVIDER_ENV)
    assert all(environment.value_reads[name] == 0 for name in _REAL_PROVIDER_ENV)
    assert environment.enumeration_attempts == 0


@pytest.mark.parametrize("access_method", ["getitem", "get"])
def test_environment_probe_distinguishes_existence_from_provider_value_read(
    access_method: str,
) -> None:
    environment = _EnvironmentValueAccessProbe(_synthetic_provider_environment())

    assert ZHIPU_API_KEY_ENV in environment
    assert environment.value_reads[ZHIPU_API_KEY_ENV] == 0
    assert environment.existence_checks[ZHIPU_API_KEY_ENV] == 1

    with pytest.raises(
        AssertionError,
        match=(f"^PROVIDER_SECRET_VALUE_READ_BEFORE_AUTHORIZATION key={ZHIPU_API_KEY_ENV}$"),
    ):
        if access_method == "getitem":
            _ = environment[ZHIPU_API_KEY_ENV]
        else:
            _ = environment.get(ZHIPU_API_KEY_ENV)


def test_product_settings_source_never_reads_or_enumerates_owner_provider_keys() -> None:
    provider_values = _synthetic_provider_environment()
    environment = _EnvironmentValueAccessProbe(provider_values)

    with _probe_process_environment(environment):
        settings = Settings(_env_file=None)

    assert settings.api_port == 8000
    assert all(environment.value_reads[name] == 0 for name in _REAL_PROVIDER_ENV)
    assert environment.enumeration_attempts == 0
    assert "zhipu_api_key" not in Settings.model_fields


def test_database_preflight_reads_database_only_and_executes_real_gate(
    db_session: Session,
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = {**_base_probe_environment(database_url), **_synthetic_provider_environment()}
    environment = _EnvironmentValueAccessProbe(values)
    counts_before = _canary_mutation_counts(db_session)

    with _probe_process_environment(environment):
        config = canary_service.verify_database_contract()

    assert isinstance(config, CanaryDatabasePreflightConfig)
    assert environment.value_reads["DATABASE_URL"] == 1
    assert all(environment.value_reads[name] == 0 for name in _REAL_PROVIDER_ENV)
    assert environment.enumeration_attempts == 0
    assert _canary_mutation_counts(db_session) == counts_before


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
    assert adapter.request_header_overrides == {"Accept-Encoding": "identity"}
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
        assert request.headers["Accept-Encoding"] == "identity"
        assert request.headers["Content-Type"] == "application/json"
        assert "Authorization" in request.headers
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

    evidence_service = LiveProviderEvidenceService(db_session)
    summaries = evidence_service.list()
    assert evidence_service.live_verified_provider_ids() == {ProviderId.ZHIPU}
    assert len(summaries) == 1
    assert summaries[0].correlation == result.invocation_id.hex[:12]
    detail = evidence_service.detail(summaries[0].correlation)
    assert detail.task_classification == "live_canary"
    assert detail.governance.approval_status == "not_decided"
    assert detail.governance.execution_grant_status == "not_issued"
    assert detail.governance.runner_authority == "not_granted"
    assert detail.governance.review_status == "not_created"
    assert detail.governance.delivery_status == "not_created"
    assert len(detail.evaluations) == len(LIVE_CANARY_EVAL_IDS)
    assert AIPlanningService(db_session).response(ai_request.id).plan is not None
    safe_evidence = detail.model_dump_json()
    assert _synthetic_credential() not in safe_evidence
    assert "Authorization" not in safe_evidence
    assert "response_instruction" not in safe_evidence


def test_identity_request_accepts_valid_compressed_success_response(
    db_session: Session,
) -> None:
    request_count = 0
    payload = gzip.compress(json.dumps(_provider_payload()).encode())

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        assert request.headers["Accept-Encoding"] == "identity"
        return httpx.Response(
            200,
            headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
            stream=_SyntheticResponseStream([payload]),
        )

    result = asyncio.run(_invoke_with_mock(db_session, handler))
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)
    ai_request = db_session.get(AIPlanRequest, result.ai_plan_request_id)

    assert request_count == 1
    assert result.status == InvocationStatus.SUCCEEDED
    assert result.requested_model_id == ZHIPU_LIVE_CANARY_MODEL_ID
    assert result.effective_model_status == "reported"
    assert result.upstream_request_id_status == "reported"
    assert result.usage_status == "reported_complete"
    assert invocation is not None and invocation.status == "succeeded"
    assert ai_request is not None and ai_request.status == "generated"
    assert ai_request.retry_count == 0


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


@pytest.mark.parametrize(
    ("kind", "expected_category", "expected_code", "expected_phase"),
    [
        ("dns", "transport_error", "provider_dns_resolution_failed", "connect"),
        ("connection_refused", "transport_error", "provider_connection_refused", "connect"),
        ("network_unreachable", "transport_error", "provider_network_unreachable", "connect"),
        (
            "tls_certificate",
            "transport_error",
            "provider_tls_certificate_verification_failed",
            "connect",
        ),
        ("tls_handshake", "transport_error", "provider_tls_handshake_failed", "connect"),
        ("connect_timeout", "timeout", "provider_connect_timeout", "connect"),
        ("read_timeout", "timeout", "provider_read_timeout", "read"),
        (
            "total_deadline",
            "timeout",
            "provider_total_deadline_exceeded",
            "total_deadline",
        ),
        ("write_error", "transport_error", "provider_write_interrupted", "write"),
        (
            "read_interruption",
            "transport_error",
            "provider_response_read_interrupted",
            "read",
        ),
        (
            "remote_protocol",
            "transport_error",
            "provider_remote_protocol_error",
            "response",
        ),
        (
            "local_protocol",
            "transport_error",
            "provider_local_protocol_error",
            "transport",
        ),
        ("protocol", "transport_error", "provider_protocol_error", "transport"),
        ("generic_network", "transport_error", "provider_network_error", "transport"),
        ("unknown", "transport_error", "provider_transport_error", "transport"),
    ],
)
def test_safe_transport_classifier_matrix_is_durable_secret_negative_and_authority_free(
    db_session: Session,
    kind: str,
    expected_category: str,
    expected_code: str,
    expected_phase: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request_count = 0
    authority_before = _authority_counts(db_session)
    transport_records: list[logging.LogRecord] = []

    class RecordCollector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            transport_records.append(record)

    transport_logger = logging.getLogger("visual_engineer.provider_transport")
    collector = RecordCollector()
    previous_level = transport_logger.level
    previous_disabled = transport_logger.disabled
    transport_logger.disabled = False
    transport_logger.setLevel(logging.WARNING)
    transport_logger.addHandler(collector)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        _raise_transport_case(kind, request)

    try:
        result = asyncio.run(_invoke_with_mock(db_session, handler))
    finally:
        transport_logger.removeHandler(collector)
        transport_logger.setLevel(previous_level)
        transport_logger.disabled = previous_disabled
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)
    ai_request = db_session.get(AIPlanRequest, result.ai_plan_request_id)

    assert request_count == 1
    assert result.status == InvocationStatus.OUTCOME_UNKNOWN
    assert invocation is not None
    assert invocation.status == "outcome_unknown"
    assert invocation.error_category == expected_category
    assert invocation.error_code == expected_code
    assert invocation.response_digest is None
    assert ai_request is not None
    assert ai_request.status == "failed"
    assert ai_request.retry_count == 0
    assert ai_request.response_payload is None
    assert db_session.scalar(select(func.count()).select_from(AIProviderInvocation)) == 1
    assert db_session.scalar(select(func.count()).select_from(Plan)) == 0
    assert db_session.scalar(select(func.count()).select_from(AIEvalResult)) == 0
    assert _authority_counts(db_session) == authority_before

    api_serialized = AIPlanningService._invocation_response(invocation).model_dump_json()
    database_serialized = json.dumps(
        {
            "request": {
                column.name: getattr(ai_request, column.name)
                for column in AIPlanRequest.__table__.columns
            },
            "invocation": {
                column.name: getattr(invocation, column.name)
                for column in AIProviderInvocation.__table__.columns
            },
        },
        default=str,
    )
    captured = capsys.readouterr()
    assert len(transport_records) == 1
    record = transport_records[0]
    assert record.getMessage() == "provider_transport_failure"
    assert record.exc_info is None
    assert record.args == ()
    assert record.invocation_correlation == result.invocation_id.hex[:12]  # type: ignore[attr-defined]
    assert record.provider == "zhipu"  # type: ignore[attr-defined]
    assert record.error_category == expected_category  # type: ignore[attr-defined]
    assert record.error_code == expected_code  # type: ignore[attr-defined]
    assert record.safe_phase == expected_phase  # type: ignore[attr-defined]
    assert record.lifecycle == "outcome_unknown"  # type: ignore[attr-defined]
    assert isinstance(record.elapsed_ms, int)  # type: ignore[attr-defined]
    log_serialized = json.dumps(
        {
            "message": record.getMessage(),
            "invocation_correlation": record.invocation_correlation,  # type: ignore[attr-defined]
            "provider": record.provider,  # type: ignore[attr-defined]
            "error_category": record.error_category,  # type: ignore[attr-defined]
            "error_code": record.error_code,  # type: ignore[attr-defined]
            "safe_phase": record.safe_phase,  # type: ignore[attr-defined]
            "elapsed_ms": record.elapsed_ms,  # type: ignore[attr-defined]
            "lifecycle": record.lifecycle,  # type: ignore[attr-defined]
        }
    )
    safe_surfaces = (
        str(result),
        api_serialized,
        database_serialized,
        captured.out,
        captured.err,
        log_serialized,
    )
    for fragment in _SECRET_NEGATIVE_FRAGMENTS:
        assert all(fragment not in surface for surface in safe_surfaces)


class _SyntheticResponseStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes], error: Exception | None = None) -> None:
        self._chunks = chunks
        self._error = error
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk
        if self._error is not None:
            raise self._error

    async def aclose(self) -> None:
        self.closed = True


def _response_path_exception(kind: str, request: httpx.Request) -> Exception:
    sensitive = " | ".join(_SECRET_NEGATIVE_FRAGMENTS)
    if kind == "decoding":
        return httpx.DecodingError(sensitive, request=request)
    if kind == "stream_closed":
        error: Exception = httpx.StreamClosed()
        error.__cause__ = RuntimeError(sensitive)
        return error
    if kind == "stream_consumed":
        error = httpx.StreamConsumed()
        error.__cause__ = RuntimeError(sensitive)
        return error
    if kind == "response_not_read":
        error = httpx.ResponseNotRead()
        error.__cause__ = RuntimeError(sensitive)
        return error
    if kind == "request_not_read":
        error = httpx.RequestNotRead()
        error.__cause__ = RuntimeError(sensitive)
        return error
    if kind == "stream_error":
        return httpx.StreamError(sensitive)
    if kind == "local_protocol":
        return httpx.LocalProtocolError(sensitive, request=request)
    if kind == "protocol":
        return httpx.ProtocolError(sensitive, request=request)
    return RuntimeError(sensitive)


def _response_path_case(
    case: str,
    request: httpx.Request,
) -> tuple[httpx.Response, _SyntheticResponseStream | None]:
    valid = json.dumps(_provider_payload()).encode()
    if case == "A":
        return httpx.Response(200, content=valid), None
    if case == "B":
        stream = _SyntheticResponseStream([valid[:17], valid[17:71], valid[71:]])
        return httpx.Response(200, stream=stream), stream
    if case == "C":
        stream = _SyntheticResponseStream(
            [valid[:17]],
            httpx.ReadError(" | ".join(_SECRET_NEGATIVE_FRAGMENTS), request=request),
        )
        return httpx.Response(200, stream=stream), stream
    if case == "D":
        stream = _SyntheticResponseStream(
            [valid[:17]],
            httpx.RemoteProtocolError(" | ".join(_SECRET_NEGATIVE_FRAGMENTS), request=request),
        )
        return httpx.Response(200, stream=stream), stream
    if case == "E":
        return httpx.Response(200, content=b'{"choices":'), None
    if case == "F":
        return httpx.Response(200, json={"choices": []}), None
    if case == "G":
        return httpx.Response(422, json={"error": {"message": "synthetic rejection"}}), None
    if case == "H":
        return httpx.Response(
            200,
            content=b"x" * (ZHIPU_LIVE_CANARY_MAXIMUM_RESPONSE_BYTES + 1),
        ), None
    if case == "I":
        stream = _SyntheticResponseStream(
            [valid[:17]],
            RuntimeError(" | ".join(_SECRET_NEGATIVE_FRAGMENTS)),
        )
        return httpx.Response(200, stream=stream), stream
    if case == "J":
        stream = _SyntheticResponseStream(
            [valid[:17]],
            _response_path_exception("stream_closed", request),
        )
        return httpx.Response(200, stream=stream), stream
    if case == "K":
        stream = _SyntheticResponseStream([b"not-a-valid-gzip-stream"])
        return httpx.Response(
            200,
            headers={"Content-Encoding": "gzip"},
            stream=stream,
        ), stream
    if case == "L":
        return httpx.Response(409, json={"error": {"message": "synthetic conflict"}}), None
    raise AssertionError("unknown synthetic response-path case")


@pytest.mark.parametrize(
    ("case", "expected_status", "expected_category", "expected_code"),
    [
        ("A", "succeeded", None, None),
        ("B", "succeeded", None, None),
        (
            "C",
            "outcome_unknown",
            "transport_error",
            "provider_response_read_interrupted",
        ),
        (
            "D",
            "outcome_unknown",
            "transport_error",
            "provider_remote_protocol_error",
        ),
        (
            "E",
            "failed",
            "structured_output_invalid",
            "provider_structured_output_invalid",
        ),
        (
            "F",
            "failed",
            "structured_output_invalid",
            "provider_structured_output_invalid",
        ),
        ("G", "failed", "request_rejected", "provider_request_rejected"),
        ("H", "failed", "budget_exceeded", "provider_response_budget_exceeded"),
        (
            "I",
            "outcome_unknown",
            "transport_error",
            "provider_response_body_processing_error",
        ),
        (
            "J",
            "outcome_unknown",
            "transport_error",
            "provider_response_stream_state_error",
        ),
        (
            "K",
            "outcome_unknown",
            "transport_error",
            "provider_response_decoding_failed",
        ),
        ("L", "failed", "request_rejected", "provider_request_rejected"),
    ],
    ids=lambda value: f"case-{value}" if isinstance(value, str) and len(value) == 1 else None,
)
def test_zhipu_response_path_a_to_l_matrix_is_closed_and_authority_free(
    db_session: Session,
    case: str,
    expected_status: str,
    expected_category: str | None,
    expected_code: str | None,
) -> None:
    request_count = 0
    authority_before = _authority_counts(db_session)
    streams: list[_SyntheticResponseStream] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        assert request.headers["Accept-Encoding"] == "identity"
        response, stream = _response_path_case(case, request)
        if stream is not None:
            streams.append(stream)
        return response

    result = asyncio.run(_invoke_with_mock(db_session, handler))
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)
    ai_request = db_session.get(AIPlanRequest, result.ai_plan_request_id)

    assert request_count == 1
    assert invocation is not None
    assert invocation.status == expected_status
    assert invocation.error_category == expected_category
    assert invocation.error_code == expected_code
    assert invocation.attempt_number == 1
    assert ai_request is not None
    assert ai_request.retry_count == 0
    assert db_session.scalar(select(func.count()).select_from(AIProviderInvocation)) == 1
    assert _authority_counts(db_session) == authority_before
    assert all(stream.closed for stream in streams)
    if expected_status == "succeeded":
        assert ai_request.status == "generated"
        assert ai_request.response_payload is not None
    else:
        assert ai_request.status == "failed"
        assert ai_request.response_payload is None
        assert db_session.scalar(select(func.count()).select_from(Plan)) == 0
        assert db_session.scalar(select(func.count()).select_from(AIEvalResult)) == 0


@pytest.mark.parametrize(
    ("kind", "expected_code"),
    [
        ("decoding", "provider_response_decoding_failed"),
        ("stream_closed", "provider_response_stream_state_error"),
        ("stream_consumed", "provider_response_stream_state_error"),
        ("response_not_read", "provider_response_stream_state_error"),
        ("request_not_read", "provider_response_stream_state_error"),
        ("stream_error", "provider_response_stream_state_error"),
        ("runtime", "provider_response_body_processing_error"),
        ("local_protocol", "provider_local_protocol_error"),
        ("protocol", "provider_protocol_error"),
    ],
)
def test_response_body_failures_are_durable_secret_negative_and_safe_logged(
    db_session: Session,
    kind: str,
    expected_code: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    request_count = 0
    authority_before = _authority_counts(db_session)
    transport_records: list[logging.LogRecord] = []

    class RecordCollector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            transport_records.append(record)

    transport_logger = logging.getLogger("visual_engineer.provider_transport")
    collector = RecordCollector()
    previous_level = transport_logger.level
    previous_disabled = transport_logger.disabled
    transport_logger.disabled = False
    transport_logger.setLevel(logging.WARNING)
    transport_logger.addHandler(collector)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        stream = _SyntheticResponseStream(
            [b'{"partial":'],
            _response_path_exception(kind, request),
        )
        return httpx.Response(200, stream=stream)

    try:
        result = asyncio.run(_invoke_with_mock(db_session, handler))
    finally:
        transport_logger.removeHandler(collector)
        transport_logger.setLevel(previous_level)
        transport_logger.disabled = previous_disabled
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)
    ai_request = db_session.get(AIPlanRequest, result.ai_plan_request_id)

    assert request_count == 1
    assert result.status == InvocationStatus.OUTCOME_UNKNOWN
    assert invocation is not None
    assert invocation.status == "outcome_unknown"
    assert invocation.error_category == "transport_error"
    assert invocation.error_code == expected_code
    assert invocation.attempt_number == 1
    assert ai_request is not None
    assert ai_request.retry_count == 0
    assert ai_request.response_payload is None
    assert db_session.scalar(select(func.count()).select_from(AIProviderInvocation)) == 1
    assert _authority_counts(db_session) == authority_before

    assert len(transport_records) == 1
    record = transport_records[0]
    assert record.getMessage() == "provider_transport_failure"
    assert record.exc_info is None
    assert record.error_code == expected_code  # type: ignore[attr-defined]
    assert record.safe_phase == "response"  # type: ignore[attr-defined]
    api_serialized = AIPlanningService._invocation_response(invocation).model_dump_json()
    database_serialized = json.dumps(
        {
            "request": {
                column.name: getattr(ai_request, column.name)
                for column in AIPlanRequest.__table__.columns
            },
            "invocation": {
                column.name: getattr(invocation, column.name)
                for column in AIProviderInvocation.__table__.columns
            },
        },
        default=str,
    )
    captured = capsys.readouterr()
    log_serialized = json.dumps(
        {
            "message": record.getMessage(),
            "invocation_correlation": record.invocation_correlation,  # type: ignore[attr-defined]
            "provider": record.provider,  # type: ignore[attr-defined]
            "error_category": record.error_category,  # type: ignore[attr-defined]
            "error_code": record.error_code,  # type: ignore[attr-defined]
            "safe_phase": record.safe_phase,  # type: ignore[attr-defined]
            "elapsed_ms": record.elapsed_ms,  # type: ignore[attr-defined]
            "lifecycle": record.lifecycle,  # type: ignore[attr-defined]
        }
    )
    for fragment in _SECRET_NEGATIVE_FRAGMENTS:
        assert fragment not in str(result)
        assert fragment not in api_serialized
        assert fragment not in database_serialized
        assert fragment not in captured.out
        assert fragment not in captured.err
        assert fragment not in log_serialized


def test_response_stage_classification_codes_are_unique_and_never_generic_transport() -> None:
    request = httpx.Request("GET", "https://example.invalid")
    classifications = {
        "decode": classify_response_body_exception(
            httpx.DecodingError("synthetic", request=request)
        ).code,
        "stream_state": classify_response_body_exception(httpx.StreamClosed()).code,
        "body_processing": classify_response_body_exception(RuntimeError("synthetic")).code,
        "protocol": classify_response_body_exception(
            httpx.RemoteProtocolError("synthetic", request=request)
        ).code,
    }
    with pytest.raises(ProviderError) as caught:
        ZhipuAdapter._raise_for_status(httpx.Response(409, request=request))
    classifications["http_rejection"] = caught.value.code

    assert classifications == {
        "decode": "provider_response_decoding_failed",
        "stream_state": "provider_response_stream_state_error",
        "body_processing": "provider_response_body_processing_error",
        "protocol": "provider_remote_protocol_error",
        "http_rejection": "provider_request_rejected",
    }
    assert len(set(classifications.values())) == len(classifications)
    assert "provider_transport_error" not in classifications.values()


@pytest.mark.parametrize(
    ("status_code", "expected_category", "expected_code"),
    [
        (400, "request_rejected", "provider_request_rejected"),
        (408, "request_rejected", "provider_request_rejected"),
        (409, "request_rejected", "provider_request_rejected"),
        (429, "rate_limited", "provider_rate_limited"),
        (500, "upstream_server_error", "provider_upstream_server_error"),
        (503, "upstream_server_error", "provider_upstream_server_error"),
    ],
)
def test_representative_non_success_http_responses_are_definite_and_authority_free(
    db_session: Session,
    status_code: int,
    expected_category: str,
    expected_code: str,
) -> None:
    request_count = 0
    authority_before = _authority_counts(db_session)

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(status_code, text=f"raw {_synthetic_credential()}")

    result = asyncio.run(_invoke_with_mock(db_session, handler))
    invocation = db_session.get(AIProviderInvocation, result.invocation_id)
    ai_request = db_session.get(AIPlanRequest, result.ai_plan_request_id)

    assert request_count == 1
    assert result.status == InvocationStatus.FAILED
    assert invocation is not None
    assert invocation.status == "failed"
    assert invocation.error_category == expected_category
    assert invocation.error_code == expected_code
    assert invocation.provider_id == "zhipu"
    assert invocation.attempt_number == 1
    assert invocation.response_digest is None
    assert ai_request is not None
    assert ai_request.status == "failed"
    assert ai_request.retry_count == 0
    assert ai_request.response_payload is None
    assert db_session.scalar(select(func.count()).select_from(AIProviderInvocation)) == 1
    assert db_session.scalar(select(func.count()).select_from(Plan)) == 0
    assert db_session.scalar(select(func.count()).select_from(AIEvalResult)) == 0
    assert _authority_counts(db_session) == authority_before
    assert _synthetic_credential() not in json.dumps(
        {
            "error_category": invocation.error_category,
            "error_code": invocation.error_code,
        }
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
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    provider_values = _synthetic_provider_environment()
    values = {**_base_probe_environment(database_url), **provider_values}
    environment = _EnvironmentValueAccessProbe(values)
    counts_before = _canary_mutation_counts(db_session)
    production_client_count = 0

    def forbidden_production_client() -> httpx.AsyncClient:
        nonlocal production_client_count
        production_client_count += 1
        raise AssertionError("HTTP_REQUEST_BEFORE_AUTHORIZATION")

    _install_real_gate_context(monkeypatch, tmp_path)
    monkeypatch.setattr(
        real_provider_adapters,
        "_create_production_client",
        forbidden_production_client,
    )

    with _probe_process_environment(environment):
        result = canary_cli.main(["preflight"])
    output = capsys.readouterr()

    assert result == 0
    assert output.out.splitlines() == [
        USER_SECRET_PROVISION_REQUIRED,
        f"secret_variable={ZHIPU_API_KEY_ENV}",
    ]
    assert all(environment.value_reads[name] == 0 for name in _REAL_PROVIDER_ENV)
    assert environment.enumeration_attempts == 0
    assert production_client_count == 0
    assert _canary_mutation_counts(db_session) == counts_before
    _assert_provider_values_absent(output.out + output.err, provider_values)


@pytest.mark.parametrize("authorization", [None, "0"], ids=["missing", "false"])
def test_authorization_fails_before_secret_read(
    db_session: Session,
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    authorization: str | None,
) -> None:
    provider_values = _synthetic_provider_environment()
    values = {**_base_probe_environment(database_url), **provider_values}
    if authorization is not None:
        values[LIVE_VALIDATION_AUTHORIZATION_ENV] = authorization
    environment = _EnvironmentValueAccessProbe(values)
    counts_before = _canary_mutation_counts(db_session)
    production_client_count = 0

    def forbidden_production_client() -> httpx.AsyncClient:
        nonlocal production_client_count
        production_client_count += 1
        raise AssertionError("HTTP_REQUEST_BEFORE_AUTHORIZATION")

    _install_real_gate_context(monkeypatch, tmp_path)
    monkeypatch.setattr(
        real_provider_adapters,
        "_create_production_client",
        forbidden_production_client,
    )

    with _probe_process_environment(environment):
        result = canary_cli.main(["run"])
    output = capsys.readouterr()

    assert result == 1
    assert "LIVE_VALIDATION_AUTHORIZATION_REQUIRED" in output.err
    assert all(environment.value_reads[name] == 0 for name in _REAL_PROVIDER_ENV)
    assert environment.enumeration_attempts == 0
    assert production_client_count == 0
    assert _canary_mutation_counts(db_session) == counts_before
    _assert_provider_values_absent(output.out + output.err, provider_values)


def test_authorized_missing_key_stops_before_adapter_or_database_write(
    db_session: Session,
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    provider_values = _synthetic_provider_environment()
    provider_values.pop(ZHIPU_API_KEY_ENV)
    values = {
        **_base_probe_environment(database_url),
        **provider_values,
        LIVE_VALIDATION_AUTHORIZATION_ENV: "1",
    }
    environment = _EnvironmentValueAccessProbe(
        values,
        allowed_provider_reads=frozenset({ZHIPU_API_KEY_ENV}),
    )
    counts_before = _canary_mutation_counts(db_session)
    production_client_count = 0

    def forbidden_production_client() -> httpx.AsyncClient:
        nonlocal production_client_count
        production_client_count += 1
        raise AssertionError("HTTP_REQUEST_WITHOUT_PROVIDER_SECRET")

    _install_real_gate_context(monkeypatch, tmp_path)
    monkeypatch.setattr(
        real_provider_adapters,
        "_create_production_client",
        forbidden_production_client,
    )

    with _probe_process_environment(environment):
        result = canary_cli.main(["run"])
    output = capsys.readouterr()

    assert result == 1
    assert USER_SECRET_PROVISION_REQUIRED in output.out
    assert environment.value_reads[ZHIPU_API_KEY_ENV] == 1
    assert all(
        environment.value_reads[name] == 0
        for name in _REAL_PROVIDER_ENV
        if name != ZHIPU_API_KEY_ENV
    )
    assert environment.enumeration_attempts == 0
    assert production_client_count == 0
    assert _canary_mutation_counts(db_session) == counts_before
    _assert_provider_values_absent(output.out + output.err, provider_values)


def test_production_factory_enforces_gate_order_before_secret_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    database_config = CanaryDatabasePreflightConfig()
    monkeypatch.setattr(
        canary_service,
        "verify_fixed_scenario_contract",
        lambda: events.append("scenario"),
    )
    monkeypatch.setattr(
        canary_service, "verify_repository_contract", lambda: events.append("repository")
    )

    def database_gate() -> CanaryDatabasePreflightConfig:
        events.append("database")
        return database_config

    monkeypatch.setattr(canary_service, "verify_database_contract", database_gate)
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

    def stop_at_secret() -> SecretStr:
        events.append("secret")
        raise UserSecretProvisionRequired()

    monkeypatch.setattr(canary_service, "_load_authorized_zhipu_secret", stop_at_secret)

    with pytest.raises(UserSecretProvisionRequired):
        with canary_service.production_zhipu_live_canary_service():
            pass

    assert events == ["scenario", "repository", "database", "safety", "authorization", "secret"]


def test_authorized_synthetic_key_runs_full_production_path_once(
    db_session: Session,
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    provider_values = _synthetic_provider_environment()
    values = {
        **_base_probe_environment(database_url),
        **provider_values,
        LIVE_VALIDATION_AUTHORIZATION_ENV: "1",
    }
    environment = _EnvironmentValueAccessProbe(
        values,
        allowed_provider_reads=frozenset({ZHIPU_API_KEY_ENV}),
    )
    mutation_counts_before = _canary_mutation_counts(db_session)
    authority_before = _authority_counts(db_session)
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        assert request.url == ZHIPU_LIVE_CANARY_ENDPOINT
        assert "Authorization" in request.headers
        return httpx.Response(200, json=_provider_payload())

    def mock_production_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            trust_env=False,
        )

    _install_real_gate_context(monkeypatch, tmp_path)
    monkeypatch.setattr(
        real_provider_adapters,
        "_create_production_client",
        mock_production_client,
    )

    with _probe_process_environment(environment):
        result = canary_cli.main(["run"])
    output = capsys.readouterr()

    db_session.expire_all()
    invocation = db_session.scalar(
        select(AIProviderInvocation).order_by(AIProviderInvocation.created_at.desc()).limit(1)
    )
    ai_request = db_session.scalar(
        select(AIPlanRequest).order_by(AIPlanRequest.created_at.desc()).limit(1)
    )
    mutation_counts_after = _canary_mutation_counts(db_session)
    mutation_deltas = {
        name: mutation_counts_after[name] - count for name, count in mutation_counts_before.items()
    }

    assert result == 0
    assert request_count == 1
    assert environment.value_reads[ZHIPU_API_KEY_ENV] == 1
    assert all(
        environment.value_reads[name] == 0
        for name in _REAL_PROVIDER_ENV
        if name != ZHIPU_API_KEY_ENV
    )
    assert environment.enumeration_attempts == 0
    assert invocation is not None and invocation.status == "succeeded"
    assert ai_request is not None and ai_request.status == "generated"
    assert ai_request.response_payload is not None
    AIPlanContract.model_validate(ai_request.response_payload)
    assert mutation_deltas == {
        "tasks": 1,
        "runs": 1,
        "repository_snapshots": 1,
        "ai_plan_requests": 1,
        "ai_provider_invocations": 1,
        "ai_eval_results": len(LIVE_CANARY_EVAL_IDS),
    }
    assert _authority_counts(db_session) == authority_before
    assert "LIVE ZHIPU CANARY — ONE EXTERNAL REQUEST MAY BE SENT" in output.out
    _assert_provider_values_absent(output.out + output.err, provider_values)


def test_production_factory_has_no_injection_parameters() -> None:
    assert inspect.signature(canary_service.production_zhipu_live_canary_service).parameters == {}
    forbidden_settings = {"transport", "endpoint", "model", "headers", "maximum_output_tokens"}
    assert forbidden_settings.isdisjoint(Settings.model_fields)

    with pytest.raises(TypeError):
        with canary_service.production_zhipu_live_canary_service(  # type: ignore[call-arg]
            httpx.MockTransport(lambda _: httpx.Response(200))
        ):
            pass


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
        runner_bootstrap_token="",
    )
    combined = output.out + output.err + repr(settings)
    assert synthetic not in combined
    assert "zhipu_api_key" not in Settings.model_fields
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
