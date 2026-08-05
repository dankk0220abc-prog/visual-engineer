import uuid
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from visual_engineer_api.ai_planning.provider_registry import ProviderRegistry
from visual_engineer_api.core.config import get_settings
from visual_engineer_api.db.session import get_db
from visual_engineer_api.schemas.ai_planning import (
    AIPlanDecisionCreate,
    AIPlanDecisionResponse,
    AIPlanRequestCreate,
    AIPlanRequestListResponse,
    AIPlanRequestResponse,
    AIProviderListResponse,
)
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.services.ai_planning import (
    AIPlanningService,
    AIPlanningServiceError,
)

router = APIRouter(prefix="/api/v1", tags=["governed AI planning"])
DatabaseSession = Annotated[Session, Depends(get_db)]

STANDARD_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "State or idempotency conflict"},
    422: {"model": ErrorResponse, "description": "Validation or policy denial"},
}


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else str(uuid.uuid4())


def _idempotency_key(value: str) -> str:
    normalized = value.strip()
    if not normalized or "\x00" in normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_idempotency_key",
                "message": "Idempotency-Key must be non-blank and contain no NUL characters",
            },
        )
    return normalized


def _raise_service_error(error: AIPlanningServiceError) -> NoReturn:
    status_code = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "policy": status.HTTP_422_UNPROCESSABLE_CONTENT,
    }.get(error.category, status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.get(
    "/ai-providers",
    response_model=AIProviderListResponse,
    summary="List installed model-neutral planning Provider capabilities",
)
def list_ai_providers() -> AIProviderListResponse:
    items = ProviderRegistry(get_settings()).list()
    return AIProviderListResponse(items=items, total=len(items))


@router.post(
    "/runs/{run_id}/ai-plan-requests",
    response_model=AIPlanRequestResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": AIPlanRequestResponse, "description": "Idempotent replay"},
        **STANDARD_ERRORS,
    },
    summary="Generate and independently evaluate one governed AI Plan",
)
def create_ai_plan_request(
    run_id: uuid.UUID,
    payload: AIPlanRequestCreate,
    request: Request,
    response: Response,
    db: DatabaseSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> AIPlanRequestResponse:
    try:
        result, replay = AIPlanningService(db).create_request(
            run_id,
            payload,
            request_id=_request_id(request),
            idempotency_key=_idempotency_key(idempotency_key),
        )
    except AIPlanningServiceError as exc:
        _raise_service_error(exc)
    if replay:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.get(
    "/runs/{run_id}/ai-plan-requests",
    response_model=AIPlanRequestListResponse,
    responses=STANDARD_ERRORS,
    summary="List governed AI Plan requests for a Run",
)
def list_ai_plan_requests(run_id: uuid.UUID, db: DatabaseSession) -> AIPlanRequestListResponse:
    try:
        items, total = AIPlanningService(db).list_for_run(run_id)
    except AIPlanningServiceError as exc:
        _raise_service_error(exc)
    return AIPlanRequestListResponse(items=items, total=total)


@router.get(
    "/ai-plan-requests/{ai_plan_request_id}",
    response_model=AIPlanRequestResponse,
    responses=STANDARD_ERRORS,
    summary="Get structured Plan, Prompt, context, Trace, Eval, and decision evidence",
)
def get_ai_plan_request(
    ai_plan_request_id: uuid.UUID, db: DatabaseSession
) -> AIPlanRequestResponse:
    try:
        return AIPlanningService(db).response(ai_plan_request_id)
    except AIPlanningServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/ai-plan-requests/{ai_plan_request_id}/freshness",
    response_model=AIPlanRequestResponse,
    responses=STANDARD_ERRORS,
    summary="Revalidate exact repository revision and fence a stale AI Plan",
)
def refresh_ai_plan_freshness(
    ai_plan_request_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> AIPlanRequestResponse:
    try:
        return AIPlanningService(db).refresh_freshness(
            ai_plan_request_id, request_id=_request_id(request)
        )
    except AIPlanningServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/ai-plan-requests/{ai_plan_request_id}/cancel",
    response_model=AIPlanRequestResponse,
    responses=STANDARD_ERRORS,
    summary="Cancel a non-terminal governed AI Plan request",
)
def cancel_ai_plan_request(
    ai_plan_request_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> AIPlanRequestResponse:
    try:
        return AIPlanningService(db).cancel(ai_plan_request_id, request_id=_request_id(request))
    except AIPlanningServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/ai-plan-requests/{ai_plan_request_id}/decisions",
    response_model=AIPlanDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": AIPlanDecisionResponse, "description": "Idempotent replay"},
        **STANDARD_ERRORS,
    },
    summary="Approve or reject a fresh evaluated AI Plan without issuing authority",
)
def decide_ai_plan_request(
    ai_plan_request_id: uuid.UUID,
    payload: AIPlanDecisionCreate,
    request: Request,
    response: Response,
    db: DatabaseSession,
) -> AIPlanDecisionResponse:
    try:
        result, replay = AIPlanningService(db).decide(
            ai_plan_request_id,
            payload,
            request_id=_request_id(request),
        )
    except AIPlanningServiceError as exc:
        _raise_service_error(exc)
    if replay:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return result
