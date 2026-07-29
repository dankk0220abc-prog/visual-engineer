# Phase 5 Governed Validation Independent Focused Re-Audit Verification

- Date: 2026-07-29 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `audit/phase-5-validation-remediation-focused-max`
- Remediation candidate:
  `8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9`
- Focused-review checkpoint:
  `cd980582e9d950cb0176eae46ffaedd528ce0afe`
- Reviewed implementation:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Main:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Status: COMPLETE — FOCUSED RE-AUDIT FAIL
- Coverage: not collected for focused `--no-cov` runs
- Final aggregate: NOT RUN
- Remote CI: NOT VERIFIED

## Evidence boundary

This evidence covers only the four authorized Phase 5 Governed Validation
focused re-audit scopes:

1. `VE-P5-FSR-001` — leader-first timeout/process-group cleanup;
2. `VE-P5-FSR-002` — cleanup-failure recovery and normal cancellation;
3. `P5-AUD-005` — trusted completion-envelope binding; and
4. `P5-AUD-006` — output/artifact/evidence budgets.

The remediation implementation report was used as a navigation aid, not as
independent proof. Every current verdict is tied to source review,
byte-identity review, independent tests, real PostgreSQL, exact local process
cleanup, or filtered Compose cleanup.

No production source, migration, Protocol, generated contract, Web, Compose,
infrastructure, Makefile, dependency, environment, or gate file was changed.
No CreativeDeploy content or sibling repository was accessed.

## Git baseline command ledger

All commands in this document ran with working directory fixed to
`/Users/danke/Developer/VisualEngineer`.

| Command / check                           | Exit | Confirmed result                                           |
| ----------------------------------------- | ---: | ---------------------------------------------------------- |
| `pwd`                                     |    0 | exact repository root                                      |
| `git rev-parse --show-toplevel`           |    0 | exact repository root                                      |
| initial `git branch --show-current`       |    0 | `fix/phase-5-governed-validation-remediation-1`            |
| initial `git rev-parse HEAD`              |    0 | exact candidate `8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9` |
| `git rev-parse main`                      |    0 | `928a89d2055d172bbd7c6670b42f668d103dcb03`                 |
| candidate object type                     |    0 | `commit`                                                   |
| focused checkpoint object type            |    0 | `commit`                                                   |
| implementation object type                |    0 | `commit`                                                   |
| candidate parent inspection               |    0 | exactly `cd980582e9d950cb0176eae46ffaedd528ce0afe`         |
| `git rev-list --count cd980582...8ca5c9e` |    0 | `1`                                                        |
| focused checkpoint ancestor check         |    0 | candidate descends from checkpoint                         |
| initial worktree/index/untracked checks   |    0 | empty                                                      |
| remote/stash/tag checks                   |    0 | empty                                                      |
| worktree inventory                        |    0 | one worktree                                               |
| `.git` lock check                         |    0 | none                                                       |
| replace/notes/special-ref review          |    0 | none affecting candidate ancestry                          |
| candidate `git diff --check`              |    0 | no whitespace error                                        |

Branch creation:

```text
git switch -c audit/phase-5-validation-remediation-focused-max \
  8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9
```

Exit: `0`. No branch was overwritten or force-moved.

## Candidate and remediation diff

The candidate is one commit:

```text
8ca5c9e fix(validation): validate runner result bindings and budgets
28 files changed, 2863 insertions(+), 221 deletions(-)
```

The complete diff, implementation/remediation ExecPlans and evidence,
historical focused report/evidence, architecture, threat model, Runner/API/
Protocol source, migrations, permanent tests, and generated contracts were
read before dynamic classification.

No test-special-casing was found in production. Normal test fixture references
were not treated as special-casing.

## Frozen production boundary

Exact paths:

```text
apps/api/src
apps/api/alembic/versions
apps/api/Dockerfile
apps/runner/src
apps/runner/Dockerfile
apps/web/src
apps/web/e2e
apps/web/Dockerfile
packages/runner-protocol/src
packages/api-contract
compose.yaml
infra
scripts
Makefile
pyproject.toml
```

Candidate inventory:

```text
tracked entries: 163
git ls-tree SHA-256:
639efb52c3061220ebbe6dd8b34a8c75274412c3b39816074da129197557cd7e
```

Pre-checkpoint production invariance:

```text
git diff --exit-code \
  8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9 -- <exact paths above>
```

Exit: `0`.

The final checkpoint repeats this comparison and the inventory digest. The
commit containing this document cannot self-embed its own object ID; the
post-commit handoff reports that hash and the final clean-state result.

## Historical audit-test integrity

Git blob comparison at the focused-review checkpoint and remediation
candidate:

| File                                                                      | Checkpoint blob                            | Candidate blob | Result         |
| ------------------------------------------------------------------------- | ------------------------------------------ | -------------- | -------------- |
| `apps/api/tests/test_phase5_focused_security_review.py`                   | `86ecffbc5dedf4dd85fb126bad16848f89869046` | same           | byte-identical |
| `apps/runner/tests/security_audit/test_phase5_focused_security_review.py` | `5e56cfe0645ecdbb45fed36484a513661756c716` | same           | byte-identical |

Runtime:

```text
Runner historical focused file: 6 passed in 2.27s; exit 0
API historical focused file:    8 passed; exit 0
```

The remediation did not delete, rewrite, skip, weaken, `xfail`, or otherwise
change those runtime assertions.

## Static-analysis preflight nonconformance

Candidate `pyproject.toml` adds:

```toml
exclude = [
  "apps/api/tests/test_phase5_focused_security_review.py",
  "apps/runner/tests/security_audit/test_phase5_focused_security_review.py",
]

[[tool.mypy.overrides]]
module = "test_phase5_focused_security_review"
ignore_errors = true
```

It also enables pytest importlib collection, which successfully lets both
same-named test files run together. The mypy behavior was independently
reproduced:

| Command                                                                               | Exit | Result                |
| ------------------------------------------------------------------------------------- | ---: | --------------------- |
| `uv run mypy apps/api/tests/test_phase5_focused_security_review.py`                   |    0 | no issues             |
| `uv run mypy apps/runner/tests/security_audit/test_phase5_focused_security_review.py` |    0 | no issues             |
| `uv run mypy <both historical focused files>`                                         |    2 | duplicate module name |

The candidate resolves aggregate mypy by excluding both exact independent
audit files and ignoring their shared module. Because the user required proof
that the original tests were not loosened, this is a blocking preflight
governance nonconformance even though both files remain byte-identical and
runtime-passing.

## Independent additive test inventory

| Test                                                                                 | Boundary                        | Expected decision                                                        |
| ------------------------------------------------------------------------------------ | ------------------------------- | ------------------------------------------------------------------------ |
| `test_reaudit_timeout_kills_multiple_descendants_after_output_closes` (2 iterations) | `VE-P5-FSR-001`                 | group-bound deadline, TERM/KILL, reap, closed streams, exact PID absence |
| `test_reaudit_normal_command_collects_and_reaps_without_timeout`                     | `VE-P5-FSR-001` control         | legal execution unaffected                                               |
| `test_reaudit_process_remained_failure_persists_recovery_once`                       | `VE-P5-FSR-002` cleanup failure | atomic failure/recovery and idempotent replay                            |
| `test_reaudit_successful_active_cancel_terminalizes_consumed_permit`                 | `VE-P5-FSR-002` normal cancel   | all durable terminal records, including Permit, cancel together          |
| `test_reaudit_execution_envelope_digest_mismatch_is_rejected_twice`                  | `P5-AUD-005`                    | trusted envelope cannot be self-blessed                                  |
| `test_reaudit_duplicate_artifact_path_is_rejected_twice`                             | `P5-AUD-006`                    | duplicate paths rejected despite forged totals/digests                   |
| `test_reaudit_invalid_artifact_arithmetic_fails_at_protocol_boundary` (2 parameters) | `P5-AUD-006`                    | negative/overflow arithmetic rejected                                    |
| `test_reaudit_utf8_output_exact_limit_and_plus_one`                                  | `P5-AUD-006`                    | exact UTF-8 byte boundary and idempotent replay                          |

No test is skipped, `xfail`, or converted into expected-failure metadata.

## Runner focused command ledger

| Selection                                             | Exit |              Count | Result                                         |
| ----------------------------------------------------- | ---: | -----------------: | ---------------------------------------------- |
| unchanged historical Runner focused file              |    0 |           6 passed | historical Findings close on candidate runtime |
| new independent Runner re-audit file                  |    0 |  3 passed in 1.93s | two adversarial iterations plus legal control  |
| complete `apps/runner/tests/security_audit` directory |    0 | 22 passed in 7.35s | necessary security regression                  |
| `apps/runner/tests/test_phase5_remediation.py`        |    0 |           2 passed | permanent remediation regressions              |
| focused Protocol validation selection                 |    0 |           5 passed | strict result model/canonical helpers          |

The multi-descendant test is parameterized for two iterations. Each test-owned
leader starts its own process group. Two descendants ignore SIGTERM and close
stdout/stderr before the timeout. After the production collector returns:

```text
exit_code = 124
timed_out = true
cancelled = false
stdout = stderr = empty
streams = closed
leader = reaped
process group = absent
both exact descendant PIDs = absent
survivor markers = absent
```

The `finally` block sends SIGKILL only to the exact test-owned process group if
it unexpectedly remains, then waits on the exact leader. No process or PID
residue remained.

The normal control returns:

```text
(0, b"normal-out", b"normal-err", false, false, false, false)
```

and proves closed streams, a reaped leader, and absent group.

## Real PostgreSQL setup

Only this unique Compose project was used:

`visualengineer-phase5-validation-reaudit-019fae88`

Setup:

```text
docker compose \
  -p visualengineer-phase5-validation-reaudit-019fae88 \
  --profile test up -d --wait test-db
```

Exit: `0`.

The tests used the real service through host port `55433`. The API fixtures
applied Alembic head. No `.env` file was edited.

No unfiltered Docker inventory, inspect, logs, exec, network, or volume
command was run.

## API focused passing ledger

| Selection                                                | Exit |                  Count | Result                                               |
| -------------------------------------------------------- | ---: | ---------------------: | ---------------------------------------------------- |
| unchanged historical API focused file                    |    0 |               8 passed | remediated outer/envelope/budget checks pass         |
| permanent Control Plane remediation file                 |    0 |     31 passed in 7.47s | real-PostgreSQL terminal, rejection and replay paths |
| new independent API file excluding active-cancel Finding |    0 | 6 passed, 1 deselected | all non-blocking independent cases pass              |

The independent envelope and duplicate-artifact cases each submit the same
invalid completion twice. The real database remains without successful
Result, completed Permit, success event, or Evidence.

The UTF-8 test proves:

```text
"界" * 2731 = 8193 bytes -> HTTP 409, no success side effect
("界" * 2730) + "xx" = 8192 bytes -> HTTP 200
identical legal replay -> HTTP 200, idempotent_replay=true
Evidence count = 1
job_succeeded count = 1
side_effect_permit_completed count = 1
```

Negative artifact count and a `2**63` artifact total return HTTP `422`.
Duplicate artifact paths with forged reported totals return HTTP `409`.

## Cleanup-failure recovery evidence

The independent real-PostgreSQL sequence:

1. creates an approved governed Validation Run and active Runner Attempt;
2. consumes the exact Validation Permit;
3. requests cancellation;
4. posts `validation_process_remained`;
5. replays the exact failure once.

Observed after transaction refresh:

```text
Job.state = failed
Job.result = NULL
Attempt.state = failed
Permit.state = failed
ValidationRun.state = recovery_required
ValidationStepRun.state = recovery_required
ValidationRun.error_code = validation_process_remained
Workspace fingerprint = unchanged
job_failed count = 1
cancel_acknowledged count = 0
job_succeeded count = 0
side_effect_permit_completed count = 0
ValidationEvidence count = 0
failure replay idempotent_replay = true
```

This closes the historical cleanup-failure behavior. It does not close the
separate successful active-cancel control.

## First active-cancel behavior failure

The first complete new API-file execution:

```text
6 passed, 1 failed; exit 1
```

The only failed test was:

```text
test_reaudit_successful_active_cancel_terminalizes_consumed_permit
```

Initial actual:

```text
permit.state = consumed
```

Expected:

```text
permit.state = cancelled
permit.terminal_at IS NOT NULL
```

No production code was changed.

## Active-cancel stability ledger

The exact secure expectation was selected twice more before any audit-test
diagnostic change:

| Run | Selection                           | Exit | Result                   |
| --: | ----------------------------------- | ---: | ------------------------ |
|   1 | first complete independent API file |    1 | Permit remained consumed |
|   2 | exact active-cancel test            |    1 | same                     |
|   3 | exact active-cancel test            |    1 | same                     |

Stable unchanged result: `3/3`.

The independent test was then improved only by:

- moving the already-required Job/Attempt/Run/step/Workspace/event/Evidence
  assertions before the Permit assertion; and
- formatting the final assertion as
  `(permit.state, permit.terminal_at is not None)`.

Two more exact focused runs failed:

```text
actual:   ("consumed", False)
expected: ("cancelled", True)
exit: 1
```

Total semantic stability: first full run plus four focused reruns, `5/5`.
The secure expectation was never weakened.

## Active-cancel invariant matrix

Real PostgreSQL after the accepted Runner cancellation acknowledgement:

| Record / event                    | Expected                          | Actual                          | Result   |
| --------------------------------- | --------------------------------- | ------------------------------- | -------- |
| HTTP cancellation acknowledgement | 200 / cancelled                   | 200 / cancelled                 | PASS     |
| Job                               | cancelled, no Result              | cancelled, no Result            | PASS     |
| Attempt                           | cancelled                         | cancelled                       | PASS     |
| Validation Run                    | cancelled                         | cancelled                       | PASS     |
| Validation step                   | cancelled                         | cancelled                       | PASS     |
| Workspace fingerprint             | unchanged                         | unchanged                       | PASS     |
| Evidence                          | absent                            | absent                          | PASS     |
| `cancel_acknowledged`             | 1                                 | 1                               | PASS     |
| `job_succeeded`                   | 0                                 | 0                               | PASS     |
| `side_effect_permit_completed`    | 0                                 | 0                               | PASS     |
| Side-effect Permit                | cancelled, terminal timestamp set | consumed, no terminal timestamp | **FAIL** |

## Static root-cause confirmation

`RunnerService.cancelled` parses the persisted job specification, then calls
`_terminalize_side_effect_permit(..., state="cancelled")` only for:

```text
WorkspacePrepareJobSpec
WorkspaceWriteTextJobSpec
WorkspaceRollbackJobSpec
WorkspaceDiscardJobSpec
```

`ValidationExecuteJobSpec` is omitted. The method then cancels the Attempt and
Job, emits `cancel_acknowledged`, and commits.

The terminalization helper would convert a consumed Permit to the requested
terminal state, set `terminal_at`, and attempt dependent Grant-revocation
finalization. The helper is simply not reached for the Validation cancel path.

Classification:

```text
Finding: VE-P5-FREAUD-001
Severity: blocking Medium
Root cause: production lifecycle omission
Production fix during review: none
```

## Audit-test preparation and correction ledger

The first formatting check for the two new audit files reported both required
formatting; exit `1`. The files were mechanically formatted. The focused
format/lint rerun:

```text
uv run ruff format --check \
  apps/api/tests/test_phase5_validation_control_plane_reaudit.py \
  apps/runner/tests/security_audit/test_phase5_validation_runner_reaudit.py

uv run ruff check \
  apps/api/tests/test_phase5_validation_control_plane_reaudit.py \
  apps/runner/tests/security_audit/test_phase5_validation_runner_reaudit.py
```

Exit: `0`; `2 files already formatted`; `All checks passed!`.

The first direct mypy check of the new API file reached an imported permanent
remediation test and reported only:

```text
apps/api/tests/test_phase5_control_plane_remediation.py:13:
Unused "type: ignore" comment [unused-ignore]
exit 1
```

No audit-file type error was reported. The focused rerun disabled only that
warning:

```text
uv run mypy --no-warn-unused-ignores \
  apps/api/tests/test_phase5_validation_control_plane_reaudit.py
```

Exit: `0`; one source file, no issues.

The new Runner file:

```text
uv run mypy \
  apps/runner/tests/security_audit/test_phase5_validation_runner_reaudit.py
```

Exit: `0`; one source file, no issues.

No existing test or production source was changed to silence static analysis.

## Source invariance

Command:

```text
make source-invariance-check
```

Exit: `0`.

Result:

```text
status = PASS
source entries = 119
Git objects = 10
status records = 2
extension markers = 0
```

Canonical Workspace state was also checked directly in all independent
real-PostgreSQL rejection, recovery, success, replay, and cancellation cases.

## Exact Compose cleanup

Cleanup:

```text
docker compose \
  -p visualengineer-phase5-validation-reaudit-019fae88 \
  --profile test down --volumes --remove-orphans
```

Exit: `0`.

Filtered post-cleanup checks:

| Exact check                                                                                                 | Result |
| ----------------------------------------------------------------------------------------------------------- | ------ |
| `docker compose -p visualengineer-phase5-validation-reaudit-019fae88 --profile test ps --all -q`            | empty  |
| `docker ps -aq --filter label=com.docker.compose.project=visualengineer-phase5-validation-reaudit-019fae88` | empty  |
| network list filtered by exact Compose project label                                                        | empty  |
| volume list filtered by exact Compose project label                                                         | empty  |

Container, network, and volume residue: `0`.

No other project was stopped, inspected, or cleaned.

## Focused outcome

| Scope           | Result | Evidence                                                                            |
| --------------- | ------ | ----------------------------------------------------------------------------------- |
| `VE-P5-FSR-001` | PASS   | unchanged `6/6`; independent `3/3`; security audit `22/22`; exact PID/group cleanup |
| `VE-P5-FSR-002` | FAIL   | recovery path passes; normal cancel Permit defect stable `5/5`                      |
| `P5-AUD-005`    | PASS   | independent mismatch rejected twice with zero success effects                       |
| `P5-AUD-006`    | PASS   | independent byte/artifact/digest/replay matrix passes                               |

```text
Critical = 0
High = 0
blocking Medium = 1
blocking audit-governance nonconformance = 1
```

## Gates intentionally not run

The following were stopped by the focused blocker:

- final `make verify`;
- aggregate coverage;
- full API/Runner/Protocol suites beyond necessary focused selections;
- full migration roundtrip;
- browser/E2E/accessibility;
- Web build;
- validation sandbox Docker probe;
- Chaos;
- broad Security;
- Eval; and
- PASS sealing.

Historical implementer results are not restated as current-review PASS
evidence.

## Final allowed-write and Git checks

Before the checkpoint, the confirmed exact changed/untracked inventory was:

```text
apps/api/tests/test_phase5_validation_control_plane_reaudit.py
apps/runner/tests/security_audit/test_phase5_validation_runner_reaudit.py
docs/evidence/phase-5-governed-validation-focused-reaudit-verification.md
docs/exec-plans/phase-5-governed-validation-focused-reaudit.md
docs/security/audits/phase-5-governed-validation-focused-reaudit.md
docs/status/project-status.md
```

Pre-checkpoint results:

- allowed-file formatting/lint/typecheck: PASS with the recorded imported
  `unused-ignore` accommodation;
- Markdown formatting: PASS;
- `git diff --check`: PASS;
- production diff from candidate: empty;
- candidate production inventory: 163 entries with unchanged
  `639efb52...57cd7e` digest;
- main: unchanged at `928a89d...cb03`;
- remote/tag/stash/lock counts: zero;
- worktree count: one;
- exact Compose and PID cleanup: zero residue; and
- index: empty before intentional staging.

Clean worktree/index/untracked inventory after the local FAIL checkpoint is
reported by the post-commit administrative handoff.

The reserved PASS commit subject is forbidden. The local FAIL checkpoint uses
an audit subject and is reported in the post-commit handoff.

## CONFIRMED / INFERRED / NOT VERIFIED

### CONFIRMED

- Exact ancestry, branch, candidate, and main.
- Historical audit tests are byte-identical and runtime-passing.
- Targeted mypy exclusions loosen their aggregate static-analysis coverage.
- Three focused scopes pass; `VE-P5-FSR-002` fails.
- `VE-P5-FREAUD-001` is stable across five semantic executions.
- Real PostgreSQL, zero-success-side-effect, Workspace invariance, source
  invariance, exact process cleanup, and filtered Compose cleanup evidence.
- No production code was changed and no production fix was attempted.
- No CreativeDeploy access, remote, push, merge, PR, tag, Customer 0, later
  Phase 5 slice, or Phase 6 action.

### INFERRED

- The open Permit can delay a requested Grant revocation until a later
  expiry/reaper path.
- Wider operational impact is possible but not observed here.

### NOT VERIFIED

- Aggregate, coverage, full migration, browser/E2E, Chaos, broad Security,
  Eval, validation sandbox Docker, remote CI, deployment, customer, or
  hostile multi-tenant behavior.

**PHASE 5 FOCUSED RE-AUDIT FAIL — REMEDIATION REQUIRED**
