from visual_engineer_api.models.run import Run

RUN_TRANSITIONS: dict[str, frozenset[str]] = {
    "created": frozenset({"snapshotting", "cancelled"}),
    "snapshotting": frozenset({"snapshot_ready", "failed", "cancelled"}),
    "snapshot_ready": frozenset({"plan_ready", "failed", "cancelled"}),
    "plan_ready": frozenset({"awaiting_plan_approval", "failed", "cancelled"}),
    "awaiting_plan_approval": frozenset({"approved", "rejected", "cancelled"}),
    "approved": frozenset(),
    "rejected": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


class InvalidRunTransitionError(Exception):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Run cannot transition from {current} to {target}")
        self.current = current
        self.target = target


def transition_run(run: Run, target: str) -> None:
    if target == run.status:
        return
    if target not in RUN_TRANSITIONS.get(run.status, frozenset()):
        raise InvalidRunTransitionError(run.status, target)
    run.status = target
    run.version += 1
