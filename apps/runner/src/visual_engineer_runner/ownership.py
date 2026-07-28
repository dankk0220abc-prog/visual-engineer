from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import stat
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner_protocol import FailureCode, canonical_json_bytes

_MAX_MANIFEST_BYTES = 16 * 1024
_KEY_BYTES = 32


class OwnershipError(Exception):
    def __init__(self, code: FailureCode) -> None:
        super().__init__(code.value)
        self.code = code


class WorkspaceOwnershipManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    workspace_id: uuid.UUID
    runner_id: uuid.UUID
    grant_id: uuid.UUID
    repository_handle_id: uuid.UUID
    repository_opaque_handle: str = Field(min_length=8, max_length=120)
    source_revision: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    policy_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    creation_nonce: str = Field(pattern=r"^[0-9a-f]{32}$")
    workspace_device: int = Field(ge=0)
    workspace_inode: int = Field(gt=0)
    signature: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorkspaceOwnershipStore:
    def __init__(self, settings: RunnerSettings) -> None:
        self._root = settings.registry_root
        self._key_path = settings.ownership_key_path
        self._key = self._load_or_create_key()

    def create(
        self,
        *,
        workspace_id: uuid.UUID,
        runner_id: uuid.UUID,
        grant_id: uuid.UUID,
        repository_handle_id: uuid.UUID,
        repository_opaque_handle: str,
        source_revision: str,
        policy_hash: str,
        creation_nonce: str,
        workspace_device: int,
        workspace_inode: int,
    ) -> WorkspaceOwnershipManifest:
        values: dict[str, object] = {
            "version": 1,
            "workspace_id": workspace_id,
            "runner_id": runner_id,
            "grant_id": grant_id,
            "repository_handle_id": repository_handle_id,
            "repository_opaque_handle": repository_opaque_handle,
            "source_revision": source_revision,
            "policy_hash": policy_hash,
            "creation_nonce": creation_nonce,
            "workspace_device": workspace_device,
            "workspace_inode": workspace_inode,
        }
        values["signature"] = self._signature(values)
        manifest = WorkspaceOwnershipManifest.model_validate(values)
        self._write_manifest(manifest)
        return manifest

    def load(self, workspace_id: uuid.UUID) -> WorkspaceOwnershipManifest:
        path = self.path(workspace_id)
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except FileNotFoundError as exc:
            raise OwnershipError(FailureCode.WORKSPACE_RECOVERY_REQUIRED) from exc
        except OSError as exc:
            raise OwnershipError(FailureCode.WORKSPACE_QUARANTINED) from exc
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_size > _MAX_MANIFEST_BYTES
            ):
                raise OwnershipError(FailureCode.WORKSPACE_QUARANTINED)
            payload = os.read(descriptor, metadata.st_size + 1)
        finally:
            os.close(descriptor)
        try:
            manifest = WorkspaceOwnershipManifest.model_validate_json(payload)
        except ValidationError as exc:
            raise OwnershipError(FailureCode.WORKSPACE_QUARANTINED) from exc
        values = manifest.model_dump(mode="json", exclude={"signature"})
        if not hmac.compare_digest(manifest.signature, self._signature(values)):
            raise OwnershipError(FailureCode.WORKSPACE_QUARANTINED)
        return manifest

    def path(self, workspace_id: uuid.UUID) -> Path:
        return self._root / f"workspace-{workspace_id.hex}.ownership.json"

    def sign_registry(self, values: dict[str, object]) -> str:
        return self._signature(values, domain=b"workspace-registry-v2")

    def registry_signature_matches(
        self,
        values: dict[str, object],
        signature: str,
    ) -> bool:
        return hmac.compare_digest(
            signature,
            self._signature(values, domain=b"workspace-registry-v2"),
        )

    def _load_or_create_key(self) -> bytes:
        parent = self._key_path.parent
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if parent.is_symlink() or not parent.is_dir():
            raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID)
        os.chmod(parent, 0o700)
        try:
            descriptor = os.open(
                self._key_path,
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            )
        except FileNotFoundError:
            return self._create_key()
        except OSError as exc:
            raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_size != _KEY_BYTES
            ):
                raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID)
            key = os.read(descriptor, _KEY_BYTES + 1)
        finally:
            os.close(descriptor)
        if len(key) != _KEY_BYTES:
            raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID)
        return key

    def _create_key(self) -> bytes:
        key = secrets.token_bytes(_KEY_BYTES)
        try:
            descriptor = os.open(
                self._key_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
        except FileExistsError:
            return self._load_or_create_key()
        except OSError as exc:
            raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        try:
            view = memoryview(key)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID)
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return key

    def _signature(
        self,
        values: dict[str, object],
        *,
        domain: bytes = b"workspace-ownership-v1",
    ) -> str:
        payload = domain + b"\0" + canonical_json_bytes(values)
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def _write_manifest(self, manifest: WorkspaceOwnershipManifest) -> None:
        payload = canonical_json_bytes(manifest)
        if len(payload) > _MAX_MANIFEST_BYTES:
            raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID)
        filename = self.path(manifest.workspace_id).name
        temporary = f".{filename}.{uuid.uuid4().hex}.tmp"
        root_descriptor = os.open(
            self._root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        )
        descriptor: int | None = None
        temporary_exists = False
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=root_descriptor,
            )
            temporary_exists = True
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID)
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.rename(
                temporary,
                filename,
                src_dir_fd=root_descriptor,
                dst_dir_fd=root_descriptor,
            )
            temporary_exists = False
            os.fsync(root_descriptor)
        except OSError as exc:
            raise OwnershipError(FailureCode.WORKSPACE_STATE_INVALID) from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary_exists:
                try:
                    os.unlink(temporary, dir_fd=root_descriptor)
                except FileNotFoundError:
                    pass
            os.close(root_descriptor)
