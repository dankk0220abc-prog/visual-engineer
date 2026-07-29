from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationProfile:
    profile_id: str
    version: int
    display_name: str
    description: str
    step_id: str
    safe_argv: tuple[str, ...]
    timeout_seconds: int
    max_output_bytes: int
    max_artifact_bytes: int
    max_artifact_count: int
    cpu_seconds: int
    memory_bytes: int
    pid_limit: int
    fd_limit: int

    @property
    def reference(self) -> str:
        return f"{self.profile_id}:v{self.version}"


FIXTURE_PYTHON_STDLIB_V1 = ValidationProfile(
    profile_id="fixture-python-stdlib-v1",
    version=1,
    display_name="Trusted fixture Python contract",
    description=(
        "Runs one system-owned Python standard-library contract check against "
        "a disposable exact-Checkpoint fixture copy."
    ),
    step_id="fixture-contract",
    safe_argv=("python", "-I", "-S", "<system-owned-fixture-validator>"),
    timeout_seconds=10,
    max_output_bytes=8192,
    max_artifact_bytes=0,
    max_artifact_count=0,
    cpu_seconds=5,
    memory_bytes=128 * 1024 * 1024,
    pid_limit=8,
    fd_limit=64,
)

VALIDATION_PROFILE_CATALOG = {
    FIXTURE_PYTHON_STDLIB_V1.profile_id: FIXTURE_PYTHON_STDLIB_V1,
}


def validation_profile(profile_id: str) -> ValidationProfile | None:
    return VALIDATION_PROFILE_CATALOG.get(profile_id)
