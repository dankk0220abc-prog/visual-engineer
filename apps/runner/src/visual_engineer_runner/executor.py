import asyncio
import platform
import re
import sys
import threading
import time
import uuid
from datetime import UTC, datetime

from visual_engineer_runner.workspace_manager import WorkspaceManager
from visual_engineer_runner_protocol import (
    RUNNER_PROTOCOL_VERSION,
    Capability,
    ControlledWaitJobSpec,
    ControlledWaitResult,
    DiagnosticResult,
    JobSpec,
    ResultPayload,
    SideEffectPermit,
    SystemDiagnosticJobSpec,
    WorkspaceBoundJobSpec,
)


def _os_family() -> str:
    value = platform.system().casefold()
    if value == "linux":
        return "linux"
    if value == "darwin":
        return "darwin"
    if value == "windows":
        return "windows"
    return "other"


def _architecture() -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]", "-", platform.machine())[:64]
    return normalized or "unknown"


async def execute_job(
    spec: JobSpec,
    *,
    software_version: str,
    capabilities: list[Capability],
    workspace_manager: WorkspaceManager | None = None,
    operation_id: uuid.UUID | None = None,
    cancel_event: threading.Event | None = None,
    side_effect_permit: SideEffectPermit | None = None,
) -> ResultPayload:
    if isinstance(spec, SystemDiagnosticJobSpec):
        started_at = datetime.now(UTC)
        started = time.perf_counter()
        await asyncio.sleep(0)
        completed_at = datetime.now(UTC)
        return DiagnosticResult(
            runner_software_version=software_version,
            protocol_version=RUNNER_PROTOCOL_VERSION,
            python_version=".".join(str(value) for value in sys.version_info[:3]),
            os_family=_os_family(),
            architecture=_architecture(),
            capability_list=capabilities,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
        )
    if isinstance(spec, ControlledWaitJobSpec):
        started_at = datetime.now(UTC)
        started = time.perf_counter()
        remaining = spec.duration_ms / 1000
        while remaining > 0:
            interval = min(0.1, remaining)
            await asyncio.sleep(interval)
            remaining -= interval
        completed_at = datetime.now(UTC)
        return ControlledWaitResult(
            requested_duration_ms=spec.duration_ms,
            elapsed_duration_ms=round((time.perf_counter() - started) * 1000, 3),
            started_at=started_at,
            completed_at=completed_at,
        )
    if isinstance(spec, WorkspaceBoundJobSpec):
        if workspace_manager is None or operation_id is None or cancel_event is None:
            raise ValueError("workspace executor dependencies are unavailable")
        return await asyncio.to_thread(
            workspace_manager.execute,
            spec,
            operation_id=operation_id,
            cancel_event=cancel_event,
            side_effect_permit=side_effect_permit,
        )
    raise ValueError("unsupported typed Job")
