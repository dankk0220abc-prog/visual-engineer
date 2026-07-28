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

    git_boundary = RUNNER_ROOT / "git_ops.py"
    for path in sorted(RUNNER_ROOT.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if "subprocess" in imports(path) and path != git_boundary:
            raise SystemExit(
                f"{path.relative_to(REPOSITORY_ROOT)} imports subprocess outside git_ops.py"
            )
        for marker in ("shell=True", "os.system("):
            if marker in source:
                raise SystemExit(
                    f"{path.relative_to(REPOSITORY_ROOT)} contains prohibited marker: {marker}"
                )
        if "Popen(" in source and path != git_boundary:
            raise SystemExit(
                f"{path.relative_to(REPOSITORY_ROOT)} starts a process outside git_ops.py"
            )
    git_source = git_boundary.read_text(encoding="utf-8")
    required_git_controls = (
        "subprocess.Popen(",
        "shell=False",
        "start_new_session=True",
        "_collect_bounded_output",
        "GIT_OUTPUT_LIMIT_EXCEEDED",
        "GIT_TERMINAL_PROMPT",
        "GIT_OPTIONAL_LOCKS",
        "core.hooksPath=/dev/null",
        "credential.helper=",
        "diff.external=",
        "protocol.allow=never",
        "filter.lfs.smudge=",
    )
    missing_git_controls = [value for value in required_git_controls if value not in git_source]
    if missing_git_controls:
        raise SystemExit(f"Runner fixed Git boundary is missing controls: {missing_git_controls}")

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
