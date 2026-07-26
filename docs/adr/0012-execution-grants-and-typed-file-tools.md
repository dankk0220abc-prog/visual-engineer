# ADR 0012: Execution Grants and Typed File Tools

- Status: Accepted
- Date: 2026-07-27

## Context

Plan approval records agreement with a proposed scope but is not execution
authority. General shell or model-selected tools would make repository and
process permissions difficult to bound or review.

## Decision

Execution requires a separate immutable Grant derived from an approved,
non-stale Plan/Snapshot and current Repository Handle. The Grant begins
pending, receives one independent local-user decision, carries a canonical
policy hash, and fixes operations, `sandbox/**`, denied sensitive paths,
budgets, revision, TTL, network `none`, and false shell/source-write/Git-
delivery authority.

The only Phase 4 capabilities are eight closed protocol jobs: prepare, list,
read UTF-8 text, create/compare-and-swap replace UTF-8 text, status, bounded
diff, baseline rollback, and discard. Control Plane constructs the job and
Permission Envelope; Runner revalidates all bindings at claim and every lease
mutation.

## Consequences

- Plan approval cannot cause execution and a Deployment Pack cannot expand it.
- Paths, hashes, limits, outcomes, and failures are typed and reviewable.
- Revocation/expiry fences every Job, including disposal.
- No shell, delete/rename tool, binary write, target command, package
  lifecycle, public network, Git delivery, or PR exists.
