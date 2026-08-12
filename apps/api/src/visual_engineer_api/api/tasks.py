import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.repositories.task import TaskRepository
from visual_engineer_api.schemas.error import ErrorResponse
from visual_engineer_api.schemas.task import TaskCreate, TaskListResponse, TaskResponse
from visual_engineer_api.services.task import (
    IdempotencyConflictError,
    TaskService,
    task_response,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def normalize_idempotency_key(value: str) -> str:
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


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"model": TaskResponse, "description": "Idempotent replay"},
        409: {"model": ErrorResponse, "description": "Idempotency key conflict"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
    },
    summary="Create a draft task without accessing its repository",
)
def create_task(
    payload: TaskCreate,
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    db: DatabaseSession,
) -> TaskResponse:
    key = normalize_idempotency_key(idempotency_key)
    try:
        task, replay = TaskService(db).create(payload, key)
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_conflict",
                "message": "Idempotency-Key is already associated with a different request",
            },
        ) from exc
    if replay:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return task_response(task)


@router.get(
    "",
    response_model=TaskListResponse,
    responses={422: {"model": ErrorResponse, "description": "Invalid pagination"}},
    summary="List tasks newest first",
)
def list_tasks(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> TaskListResponse:
    tasks, total = TaskRepository(db).list(limit=limit, offset=offset)
    return TaskListResponse(
        items=[task_response(task) for task in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Task not found"},
        422: {"model": ErrorResponse, "description": "Invalid task ID"},
    },
    summary="Get a task by ID",
)
def get_task(task_id: uuid.UUID, db: DatabaseSession) -> TaskResponse:
    task = TaskRepository(db).get_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": "Task was not found"},
        )
    return task_response(task)
