# Workspace Recovery Runbook

## Recovery principles

Never repair Runner state by editing database rows, changing a Grant, deleting
an arbitrary path, writing the source fixture, or disabling Lease/identity
checks. Never recreate ownership proof from a UUID-like path or Git
cleanliness. Recovery must use the same typed Job under a new fenced Attempt;
every new mutation requires a new current Side-effect Permit.

## Runner lost while preparing

1. Leave the Workspace and Job records intact.
2. Restart the configured Runner.
3. The lease reaper expires the old Attempt and requeues within its retry
   budget.
4. Runner validates the same Grant, revision, policy hash, and Workspace ID.
5. Existing exact mirror/worktree/authenticated-registry/signed-manifest
   evidence is reconciled idempotently; otherwise the Job fails closed into a
   typed recovery state without deleting anything.

An old Runner completion must receive `409 stale_lease`.

## Runner lost while writing

The operation ID determines the same-directory temporary name.

- If interruption happened before the atomic commit, the target is unchanged
  and a new permitted retry removes only that exact regular one-link temp.
- If the commit happened before acknowledgement, retry reopens the target,
  verifies the requested content hash/size and original Permit lineage,
  reconciles the authenticated pending operation, and returns the same result
  without a second write or budget charge.
- Any unexpected type, link count, identity, content, registry binding, or
  budget becomes a stable failure; do not force success.

Cancellation before commit cleans the temp and cannot report success. A stale
Attempt/Lease/Permit cannot mutate the filesystem or durable Control Plane
state even if it later returns.

## Ownership, registry, and discard failures

- Missing registry or ownership manifest: preserve the Workspace and enter
  `recovery_required`.
- Invalid signature, registry/manifest disagreement, wrong Runner/Grant/
  Handle/revision/policy/nonce, or root device/inode drift: preserve the
  Workspace and enter `quarantined`.
- Ignored, unknown, unexpected-type, or out-of-inventory content: preserve the
  Workspace and enter `quarantined`.
- Interrupted discard: reconcile as complete only when the domain-separated
  signed pending/completed proof exactly binds the registry/manifest,
  Workspace, Runner, Grant, Handle, revision, policy, nonce, root
  device/inode, Job/operation, Permit sequence, Attempt, Lease, digests, and
  authorization window; the expected root and original inode must both be
  absent.
- Registry and expected root both absent with no valid proof:
  `recovery_required`, never idempotent success.
- Terminal registry with missing, pending-rollback, mismatched, replayed, or
  expired proof: fail closed. Preserve any recreated, replaced, or renamed
  root and all siblings.

Both recovery states disable destructive browser controls. Do not rename,
remove, edit, resign, or database-reset the evidence manually. Capture the
typed reason and stop for controlled diagnosis. No privileged garbage
collector exists.

## Failed or expired Workspace

If the Grant is still approved and unexpired, request typed discard from the
browser. Workspace expiry deliberately precedes Grant expiry by ten minutes.
If the Grant is already revoked/expired, Phase 4 refuses all Jobs including
discard; stop and preserve evidence. Privileged garbage collection is a future
separately reviewed capability.

## Verification

Use `make workspace-chaos-check` for an isolated disposable exercise. It stops
Runner during prepare, before commit, and after atomic rename/before result;
proves lease expiry/requeue, stale Attempt/Permit denial, one-time budget
accounting, and requested/effective revocation; then completes bounded
recovery and compares the full source and `.git` evidence.

For the normal running stack, `make workspace-smoke` performs the typed
read/write/deny/diff/checkpoint/rollback/discard path and source comparison.
Never point either command at CreativeDeploy. Round 2 is not an independent
Gate decision; only Phase 4 Independent Focused Security Re-Audit may make a
new decision.
