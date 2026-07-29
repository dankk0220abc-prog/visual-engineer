# Phase 5 Governed Validation Independent Focused Security Re-Audit

- Review date: 2026-07-29 (Asia/Shanghai)
- Remediation candidate:
  `8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9`
- Focused-review checkpoint:
  `cd980582e9d950cb0176eae46ffaedd528ce0afe`
- Reviewed implementation:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Main baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Review branch: `audit/phase-5-validation-remediation-focused-max`
- Independence: no production implementation was changed
- Status: **COMPLETE**
- Focused Re-Audit Gate: **FAIL**
- Required next state: **REMEDIATION REQUIRED**

## 1. Completion status

The independent focused re-audit is administratively complete. Three of the
four requested scopes pass their focused checks. `VE-P5-FSR-002` fails because
a newly preserved real-PostgreSQL production-path reproduction proves that a
successful active Validation cancellation leaves its consumed Side-effect
Permit open.

The Finding is `VE-P5-FREAUD-001`, classified blocking Medium. The focused
PASS prerequisite is therefore false. The final aggregate and PASS sealing
were correctly not run.

A separate preflight governance nonconformance is also confirmed: the
remediation candidate leaves both historical focused-review tests
byte-identical and runtime-passing, but adds targeted mypy exclusions for
those exact files. That weakens their aggregate static-analysis coverage and
fails the request's strict “not loosened” condition. It is not counted as a
production security Finding.

## 2. Focused Security Re-Audit

**FAIL.**

- Critical: 0
- High: 0
- blocking Medium: 1
- non-blocking new Findings: 0
- blocking audit-governance nonconformances: 1

The decision follows from independent tests reaching candidate production
code and a direct source-path confirmation. It does not rely on implementer
claims or historical aggregate results.

## 3. Final Integration Gate

**NOT RUN.**

The review contract permits one final `make verify` only after all four
focused scopes pass with no blocking Finding. That prerequisite is false.
Browser/E2E, Chaos, broad Docker, Security, Eval, coverage, full migration
roundtrip, and the reserved PASS sealing subject were not run.

## 4. Git baseline and branch

The independently confirmed ancestry is:

```text
main 928a89d2055d172bbd7c6670b42f668d103dcb03
  ...
implementation 1b6481156337c9f615240bf10dcca3f1e6833400
  ...
focused checkpoint cd980582e9d950cb0176eae46ffaedd528ce0afe
  |
remediation candidate 8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9
```

The candidate parent is exactly the focused-review checkpoint and the range
contains exactly one commit. The audit branch was created directly from the
candidate without force:

`audit/phase-5-validation-remediation-focused-max`

Preflight found a clean candidate worktree/index/untracked inventory, one
worktree, and no remote, stash, tag, Git lock, replace ref, or hidden
remote-tracking ref.

## 5. Independence and production-code invariance

The frozen production boundary contains 163 tracked entries and has candidate
`git ls-tree` digest:

`639efb52c3061220ebbe6dd8b34a8c75274412c3b39816074da129197557cd7e`

It covers:

- `apps/api/src`
- `apps/api/alembic/versions`
- `apps/api/Dockerfile`
- `apps/runner/src`
- `apps/runner/Dockerfile`
- `apps/web/src`
- `apps/web/e2e`
- `apps/web/Dockerfile`
- `packages/runner-protocol/src`
- `packages/api-contract`
- `compose.yaml`
- `infra`
- `scripts`
- `Makefile`
- `pyproject.toml`

Review changes are confined to two additive independent audit-test files, the
focused re-audit ExecPlan, this report, verification evidence, and project
status. No production source, migration, generated contract, Web, Compose,
infrastructure, gate, dependency, or environment file was changed.

## 6. Four-scope decision matrix

| Scope           | Decision | Independent result                                                                                                                                                         |
| --------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VE-P5-FSR-001` | **PASS** | Leader-first timeout remains bound to the process group; two TERM-ignoring descendants with already-closed output are killed and reaped; legal control remains unaffected. |
| `VE-P5-FSR-002` | **FAIL** | Typed cleanup failure persists one atomic `recovery_required` result, but successful active cancellation leaves the Validation Permit `consumed`.                          |
| `P5-AUD-005`    | **PASS** | A wrong trusted execution-envelope digest with a recomputed self-consistent evidence digest is rejected twice with zero success side effects.                              |
| `P5-AUD-006`    | **PASS** | Independent UTF-8, artifact arithmetic, duplicate-path, digest, exact-boundary, overflow, rejection-replay, and legal-replay checks pass.                                  |

These are focused decisions only. They do not imply aggregate, deployment,
remote CI, customer, or later-phase approval.

## 7. `VE-P5-FSR-001` — timeout and process-group cleanup

**PASS.**

The unchanged historical Runner focused audit passes `6/6`. The new
independent reproduction runs twice and makes the leader spawn two
TERM-ignoring descendants. Each descendant closes stdout/stderr before the
governed deadline, so pipe EOF cannot be used as a proxy for process-group
absence.

Both iterations prove:

- the collector remains bound to the timeout after leader exit and pipe EOF;
- TERM/grace/KILL completes within the audit deadline;
- the typed timeout exit is `124`;
- the leader is reaped;
- stdout and stderr resources are closed;
- the process group and both exact descendant PIDs are absent; and
- neither descendant reaches its post-sleep survivor marker.

A separate legal short-command control returns its exact stdout/stderr, exit
`0`, closed streams, a reaped leader, and no live process group.

The independent Runner file passes `3/3`; the complete Runner security-audit
selection passes `22/22`.

## 8. `VE-P5-FSR-002` — cleanup failure, recovery, and normal cancellation

**FAIL.**

The repaired cleanup-failure path itself passes. With a real PostgreSQL
database, an active Validation cancellation followed by
`validation_process_remained`:

- fails Job and Attempt;
- terminalizes the Permit as `failed`;
- sets Validation Run and step to `recovery_required`;
- stores no successful Result or Evidence;
- emits one `job_failed`, no `cancel_acknowledged`, no `job_succeeded`, and no
  `side_effect_permit_completed`;
- preserves the canonical Workspace fingerprint; and
- replays idempotently without duplicate terminal effects.

The required normal active-cancel control fails. The cancel request and
Runner acknowledgement both return HTTP `200`. Job, Attempt, Validation Run,
and step become `cancelled`; one `cancel_acknowledged` exists; no Evidence or
success event exists; and the Workspace is unchanged. The consumed Permit,
however, remains:

```text
actual:   ("consumed", terminal_at is not None == False)
expected: ("cancelled", terminal_at is not None == True)
```

The same semantic secure expectation failed on the first full independent API
run and four focused reruns. It was unchanged for the initial `3/3`. A later
audit-only change moved already-required invariant assertions before the
Permit assertion and improved the final tuple diagnostic; the expectation
then failed another `2/2`.

## 9. `P5-AUD-005` — trusted completion envelope

**PASS within the requested focused scope.**

The independent test replaces the execution-envelope digest with a distinct
wrong value, recomputes the outer evidence digest so the payload is internally
self-consistent, and submits the payload twice. Both requests return HTTP
`409` with `validation_result_evidence_invalid`.

After both rejections:

- the Job remains non-terminal with no stored Result;
- the Permit remains consumed but not completed;
- the Validation Run remains incomplete;
- Evidence count is zero;
- `job_succeeded` count is zero;
- `side_effect_permit_completed` count is zero; and
- the Workspace fingerprint is unchanged.

The unchanged historical API focused audit passes `8/8`, and the permanent
Control Plane remediation suite passes `31/31`.

## 10. `P5-AUD-006` — output, artifact, and evidence budgets

**PASS within the requested focused scope.**

Independent cases prove:

- 8192 UTF-8 output bytes are accepted and identical replay persists exactly
  one Evidence and one success event;
- 8193 UTF-8 bytes are rejected with zero success side effects;
- a negative artifact count and an overflow-sized artifact total fail at the
  Protocol boundary with HTTP `422`;
- duplicate artifact paths cannot hide behind reported count/byte totals of
  zero;
- the artifact manifest and full evidence digest are independently checked;
  and
- repeated invalid completion does not create a Result, complete a Permit,
  emit success, create Evidence, or mutate the Workspace.

The candidate Profile's artifact budget remains zero. No non-zero artifact
transport or broader artifact feature is approved.

## 11. Zero-success-side-effect evidence

Every independent completion rejection that reaches the Control Plane is
checked against real PostgreSQL state. Rejections require:

```text
RunnerJob.state = running
RunnerJob.result IS NULL
SideEffectPermit.state = consumed
ValidationRun.completed_at IS NULL
ValidationEvidence count = 0
job_succeeded count = 0
side_effect_permit_completed count = 0
Workspace.current_tree_hash = original Checkpoint fingerprint
```

The valid exact-boundary case succeeds and replays idempotently with one
Evidence, one `job_succeeded`, and one `side_effect_permit_completed`.

The new cancellation Finding does not create a false success result or mutate
the Workspace. Its defect is the open durable Permit fence after the system
has otherwise acknowledged clean cancellation.

## 12. PostgreSQL and transaction evidence

The API focused checks used a real disposable PostgreSQL service on host port
`55433`, not SQLite or a mock. Alembic head was applied by the test fixture.

The unique Compose project was:

`visualengineer-phase5-validation-reaudit-019fae88`

The original focused API file passes `8/8`; permanent Control Plane
remediation tests pass `31/31`; the six non-blocking independent API cases
pass with the active-cancel reproduction deselected; and the active-cancel
reproduction fails consistently through the real transaction path.

The full migration base/head/base/head roundtrip was not run after the focused
Gate became FAIL.

## 13. Runner and Protocol evidence

Focused results:

- unchanged historical Runner focused audit: `6 passed`;
- new independent Runner re-audit: `3 passed`;
- full Runner security-audit directory: `22 passed`;
- permanent Runner remediation regressions: `2 passed`; and
- focused Protocol selection: `5 passed`.

The production timeout test creates and later proves absence of exact PIDs and
the complete process group. The legal control prevents a repair-only
regression from being hidden by the adversarial case.

## 14. Source, sandbox, and resource invariance

`make source-invariance-check` passes with:

- 119 source entries;
- 10 Git objects;
- 2 status records; and
- 0 extension markers.

No canonical Workspace content changed in any real-PostgreSQL rejection,
recovery, success, replay, or cancellation case.

The dedicated validation sandbox Docker probe was not rerun after the blocker
because it cannot change the focused Gate decision and its script would
perform diagnostics broader than the review's exact Docker filter. No claim
is inferred from historical sandbox evidence.

## 15. Original focused tests after remediation

Both historical independent focused-review files have the same Git blob IDs
at the focused checkpoint and remediation candidate:

- API:
  `86ecffbc5dedf4dd85fb126bad16848f89869046`
- Runner:
  `5e56cfe0645ecdbb45fed36484a513661756c716`

Their runtime suites pass `8/8` and `6/6`. Their source/assertions were not
deleted, rewritten, weakened, skipped, marked `xfail`, or converted to
expected-failure metadata. Their aggregate static-analysis coverage was
nevertheless loosened by the separate configuration change below.

## 16. Targeted static-analysis governance nonconformance

**BLOCKING PREFLIGHT NONCONFORMANCE.**

The remediation changes `pyproject.toml` to:

- exclude both exact historical focused-review test files from mypy
  discovery; and
- ignore errors for their shared
  `test_phase5_focused_security_review` module name.

The same remediation also enables pytest importlib mode and adds the API test
directory to `pythonpath`, so the runtime duplicate-module collection issue is
resolved and both files execute.

Each historical focused file passes mypy when checked separately. Checking
both together exposes the duplicate module-name error that motivated the
configuration. Targeted exclusion solves the aggregate tooling collision by
removing independent audit tests from static analysis, which is a loosening of
their gate coverage. The strict re-audit preflight therefore cannot be
declared fully PASS.

This is recorded independently of `VE-P5-FREAUD-001`. It is governance/tooling
evidence, not a second production severity count.

## 17. Final `make verify`

**NOT RUN.**

The remediation report's prior successful aggregate is historical implementer
evidence. It is not an independent re-audit result and cannot override the
current blocking Finding or the preflight nonconformance.

## 18. First failures, audit corrections, and reruns

The first new Runner file was mechanically formatted before behavior
classification; the secure assertions did not change. It then passed `3/3`.

The first new API run produced:

```text
6 passed, 1 failed; exit 1
```

The sole failure was the active-cancel Permit assertion. No production change
was made. Two exact focused reruns failed with the same `consumed` state,
establishing an unchanged `3/3`.

For clearer evidence, the independent test was then changed only to check the
already-required Job/Attempt/Run/step/Workspace/event/Evidence invariants
before the Permit and to display the state/terminal tuple. Two further focused
runs failed with the same Permit outcome.

No assertion was removed, weakened, skipped, marked `xfail`, or changed into
an expected failure. No production repair was attempted.

## 19. New Finding

| Finding            | Boundary                                   | Trigger                                                                                                                     | Expected                                                                                                                                                                | Actual                                                                                                                  | Severity        | Stable evidence                                       | Persistent side effect                                                                                                            |
| ------------------ | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | --------------- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `VE-P5-FREAUD-001` | `VE-P5-FSR-002` normal active cancellation | A running Validation job has consumed its Permit; the user requests cancel; Runner confirms cleanup and posts `/cancelled`. | Job, Attempt, Validation Run, step, and Permit become cancelled atomically; Permit receives `terminal_at`; no Result/Evidence/success side effect; Workspace unchanged. | HTTP `200`; Job/Attempt/Run/step cancel and clean invariants hold, but Permit remains `consumed` with no `terminal_at`. | blocking Medium | first full run plus four focused reruns; all exit `1` | Disposable test transaction rolls back. In a durable deployment the Permit remains an in-flight fence until later expiry/reaping. |

Static root cause:

`RunnerService.cancelled` terminalizes a consumed Permit only when the stored
spec is one of four Workspace job types. `ValidationExecuteJobSpec` is omitted
from that tuple. The method then transitions the Validation Job and Attempt to
`cancelled`, emits `cancel_acknowledged`, and commits.

Potential operational impact beyond the directly proven stale Permit and
deferred grant-revocation path is inferred, not claimed as observed
production impact.

The permanent reproduction is:

`apps/api/tests/test_phase5_validation_control_plane_reaudit.py::test_reaudit_successful_active_cancel_terminalizes_consumed_permit`

## 20. Remaining non-blocking limitations

The following are intentionally `NOT RUN` or `NOT VERIFIED` after the blocker:

- final aggregate and aggregate coverage;
- complete API/Runner/Protocol suites outside the necessary focused set;
- full migration roundtrip;
- browser/E2E/accessibility and Web build;
- validation sandbox Docker probe;
- Chaos, broad Security, and Eval;
- remote CI, deployment, hostile multi-tenant behavior, and customer
  repositories; and
- LLMs, Agents SDK, Providers, credentials, arbitrary commands, package
  installation, non-zero artifact transport, Git delivery, later Phase 5
  slices, and Phase 6.

These limitations are not additional Findings and do not weaken the confirmed
FAIL.

## 21. Git audit checkpoint

This report belongs to a local FAIL audit checkpoint, not the reserved PASS
sealing commit. A commit cannot embed its own object ID without changing that
ID; the exact checkpoint hash is reported in the post-commit administrative
handoff.

The reserved PASS subject
`chore: seal phase 5 governed validation first slice` is not used.

## 22. Worktree, index, and untracked inventory

The remediation candidate started clean. Before checkpoint, every changed or
untracked path is in the explicit audit-only allowlist. After the local
checkpoint, the worktree, index, and untracked inventory must be empty; the
post-commit administrative verification is authoritative for that final
fact.

## 23. CreativeDeploy metadata/content access ledger

CreativeDeploy content was not accessed, read, mounted, scanned, built,
tested, modified, stopped, or cleaned by this review.

No parent/sibling repository discovery or unfiltered Docker inventory was
performed.

## 24. Remote, push, merge, PR, and tag status

- Remote: none
- Push: none
- Merge / fast-forward main: none
- Pull request: none
- Tag: none
- Customer 0: not run
- Later Phase 5 slice / Phase 6: not started

## 25. CONFIRMED / INFERRED / NOT VERIFIED ledger

### CONFIRMED

- Exact main, implementation, focused-checkpoint, and remediation hashes.
- Exact candidate parent and one-commit remediation range.
- Independent branch creation from the exact remediation candidate.
- `VE-P5-FSR-001`, `P5-AUD-005`, and `P5-AUD-006` focused checks pass.
- Cleanup-failure/recovery behavior inside `VE-P5-FSR-002` passes.
- Normal active cancellation leaves a consumed Permit; blocking Medium
  `VE-P5-FREAUD-001`.
- The new Finding's semantic secure expectation is stable across five
  executions.
- Historical focused tests are byte-identical and runtime-passing.
- Their targeted mypy exclusion is a blocking governance nonconformance.
- Real PostgreSQL, exact process/PID cleanup, source invariance, and filtered
  Compose cleanup results described above.
- Production code is unchanged relative to the candidate.
- Main is unchanged and no remote, push, merge, PR, or tag occurred.
- CreativeDeploy content was not accessed.

### INFERRED

- An unterminated consumed Permit can delay a pending Grant revocation until a
  later expiry/reaper path.
- Wider fleet or operator impact is possible but was not tested or observed.

### NOT VERIFIED

- Aggregate, coverage, full migration, browser/E2E, Chaos, broad Security,
  Eval, and sandbox Docker probe.
- Remote CI, production, deployment, hostile multi-tenant execution, or
  customer behavior.
- Any scope outside this first governed-validation vertical slice.

## 26. Recommended next action

Create a narrow production remediation from
`8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9` that:

1. atomically terminalizes the exact consumed Validation Permit during a
   successful active cancellation, including `terminal_at` and any dependent
   grant-revocation finalization;
2. preserves every independent secure assertion unchanged; and
3. removes the targeted mypy weakening while retaining deterministic
   collection of both historical audit modules.

Then request a fresh independent focused re-audit. Do not run PASS sealing,
move main, start Customer 0, or begin a later phase before that review passes.

**PHASE 5 FOCUSED RE-AUDIT FAIL — REMEDIATION REQUIRED**
