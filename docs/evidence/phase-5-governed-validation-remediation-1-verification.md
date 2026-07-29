# Phase 5 Targeted Security Remediation 1 Verification

- Date: 2026-07-29 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/phase-5-governed-validation-remediation-1`
- Base/HEAD before remediation:
  `cd980582e9d950cb0176eae46ffaedd528ce0afe`
- Main:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Reviewed implementation:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Candidate status:
  `PHASE 5 TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`
- Final aggregate: `make verify`; exit `0`
- Git checkpoint: created by this candidate commit
- Remote CI: `NOT VERIFIED`

## Evidence boundary

This is implementer remediation evidence, not an independent review. It
preserves the historical focused-review FAIL and records:

1. exact Git/state protection;
2. original stable failures;
3. the four remediation scopes and permanent regressions;
4. real-PostgreSQL transaction, rejection, replay and migration behavior;
5. Runner sandbox, source/canonical Workspace invariance, Web/E2E/Chaos and
   broader local gates; and
6. the final aggregate and local checkpoint disposition.

No Security Gate PASS is claimed.

## State protection

| Check                            | Exit | Result                                                               |
| -------------------------------- | ---: | -------------------------------------------------------------------- |
| `pwd`                            |    0 | exact `/Users/danke/Developer/VisualEngineer`                        |
| `git branch --show-current`      |    0 | `fix/phase-5-governed-validation-remediation-1`                      |
| `git rev-parse HEAD`             |    0 | `cd980582e9d950cb0176eae46ffaedd528ce0afe`                           |
| `git rev-parse main`             |    0 | `928a89d2055d172bbd7c6670b42f668d103dcb03`                           |
| status/diff/untracked inventory  |    0 | required three modified plus three untracked preserved before work   |
| `git diff --cached --name-only`  |    0 | empty                                                                |
| remote/stash/Git lock checks     |    0 | none                                                                 |
| independent audit source re-read |    0 | report, evidence and both unchanged test entrypoints read completely |

No reset, stash, branch switch, WIP commit or current-change removal occurred.

## Original failures preserved

### Runner findings

The first unchanged Runner audit produced:

```text
2 failed, 4 passed; exit 1
```

Each secure assertion then failed two more focused reruns:

```text
VE-P5-FSR-001: 3/3 stable failures
VE-P5-FSR-002: 3/3 stable failures
```

### Original third boundary

After one connection-refused setup attempt, the exact disposable PostgreSQL
project `visualengineer-phase5-remediation-1` produced:

```text
1 passed, 7 failed; exit 1
```

`P5-AUD-005` and `P5-AUD-006` each repeated unchanged two more times:

```text
P5-AUD-005: 3/3 stable failures
P5-AUD-006: 3/3 stable failures
```

Five inner identity/fixed-argv mismatches and two budget violations were
accepted as HTTP `200` / Job `succeeded`. The last observation showed one
stored Result, one completed Permit, `job_succeeded` and
`side_effect_permit_completed`, with no Evidence only because synchronization
had not run.

That evidence remains the pre-repair baseline and was not overwritten.

## Production repair

### `VE-P5-FSR-001`

`ValidationExecutor._collect` now:

- keeps the process-group ID after leader exit;
- observes one monotonic timeout;
- performs bounded group TERM/grace/KILL;
- requires closed streams, reaped leader and absent group;
- proves group absence; and
- closes selector/stdout/stderr resources in `finally`.

### `VE-P5-FSR-002`

The Runner cancellation branch submits the exact typed
`WorkspaceExecutionError` with the consumed Permit and returns without
acknowledging cancellation.

The API now permits `cancel_requested → failed` only for the closed Validation
recovery set:

- `validation_cleanup_failed`;
- `validation_process_remained`; and
- `validation_sandbox_unavailable`.

The same PostgreSQL transaction terminalizes the Permit as failed, fails the
Job/Attempt, and persists Validation Run/step `recovery_required`. A retry
returns the one existing terminal failure.

### `P5-AUD-005`

Before terminal persistence, the API locks and binds:

- authenticated Runner and Runner Job;
- Validation Run and exact step;
- active Attempt and Lease;
- exact approved/non-expired Grant and policy hash;
- Profile ID/version and fixed operation;
- source revision and Checkpoint ID/fingerprint;
- Validation policy digest;
- fixed argv digest, symbolic fixed cwd and fixed environment-allowlist
  digest;
- result schema version; and
- Permit ID, sequence, operation digest, expiry and fencing token.

The expected versioned envelope is reconstructed from trusted persisted
records and the system-owned Profile. The Runner-provided digest cannot define
its own expected values.

### `P5-AUD-006`

Before Result/Permit/Event terminal writes, the API recomputes:

- combined UTF-8 stdout/stderr bytes;
- truncation consistency;
- artifact relative paths, regular-file type and uniqueness;
- artifact count, each size and total bytes;
- canonical manifest digest; and
- canonical full evidence digest.

Missing evidence, mismatch, or overflow returns `409`. Protocol-invalid
traversal or special-file metadata returns `422`; both boundaries leave zero
success side effects. The current Profile's exact artifact limit is zero.

## Permanent regressions

### Runner

File: `apps/runner/tests/test_phase5_remediation.py`

Coverage:

- leader-first, TERM-ignoring descendant cleanup;
- typed cancellation cleanup failure forwarded instead of acknowledged.

Result with unchanged independent Runner audit:

```text
8 passed in 4.45s; exit 0
```

Complete Runner plus Protocol:

```text
96 passed in 18.79s; exit 0
```

### Control Plane / PostgreSQL

File: `apps/api/tests/test_phase5_control_plane_remediation.py`

Thirty-one tests cover:

- Validation Run/step/Workspace/Checkpoint/Profile/revision/policy/schema;
- fixed argv/cwd/environment;
- Runner/Job/Attempt/Lease/Permit sequence/ID/fence;
- revoke-requested Grant;
- stdout, stderr, combined output, exact limit and limit + 1;
- zero-artifact exact boundary and any-artifact overflow;
- truncation, manifest and evidence-digest mismatch;
- path traversal and special-file metadata;
- repeated rejection with zero success side effects;
- legal completion and identical replay stored once; and
- real cancellation cleanup failure/replay to `recovery_required`.

Result:

```text
31 passed in 7.51s; exit 0
```

Combined focused Validation selection:

```text
40 passed, 13 deselected in 9.67s; exit 0
```

## Unchanged focused audit after repair

```text
uv run pytest \
  apps/api/tests/test_phase5_focused_security_review.py \
  --no-cov -q
```

```text
8 passed in 1.90s; exit 0
```

Focused `P5-AUD-005 or P5-AUD-006`:

```text
7 passed, 1 deselected in 1.83s; exit 0
```

The independent test file itself is unchanged. These local passes are
implementer evidence and do not close independent Findings.

## Zero-success-side-effect evidence

Every permanent rejection is submitted twice where the protocol reaches the
Control Plane. PostgreSQL assertions after rejection require:

```text
RunnerJob.state in {running, cancel_requested}
RunnerJob.result is NULL
SideEffectPermit.state = consumed
ValidationRun.completed_at is NULL
ValidationEvidence count = 0
job_succeeded count = 0
side_effect_permit_completed count = 0
Workspace.current_tree_hash = original Checkpoint fingerprint
```

The valid 8192-byte exact-boundary case succeeds. Its identical replay reports
`idempotent_replay=true`, with exactly one Evidence and one
`job_succeeded`.

The cancellation cleanup-failure case requires:

```text
RunnerJob.state = failed
RunnerJob.result is NULL
SideEffectPermit.state = failed
ValidationRun.state = recovery_required
ValidationEvidence absent
job_failed count = 1
cancel_acknowledged count = 0
job_succeeded count = 0
side_effect_permit_completed count = 0
Workspace fingerprint unchanged
```

The identical failure replay returns the same terminal outcome without new
events or Evidence.

## PostgreSQL and migration

Complete API:

```text
118 passed in 18.53s; exit 0
```

The final full backend collection, including both same-named independent audit
modules under importlib collection, produced:

```text
214 passed; 82.82% coverage; exit 0
```

The first migration command ran against a populated test database. Revision
0007 downgraded successfully to 0006, then historical 0006 correctly could not
restore the pre-Validation Permit operation constraint while `validate` rows
existed:

```text
ck_side_effect_permits_operation violated; exit 1
```

This is classified as a populated-fixture precondition failure, not a 0007 DDL
failure. Only the exact disposable project/volume was removed and recreated.
On the empty real PostgreSQL database:

```text
base → 0007 head → base → 0007 head; exit 0
```

No migration was rewritten. New evidence fields are additive in
`20260729_0007_bind_validation_result_evidence`.

## Contracts, static and Web

| Gate                                | Result                                           |
| ----------------------------------- | ------------------------------------------------ |
| first `make contracts-check`        | expected drift at OpenAPI line 4034; exit 1      |
| regenerate + `make contracts-check` | pass; exit 0                                     |
| Python format                       | 116 files formatted after two focused fixes      |
| Ruff                                | all checks passed                                |
| mypy                                | 85 source files, no issues                       |
| TypeScript                          | pass after evidence fixture received new fields  |
| Web tests                           | 8 files / 44 tests passed                        |
| Web coverage                        | 71.19% statements, 66.13% branches, 73.07% lines |
| Next production build               | pass; 11 routes                                  |
| `git diff --check`                  | pass                                             |

The two independent focused audit files have the same non-package top-level
module name and include audit-intentional dynamic typing. They remain fully
runtime-tested but are excluded from mypy discovery; their source and
assertions are unchanged.

## Sandbox, invariance and broader gates

| Gate                             | Result                                                                   |
| -------------------------------- | ------------------------------------------------------------------------ |
| Validation sandbox               | Landlock FS, seccomp network, fixed pass/fail and bounded exits passed   |
| source invariance                | 119 entries, 10 Git objects, 2 status records; PASS                      |
| Phase 4 findings tool            | six repair controls present; historical `FAIL_PRESERVED`                 |
| historical Runner security audit | 19 passed                                                                |
| Workspace/Protocol security      | 63 passed plus static descriptor/isolation checks                        |
| Phase 4 repair aggregate         | 82 Runner/Protocol + 14 PostgreSQL API passed                            |
| Playwright E2E                   | 16/16 desktop/narrow passed, including Phase 5 validation                |
| Workspace chaos                  | stale fences, atomicity, revocation, recovery and source/.git invariance |
| Security                         | secrets/static checks; 7 scanner + 106 Runner/API/Protocol tests passed  |
| Eval                             | 58 deterministic cases plus 7 scanner tests passed                       |

The E2E and Chaos scripts compare the source and canonical Workspace fixture
HEAD/status/tree fingerprints before and after. Validation sandbox cleanup and
complete process-group absence are exercised by the dedicated sandbox and
Runner suites.

## First gate failures and corrections

| First failure                                               | Classification                         | Correction and focused rerun                        |
| ----------------------------------------------------------- | -------------------------------------- | --------------------------------------------------- |
| Runner fixture Lease `1` below Protocol minimum `2`         | test setup                             | fixture `2`; secure assertion unchanged             |
| legal API fixture missing new evidence returned `409`       | expected compatibility fixture failure | fixture constructs real binding; success passes     |
| populated DB downgrade hit pre-Validation Permit constraint | disposable data precondition           | empty exact project volume; full roundtrip passes   |
| mypy duplicate independent audit module name                | tooling/test-layout issue              | exclude only immutable runtime-tested audit modules |
| OpenAPI contract drift                                      | expected generated artifact drift      | regenerate; drift check passes                      |
| Python/export formatting                                    | mechanical                             | focused format/sort; checks pass                    |
| Web evidence fixture missing new fields                     | generated contract fixture             | add bounded evidence fields; TS/Web/build pass      |
| first final aggregate collected duplicate audit module name | tooling/test-layout issue              | importlib collection; full 214-test backend passes  |

## Runtime cleanup

Every E2E/Chaos project uses an explicit project name and its own cleanup trap.
The remediation PostgreSQL operations use only
`visualengineer-phase5-remediation-1`. After exact project cleanup, filtered
container/network/volume counts are:

```text
visualengineer-phase5-remediation-1 containers=0 networks=0 volumes=0
visualengineer-e2e containers=0 networks=0 volumes=0
visualengineer-workspace-chaos containers=0 networks=0 volumes=0
```

No unfiltered global Docker inventory/inspect/log/exec/network/volume command
was used.

## Final aggregate and disposition

The first final aggregate reached full pytest collection and failed because
the two immutable independent audit files have the same basename in a
non-package test layout. That first failure is preserved. The repository now
uses pytest importlib collection and includes the API tests in the configured
Python path; no audit source was changed.

The simultaneous focused selection then passed `45/45`, and the full backend
suite passed `214/214` at 82.82% coverage. The final complete command:

```text
COMPOSE_PROJECT_NAME=visualengineer-phase5-remediation-1 make verify
```

returned exit `0`. It included contracts, formatting, lint, Python and
TypeScript typecheck, the full backend/Runner/Protocol suite, Web `44/44`,
production build, real-PostgreSQL migration and integration gates, Validation
sandbox, source invariance, Phase 4 security regressions, E2E `16/16`, Chaos,
Security, Eval and final `git diff --check`.

Exact filtered remediation, E2E and Chaos resource inventories are zero.
Main, reviewed implementation and audit references remain unchanged. The two
independent audit test files remain byte-for-byte unchanged from the base.
The one authorized local checkpoint is created by this candidate with:

```text
fix(validation): validate runner result bindings and budgets
```

This is implementer evidence. Independent focused re-audit, remote CI, main
integration and Security Gate approval remain not verified or authorized.
