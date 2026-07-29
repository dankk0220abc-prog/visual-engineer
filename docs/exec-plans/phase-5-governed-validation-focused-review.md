# Phase 5 Independent Focused Security Review

- Started: 2026-07-29
- Reviewer branch: `audit/phase-5-governed-validation-focused-max`
- Candidate:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Main baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Status: `COMPLETE — FOCUSED SECURITY REVIEW FAIL`
- Remote CI: `NOT VERIFIED`

## Goal

Independently review only the Phase 5 Governed Validation Execution boundary:
arbitrary-command prevention, disposable sandbox and canonical Workspace
isolation, network and credential isolation, Lease/fencing/cancel/timeout,
output and artifact budgets, and cleanup/recovery/invariance.

If any Critical, High, or blocking Medium finding is stable, preserve a
minimal audit-owned reproduction, stop the expensive aggregate, publish a
FAIL decision, and leave production code byte-for-byte equal to the candidate.
Only a focused PASS may proceed to the final aggregate and sealing commit.

## Scope

Allowed changes are limited to:

- independent security tests;
- this focused-review ExecPlan;
- the focused audit report;
- focused verification evidence;
- project status; and
- audit-governance documentation required to preserve the decision.

Production API, Runner, Protocol, Web, migration, Compose, infrastructure, and
gate scripts are read-only during this review.

## Non-goals

- Reopening the completed Phase 4 audit.
- Repairing any Phase 5 production defect.
- CreativeDeploy, Customer 0, a real repository, LLM/Agents SDK/Provider,
  package installation, Git delivery, deployment, Phase 6, or a later Phase 5
  slice.
- Merge, push, pull request, tag, remote configuration, or main movement.

## Constraints and safety

- Every filesystem command is anchored to
  `/Users/danke/Developer/VisualEngineer`.
- No parent-directory discovery, sibling repository read, or symlink follow is
  permitted.
- Docker inspection, execution, and cleanup may use only one unique
  review-owned Compose project name or its exact
  `com.docker.compose.project` label.
- The two implementation-era boundary events remain in the ledger: one
  `find ..` exposed only a sibling path name, and one unfiltered Docker
  inventory exposed only a CreativeDeploy container name/status. This review
  does not repeat either action or reopen Phase 4.
- A stable blocker stops `make verify`, broad E2E, Chaos, and unrelated full
  suites.

## Current progress

- done — candidate Git baseline, ancestry, refs, cleanliness, lock, remote,
  stash, tag, worktree, and scope preflight
- done — independent branch creation without force
- done — required governance, architecture, security, runbook, data model,
  migration, API, Protocol, Runner, Web, and existing Phase 5 test inspection
- done — independent Protocol negative-input regression
- done — two minimal production-path regressions, each stable on the first run
  plus two independent focused reruns (`3/3`)
- done — classify two blocking Medium Findings and preserve their unchanged
  secure expectations
- stopped by explicit user direction — the third candidate boundary
  (Control Plane result budget and identity binding) is `NOT VERIFIED`; its
  drafted audit tests were not executed
- done — focused FAIL report, verification evidence, and project-status
  update
- not run — final aggregate, E2E, Chaos, broad Docker, Security, Eval, and
  PASS sealing
- done when committed — local FAIL audit checkpoint containing only audit
  tests and audit/governance documentation

## Decisions

1. Treat Runner-submitted protocol results as untrusted at the Control Plane
   boundary. Authentication identifies a Runner; it does not permit authority,
   identity, Profile, output, or artifact budgets to be widened.
2. A validation cancellation is terminal only after process-group and sandbox
   cleanup are proved. Cleanup/process errors must become
   `recovery_required`, not be discarded behind a generic cancellation
   acknowledgement.
3. Preserve secure-expectation tests even when they fail against the candidate.
   The auditor will not patch production to make them pass.
4. The candidate adds no Phase 5 ADR, dedicated validation threat model, or
   validation lifecycle/recovery runbook. Existing threat models and runbooks
   still contain Phase 4-only milestone language. Record this governance
   asymmetry separately from runtime blockers.

## Risks and discoveries

- Candidate production boundary contains 157 tracked entries with frozen
  `git ls-tree` digest
  `b5f8175c2b353870d9b1995a3ddccb369bbe79c81a9f6a60fa7184e934ef153d`.
- Candidate tree is
  `c0960ab6a75c974917d75cff7f5a5acdadd3cb85`.
- The validation output collector has a distinct leader-first descendant path
  from the already closed Phase 4 Git subprocess implementation. The audit
  must verify that TERM is followed by bounded KILL and group absence even
  after the leader exits.
- The cancellation lifecycle catches and discards Workspace execution errors
  before acknowledging cancellation. The audit must inject cleanup/process
  failure after cancellation and require a typed failure instead.
- Validation result schemas have broad absolute field limits. The Control
  Plane must independently compare submitted identity, fixed argv, combined
  output, and artifact claims to the exact stored Job/Grant budgets. Dynamic
  validation of this candidate boundary was stopped by explicit user direction
  after the Gate was already FAIL and is `NOT VERIFIED`; it is not a Finding.
- The migration protects Validation Run authority and Validation Evidence from
  update/delete, but does not install equivalent immutability for
  `validation_step_runs`. Database symmetry remains under review.

## Verification strategy

Planned order:

1. audit-only Protocol/API negative-input tests;
2. audit-only leader-first timeout/process-group test;
3. audit-only cancellation cleanup/recovery coordination test;
4. audit-only Control Plane result identity/output/artifact budget test against
   real PostgreSQL — `NOT RUN` by explicit stop direction;
5. only the smallest existing Phase 5 tests needed to distinguish an audit
   harness fault from a production defect;
6. only if no blocker remains, the other focused runtime boundaries and
   necessary Phase 4 regressions;
7. only after all six boundaries pass, one repository aggregate.

Every command, exit code, test count, first failure, harness correction,
focused rerun, PostgreSQL/Docker/browser fact, and final Git state belongs in
`docs/evidence/phase-5-governed-validation-focused-review-verification.md`.

The actual focused execution stopped after item 3. Items 4–7 did not execute
because two blocking Medium production failures were already stable and the
user explicitly directed administrative closeout. No conclusion is inferred
for an unexecuted boundary.

## Rollback

Stop only exact review-owned runtime resources. Revert no production file and
do not reset, clean, stash, or rewrite history. Audit-only files may be
corrected through reviewed patches if the first run exposes a harness defect;
the first failure remains recorded.

## Completion conditions

A PASS requires all six focused boundaries, required Phase 4 regressions,
production/source/canonical invariance, resource cleanup, and the final
aggregate to pass with no Critical, High, or blocking Medium findings.

A stable blocker completes this review as FAIL after:

- the minimal reproduction is committed as audit evidence;
- production code remains unchanged from the candidate;
- the final aggregate is explicitly `NOT RUN`;
- main remains unchanged; and
- no remote, push, merge, PR, tag, Customer 0, CreativeDeploy, or later-phase
  action occurred.

## Outcome and follow-ups

`PHASE 5 FOCUSED SECURITY REVIEW FAIL — REMEDIATION REQUIRED`

Confirmed Findings:

- `VE-P5-FSR-001` — blocking Medium
- `VE-P5-FSR-002` — blocking Medium

The minimum next action is production remediation outside this independent
audit branch, followed by a fresh independent focused review. The unexecuted
Runner-result budget/identity boundary must also receive independent dynamic
coverage before any future PASS. This audit does not authorize merge, push,
pull request, tag, main movement, Customer 0, CreativeDeploy access, another
Phase 5 slice, or Phase 6.
