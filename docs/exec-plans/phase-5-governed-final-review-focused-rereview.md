# Phase 5 governed final review independent focused re-review

## Goal

Independently re-review only `VE-P5-REVIEW-FR-001` through
`VE-P5-REVIEW-FR-005` at remediation candidate
`3eddb9623550227a30013df6dbc6dc7a17d5315c`. The review must prove generation
freshness, canonical Package/Decision/readiness integrity, append-only review
AuditEvents, expected-generation keyed Decision semantics, and trusted
blocker-gated readiness before any final aggregate or PASS sealing.

## Scope

- Remediation range:
  `5371495b1dd27db2ff3bbca4ddc12eaee47e7982..3eddb9623550227a30013df6dbc6dc7a17d5315c`.
- Review branch: `audit/phase-5-governed-final-review-reaudit-max`.
- The unchanged original focused-audit file.
- One independent real-PostgreSQL secure-expectation test.
- This ExecPlan, the focused re-review report, verification evidence, and
  project status.
- Read-only inspection of the complete remediation diff and the Review
  migration, model, service, API, generated contract, and Web boundaries.

## Non-goals

- Re-auditing Phase 4 or the first two Phase 5 slices.
- Re-reviewing ordinary Third Slice product behavior.
- Modifying API, migration, model, repository, service, Web, generated
  contract, Runner, or any other production code.
- Repairing a Finding during the independent review.
- Running `make verify` after a blocking focused Finding.
- Main integration, remote delivery, push, pull request, tag, Customer 0,
  CreativeDeploy, a later slice, or Phase 6.

## Constraints and safety

- The only repository root used after instruction intake is
  `/Users/danke/Developer/VisualEngineer`.
- Git identity, ancestry, one-commit remediation scope, historical evidence,
  and clean-state mismatches are stop conditions.
- Historical focused-review tests and FAIL documents remain unchanged.
- Critical, High, or blocking Medium incorrect approval/readiness, digest
  forgery, or mutable audit history stops aggregate expansion.
- Audit-owned PostgreSQL projects use unique Compose labels and bind-probed
  loopback ports. Cleanup removes only those exact projects.
- Production code remains byte-for-byte equal to the remediation candidate.

## Current progress

- 2026-07-30 CST — **done**: exact Developer repository, branch, HEAD, main,
  worktree, index, untracked, remote, stash, tag, worktree, heads, Git locks,
  objects, ancestry, parent, and one-commit range verified.
- 2026-07-30 CST — **done**: original focused test and three historical FAIL
  documents verified unchanged; no test deletion, skip, xfail, or assertion
  weakening found.
- 2026-07-30 CST — **done**: independent branch created from the exact
  remediation candidate.
- 2026-07-30 CST — **done**: required plans, reports, evidence, project
  status, migration, models, repository, schemas, service, API, blocker and
  digest reconstruction, AuditEvent guards, and Review Web flow inspected.
- 2026-07-30 CST — **done**: unchanged six-test original focused matrix passed
  against task-owned real PostgreSQL.
- 2026-07-30 CST — **done**: independent revision-freshness/database-boundary
  secure expectation failed on its first run and one unchanged rerun.
- 2026-07-30 CST — **done**: one new blocking Medium Finding recorded.
- 2026-07-30 CST — **stopped**: remaining expanded focused matrix, final
  `make verify`, migration roundtrip, browser expansion, final cleanup probe,
  and PASS sealing are not eligible.
- 2026-07-30 CST — **prepared**: audit-only FAIL checkpoint; its exact hash is
  reported administratively after commit.

## Decisions

- Treat repository revision authority as a freshness fact because the
  candidate itself reports a Package stale when that authority no longer
  matches.
- Treat the database insert guards as an explicit security boundary. A stale
  Package must not acquire a canonical approved Decision or durable `ready`
  row even if the read path later reports the effective verdict as stale.
- Classify the stable accepted stale approval/readiness chain as blocking
  Medium because it violates FR-001 database fencing, FR-005
  approved-readiness correctness, and the required zero-approved-decision
  rejection invariant.
- Stop without running the aggregate or attempting a production repair.

## Finding

| ID                    | Severity        | Boundary        | Result                                                                                                                                                                              |
| --------------------- | --------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VE-P5-REVIEW-RR-001` | blocking Medium | FR-001 / FR-005 | A trusted revision-authority change is visible as stale to the API but does not advance generation; PostgreSQL accepts an approved Decision and `ready` row for the old generation. |

## Verification

- Git preflight: **PASS**.
- Unchanged original focused matrix: **PASS**, exit `0`, `6 passed`.
- New independent secure expectation, first run: **FAIL**, exit `1`,
  `1 failed`.
- Same test, unchanged rerun: **FAIL**, exit `1`, same final assertion and
  durable row counts.
- Audit-test Ruff format, lint, and mypy: **PASS**, exit `0`.
- First new-document Prettier check: **AUDIT-ONLY FORMAT FAILURE**, exit `1`;
  only the three new documents were mechanically formatted.
- Static trigger inventory: **CONFIRMED** that the revision authority is
  checked during Package creation/read freshness but has no automatic
  freshness-generation trigger.
- Final `make verify`: **NOT RUN** after the blocking stop.

Exact commands, exit codes, first-failure facts, and cleanup evidence are in
[`docs/evidence/phase-5-governed-final-review-focused-rereview-verification.md`](../evidence/phase-5-governed-final-review-focused-rereview-verification.md).

## Rollback

Every dynamic check used an exact audit-owned Compose project. If this FAIL
package must be abandoned, remove only its one audit test and four audit/status
documents. Do not reset, clean, stash, or modify the candidate or historical
records.

## Completion conditions

This focused re-review completes as FAIL when:

- the blocking Finding is preserved by a minimal real-PostgreSQL test;
- its unchanged rerun reaches the same secure assertion;
- the first failure and stopped-gate decision remain disclosed;
- production code is unchanged from the candidate;
- exact audit-owned Docker inventories are zero;
- main remains unchanged;
- only authorized audit artifacts are committed; and
- the worktree, index, and untracked inventory are clean after the checkpoint.

## Outcome and follow-up

**COMPLETE — FOCUSED RE-REVIEW FAIL — REMEDIATION REQUIRED.**

The next eligible milestone is a narrow production remediation that makes
every trusted revision-authority change advance or otherwise database-fence
the Package generation before Decision/readiness inserts, followed by a fresh
independent focused re-review. Main integration and later phases remain
unauthorized.
