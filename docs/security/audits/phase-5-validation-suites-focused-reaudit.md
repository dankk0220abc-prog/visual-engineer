# Phase 5 Validation Suites Independent Focused Re-Audit

- Date: 2026-07-30 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `audit/phase-5-validation-suites-reaudit-max`
- Main baseline: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Original FAIL checkpoint:
  `d325fa197e1fdad2c522fdf76f11b738682a86ca`
- Remediation candidate:
  `b6d53ba0275933e18919ceb2d90152e5ae8efcac`
- Verdict: `FOCUSED RE-AUDIT PASS`
- Final aggregate: `PASS`, exit `0`
- New Critical / High / blocking Medium Findings: `0 / 0 / 0`

## Completion status

**PHASE 5 SUITES FOCUSED RE-AUDIT PASS — SECOND SLICE SEALED — READY FOR
USER-AUTHORIZED MAIN INTEGRATION**

This decision independently closes only:

- `VE-P5-SUITES-FR-001` — Suite Grant single-root lineage, idempotency,
  fresh-Grant retry, and concurrent consumption; and
- `VE-P5-SUITES-FR-002` — trusted child execution and complete ordered
  Evidence as prerequisites for Suite success.

It also closes only the previously stopped combined-output, cancellation,
retry-race, cleanup-recovery, and source/canonical-invariance boundaries. It
does not reopen Phase 4, the sealed Phase 5 first slice, or the full Suite
architecture.

## Git baseline and independence

The remediation candidate is exactly one commit after the historical focused
FAIL checkpoint. Its parent is the FAIL checkpoint, the checkpoint is its
ancestor, and the range count is one. The commit subject is exactly:

`fix(validation): enforce suite grant lineage and trusted aggregation`

The original focused-review test has SHA-256
`47d9623ce5aab2e0de18e14fc473970f828c312f2d27ad167574be72c0bb350d`
at both checkpoints and in the review worktree. It has no added skip or xfail
marker. The audit branch was created without force directly from the exact
candidate.

Preflight confirmed one worktree and no remote, stash, tag, Git lock, target
branch collision, undisclosed candidate commit, or initial worktree/index/
untracked change.

## Review method

The review read the historical focused report/evidence/ExecPlan, remediation
plan/evidence, complete one-commit diff, permanent regressions, Migration 0009,
Suite/Grant/Run/Evidence models and repositories, service and state
transitions, API schemas/routes, Protocol, Runner orchestration, and the
bounded budget/cancel/retry/cleanup tests.

Verdicts rely on current candidate source review, real PostgreSQL, independent
tests, database constraints/triggers, focused API/Protocol/Runner checks,
fresh migration and contract checks, local-image identity checks, the final
complete aggregate, and exact cleanup. Remediator prose is navigation context,
not independent proof.

## VE-P5-SUITES-FR-001

**PASS.**

The unchanged original reproduction passes on real PostgreSQL. The remediation
matrix and independent tests prove:

- the same Grant plus the same idempotency key returns the original Suite Run;
- the same Grant plus a different key is denied;
- concurrent double create produces at most one Suite Run;
- the Grant cannot create a second root lineage, additional execution
  records, duplicate Evidence/Result, or duplicate charge;
- stale, revoked, expired, mismatched, old, or foreign retry authority is
  denied with durable counts unchanged;
- retry requires a new approved Grant bound to the exact root, source attempt,
  next attempt number, Suite/version/definition, revision/checkpoint, policy,
  and budget;
- exact retry replay is idempotent; and
- a late completion from the old child cannot write into or authorize the new
  retry lineage.

The independent race cancels the old active child, acknowledges cancellation,
creates a fresh retry Grant, and releases retry creation and old completion
from separate database sessions at the same barrier. Exactly one attempt-two
lineage is created. The old completion is rejected as `stale_lease`; it
creates no Evidence and cannot complete the old Permit. Replaying the retry
does not change durable counts.

The independent foreign-retry case uses an otherwise approved Grant belonging
to another Suite root. It is denied without creating a Suite Run, step, Job,
Attempt, Lease, Permit, Result, Evidence, event, charge, or Workspace change.

## VE-P5-SUITES-FR-002

**PASS.**

The unchanged original zero-Evidence reproduction passes on real PostgreSQL.
The combined matrix proves that a successful step status alone is
insufficient and rejects missing, foreign, duplicate, reordered, stale, null,
or mismatched Evidence and execution bindings.

The independent adversarial case supplies an internally coherent and correctly
ordered two-step Evidence chain from a different Suite execution. The target
Suite cannot use it to create a succeeded aggregate Result. The rejection
creates no success event, Permit completion, Evidence, charge, execution
identity, or Workspace mutation.

The independent legal two-step case succeeds and independently recomputes the
aggregate digest from trusted persisted Evidence. The Result binds the exact
root lineage, Suite/version/definition, revision/checkpoint, Grant, policy,
budget, and catalog-ordered Evidence. Two exact aggregate replays create no
duplicate Result, Evidence, event, or charge. A terminal step cannot replace
its Evidence reference, and a terminal Suite cannot replace its aggregate
Result references.

Failed, timed-out, cancelled, or `recovery_required` child steps cannot
authorize Suite success.

## Budget, race, and cleanup boundaries

**PASS.**

The bounded current-candidate matrix confirms:

- two individually legal step outputs whose combined retained output is
  exactly 10,000 bytes can succeed;
- combined output of 10,001 bytes is denied;
- cancel-before-next-dispatch never starts the pending child;
- cancellation wins before a completed child can dispatch the next step;
- Suite and step timeouts cancel active work before terminalization;
- retry racing the old completion preserves lineage fencing;
- cleanup failure and a remaining process produce failed/
  `recovery_required`, not clean cancellation or success; and
- source and canonical Workspace fingerprints remain unchanged.

Every rejection path relevant to this focused decision retains zero succeeded
Suite Result, zero Suite success event, zero erroneous Permit completion, zero
new Evidence, zero duplicate charge, no unexpected Job/Attempt/Lease, and an
unchanged canonical Workspace.

## PostgreSQL, Migration, API, Protocol, and Runner

**PASS.**

- Unchanged original focused tests: `2 passed`.
- New independent focused tests: `4 passed`.
- Combined Suite focused matrix: `23 passed`.
- Focused Protocol/Runner selection: `6 passed`.
- Fresh isolated Migration 0009 roundtrip: base to head, head to base, base to
  head.
- Generated OpenAPI and TypeScript contracts: no drift.
- Standalone and aggregate source-invariance checks: PASS.

The PostgreSQL matrix exercised service locks and independent database
constraints/triggers. No SQLite or mock persistence was used.

## Final `make verify`

**PASS, final complete invocation exit `0`.**

The passing aggregate includes:

- contracts, Ruff/Prettier format, Ruff/ESLint lint, strict mypy, and
  TypeScript;
- Python/API/Runner/Protocol `252/252` at `83.33%` coverage;
- Web `47/47` with configured coverage thresholds;
- Next.js production build and all Docker Compose rendering;
- Migration 0009 roundtrip;
- Phase 4 permanent Finding controls and Runner security audit `22/22`;
- source invariance;
- Workspace repair `86/86` plus API `14/14`;
- Playwright E2E `16/16`;
- Workspace Chaos and unchanged source/`.git` fingerprint;
- Workspace Security `64/64` and static isolation;
- Validation sandbox isolation;
- broad Runner Security `111/111` plus scanner `7/7`;
- Eval 67 plus scanner `7/7`; and
- final `git diff --check`.

## First failures and reruns

The evidence preserves three independent audit-environment issues:

1. The first new-test static check reported import ordering and missing strict
   `zip()` in the new audit file. Ruff mechanically fixed only that file.
2. The first aggregate invocation exited `2` at Prettier because the new audit
   ExecPlan was unformatted. It stopped before tests or Docker. The document
   was formatted without a production change.
3. The next aggregate invocation used a reused Web image compiled for API port
   `38640` while the audit mapped `38741`. One browser case failed and two
   timed out before the task-owned run was interrupted with exit `130`; its
   cleanup trap ran. Bundle inspection confirmed the mismatch. A fresh
   listener and project preflight found the repository-supported port free.
   The final complete rerun used the formal environment overrides and exited
   `0`.

These failures are not hidden and are not classified as production security
Findings. The intended single-pass aggregate procedure was exceeded because
of audit-artifact and environment setup errors; the successful final result
comes from a complete, not partial, rerun.

## Production-code invariance and cleanup

The working-tree diff from the exact remediation candidate is empty for API
source/migrations, Runner, Protocol, Web, generated contracts, Dockerfiles,
Compose, infrastructure, scripts, `Makefile`, and project configuration.
Only one independent audit test and governance/evidence documents are in the
sealing scope.

Filtered post-cleanup inventories are zero containers, zero networks, and zero
volumes for:

- `ve-p5-suites-reaudit-max`;
- `ve-p5-suites-reaudit-final`;
- `ve-p5-suites-reaudit-final-rerun`;
- `ve-p5-suites-reaudit-final-e2e`; and
- `ve-p5-suites-reaudit-final-chaos`.

All focused/final published ports have no listener. Five temporary audit image
aliases were removed; the original remediation image tags still retain the
underlying local images.

## Findings

- Critical: `0`
- High: `0`
- blocking Medium: `0`
- new non-blocking production security Findings: `0`
- unresolved aggregate environment blockers: `0`

The two historical blocking Medium Findings remain preserved in their
historical FAIL report. This report records their independent closure against
the exact remediation candidate; it does not rewrite the original decision.

## CONFIRMED / INFERRED / NOT VERIFIED

**CONFIRMED**

- exact Git lineage, candidate subject, unchanged original audit test, and
  independent branch;
- FR-001 and FR-002 behavior on real PostgreSQL;
- bounded budget/race/retry/cleanup and Workspace-invariance behavior;
- Migration, contracts, API, Protocol, Runner, Web, E2E, Chaos, Docker,
  Security, Eval, coverage, and final aggregate;
- production-code invariance, main invariance, exact cleanup, and delivery
  prohibitions.

**INFERRED**

- The complementary service and database controls materially reduce future
  bypass risk beyond the exercised cases. This is a design inference, not a
  proof for arbitrary future migrations or hostile multi-user deployments.

**NOT VERIFIED / OUT OF SCOPE**

- non-zero artifact transport;
- remote CI, push, pull request, tag, deployment, and production operations;
- hostile multi-user execution;
- Customer 0;
- a later Phase 5 slice or Phase 6.

None is a blocker for this explicitly local focused seal.

## Sealing and next action

The authorized local sealing subject is:

`chore: seal phase 5 governed validation suites`

The sealing commit contains only the independent audit test, this report, the
ExecPlan, verification evidence, project status, and necessary `PLANS.md`
governance. A commit cannot embed its own object ID without changing that ID;
the exact checkpoint is reported in the post-commit handoff.

Even after sealing, `main` must remain at
`f547091307c52df8f20fc69bac4b4826cbbc74ad`. The next eligible action is only
an explicitly user-authorized local main integration. This report does not
authorize merge/fast-forward, push, pull request, tag, deployment, Customer 0,
another Phase 5 slice, or Phase 6.
