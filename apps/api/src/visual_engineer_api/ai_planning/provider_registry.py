from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from visual_engineer_api.core.config import Settings


class ProviderId(StrEnum):
    DETERMINISTIC_FIXTURE = "deterministic-fixture"
    ZHIPU = "zhipu"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"
    KIMI = "kimi"


class CapabilitySupport(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    NOT_VERIFIED = "not_verified"


class ProviderLiveValidationStatus(StrEnum):
    FIXTURE_VALIDATED = "fixture_validated"
    NOT_PERFORMED = "not_performed"


class ProviderStatusReason(StrEnum):
    AVAILABLE = "available"
    MISSING_LOCAL_API_KEY = "missing_local_api_key"
    LIVE_VALIDATION_NOT_PERFORMED = "live_validation_not_performed"


class ProviderCapabilityDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    structured_output: CapabilitySupport
    tool_calling: CapabilitySupport
    streaming: CapabilitySupport
    reasoning: CapabilitySupport
    token_usage_reporting: CapabilitySupport
    request_id: CapabilitySupport
    configurable_timeout: CapabilitySupport
    model_availability: CapabilitySupport
    maximum_output_control: CapabilitySupport


class ProviderConfigurationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_id: ProviderId
    display_name: str
    model_id: str
    configured: bool
    enabled: bool
    live_validation_status: ProviderLiveValidationStatus
    local_secret_required: bool
    status_reason: ProviderStatusReason
    reason_disabled: ProviderStatusReason | None
    status_description: str
    documentation_url: str
    capabilities: ProviderCapabilityDeclaration


@dataclass(frozen=True)
class ProviderDefinition:
    provider_id: ProviderId
    display_name: str
    model_id: str
    secret_setting: str | None
    documentation_url: str


_FIXTURE_CAPABILITIES = ProviderCapabilityDeclaration(
    structured_output=CapabilitySupport.SUPPORTED,
    tool_calling=CapabilitySupport.UNSUPPORTED,
    streaming=CapabilitySupport.UNSUPPORTED,
    reasoning=CapabilitySupport.UNSUPPORTED,
    token_usage_reporting=CapabilitySupport.SUPPORTED,
    request_id=CapabilitySupport.UNSUPPORTED,
    configurable_timeout=CapabilitySupport.SUPPORTED,
    model_availability=CapabilitySupport.SUPPORTED,
    maximum_output_control=CapabilitySupport.SUPPORTED,
)

_UNVALIDATED_REAL_CAPABILITIES = ProviderCapabilityDeclaration(
    structured_output=CapabilitySupport.NOT_VERIFIED,
    tool_calling=CapabilitySupport.UNSUPPORTED,
    streaming=CapabilitySupport.UNSUPPORTED,
    reasoning=CapabilitySupport.UNSUPPORTED,
    token_usage_reporting=CapabilitySupport.NOT_VERIFIED,
    request_id=CapabilitySupport.NOT_VERIFIED,
    configurable_timeout=CapabilitySupport.SUPPORTED,
    model_availability=CapabilitySupport.NOT_VERIFIED,
    maximum_output_control=CapabilitySupport.NOT_VERIFIED,
)

PROVIDER_DEFINITIONS: tuple[ProviderDefinition, ...] = (
    ProviderDefinition(
        provider_id=ProviderId.DETERMINISTIC_FIXTURE,
        display_name="Deterministic Fixture",
        model_id="fixture-planner-v1",
        secret_setting=None,
        documentation_url="https://github.com/dankk0220abc-prog/visual-engineer",
    ),
    ProviderDefinition(
        provider_id=ProviderId.ZHIPU,
        display_name="Zhipu GLM",
        model_id="glm-5.2",
        secret_setting="zhipu_api_key",
        documentation_url="https://docs.bigmodel.cn/api-reference/模型-api/对话补全",
    ),
    ProviderDefinition(
        provider_id=ProviderId.QWEN,
        display_name="Qwen",
        model_id="qwen3.8-max",
        secret_setting="qwen_api_key",
        documentation_url="https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions",
    ),
    ProviderDefinition(
        provider_id=ProviderId.DEEPSEEK,
        display_name="DeepSeek",
        model_id="deepseek-v4-pro",
        secret_setting="deepseek_api_key",
        documentation_url="https://api-docs.deepseek.com/api/create-chat-completion",
    ),
    ProviderDefinition(
        provider_id=ProviderId.DOUBAO,
        display_name="Doubao",
        model_id="doubao-seed-2-0-lite-260215",
        secret_setting="doubao_api_key",
        documentation_url="https://www.volcengine.com/docs/82379/1795150",
    ),
    ProviderDefinition(
        provider_id=ProviderId.KIMI,
        display_name="Kimi",
        model_id="kimi-k2.6",
        secret_setting="kimi_api_key",
        documentation_url="https://platform.kimi.com/docs/api/chat",
    ),
)

_DEFINITIONS_BY_ID = {item.provider_id: item for item in PROVIDER_DEFINITIONS}


class ProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get(self, provider_id: ProviderId) -> ProviderConfigurationStatus:
        definition = _DEFINITIONS_BY_ID[provider_id]
        if provider_id == ProviderId.DETERMINISTIC_FIXTURE:
            return ProviderConfigurationStatus(
                provider_id=provider_id,
                display_name=definition.display_name,
                model_id=definition.model_id,
                configured=True,
                enabled=True,
                live_validation_status=ProviderLiveValidationStatus.FIXTURE_VALIDATED,
                local_secret_required=False,
                status_reason=ProviderStatusReason.AVAILABLE,
                reason_disabled=None,
                status_description=(
                    "Offline deterministic Provider for CI, Eval, demos, and diagnosis."
                ),
                documentation_url=definition.documentation_url,
                capabilities=_FIXTURE_CAPABILITIES,
            )

        configured = self._has_secret(definition)
        reason = (
            ProviderStatusReason.LIVE_VALIDATION_NOT_PERFORMED
            if configured
            else ProviderStatusReason.MISSING_LOCAL_API_KEY
        )
        return ProviderConfigurationStatus(
            provider_id=provider_id,
            display_name=definition.display_name,
            model_id=definition.model_id,
            configured=configured,
            enabled=False,
            live_validation_status=ProviderLiveValidationStatus.NOT_PERFORMED,
            local_secret_required=True,
            status_reason=reason,
            reason_disabled=reason,
            status_description=(
                "Adapter foundation is mock-contract verified; live validation was not performed."
            ),
            documentation_url=definition.documentation_url,
            capabilities=_UNVALIDATED_REAL_CAPABILITIES,
        )

    def list(self) -> list[ProviderConfigurationStatus]:
        return [self.get(item.provider_id) for item in PROVIDER_DEFINITIONS]

    def definition(self, provider_id: ProviderId) -> ProviderDefinition:
        return _DEFINITIONS_BY_ID[provider_id]

    def _has_secret(self, definition: ProviderDefinition) -> bool:
        if definition.secret_setting is None:
            return True
        secret = getattr(self._settings, definition.secret_setting)
        return bool(secret.get_secret_value().strip())
