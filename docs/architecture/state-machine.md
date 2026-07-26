# Run State Machine

## Foundation reality

The Foundation database formally implements only a Task with status `draft`.
There is no Run entity, orchestration loop, approval engine, tool executor, or
rollback engine in this phase. The lifecycle below is a V1 design constraint,
not a claim of current execution.

## Future Run lifecycle

```mermaid
stateDiagram-v2
    [*] --> created
    created --> investigating
    investigating --> plan_ready
    investigating --> failed
    plan_ready --> awaiting_plan_approval
    awaiting_plan_approval --> approved
    awaiting_plan_approval --> cancelled
    approved --> executing
    executing --> validating
    executing --> failed
    validating --> awaiting_final_approval
    validating --> executing: bounded repair approved
    validating --> failed
    awaiting_final_approval --> completed
    awaiting_final_approval --> rollback_required

    created --> cancel_requested
    investigating --> cancel_requested
    plan_ready --> cancel_requested
    awaiting_plan_approval --> cancel_requested
    approved --> cancel_requested
    executing --> cancel_requested
    validating --> cancel_requested
    awaiting_final_approval --> cancel_requested
    cancel_requested --> cancelled: no durable change
    cancel_requested --> rollback_required: durable change exists

    failed --> rollback_required: reversible change exists
    failed --> [*]: no change to reverse
    rollback_required --> rolling_back
    rolling_back --> rolled_back
    rolling_back --> failed: rollback failure recorded
    completed --> [*]
    cancelled --> [*]
    rolled_back --> [*]
```

## State meanings and gates

| State                     | Meaning                                              | Required exit evidence                               |
| ------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| `created`                 | Run accepted; no repository access yet.              | Policy and target binding.                           |
| `investigating`           | Level 0 read-only inspection is active.              | Cited facts, uncertainty, unchanged target baseline. |
| `plan_ready`              | A bounded plan and validation/rollback design exist. | Plan artifact and permission request.                |
| `awaiting_plan_approval`  | No write is allowed; awaiting human decision.        | Signed/attributed approval or rejection.             |
| `approved`                | Exact plan and permission ceiling approved.          | Immutable approval reference.                        |
| `executing`               | Scoped work in an isolated worktree.                 | Tool-call audit and checkpoints.                     |
| `validating`              | Controlled tests/browser checks are running.         | Command, exit, artifacts, failure class.             |
| `awaiting_final_approval` | Change and evidence ready for human review.          | Final approval or rollback decision.                 |
| `completed`               | Authorized deliverable finished.                     | Required checks and delivery evidence.               |
| `failed`                  | Work cannot safely continue.                         | Root cause, residual changes, recovery option.       |
| `cancel_requested`        | Cancellation requested; safe point sought.           | Tool quiescence and change assessment.               |
| `cancelled`               | Stopped with no outstanding reversible change.       | Cleanup evidence.                                    |
| `rollback_required`       | Durable scoped changes need reversal.                | Checkpoint and approved rollback action.             |
| `rolling_back`            | Bounded rollback in progress.                        | Audited rollback actions.                            |
| `rolled_back`             | Scoped changes restored to checkpoint.               | Target status and artifact evidence.                 |

## Invariants

- Only a human approval can cross into repository-writing execution.
- Approval binds a plan version, repository/worktree identity, allowed paths,
  commands, time window, and maximum permission level.
- Cancellation never silently discards an in-flight external effect.
- `completed` is impossible with a mandatory failed or missing check.
- Rollback failure remains `failed`; it must not be relabeled `rolled_back`.
- Every transition is idempotent, version-checked, timestamped in UTC, and
  attributable.
