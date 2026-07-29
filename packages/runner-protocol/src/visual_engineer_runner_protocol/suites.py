from dataclasses import dataclass

from visual_engineer_runner_protocol.canonical import compute_validation_policy_digest
from visual_engineer_runner_protocol.profiles import validation_profile


@dataclass(frozen=True)
class ValidationSuiteStep:
    sequence: int
    step_id: str
    profile_id: str
    profile_version: int
    timeout_seconds: int
    max_output_bytes: int

    @property
    def profile_reference(self) -> str:
        return f"{self.profile_id}:v{self.profile_version}"


@dataclass(frozen=True)
class ValidationSuite:
    suite_id: str
    version: int
    name: str
    purpose: str
    steps: tuple[ValidationSuiteStep, ...]
    failure_policy: str
    total_timeout_seconds: int
    total_output_bytes: int
    max_attempts: int

    @property
    def reference(self) -> str:
        return f"{self.suite_id}:v{self.version}"

    @property
    def policy_digest(self) -> str:
        return compute_validation_policy_digest(
            {
                "kind": "validation_suite",
                "suite_id": self.suite_id,
                "suite_version": self.version,
                "steps": [
                    {
                        "sequence": step.sequence,
                        "step_id": step.step_id,
                        "profile_id": step.profile_id,
                        "profile_version": step.profile_version,
                        "timeout_seconds": step.timeout_seconds,
                        "max_output_bytes": step.max_output_bytes,
                    }
                    for step in self.steps
                ],
                "failure_policy": self.failure_policy,
                "total_timeout_seconds": self.total_timeout_seconds,
                "total_output_bytes": self.total_output_bytes,
                "max_attempts": self.max_attempts,
                "max_artifact_bytes": 0,
                "max_artifact_count": 0,
            }
        )


def _step(sequence: int, step_id: str, profile_id: str) -> ValidationSuiteStep:
    profile = validation_profile(profile_id)
    if profile is None:
        raise RuntimeError("Suite references an unavailable Validation Profile")
    if profile.step_id != step_id:
        raise RuntimeError("Suite step does not match its Validation Profile")
    return ValidationSuiteStep(
        sequence=sequence,
        step_id=step_id,
        profile_id=profile.profile_id,
        profile_version=profile.version,
        timeout_seconds=profile.timeout_seconds,
        max_output_bytes=profile.max_output_bytes,
    )


FIXTURE_INTEGRITY_SUITE_V1 = ValidationSuite(
    suite_id="fixture-integrity-suite-v1",
    version=1,
    name="Trusted fixture integrity suite",
    purpose=(
        "Validates the exact trusted fixture content contract and then its bounded "
        "manifest/content digest using two isolated fixed-Profile executions."
    ),
    steps=(
        _step(1, "fixture-contract", "fixture-python-stdlib-v1"),
        _step(2, "fixture-manifest", "fixture-python-manifest-v1"),
    ),
    failure_policy="fail_fast",
    total_timeout_seconds=30,
    total_output_bytes=10_000,
    max_attempts=2,
)

VALIDATION_SUITE_CATALOG = {
    FIXTURE_INTEGRITY_SUITE_V1.suite_id: FIXTURE_INTEGRITY_SUITE_V1,
}


def validation_suite(suite_id: str) -> ValidationSuite | None:
    return VALIDATION_SUITE_CATALOG.get(suite_id)
