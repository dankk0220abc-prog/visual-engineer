import uuid
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, Response, status
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.models.run import (
    ApprovalDecision,
    Plan,
    RepositorySnapshot,
    Run,
)
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.schemas.run import (
    ApprovalDecisionResponse,
    AuditEventListResponse,
    AuditEventResponse,
    PlanCreate,
    PlanDecisionCreate,
    PlanListResponse,
    PlanResponse,
    PlanRevisionCreate,
    RunCancelCreate,
    RunCreate,
    RunListResponse,
    RunResponse,
    SnapshotResponse,
)
from visual_engineer_api.services.run import RunService, RunServiceError

router = APIRouter(prefix="/api/v1", tags=["repository intelligence"])
DatabaseSession = Annotated[Session, Depends(get_db)]
PlanVersion = Annotated[int, Path(ge=1, le=1_000_000)]

STANDARD_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "State or idempotency conflict"},
    422: {"model": ErrorResponse, "description": "Validation or policy denial"},
}


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else str(uuid.uuid4())


def _optional_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
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


def _raise_service_error(error: RunServiceError) -> NoReturn:
    status_code = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "policy": status.HTTP_422_UNPROCESSABLE_CONTENT,
    }.get(error.category, status.HTTP_500_INTERNAL_SERVER_ERROR)
    detail: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.details is not None:
        detail["details"] = error.details
    raise HTTPException(status_code=status_code, detail=detail) from error


@router.post(
    "/tasks/{task_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": RunResponse, "description": "Idempotent replay"},
        **STANDARD_ERRORS,
    },
    summary="Create a Level 0 committed-HEAD Run",
)
def create_run(
    task_id: uuid.UUID,
    payload: RunCreate,
    request: Request,
    response: Response,
    db: DatabaseSession,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ] = None,
) -> Run:
    try:
        run, replay = RunService(db).create_run(
            task_id,
            payload,
            request_id=_request_id(request),
            idempotency_key=_optional_idempotency_key(idempotency_key),
        )
    except RunServiceError as exc:
        _raise_service_error(exc)
    if replay:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return run


@router.get(
    "/tasks/{task_id}/runs",
    response_model=RunListResponse,
    responses=STANDARD_ERRORS,
    summary="List Runs for a Task",
)
def list_runs(task_id: uuid.UUID, db: DatabaseSession) -> RunListResponse:
    try:
        items, total = RunService(db).list_runs(task_id)
    except RunServiceError as exc:
        _raise_service_error(exc)
    return RunListResponse(items=[RunResponse.model_validate(item) for item in items], total=total)


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    responses=STANDARD_ERRORS,
    summary="Get a durable Run",
)
def get_run(run_id: uuid.UUID, db: DatabaseSession) -> Run:
    try:
        return RunService(db).get_run(run_id)
    except RunServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/runs/{run_id}/snapshot",
    response_model=SnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": SnapshotResponse, "description": "Idempotent replay"},
        **STANDARD_ERRORS,
    },
    summary="Create one immutable committed-HEAD Snapshot",
)
def create_snapshot(
    run_id: uuid.UUID, request: Request, response: Response, db: DatabaseSession
) -> RepositorySnapshot:
    try:
        snapshot, replay = RunService(db).create_snapshot(run_id, request_id=_request_id(request))
    except RunServiceError as exc:
        _raise_service_error(exc)
    if replay:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return snapshot


@router.get(
    "/runs/{run_id}/snapshot",
    response_model=SnapshotResponse,
    responses=STANDARD_ERRORS,
    summary="Get the immutable committed-HEAD Snapshot",
)
def get_snapshot(run_id: uuid.UUID, db: DatabaseSession) -> RepositorySnapshot:
    try:
        return RunService(db).get_snapshot(run_id)
    except RunServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/runs/{run_id}/plans",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": PlanResponse, "description": "Idempotent replay"},
        **STANDARD_ERRORS,
    },
    summary="Create a deterministic policy Plan",
)
def create_plan(
    run_id: uuid.UUID,
    payload: PlanCreate,
    request: Request,
    response: Response,
    db: DatabaseSession,
) -> Plan:
    try:
        plan, replay = RunService(db).create_plan(
            run_id, payload.delivery_package, request_id=_request_id(request)
        )
    except RunServiceError as exc:
        _raise_service_error(exc)
    if replay:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return plan


@router.get(
    "/runs/{run_id}/plans",
    response_model=PlanListResponse,
    responses=STANDARD_ERRORS,
    summary="List Plan versions newest first",
)
def list_plans(run_id: uuid.UUID, db: DatabaseSession) -> PlanListResponse:
    try:
        items, total = RunService(db).list_plans(run_id)
    except RunServiceError as exc:
        _raise_service_error(exc)
    return PlanListResponse(
        items=[PlanResponse.model_validate(item) for item in items], total=total
    )


@router.get(
    "/runs/{run_id}/plans/{version}",
    response_model=PlanResponse,
    responses=STANDARD_ERRORS,
    summary="Get a Plan version",
)
def get_plan(run_id: uuid.UUID, version: PlanVersion, db: DatabaseSession) -> Plan:
    try:
        return RunService(db).get_plan(run_id, version)
    except RunServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/runs/{run_id}/plans/{version}/revisions",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    responses=STANDARD_ERRORS,
    summary="Create a bounded deterministic Plan revision",
)
def revise_plan(
    run_id: uuid.UUID,
    version: PlanVersion,
    payload: PlanRevisionCreate,
    request: Request,
    db: DatabaseSession,
) -> Plan:
    try:
        return RunService(db).revise_plan(run_id, version, payload, request_id=_request_id(request))
    except RunServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/runs/{run_id}/plans/{version}/submit",
    response_model=PlanResponse,
    responses=STANDARD_ERRORS,
    summary="Submit the latest Plan for human approval",
)
def submit_plan(
    run_id: uuid.UUID, version: PlanVersion, request: Request, db: DatabaseSession
) -> Plan:
    try:
        return RunService(db).submit_plan(run_id, version, request_id=_request_id(request))
    except RunServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/runs/{run_id}/plans/{version}/decisions",
    response_model=ApprovalDecisionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": ApprovalDecisionResponse, "description": "Idempotent replay"},
        **STANDARD_ERRORS,
    },
    summary="Approve or reject the latest awaiting Plan without executing code",
)
def decide_plan(
    run_id: uuid.UUID,
    version: PlanVersion,
    payload: PlanDecisionCreate,
    request: Request,
    response: Response,
    db: DatabaseSession,
) -> ApprovalDecision:
    try:
        decision, replay = RunService(db).decide_plan(
            run_id, version, payload, request_id=_request_id(request)
        )
    except RunServiceError as exc:
        _raise_service_error(exc)
    if replay:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return decision


@router.get(
    "/runs/{run_id}/audit-events",
    response_model=AuditEventListResponse,
    responses=STANDARD_ERRORS,
    summary="List sanitized governance Audit Events",
)
def list_audit_events(run_id: uuid.UUID, db: DatabaseSession) -> AuditEventListResponse:
    try:
        items, total = RunService(db).list_audit_events(run_id)
    except RunServiceError as exc:
        _raise_service_error(exc)
    return AuditEventListResponse(
        items=[AuditEventResponse.model_validate(item) for item in items],
        total=total,
    )


@router.post(
    "/runs/{run_id}/cancel",
    response_model=RunResponse,
    responses=STANDARD_ERRORS,
    summary="Cancel a non-terminal Phase 2 Run",
)
def cancel_run(
    run_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
    payload: RunCancelCreate | None = None,
) -> Run:
    body = payload or RunCancelCreate()
    try:
        return RunService(db).cancel_run(
            run_id,
            request_id=_request_id(request),
            reason_provided=body.reason is not None,
        )
    except RunServiceError as exc:
        _raise_service_error(exc)
