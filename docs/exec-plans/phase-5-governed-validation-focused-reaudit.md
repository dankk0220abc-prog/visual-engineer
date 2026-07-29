# Phase 5 Independent Focused Re-Audit — Validation Result Trust Boundary

- Started: 2026-07-29 (Asia/Shanghai)
- Branch: `audit/phase-5-validation-remediation-focused-max`
- Remediation candidate:
  `8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9`
- Focused-review checkpoint:
  `cd980582e9d950cb0176eae46ffaedd528ce0afe`
- Reviewed implementation:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Main baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Status: `COMPLETE — FOCUSED RE-AUDIT FAIL — REMEDIATION REQUIRED`
- Remote CI: `NOT VERIFIED`

## Goal

Independently re-audit only:

- `VE-P5-FSR-001` — leader-first timeout and descendant process-group
  cleanup;
- `VE-P5-FSR-002` — cancellation cleanup failure and durable recovery;
- `P5-AUD-005` — trusted Validation Result execution-envelope binding; and
- `P5-AUD-006` — output, artifact, and evidence budget revalidation.

If all four scopes pass with no Critical, High, or blocking Medium finding,
run one final repository aggregate and create the local Phase 5 first-slice
sealing checkpoint. A stable blocker instead requires a minimal permanent
reproduction, a FAIL checkpoint, and no aggregate.

## Scope

Permitted writes are limited to:

- additive independent audit tests;
- this ExecPlan;
- `docs/security/audits/phase-5-governed-validation-focused-reaudit.md`;
- `docs/evidence/phase-5-governed-validation-focused-reaudit-verification.md`;
- `docs/status/project-status.md`; and
- directly necessary audit-governance documentation.

All production API, Runner, Protocol, migration, Web, Compose, infrastructure,
and gate code is read-only.

## Non-goals

- Reopening the Phase 4 audit.
- Repairing a production defect found by this review.
- LLMs, Agents SDK, Providers, credentials, arbitrary commands, package
  installation, non-zero artifact transport, real/customer repositories,
  CreativeDeploy, Customer 0, Git delivery, deployment, a later Phase 5
  slice, or Phase 6.
- Main integration, merge, push, pull request, tag, remote configuration, or
  Customer 0 runtime.

## Constraints and safety

- Every repository command is anchored to
  `/Users/danke/Developer/VisualEngineer`.
- No parent/sibling discovery or repository-external symlink following is
  permitted.
- Docker commands use only the unique Compose project
  `visualengineer-phase5-validation-reaudit-019fae88` or its exact Compose
  label.
- No unfiltered Docker inventory, inspect, logs, exec, network, or volume
  command is permitted.
- A Critical, High, or blocking Medium result stops the aggregate. Production
  code remains frozen at the remediation candidate.
- No reset, clean, stash, force, history rewrite, or existing-branch overwrite
  is permitted.

## Current progress

- done — exact repository root and candidate/main/reference verification
- done — clean worktree/index/untracked inventory, remote/stash/tag/lock and
  worktree preflight
- done — exact one-commit remediation ancestry and parent verification
- done — independent branch creation without force
- done — complete governance, implementation, focused-review,
  remediation, source, test, and full remediation-diff review
- done — unchanged original focused reproduction suite
- done — independent Runner timeout/cleanup scenario
- done — real-PostgreSQL cancellation/recovery/envelope/budget matrix
- done — necessary Runner/API/Protocol/source-invariance regressions
- not run — one final `make verify`; the focused PASS prerequisite is false
- done — final audit report, evidence, status, and invariance
- prepared — local FAIL checkpoint; exact object and clean state are reported
  after the commit containing this plan

## Decisions

1. Treat every completion field supplied by Runner as untrusted until the
   Control Plane reconstructs the expected value from locked persisted state
   and the system-owned Profile.
2. Treat process-group absence, leader reap, closed output resources, and
   sandbox cleanup as part of a terminal outcome rather than best-effort
   cleanup.
3. Require both cleanup-failure recovery and the successful active-cancel path
   to terminalize Job, Attempt, Permit, Validation Run, and step consistently.
4. Use additive tests with distinct module names so the re-audit does not
   weaken or rewrite historical focused-review tests.
5. Preserve every first behavior failure and separate audit-harness defects
   from production findings.
6. Classify the successful active-cancel Permit result as
   `VE-P5-FREAUD-001`, a blocking Medium production Finding inside
   `VE-P5-FSR-002`; do not repair it in an independent review.
7. Record the remediation's targeted mypy exclusions as a separate blocking
   audit-governance nonconformance. The original focused tests remain
   byte-identical and pass at runtime, but the candidate did loosen their
   aggregate static-analysis coverage.

## Risks

| Risk                                                             | Likelihood | Impact                                       | Mitigation / next action                                                     |
| ---------------------------------------------------------------- | ---------- | -------------------------------------------- | ---------------------------------------------------------------------------- |
| Leader exits while multiple descendants outlive captured streams | medium     | governed deadline and PID-budget escape      | independent multi-descendant process-group test with exact cleanup           |
| Cleanup failure is hidden by cancellation acknowledgement        | medium     | incorrect clean terminal state               | unchanged Runner audit plus real PostgreSQL failure/replay matrix            |
| Successful active cancellation leaves a consumed Permit          | confirmed  | stale authority and revocation inconsistency | blocking Medium Finding; production remediation required                     |
| Runner self-reports an internally consistent but wrong envelope  | medium     | cross-run or stale authority acceptance      | mutate one independently selected trusted binding and recompute self-digests |
| Artifact metadata is internally inconsistent at zero budget      | medium     | evidence/budget bypass                       | duplicate-path and zero-success-side-effect test                             |
| Targeted static-analysis exclusions weaken audit assurance       | confirmed  | governance gate mismatch                     | blocking preflight nonconformance; restore coverage in remediation           |

## Discoveries

- The candidate parent is exactly the historical focused-review checkpoint and
  the remediation range contains one commit.
- Main remains at the declared Phase 4 seal; no remote, stash, tag, Git lock,
  or additional worktree exists.
- Historical focused-review test files are byte-for-byte absent from the
  remediation file diff, while `pyproject.toml` adds targeted mypy exclusions
  for their colliding module name. Both unchanged files pass at runtime, but
  the targeted static-analysis loosening violates the strict re-audit
  preflight and is a blocking audit-governance nonconformance.
- The real-PostgreSQL active Validation cancellation test reaches production,
  returns clean cancellation for Job, Attempt, Run, and step, and preserves
  Workspace/Evidence/event invariants, but leaves the consumed Side-effect
  Permit without `terminal_at`.
- Static root-cause review confirms that `RunnerService.cancelled` terminalizes
  Permits for Workspace job specifications but omits
  `ValidationExecuteJobSpec` before committing cancellation.
- The same secure expectation failed on the first full run and four focused
  reruns. The original assertion was unchanged for the first `3/3`; later
  audit-only assertion ordering and tuple diagnostics did not change the
  expectation and failed `2/2`.
- The cleanup-failure recovery path, timeout/process-group cleanup, trusted
  envelope, and output/artifact/evidence budget paths all passed their focused
  independent checks.

## Verification strategy

1. Run the unchanged Runner and API focused-review tests.
2. Add and run an independent multi-descendant/early-output-close Runner
   timeout case plus a normal-command control.
3. Run real-PostgreSQL cleanup-failure and successful active-cancel paths.
4. Run an independently selected envelope mismatch, duplicate artifact path,
   exact output limit, limit plus one, rejection replay, and legal replay.
5. Inspect zero success Result, Permit, event, Evidence, and Workspace
   invariance after every rejection.
6. Run the smallest necessary Runner/API/Protocol and source/canonical
   Workspace regressions; stop broader sandbox/Phase 4 expansion once a
   blocker is stable.
7. Only if no blocker exists, read the aggregate coverage one final time and
   run exactly one final `make verify`, followed by only uniquely scoped
   runtime probes not already covered.

Every command, exit code, count, first failure, correction, rerun, PostgreSQL/
Docker/browser fact, digest, production-invariance check, and final Git state
is recorded in the re-audit evidence document.

## Rollback

Stop and remove only the exact re-audit Compose project. Do not revert
production, reset, clean, stash, or rewrite history. Audit-only files may be
corrected with reviewed patches; first failures remain in evidence. The final
checkpoint must contain only audit tests and allowed governance/evidence
documents.

## Completion conditions

A PASS requires all four findings, zero-success-side-effect checks, real
PostgreSQL transaction/locking, Runner/API/Protocol, source/canonical
Workspace invariance, all necessary regressions, one final aggregate, and
resource cleanup to pass with:

- Critical = 0;
- High = 0;
- blocking Medium = 0;
- no production diff from the remediation candidate;
- unchanged main;
- no CreativeDeploy access;
- no remote, push, merge, pull request, or tag; and
- a clean worktree/index/untracked inventory after the checkpoint.

A stable blocker completes the review as FAIL after the minimal reproduction,
evidence/report/status update, production-invariance proof, exact resource
cleanup, and a local FAIL audit checkpoint. The aggregate remains `NOT RUN`.

## Outcome and follow-ups

`COMPLETE — FOCUSED RE-AUDIT FAIL — REMEDIATION REQUIRED`

Focused decision:

- `VE-P5-FSR-001`: PASS;
- `VE-P5-FSR-002`: FAIL because `VE-P5-FREAUD-001` leaves the consumed
  Validation Permit open after successful cancellation;
- `P5-AUD-005`: PASS within this focused review; and
- `P5-AUD-006`: PASS within this focused review.

Critical = 0, High = 0, blocking Medium = 1. The separate targeted-mypy
preflight nonconformance is also blocking governance evidence, but is not
misclassified as a production security Finding.

The final aggregate, browser/E2E, Chaos, broad Docker, Security, Eval,
coverage, full migration roundtrip, PASS sealing subject, and main integration
are `NOT RUN`. The next authorized action is narrow production remediation of
the Validation cancel Permit lifecycle and removal of the targeted audit-test
static-analysis weakening, followed by a fresh independent focused re-audit.

The only eligible PASS handoff is:

`PHASE 5 FOCUSED RE-AUDIT PASS — FIRST VERTICAL SLICE SEALED — READY FOR USER-AUTHORIZED MAIN INTEGRATION`

The required blocker handoff is:

`PHASE 5 FOCUSED RE-AUDIT FAIL — REMEDIATION REQUIRED`
