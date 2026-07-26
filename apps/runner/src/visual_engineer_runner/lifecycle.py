import asyncio
import logging
import random
import threading

from pydantic import SecretStr

from visual_engineer_runner.client import ControlPlaneClient, ControlPlaneError
from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.credentials import CredentialStore, RunnerCredential
from visual_engineer_runner.evidence import PermissionEnvelopeDeniedError, validate_assignment
from visual_engineer_runner.executor import execute_job
from visual_engineer_runner.workspace_manager import WorkspaceExecutionError, WorkspaceManager
from visual_engineer_runner_protocol import (
    RUNNER_PROTOCOL_VERSION,
    CancelledRequest,
    Capability,
    ClaimRequest,
    CompleteRequest,
    ControlledWaitJobSpec,
    FailRequest,
    FailureCode,
    HeartbeatRequest,
    JobAssignment,
    ProgressEventRequest,
    RegisterRequest,
    RenewRequest,
    StartRequest,
    WorkspaceBoundJobSpec,
)

LOGGER = logging.getLogger("visual_engineer_runner")
CAPABILITIES = [
    Capability.CONTROLLED_WAIT_V1,
    Capability.SYSTEM_DIAGNOSTIC_V1,
]
WORKSPACE_CAPABILITIES = [
    Capability.WORKSPACE_PREPARE_V1,
    Capability.WORKSPACE_LIST_V1,
    Capability.WORKSPACE_READ_TEXT_V1,
    Capability.WORKSPACE_WRITE_TEXT_V1,
    Capability.WORKSPACE_STATUS_V1,
    Capability.WORKSPACE_DIFF_V1,
    Capability.WORKSPACE_ROLLBACK_V1,
    Capability.WORKSPACE_DISCARD_V1,
]


class RunnerLifecycle:
    def __init__(
        self,
        settings: RunnerSettings,
        client: ControlPlaneClient,
        credentials: CredentialStore,
        *,
        workspace_manager: WorkspaceManager | None = None,
        sleep: object = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._client = client
        self._credentials = credentials
        self._workspace_manager = workspace_manager
        self._capabilities = [
            *CAPABILITIES,
            *(WORKSPACE_CAPABILITIES if settings.repository_handles else []),
        ]
        self._stop = asyncio.Event()
        self._sleep = sleep
        self._backoff_attempt = 0

    def request_stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        credential: RunnerCredential | None = None
        next_heartbeat = 0.0
        loop = asyncio.get_running_loop()
        while not self._stop.is_set():
            try:
                credential = credential or await self._ensure_credential()
                now = loop.time()
                if now >= next_heartbeat:
                    await self._register_repositories(credential)
                    await self._client.heartbeat(
                        HeartbeatRequest(
                            runner_id=credential.runner_id,
                            protocol_version=RUNNER_PROTOCOL_VERSION,
                            software_version=self._settings.software_version,
                            capabilities=self._capabilities,
                        ),
                        credential.token,
                    )
                    next_heartbeat = now + self._settings.heartbeat_interval_seconds
                claim = await self._client.claim(
                    ClaimRequest(runner_id=credential.runner_id, wait_seconds=0),
                    credential.token,
                )
                self._backoff_attempt = 0
                if claim.assignment is not None:
                    await self._execute_assignment(credential, claim.assignment)
                else:
                    await self._sleep_or_stop(self._settings.poll_interval_seconds)
            except ControlPlaneError as exc:
                LOGGER.warning(
                    "control plane request failed",
                    extra={"event": "control_plane_error", "error_code": exc.code},
                )
                if exc.status_code == 401 and credential is not None:
                    self._credentials.clear()
                    credential = None
                await self._backoff()
            except (ValueError, OSError, WorkspaceExecutionError) as exc:
                LOGGER.error(
                    "runner local state error",
                    extra={"event": "runner_local_error", "error_type": type(exc).__name__},
                )
                await self._backoff()

    async def _ensure_credential(self) -> RunnerCredential:
        existing = self._credentials.load()
        if existing is not None:
            return existing
        bootstrap = self._settings.bootstrap_token
        if len(bootstrap.get_secret_value()) < 32:
            raise ValueError("Runner bootstrap credential is unavailable")
        response = await self._client.register(
            RegisterRequest(
                display_name=self._settings.display_name,
                protocol_version=RUNNER_PROTOCOL_VERSION,
                software_version=self._settings.software_version,
                capabilities=self._capabilities,
            ),
            bootstrap,
        )
        credential = RunnerCredential(
            runner_id=response.runner_id,
            token=SecretStr(response.runner_token),
            protocol_version=response.protocol_version,
        )
        self._credentials.save(credential)
        LOGGER.info(
            "runner registered",
            extra={"event": "runner_registered", "runner_id": str(response.runner_id)[:8]},
        )
        return credential

    async def _register_repositories(self, credential: RunnerCredential) -> None:
        if not self._settings.repository_handles:
            return
        if self._workspace_manager is None:
            raise ValueError("Workspace Manager is unavailable")
        for request in await asyncio.to_thread(
            self._workspace_manager.registration_requests,
            credential.runner_id,
        ):
            response = await self._client.register_repository(request, credential.token)
            if (
                response.opaque_handle != request.opaque_handle
                or response.current_revision != request.current_revision
            ):
                raise ValueError("Repository registration response is inconsistent")

    async def _execute_assignment(
        self,
        credential: RunnerCredential,
        assignment: JobAssignment,
    ) -> None:
        identity = {
            "runner_id": credential.runner_id,
            "attempt_id": assignment.attempt_id,
            "lease_id": assignment.lease_id,
        }
        try:
            validate_assignment(assignment)
        except PermissionEnvelopeDeniedError as exc:
            await self._client.fail(
                assignment.job_id,
                FailRequest(
                    **identity,
                    error_code=_policy_failure_code(exc.code),
                    error_message=None,
                ),
                credential.token,
            )
            return

        started = await self._client.start(
            assignment.job_id,
            StartRequest(**identity),
            credential.token,
        )
        if started.cancel_requested:
            await self._client.cancelled(
                assignment.job_id,
                CancelledRequest(**identity),
                credential.token,
            )
            return

        cancel_event = threading.Event()
        execution = asyncio.create_task(
            execute_job(
                assignment.job,
                software_version=self._settings.software_version,
                capabilities=self._capabilities,
                workspace_manager=self._workspace_manager,
                operation_id=assignment.job_id,
                cancel_event=cancel_event,
            )
        )
        renewal_interval = max(
            0.5,
            assignment.permission_envelope.lease_seconds / 3,
        )
        progress_sequence = 0
        try:
            while not execution.done():
                done, _ = await asyncio.wait({execution}, timeout=renewal_interval)
                if done:
                    break
                renewed = await self._client.renew(
                    assignment.job_id,
                    RenewRequest(**identity),
                    credential.token,
                )
                if renewed.cancel_requested:
                    cancel_event.set()
                    if isinstance(assignment.job, WorkspaceBoundJobSpec):
                        try:
                            await execution
                        except WorkspaceExecutionError:
                            pass
                    else:
                        execution.cancel()
                        try:
                            await execution
                        except asyncio.CancelledError:
                            pass
                    await self._client.cancelled(
                        assignment.job_id,
                        CancelledRequest(**identity),
                        credential.token,
                    )
                    return
                if isinstance(assignment.job, ControlledWaitJobSpec):
                    progress_sequence += 1
                    await self._client.progress(
                        assignment.job_id,
                        ProgressEventRequest(
                            **identity,
                            sequence=progress_sequence,
                            progress_percent=min(
                                99,
                                round(
                                    progress_sequence
                                    * renewal_interval
                                    * 100
                                    / (assignment.job.duration_ms / 1000)
                                ),
                            ),
                        ),
                        credential.token,
                    )
            result = await execution
            await self._client.complete(
                assignment.job_id,
                CompleteRequest(**identity, result=result),
                credential.token,
            )
        except ControlPlaneError:
            cancel_event.set()
            if not execution.done():
                execution.cancel()
            raise
        except WorkspaceExecutionError as exc:
            cancel_event.set()
            await self._client.fail(
                assignment.job_id,
                FailRequest(
                    **identity,
                    error_code=exc.code,
                    error_message=None,
                ),
                credential.token,
            )
        except Exception as exc:
            cancel_event.set()
            if not execution.done():
                execution.cancel()
            LOGGER.error(
                "typed executor failed",
                extra={"event": "executor_error", "error_type": type(exc).__name__},
            )
            await self._client.fail(
                assignment.job_id,
                FailRequest(
                    **identity,
                    error_code=FailureCode.RUNNER_INTERNAL_ERROR,
                    error_message=None,
                ),
                credential.token,
            )

    async def _backoff(self) -> None:
        delay = min(
            self._settings.backoff_max_seconds,
            self._settings.backoff_initial_seconds * (2**self._backoff_attempt),
        )
        self._backoff_attempt = min(self._backoff_attempt + 1, 10)
        jittered = delay * random.uniform(0.8, 1.2)
        await self._sleep_or_stop(jittered)

    async def _sleep_or_stop(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=seconds)
        except TimeoutError:
            pass


def _policy_failure_code(code: str) -> FailureCode:
    if code == "envelope_hash_mismatch":
        return FailureCode.ENVELOPE_HASH_MISMATCH
    if code == "envelope_expired":
        return FailureCode.ENVELOPE_EXPIRED
    if code == "unsupported_capability":
        return FailureCode.UNSUPPORTED_CAPABILITY
    return FailureCode.POLICY_DENIED
