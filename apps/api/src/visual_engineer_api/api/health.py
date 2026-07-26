from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from visual_engineer_api.db.session import get_db
from visual_engineer_api.schemas.error import ErrorResponse

router = APIRouter(prefix="/health", tags=["health"])
DatabaseSession = Annotated[Session, Depends(get_db)]


class HealthResponse(BaseModel):
    status: str


@router.get("/live", response_model=HealthResponse, summary="Process liveness")
def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={503: {"model": ErrorResponse, "description": "Database is unavailable"}},
    summary="Database readiness",
)
def readiness(db: DatabaseSession) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "database_not_ready", "message": "Database is unavailable"},
        ) from exc
    return HealthResponse(status="ready")
