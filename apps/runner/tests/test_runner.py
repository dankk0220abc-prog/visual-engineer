import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import httpx
import pytest
from pydantic import SecretStr

from visual_engineer_runner.client import ControlPlaneClient, ControlPlaneError
from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.credentials import CredentialStore, RunnerCredential
from visual_engineer_runner.evidence import PermissionEnvelopeDeniedError, validate_assignment
from visual_engineer_runner.executor import execute_job
from visual_engineer_runner.lifecycle import CAPABILITIES, RunnerLifecycle
from visual_engineer_runner_protocol import (
    Capability,
    ClaimRequest,
    ClaimResponse,
    ControlledWaitJobSpec,
    DiagnosticResult,
    HeartbeatRequest,
    HeartbeatResponse,
    JobAssignment,
    PermissionEnvelope,
    RegisterResponse,
    RunnerStatus,
    SystemDiagnosticJobSpec,
    compute_permission_policy_hash,
)


def assignment(
    *,
    job: SystemDiagnosticJobSpec | ControlledWaitJobSpec | None = None,
    expires_delta: timedelta = timedelta(minutes=5),
) -> JobAssignment:
    job_id = uuid.uuid4()
    envelope_id = uuid.uuid4()
    now = datetime.now(UTC)
    issued = now - timedelta(minutes=10) if expires_delta.total_seconds() < 0 else now
    selected = job or SystemDiagnosticJobSpec()
    values = {
        "id": envelope_id,
        "job_id": job_id,
        "allowed_capabilities": [selected.kind.value],
        "max_runtime_seconds": 20,
        "lease_seconds": 6,
        "max_attempts": 2,
        "max_result_bytes": 8192,
        "issued_at": issued,
        "expires_at": (
            now + expires_delta if expires_delta.total_seconds() < 0 else issued + expires_delta
        ),
        "policy_hash": "0" * 64,
    }
    draft = PermissionEnvelope.model_validate(values)
    values["policy_hash"] = compute_permission_policy_hash(draft)
    envelope = PermissionEnvelope.model_validate(values)
    return JobAssignment(
        job_id=job_id,
        attempt_id=uuid.uuid4(),
        lease_id=uuid.uuid4(),
        attempt_number=1,
        job=selected,
        permission_envelope=envelope,
        leased_until=issued + timedelta(seconds=6),
    )


def settings(path: Path, bootstrap: str = "dynamic-" + "x" * 48) -> RunnerSettings:
    return RunnerSettings(
        control_plane_url="http://control-plane.test",
        bootstrap_token=SecretStr(bootstrap),
        credential_path=path,
        heartbeat_interval_seconds=1,
        poll_interval_seconds=0.1,
        backoff_initial_seconds=0.1,
        backoff_max_seconds=1,
    )


def test_credential_persistence_restart_and_restrictive_mode(tmp_path: Path) -> None:
    path = tmp_path / "runner" / "credentials.json"
    store = CredentialStore(path)
    assert store.load() is None
    credential = RunnerCredential(
        runner_id=uuid.uuid4(),
        token=SecretStr("dynamic-" + "t" * 48),
        protocol_version=1,
    )
    store.save(credential)

    loaded = CredentialStore(path).load()
    assert loaded is not None
    assert loaded.runner_id == credential.runner_id
    assert loaded.token.get_secret_value() == credential.token.get_secret_value()
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert "SecretStr" not in path.read_text(encoding="utf-8")
    store.clear()
    assert store.load() is None


def test_assignment_validation_denies_hash_expiry_and_capability() -> None:
    safe = assignment()
    validate_assignment(safe)

    tampered_envelope = safe.permission_envelope.model_copy(update={"policy_hash": "f" * 64})
    with pytest.raises(PermissionEnvelopeDeniedError) as hash_error:
        validate_assignment(safe.model_copy(update={"permission_envelope": tampered_envelope}))
    assert hash_error.value.code == "envelope_hash_mismatch"

    expired = assignment(expires_delta=timedelta(seconds=-1))
    with pytest.raises(PermissionEnvelopeDeniedError) as expiry_error:
        validate_assignment(expired)
    assert expiry_error.value.code == "envelope_expired"

    unsupported = safe.permission_envelope.model_copy(
        update={"allowed_capabilities": [Capability.CONTROLLED_WAIT_V1]}
    )
    unsupported = unsupported.model_copy(
        update={"policy_hash": compute_permission_policy_hash(unsupported)}
    )
    with pytest.raises(PermissionEnvelopeDeniedError) as capability_error:
        validate_assignment(safe.model_copy(update={"permission_envelope": unsupported}))
    assert capability_error.value.code == "unsupported_capability"


def test_typed_executors_return_only_bounded_results_and_cancel_gracefully() -> None:
    diagnostic = asyncio.run(
        execute_job(
            SystemDiagnosticJobSpec(),
            software_version="0.3.0",
            capabilities=CAPABILITIES,
        )
    )
    assert isinstance(diagnostic, DiagnosticResult)
    payload = diagnostic.model_dump(mode="json")
    assert set(payload) == {
        "kind",
        "runner_software_version",
        "protocol_version",
        "python_version",
        "os_family",
        "architecture",
        "capability_list",
        "started_at",
        "completed_at",
        "duration_ms",
    }
    assert not {"hostname", "username", "ip", "environment", "path"} & set(payload)

    async def cancel_wait() -> None:
        execution = asyncio.create_task(
            execute_job(
                ControlledWaitJobSpec(duration_ms=10_000),
                software_version="0.3.0",
                capabilities=CAPABILITIES,
            )
        )
        await asyncio.sleep(0.02)
        execution.cancel()
        with pytest.raises(asyncio.CancelledError):
            await execution

    asyncio.run(cancel_wait())


class RegistrationClient:
    def __init__(self) -> None:
        self.register_calls = 0
        self.runner_id = uuid.uuid4()
        self.token = "dynamic-" + "r" * 48

    async def register(self, _: object, bootstrap: SecretStr) -> RegisterResponse:
        assert bootstrap.get_secret_value().startswith("dynamic-")
        self.register_calls += 1
        return RegisterResponse(
            runner_id=self.runner_id,
            runner_token=self.token,
            registered_at=datetime.now(UTC),
        )


def test_first_registration_then_existing_credential_restart(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path = tmp_path / "credentials.json"
    fake = RegistrationClient()
    lifecycle = RunnerLifecycle(
        settings(path),
        cast(ControlPlaneClient, fake),
        CredentialStore(path),
    )
    with caplog.at_level(logging.INFO):
        first = asyncio.run(lifecycle._ensure_credential())
    assert first.runner_id == fake.runner_id
    assert fake.register_calls == 1
    assert fake.token not in caplog.text

    restarted = RunnerLifecycle(
        settings(path),
        cast(ControlPlaneClient, fake),
        CredentialStore(path),
    )
    second = asyncio.run(restarted._ensure_credential())
    assert second.runner_id == first.runner_id
    assert fake.register_calls == 1


def test_control_plane_client_uses_bearer_without_exposing_it() -> None:
    token = "dynamic-" + "a" * 48
    runner_id = uuid.uuid4()

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {token}"
        assert request.headers["x-request-id"]
        payload = json.loads(request.content)
        assert payload["runner_id"] == str(runner_id)
        return httpx.Response(
            200,
            json={
                "runner_id": str(runner_id),
                "status": "online",
                "server_time": datetime.now(UTC).isoformat(),
            },
        )

    async def exercise() -> HeartbeatResponse:
        client = ControlPlaneClient(
            "http://control-plane.test",
            timeout_seconds=1,
            transport=httpx.MockTransport(handler),
        )
        try:
            return await client.heartbeat(
                HeartbeatRequest(
                    runner_id=runner_id,
                    software_version="0.3.0",
                ),
                SecretStr(token),
            )
        finally:
            await client.close()

    response = asyncio.run(exercise())
    assert response.status == RunnerStatus.ONLINE
    assert token not in repr(response)


def test_transient_failure_and_protocol_failure_classification() -> None:
    assert ControlPlaneError(0, "control_plane_unavailable").transient is True
    assert ControlPlaneError(503, "unavailable").transient is True
    assert ControlPlaneError(409, "stale_lease").transient is False

    async def invalid_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'{"unexpected":true}')

    async def exercise() -> None:
        client = ControlPlaneClient(
            "http://control-plane.test",
            timeout_seconds=1,
            transport=httpx.MockTransport(invalid_handler),
        )
        try:
            with pytest.raises(ControlPlaneError) as error:
                await client.claim(
                    ClaimRequest(runner_id=uuid.uuid4()),
                    SecretStr("dynamic-" + "z" * 48),
                )
            assert error.value.code == "invalid_protocol_response"
        finally:
            await client.close()

    asyncio.run(exercise())


class StopAfterHeartbeatClient:
    def __init__(self, lifecycle: RunnerLifecycle | None = None) -> None:
        self.lifecycle = lifecycle

    async def heartbeat(self, payload: HeartbeatRequest, _: SecretStr) -> HeartbeatResponse:
        runner_id = payload.runner_id
        return HeartbeatResponse(
            runner_id=runner_id,
            status=RunnerStatus.ONLINE,
            server_time=datetime.now(UTC),
        )

    async def claim(self, payload: ClaimRequest, _: SecretStr) -> ClaimResponse:
        if self.lifecycle is not None:
            self.lifecycle.request_stop()
        return ClaimResponse(assignment=None, server_time=datetime.now(UTC))


def test_graceful_shutdown_after_heartbeat_and_empty_claim(tmp_path: Path) -> None:
    path = tmp_path / "credentials.json"
    store = CredentialStore(path)
    store.save(
        RunnerCredential(
            runner_id=uuid.uuid4(),
            token=SecretStr("dynamic-" + "g" * 48),
            protocol_version=1,
        )
    )
    fake = StopAfterHeartbeatClient()
    lifecycle = RunnerLifecycle(
        settings(path),
        cast(ControlPlaneClient, fake),
        store,
    )
    fake.lifecycle = lifecycle
    asyncio.run(asyncio.wait_for(lifecycle.run(), timeout=1))
