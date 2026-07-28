# ADR 0014: Side-Effect Permits and Bounded Grant Revocation

- Status: Accepted for repair candidate
- Date: 2026-07-28

## Context

Lease fencing at Job start, renewal, and completion did not establish current
authority immediately before a durable Workspace mutation. A Grant could be
revoked after start while a Runner reached the filesystem before its first
renewal. Completion fencing detects that race too late.

## Decision

Every Workspace operation that can create, replace, restore, or remove
Runner-owned filesystem state requires a PostgreSQL-backed
`SideEffectPermit`. Acquisition locks and validates the authenticated Runner,
Job, active Attempt, Lease and deadline, Grant, Workspace, Repository Handle,
source revision, policy hash, operation, normalized path, precondition,
content/operation digest, and budget in one transaction.

The acquired permit is immutable, single-use, short-lived, and bound to the
current Attempt and Lease. The Runner recomputes its canonical operation
digest and checks all bindings and expiry immediately before mutation. The
digest covers the permit state and its issued, consumed, and expiry timestamps,
so changing the local authorization window is detected as tampering rather
than reclassified as an ordinary expiry.
Mutating manager methods reject a missing, stale, expired, or mismatched
permit. Results, Workspace Events, and Checkpoints carry the permit identity
where applicable.

Revocation has two observable states:

- `revoke_requested` commits first and prevents acquisition of any new permit;
- `revoked` becomes effective only after all consumed permits are terminal or
  expired.

An operation already authorized and consumed may complete within its exact
permit window. No new operation is accepted after the request, and no old
permit remains usable after revocation becomes effective.

## Consequences

- Job start is no longer treated as sufficient filesystem authority.
- Stale Lease/Attempt, cancellation, expiry, digest drift, replay, and
  effective revocation fail before a new side effect.
- Crash recovery coordinates an already committed operation without applying
  it or charging its budget twice.
- Distributed revocation is explicitly bounded; instantaneous erasure of an
  already consumed operation is not claimed.
- The repair candidate still requires an independent Security Re-Audit.
