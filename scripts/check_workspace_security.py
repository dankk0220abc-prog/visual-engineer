import ast
import json
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUNNER_ROOT = REPOSITORY_ROOT / "apps" / "runner" / "src" / "visual_engineer_runner"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".", 1)[0])
    return modules


def require_markers(path: Path, markers: tuple[str, ...]) -> None:
    source = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in source]
    if missing:
        raise SystemExit(
            f"{path.relative_to(REPOSITORY_ROOT)} is missing security controls: {missing}"
        )


def main() -> None:
    subprocess_users = [
        path.name
        for path in sorted(RUNNER_ROOT.glob("*.py"))
        if "subprocess" in imported_modules(path)
    ]
    if subprocess_users != ["git_ops.py"]:
        raise SystemExit(
            f"Runner subprocess boundary is not closed to git_ops.py: {subprocess_users}"
        )
    for path in sorted(RUNNER_ROOT.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for prohibited in ("shell=True", "os.system(", "shutil.rmtree", "eval(", "exec("):
            if prohibited in source:
                raise SystemExit(f"{path.relative_to(REPOSITORY_ROOT)} contains {prohibited}")

    require_markers(
        RUNNER_ROOT / "safe_fs.py",
        (
            "dir_fd=",
            "os.O_DIRECTORY",
            "os.O_NOFOLLOW",
            "os.fstat(",
            "st_nlink",
            "os.fsync(",
            "os.link(",
            "os.rename(",
            "expected_sha256",
            "WORKSPACE_CANCELLED",
        ),
    )
    require_markers(
        RUNNER_ROOT / "git_ops.py",
        (
            "shell=False",
            "--no-ext-diff",
            "--no-textconv",
            "core.hooksPath=/dev/null",
            "credential.helper=",
            "protocol.allow=never",
            "GIT_LFS_SKIP_SMUDGE",
            "_copy_source_objects",
            "_collect_bounded_output",
            "start_new_session=True",
            "worktree",
            "--detach",
        ),
    )
    require_markers(
        RUNNER_ROOT / "workspace_manager.py",
        (
            "execution_grant_policy_hash_matches",
            "SOURCE_REVISION_MISMATCH",
            "workspace_device",
            "workspace_inode",
            "created_paths",
            "completed_operations",
        ),
    )

    base_compose = (REPOSITORY_ROOT / "compose.yaml").read_text(encoding="utf-8")
    workspace_compose = (REPOSITORY_ROOT / "infra" / "compose.workspace.yaml").read_text(
        encoding="utf-8"
    )
    runner_override = workspace_compose.split("\n  runner:\n", 1)[1].split("\nvolumes:\n", 1)[0]
    for marker in (
        "target: /repositories/fixture",
        "read_only: true",
        "runner-mirrors:",
        "runner-workspaces:",
        "runner-registry:",
    ):
        if marker not in workspace_compose:
            raise SystemExit(f"Workspace Compose override is missing {marker}")
    if "ports:" in runner_override:
        raise SystemExit("Workspace Runner publishes a prohibited port")
    for prohibited in ("docker.sock", "/.ssh", "/Users/", "~/Developer"):
        if prohibited in workspace_compose:
            raise SystemExit(f"Workspace Compose contains prohibited mount {prohibited}")
    for service in ("api", "web", "db"):
        section_marker = f"\n  {service}:\n"
        if section_marker in workspace_compose:
            section = workspace_compose.split(section_marker, 1)[1].split("\n  ", 1)[0]
            if "/repositories/fixture" in section or "runner-workspaces" in section:
                raise SystemExit(f"{service} receives prohibited Workspace mounts")
    for marker in (
        "read_only: true",
        "cap_drop:",
        "no-new-privileges:true",
        "runner-control:",
        "internal: true",
    ):
        if marker not in base_compose:
            raise SystemExit(f"Base Runner isolation control is missing {marker}")

    dockerfile = (REPOSITORY_ROOT / "apps" / "runner" / "Dockerfile").read_text(encoding="utf-8")
    for marker in ("USER runner", "git", "/var/lib/visual-engineer-runner/workspaces"):
        if marker not in dockerfile:
            raise SystemExit(f"Runner image is missing {marker}")

    fixture_manifest = json.loads(
        (REPOSITORY_ROOT / "fixtures" / "workspace-adversarial-source" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        fixture_manifest.get("fixture_version") != "workspace-adversarial-v0.1"
        or fixture_manifest.get("contains_real_secret") is not False
        or fixture_manifest.get("source_mount") != "runner_only_read_only"
    ):
        raise SystemExit("Workspace fixture manifest is invalid")
    print("Workspace static isolation and descriptor-safe tool boundaries pass.")


if __name__ == "__main__":
    main()
