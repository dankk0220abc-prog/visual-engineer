# ADR 0018: Separate immutable final review from release authority

- Status: Accepted for the Phase 5 Third Vertical Slice implementation
- Date: 2026-07-30

## Context

The sealed Validation Suite boundary can produce one trusted aggregate result
whose ordered child Evidence is reconstructed from immutable execution
identities and digests. A final reviewer needs a stable object to inspect and
decide, but a historical approval must not remain usable after the exact
revision, Workspace Checkpoint, latest successful Suite Result, or Evidence
chain becomes stale. Review approval also must not be mistaken for Git or
deployment authority.

## Decision

Create four additive immutable PostgreSQL records:

1. `ReviewPackage` binds one latest successful Suite Result to the exact
   Run/Plan/revision/Repository Handle/Workspace/Checkpoint and a canonical,
   ordered Evidence Manifest digest.
2. `ReviewPackageInvalidation` permanently records the first observed
   freshness or integrity failure without mutating the package.
3. `ReviewDecision` records one final local-user approve/reject outcome against
   the exact package digest.
4. `ReleaseReadinessVerdict` records one deterministic `ready` or `not_ready`
   evaluation against the package, decision, and manifest digests.

Every read exposes effective freshness. A historical `ready` verdict becomes
effectively `stale` whenever the current baseline no longer matches, even
before a durable invalidation is requested. Decision and readiness creation
lock and revalidate the baseline and trusted Evidence. PostgreSQL triggers
independently reject mutation, stale decisions, foreign digest bindings, and a
stale or rejected `ready` insert.

All four records force `git_authorization = false` and
`deployment_authorization = false`. They do not create commands, branches,
commits, remotes, pull requests, tags, or deployment actions.

## Consequences

- Reviewers inspect one stable digest-addressed Evidence Manifest rather than
  mutable Suite summaries or raw process output.
- One decision and one verdict may win under concurrency; identical retries are
  safe and conflicting outcomes return `409`.
- Staleness never rewrites historical decisions or verdicts, but it fences
  their current effect.
- The browser can perform the complete review workflow without accepting
  command, argv, cwd, environment, credential, Provider, or delivery input.
- Independent focused review and sealing remain required before local main
  integration.

## Rejected alternatives

- Updating the package or decision status in place: destroys immutable review
  history and creates stale-approval races.
- Treating Suite success as automatic approval: collapses execution evidence
  and human governance.
- Letting Review approval authorize Git delivery: exceeds this slice and
  violates least privilege.
