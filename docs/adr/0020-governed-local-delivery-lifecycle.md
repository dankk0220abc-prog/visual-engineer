# ADR 0020: Governed Local Delivery Lifecycle

- Status: Accepted for Phase 6 second-slice implementation
- Date: 2026-08-01

## Context

ADR 0019 authorizes one deterministic local commit but its first-slice API has
no final artifact preview, dispatch idempotency key, durable attempt identity,
or recovery path after a cancelled or failed Runner Job. Reusing the
Authorization without explicit lineage would make double-clicks, ambiguous
terminal outcomes, and retries difficult to audit safely.

## Decision

Keep one immutable Delivery Authorization and one final LocalDelivery proof.
Represent execution as one to three linear, durable `DeliveryDispatch`
attempts. Before each attempt, the API derives a `LocalDeliveryManifest` from
the immutable Workspace Checkpoint. It binds the Authorization, Workspace,
Checkpoint tree/diff hashes, source revision, changed-path closure, bounded
diff size, system-derived ref/message, and literal false remote/source-write
effects under one canonical SHA-256 digest.

The browser must fetch the preview and explicitly confirm that exact digest.
Dispatch also requires an `Idempotency-Key`. The Authorization row lock,
request hash, unique active-attempt constraint, attempt number, and optional
`retry_of_dispatch_id` create one concurrent winner and an exact replay.

A retry is permitted only when the latest attempt is `failed` or `cancelled`,
no LocalDelivery exists, the exact authorization/manifest remains fresh, the
original implementation Grant is still active, and fewer than three attempts
exist. Every Job, Permit digest, Runner assignment, terminal result,
AuditEvent, and Web history entry binds the Dispatch ID, attempt number, and
manifest digest. Runner independently recomputes the manifest from current
Workspace state immediately before Git mutation.

## Consequences

- Failure and cancellation are terminal facts, not erased queue state.
- The same key and request replay the same attempt; a changed payload conflicts.
- Concurrent dispatch has one durable Job/Dispatch winner.
- Retry cannot widen paths, ref, message, timestamp, authority, or remote scope.
- Revocation, expiry, staleness, manifest drift, non-linear lineage, exhausted
  budget, or an existing successful LocalDelivery fail closed before a new Job.
- Migration `20260801_0014` is additive and reversibly restores the first-slice
  transition and audit guards on downgrade.

Remote access, push, PR, merge, tag, deploy, source writes, arbitrary Git,
credentials, real repositories, and a third Phase 6 slice still require new
authority, ADRs, and independent review.
