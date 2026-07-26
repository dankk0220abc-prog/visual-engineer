import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

API_BASE_URL = os.environ.get("RUNNER_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT_SECONDS = float(os.environ.get("RUNNER_STATUS_TIMEOUT", "30"))


def fetch_runners() -> list[dict[str, Any]]:
    request = urllib.request.Request(
        f"{API_BASE_URL}/api/v1/runners",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        payload: Any = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Runner registry returned an invalid response")
    return [item for item in payload["items"] if isinstance(item, dict)]


def main() -> None:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    last_error = "no Runner registered"
    while time.monotonic() < deadline:
        try:
            runners = fetch_runners()
            online = [item for item in runners if item.get("status") == "online"]
            if online:
                item = online[0]
                print(
                    "Runner online: "
                    f"{item.get('display_name', 'Local Runner')} "
                    f"({str(item.get('id', ''))[:8]})"
                )
                return
            last_error = "Runner is not online yet"
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = type(exc).__name__
        time.sleep(0.5)
    print(f"Runner status check failed: {last_error}", file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
