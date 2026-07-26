# ADR 0013: Checkpoint Evidence and Baseline-Only Rollback

- Status: Accepted
- Date: 2026-07-27

## Context

Every write must be reviewable and reversible without letting rollback become
a broad deletion or arbitrary Git-reset primitive.

## Decision

Successful writes and diffs produce immutable bounded Checkpoints containing
only source revision, tree fingerprint, diff hash, allowed relative paths,
counts/bytes, and bounded textual evidence. Phase 4 rollback targets only the
initial exact source revision. Fixed Git restore handles tracked changes and
an exact per-Workspace ledger removes only created files whose type, path, and
expected content remain valid. Clean status and the initial tree fingerprint
are mandatory postconditions.

Arbitrary checkpoint restore, directory deletion, user-selected reset targets,
and source-repository changes are excluded.

## Consequences

- Checkpoints are durable evidence, not executable authority.
- Rollback is narrow enough to reason about and test under interruption.
- A user modification that breaks the recorded identity/hash fails closed
  instead of being deleted.
- More flexible history restoration requires a later ADR and security review.
