import uuid
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.models.runner import Runner
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError
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
    StartRequest,
)

router = APIRouter(prefix=RUNNER_PROTOCOL_PREFIX, tags=["runner protocol"])
DatabaseSession = Annotated[Session, Depends(get_db)]

PROTOCOL_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Invalid Runner credential"},
    403: {"model": ErrorResponse, "description": "Revoked or mismatched Runner"},
    409: {"model": ErrorResponse, "description": "Stale or conflicting lease"},
    413: {"model": ErrorResponse, "description": "Runner protocol payload too large"},
    422: {"model": ErrorResponse, "description": "Protocol or policy validation failure"},
    503: {"model": ErrorResponse, "description": "Registration unavailable"},
}


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else str(uuid.uuid4())


def _bearer_token(authorization: str | None) -> str:
    if authorization is None:
        _raise_service_error(
            RunnerServiceError(
                "runner_auth_invalid",
                "Runner authentication failed",
                category="auth",
            )
        )
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.casefold() != "bearer" or not token.strip():
        _raise_service_error(
            RunnerServiceError(
                "runner_auth_invalid",
                "Runner authentication failed",
                category="auth",
            )
        )
    return token.strip()


def _raise_service_error(error: RunnerServiceError) -> NoReturn:
    status_code = {
        "auth": status.HTTP_401_UNAUTHORIZED,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "policy": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "validation": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
        "internal": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }.get(error.category, status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


def _authenticated_runner(
    db: DatabaseSession,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> Runner:
    token = _bearer_token(authorization)
    try:
        return RunnerService(db).authenticate(token)
    except RunnerServiceError as exc:
        _raise_service_error(exc)


AuthenticatedRunner = Annotated[Runner, Depends(_authenticated_runner)]


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTOCOL_ERRORS,
    summary="Register a Local Runner with the one-time bootstrap credential",
)
def register_runner(
    payload: RegisterRequest,
    request: Request,
    db: DatabaseSession,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> RegisterResponse:
    try:
        return RunnerService(db).register(
            payload,
            bootstrap_token=_bearer_token(authorization),
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/heartbeat",
    response_model=HeartbeatResponse,
    responses=PROTOCOL_ERRORS,
    summary="Refresh Runner liveness without creating heartbeat event spam",
)
def heartbeat(
    payload: HeartbeatRequest,
    request: Request,
    db: DatabaseSession,
    authenticated: AuthenticatedRunner,
) -> HeartbeatResponse:
    try:
        return RunnerService(db).heartbeat(
            authenticated,
            payload,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/jobs/claim",
    response_model=ClaimResponse,
    responses=PROTOCOL_ERRORS,
    summary="Atomically claim one compatible queued Job",
)
def claim_job(
    payload: ClaimRequest,
    request: Request,
    db: DatabaseSession,
    authenticated: AuthenticatedRunner,
) -> ClaimResponse:
    try:
        return RunnerService(db).claim(
            authenticated,
            payload,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/jobs/{job_id}/start",
    response_model=LeaseMutationResponse,
    responses=PROTOCOL_ERRORS,
    summary="Start the active fenced Job Attempt",
)
def start_job(
    job_id: uuid.UUID,
    payload: StartRequest,
    request: Request,
    db: DatabaseSession,
    authenticated: AuthenticatedRunner,
) -> LeaseMutationResponse:
    try:
        return RunnerService(db).start(
            authenticated,
            job_id,
            payload,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/jobs/{job_id}/renew",
    response_model=LeaseMutationResponse,
    responses=PROTOCOL_ERRORS,
    summary="Renew the active lease and receive cancellation state",
)
def renew_job(
    job_id: uuid.UUID,
    payload: RenewRequest,
    request: Request,
    db: DatabaseSession,
    authenticated: AuthenticatedRunner,
) -> LeaseMutationResponse:
    try:
        return RunnerService(db).renew(
            authenticated,
            job_id,
            payload,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/jobs/{job_id}/events",
    response_model=LeaseMutationResponse,
    responses=PROTOCOL_ERRORS,
    summary="Append one closed, bounded Runner progress event",
)
def append_job_event(
    job_id: uuid.UUID,
    payload: ProgressEventRequest,
    request: Request,
    db: DatabaseSession,
    authenticated: AuthenticatedRunner,
) -> LeaseMutationResponse:
    try:
        return RunnerService(db).progress(
            authenticated,
            job_id,
            payload,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/jobs/{job_id}/complete",
    response_model=LeaseMutationResponse,
    responses=PROTOCOL_ERRORS,
    summary="Store one typed result for the active fenced Attempt",
)
def complete_job(
    job_id: uuid.UUID,
    payload: CompleteRequest,
    request: Request,
    db: DatabaseSession,
    authenticated: AuthenticatedRunner,
) -> LeaseMutationResponse:
    try:
        return RunnerService(db).complete(
            authenticated,
            job_id,
            payload,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/jobs/{job_id}/fail",
    response_model=LeaseMutationResponse,
    responses=PROTOCOL_ERRORS,
    summary="Store one typed sanitized failure for the active Attempt",
)
def fail_job(
    job_id: uuid.UUID,
    payload: FailRequest,
    request: Request,
    db: DatabaseSession,
    authenticated: AuthenticatedRunner,
) -> LeaseMutationResponse:
    try:
        return RunnerService(db).fail(
            authenticated,
            job_id,
            payload,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/jobs/{job_id}/cancelled",
    response_model=LeaseMutationResponse,
    responses=PROTOCOL_ERRORS,
    summary="Acknowledge cancellation for the active fenced Attempt",
)
def acknowledge_cancelled(
    job_id: uuid.UUID,
    payload: CancelledRequest,
    request: Request,
    db: DatabaseSession,
    authenticated: AuthenticatedRunner,
) -> LeaseMutationResponse:
    try:
        return RunnerService(db).cancelled(
            authenticated,
            job_id,
            payload,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)
