# Phase 5 Review revision-freshness independent single-Finding re-review

## Decision

- Candidate: `efeecda57109ff8c3470f83a2aeb659e7ead31be`
- Candidate parent / previous independent FAIL:
  `cce04d460a40416bc01f6ca2b44ee71948775c88`
- Main: `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Review branch:
  `audit/phase-5-review-revision-freshness-single-finding-rereview`
- `VE-P5-REVIEW-RR-001`: **FAIL**
- Severity: blocking Medium
- Final aggregate: **NOT RUN**
- Sealing: **NOT ELIGIBLE**
- Production changes by reviewer: **none**

The candidate closes the original stale Decision/readiness database chain and
passes the unchanged minimum `8/8` matrix. It does not satisfy the same
Finding's invalidation replay idempotency boundary: two concurrent identical
trusted revision registrations advance one freshness scope twice.

## Finding disposition

### VE-P5-REVIEW-RR-001

- Trigger: two authenticated trusted registration transactions concurrently
  report the same new revision for one existing Repository Handle and one
  Package freshness scope.
- Expected: exactly one accepted authority transition, generation `1 -> 2`,
  one invalidation, one invalidation AuditEvent, and no Decision or ready row.
- Actual: both registrations return the same new revision; generation becomes
  `3`, while invalidation rows/events remain `1/1` and Decision/ready rows
  remain `0/0`.
- Finding: repeated concurrent handling of the same trusted revision change is
  not idempotent and creates a generation gap.
- Test:
  `test_audit_concurrent_duplicate_revision_replay_advances_once`
- Stability: failed in the corrected expanded matrix, in two deterministic
  focused runs, and in the final `11`-case audit matrix.
- Exit code: `1`.
- Production-hash status: unchanged from candidate.
- Severity: blocking Medium.

## Passing single-Finding controls

- Unchanged original Finding plus permanent remediation matrix: `8/8`.
- One committed trusted revision change advances generation exactly once,
  persists one invalidation/event, and makes historical readiness effectively
  stale.
- A forced commit failure rolls revision, generation, invalidation, and event
  back together.
- Old-generation `approve` and `reject` repository writes fail with SQLSTATE
  `55000`.
- `changes_requested` is rejected by API and PostgreSQL storage boundaries.
- Direct stale readiness insertion fails with SQLSTATE `55000`.
- Approve-first ordering commits one historical Decision, then the trusted
  revision transaction invalidates it before any ready row.
- Revision-first ordering makes the waiting approval fail with
  `review_generation_mismatch`.
- Old-generation keyed replay returns `409`.
- Invalidation AuditEvent update/delete attempts fail with SQLSTATE `55000`.
- No passing or failing case creates Git, pull-request, merge, tag,
  deployment, or later-phase authority.

## Root-cause boundary

The trusted registration path performs an unlocked Handle lookup before the
shared advisory lock, then performs a locked lookup in the same ORM Session.
The dynamic evidence shows that a transaction which waited for its peer can
still compare the pre-wait revision and invoke the generation bump again.

The minimal repair boundary is the post-lock trusted Handle reload/comparison.
No Review redesign, schema expansion, Decision-state addition, or wider Phase
5 change is required.

## Stop decision

Non-idempotent invalidation replay is an explicit single-Finding FAIL
condition. The `28/28` Review matrix, `37/37` Workspace/Validation matrix,
dynamic migration roundtrips, final `make verify`, E2E/accessibility,
Security/Eval/Chaos, Final Gate cleanup probe, and sealing were not run.
Implementer evidence was not promoted into this decision.

The audit-owned PostgreSQL project was removed exactly; filtered
container/network/volume inventories are empty, cleanup replay succeeds, and
its loopback port is free. Main is unchanged. No remote, push, pull request,
merge, tag, deployment, CreativeDeploy, sibling repository, Customer 0, later
slice, or Phase 6 action occurred.

**PHASE 5 REVIEW REVISION FRESHNESS SINGLE-FINDING RE-REVIEW FAIL — REMEDIATION REQUIRED**
