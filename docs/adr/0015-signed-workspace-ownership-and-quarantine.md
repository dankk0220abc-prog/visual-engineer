# ADR 0015: Signed Workspace Ownership and Fail-Closed Quarantine

- Status: Accepted for repair candidate
- Date: 2026-07-28

## Context

A missing mutable registry was previously recoverable from a clean Git status.
That did not prove Runner ownership and could omit ignored or unknown content,
making forced disposal unsafe.

## Decision

The Runner generates a mode-`0600` HMAC key in its private credential volume.
Each prepared Workspace receives two independent local records:

1. a registry whose complete canonical payload is domain-separated and
   authenticated; and
2. a signed ownership manifest binding the Workspace, Runner, Grant,
   Repository Handle, revision, policy, nonce, managed path, and root
   device/inode.

Discard also requires a current discard permit, an allowed local state, exact
registry/manifest agreement, valid signatures, exact root identity, the
managed-root boundary, and a complete no-follow inventory. A missing proof
enters `recovery_required`. Contradictory proof, signature failure, identity
drift, or unknown/ignored content enters `quarantined`. Neither state deletes
the Workspace, mirror, source, or sibling Workspace.

Interrupted discard may be reconciled only from an authenticated, exact
pending-discard record and an already absent Workspace root. UUID-shaped paths
and Git cleanliness are never ownership evidence.

## Consequences

- Loss of local proof becomes a visible operator recovery condition, not
  implicit permission to delete.
- The signing key and signed local paths remain Runner-local and never enter
  API payloads, PostgreSQL events, logs, or Git.
- Normal exact disposal remains idempotent.
- Automated broad garbage collection is still not implemented.
- The single-Writer and no-portable-`openat2` assumptions remain explicit.
