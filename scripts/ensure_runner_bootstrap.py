import os
import secrets
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DESTINATION = REPOSITORY_ROOT / ".env.runner.local"
PREFIX = "RUNNER_BOOTSTRAP_TOKEN="


def existing_token() -> str | None:
    try:
        content = DESTINATION.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    for line in content.splitlines():
        if line.startswith(PREFIX):
            return line.removeprefix(PREFIX).strip()
    return None


def main() -> None:
    current = existing_token()
    if current is not None and len(current) >= 43:
        os.chmod(DESTINATION, 0o600)
        print("Runner bootstrap configuration is ready.")
        return
    token = secrets.token_urlsafe(48)
    temporary = DESTINATION.with_name(f".{DESTINATION.name}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"{PREFIX}{token}\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, DESTINATION)
    os.chmod(DESTINATION, 0o600)
    print("Generated local Runner bootstrap configuration.")


if __name__ == "__main__":
    main()
