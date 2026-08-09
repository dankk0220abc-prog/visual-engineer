import asyncio
import os
import shutil
import subprocess
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from visual_engineer_api.ai_planning.contracts import (
    AIPlanContract,
    canonical_digest,
    canonical_json,
)
from visual_engineer_api.ai_planning.invocation_contract import (
    InvocationClassification,
    InvocationStatus,
    InvocationUsageStatus,
    ReportedValueStatus,
    normalized_response_digest,
    upstream_request_fingerprint,
)
from visual_engineer_api.ai_planning.prompt_registry import redact_structured_payload
from visual_engineer_api.ai_planning.provider import (
    CancellationToken,
    ProviderError,
    ProviderErrorCategory,
)
from visual_engineer_api.ai_planning.provider_registry import ProviderId, ProviderRegistry
from visual_engineer_api.ai_planning.real_provider_adapters import (
    REAL_PROVIDER_ADAPTERS,
    ProviderAdapterResult,
    ProviderCallPolicy,
    ZhipuAdapter,
)
from visual_engineer_api.ai_planning.zhipu_live_canary import (
    LIVE_CANARY_EVALUATOR_VERSION,
    ZHIPU_LIVE_CANARY_ENDPOINT,
    ZHIPU_LIVE_CANARY_MAXIMUM_OUTPUT_TOKENS,
    ZHIPU_LIVE_CANARY_MAXIMUM_RESPONSE_BYTES,
    ZHIPU_LIVE_CANARY_MODEL_ID,
    ZHIPU_LIVE_CANARY_PROMPT_DIGEST,
    ZHIPU_LIVE_CANARY_PROMPT_TEMPLATE_ID,
    ZHIPU_LIVE_CANARY_PROMPT_VERSION,
    ZHIPU_LIVE_CANARY_PROVIDER_METADATA,
    ZHIPU_LIVE_CANARY_SCENARIO_ID,
    ZHIPU_LIVE_CANARY_SCENARIO_VERSION,
    ZHIPU_LIVE_CANARY_SNAPSHOT_FINGERPRINT,
    ZHIPU_LIVE_CANARY_SOURCE_REVISION,
    ZhipuLiveCanaryDispatch,
    ZhipuLiveCanaryPlanContent,
    build_zhipu_live_canary_dispatch,
    build_zhipu_live_canary_plan,
    evaluate_zhipu_live_canary_plan,
)
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
from visual_engineer_api.services.provider_invocations import (
    ProviderInvocationLifecycle,
    reported_usage_status,
)

EXPECTED_ALEMBIC_HEAD = "20260809_0016"
LIVE_VALIDATION_AUTHORIZATION_ENV = "VISUALENGINEER_LIVE_VALIDATION_AUTHORIZED"
ZHIPU_API_KEY_ENV = "ZHIPU_API_KEY"
LIVE_CANARY_WARNING = "LIVE ZHIPU CANARY — ONE EXTERNAL REQUEST MAY BE SENT"
USER_SECRET_PROVISION_REQUIRED = "USER_SECRET_PROVISION_REQUIRED"

ZHIPU_LIVE_CANARY_POLICY = ProviderCallPolicy(
    maximum_output_tokens=ZHIPU_LIVE_CANARY_MAXIMUM_OUTPUT_TOKENS,
    maximum_response_bytes=ZHIPU_LIVE_CANARY_MAXIMUM_RESPONSE_BYTES,
    maximum_retries=0,
    concurrency_limit=1,
)

_PROVIDER_SECRET_ENV_NAMES = (
    "ZHIPU_API_KEY",
    "QWEN_API_KEY",
    "DEEPSEEK_API_KEY",
    "DOUBAO_API_KEY",
    "KIMI_API_KEY",
    "RUNNER_BOOTSTRAP_TOKEN",
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


class CanaryDatabaseSettings(BaseSettings):
    """Secret-blind settings used before live-validation authorization."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    database_url: str = (
        "postgresql+psycopg://visualengineer:visualengineer-local@localhost:5432/visualengineer"
    )


class ZhipuLiveCanaryError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class LiveValidationAuthorizationRequired(ZhipuLiveCanaryError):
    def __init__(self) -> None:
        super().__init__("live_validation_authorization_required")


class UserSecretProvisionRequired(ZhipuLiveCanaryError):
    def __init__(self) -> None:
        super().__init__("user_secret_provision_required")


@dataclass(frozen=True)
class ZhipuLiveCanaryResult:
    ai_plan_request_id: uuid.UUID
    invocation_id: uuid.UUID
    status: InvocationStatus
    provider_id: str
    requested_model_id: str
    effective_model_status: str
    upstream_request_id_status: str
    upstream_request_fingerprint: str | None
    usage_status: str
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    queue_wait_ms: int | None
    provider_elapsed_ms: int | None
    client_total_elapsed_ms: int | None
    billing_status: str
    error_code: str | None


def repository_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _secret_blind_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in _PROVIDER_SECRET_ENV_NAMES:
        environment.pop(name, None)
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "never",
        }
    )
    return environment


def _git(root: Path, *arguments: str, allow_absent: bool = False) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        env=_secret_blind_environment(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        if allow_absent and completed.returncode == 1:
            return ""
        raise ZhipuLiveCanaryError("repository_contract_unavailable")
    return completed.stdout.strip()


def verify_repository_contract() -> None:
    root = repository_root()
    if Path.cwd().resolve() != root or _git(root, "rev-parse", "--show-toplevel") != str(root):
        raise ZhipuLiveCanaryError("repository_root_mismatch")
    if _git(root, "symbolic-ref", "--short", "HEAD") != "main":
        raise ZhipuLiveCanaryError("repository_main_required")
    head = _git(root, "rev-parse", "HEAD")
    if head != _git(root, "rev-parse", "main") or head != _git(root, "rev-parse", "origin/main"):
        raise ZhipuLiveCanaryError("repository_main_drift")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ZhipuLiveCanaryError("repository_worktree_not_clean")
    if _git(root, "show-ref", "--verify", "refs/stash", allow_absent=True):
        raise ZhipuLiveCanaryError("repository_stash_present")
    git_dir = Path(_git(root, "rev-parse", "--absolute-git-dir"))
    markers = (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "BISECT_START",
        "rebase-apply",
        "rebase-merge",
        "sequencer",
    )
    if any((git_dir / marker).exists() for marker in markers):
        raise ZhipuLiveCanaryError("repository_git_operation_active")


def _database_engine() -> Engine:
    settings = CanaryDatabaseSettings()
    url = make_url(settings.database_url)
    if url.drivername != "postgresql+psycopg" or url.host not in {
        None,
        "localhost",
        "127.0.0.1",
        "::1",
        "db",
    }:
        raise ZhipuLiveCanaryError("local_database_required")
    return create_engine(settings.database_url, pool_pre_ping=True)


def verify_database_contract() -> None:
    engine = _database_engine()
    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT 1")) != 1:
                raise ZhipuLiveCanaryError("database_health_failed")
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != EXPECTED_ALEMBIC_HEAD:
                raise ZhipuLiveCanaryError("database_migration_head_mismatch")
    except ZhipuLiveCanaryError:
        raise
    except Exception:
        raise ZhipuLiveCanaryError("database_contract_unavailable") from None
    finally:
        engine.dispose()


def verify_provider_disabled_contract() -> None:
    if not ProviderRegistry.is_enabled(ProviderId.DETERMINISTIC_FIXTURE):
        raise ZhipuLiveCanaryError("fixture_provider_not_enabled")
    if any(
        ProviderRegistry.is_enabled(provider_id)
        for provider_id in (
            ProviderId.ZHIPU,
            ProviderId.QWEN,
            ProviderId.DEEPSEEK,
            ProviderId.DOUBAO,
            ProviderId.KIMI,
        )
    ):
        raise ZhipuLiveCanaryError("real_provider_enablement_drift")


def verify_pre_live_safety_contract() -> None:
    verify_provider_disabled_contract()
    dispatch = build_zhipu_live_canary_dispatch()
    if (
        dispatch.scenario_id != ZHIPU_LIVE_CANARY_SCENARIO_ID
        or dispatch.scenario_version != ZHIPU_LIVE_CANARY_SCENARIO_VERSION
    ):
        raise ZhipuLiveCanaryError("canary_scenario_drift")
    if REAL_PROVIDER_ADAPTERS.get(ProviderId.ZHIPU) is not ZhipuAdapter:
        raise ZhipuLiveCanaryError("zhipu_production_adapter_missing")
    if (
        ZhipuAdapter.endpoint != ZHIPU_LIVE_CANARY_ENDPOINT
        or ZhipuAdapter.model_id != ZHIPU_LIVE_CANARY_MODEL_ID
        or ZhipuAdapter.request_overrides != {"thinking": {"type": "disabled"}}
    ):
        raise ZhipuLiveCanaryError("zhipu_production_contract_drift")
    if "zhipu_api_key" not in Settings.model_fields:
        raise ZhipuLiveCanaryError("zhipu_secret_setting_missing")
    scanner = repository_root() / "scripts" / "check-secrets.sh"
    if shutil.which("rg") is None or not scanner.is_file():
        raise ZhipuLiveCanaryError("secret_scanner_unavailable")
    if LIVE_VALIDATION_AUTHORIZATION_ENV != "VISUALENGINEER_LIVE_VALIDATION_AUTHORIZED":
        raise ZhipuLiveCanaryError("live_authorization_contract_drift")


def run_secret_blind_preflight() -> None:
    verify_repository_contract()
    verify_database_contract()
    verify_pre_live_safety_contract()


def require_live_validation_authorization() -> None:
    if os.environ.get(LIVE_VALIDATION_AUTHORIZATION_ENV) != "1":
        raise LiveValidationAuthorizationRequired()


def _load_authorized_runtime_settings() -> Settings:
    """Read only the Zhipu credential, after the caller has passed every safe gate."""
    database_url = CanaryDatabaseSettings().database_url
    zhipu_value = os.environ.get(ZHIPU_API_KEY_ENV, "")
    settings = Settings.model_validate(
        {
            "database_url": database_url,
            "zhipu_api_key": SecretStr(zhipu_value),
            "qwen_api_key": SecretStr(""),
            "deepseek_api_key": SecretStr(""),
            "doubao_api_key": SecretStr(""),
            "kimi_api_key": SecretStr(""),
            "runner_bootstrap_token": SecretStr(""),
        }
    )
    if not settings.zhipu_api_key.get_secret_value().strip():
        raise UserSecretProvisionRequired()
    return settings


@contextmanager
def production_zhipu_live_canary_service() -> Generator["ZhipuLiveCanaryService", None, None]:
    verify_repository_contract()
    verify_database_contract()
    require_live_validation_authorization()
    verify_pre_live_safety_contract()
    settings = _load_authorized_runtime_settings()
    adapter = ZhipuAdapter(settings.zhipu_api_key)
    if adapter.uses_injected_mock_transport:
        raise ZhipuLiveCanaryError("production_transport_injection_rejected")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            yield ZhipuLiveCanaryService(session, adapter=adapter)
    finally:
        engine.dispose()


class ZhipuLiveCanaryService:
    def __init__(
        self,
        session: Session,
        *,
        adapter: ZhipuAdapter,
        _allow_mock_transport: bool = False,
    ) -> None:
        self._session = session
        self._adapter = adapter
        self._allow_mock_transport = _allow_mock_transport

    async def run(
        self,
        *,
        _test_cancellation: CancellationToken | None = None,
    ) -> ZhipuLiveCanaryResult:
        self._validate_fixed_adapter()
        authority_before = self._authority_counts()
        dispatch = build_zhipu_live_canary_dispatch()
        ai_request = self._create_ai_plan_request(dispatch)
        lifecycle = ProviderInvocationLifecycle(self._session)
        timing = lifecycle.prepare(
            ai_plan_request_id=ai_request.id,
            attempt_number=1,
            classification=InvocationClassification.LIVE,
            provider_id=ProviderId.ZHIPU.value,
            provider_metadata=ZHIPU_LIVE_CANARY_PROVIDER_METADATA.model_dump(mode="json"),
            adapter_version=self._adapter.adapter_version,
            requested_model_id=ZHIPU_LIVE_CANARY_MODEL_ID,
            request_digest=canonical_digest(
                self._adapter.request_body(dispatch, ZHIPU_LIVE_CANARY_POLICY)
            ),
            redactions=[],
        )
        cancellation = _test_cancellation or CancellationToken()
        try:
            provider_result = await self._adapter.invoke(
                dispatch,
                cancellation,
                policy=ZHIPU_LIVE_CANARY_POLICY,
                on_dispatch_ready=lambda: lifecycle.mark_dispatching(timing),
            )
        except asyncio.CancelledError:
            cancelled = ProviderError(
                ProviderErrorCategory.CANCELLED,
                "provider_cancelled",
                "Provider generation was cancelled",
            )
            status = lifecycle.fail(timing, cancelled)
            self._mark_request_failed(ai_request.id, cancelled)
            self._assert_authority_unchanged(authority_before)
            return self._result(ai_request.id, timing.invocation_id, status)
        except ProviderError as error:
            status = lifecycle.fail(timing, error)
            self._mark_request_failed(ai_request.id, error)
            self._assert_authority_unchanged(authority_before)
            return self._result(ai_request.id, timing.invocation_id, status)

        try:
            plan = self._validated_plan(dispatch, provider_result)
        except (ValidationError, ValueError) as error:
            del error
            invalid = ProviderError(
                ProviderErrorCategory.INVALID_RESPONSE,
                "provider_schema_invalid",
                "Provider response did not match the live canary Plan contract",
            )
            status = lifecycle.fail(timing, invalid, force_definite=True)
            self._mark_request_failed(ai_request.id, invalid)
            self._assert_authority_unchanged(authority_before)
            return self._result(ai_request.id, timing.invocation_id, status)

        usage_status = (
            InvocationUsageStatus.REPORTED_INVALID
            if provider_result.usage.reported_invalid
            else reported_usage_status(
                provider_result.usage.input_tokens,
                provider_result.usage.output_tokens,
                provider_result.usage.total_tokens,
            )
        )
        effective_status = (
            ReportedValueStatus.REPORTED
            if provider_result.model_id is not None
            else ReportedValueStatus.UNAVAILABLE
        )
        upstream_status = (
            ReportedValueStatus.REPORTED
            if provider_result.provider_request_id is not None
            else ReportedValueStatus.UNAVAILABLE
        )
        response_payload = plan.model_dump(mode="json")
        response_digest = normalized_response_digest(
            plan_payload=response_payload,
            effective_model_status=effective_status,
            effective_model_id=provider_result.model_id,
            upstream_request_id_status=upstream_status,
            upstream_request_id=provider_result.provider_request_id,
            usage_status=usage_status,
            input_tokens=provider_result.usage.input_tokens,
            output_tokens=provider_result.usage.output_tokens,
            total_tokens=provider_result.usage.total_tokens,
        )
        lifecycle.succeed(
            timing,
            response_digest=response_digest,
            effective_model_status=effective_status,
            effective_model_id=provider_result.model_id,
            upstream_request_id_status=upstream_status,
            upstream_request_id=provider_result.provider_request_id,
            usage_status=usage_status,
            input_tokens=provider_result.usage.input_tokens,
            output_tokens=provider_result.usage.output_tokens,
            total_tokens=provider_result.usage.total_tokens,
        )
        self._persist_validated_plan(ai_request.id, dispatch, plan)
        self._assert_authority_unchanged(authority_before)
        return self._result(ai_request.id, timing.invocation_id, InvocationStatus.SUCCEEDED)

    def _validate_fixed_adapter(self) -> None:
        if (
            type(self._adapter) is not ZhipuAdapter
            or self._adapter.provider_id != ProviderId.ZHIPU
            or self._adapter.model_id != ZHIPU_LIVE_CANARY_MODEL_ID
            or self._adapter.endpoint != ZHIPU_LIVE_CANARY_ENDPOINT
        ):
            raise ZhipuLiveCanaryError("zhipu_fixed_adapter_required")
        if self._adapter.uses_injected_mock_transport != self._allow_mock_transport:
            raise ZhipuLiveCanaryError("canary_transport_boundary_mismatch")

    def _create_ai_plan_request(self, dispatch: ZhipuLiveCanaryDispatch) -> AIPlanRequest:
        operation_id = uuid.uuid4()
        task_values = {
            "title": "Zhipu governed live canary",
            "objective": dispatch.requirement,
            "repository_kind": "github",
            "repository_display_name": "Synthetic public live-canary context",
            "repository_locator": "https://example.invalid/visualengineer/zhipu-live-canary-v1",
        }
        task = Task(
            **task_values,
            status="draft",
            version=1,
            idempotency_key=f"zhipu-live-canary-task-{operation_id}",
            idempotency_request_hash=canonical_digest(task_values),
        )
        self._session.add(task)
        self._session.flush()
        run = Run(
            task_id=task.id,
            status="snapshot_ready",
            permission_level="read_only",
            snapshot_mode="git_head",
            version=1,
            trace_id=uuid.uuid4(),
            idempotency_key=f"zhipu-live-canary-run-{operation_id}",
            idempotency_request_hash=canonical_digest(
                {"scenario_id": dispatch.scenario_id, "operation_id": str(operation_id)}
            ),
        )
        self._session.add(run)
        self._session.flush()
        self._session.add(
            RepositorySnapshot(
                run_id=run.id,
                source_revision=ZHIPU_LIVE_CANARY_SOURCE_REVISION,
                branch_name="synthetic-live-canary",
                repository_is_dirty=False,
                dirty_path_count=0,
                dirty_paths=[],
                scanner_version="live-canary-synthetic-v1",
                scan_policy_version="live-canary-public-v1",
                fingerprint=ZHIPU_LIVE_CANARY_SNAPSHOT_FINGERPRINT,
                tracked_file_count=0,
                selected_file_count=0,
                skipped_file_count=0,
                total_selected_bytes=0,
                tech_stack={"languages": ["TypeScript"], "frameworks": ["React"]},
                package_manager=None,
                available_scripts=[],
                test_surfaces=[],
                design_system_signals=[],
                repository_instructions=[],
                safety_findings=[],
                manifest=[],
            )
        )
        request_payload = dispatch.model_dump(mode="json")
        context_payload = [item.model_dump(mode="json") for item in dispatch.context_manifest]
        ai_request = AIPlanRequest(
            run_id=run.id,
            status="requested",
            delivery_package=dispatch.delivery_package.value,
            source_revision=dispatch.repository.source_revision,
            snapshot_fingerprint=dispatch.repository.snapshot_fingerprint,
            prompt_template_id=ZHIPU_LIVE_CANARY_PROMPT_TEMPLATE_ID,
            prompt_version=ZHIPU_LIVE_CANARY_PROMPT_VERSION,
            prompt_digest=ZHIPU_LIVE_CANARY_PROMPT_DIGEST,
            prompt_payload={
                "template_id": ZHIPU_LIVE_CANARY_PROMPT_TEMPLATE_ID,
                "version": ZHIPU_LIVE_CANARY_PROMPT_VERSION,
                "digest": ZHIPU_LIVE_CANARY_PROMPT_DIGEST,
                "scenario_id": dispatch.scenario_id,
                "scenario_version": dispatch.scenario_version,
            },
            provider_id=ProviderId.ZHIPU.value,
            provider_metadata=ZHIPU_LIVE_CANARY_PROVIDER_METADATA.model_dump(mode="json"),
            request_payload=request_payload,
            request_digest=canonical_digest(request_payload),
            response_payload=None,
            deterministic_digest=None,
            context_manifest=context_payload,
            context_digest=canonical_digest(context_payload),
            context_bytes=len(canonical_json(context_payload)),
            context_reference_count=len(context_payload),
            context_excluded_count=0,
            redaction_record=[],
            retry_count=0,
            idempotency_key=f"zhipu-live-canary-request-{operation_id}",
            idempotency_request_hash=canonical_digest(
                {"scenario_id": dispatch.scenario_id, "operation_id": str(operation_id)}
            ),
        )
        self._session.add(ai_request)
        self._session.commit()
        ai_request.status = "generating"
        self._session.commit()
        return ai_request

    @staticmethod
    def _validated_plan(
        dispatch: ZhipuLiveCanaryDispatch,
        provider_result: ProviderAdapterResult,
    ) -> AIPlanContract:
        safe_payload, redactions = redact_structured_payload(provider_result.response_payload)
        if redactions:
            raise ValueError("provider response required secret redaction")
        content = ZhipuLiveCanaryPlanContent.model_validate(safe_payload)
        return build_zhipu_live_canary_plan(dispatch, content)

    def _persist_validated_plan(
        self,
        ai_plan_request_id: uuid.UUID,
        dispatch: ZhipuLiveCanaryDispatch,
        plan: AIPlanContract,
    ) -> None:
        evaluations = evaluate_zhipu_live_canary_plan(dispatch, plan)
        if not all(item.passed for item in evaluations):
            raise ZhipuLiveCanaryError("live_canary_eval_failed")
        request = self._session.get(AIPlanRequest, ai_plan_request_id)
        if request is None or request.status != "generating":
            raise ZhipuLiveCanaryError("ai_plan_request_state_drift")
        request.response_payload = plan.model_dump(mode="json")
        request.deterministic_digest = plan.deterministic_digest
        request.status = "generated"
        run = self._session.get(Run, request.run_id)
        if run is None or run.status != "snapshot_ready":
            raise ZhipuLiveCanaryError("canary_run_state_drift")
        run.status = "plan_ready"
        for item in evaluations:
            self._session.add(
                AIEvalResult(
                    ai_plan_request_id=request.id,
                    eval_id=item.eval_id,
                    passed=item.passed,
                    severity=item.severity,
                    summary=item.summary,
                    evidence=item.evidence,
                    evaluator_version=LIVE_CANARY_EVALUATOR_VERSION,
                    evaluator_trust="system_policy",
                )
            )
        self._session.commit()

    def _mark_request_failed(self, ai_plan_request_id: uuid.UUID, error: ProviderError) -> None:
        request = self._session.get(AIPlanRequest, ai_plan_request_id)
        if request is None:
            raise ZhipuLiveCanaryError("ai_plan_request_missing")
        request.status = "failed"
        request.error_category = error.category.value
        request.error_code = error.code[:64]
        request.error_message = error.public_message[:500]
        run = self._session.get(Run, request.run_id)
        if run is not None and run.status == "snapshot_ready":
            run.status = "failed"
            run.error_code = request.error_code
            run.error_message = request.error_message
        self._session.commit()

    def _authority_counts(self) -> tuple[int, ...]:
        return tuple(
            int(self._session.scalar(select(func.count()).select_from(model)) or 0)
            for model in _AUTHORITY_MODELS
        )

    def _assert_authority_unchanged(self, before: tuple[int, ...]) -> None:
        if self._authority_counts() != before:
            raise ZhipuLiveCanaryError("canary_authority_side_effect_detected")

    def _result(
        self,
        ai_plan_request_id: uuid.UUID,
        invocation_id: uuid.UUID,
        status: InvocationStatus,
    ) -> ZhipuLiveCanaryResult:
        invocation = self._session.get(AIProviderInvocation, invocation_id)
        if invocation is None:
            raise ZhipuLiveCanaryError("provider_invocation_missing")
        return ZhipuLiveCanaryResult(
            ai_plan_request_id=ai_plan_request_id,
            invocation_id=invocation_id,
            status=status,
            provider_id=invocation.provider_id,
            requested_model_id=invocation.requested_model_id,
            effective_model_status=invocation.effective_model_status,
            upstream_request_id_status=invocation.upstream_request_id_status,
            upstream_request_fingerprint=upstream_request_fingerprint(
                invocation.upstream_request_id
            ),
            usage_status=invocation.usage_status,
            input_tokens=invocation.input_tokens,
            output_tokens=invocation.output_tokens,
            total_tokens=invocation.total_tokens,
            queue_wait_ms=invocation.queue_wait_ms,
            provider_elapsed_ms=invocation.provider_elapsed_ms,
            client_total_elapsed_ms=invocation.client_total_elapsed_ms,
            billing_status=invocation.billing_status,
            error_code=invocation.error_code,
        )
