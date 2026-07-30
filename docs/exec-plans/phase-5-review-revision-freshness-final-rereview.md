# Phase 5 Review revision-freshness final independent re-review

- Started: 2026-07-31 (Asia/Shanghai)
- Branch:
  `audit/phase-5-review-revision-freshness-final-rereview`
- Candidate:
  `7450d4665d682db808692347860a602809bfa080`
- Main baseline:
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Finding: `VE-P5-REVIEW-RR-001`
- Status: `COMPLETE — PASS — SEALING PREPARED`

## Goal

Independently decide only whether concurrent authenticated registration of the
same trusted Repository Handle revision reloads committed PostgreSQL state
after the revision-authority lock and advances freshness generation exactly
once. If that single Finding and every required non-regression gate pass, run
one complete `make verify` and create the local Third Slice sealing commit.

## Scope

- Exact remediation candidate
  `7450d4665d682db808692347860a602809bfa080`.
- The one locked Repository Handle query changed by remediation 3.
- The byte-unchanged independent single-Finding test.
- The permanent remediation-3 identical/different revision concurrency tests.
- Original `8/8`, Review `28/28`, and Workspace/Validation `37/37` matrices.
- Populated and clean migration roundtrips, contracts, format, lint,
  typecheck, build, source invariance, one complete `make verify`, and exact
  Docker cleanup.
- This ExecPlan, its Evidence, Project Status, and the ExecPlan index.

## Non-goals

- Reopening or redesigning `FR-002`, `FR-003`, `FR-004`, or `FR-005`.
- Editing production code, migration history, generated contracts, tests, or
  historical FAIL records during the review.
- Moving `main`, merging, rebasing, cherry-picking, resetting, stashing,
  pushing, creating a pull request, tagging, deploying, or starting another
  phase.
- CreativeDeploy, Customer 0, sibling repositories, real customer
  repositories, Providers, credentials, or remote CI.

## Constraints and safety

- Operate only in `/Users/danke/Developer/VisualEngineer`.
- Stop on any repository, HEAD, main, clean-state, ancestry, object, or target
  branch mismatch.
- A same-revision result other than exact generation `1 -> 2` is a blocking
  Finding failure and forbids aggregate verification and sealing.
- Preserve the independent test and historical FAIL Evidence/ExecPlan/audit
  report byte-for-byte.
- Use only task-owned Compose projects and bind-probed loopback ports. Never
  stop an unknown process.
- Audit-only documentation is the only permitted reviewer write before the
  sealing commit.

## Current progress

- done — root `AGENTS.md`, relevant ADR, architecture, product, security,
  runbook, prior FAIL, remediation plan/evidence, source, migrations, tests,
  and gate entrypoints reviewed
- done — exact repository, candidate HEAD, main, clean index/worktree/
  untracked inventory, ancestry, merge-base, non-merge range, empty
  remote/stash/tag inventory, no in-progress Git operation, and absent audit
  branch verified
- done — independent audit branch created directly from the exact candidate
- done — production diff statically reduced to the locked Handle query using
  `FOR UPDATE` plus `populate_existing=True`
- done — independent test SHA-256 confirmed unchanged as
  `438acf304880b11e5f57aa198da7c918b1dc96a5bf357d507e063bc46b5c7559`
- done — real PostgreSQL identical/different concurrent revision tests pass
  `2/2` with observed advisory lock waits
- done — byte-unchanged independent single-Finding file passes `11/11`
- done — original matrix passes `8/8`, Review matrix passes `28/28`, and
  Workspace/Validation matrix passes `37/37`
- done — populated `0012 -> 0011 -> 0012`, clean
  `base -> head -> base -> head`, one migration head, and migration pytest
  pass
- done — contracts, format, lint, typecheck, build, source invariance, and
  `git diff --check` pass
- done — exactly one complete `make verify` passes with exit `0`
- done — all task-owned Compose container/network/volume inventories are zero,
  cleanup replay passes, and every selected port is free
- done — independent Evidence, this ExecPlan, Project Status, and ExecPlan
  index finalized without production edits
- prepared — create the one local sealing commit; its resulting hash and final
  clean state are reported after commit

## Decisions

1. Treat the existing independent test as the primary regression and leave it
   byte-identical.
2. Accept the additive remediation-3 concurrency tests as supporting evidence
   only after independently inspecting their barriers, `pg_stat_activity`
   lock probe, response assertions, and final database ledger.
3. Require both the same-revision exact-once case and the different-revision
   `1 -> 3` case so the repair cannot collapse two real transitions.
4. Preserve the first migration-order failure as an invalid non-clean attempt:
   populated Validation rows were incorrectly carried into a gate explicitly
   requiring a clean database. Recreate only the audit-owned tmpfs database,
   then execute the clean roundtrip unchanged.
5. Run the complete aggregate once, only after every focused gate passes.
6. Keep all historical FAIL artifacts unchanged; this final result is
   additive evidence, not a rewrite of prior decisions.

## Risks

- An ORM identity-map value could remain stale after a real PostgreSQL wait.
  The deterministic concurrent test requires the second backend to be
  observed waiting on `Lock/advisory` and both callers to observe generation
  `2`.
- Over-refreshing an unlocked lookup could alter unrelated Workspace reads.
  Static review confirms `populate_existing=True` is limited to the existing
  locked lookup.
- Lock-order drift could deadlock approval or revision registration. Both
  approve-first and revision-first cases observe the waiting advisory lock
  and terminate with the expected database ledger.
- A replay could preserve one invalidation while still skipping a generation.
  The final scope generation, response generations, invalidation count, and
  AuditEvent count are checked independently.

## Discoveries

- The existing advisory transaction lock already serialized the two
  transactions. The former defect was post-wait ORM state reuse, not absence
  of PostgreSQL locking.
- `populate_existing=True` on the locked query reloads the committed Handle
  row after the wait. Two identical callers then return the same revision and
  generation `2`.
- Two different revisions remain two real transitions and finish at
  generation `3`; invalidation and AuditEvent remain unique for the historical
  Package.
- Direct stale Decision/readiness inserts, old-generation keyed replay, and
  AuditEvent mutation remain independently fenced.

## Verification

| Gate                                            | Result                   |
| ----------------------------------------------- | ------------------------ |
| concurrent identical/different revision support | `2 passed`, exit `0`     |
| unchanged independent single-Finding file       | `11 passed`, exit `0`    |
| original Finding/remediation matrix             | `8 passed`, exit `0`     |
| focused Review matrix                           | `28 passed`, exit `0`    |
| affected Workspace/Validation matrix            | `37 passed`, exit `0`    |
| migration pytest                                | `1 passed`, exit `0`     |
| populated and clean migration roundtrips        | pass, exit `0`           |
| contracts/format/lint/typecheck/build           | pass, exit `0`           |
| source invariance                               | `PASS`, exit `0`         |
| one complete `make verify`                      | pass, exit `0`           |
| exact Docker cleanup and replay                 | zero resources, exit `0` |
| candidate production-tree invariance            | pass, empty diff         |

Exact commands, ledgers, SQLSTATEs, aggregate totals, first failure, and
cleanup facts are recorded in
[`docs/evidence/phase-5-review-revision-freshness-final-rereview-verification.md`](../evidence/phase-5-review-revision-freshness-final-rereview-verification.md).

## Rollback

Stop and remove only the exact task-owned Compose projects. Before the sealing
commit, abandon only the new audit governance documents with a reviewed patch
if required. Do not reset, clean, stash, force, rewrite history, edit
production code, or move any existing ref.

## Completion conditions

- Candidate and main remain exact and the audit branch remains candidate-based.
- Identical concurrent registration is exact `1 -> 2`; both responses return
  the same revision and generation; invalidation/AuditEvent are `1/1`.
- Sequential replay advances only once; different concurrent revisions finish
  at `1 -> 3`.
- PostgreSQL lock wait, post-lock committed state, both Review lock orders,
  rollback atomicity, stale direct-write fencing, keyed replay fencing, and
  append-only AuditEvent behavior all pass.
- Every focused, migration, static/build/invariance, aggregate, and cleanup
  gate passes.
- Reviewer production diff from the candidate is empty.
- One local sealing commit exists; main remains unchanged; no remote, push,
  pull request, tag, deploy, merge, or delivery occurs.

## Outcome and follow-ups

`VE-P5-REVIEW-RR-001` independently passes. The Third Slice Final Gate passes
with one complete aggregate and exact task-owned cleanup. The only next
eligible action after the local sealing commit is an explicitly
user-authorized local fast-forward of `main`.

`PHASE 5 THIRD SLICE FINAL GATE PASS — SEALED AND AWAITING EXPLICIT USER AUTHORIZATION FOR LOCAL FAST-FORWARD MAIN`
