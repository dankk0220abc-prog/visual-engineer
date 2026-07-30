# Phase 5 Governed Validation Suites Independent Focused Review

- Started: 2026-07-30 16:41:09 +0800
- Repository: `/Users/danke/Developer/VisualEngineer`
- Main baseline: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Candidate: `10399722e37f3209fa08e5e7edc25f31b429aaad`
- Review branch: `audit/phase-5-validation-suites-focused-max`
- Status: `COMPLETE — FOCUSED SECURITY REVIEW FAIL`

## Goal

Independently review only the second Phase 5 governed multi-step Validation
Suite boundary. A PASS requires Suite definition immutability, step
ordering/injection prevention, Suite/step state consistency, cancellation and
retry fencing, Suite-level budgets, aggregate Result/Evidence integrity, and
cleanup/invariance to pass before one final `make verify` and a local sealing
checkpoint.

Any stable Critical, High, or blocking Medium Finding stops the aggregate,
preserves a minimal audit-owned reproduction, and produces a FAIL checkpoint
without modifying production code.

## Scope

Allowed writes are limited to:

- independent audit tests;
- this focused-review ExecPlan;
- `docs/security/audits/phase-5-validation-suites-focused-review.md`;
- `docs/evidence/phase-5-validation-suites-focused-review-verification.md`;
- `docs/status/project-status.md`; and
- necessary audit-governance documentation.

Migration, API, service, Runner, Protocol, Web, Compose, infrastructure,
scripts, generated contracts, and all other production files are read-only.

## Non-goals

- Re-auditing Phase 4 or the sealed Phase 5 first slice.
- Repairing a production defect found by this review.
- CreativeDeploy, Customer 0, another repository, LLM/Agents SDK/Provider,
  arbitrary commands, package installation, Git delivery, deployment, a later
  Phase 5 slice, or Phase 6.
- Remote configuration, push, pull request, tag, merge, or main movement.

## Constraints and safety

- Every repository operation is anchored at the exact repository root.
- Docker operations use only the unique review-owned Compose project or its
  exact `com.docker.compose.project` label.
- No parent discovery, sibling-repository access, or external symlink follow is
  allowed.
- Existing security tests may not be deleted, weakened, skipped, or marked
  expected-failing.
- A stable blocker stops `make verify`, broad E2E, Chaos, Security, Eval, and
  other expensive aggregate work.

## Current progress

- done — exact Git baseline, ancestry, scope, refs, worktree/index/untracked,
  remote, stash, tag, lock, and branch preflight
- done — review branch created directly from the exact candidate without force
- done — required governance, architecture, implementation evidence,
  migration, catalog, API, orchestration, Protocol, Runner, Web, and existing
  Suite test review
- done — two independent real-PostgreSQL focused reproductions failed on the
  first run and remained stable on two unchanged focused reruns each
- done — classified `VE-P5-SUITES-FR-001` and
  `VE-P5-SUITES-FR-002` as blocking Medium
- done — unchanged candidate Suite controls passed `10/10`
- done — exact review-owned Docker cleanup and production/main invariance
- done — focused report, evidence, project status, and local audit-only FAIL
  checkpoint preparation
- stopped by contract — final `make verify`, broad E2E, Chaos, Docker,
  Security, Eval, coverage, and PASS sealing

## Decisions

1. Treat the approved Suite Grant as one exact Suite-attempt authority. A new
   idempotency key cannot turn the same Grant into a second Suite attempt;
   retry requires a newly approved Grant.
2. Treat persisted Suite/step/result rows as untrusted orchestration input.
   Database transition guards or Control Plane revalidation must prevent
   missing, foreign, reordered, or definition-inconsistent Evidence from
   becoming successful aggregate proof.
3. Preserve secure-expectation tests unchanged when they expose candidate
   behavior. This branch does not patch production.

## Risks and discoveries

- `VE-P5-SUITES-FR-001` — the same approved Suite Grant accepts another root
  Suite create under a fresh idempotency key. Both Suite and child Validation
  Run counts increase, bypassing the fresh-Grant retry boundary.
- `VE-P5-SUITES-FR-002` — the step database guard lacks a legal nonterminal
  transition matrix, and aggregate finalization does not require exact ordered
  current-run Evidence. Injected successful step summaries become a succeeded
  Suite/Result with zero Evidence references.
- Both Findings reproduced `3/3` with unchanged secure-expectation tests on
  real PostgreSQL.
- The candidate's unchanged expected-path Suite controls pass `10/10`; this
  does not close either independent Finding.
- The unique review-owned Compose project has no container, network, or volume
  residue after exact cleanup. Production paths and main are unchanged.

## Verification

Focused execution order:

1. request/Grant/catalog immutability and injection;
2. step ordering and transition consistency;
3. cancel/retry races;
4. per-step and aggregate budgets;
5. ordered current-run Evidence aggregation;
6. cleanup/invariance;
7. only necessary sealed-boundary regressions;
8. only after all seven boundaries pass, one final `make verify`.

Exact commands, project identity, exit codes, counts, first failures, reruns,
resource cleanup, hashes, and the final Git state are recorded in
`docs/evidence/phase-5-validation-suites-focused-review-verification.md`.

Executed focused results:

- independent audit file: `2 failed`, exit `1`;
- each Finding: initial failure plus two unchanged reruns, `3/3` stable;
- unchanged candidate Suite controls: `10 passed`, exit `0`;
- focused test format/lint: exit `0`;
- production-path diff and exact cleanup: exit `0`.

The final aggregate is `NOT RUN` with exit `N/A` because the mandatory blocker
stop condition applies.

## Rollback

Stop and remove only the exact review-owned Compose project. Do not reset,
clean, stash, force, or rewrite history. Audit-only files may be corrected if
the first run exposes a harness defect, while preserving the original failure
in the evidence ledger.

## Completion conditions

A PASS requires every seven-boundary check, real PostgreSQL migration
roundtrip, required API/Protocol/Runner/Web/Docker/E2E/Chaos/Security/Eval
coverage, source/canonical invariance, zero residue, and the final aggregate to
pass with no Critical, High, or blocking Medium Finding.

A stable blocker completes the review as FAIL after its minimal reproduction,
focused evidence, production invariance, zero review-owned residue, main
invariance, and a local audit-only FAIL checkpoint are confirmed.

## Outcome and follow-ups

**PHASE 5 SECOND SLICE FOCUSED REVIEW FAIL — REMEDIATION REQUIRED**

The candidate is not approved for PASS sealing, main integration, Customer 0,
a later Phase 5 slice, or Phase 6. The next eligible milestone is a narrow
production remediation for the two Findings, followed by a fresh independent
focused re-review that completes every stopped boundary before one final
aggregate.

The local FAIL checkpoint hash is reported administratively after commit
because a commit cannot embed its own object ID.
