# Phase 5 Governed Multi-Step Validation Suites

- Started: 2026-07-30 01:38:35 +0800
- Repository: `/Users/danke/Developer/VisualEngineer`
- Baseline branch: `main`
- Baseline / `main`: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Implementation branch: `feat/phase-5-governed-validation-suites`
- Status: `COMPLETE_PENDING_INDEPENDENT_FOCUSED_REVIEW`

## Goal

Add a Browser-first, system-owned, immutable multi-step Validation Suite that
serially executes fixed fixture-only Validation Profiles. A Suite Run binds an
approved Run/Plan/revision, exact Workspace Checkpoint, validation-only
Execution Grant, Runner jobs, Attempts, Leases, immutable Suite definition and
policy digest, per-step and aggregate budgets, and bounded Evidence. No request
may supply a command, argv, environment, cwd, Profile definition, or step list.

## Scope

This maximum-safe batch may change the Validation Profile/Suite catalog,
validation-scoped Grant contract, PostgreSQL models and one new migration,
Control Plane API/service/repository code, Runner Protocol fixed Profile
selection, fixed Runner validator behavior, `/validations`, generated
OpenAPI/TypeScript contract, tests/evals, architecture/security/runbook/status
documentation, and verification evidence.

The vertical closure includes Suite catalog/listing, Suite Run
create/list/detail/timeline/result, cancel and bounded retry, deterministic
serial orchestration, fail-fast skipping, per-step Runner Job/Attempt/Lease/
Permit/Result/Evidence, suite timeout/output/attempt enforcement, aggregate
result, desktop/390 px Browser flow, accessibility, and fixture-only real
PostgreSQL/Runner/Docker evidence.

## Non-goals

- LLMs, OpenAI Agents SDK, model Providers, credentials, API keys, or tokens.
- CreativeDeploy, Customer 0, sibling or non-fixture repositories.
- User command, argv, environment, cwd, shell, package lifecycle, install, or
  network download.
- Artifact content transfer; every Suite Profile retains zero artifacts.
- Canonical Workspace or source mutation.
- Git delivery, remote, push, pull request, merge, tag, deployment, Phase 6,
  or reopening completed Phase 0-4 / Phase 5 first-slice decisions.

Any necessary expansion into these areas stops with
`PHASE_5_REQUIRES_EXPLICIT_USER_APPROVAL`.

## Constraints and safety

- All searches and operations remain anchored at this repository root.
- The exact baseline must remain reachable as unchanged `main`.
- Historical migrations, findings, FAIL reports, and sealed first-slice
  evidence are immutable.
- The Suite catalog is versioned source code, not persisted request input.
- Runner jobs remain a closed discriminated union and execute only catalogued
  Profiles. The hardened no-shell, no-network, Landlock/seccomp, bounded
  process-group and exact-cleanup boundary remains mandatory.
- Control Plane independently validates every child result and aggregate
  budget before a successful Suite result may exist.
- One local implementation checkpoint is allowed only after final
  `make verify` exits `0`; no remote action is allowed.
- If the execution boundary cannot be proven, stop with
  `PHASE 5 SECOND SLICE STOPPED — EXECUTION BOUNDARY NOT PROVEN`.

## Suite Catalog

The initial immutable Suite is
`fixture-integrity-suite-v1:v1`, a meaningful two-step fixture gate:

1. `fixture-contract`: `fixture-python-stdlib-v1:v1`, proving the exact trusted
   fixture content contract in the existing disposable sandbox.
2. `fixture-manifest`: `fixture-python-manifest-v1:v1`, proving the bounded
   input manifest and content digest with a second fixed standard-library
   validator mode.

Both steps are serial and deterministic, use zero artifacts, have fixed
timeouts/output caps, and use the current fixture-only Workspace. The failure
policy is `fail_fast`: the first non-success prevents later dispatch and marks
remaining steps `skipped`. Suite total timeout, combined output cap, step
count, and maximum attempts are immutable catalog fields.

## Data model

A new migration adds:

- validation Grant Suite references without weakening single-Profile grants;
- `validation_suite_runs`, bound to Run/Plan/revision/Workspace/Checkpoint/
  Grant, immutable Suite ID/version/policy digest, idempotency, attempt/retry,
  suite budgets, state and timestamps;
- `validation_suite_step_runs`, ordered fixed Profile references and child
  Validation Run/Runner/Attempt/Lease/Evidence bindings; and
- `validation_suite_results`, one immutable aggregate verdict, consumption
  summary, ordered Evidence references, cleanup/invariance state, and Audit/
  Runner event references.

Closed database checks, foreign keys, unique idempotency/order/attempt
constraints, indexes, terminal consistency, immutable-authority triggers, and
an upgrade/downgrade/re-upgrade path are required. No historical migration is
edited.

## API and Protocol

The API adds immutable Suite catalog and Suite Run create/list/detail,
timeline, aggregate result, cancel, and retry routes. Create accepts only an
approved Suite-scoped Grant plus a closed Suite ID/version. Retry accepts only
a new approved Suite-scoped Grant and an idempotency key; the definition and
successful-step reuse come from the original immutable run.

The validation Grant request gains a closed Suite ID/version alternative to a
single Profile. The derived Grant fixes the exact Suite reference and its
Profile references. Runner Protocol retains `validation_execute_v1`; its
closed Profile/step literals expand only for the second system-owned Profile.
No Suite request or Runner Job carries user steps or command-bearing fields.

## Runner orchestration

The Control Plane owns Suite orchestration and dispatches one existing
`validation_execute_v1` child job at a time. Every started Suite step therefore
has an independent Validation Run, Runner Job, Attempt, Lease, Side-effect
Permit, fixed Profile result, and Evidence. No next step is created after
cancel request, fail-fast failure, total timeout, aggregate output overflow,
stale authority, or cleanup/recovery failure.

Retry creates a new Suite attempt and requires a new Grant. Successful prior
steps are reused by immutable Evidence reference and are not redispatched or
charged again; failed/skipped steps receive new child jobs and therefore new
Attempts/Leases/Permits.

## State machines

Suite states are `requested`, `queued`, `running`, `cancel_requested`,
`succeeded`, `failed`, `timed_out`, `cancelled`, and `recovery_required`.
Step states are `pending`, `queued`, `running`, `succeeded`, `failed`,
`timed_out`, `cancelled`, `skipped`, and `recovery_required`.

Only declared transitions are allowed. A terminal Suite is immutable; success
requires every step to be succeeded or explicitly reused-success with no
failed/timed-out/recovery step. Cancellation forbids new dispatch. Cleanup
failure dominates success and maps to `recovery_required`.

## Idempotency, cancel, retry, and recovery

Suite create/retry keys are globally unique and bound to canonical request
hashes. Exact replay returns the existing Suite Run; conflicting replay is
rejected. Cancel is idempotent only while cancellation is already requested;
terminal non-cancelled runs reject cancel. Runner stale Attempt/Lease/Grant
checks remain authoritative. Recovery state is visible and never synthesized
into success.

## Budgets and Evidence aggregation

Each step uses immutable Profile timeout/output caps and zero artifact budget.
The Suite enforces fixed step count, total monotonic/wall-clock timeout,
combined retained stdout/stderr bytes, and maximum attempts. Exact limits are
allowed; `limit + 1` is rejected before a successful aggregate result or
success event.

Aggregate Evidence records Suite/Profile versions, revision/Checkpoint,
Runner/Attempt/Lease and Evidence references, ordering, timing/duration, exit
codes, truncation/redaction, verdict, cancellation/timeout/recovery, output
consumption, zero artifacts, cleanup state, and bounded Audit/Runner event
references. Raw environment and credentials are never stored.

## Web timeline

`/validations` lists fixed Suite metadata and limits, creates a Suite-scoped
pending Grant for an exact Checkpoint, supports explicit local approval,
creates a Suite Run, polls queued/running/terminal state, renders ordered step
timeline and bounded logs/evidence, shows aggregate consumption/verdict and
disabled reasons, and exposes cancel/retry when valid. It contains no command
textbox and must pass desktop, 390 px, keyboard, focus, and axe checks.

## Testing and failure handling

Focused coverage includes unknown/tampered Suite, extra-field step/Profile/
command/argv/env/cwd injection, ordering/duplicate constraints, stale
Attempt/Lease/Grant/baseline/policy, cancellation races, post-cancel dispatch
denial, step/suite timeout, output exact/+1, duplicate completion, retry reuse,
cleanup/recovery, Runner identity, partial success/fail-fast, zero artifacts,
source/canonical Workspace invariance, process/sandbox cleanup, API/Protocol,
real PostgreSQL migration roundtrip, Runner integration, Web/build/contracts,
desktop/390 px E2E, accessibility, Security, Eval, Chaos, Docker isolation, and
no residual resources.

Failures are recorded before their fixes. Narrow tests run first. Expensive
aggregate verification runs once after focused fixes.

## Rollback

Before the checkpoint, reverse only reviewed second-slice changes; never reset,
clean, stash, or rewrite history. The new migration downgrade removes only the
Suite tables/triggers/indexes/constraints and new Grant columns. Stop only
exact, uniquely named VisualEngineer Compose projects. Preserve first-slice
tables, evidence, Runner volumes, source fixtures, and canonical Workspaces.

## Current progress

- done — exact baseline, repository, branch, clean state, remotes/stash/tags,
  lock and first-slice status inspection
- done — scope-conflict check; no approved conflicting next milestone found
- done — designated implementation branch created from exact baseline
- done — model/catalog/API/Protocol/Runner/Web implementation
- done — focused negative/race/budget/recovery tests and fixes
- done — migration/contracts/real PostgreSQL and Runner verification
- done — desktop/390 px E2E, accessibility, Security, Eval, Chaos, Docker
- done — documentation/evidence reconciliation
- done — final aggregate `make verify` exit `0`
- pending — final diff review and one local checkpoint

## Decisions

- Reuse the sealed fixed-Profile Validation Run as the unit of Suite execution.
  This preserves independent Runner Job/Attempt/Lease/Permit/Result/Evidence
  fencing per step instead of inventing an unfenced in-process loop.
- Add a second fixed Python standard-library Profile mode; do not install a
  dependency or invoke repository lifecycle scripts.
- Keep Suite definitions in versioned source and persist only their immutable
  identity/digest plus instantiated ordered steps.
- Require a new Suite-scoped Grant for retry and reuse successful immutable
  child Evidence rather than rerunning or recharging it.

## Discoveries

- The sealed first slice has one system-owned
  `fixture-python-stdlib-v1:v1` Profile and one fixed
  `validation_execute_v1` Runner job per Validation Run.
- Existing validation execution already provides no-shell fixed argv,
  disposable input copy, Landlock filesystem confinement, seccomp network
  denial, output redaction/caps, zero artifacts, process-group cleanup, and
  immutable per-run Evidence.
- Existing project status explicitly reserves later Phase 5 slices for
  separate authorization; no conflicting approved next milestone exists.

## Risks

- Lazy Control Plane synchronization must not dispatch a later step twice.
  PostgreSQL row locks, unique child bindings, and idempotent internal keys
  mitigate this.
- Cancel may race child terminal completion. Locked Suite and Validation rows
  must make one terminal path authoritative and prevent post-cancel dispatch.
- Total timeout spans multiple jobs. The persisted Suite start/deadline is
  authoritative and rechecked before every dispatch and aggregate success.
- Aggregate result construction must not trust child JSON. It uses
  Control-Plane-validated immutable `ValidationEvidence` rows and rechecks all
  policy/budget/binding fields.

## Verification

Focused and final aggregate verification is recorded with commands, exit
codes, counts, coverage, first failures, fixes, E2E/Chaos project identities,
Docker residue, and invariance digests in
`docs/evidence/phase-5-governed-validation-suites-verification.md`. Final
`make verify` exited `0`; only diff review and the one local checkpoint remain.

## Completion conditions

All implementation, closed contract, migration roundtrip, focused negative
matrix, real PostgreSQL/Runner/Browser/Docker/Chaos/Security/Eval/invariance
gates and final `make verify` must pass. The exact diff must be in scope,
`main` must remain at `f547091307c52df8f20fc69bac4b4826cbbc74ad`,
there must be no remote/push/merge/PR/tag/deployment or external repository
access, and one local commit must leave index/worktree/untracked clean.

## Focused independent review

The implementation handoff does not declare Security Gate PASS. The next
independent read-only review is limited to Suite definition immutability, step
injection prevention, Suite/step consistency, cancel/retry races, suite-level
budget enforcement, result/Evidence aggregation, cleanup, and source/canonical
Workspace invariance. It does not reopen Phase 4 or the sealed first slice.

## Outcome and follow-ups

`IN PROGRESS`. Final hash, deviations, command ledger, limitations, and the
recommended next milestone will be added only after successful verification
and the authorized local checkpoint.
