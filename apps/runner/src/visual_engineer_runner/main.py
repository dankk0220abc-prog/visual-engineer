import asyncio
import logging
import signal

from visual_engineer_runner.client import ControlPlaneClient
from visual_engineer_runner.config import RunnerSettings
from visual_engineer_runner.credentials import CredentialStore
from visual_engineer_runner.lifecycle import RunnerLifecycle
from visual_engineer_runner.workspace_manager import WorkspaceManager


async def async_main() -> None:
    settings = RunnerSettings()
    logging.basicConfig(level=settings.log_level)
    client = ControlPlaneClient(
        settings.control_plane_url,
        timeout_seconds=settings.request_timeout_seconds,
    )
    lifecycle = RunnerLifecycle(
        settings,
        client,
        CredentialStore(settings.credential_path),
        workspace_manager=WorkspaceManager(settings),
    )
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signal_name, lifecycle.request_stop)
    try:
        await lifecycle.run()
    finally:
        await client.close()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
