import uuid
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.schemas.workspace import (
    EligibleExecutionContextListResponse,
    ExecutionGrantCreate,
    ExecutionGrantDecisionCreate,
    ExecutionGrantListResponse,
    ExecutionGrantResponse,
    RepositoryHandleListResponse,
    RepositoryHandleResponse,
    WorkspaceActionResponse,
    WorkspaceCheckpointListResponse,
    WorkspaceCreate,
    WorkspaceEventListResponse,
    WorkspaceEventResponse,
    WorkspaceListAction,
    WorkspaceListResponse,
    WorkspaceReadTextAction,
    WorkspaceResponse,
    WorkspaceWriteTextAction,
)
from visual_engineer_api.services.runner import RunnerServiceError
from visual_engineer_api.services.workspace import (
    WorkspaceService,
    WorkspaceServiceError,
)

router = APIRouter(prefix="/api/v1", tags=["isolated workspaces"])
DatabaseSession = Annotated[Session, Depends(get_db)]

WORKSPACE_ERRORS: dict[int | str, dict[str, Any]] = {
    403: {"model": ErrorResponse, "description": "Revoked Runner or Handle"},
    404: {"model": ErrorResponse, "description": "Workspace entity not found"},
    409: {"model": ErrorResponse, "description": "State, hash, or idempotency conflict"},
    422: {"model": ErrorResponse, "description": "Execution policy denied the action"},
}


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else str(uuid.uuid4())


def _raise_service_error(
    error: WorkspaceServiceError | RunnerServiceError,
) -> NoReturn:
    status_code = {
        "forbidden": status.HTTP_403_FORBIDDEN,
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
    "/repositories",
    response_model=RepositoryHandleListResponse,
    responses=WORKSPACE_ERRORS,
    summary="List Runner-registered opaque Repository Handles",
)
def list_repositories(db: DatabaseSession) -> RepositoryHandleListResponse:
    items = WorkspaceService(db).list_repositories()
    return RepositoryHandleListResponse(items=items, total=len(items))


@router.get(
    "/repositories/{repository_id}",
    response_model=RepositoryHandleResponse,
    responses=WORKSPACE_ERRORS,
    summary="Get a Repository Handle without a Runner host path",
)
def get_repository(repository_id: uuid.UUID, db: DatabaseSession) -> RepositoryHandleResponse:
    try:
        return WorkspaceService(db).get_repository(repository_id)
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.get(
    "/execution-grants/eligible-contexts",
    response_model=EligibleExecutionContextListResponse,
    responses=WORKSPACE_ERRORS,
    summary="List approved non-stale Plan and Repository contexts",
)
def list_eligible_execution_contexts(
    db: DatabaseSession,
) -> EligibleExecutionContextListResponse:
    items = WorkspaceService(db).list_eligible_contexts()
    return EligibleExecutionContextListResponse(items=items, total=len(items))


@router.get(
    "/execution-grants",
    response_model=ExecutionGrantListResponse,
    responses=WORKSPACE_ERRORS,
    summary="List immutable Execution Grants",
)
def list_execution_grants(db: DatabaseSession) -> ExecutionGrantListResponse:
    items = WorkspaceService(db).list_grants()
    return ExecutionGrantListResponse(items=items, total=len(items))


@router.post(
    "/execution-grants",
    response_model=ExecutionGrantResponse,
    status_code=status.HTTP_201_CREATED,
    responses=WORKSPACE_ERRORS,
    summary="Derive a pending narrow Grant from an approved current Plan",
)
def create_execution_grant(
    payload: ExecutionGrantCreate,
    request: Request,
    db: DatabaseSession,
) -> ExecutionGrantResponse:
    try:
        return WorkspaceService(db).create_grant(payload, request_id=_request_id(request))
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.get(
    "/execution-grants/{grant_id}",
    response_model=ExecutionGrantResponse,
    responses=WORKSPACE_ERRORS,
    summary="Get one immutable Execution Grant and its decision",
)
def get_execution_grant(grant_id: uuid.UUID, db: DatabaseSession) -> ExecutionGrantResponse:
    try:
        return WorkspaceService(db).get_grant(grant_id)
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/execution-grants/{grant_id}/decisions",
    response_model=ExecutionGrantResponse,
    responses=WORKSPACE_ERRORS,
    summary="Independently approve or reason-reject a pending Grant",
)
def decide_execution_grant(
    grant_id: uuid.UUID,
    payload: ExecutionGrantDecisionCreate,
    request: Request,
    db: DatabaseSession,
) -> ExecutionGrantResponse:
    try:
        return WorkspaceService(db).decide_grant(
            grant_id,
            payload,
            request_id=_request_id(request),
        )
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/execution-grants/{grant_id}/revoke",
    response_model=ExecutionGrantResponse,
    responses=WORKSPACE_ERRORS,
    summary="Revoke a pending or approved Execution Grant",
)
def revoke_execution_grant(
    grant_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> ExecutionGrantResponse:
    try:
        return WorkspaceService(db).revoke_grant(grant_id, request_id=_request_id(request))
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.get(
    "/workspaces",
    response_model=WorkspaceListResponse,
    responses=WORKSPACE_ERRORS,
    summary="List isolated Runner-owned Workspaces",
)
def list_workspaces(db: DatabaseSession) -> WorkspaceListResponse:
    items = WorkspaceService(db).list_workspaces()
    return WorkspaceListResponse(items=items, total=len(items))


@router.post(
    "/workspaces",
    response_model=WorkspaceActionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=WORKSPACE_ERRORS,
    summary="Request an exact-revision Runner-owned isolated Workspace",
)
def create_workspace(
    payload: WorkspaceCreate,
    request: Request,
    db: DatabaseSession,
) -> WorkspaceActionResponse:
    try:
        return WorkspaceService(db).create_workspace(payload, request_id=_request_id(request))
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceResponse,
    responses=WORKSPACE_ERRORS,
    summary="Get Workspace state without exposing its Runner path",
)
def get_workspace(workspace_id: uuid.UUID, db: DatabaseSession) -> WorkspaceResponse:
    try:
        return WorkspaceService(db).get_workspace(workspace_id)
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/workspaces/{workspace_id}/actions/list",
    response_model=WorkspaceActionResponse,
    responses=WORKSPACE_ERRORS,
)
def list_workspace_directory(
    workspace_id: uuid.UUID,
    payload: WorkspaceListAction,
    request: Request,
    db: DatabaseSession,
) -> WorkspaceActionResponse:
    try:
        return WorkspaceService(db).list_action(
            workspace_id, payload, request_id=_request_id(request)
        )
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/workspaces/{workspace_id}/actions/read-text",
    response_model=WorkspaceActionResponse,
    responses=WORKSPACE_ERRORS,
)
def read_workspace_text(
    workspace_id: uuid.UUID,
    payload: WorkspaceReadTextAction,
    request: Request,
    db: DatabaseSession,
) -> WorkspaceActionResponse:
    try:
        return WorkspaceService(db).read_action(
            workspace_id, payload, request_id=_request_id(request)
        )
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/workspaces/{workspace_id}/actions/write-text",
    response_model=WorkspaceActionResponse,
    responses=WORKSPACE_ERRORS,
)
def write_workspace_text(
    workspace_id: uuid.UUID,
    payload: WorkspaceWriteTextAction,
    request: Request,
    db: DatabaseSession,
) -> WorkspaceActionResponse:
    try:
        return WorkspaceService(db).write_action(
            workspace_id, payload, request_id=_request_id(request)
        )
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/workspaces/{workspace_id}/actions/status",
    response_model=WorkspaceActionResponse,
    responses=WORKSPACE_ERRORS,
)
def workspace_status(
    workspace_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> WorkspaceActionResponse:
    try:
        return WorkspaceService(db).status_action(workspace_id, request_id=_request_id(request))
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/workspaces/{workspace_id}/actions/diff",
    response_model=WorkspaceActionResponse,
    responses=WORKSPACE_ERRORS,
)
def workspace_diff(
    workspace_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> WorkspaceActionResponse:
    try:
        return WorkspaceService(db).diff_action(workspace_id, request_id=_request_id(request))
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/workspaces/{workspace_id}/actions/rollback",
    response_model=WorkspaceActionResponse,
    responses=WORKSPACE_ERRORS,
)
def workspace_rollback(
    workspace_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> WorkspaceActionResponse:
    try:
        return WorkspaceService(db).rollback_action(workspace_id, request_id=_request_id(request))
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.post(
    "/workspaces/{workspace_id}/actions/discard",
    response_model=WorkspaceActionResponse,
    responses=WORKSPACE_ERRORS,
)
def workspace_discard(
    workspace_id: uuid.UUID,
    request: Request,
    db: DatabaseSession,
) -> WorkspaceActionResponse:
    try:
        return WorkspaceService(db).discard_action(workspace_id, request_id=_request_id(request))
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)


@router.get(
    "/workspaces/{workspace_id}/events",
    response_model=WorkspaceEventListResponse,
    responses=WORKSPACE_ERRORS,
)
def list_workspace_events(
    workspace_id: uuid.UUID, db: DatabaseSession
) -> WorkspaceEventListResponse:
    try:
        events = WorkspaceService(db).list_events(workspace_id)
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)
    items = [WorkspaceEventResponse.model_validate(item) for item in events]
    return WorkspaceEventListResponse(items=items, total=len(items))


@router.get(
    "/workspaces/{workspace_id}/checkpoints",
    response_model=WorkspaceCheckpointListResponse,
    responses=WORKSPACE_ERRORS,
)
def list_workspace_checkpoints(
    workspace_id: uuid.UUID, db: DatabaseSession
) -> WorkspaceCheckpointListResponse:
    try:
        items = WorkspaceService(db).list_checkpoints(workspace_id)
    except (WorkspaceServiceError, RunnerServiceError) as exc:
        _raise_service_error(exc)
    return WorkspaceCheckpointListResponse(items=items, total=len(items))
