from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


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
    LIVE_VERIFIED = "live_verified"
    NOT_PERFORMED = "not_performed"


class ProviderStatusReason(StrEnum):
    AVAILABLE = "available"
    MISSING_SESSION_CREDENTIAL = "missing_session_credential"
    # Source-compatible alias for callers compiled against the pre-BYOK name.
    MISSING_LOCAL_API_KEY = "missing_session_credential"
    CONNECTED_WITH_USER_CREDENTIAL = "connected_with_user_credential"
    LIVE_VALIDATION_NOT_PERFORMED = "live_validation_not_performed"


class ProviderAdapterStatus(StrEnum):
    SUPPORTED = "supported"


class ProviderSessionCredentialStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    NOT_CONNECTED = "not_connected"
    CONNECTED = "connected"


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
    adapter_status: ProviderAdapterStatus
    session_credential_status: ProviderSessionCredentialStatus
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
    local_secret_required: bool
    documentation_url: str
    enabled: bool


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

_VALIDATED_ZHIPU_CAPABILITIES = ProviderCapabilityDeclaration(
    structured_output=CapabilitySupport.SUPPORTED,
    tool_calling=CapabilitySupport.UNSUPPORTED,
    streaming=CapabilitySupport.UNSUPPORTED,
    reasoning=CapabilitySupport.UNSUPPORTED,
    token_usage_reporting=CapabilitySupport.SUPPORTED,
    request_id=CapabilitySupport.SUPPORTED,
    configurable_timeout=CapabilitySupport.SUPPORTED,
    model_availability=CapabilitySupport.SUPPORTED,
    maximum_output_control=CapabilitySupport.SUPPORTED,
)

PROVIDER_DEFINITIONS: tuple[ProviderDefinition, ...] = (
    ProviderDefinition(
        provider_id=ProviderId.DETERMINISTIC_FIXTURE,
        display_name="Deterministic Fixture",
        model_id="fixture-planner-v1",
        local_secret_required=False,
        documentation_url="https://github.com/dankk0220abc-prog/visual-engineer",
        enabled=True,
    ),
    ProviderDefinition(
        provider_id=ProviderId.ZHIPU,
        display_name="Zhipu GLM",
        model_id="glm-5.2",
        local_secret_required=True,
        documentation_url="https://docs.bigmodel.cn/api-reference/模型-api/对话补全",
        enabled=False,
    ),
    ProviderDefinition(
        provider_id=ProviderId.QWEN,
        display_name="Qwen",
        model_id="qwen3.8-max",
        local_secret_required=True,
        documentation_url="https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions",
        enabled=False,
    ),
    ProviderDefinition(
        provider_id=ProviderId.DEEPSEEK,
        display_name="DeepSeek",
        model_id="deepseek-v4-pro",
        local_secret_required=True,
        documentation_url="https://api-docs.deepseek.com/api/create-chat-completion",
        enabled=False,
    ),
    ProviderDefinition(
        provider_id=ProviderId.DOUBAO,
        display_name="Doubao",
        model_id="doubao-seed-2-0-lite-260215",
        local_secret_required=True,
        documentation_url="https://www.volcengine.com/docs/82379/1795150",
        enabled=False,
    ),
    ProviderDefinition(
        provider_id=ProviderId.KIMI,
        display_name="Kimi",
        model_id="kimi-k2.6",
        local_secret_required=True,
        documentation_url="https://platform.kimi.com/docs/api/chat",
        enabled=False,
    ),
)

_DEFINITIONS_BY_ID = {item.provider_id: item for item in PROVIDER_DEFINITIONS}


class ProviderRegistry:
    def get(
        self,
        provider_id: ProviderId,
        *,
        session_connected: bool = False,
        live_verified: bool = False,
    ) -> ProviderConfigurationStatus:
        definition = _DEFINITIONS_BY_ID[provider_id]
        if definition.enabled:
            return ProviderConfigurationStatus(
                provider_id=provider_id,
                display_name=definition.display_name,
                model_id=definition.model_id,
                configured=True,
                enabled=True,
                adapter_status=ProviderAdapterStatus.SUPPORTED,
                session_credential_status=ProviderSessionCredentialStatus.NOT_REQUIRED,
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

        return ProviderConfigurationStatus(
            provider_id=provider_id,
            display_name=definition.display_name,
            model_id=definition.model_id,
            configured=session_connected,
            enabled=session_connected,
            adapter_status=ProviderAdapterStatus.SUPPORTED,
            session_credential_status=(
                ProviderSessionCredentialStatus.CONNECTED
                if session_connected
                else ProviderSessionCredentialStatus.NOT_CONNECTED
            ),
            live_validation_status=(
                ProviderLiveValidationStatus.LIVE_VERIFIED
                if live_verified
                else ProviderLiveValidationStatus.NOT_PERFORMED
            ),
            local_secret_required=definition.local_secret_required,
            status_reason=(
                ProviderStatusReason.CONNECTED_WITH_USER_CREDENTIAL
                if session_connected
                else ProviderStatusReason.MISSING_SESSION_CREDENTIAL
            ),
            reason_disabled=(
                None if session_connected else ProviderStatusReason.MISSING_SESSION_CREDENTIAL
            ),
            status_description=(
                "Available for this browser session with the user's ephemeral credential."
                if session_connected
                else "Provider unavailable for this session: configure your own credential. "
                "A maintainer credential is never a product fallback."
            ),
            documentation_url=definition.documentation_url,
            capabilities=(
                _VALIDATED_ZHIPU_CAPABILITIES
                if provider_id == ProviderId.ZHIPU and live_verified
                else _UNVALIDATED_REAL_CAPABILITIES
            ),
        )

    def list(
        self,
        *,
        connected: set[ProviderId] | None = None,
        live_verified: set[ProviderId] | None = None,
    ) -> list[ProviderConfigurationStatus]:
        connected_ids = connected or set()
        verified_ids = live_verified or set()
        return [
            self.get(
                item.provider_id,
                session_connected=item.provider_id in connected_ids,
                live_verified=item.provider_id in verified_ids,
            )
            for item in PROVIDER_DEFINITIONS
        ]

    def definition(self, provider_id: ProviderId) -> ProviderDefinition:
        return _DEFINITIONS_BY_ID[provider_id]

    @staticmethod
    def is_enabled(provider_id: ProviderId) -> bool:
        """Return product enablement without reading any Provider credential."""
        return _DEFINITIONS_BY_ID[provider_id].enabled
