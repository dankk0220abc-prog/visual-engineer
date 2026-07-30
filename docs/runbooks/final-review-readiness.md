# Final review and readiness runbook

## Purpose

Use this runbook only for the local Phase 5 Third Vertical Slice review
workflow. It does not authorize Git delivery, deployment, Customer 0, a later
slice, or Phase 6.

## Preconditions

- The selected Validation Suite is terminal `succeeded` and its aggregate
  Result reconstructs from the trusted ordered Evidence chain.
- The Package response is schema version `2`, reports
  `freshness = fresh`, and shows matching package/current generations.
- Checkpoint tree/diff, source revision, Suite/Profile versions, policy digest,
  execution Grant lineage, Evidence Manifest digest, aggregate Result digest,
  and blocker-summary digest are present.
- The frozen blocker summary identifies
  `governed-review-security-findings`, includes a source version, and reports
  Critical/High/blocking-Medium counts.
- Git and deployment authorization are both `false`.

## Review procedure

1. Create a Review Package from the latest successful Suite candidate.
2. Record the Package ID, version, freshness generation, Package digest,
   Manifest digest, blocker-summary digest, and three blocker counts.
3. Recheck freshness immediately before deciding.
4. Submit approve or reasoned reject with the displayed expected generation.
   The client must retain one independent `Idempotency-Key` for retries of the
   same Decision payload.
5. Treat exact-key/exact-payload replay as the original result. Stop on a
   generation mismatch, stale response, same-key/different-payload conflict,
   or existing different terminal Decision.
6. Compute readiness only after the immutable Decision exists.
7. Treat `ready` as valid only while freshness remains `fresh`, the Decision
   is `approve`, the full digest chain matches, and blocker counts are
   `0 / 0 / 0`.

## Stale or blocked handling

Any accepted
Validation/Suite/Evidence/Workspace/Checkpoint/Repository-Handle-revision/
Grant/blocker fact change advances the database freshness generation. The
authenticated Runner registration transaction is the trusted Repository
Handle revision writer; it must update the Handle, generation, invalidation,
and invalidation AuditEvent in one commit. The old Package, Decision, and
readiness remain historical and immutable; the old effective readiness is
`stale`. Do not retry approval with the old generation or its idempotency key.

After the new trusted validation facts are complete, create a new Package
generation and perform a new Decision/readiness workflow. Never copy or attach
the old Decision to the new Package.

## Database evidence

For focused verification, confirm:

- the Package, Decision, blocker summary, and readiness digests equal
  PostgreSQL canonical recomputation;
- stale packages are invalidated and cannot receive a database-only Decision
  or `ready` row;
- the trusted Repository Handle revision transaction advances generation
  exactly once, while an exact unchanged registration does not;
- an out-of-band Handle revision drift is independently rejected by the
  Decision and readiness database insert guards;
- Critical, High, or blocking-Medium count above zero prevents approve/ready;
- direct update/delete of review records and AuditEvents fails;
- each Package has a unique monotonically increasing review-event sequence;
- replay is checked against current generation and revision before return, and
  adds no Decision or AuditEvent; and
- denied paths add no effective-ready verdict, readiness-success event, Git
  delivery Grant, Workspace/source/Evidence mutation, or duplicate charge.

## Escalation

Stop and request a new security decision for a mutable audit trail, an
unreconstructable Evidence/readiness chain, stale approval that remains
effective, any expansion into Git/deployment authority, or a new Critical/High
Finding. A successful implementer verification is only a candidate for fresh
independent focused re-review.
