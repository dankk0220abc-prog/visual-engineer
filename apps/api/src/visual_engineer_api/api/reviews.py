import uuid
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.schemas.review import (
    ReviewDecisionCreate,
    ReviewPackageCreate,
    ReviewPackageListResponse,
    ReviewPackageResponse,
)
from visual_engineer_api.services.review import ReviewService, ReviewServiceError

router = APIRouter(prefix="/api/v1", tags=["governed final review"])
DatabaseSession = Annotated[Session, Depends(get_db)]

REVIEW_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Review resource not found"},
    409: {"model": ErrorResponse, "description": "Review freshness or decision conflict"},
    422: {"model": ErrorResponse, "description": "Review policy denied the request"},
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


def _raise_service_error(error: ReviewServiceError) -> NoReturn:
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
    "/review-packages",
    response_model=ReviewPackageResponse,
    status_code=status.HTTP_201_CREATED,
    responses=REVIEW_ERRORS,
    summary="Create an immutable trusted-Evidence Review Package",
)
def create_review_package(
    payload: ReviewPackageCreate,
    request: Request,
    db: DatabaseSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> ReviewPackageResponse:
    try:
        return ReviewService(db).create(
            payload,
            idempotency_key=_idempotency_key(idempotency_key),
            request_id=_request_id(request),
        )
    except ReviewServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/review-packages",
    response_model=ReviewPackageListResponse,
    responses=REVIEW_ERRORS,
    summary="List governed Review Packages and effective freshness",
)
def list_review_packages(db: DatabaseSession) -> ReviewPackageListResponse:
    try:
        return ReviewService(db).list()
    except ReviewServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/review-packages/{package_id}",
    response_model=ReviewPackageResponse,
    responses=REVIEW_ERRORS,
    summary="Get an immutable Review Package and readiness state",
)
def get_review_package(
    package_id: uuid.UUID,
    db: DatabaseSession,
) -> ReviewPackageResponse:
    try:
        return ReviewService(db).get(package_id)
    except ReviewServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/review-packages/{package_id}/freshness",
    response_model=ReviewPackageResponse,
    responses=REVIEW_ERRORS,
    summary="Revalidate freshness and durably fence a stale Review Package",
)
def refresh_review_package_freshness(
    package_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> ReviewPackageResponse:
    try:
        return ReviewService(db).refresh_freshness(
            package_id,
            request_id=_request_id(request),
        )
    except ReviewServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/review-packages/{package_id}/decisions",
    response_model=ReviewPackageResponse,
    responses=REVIEW_ERRORS,
    summary="Record one immutable local-user Review Decision",
)
def decide_review_package(
    package_id: uuid.UUID,
    payload: ReviewDecisionCreate,
    request: Request,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ] = None,
) -> ReviewPackageResponse:
    try:
        return ReviewService(db).decide(
            package_id,
            payload,
            request_id=_request_id(request),
            idempotency_key=(
                _idempotency_key(idempotency_key) if idempotency_key is not None else None
            ),
        )
    except ReviewServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/review-packages/{package_id}/readiness",
    response_model=ReviewPackageResponse,
    responses=REVIEW_ERRORS,
    summary="Compute one deterministic Release Readiness Verdict",
)
def evaluate_release_readiness(
    package_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> ReviewPackageResponse:
    try:
        return ReviewService(db).evaluate_readiness(
            package_id,
            request_id=_request_id(request),
        )
    except ReviewServiceError as exc:
        _raise_service_error(exc)
