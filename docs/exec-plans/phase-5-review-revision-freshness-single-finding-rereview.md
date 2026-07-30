# Phase 5 Review revision-freshness independent single-Finding re-review

## Goal

Independently re-review only `VE-P5-REVIEW-RR-001` at exact remediation
candidate `efeecda57109ff8c3470f83a2aeb659e7ead31be`. Prove trusted
revision-generation atomicity, old-generation Decision/readiness fencing,
deterministic locking, replay idempotency, append-only invalidation evidence,
and migration integrity before any final aggregate or sealing decision.

## Scope

- Candidate range:
  `cce04d460a40416bc01f6ca2b44ee71948775c88..efeecda57109ff8c3470f83a2aeb659e7ead31be`.
- Independent branch:
  `audit/phase-5-review-revision-freshness-single-finding-rereview`.
- The unchanged original Finding test and seven-case permanent remediation
  matrix.
- One additive independent real-PostgreSQL audit test.
- This ExecPlan, independent audit report, verification evidence, `PLANS.md`,
  and Project Status.
- Read-only inspection of the candidate migration, trusted Repository Handle
  writer, Review repository/service paths, Decision/readiness guards,
  generation/invalidation functions, tests, and governance documents.

## Non-goals

- Reopening the complete five-Finding Third Slice review.
- Modifying migration, API, repository, service, model, schema, Web, Runner,
  protocol, generated contract, or any other production code.
- Repairing the Finding during this independent review.
- Running the `28/28`, `37/37`, migration roundtrip, or final `make verify`
  after a conclusive blocking single-Finding failure.
- Sealing, main integration, remote, push, pull request, tag, deployment,
  CreativeDeploy, Customer 0, another repository, later slice, or Phase 6.

## Constraints and safety

- The only repository root used after instruction intake is
  `/Users/danke/Developer/VisualEngineer`.
- Repository identity, main/candidate hashes, ancestry, candidate scope,
  historical evidence, clean-state, remote/stash/tag, or test-integrity
  mismatches are stop conditions.
- The original independent Finding test and historical FAIL documents remain
  byte-identical.
- The reviewer may add audit-owned tests and documents but cannot edit
  production code or weaken an existing test.
- PostgreSQL uses only Compose project
  `ve-p5-review-freshness-rereview` on bind-probed loopback port `62941`.
- A non-idempotent repeated revision invalidation is an explicit FAIL
  condition and makes aggregate/sealing ineligible.

## Current progress

- 2026-07-31 CST — **done**: exact Developer repository, branch, HEAD, main,
  clean worktree/index/untracked, no remote/stash/tag, candidate objects,
  ancestry, direct parent, subject, and candidate range verified.
- 2026-07-31 CST — **done**: target audit branch confirmed absent and created
  from the exact candidate.
- 2026-07-31 CST — **done**: original Finding test and three historical FAIL
  documents verified byte-identical; no skip/xfail weakening found.
- 2026-07-31 CST — **done**: AGENTS, PLANS, focused review/re-review,
  remediation plan/evidence, Project Status, migration graph, build/test
  entrypoints, Review/Workspace services, database functions/triggers, and
  candidate tests inspected.
- 2026-07-31 CST — **done**: unchanged original Finding plus permanent
  remediation matrix passed `8/8`.
- 2026-07-31 CST — **done**: final independent audit matrix produced
  `10 passed, 1 failed`; old-generation Decision/readiness, deterministic
  approve/revision orderings, rollback atomicity, AuditEvent immutability, and
  sequential replay controls passed.
- 2026-07-31 CST — **done**: concurrent same-revision trusted registration
  replay produced generation `1 -> 3`; the deterministic focused case failed
  on two unchanged reruns and again in the final audit matrix.
- 2026-07-31 CST — **stopped**: `28/28`, `37/37`, migration roundtrip, broad
  static/build gates, final `make verify`, Final Gate cleanup probe, and
  sealing are not eligible.
- 2026-07-31 CST — **done**: exact audit-owned PostgreSQL resources removed;
  filtered container/network/volume inventories are empty, cleanup replay
  exits zero, and port `62941` is free.
- 2026-07-31 CST — **prepared**: audit-only FAIL checkpoint; its exact hash
  and final clean Git reconciliation are reported after commit.

## Decisions

- Keep the Finding identifier `VE-P5-REVIEW-RR-001`; the reproduced defect is
  inside its explicit invalidation-replay idempotency acceptance boundary, not
  a reopened FR-002/003/004/005 review.
- Classify the initial Ruff format failure and first mypy redundant-cast
  failure as audit-only quality failures. Both were corrected only in the new
  audit test.
- Classify five assertions in the first expanded run as audit-test mistakes:
  three used the wrong invalidation primary-key assumption and two expected a
  constraint SQLSTATE even though the literal exceeds the 16-character
  database column. Corrected assertions retained all secure expectations.
- Treat generation `1 -> 3` for two concurrent identical trusted
  registrations as a blocking single-Finding failure. One invalidation/event
  does not cure the extra generation advance or the resulting generation gap.
- Stop without promoting implementer evidence or running any aggregate that
  cannot change the FAIL disposition.

## Risks

- Concurrent identical trusted revision reports can advance freshness more
  than once for one real authority change.
- Extra generation advances can skip the generation a client expects and can
  force unnecessary Package/Decision recreation.
- The currently reproduced case creates no stale Decision or ready row, but it
  violates the required monotonic exact-once generation and replay contract.

The production owner must repair the locked revision comparison and then
request another independent single-Finding review.

## Discoveries

- The shared advisory lock correctly serializes approve-first and
  revision-first orders; PostgreSQL reports the losing transaction waiting on
  an advisory `Lock`.
- A committed trusted revision change advances generation by one, creates one
  invalidation/event, stales historical readiness, and rejects old keyed
  replay.
- A forced pre-commit failure rolls revision, generation, invalidation, and
  event back together.
- Direct old-revision approve/reject writes fail with SQLSTATE `55000`;
  `changes_requested` is rejected by both the API and PostgreSQL closed
  storage boundary; direct stale ready fails with `55000`.
- In the concurrent identical-registration case, both responses report the
  same new revision, the current revision is correct, and invalidation/event
  counts remain one, but generation advances twice.
- Static inspection localizes the incorrect comparison to the transition from
  the initial unlocked Handle read to the post-advisory locked read in the
  same SQLAlchemy Session.

## Verification

- Git/candidate preflight: **PASS**; required commands exit `0`, and the
  expected absent audit-branch probe exits `1`.
- Migration graph static check: **PASS**, one head `20260730_0012`.
- Original Finding plus permanent remediation tests: **PASS**, exit `0`,
  `8 passed`.
- First independent expanded run: **INVALID MIXED ATTEMPT**, exit `1`,
  `5 passed, 6 failed`; five audit-test defects were corrected without
  production changes.
- Corrected expanded run: **FAIL**, exit `1`, `10 passed, 1 failed`.
- Deterministic concurrent duplicate revision case: **FAIL**, exit `1`, and
  one unchanged rerun also exits `1`; both record generation `1 -> 3`.
- Final independent matrix from the final audit test file: **FAIL**, exit `1`,
  `10 passed, 1 failed`, same generation assertion.
- Audit test Ruff format/lint and mypy: **PASS** after the preserved audit-only
  failures.
- `28/28`, `37/37`, dynamic migration roundtrip, contracts, full format/lint/
  typecheck/build/source-invariance harness, final `make verify`, E2E,
  accessibility, Security, Eval, Chaos, and sealing: **NOT RUN** after the
  explicit blocker stop.

Exact commands, SQLSTATEs, database ledgers, first failures, and cleanup facts
are in
[`docs/evidence/phase-5-review-revision-freshness-single-finding-rereview-verification.md`](../evidence/phase-5-review-revision-freshness-single-finding-rereview-verification.md).

## Rollback

The audit branch contains no production change. Exact Compose cleanup has
already removed the task-owned database. If the audit package must be
abandoned, remove only its audit test, ExecPlan, report, evidence, and
status/index edits. Do not reset, clean, stash, or alter the candidate or
historical records.

## Completion conditions

This review completes as FAIL when:

- the unchanged `8/8` minimum matrix is preserved;
- the non-idempotent concurrent replay is stable in an additive independent
  test;
- initial audit-test failures remain distinguished from the production
  failure;
- aggregate and sealing remain not run;
- production code is byte-identical to the candidate;
- exact audit-owned Docker inventories are zero and the port is free;
- main remains unchanged;
- only audit-owned test/documents are committed; and
- worktree, index, and untracked state are clean after the FAIL checkpoint.

## Outcome and follow-ups

**COMPLETE — SINGLE-FINDING RE-REVIEW FAIL — REMEDIATION REQUIRED.**

The next eligible milestone is a narrow production remediation that compares
the post-lock committed Repository Handle state before deciding whether to
advance freshness, followed by another fresh independent review of
`VE-P5-REVIEW-RR-001`. Final aggregate, sealing, main integration, delivery,
CreativeDeploy, Customer 0, later phases, and Phase 6 remain unauthorized.
