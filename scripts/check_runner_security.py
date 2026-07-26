import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_ROOT = (
    REPOSITORY_ROOT / "packages" / "runner-protocol" / "src" / "visual_engineer_runner_protocol"
)
RUNNER_ROOT = REPOSITORY_ROOT / "apps" / "runner" / "src" / "visual_engineer_runner"
FORBIDDEN_PROTOCOL_IMPORTS = {
    "fastapi",
    "sqlalchemy",
    "visual_engineer_api",
    "visual_engineer_runner",
}
FORBIDDEN_EXECUTOR_IMPORTS = {
    "httpx",
    "os",
    "pathlib",
    "requests",
    "socket",
    "subprocess",
    "urllib",
}


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".", 1)[0])
    return names


def main() -> None:
    for path in sorted(PROTOCOL_ROOT.glob("*.py")):
        prohibited_imports = imports(path) & FORBIDDEN_PROTOCOL_IMPORTS
        if prohibited_imports:
            raise SystemExit(
                f"{path.relative_to(REPOSITORY_ROOT)} imports prohibited layers: "
                f"{sorted(prohibited_imports)}"
            )

    executor = RUNNER_ROOT / "executor.py"
    prohibited_executor = imports(executor) & FORBIDDEN_EXECUTOR_IMPORTS
    if prohibited_executor:
        raise SystemExit(
            f"Runner executor imports prohibited capabilities: {sorted(prohibited_executor)}"
        )
    executor_source = executor.read_text(encoding="utf-8")
    for marker in ("shell=True", "os.system(", "subprocess.", "Popen("):
        if marker in executor_source:
            raise SystemExit(f"Runner executor contains prohibited marker: {marker}")

    compose = (REPOSITORY_ROOT / "compose.yaml").read_text(encoding="utf-8")
    required = (
        "runner-control:",
        "internal: true",
        "read_only: true",
        "no-new-privileges:true",
        "cap_drop:",
        "runner-credentials:/var/lib/visual-engineer-runner",
    )
    missing = [value for value in required if value not in compose]
    if missing:
        raise SystemExit(f"Runner Compose security controls are missing: {missing}")
    runner_section = compose.split("\n  runner:\n", 1)[1].split("\nvolumes:\n", 1)[0]
    for prohibited_mount in (
        "ports:",
        "docker.sock",
        "/.ssh",
        "/repositories",
        "/Users/",
        "~/Developer",
    ):
        if prohibited_mount in runner_section:
            raise SystemExit(
                f"Runner Compose section contains prohibited mount/port: {prohibited_mount}"
            )

    print("Runner protocol, executor, and Compose static security boundaries pass.")


if __name__ == "__main__":
    main()
