import json
import os
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class RunnerCredential(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runner_id: uuid.UUID
    token: SecretStr = Field(repr=False)
    protocol_version: int = Field(ge=1, le=1)


class CredentialStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> RunnerCredential | None:
        try:
            descriptor = os.open(self._path, os.O_RDONLY)
        except FileNotFoundError:
            return None
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            payload = handle.read(4097)
        if len(payload.encode("utf-8")) > 4096:
            raise ValueError("Runner credential file exceeds its size limit")
        return RunnerCredential.model_validate_json(payload)

    def save(self, credential: RunnerCredential) -> None:
        self._path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        payload = json.dumps(
            {
                "runner_id": str(credential.runner_id),
                "token": credential.token.get_secret_value(),
                "protocol_version": credential.protocol_version,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, self._path)
        os.chmod(self._path, 0o600)

    def clear(self) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            return
