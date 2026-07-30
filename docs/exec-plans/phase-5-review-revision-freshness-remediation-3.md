# Phase 5 Review revision-freshness final narrow remediation 3

## Goal

Close only `VE-P5-REVIEW-RR-001` by making concurrent identical trusted
Repository Handle revision registration reload the committed Handle state
after the existing PostgreSQL revision-authority lock. One real revision
transition must advance freshness generation exactly once.

## Scope

- Baseline:
  `a1dd0a9b68c73a45e4aa8b8754e51c385f3bad95`.
- Branch:
  `fix/phase-5-review-revision-freshness-remediation-3`.
- The locked Repository Handle lookup used by trusted registration.
- Permanent real-PostgreSQL sequential/concurrent revision replay regression
  coverage.
- This ExecPlan, its verification Evidence, `PLANS.md`, and Project Status.

## Non-goals

- Redesigning Review, changing `FR-002` through `FR-005`, changing the Review
  Decision domain, adding delivery authority, or changing an HTTP contract.
- Editing migration history or adding a migration unless the existing model
  proves insufficient.
- Editing or weakening the independent test, historical FAIL evidence, or
  audit report.
- Full `make verify`, final aggregate, E2E, Chaos, broad Security/Eval,
  sealing, main integration, remote, push, pull request, tag, or deployment.
- CreativeDeploy, Customer 0, sibling repositories, LLMs, Providers,
  credentials, or real customer repositories.

## Constraints and safety

- Operate only in `/Users/danke/Developer/VisualEngineer`.
- Local `main` must remain
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`.
- Preserve the existing advisory-lock then Handle-row-lock ordering shared
  with Review Decision/readiness writes.
- Compare canonical revision identity only after a transaction-bound reload
  of the committed Handle.
- Revision update, generation decision, invalidation, and AuditEvent remain in
  one PostgreSQL transaction and roll back together.
- Use only Compose project `ve-p5-review-freshness-remediation-3`, with every
  Docker query and cleanup filtered to that exact project.
- Stop on any user-defined Git, database, locking, regression, migration,
  cleanup, or scope mismatch.

## Current progress

- 2026-07-31 CST — **done**: exact repository, branch, HEAD, main, ancestry,
  candidate/checkpoint subjects, audit-only checkpoint scope, clean
  worktree/index/untracked, empty remote/stash/tag, and absent target branch
  verified.
- 2026-07-31 CST — **done**: branch created from the exact independent FAIL
  checkpoint without overwrite.
- 2026-07-31 CST — **done**: root agent contract, remediation-2 plan/evidence,
  single-Finding plan/evidence/report/test, current Project Status, Review
  lock order, trusted registration service/repository/model/API path,
  migrations, Makefile, package scripts, and Compose configuration inspected.
- 2026-07-31 CST — **done**: unchanged concurrent identical-revision test
  reproduced generation `1 -> 3`, one invalidation, one AuditEvent, and zero
  Decision/ready rows before production edits.
- 2026-07-31 CST — **done**: the locked opaque-Handle query now forces
  transaction-bound refresh of the already-loaded ORM entity.
- 2026-07-31 CST — **done**: unchanged failing case passes with exact
  generation `1 -> 2`; additive identical/different concurrency regressions
  observe a real PostgreSQL advisory lock wait and pass `2/2`.
- 2026-07-31 CST — **done**: original `8/8`, independent `11/11`, focused
  Review `28/28`, and affected Workspace/Validation `37/37` pass.
- 2026-07-31 CST — **done**: populated and clean migration roundtrips, clean
  migration pytest, contracts, format, lint, typecheck, build, source
  invariance, and exact task Docker cleanup pass.
- 2026-07-31 CST — **done**: six-file pre-commit scope, one-file production
  boundary, unchanged historical test/evidence, secret scan, formatting, and
  `git diff --check` reconciled.
- 2026-07-31 CST — **prepared**: create the one local checkpoint and prove
  final clean state; the exact resulting hash is reported after commit.

## Decisions

- Keep the existing transaction-level advisory mutex and Handle `FOR UPDATE`
  lock. Static inspection shows the gap is ORM identity-map reuse, not missing
  PostgreSQL serialization.
- Prefer a forced refresh on the existing locked Handle query. This preserves
  the current transaction and lock architecture without adding a migration,
  cache, process mutex, or API field.
- Preserve the independent concurrent test byte-for-byte and use it as the
  primary before/after regression.

## Risks

- A refresh applied too broadly could change unrelated Workspace reads.
  Mitigation: constrain it to the existing locked opaque-Handle lookup used
  only by trusted registration.
- Lock-order drift could deadlock Review approval/readiness.
  Mitigation: retain advisory lock before Handle row lock and rerun both
  deterministic orderings.
- A replay could still duplicate generation, invalidation, or audit history.
  Mitigation: assert the complete PostgreSQL ledger under a deterministic
  barrier.

## Discoveries

- The registration path performs an unlocked Handle lookup, takes the shared
  advisory mutex, and then performs a locked lookup in the same SQLAlchemy
  Session.
- The locked query does not currently request `populate_existing`, so an
  already-loaded Handle can retain its pre-wait revision even though
  PostgreSQL has serialized the transactions.
- The independent reproduction records generation `1 -> 3` while the
  invalidation and AuditEvent uniqueness boundaries each retain one row.

## Verification

- Git/candidate preflight: **VERIFIED**, all required success commands exit
  `0`; absent target-branch probe exits nonzero as expected.
- Original concurrent failure: **VERIFIED**, exit `1`, generation `1 -> 3`.
- Independent single-Finding matrix: **VERIFIED**, `11 passed`, exit `0`.
- Original remediation `8/8`, focused Review `28/28`, affected
  Workspace/Validation `37/37`: **VERIFIED**, each exits `0`.
- Direct-write fencing, both lock orders, forced rollback, sequential and
  concurrent replay idempotency: **VERIFIED**.
- Populated `0012 -> 0011 -> 0012`, clean
  `base -> head -> base -> head`, one migration head, and migration pytest:
  **VERIFIED**.
- Contracts, format, lint, typecheck, build, and source invariance:
  **VERIFIED**.
- Final `git diff --check`: **VERIFIED**, exit `0`.
- Post-commit clean-state inventory: **NOT YET VERIFIED**.
- Full `make verify` and final aggregate: **NOT AUTHORIZED**.

## Rollback

Stop and remove only the exact task-owned Compose project. Before commit,
revert only this remediation's explicitly owned edits with a reviewed patch;
do not reset, clean, stash, force, or overwrite any ref. No migration rollback
is expected because no schema change is planned.

## Completion conditions

- The unchanged reproduction changes from generation `1 -> 3` to exact
  `1 -> 2`, with both calls returning the same revision and generation.
- Sequential and concurrent identical replay produce one invalidation and one
  invalidation AuditEvent, stale historical readiness only once, no duplicate
  ready/blocker state, and no generation gap.
- Different revision transitions, approve-first/revision-first ordering,
  forced rollback, direct Decision/readiness fencing, and generation-scoped
  idempotency do not regress.
- Every authorized focused matrix and migration/static/build/invariance check
  passes; task Docker resources are zero; main is unchanged.
- One scoped local commit exists and worktree, index, and untracked state are
  clean.

## Outcome and follow-ups

The narrow production repair, every authorized dynamic/static check, exact
Docker cleanup, and pre-commit Git reconciliation are complete. The one local
checkpoint and post-commit clean-state inventory are performed immediately
after this plan is finalized. A successful implementer handoff may be ready
only for a fresh independent single-Finding re-review; it cannot claim Gate
PASS, sealing, main integration, or later-phase authority.
