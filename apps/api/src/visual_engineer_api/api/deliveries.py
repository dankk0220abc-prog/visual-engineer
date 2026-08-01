import uuid
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.schemas.delivery import (
    DeliveryAuthorizationCreate,
    DeliveryAuthorizationDecisionCreate,
    DeliveryAuthorizationListResponse,
    DeliveryAuthorizationResponse,
)
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.services.delivery import DeliveryService, DeliveryServiceError

router = APIRouter(prefix="/api/v1", tags=["governed local delivery"])
DatabaseSession = Annotated[Session, Depends(get_db)]

DELIVERY_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Delivery resource not found"},
    409: {"model": ErrorResponse, "description": "Delivery state or freshness conflict"},
    422: {"model": ErrorResponse, "description": "Delivery policy denied the request"},
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


def _raise_service_error(error: DeliveryServiceError) -> NoReturn:
    status_code = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "policy": status.HTTP_422_UNPROCESSABLE_CONTENT,
    }.get(error.category, status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.post(
    "/delivery-authorizations",
    response_model=DeliveryAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
    responses=DELIVERY_ERRORS,
)
def create_delivery_authorization(
    payload: DeliveryAuthorizationCreate,
    request: Request,
    db: DatabaseSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> DeliveryAuthorizationResponse:
    try:
        return DeliveryService(db).create(
            payload,
            idempotency_key=_idempotency_key(idempotency_key),
            request_id=_request_id(request),
        )
    except DeliveryServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/delivery-authorizations",
    response_model=DeliveryAuthorizationListResponse,
    responses=DELIVERY_ERRORS,
)
def list_delivery_authorizations(db: DatabaseSession) -> DeliveryAuthorizationListResponse:
    try:
        return DeliveryService(db).list()
    except DeliveryServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/delivery-authorizations/{authorization_id}",
    response_model=DeliveryAuthorizationResponse,
    responses=DELIVERY_ERRORS,
)
def get_delivery_authorization(
    authorization_id: uuid.UUID,
    db: DatabaseSession,
) -> DeliveryAuthorizationResponse:
    try:
        return DeliveryService(db).get(authorization_id)
    except DeliveryServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/delivery-authorizations/{authorization_id}/decisions",
    response_model=DeliveryAuthorizationResponse,
    responses=DELIVERY_ERRORS,
)
def decide_delivery_authorization(
    authorization_id: uuid.UUID,
    payload: DeliveryAuthorizationDecisionCreate,
    request: Request,
    db: DatabaseSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> DeliveryAuthorizationResponse:
    try:
        return DeliveryService(db).decide(
            authorization_id,
            payload,
            idempotency_key=_idempotency_key(idempotency_key),
            request_id=_request_id(request),
        )
    except DeliveryServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/delivery-authorizations/{authorization_id}/dispatch",
    response_model=DeliveryAuthorizationResponse,
    responses=DELIVERY_ERRORS,
)
def dispatch_local_delivery(
    authorization_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> DeliveryAuthorizationResponse:
    try:
        return DeliveryService(db).dispatch(
            authorization_id,
            request_id=_request_id(request),
        )
    except DeliveryServiceError as exc:
        _raise_service_error(exc)
