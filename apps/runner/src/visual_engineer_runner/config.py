import re
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalRepositoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: Path
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("path")
    @classmethod
    def require_absolute_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("Runner repository paths must be absolute")
        return value


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
    software_version: str = Field(default="0.5.0", pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
    credential_path: Path = Path("/var/lib/visual-engineer-runner/credentials.json")
    ownership_key_path: Path = Path("/var/lib/visual-engineer-runner/ownership.key")
    repository_handles: dict[str, LocalRepositoryConfig] = Field(default_factory=dict)
    mirror_root: Path = Path("/var/lib/visual-engineer-runner/mirrors")
    workspace_root: Path = Path("/var/lib/visual-engineer-runner/workspaces")
    registry_root: Path = Path("/var/lib/visual-engineer-runner/registry")
    validation_root: Path = Path("/var/lib/visual-engineer-runner/validations")
    require_source_read_only: bool = True
    git_timeout_seconds: float = Field(default=15.0, ge=1, le=60)
    git_max_output_bytes: int = Field(default=1024 * 1024, ge=4096, le=8 * 1024 * 1024)
    mirror_max_object_files: int = Field(default=200_000, ge=1, le=1_000_000)
    mirror_max_object_bytes: int = Field(
        default=1024 * 1024 * 1024,
        ge=1024,
        le=10 * 1024 * 1024 * 1024,
    )
    mirror_max_single_object_bytes: int = Field(
        default=64 * 1024 * 1024,
        ge=1024,
        le=1024 * 1024 * 1024,
    )
    mirror_max_pack_files: int = Field(default=256, ge=1, le=4096)
    mirror_max_delta_depth: int = Field(default=64, ge=1, le=128)
    mirror_max_tree_depth: int = Field(default=64, ge=1, le=256)
    mirror_max_tree_entries: int = Field(default=1_000_000, ge=1, le=10_000_000)
    mirror_max_object_references: int = Field(default=2_000_000, ge=1, le=20_000_000)
    mirror_max_graph_depth: int = Field(default=50_000, ge=1, le=1_000_000)
    git_termination_grace_seconds: float = Field(default=0.5, ge=0.05, le=5)
    workspace_prepare_delay_ms: int = Field(default=0, ge=0, le=10_000)
    workspace_write_commit_delay_ms: int = Field(default=0, ge=0, le=10_000)
    workspace_write_post_commit_delay_ms: int = Field(default=0, ge=0, le=10_000)
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

    @field_validator(
        "credential_path",
        "ownership_key_path",
        "mirror_root",
        "workspace_root",
        "registry_root",
        "validation_root",
    )
    @classmethod
    def require_absolute_credential_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("Runner state paths must be absolute")
        return value

    @field_validator("repository_handles")
    @classmethod
    def validate_repository_handles(
        cls, value: dict[str, LocalRepositoryConfig]
    ) -> dict[str, LocalRepositoryConfig]:
        pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,119}$")
        if len(value) > 16:
            raise ValueError("At most 16 local Repository Handles are supported")
        if any(pattern.fullmatch(handle) is None for handle in value):
            raise ValueError("Runner Repository Handle is invalid")
        paths = [str(item.path) for item in value.values()]
        if len(paths) != len(set(paths)):
            raise ValueError("Runner Repository Handle paths must be unique")
        return value

    @model_validator(mode="after")
    def require_distinct_state_roots(self) -> "RunnerSettings":
        if "ownership_key_path" not in self.model_fields_set:
            object.__setattr__(
                self,
                "ownership_key_path",
                self.credential_path.parent / "ownership.key",
            )
        roots = {
            str(self.mirror_root),
            str(self.workspace_root),
            str(self.registry_root),
            str(self.validation_root),
        }
        if len(roots) != 4:
            raise ValueError(
                "Runner mirror, workspace, registry, and validation roots must be distinct"
            )
        state_roots = (
            self.mirror_root,
            self.workspace_root,
            self.registry_root,
            self.validation_root,
        )
        for index, root in enumerate(state_roots):
            for other in state_roots[index + 1 :]:
                if root.is_relative_to(other) or other.is_relative_to(root):
                    raise ValueError("Runner state roots must not contain one another")
        if self.credential_path == self.ownership_key_path:
            raise ValueError("Runner credential and ownership key paths must be distinct")
        if self.credential_path.parent != self.ownership_key_path.parent:
            raise ValueError("Runner ownership key must share the credential volume")
        return self

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("RUNNER_LOG_LEVEL is invalid")
        return normalized
