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
    ValidationSuiteAggregateResponse,
    ValidationSuiteListResponse,
    ValidationSuiteRetryCreate,
    ValidationSuiteRunCreate,
    ValidationSuiteRunListResponse,
    ValidationSuiteRunResponse,
    ValidationSuiteTimelineResponse,
)
from visual_engineer_api.services.validation import ValidationService, ValidationServiceError
from visual_engineer_api.services.validation_suite import (
    ValidationSuiteService,
    ValidationSuiteServiceError,
)

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


def _raise_suite_service_error(error: ValidationSuiteServiceError) -> NoReturn:
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


@router.get(
    "/validation-suites",
    response_model=ValidationSuiteListResponse,
    summary="List immutable system-owned Validation Suites",
)
def list_validation_suites(db: DatabaseSession) -> ValidationSuiteListResponse:
    return ValidationSuiteService(db).catalog()


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


@router.post(
    "/validation-suite-runs",
    response_model=ValidationSuiteRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses=VALIDATION_ERRORS,
    summary="Queue one exact-Checkpoint fixed Validation Suite Run",
)
def create_validation_suite_run(
    payload: ValidationSuiteRunCreate,
    request: Request,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
) -> ValidationSuiteRunResponse:
    try:
        return ValidationSuiteService(db).create(
            payload,
            idempotency_key=_idempotency_key(idempotency_key),
            request_id=_request_id(request),
        )
    except ValidationSuiteServiceError as exc:
        _raise_suite_service_error(exc)


@router.get(
    "/validation-suite-runs",
    response_model=ValidationSuiteRunListResponse,
    responses=VALIDATION_ERRORS,
    summary="List governed Validation Suite Runs",
)
def list_validation_suite_runs(
    db: DatabaseSession,
    workspace_id: Annotated[uuid.UUID | None, Query()] = None,
) -> ValidationSuiteRunListResponse:
    try:
        return ValidationSuiteService(db).list(workspace_id=workspace_id)
    except ValidationSuiteServiceError as exc:
        _raise_suite_service_error(exc)


@router.get(
    "/validation-suite-runs/{suite_run_id}",
    response_model=ValidationSuiteRunResponse,
    responses=VALIDATION_ERRORS,
    summary="Get Validation Suite status, timeline, and bounded Evidence",
)
def get_validation_suite_run(
    suite_run_id: uuid.UUID,
    db: DatabaseSession,
) -> ValidationSuiteRunResponse:
    try:
        return ValidationSuiteService(db).get(suite_run_id)
    except ValidationSuiteServiceError as exc:
        _raise_suite_service_error(exc)


@router.get(
    "/validation-suite-runs/{suite_run_id}/timeline",
    response_model=ValidationSuiteTimelineResponse,
    responses=VALIDATION_ERRORS,
    summary="Get the ordered Validation Suite step timeline",
)
def get_validation_suite_timeline(
    suite_run_id: uuid.UUID,
    db: DatabaseSession,
) -> ValidationSuiteTimelineResponse:
    try:
        return ValidationSuiteService(db).timeline(suite_run_id)
    except ValidationSuiteServiceError as exc:
        _raise_suite_service_error(exc)


@router.get(
    "/validation-suite-runs/{suite_run_id}/result",
    response_model=ValidationSuiteAggregateResponse,
    responses=VALIDATION_ERRORS,
    summary="Get the aggregate Validation Suite Result and Evidence summary",
)
def get_validation_suite_result(
    suite_run_id: uuid.UUID,
    db: DatabaseSession,
) -> ValidationSuiteAggregateResponse:
    try:
        return ValidationSuiteService(db).aggregate(suite_run_id)
    except ValidationSuiteServiceError as exc:
        _raise_suite_service_error(exc)


@router.post(
    "/validation-suite-runs/{suite_run_id}/cancel",
    response_model=ValidationSuiteRunResponse,
    responses=VALIDATION_ERRORS,
    summary="Request cancellation of an active Validation Suite",
)
def cancel_validation_suite_run(
    suite_run_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> ValidationSuiteRunResponse:
    try:
        return ValidationSuiteService(db).cancel(
            suite_run_id,
            request_id=_request_id(request),
        )
    except ValidationSuiteServiceError as exc:
        _raise_suite_service_error(exc)


@router.post(
    "/validation-suite-runs/{suite_run_id}/retry",
    response_model=ValidationSuiteRunResponse,
    status_code=status.HTTP_201_CREATED,
    responses=VALIDATION_ERRORS,
    summary="Retry failed Suite steps under a new exact Grant",
)
def retry_validation_suite_run(
    suite_run_id: uuid.UUID,
    payload: ValidationSuiteRetryCreate,
    request: Request,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ],
) -> ValidationSuiteRunResponse:
    try:
        return ValidationSuiteService(db).retry(
            suite_run_id,
            payload,
            idempotency_key=_idempotency_key(idempotency_key),
            request_id=_request_id(request),
        )
    except ValidationSuiteServiceError as exc:
        _raise_suite_service_error(exc)
