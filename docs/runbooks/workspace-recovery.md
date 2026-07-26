# Workspace Recovery Runbook

## Recovery principles

Never repair Runner state by editing database rows, changing a Grant, deleting
an arbitrary path, writing the source fixture, or disabling Lease/identity
checks. Recovery must replay the same typed Job under a new fenced Attempt.

## Runner lost while preparing

1. Leave the Workspace and Job records intact.
2. Restart the configured Runner.
3. The lease reaper expires the old Attempt and requeues within its retry
   budget.
4. Runner validates the same Grant, revision, policy hash, and Workspace ID.
5. Existing exact mirror/worktree/registry evidence is reconciled
   idempotently; otherwise the Job fails closed.

An old Runner completion must receive `409 stale_lease`.

## Runner lost while writing

The operation ID determines the same-directory temporary name.

- If interruption happened before the atomic commit, the target is unchanged
  and retry removes only that exact regular one-link temp.
- If the commit happened before acknowledgement, retry reopens the target,
  verifies the requested content hash/size, reconciles the pending registry
  operation, and returns the same result.
- Any unexpected type, link count, identity, content, registry binding, or
  budget becomes a stable failure; do not force success.

Cancellation before commit cleans the temp and cannot report success. A stale
Attempt cannot mutate durable Control Plane state even if it later returns.

## Failed or expired Workspace

If the Grant is still approved and unexpired, request typed discard from the
browser. Workspace expiry deliberately precedes Grant expiry by ten minutes.
If the Grant is already revoked/expired, Phase 4 refuses all Jobs including
discard; stop and preserve evidence. Privileged garbage collection is a future
separately reviewed capability.

## Verification

Use `make workspace-chaos-check` for an isolated disposable exercise. It stops
Runner during prepare and again after an atomic temp has been synced, proves
lease expiry/requeue, rejects both old leases, restarts Runner, completes
recovery, rolls back, discards, checks no residual workspace, and compares the
full source and `.git` fingerprint.

For the normal running stack, `make workspace-smoke` performs the typed
read/write/deny/diff/checkpoint/rollback/discard path and source comparison.
Never point either command at CreativeDeploy.
