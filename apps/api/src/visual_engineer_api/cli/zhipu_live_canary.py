import asyncio
import sys
from collections.abc import Sequence

from visual_engineer_api.ai_planning.invocation_contract import InvocationStatus
from visual_engineer_api.ai_planning.zhipu_live_canary import (
    ZHIPU_LIVE_CANARY_MODEL_ID,
    ZHIPU_LIVE_CANARY_SCENARIO_ID,
    ZHIPU_LIVE_CANARY_SCENARIO_VERSION,
)
from visual_engineer_api.services.zhipu_live_canary import (
    LIVE_CANARY_WARNING,
    USER_SECRET_PROVISION_REQUIRED,
    ZHIPU_API_KEY_ENV,
    LiveValidationAuthorizationRequired,
    UserSecretProvisionRequired,
    ZhipuLiveCanaryError,
    ZhipuLiveCanaryResult,
    production_zhipu_live_canary_service,
    run_secret_blind_preflight,
)

_USAGE = "usage: zhipu-live-canary {preflight|run}"


def _preflight() -> int:
    try:
        run_secret_blind_preflight()
    except ZhipuLiveCanaryError as error:
        print(f"ZHIPU_LIVE_CANARY_PREFLIGHT_FAILED code={error.code}", file=sys.stderr)
        return 1
    print(f"scenario_id={ZHIPU_LIVE_CANARY_SCENARIO_ID}")
    print(f"scenario_version={ZHIPU_LIVE_CANARY_SCENARIO_VERSION}")
    print("provider=zhipu")
    print(f"requested_model={ZHIPU_LIVE_CANARY_MODEL_ID}")
    print(f"secret_variable={ZHIPU_API_KEY_ENV}")
    print("Configure the secret only in the local terminal after independent review.")
    print("Do not paste it into chat or place it in a tracked .env file.")
    print(USER_SECRET_PROVISION_REQUIRED)
    return 0


def _safe_result(result: ZhipuLiveCanaryResult) -> None:
    print(f"scenario_id={ZHIPU_LIVE_CANARY_SCENARIO_ID}")
    print("provider=zhipu")
    print(f"invocation_correlation={result.invocation_id.hex[:12]}")
    print(f"lifecycle_status={result.status.value}")
    print(f"requested_model={result.requested_model_id}")
    print(f"effective_model_status={result.effective_model_status}")
    print(f"upstream_request_id_status={result.upstream_request_id_status}")
    if result.upstream_request_fingerprint is not None:
        print(f"upstream_request_fingerprint={result.upstream_request_fingerprint}")
    print(f"usage_status={result.usage_status}")
    if result.input_tokens is not None:
        print(f"input_tokens={result.input_tokens}")
    if result.output_tokens is not None:
        print(f"output_tokens={result.output_tokens}")
    if result.total_tokens is not None:
        print(f"total_tokens={result.total_tokens}")
    if result.queue_wait_ms is not None:
        print(f"queue_wait_ms={result.queue_wait_ms}")
    if result.provider_elapsed_ms is not None:
        print(f"provider_elapsed_ms={result.provider_elapsed_ms}")
    if result.client_total_elapsed_ms is not None:
        print(f"client_total_elapsed_ms={result.client_total_elapsed_ms}")
    print(f"billing_status={result.billing_status}")
    if result.status == InvocationStatus.SUCCEEDED:
        print(f"ai_plan_request_id={result.ai_plan_request_id}")
    if result.error_code is not None:
        print(f"error_code={result.error_code}")


def _run() -> int:
    try:
        with production_zhipu_live_canary_service() as service:
            print(LIVE_CANARY_WARNING)
            result = asyncio.run(service.run())
    except LiveValidationAuthorizationRequired:
        print("LIVE_VALIDATION_AUTHORIZATION_REQUIRED", file=sys.stderr)
        return 1
    except UserSecretProvisionRequired:
        print(USER_SECRET_PROVISION_REQUIRED)
        return 1
    except ZhipuLiveCanaryError as error:
        print(f"ZHIPU_LIVE_CANARY_FAILED code={error.code}", file=sys.stderr)
        return 1
    except Exception:
        print("ZHIPU_LIVE_CANARY_FAILED code=internal_failure", file=sys.stderr)
        return 1
    _safe_result(result)
    return 0 if result.status == InvocationStatus.SUCCEEDED else 1


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["preflight"]:
        return _preflight()
    if arguments == ["run"]:
        return _run()
    print(_USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
