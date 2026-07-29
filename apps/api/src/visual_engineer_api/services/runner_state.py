from visual_engineer_api.models.runner import RunnerJob, RunnerJobAttempt

JOB_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"leased", "cancelled", "failed"}),
    "leased": frozenset({"running", "cancel_requested", "queued", "failed"}),
    "running": frozenset({"cancel_requested", "succeeded", "failed", "queued"}),
    "cancel_requested": frozenset({"cancelled", "failed"}),
    "succeeded": frozenset(),
    "cancelled": frozenset(),
    "failed": frozenset(),
}

ATTEMPT_TRANSITIONS: dict[str, frozenset[str]] = {
    "leased": frozenset({"running", "cancelled", "failed", "lease_expired"}),
    "running": frozenset({"succeeded", "cancelled", "failed", "lease_expired"}),
    "succeeded": frozenset(),
    "cancelled": frozenset(),
    "failed": frozenset(),
    "lease_expired": frozenset(),
}


class InvalidRunnerJobTransitionError(Exception):
    pass


class InvalidRunnerAttemptTransitionError(Exception):
    pass


def transition_job(job: RunnerJob, target: str) -> None:
    if target not in JOB_TRANSITIONS.get(job.state, frozenset()):
        raise InvalidRunnerJobTransitionError(f"{job.state} -> {target}")
    job.state = target
    job.version += 1


def transition_attempt(attempt: RunnerJobAttempt, target: str) -> None:
    if target not in ATTEMPT_TRANSITIONS.get(attempt.state, frozenset()):
        raise InvalidRunnerAttemptTransitionError(f"{attempt.state} -> {target}")
    attempt.state = target
