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
   evaluation against the package, decision, manifest, policy, Suite Result,
   and blocker-summary digests.

The targeted security remediation adds an explicit
`ReviewFreshnessState` generation and append-only scoped
`ReviewBlockerFinding` facts. Package creation freezes the current generation,
Checkpoint diff, Grant lineage, Suite policy, complete Evidence Manifest, and
server-derived Critical/High/blocking-Medium summary into one PostgreSQL-
recomputed canonical digest chain. Any accepted validation, Suite, Evidence,
Checkpoint, Workspace, Grant, or blocker fact change advances the scope and
atomically appends a package invalidation event. Immutable source facts reject
in-place policy or Evidence replacement.

Every read exposes effective freshness. A historical `ready` verdict becomes
effectively `stale` whenever the current generation or baseline no longer
matches. Decision requests bind the observed generation and a persisted keyed
idempotency hash. Decision and readiness creation lock and revalidate the
baseline, trusted Evidence, policy, Grant, and blocker summary. PostgreSQL
recomputes the canonical package/Decision/readiness values, rejects mutation
or foreign bindings, and permits `ready` only for an approved current
generation whose three blocking counts are zero. Review AuditEvents carry a
package-local monotonic sequence and are append-only.

All four records force `git_authorization = false` and
`deployment_authorization = false`. They do not create commands, branches,
commits, remotes, pull requests, tags, or deployment actions.

## Consequences

- Reviewers inspect one stable digest-addressed Evidence Manifest rather than
  mutable Suite summaries or raw process output.
- One decision and one verdict may win under concurrency; exact-key/exact-
  payload retries return the original Decision and key reuse with a different
  payload returns `409`.
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
