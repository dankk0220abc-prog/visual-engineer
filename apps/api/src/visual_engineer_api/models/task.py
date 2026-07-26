import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from visual_engineer_api.db.base import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("char_length(title) BETWEEN 1 AND 120", name="ck_tasks_title_length"),
        CheckConstraint(
            "char_length(objective) BETWEEN 1 AND 4000", name="ck_tasks_objective_length"
        ),
        CheckConstraint(
            "repository_kind IN ('local_path', 'github')", name="ck_tasks_repository_kind"
        ),
        CheckConstraint(
            "char_length(repository_display_name) BETWEEN 1 AND 120",
            name="ck_tasks_repository_display_name_length",
        ),
        CheckConstraint(
            "char_length(repository_locator) BETWEEN 1 AND 1024",
            name="ck_tasks_repository_locator_length",
        ),
        CheckConstraint("status IN ('draft')", name="ck_tasks_status"),
        CheckConstraint("version >= 1", name="ck_tasks_version"),
        Index("ix_tasks_created_at", "created_at"),
        Index("ix_tasks_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(120))
    objective: Mapped[str] = mapped_column(String(4000))
    repository_kind: Mapped[str] = mapped_column(String(32))
    repository_display_name: Mapped[str] = mapped_column(String(120))
    repository_locator: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="draft", server_default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    idempotency_request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
