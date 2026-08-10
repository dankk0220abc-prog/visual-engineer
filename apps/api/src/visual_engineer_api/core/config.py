import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://visualengineer:visualengineer-local@localhost:5432/visualengineer"
)


def validate_database_url(value: str) -> str:
    if not value.startswith("postgresql+psycopg://"):
        raise ValueError("DATABASE_URL must use postgresql+psycopg")
    return value


class Settings(BaseModel):
    """Typed configuration loaded from environment variables or safe local defaults."""

    model_config = ConfigDict(extra="ignore")

    database_url: str = DEFAULT_DATABASE_URL
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    web_origin: str = "http://localhost:3000,http://127.0.0.1:3000"
    log_level: str = "INFO"
    read_only_repository_roots: str = "/repositories"
    repository_scan_max_files: int = Field(default=5000, ge=1, le=100_000)
    repository_scan_max_selected_files: int = Field(default=250, ge=1, le=5000)
    repository_scan_max_file_bytes: int = Field(default=256 * 1024, ge=1024, le=10 * 1024 * 1024)
    repository_scan_max_total_bytes: int = Field(
        default=5 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024
    )
    repository_scan_timeout_seconds: float = Field(default=20.0, ge=0.1, le=120.0)
    repository_dirty_path_limit: int = Field(default=200, ge=1, le=5000)
    ai_plan_context_max_bytes: int = Field(default=16 * 1024, ge=1024, le=256 * 1024)
    ai_plan_context_max_references: int = Field(default=64, ge=1, le=500)
    ai_provider_timeout_seconds: float = Field(default=2.0, ge=0.05, le=30.0)
    byok_credential_ttl_seconds: int = Field(default=3600, ge=60, le=86_400)
    byok_max_sessions: int = Field(default=128, ge=1, le=10_000)
    runner_bootstrap_token: SecretStr = SecretStr("")
    runner_online_threshold_seconds: int = Field(default=15, ge=3, le=300)
    runner_lease_seconds: int = Field(default=6, ge=2, le=60)
    runner_job_max_attempts: int = Field(default=2, ge=1, le=5)
    runner_max_result_bytes: int = Field(default=8192, ge=256, le=65_536)
    runner_envelope_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    side_effect_permit_ttl_seconds: int = Field(default=5, ge=1, le=10)
    side_effect_permit_safety_seconds: int = Field(default=1, ge=1, le=5)
    delivery_authorization_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    runner_reaper_interval_seconds: float = Field(default=1.0, ge=0.25, le=30)
    runner_reaper_enabled: bool = True

    @field_validator("database_url")
    @classmethod
    def require_postgresql_psycopg(cls, value: str) -> str:
        return validate_database_url(value)

    @field_validator("web_origin")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        if not origins or any(not origin.startswith(("http://", "https://")) for origin in origins):
            raise ValueError("WEB_ORIGIN must contain comma-separated HTTP(S) origins")
        return ",".join(origins)

    @property
    def cors_origins(self) -> list[str]:
        return self.web_origin.split(",")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL is invalid")
        return normalized

    @field_validator("read_only_repository_roots")
    @classmethod
    def validate_repository_roots(cls, value: str) -> str:
        roots = [item.strip() for item in value.split(os.pathsep) if item.strip()]
        if not roots:
            raise ValueError("READ_ONLY_REPOSITORY_ROOTS must contain at least one path")
        for root in roots:
            if "\x00" in root or not Path(root).expanduser().is_absolute():
                raise ValueError("READ_ONLY_REPOSITORY_ROOTS must contain absolute paths")
        return os.pathsep.join(roots)

    @property
    def repository_roots(self) -> tuple[Path, ...]:
        return tuple(
            Path(root).expanduser().resolve(strict=False)
            for root in self.read_only_repository_roots.split(os.pathsep)
        )


@lru_cache
def get_settings() -> Settings:
    values: dict[str, Any] = {}
    for field_name in Settings.model_fields:
        value = os.environ.get(field_name.upper())
        if value is not None:
            values[field_name] = value
    return Settings.model_validate(values)
