import uuid
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.schemas.validation import (
    ValidationProfileListResponse,
    ValidationRunCreate,
    ValidationRunListResponse,
    ValidationRunResponse,
)
from visual_engineer_api.services.validation import ValidationService, ValidationServiceError

router = APIRouter(prefix="/api/v1", tags=["governed validation"])
DatabaseSession = Annotated[Session, Depends(get_db)]

VALIDATION_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Validation resource not found"},
    409: {"model": ErrorResponse, "description": "Validation state or idempotency conflict"},
    422: {"model": ErrorResponse, "description": "Validation policy denied the request"},
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


def _raise_service_error(error: ValidationServiceError) -> NoReturn:
    status_code = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "policy": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "validation": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "internal": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }.get(error.category, status.HTTP_500_INTERNAL_SERVER_ERROR)
    raise HTTPException(
        status_code=status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.get(
    "/validation-profiles",
    response_model=ValidationProfileListResponse,
    summary="List immutable system-owned Validation Profiles",
)
def list_validation_profiles(db: DatabaseSession) -> ValidationProfileListResponse:
    return ValidationService(db).profiles()


@router.post(
    "/validation-runs",
    response_model=ValidationRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses=VALIDATION_ERRORS,
    summary="Queue one exact-Checkpoint fixed-Profile Validation Run",
)
def create_validation_run(
    payload: ValidationRunCreate,
    request: Request,
    db: DatabaseSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> ValidationRunResponse:
    try:
        return ValidationService(db).create(
            payload,
            idempotency_key=_idempotency_key(idempotency_key),
            request_id=_request_id(request),
        )
    except ValidationServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/validation-runs",
    response_model=ValidationRunListResponse,
    responses=VALIDATION_ERRORS,
    summary="List governed Validation Runs",
)
def list_validation_runs(
    db: DatabaseSession,
    workspace_id: Annotated[uuid.UUID | None, Query()] = None,
) -> ValidationRunListResponse:
    try:
        return ValidationService(db).list(workspace_id=workspace_id)
    except ValidationServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/validation-runs/{validation_run_id}",
    response_model=ValidationRunResponse,
    responses=VALIDATION_ERRORS,
    summary="Get structured Validation status and bounded evidence",
)
def get_validation_run(
    validation_run_id: uuid.UUID,
    db: DatabaseSession,
) -> ValidationRunResponse:
    try:
        return ValidationService(db).get(validation_run_id)
    except ValidationServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/validation-runs/{validation_run_id}/cancel",
    response_model=ValidationRunResponse,
    responses=VALIDATION_ERRORS,
    summary="Request cancellation through the fenced Runner Job",
)
def cancel_validation_run(
    validation_run_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> ValidationRunResponse:
    try:
        return ValidationService(db).cancel(
            validation_run_id,
            request_id=_request_id(request),
        )
    except ValidationServiceError as exc:
        _raise_service_error(exc)
