import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed configuration loaded from environment variables or safe local defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str = (
        "postgresql+psycopg://visualengineer:visualengineer-local@localhost:5432/visualengineer"
    )
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
    runner_bootstrap_token: SecretStr = SecretStr("")
    runner_online_threshold_seconds: int = Field(default=15, ge=3, le=300)
    runner_lease_seconds: int = Field(default=6, ge=2, le=60)
    runner_job_max_attempts: int = Field(default=2, ge=1, le=5)
    runner_max_result_bytes: int = Field(default=8192, ge=256, le=65_536)
    runner_envelope_ttl_seconds: int = Field(default=300, ge=30, le=3600)
    side_effect_permit_ttl_seconds: int = Field(default=5, ge=1, le=10)
    side_effect_permit_safety_seconds: int = Field(default=1, ge=1, le=5)
    runner_reaper_interval_seconds: float = Field(default=1.0, ge=0.25, le=30)
    runner_reaper_enabled: bool = True

    @field_validator("database_url")
    @classmethod
    def require_postgresql_psycopg(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value

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
    return Settings()
