# ADR 0019: Separate Local Delivery Authorization

- Status: Accepted for Phase 6 first-slice implementation
- Date: 2026-07-31

## Context

Phase 5 Review approval and Release Readiness prove an exact evidence chain,
but both deliberately carry false Git and deployment authority. The existing
Phase 4 implementation Grant owns Workspace paths and budgets. Neither record
may be silently widened to authorize Git.

## Decision

Add one immutable Delivery Authorization with a separate local-user decision.
It binds the exact fresh Review generation, Workspace, Checkpoint, tree/diff
digests, revision, system-derived
`refs/heads/visual-engineer/<workspace-id-hex>` ref, and fixed commit message.

The local commit Job uses two authorities:

1. the Workspace's original implementation Grant for repository identity,
   paths, budgets, expiry, and Runner binding; and
2. the approved Delivery Authorization for exactly one local Git commit.

A short-lived Side-effect Permit binds both authorities to the active
Job/Attempt/Lease immediately before mutation. Runner constructs the tree and
commit with fixed Git plumbing and performs one old-OID-guarded local ref
update. The source repository and canonical Workspace bytes remain unchanged.

## Consequences

Remote access, push, PR, tag, merge, deploy, credentials, user-supplied branch
or commit inputs, hooks, signing, and source-repository write remain denied in
protocol, database, API, Runner, and Web. A later remote-delivery capability
requires a new ADR, authority model, security review, and explicit user
authorization.
