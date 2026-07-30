# Phase 5 governed final review independent focused review

## Goal

Independently review the Phase 5 Third Vertical Slice at exact candidate
`c2054469c8d10441bcab8ade89c52de1f9aa893f` for Review Package integrity,
freshness, Evidence completeness, Decision concurrency/idempotency, Release
Readiness correctness, delivery-authority separation, and audit immutability.
If any blocking defect can produce stale or forged readiness or rewrite its
audit history, preserve a minimal reproduction and stop before the aggregate.

## Scope

- Candidate range:
  `50dcc05ce48d042882bcdf199ae1bee662a83af6..c2054469c8d10441bcab8ade89c52de1f9aa893f`.
- Review branch: `audit/phase-5-governed-final-review-focused-max`.
- One independent real-PostgreSQL/API test file.
- This ExecPlan, the focused security report, verification evidence, and
  project status.
- Read-only inspection of the complete Third Slice implementation, migration,
  Web workflow, contracts, tests, and governance documents.

## Non-goals

- Re-auditing Phase 4 or either sealed Phase 5 slice.
- Modifying API, migration, model, repository, service, Web, generated
  contract, Runner, or other production code.
- Repairing any Finding.
- Running the final aggregate after a blocking focused Finding.
- Git delivery, main integration, remote, push, pull request, tag, Customer 0,
  CreativeDeploy, Phase 6, or a later slice.

## Constraints and safety

- The only repository root used after instruction intake is
  `/Users/danke/Developer/VisualEngineer`.
- A path, Git baseline, parent, count, dirty-state, historical-record, or
  security-test mismatch is a stop condition.
- Existing Finding tests and historical FAIL/remediation/sealing records stay
  intact.
- Audit failures may change only audit-owned tests and documents.
- Critical, High, or blocking Medium incorrect-approval, incorrect-readiness,
  Evidence-integrity, authorization-expansion, or audit-forgery behavior stops
  aggregate expansion.
- Exact task-owned Compose projects are removed without touching unknown
  resources.

## Current progress

- 2026-07-30 CST — **done**: exact Developer repository and candidate/main
  preflight.
- 2026-07-30 CST — **done**: candidate parent and one-commit range verified.
- 2026-07-30 CST — **done**: clean worktree/index/untracked baseline, no
  remote/stash/tag/Git lock, and no existing audit branch.
- 2026-07-30 CST — **done**: historical records and earlier Phase 5 security
  tests verified present without deletion, skip, xfail, or weakening.
- 2026-07-30 CST — **done**: audit branch created from the exact candidate.
- 2026-07-30 CST — **done**: required governance, architecture, security,
  migration, model, repository, schema, service, API, Web, Evidence Manifest,
  freshness, Decision, readiness, and candidate tests inspected.
- 2026-07-30 CST — **done**: unchanged candidate focused baseline passed
  `7/7`.
- 2026-07-30 CST — **done**: independent six-case PostgreSQL/API matrix
  completed with `4 failed, 2 passed`.
- 2026-07-30 CST — **done**: four dynamic blocking Findings and one static
  blocking readiness Finding recorded.
- 2026-07-30 CST — **done**: aggregate, browser expansion, PASS sealing, and
  project-label-only cleanup probe marked not eligible.
- 2026-07-30 CST — **prepared**: audit-only FAIL checkpoint; its exact hash and
  final clean Git reconciliation are reported after commit.

## Decisions

- Classify the first Suite-rerun construction and the first failed-result
  helper use as `INVALID_ATTEMPT`; neither reached its intended secure
  assertion and neither is a Finding.
- Retain the corrected real Validation rerun: it uses a separately approved
  fixed-Profile Grant on the same exact Checkpoint and persists a real failed
  Validation before observing the old Package.
- Treat direct database writes as an explicit acceptance boundary. The test
  records only whether forged digest-bound rows are accepted, without
  expanding into unrelated state.
- Treat missing freshness generation/keyed Decision idempotency and missing
  trusted Finding counts as blocking acceptance gaps because the requested
  stale and deterministic-readiness rules cannot be expressed.
- Do not run `make verify`; a conclusive blocking focused Gate makes it
  ineligible and unable to close these Findings.

## Findings

| ID                    | Severity        | Boundary                             | Result                                                                                                                                                                             |
| --------------------- | --------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VE-P5-REVIEW-FR-001` | blocking Medium | freshness/readiness                  | A later failed fixed-Profile Validation on the exact baseline leaves the old Package `fresh` and its historical ready verdict effective.                                           |
| `VE-P5-REVIEW-FR-002` | blocking Medium | Package/Evidence/readiness integrity | PostgreSQL accepts a Review Package, approve Decision, and ready verdict whose canonical digest fields are forged rather than recomputed.                                          |
| `VE-P5-REVIEW-FR-003` | blocking Medium | audit immutability                   | Review Package, Decision, and readiness AuditEvents can be updated or deleted.                                                                                                     |
| `VE-P5-REVIEW-FR-004` | blocking Medium | Decision concurrency/idempotency     | Review Package responses and Decision requests have no freshness generation, expected generation, or keyed Decision idempotency contract.                                          |
| `VE-P5-REVIEW-FR-005` | blocking Medium | deterministic readiness              | No trusted Critical/High/blocking-Medium inventory or counts exist in the package, Decision, verdict, or readiness evaluation, so the required zero-Finding rule cannot be proved. |

## Risks

- An old approval can remain operationally ready after new negative Validation
  evidence.
- Database defense-in-depth can store a forged digest-addressed ready chain.
- Governance history can be rewritten after the fact.
- A Decision caller cannot fence the exact observed freshness generation or
  distinguish same-key replay from same-key payload conflict.
- `ready` currently means fresh trusted Suite Evidence plus approve; it does
  not prove the required security-Finding counts.

Each risk blocks this slice. The next action is production remediation followed
by a fresh independent focused review.

## Discoveries

- Candidate application concurrency permits exactly one approve/reject winner,
  and exact payload replay does not add a second Decision event.
- Strict request schemas reject Git, push, pull-request, tag, deployment, and
  delivery-authority fields with zero Review Decision/readiness rows.
- Candidate package idempotency passes its existing same-key request checks.
- The package digest payload includes a random package UUID, while PostgreSQL
  checks only digest shape/bindings and does not independently recompute the
  canonical package, manifest, Decision, or verdict digests.
- Freshness queries select the latest successful Suite Result but do not treat
  a later fixed-Profile failed Validation as stale evidence.
- Third Slice changes update a general security-boundary document but add no
  dedicated Third Slice threat model or review runbook.

## Verification

- Git preflight: **PASS**, all required identity/baseline/cleanliness commands
  exit `0`; expected missing audit branch check exits `1`.
- Candidate `make review-security-check`: **PASS**, exit `0`, `7 passed`.
- Corrected independent final matrix: **FAIL**, exit `1`,
  `4 failed, 2 passed`.
- `VE-P5-REVIEW-FR-001` corrected focused rerun: **FAIL**, exit `1`, stable
  `2/2` at the intended freshness assertion.
- `VE-P5-REVIEW-FR-002` and `VE-P5-REVIEW-FR-003`: **FAIL**, stable across
  unchanged focused runs.
- `VE-P5-REVIEW-FR-004`: **FAIL**, exit `1`; no freshness generation is
  returned.
- Independent approve/reject concurrency and replay: **PASS**.
- Independent Git/PR/delivery injection denial: **PASS**.
- Audit test Ruff format/lint, audit-document Prettier, and repository
  `git diff --check`: **PASS** after preserved audit-only formatting failures.
- Final aggregate, migration roundtrip, browser E2E, accessibility, broad
  Security/Eval/Chaos, and PASS sealing: **NOT RUN** after the blocker stop.

Exact command and first-failure details are in
[`docs/evidence/phase-5-governed-final-review-focused-review-verification.md`](../evidence/phase-5-governed-final-review-focused-review-verification.md).

## Rollback

Every test used a unique task-owned Compose project and a bind-probed loopback
port. Cleanup removed each exact project container, network, and volume. The
FAIL checkpoint contains no production code. If this audit package must be
abandoned, remove only its four documents and one audit test; do not reset,
clean, stash, or modify candidate/history.

## Completion conditions

This review completes as FAIL when:

- each blocker has a minimal test or static source proof;
- first invalid audit attempts remain disclosed;
- aggregate and PASS sealing remain not run;
- production code is byte-for-byte unchanged from the candidate;
- all exact audit-owned Docker resource inventories are zero;
- main remains unchanged;
- only authorized audit artifacts are committed; and
- worktree, index, and untracked state are clean after the FAIL checkpoint.

## Outcome and follow-ups

**COMPLETE — FOCUSED REVIEW FAIL — REMEDIATION REQUIRED.**

The eligible next milestone is a narrow production remediation of
`VE-P5-REVIEW-FR-001` through `VE-P5-REVIEW-FR-005`, followed by a fresh
independent focused review. Main integration, PASS sealing, Customer 0,
CreativeDeploy, remote delivery, and Phase 6 remain unauthorized.
