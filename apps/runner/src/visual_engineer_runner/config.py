from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunnerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RUNNER_",
        env_file=".env.runner.local",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    control_plane_url: str = "http://api:8000"
    bootstrap_token: SecretStr = SecretStr("")
    display_name: str = Field(default="Local Runner", min_length=1, max_length=120)
    software_version: str = Field(default="0.3.0", pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
    credential_path: Path = Path("/var/lib/visual-engineer-runner/credentials.json")
    heartbeat_interval_seconds: float = Field(default=3.0, ge=0.5, le=60)
    poll_interval_seconds: float = Field(default=0.5, ge=0.1, le=10)
    request_timeout_seconds: float = Field(default=10.0, ge=1, le=60)
    backoff_initial_seconds: float = Field(default=0.5, ge=0.1, le=10)
    backoff_max_seconds: float = Field(default=10.0, ge=1, le=60)
    log_level: str = "INFO"

    @field_validator("control_plane_url")
    @classmethod
    def validate_control_plane_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("RUNNER_CONTROL_PLANE_URL must be an HTTP(S) origin")
        return normalized

    @field_validator("credential_path")
    @classmethod
    def require_absolute_credential_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("RUNNER_CREDENTIAL_PATH must be absolute")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("RUNNER_LOG_LEVEL is invalid")
        return normalized
