# ADR 0015: Signed Workspace Ownership and Fail-Closed Quarantine

- Status: Accepted for repair candidate
- Date: 2026-07-28

## Context

A missing mutable registry was previously recoverable from a clean Git status.
That did not prove Runner ownership and could omit ignored or unknown content,
making forced disposal unsafe.

## Decision

The Runner generates a mode-`0600` HMAC key in its private credential volume.
Each prepared Workspace receives independent local records:

1. a registry whose complete canonical payload is domain-separated and
   authenticated; and
2. a signed ownership manifest binding the Workspace, Runner, Grant,
   Repository Handle, revision, policy, nonce, managed path, and root
   device/inode; and
3. when discard begins, a domain-separated signed proof binding those
   identities plus the exact operation, Permit ID/sequence, Attempt, Lease,
   job/operation/current/proposed digests, authorization window, state, and a
   proof nonce.

Discard also requires a current discard permit, an allowed local state, exact
registry/manifest agreement, valid signatures, exact root identity, the
managed-root boundary, and a complete no-follow inventory. A missing proof
enters `recovery_required`. Contradictory proof, signature failure, identity
drift, or unknown/ignored content enters `quarantined`. Neither state deletes
the Workspace, mirror, source, or sibling Workspace.

The proof is durably `pending` before the registry records pending deletion and
before disk mutation. It becomes durably `completed` after exact deletion and
before terminal registry state. Interrupted discard may be reconciled only
from one of those exact state combinations, an absent expected root, and a
bounded no-follow search proving the original root inode was not renamed
elsewhere in the managed Workspace volume. Terminal replay must carry the
same completed-operation and Permit lineage. UUID-shaped paths, bare absence,
and Git cleanliness are never ownership evidence.

## Consequences

- Loss of local proof becomes a visible operator recovery condition, not
  implicit permission to delete.
- The signing key and signed local paths remain Runner-local and never enter
  API payloads, PostgreSQL events, logs, or Git.
- Normal exact disposal remains idempotent.
- Registry loss, root replacement/rename, signed-state rollback, tamper,
  mismatch, replay, and expiry fail closed without modifying preserved roots
  or siblings.
- Automated broad garbage collection is still not implemented.
- The single-Writer and no-portable-`openat2` assumptions remain explicit.
