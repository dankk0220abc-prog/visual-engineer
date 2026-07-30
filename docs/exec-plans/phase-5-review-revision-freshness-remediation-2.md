# Phase 5 final review revision freshness remediation 2

## Goal

Close only `VE-P5-REVIEW-RR-001` by making a trusted Repository Handle
revision/status change advance the durable Review freshness generation in the
same PostgreSQL transaction, invalidate every affected old Package, append one
immutable invalidation AuditEvent per Package, and database-fence old
Decision/readiness inserts and keyed replays. Preserve `FR-002` through
`FR-005`, the independent re-review FAIL checkpoint, and every unchanged
independent assertion.

## Scope

- Baseline:
  `cce04d460a40416bc01f6ca2b44ee71948775c88`.
- Branch:
  `fix/phase-5-review-revision-freshness-remediation-2`.
- One additive Alembic migration after `20260730_0011`.
- Narrow Review service ordering changes for generation/freshness validation
  before Decision idempotency replay.
- Permanent real-PostgreSQL revision freshness, direct-write, concurrency,
  idempotency, AuditEvent, and no-side-effect regressions.
- Focused architecture, security, runbook, project-status, and verification
  evidence updates.

## Non-goals

- Redesigning the Third Slice or adding a new Review Decision state. The
  existing closed terminal Decision domain is `approve` / `reject`;
  `changes_requested` remains rejected by the API and PostgreSQL.
- Modifying `FR-002`, `FR-003`, `FR-004`, or the `FR-005` blocker-summary
  design.
- LLM, Customer 0, CreativeDeploy, another repository, Git delivery,
  remote/push/merge/pull request/tag, deployment, sealing, Gate PASS, another
  Phase, or a later slice.
- Full `make verify`, full E2E, Chaos, Security, or Eval in this remediation
  conversation.

## Constraints and safety

- Operate only in `/Users/danke/Developer/VisualEngineer`.
- Local `main` must remain
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`.
- Do not delete, edit, skip, xfail, or relax
  `test_p5_review_rereview_001_repository_revision_change_rejects_database_ready_chain`.
- Revision change, generation advance, invalidation, and invalidation
  AuditEvent must commit or roll back together.
- Old Decisions/readiness remain immutable history but cannot be effective or
  replayed into the new generation.
- Every denied path must add zero approved Decision, effective ready row,
  readiness-success event, delivery Grant, duplicate invalidation event, or
  Workspace/source/Evidence mutation.
- Stop for the user-specified Critical/High, data-damage, unpreventable stale
  approval, database-fencing, prohibited-scope, or source/canonical Workspace
  conditions.

## Current progress

- 2026-07-30 CST — **done**: exact repository, refs, ancestry, audit-only
  checkpoint scope, clean state, absent remote/stash/tag/lock, and absent
  remediation branch verified.
- 2026-07-30 CST — **done**: branch created from the exact FAIL checkpoint.
- 2026-07-30 CST — **done**: re-review report/evidence/plan/test, previous
  remediation plan/evidence, Review service/repository/models/API/Web,
  revision authority, migrations `0010`/`0011`, and focused governance
  documents read.
- 2026-07-30 CST — **done**: unchanged independent test run twice against
  task-owned PostgreSQL; both runs failed at the same final secure assertion
  with `(True, True, 1, 1, 0)`.
- 2026-07-30 CST — **done**: the sole trusted Repository Handle revision
  writer now serializes with Review writes and advances affected freshness
  scopes in its registration transaction; direct Decision/readiness revision
  guards and pre-replay generation validation are installed additively.
- 2026-07-30 CST — **done**: unchanged Finding plus permanent remediation
  tests pass `8/8`; the focused Review/FR-002/003/004/005 matrix passes
  `28/28`; Workspace/Validation affected tests pass `37/37`.
- 2026-07-30 CST — **done**: populated `0012 -> 0011 -> 0012`, clean
  `base -> head -> base -> head`, the clean migration pytest, contracts,
  lint, typecheck, build, and source invariance pass.
- 2026-07-30 CST — **done**: focused documentation, final formatting,
  Git/invariance inventory, and task-owned PostgreSQL cleanup.
- 2026-07-30 CST — **done**: one exact local checkpoint is authorized with
  subject `fix(review): fence decisions on revision freshness generation`;
  the post-commit clean-state inventory is the final handoff check.

## Root cause and repair matrix

| Boundary                      | Confirmed gap                                                                                                                               | Repair                                                                                                                                                                                                                | Closing evidence                                                                       |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Repository revision authority | the authenticated Runner registration transaction changed `repository_handles.current_revision` without advancing `review_freshness_states` | serialize the sole trusted writer with Review writes and call an additive database function that advances each affected scope once through the existing atomic invalidation/event function                            | generation `+1`, stale Package, one invalidation/event, unchanged registration no bump |
| Direct Decision insert        | migration `0011` replaced the `0010` guard without rechecking the trusted Repository Handle                                                 | Add a database insert guard that locks and compares Handle status/revision with the frozen Package revision                                                                                                           | old-generation direct approve/reject rejected                                          |
| Direct readiness insert       | migration `0011` relies on generation/invalidation but omits direct revision authority recheck                                              | Add the same trusted Handle comparison before any readiness insert                                                                                                                                                    | stale direct `ready` rejected                                                          |
| Decision idempotency replay   | keyed replay is returned before current-generation/freshness validation                                                                     | Validate locked scope generation and freshness before replay lookup/return                                                                                                                                            | exact replay succeeds only while current; old-generation key returns conflict          |
| Revision/approve race         | Handle update and Decision insert can overlap                                                                                               | a transaction-level advisory mutex plus Handle/Package/scope row locks serialize the trusted authority and Decision transactions; generation/invalidation plus the direct guard make the final state order-consistent | independent transactions; no effective stale approval                                  |

## Decisions

- Reuse the existing `bump_review_freshness_scope` function so generation,
  invalidation, and package-local AuditEvent retain the already-reviewed
  `FR-003` ordering and idempotency behavior.
- Select distinct affected freshness scopes by immutable Package
  `repository_handle_id`, in deterministic order, so one Handle update
  advances each scope once even when it has multiple historical Packages.
- Treat authenticated Runner repository registration as the sole trusted
  revision-authority writer. Static search confirms no other API production
  service writes `RepositoryHandle.current_revision`. It acquires the shared
  revision advisory mutex and Handle row lock, flushes the revision/status
  update, and invokes the database scope-bump function before the same commit.
- Do not reinterpret an arbitrary direct table update as an accepted trusted
  revision event. Such drift is deliberately caught by independent
  database-insert revision guards, which reject both Decision and readiness.
  This preserves the unchanged independent reproduction while preventing a
  database-only stale ready chain.
- Advance only on null-safe changes to `current_revision` or transition back
  to `available`; an exact re-registration does not advance generation.
- Keep direct Decision/readiness revision guards independent of the trusted
  writer. Generation is the primary accepted-transition fence; direct
  trusted-revision checks fail closed against out-of-band drift at the
  database insert boundary.
- Do not add persistent columns or change HTTP schemas. The migration changes
  PostgreSQL functions/triggers only, so generated contracts should remain
  unchanged.

## Verification plan

1. Preserve the two unchanged pre-repair failures.
2. Run the original independent Finding test after repair.
3. Run the permanent revision freshness and PostgreSQL
   concurrency/idempotency matrix.
4. Run focused Review API and unchanged `FR-002`/`FR-003`/`FR-004`/`FR-005`
   tests.
5. Run migration upgrade/downgrade/re-upgrade.
6. Run format-check, lint, typecheck, affected backend tests, Web build,
   source/canonical Workspace invariance, and `git diff --check`.
7. Do not run full `make verify`, full E2E, Chaos, Security, or Eval.

## Rollback

Downgrade `20260730_0012` to `20260730_0011`; this removes only the shared
revision-authority mutex, trusted registration scope-bump function, and the
two defense-in-depth revision insert guards/functions. Stop and remove only
the exact task-owned Compose project. Do not reset, stash, clean, overwrite
another branch, or alter historical migrations/evidence.

## Completion conditions

- The unchanged independent test changes from the preserved stable failure to
  pass.
- Revision/status changes advance generation monotonically and atomically
  persist one invalidation and one AuditEvent per affected Package.
- Old-generation terminal Decisions, direct database inserts, readiness, and
  keyed replay fail closed.
- A new trusted generation/Package can be reviewed without reusing an old
  Decision.
- Existing checkpoint/tree/policy/Grant/blocker freshness, canonical digests,
  append-only events, idempotency, blocker readiness, and no-delivery
  authority do not regress.
- Required focused verification passes; local `main` is unchanged; no
  prohibited repository or delivery action occurs.
- One local commit has subject
  `fix(review): fence decisions on revision freshness generation`, followed by
  a clean worktree/index/untracked inventory.

## Outcome

Implementation, the authorized focused verification, tracked-document
formatting, closeout inventory, and task-owned database cleanup are complete.
The exact local checkpoint subject is fixed below; its resulting hash and
post-commit clean-state inventory are recorded in the final handoff. No full
aggregate was run. The only successful outcome label is:

`PHASE 5 REVIEW REVISION FRESHNESS REMEDIATION COMPLETE — READY FOR INDEPENDENT SINGLE-FINDING RE-REVIEW`
