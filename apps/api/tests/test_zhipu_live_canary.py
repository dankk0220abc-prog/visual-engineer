import asyncio
import inspect
import json
import os
import subprocess
import uuid
from collections import Counter
from collections.abc import Callable, Generator, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

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
from visual_engineer_api.models.run import ApprovalDecision, Plan, RepositorySnapshot, Run
from visual_engineer_api.models.runner import RunnerJob
from visual_engineer_api.models.task import Task
from visual_engineer_api.models.workspace import ExecutionGrant, Workspace
from visual_engineer_api.services import zhipu_live_canary as canary_service
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
