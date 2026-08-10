import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RepositoryKind(StrEnum):
    LOCAL_PATH = "local_path"
    GITHUB = "github"


class TaskStatus(StrEnum):
    DRAFT = "draft"


class TaskClassification(StrEnum):
    USER = "user"
    DEMO = "demo"
    SYSTEM_VALIDATION = "system_validation"
    SECURITY_TEST = "security_test"
    FIXTURE = "fixture"
    LIVE_CANARY = "live_canary"


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=4000)
    repository_kind: RepositoryKind
    repository_display_name: str = Field(min_length=1, max_length=120)
    repository_locator: str = Field(min_length=1, max_length=1024)
    classification: Literal[TaskClassification.USER, TaskClassification.DEMO] = (
        TaskClassification.USER
    )

    @field_validator("title", "objective", "repository_display_name", "repository_locator")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("NUL characters are not allowed")
        normalized = value.strip()
        if not normalized:
            raise ValueError("must not be blank")
        return normalized


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    objective: str
    repository_kind: RepositoryKind
    repository_display_name: str
    repository_locator: str
    status: TaskStatus
    classification: TaskClassification
    content_redacted: bool
    version: int
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int
