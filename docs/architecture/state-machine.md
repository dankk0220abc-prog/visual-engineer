# Run State Machine

## Implemented Phase 2 lifecycle

The service owns a closed transition table; routes cannot assign state
directly.

```mermaid
stateDiagram-v2
    [*] --> created
    created --> snapshotting
    snapshotting --> snapshot_ready
    snapshot_ready --> plan_ready
    plan_ready --> awaiting_plan_approval
    awaiting_plan_approval --> approved
    awaiting_plan_approval --> rejected

    created --> cancelled
    snapshotting --> cancelled
    snapshot_ready --> cancelled
    plan_ready --> cancelled
    awaiting_plan_approval --> cancelled

    snapshotting --> failed
    snapshot_ready --> failed
    plan_ready --> failed
```

`approved`, `rejected`, `failed`, and `cancelled` are terminal in Phase 2.
There is intentionally no `executing` transition.

## State meanings

| State                    | Meaning                                                   | Exit gate                                |
| ------------------------ | --------------------------------------------------------- | ---------------------------------------- |
| `created`                | Level 0 Run exists; no repository scan began.             | Explicit Snapshot request.               |
| `snapshotting`           | Bounded committed-object scan is active.                  | Immutable Snapshot or redacted failure.  |
| `snapshot_ready`         | One successful Snapshot is durable.                       | Deterministic Plan creation.             |
| `plan_ready`             | Latest Plan is a reviewable draft.                        | Valid latest-version submission.         |
| `awaiting_plan_approval` | Latest Plan awaits the local user.                        | One approve or reasoned reject decision. |
| `approved`               | Exact Plan version was approved as a governance decision. | None in Phase 2.                         |
| `rejected`               | Exact Plan version was rejected.                          | None in Phase 2.                         |
| `failed`                 | Run stopped safely with a stable redacted error.          | None in Phase 2.                         |
| `cancelled`              | User stopped a pre-decision Run.                          | None in Phase 2.                         |

## Plan lifecycle

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> superseded: create latest revision
    draft --> awaiting_approval: submit latest valid version
    awaiting_approval --> approved: one final approve
    awaiting_approval --> rejected: one final reject with reason
```

A revision creates `version + 1`, copies immutable context, applies only
allowlisted editable fields, recomputes the content hash, and supersedes the
prior draft. Only the latest draft may be revised or submitted. Only the latest
awaiting Plan may be decided. An approved Run cannot create another version.

## Conflict and idempotency rules

- Run creation replays only when the same idempotency key represents the same
  normalized request; otherwise it returns a stable conflict.
- A completed Snapshot request returns the existing immutable Snapshot.
- Re-creating the same initial draft returns that draft; subsequent versions
  use the revision endpoint.
- Re-submitting the same awaiting Plan is idempotent.
- An identical final decision and comment replay returns the decision.
- A stale version returns `409`.
- A different decision after a winner returns `decision_conflict`.
- PostgreSQL row locks and the unique `plan_id` decision constraint allow only
  one winner in a concurrent approve/reject race.

## Invariants

- `permission_level` is always `read_only`.
- `snapshot_mode` is always `git_head`.
- One successful immutable Snapshot exists at most once per Run.
- Every Plan binds that Snapshot fingerprint and has
  `source = deterministic_policy`.
- `execution_available` is always false at both API and database boundaries.
- Rejection requires a non-blank reason.
- Every material transition appends a sanitized AuditEvent with request ID.
- Approval records a human decision only; it does not authorize or trigger
  code execution, a worktree, a command, Git, PR, or deployment action.
