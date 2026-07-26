# ADR 0006: Plan Approval Does Not Authorize Execution

- Status: Accepted
- Date: 2026-07-26

## Context

A durable approval UI can be mistaken for permission to modify a repository.
Phase 2 has no isolated worktree, write tool, runtime policy engine, command
executor, checkpoint, final-change approval, or delivery integration.

## Decision

`approved` is a terminal Phase 2 Run state that means only one local user
approved an exact latest Plan version. The database forces every Plan's
`execution_available` to false. The API has no execution endpoint or
transition, and the UI always displays:

```text
Plan approval does not execute code.
Execution is not available in Phase 2.
```

PostgreSQL row locks and one-decision uniqueness serialize concurrent
approve/reject requests. Rejection requires a reason; stale decisions fail.

## Consequences

- Approval provides durable governance evidence without an external effect.
- No agent may approve the real Customer 0 Plan for the user.
- A future Level 1 milestone needs a distinct explicit permission grant,
  isolated workspace identity, typed runtime policy, audit, and checkpoint.
- Existing Phase 2 approvals cannot be reused as future execution tokens.
