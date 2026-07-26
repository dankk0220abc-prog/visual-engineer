import uuid
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.schemas.runner import (
    RunnerJobCreate,
    RunnerJobEventListResponse,
    RunnerJobListResponse,
    RunnerJobResponse,
    RunnerListResponse,
    RunnerResponse,
)
from visual_engineer_api.services.runner import RunnerService, RunnerServiceError

router = APIRouter(prefix="/api/v1", tags=["runner control plane"])
DatabaseSession = Annotated[Session, Depends(get_db)]

USER_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Runner or Job not found"},
    409: {"model": ErrorResponse, "description": "Runner or Job state conflict"},
    422: {"model": ErrorResponse, "description": "Invalid closed Job request"},
}


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else str(uuid.uuid4())


def _raise_service_error(error: RunnerServiceError) -> NoReturn:
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
    "/runners",
    response_model=RunnerListResponse,
    responses=USER_ERRORS,
    summary="List the local Runner registry with derived liveness",
)
def list_runners(db: DatabaseSession) -> RunnerListResponse:
    items = RunnerService(db).list_runners()
    return RunnerListResponse(items=items, total=len(items))


@router.get(
    "/runners/{runner_id}",
    response_model=RunnerResponse,
    responses=USER_ERRORS,
    summary="Get one Runner without exposing its credential",
)
def get_runner(runner_id: uuid.UUID, db: DatabaseSession) -> RunnerResponse:
    try:
        return RunnerService(db).get_runner(runner_id)
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/runners/{runner_id}/revoke",
    response_model=RunnerResponse,
    responses=USER_ERRORS,
    summary="Revoke one Runner credential and request cancellation",
)
def revoke_runner(
    runner_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> RunnerResponse:
    try:
        return RunnerService(db).revoke_runner(
            runner_id,
            request_id=_request_id(request),
        )
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/runner-jobs",
    response_model=RunnerJobListResponse,
    responses=USER_ERRORS,
    summary="List browser-dispatched Runner Jobs newest first",
)
def list_runner_jobs(db: DatabaseSession) -> RunnerJobListResponse:
    items = RunnerService(db).list_jobs()
    return RunnerJobListResponse(items=items, total=len(items))


@router.post(
    "/runner-jobs",
    response_model=RunnerJobResponse,
    status_code=status.HTTP_201_CREATED,
    responses=USER_ERRORS,
    summary="Create a typed Job and server-derived immutable Permission Envelope",
)
def create_runner_job(
    payload: RunnerJobCreate,
    request: Request,
    db: DatabaseSession,
) -> RunnerJobResponse:
    try:
        return RunnerService(db).create_job(payload, request_id=_request_id(request))
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/runner-jobs/{job_id}",
    response_model=RunnerJobResponse,
    responses=USER_ERRORS,
    summary="Get a Runner Job, safe lease summary, Envelope, and Attempts",
)
def get_runner_job(job_id: uuid.UUID, db: DatabaseSession) -> RunnerJobResponse:
    try:
        return RunnerService(db).get_job(job_id)
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/runner-jobs/{job_id}/cancel",
    response_model=RunnerJobResponse,
    responses=USER_ERRORS,
    summary="Request or complete cancellation without allowing later success",
)
def cancel_runner_job(
    job_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> RunnerJobResponse:
    try:
        return RunnerService(db).cancel_job(job_id, request_id=_request_id(request))
    except RunnerServiceError as exc:
        _raise_service_error(exc)


@router.get(
    "/runner-jobs/{job_id}/events",
    response_model=RunnerJobEventListResponse,
    responses=USER_ERRORS,
    summary="List the bounded Runner Job execution timeline",
)
def list_runner_job_events(
    job_id: uuid.UUID,
    db: DatabaseSession,
) -> RunnerJobEventListResponse:
    try:
        items = RunnerService(db).list_events(job_id)
    except RunnerServiceError as exc:
        _raise_service_error(exc)
    return RunnerJobEventListResponse(items=items, total=len(items))
