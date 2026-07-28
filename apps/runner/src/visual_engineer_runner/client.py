import uuid
from typing import TypeVar

import httpx
from pydantic import BaseModel, SecretStr

from visual_engineer_runner.auth import bearer_header
from visual_engineer_runner_protocol import (
    RUNNER_PROTOCOL_PREFIX,
    CancelledRequest,
    ClaimRequest,
    ClaimResponse,
    CompleteRequest,
    FailRequest,
    HeartbeatRequest,
    HeartbeatResponse,
    LeaseMutationResponse,
    ProgressEventRequest,
    RegisterRequest,
    RegisterResponse,
    RenewRequest,
    RepositoryRegistrationRequest,
    RepositoryRegistrationResponse,
    SideEffectPermit,
    SideEffectPermitAcquireRequest,
    StartRequest,
)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


class ControlPlaneError(Exception):
    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code

    @property
    def transient(self) -> bool:
        return self.status_code == 0 or self.status_code >= 500


class ControlPlaneClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def register(
        self,
        payload: RegisterRequest,
        bootstrap_token: SecretStr,
    ) -> RegisterResponse:
        return await self._request(
            "POST",
            f"{RUNNER_PROTOCOL_PREFIX}/register",
            RegisterResponse,
            payload=payload,
            token=bootstrap_token,
        )

    async def heartbeat(
        self,
        payload: HeartbeatRequest,
        token: SecretStr,
    ) -> HeartbeatResponse:
        return await self._request(
            "POST",
            f"{RUNNER_PROTOCOL_PREFIX}/heartbeat",
            HeartbeatResponse,
            payload=payload,
            token=token,
        )

    async def register_repository(
        self,
        payload: RepositoryRegistrationRequest,
        token: SecretStr,
    ) -> RepositoryRegistrationResponse:
        return await self._request(
            "POST",
            f"{RUNNER_PROTOCOL_PREFIX}/repositories/register",
            RepositoryRegistrationResponse,
            payload=payload,
            token=token,
        )

    async def claim(self, payload: ClaimRequest, token: SecretStr) -> ClaimResponse:
        return await self._request(
            "POST",
            f"{RUNNER_PROTOCOL_PREFIX}/jobs/claim",
            ClaimResponse,
            payload=payload,
            token=token,
        )

    async def start(
        self,
        job_id: uuid.UUID,
        payload: StartRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        return await self._lease_mutation("start", job_id, payload, token)

    async def acquire_side_effect_permit(
        self,
        job_id: uuid.UUID,
        payload: SideEffectPermitAcquireRequest,
        token: SecretStr,
    ) -> SideEffectPermit:
        return await self._request(
            "POST",
            f"{RUNNER_PROTOCOL_PREFIX}/jobs/{job_id}/side-effect-permit",
            SideEffectPermit,
            payload=payload,
            token=token,
        )

    async def renew(
        self,
        job_id: uuid.UUID,
        payload: RenewRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        return await self._lease_mutation("renew", job_id, payload, token)

    async def progress(
        self,
        job_id: uuid.UUID,
        payload: ProgressEventRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        return await self._lease_mutation("events", job_id, payload, token)

    async def complete(
        self,
        job_id: uuid.UUID,
        payload: CompleteRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        return await self._lease_mutation("complete", job_id, payload, token)

    async def fail(
        self,
        job_id: uuid.UUID,
        payload: FailRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        return await self._lease_mutation("fail", job_id, payload, token)

    async def cancelled(
        self,
        job_id: uuid.UUID,
        payload: CancelledRequest,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        return await self._lease_mutation("cancelled", job_id, payload, token)

    async def _lease_mutation(
        self,
        action: str,
        job_id: uuid.UUID,
        payload: BaseModel,
        token: SecretStr,
    ) -> LeaseMutationResponse:
        return await self._request(
            "POST",
            f"{RUNNER_PROTOCOL_PREFIX}/jobs/{job_id}/{action}",
            LeaseMutationResponse,
            payload=payload,
            token=token,
        )

    async def _request(
        self,
        method: str,
        path: str,
        response_model: type[ResponseModel],
        *,
        payload: BaseModel,
        token: SecretStr,
    ) -> ResponseModel:
        try:
            response = await self._client.request(
                method,
                path,
                headers={
                    **bearer_header(token),
                    "Content-Type": "application/json",
                    "X-Request-ID": str(uuid.uuid4()),
                },
                content=payload.model_dump_json(),
            )
        except httpx.HTTPError as exc:
            raise ControlPlaneError(0, "control_plane_unavailable") from exc
        if len(response.content) > 64 * 1024:
            raise ControlPlaneError(502, "protocol_response_too_large")
        if not response.is_success:
            code = "control_plane_error"
            try:
                body = response.json()
                candidate = body.get("error", {}).get("code")
                if isinstance(candidate, str) and candidate:
                    code = candidate[:64]
            except ValueError:
                pass
            raise ControlPlaneError(response.status_code, code)
        try:
            return response_model.model_validate_json(response.content)
        except ValueError as exc:
            raise ControlPlaneError(502, "invalid_protocol_response") from exc
