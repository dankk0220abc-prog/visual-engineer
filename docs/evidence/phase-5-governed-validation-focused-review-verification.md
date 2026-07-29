# Phase 5 Governed Validation Independent Focused Review Evidence

- Date: 2026-07-29 (Asia/Shanghai)
- Candidate:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Main:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Audit branch: `audit/phase-5-governed-validation-focused-max`
- Status: COMPLETE — FOCUSED SECURITY REVIEW FAIL
- Coverage: not collected for focused `--no-cov` runs
- Final aggregate: NOT RUN
- Third candidate boundary: NOT VERIFIED

## Evidence boundary

This independent evidence covers only the Phase 5 Governed Validation
Execution boundary. Candidate implementation evidence was used to locate
controls, not to award an independent PASS.

No production source, migration, Protocol, Web, Compose, infrastructure,
Makefile, or gate script was changed. The only write inventory is:

- independent audit tests;
- the focused ExecPlan;
- the focused audit report;
- this verification evidence; and
- project status.

CreativeDeploy content was not accessed. No Docker command was executed during
this review, so no unfiltered global Docker diagnostic was run and no
review-owned container, network, or volume exists.

## Git baseline command ledger

The preflight ran before the independent branch was created.

| Command / check                                                                                                  | Exit | Confirmed result                                                  |
| ---------------------------------------------------------------------------------------------------------------- | ---: | ----------------------------------------------------------------- |
| `pwd`                                                                                                            |    0 | `/Users/danke/Developer/VisualEngineer`                           |
| `git rev-parse --show-toplevel`                                                                                  |    0 | exact VisualEngineer root                                         |
| `git branch --show-current`                                                                                      |    0 | `feat/phase-5-governed-validation-execution`                      |
| `git rev-parse HEAD`                                                                                             |    0 | exact candidate `1b6481156337c9f615240bf10dcca3f1e6833400`        |
| `git rev-parse main`                                                                                             |    0 | exact main `928a89d2055d172bbd7c6670b42f668d103dcb03`             |
| `git status --porcelain=v2 --branch`                                                                             |    0 | candidate branch; clean                                           |
| `git diff --stat`                                                                                                |    0 | empty                                                             |
| `git diff --cached --stat`                                                                                       |    0 | empty                                                             |
| `git ls-files --others --exclude-standard`                                                                       |    0 | empty                                                             |
| `git remote -v`                                                                                                  |    0 | empty                                                             |
| `git stash list`                                                                                                 |    0 | empty                                                             |
| `git worktree list`                                                                                              |    0 | one VisualEngineer worktree                                       |
| `git tag --list`                                                                                                 |    0 | empty                                                             |
| `git show-ref --heads`                                                                                           |    0 | disclosed local branch refs only                                  |
| `git log --oneline --decorate --graph --all -25`                                                                 |    0 | claimed main/candidate history present; no extra candidate commit |
| `git cat-file -t 928a89d2055d172bbd7c6670b42f668d103dcb03`                                                       |    0 | `commit`                                                          |
| `git cat-file -t 1b6481156337c9f615240bf10dcca3f1e6833400`                                                       |    0 | `commit`                                                          |
| `git show --stat --oneline 1b6481156337c9f615240bf10dcca3f1e6833400`                                             |    0 | candidate scope: 60 files, 8,474 insertions, 161 deletions        |
| `git merge-base --is-ancestor 928a89d2055d172bbd7c6670b42f668d103dcb03 1b6481156337c9f615240bf10dcca3f1e6833400` |    0 | main is candidate ancestor                                        |
| `git rev-list --count 928a89d2055d172bbd7c6670b42f668d103dcb03..1b6481156337c9f615240bf10dcca3f1e6833400`        |    0 | `1`                                                               |
| `git diff --check 928a89d2055d172bbd7c6670b42f668d103dcb03..1b6481156337c9f615240bf10dcca3f1e6833400`            |    0 | no whitespace error                                               |
| candidate parent inspection                                                                                      |    0 | parent is exactly main                                            |
| Git lock search anchored at `.git`                                                                               |    0 | no `*.lock` file                                                  |
| submodule / replace / notes / special-ref checks                                                                 |    0 | none                                                              |

Branch creation command:

```text
git switch -c audit/phase-5-governed-validation-focused-max \
  1b6481156337c9f615240bf10dcca3f1e6833400
```

Exit: `0`. No existing branch was overwritten.

## Frozen production boundary

Candidate Git tree:

```text
c0960ab6a75c974917d75cff7f5a5acdadd3cb85
```

Frozen production paths:

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
compose.yaml
infra
scripts
Makefile
```

Candidate boundary inventory:

```text
tracked entries: 157
git ls-tree SHA-256:
b5f8175c2b353870d9b1995a3ddccb369bbe79c81a9f6a60fa7184e934ef153d
```

The checkpoint-stage and post-checkpoint checks compare these exact paths to
the candidate. The commit containing this evidence cannot self-embed its own
Git object ID; the final checkpoint ID and clean-state result are reported in
the post-commit administrative handoff.

Pre-checkpoint invariance rerun:

| Command / check                                                                                              | Exit | Result                                                             |
| ------------------------------------------------------------------------------------------------------------ | ---: | ------------------------------------------------------------------ |
| `git diff --exit-code 1b6481156337c9f615240bf10dcca3f1e6833400 -- <exact production paths above>`            |    0 | no production diff                                                 |
| `git ls-tree -r 1b6481156337c9f615240bf10dcca3f1e6833400 -- <exact production paths above> \| wc -l`         |    0 | 157 entries                                                        |
| `git ls-tree -r 1b6481156337c9f615240bf10dcca3f1e6833400 -- <exact production paths above> \| shasum -a 256` |    0 | `b5f8175c2b353870d9b1995a3ddccb369bbe79c81a9f6a60fa7184e934ef153d` |
| `git rev-parse 1b6481156337c9f615240bf10dcca3f1e6833400^{tree}`                                              |    0 | `c0960ab6a75c974917d75cff7f5a5acdadd3cb85`                         |
| `git rev-parse main`                                                                                         |    0 | `928a89d2055d172bbd7c6670b42f668d103dcb03`                         |
| `git remote -v`; `git tag --list`                                                                            |    0 | both empty                                                         |

## Independent audit test inventory

| Test ID            | Test selection                                                               | Boundary                                       | Status                            |
| ------------------ | ---------------------------------------------------------------------------- | ---------------------------------------------- | --------------------------------- |
| `P5-AUD-001`       | `test_phase5_aud_001_protocol_rejects_free_command_authority` (4 parameters) | closed Protocol command/argv/env/cwd authority | PASS, 4/4                         |
| `P5-AUD-002`       | `test_phase5_aud_002_timeout_kills_leader_first_term_ignoring_descendant`    | timeout and complete cleanup                   | FAIL, stable 3/3; `VE-P5-FSR-001` |
| `P5-AUD-003`       | `test_phase5_aud_003_cancel_cleanup_failure_enters_recovery_not_cancelled`   | cancel cleanup/recovery                        | FAIL, stable 3/3; `VE-P5-FSR-002` |
| `P5-AUD-004`–`006` | API result outer/inner identity and exact-budget draft                       | stopped third candidate boundary               | NOT RUN / NOT VERIFIED            |

The two confirmed Finding assertions remain ordinary failing assertions. They
are not skipped, weakened, deleted, marked `xfail`, or converted into expected
failure metadata.

## Audit-test preparation and static correction ledger

Before the first behavior run, direct review of the new timeout test found an
unbounded audit-harness wait expression. It was replaced with a bounded
monotonic `while` loop. This correction occurred before any candidate behavior
was classified and did not change production code.

The first audit-file formatting/static command was:

```text
uv run ruff format \
  apps/runner/tests/security_audit/test_phase5_focused_security_review.py \
&& uv run ruff check \
  apps/runner/tests/security_audit/test_phase5_focused_security_review.py
```

Exit: `1`.

Result:

```text
1 file reformatted
3 audit-only static findings:
- import ordering
- constant getattr style
- polling wait style
```

Authorized correction:

- organize the audit-only imports;
- use typed attribute access in the fake client; and
- wait on the audit event through `asyncio.to_thread`.

Focused static rerun:

```text
uv run ruff check --fix \
  apps/runner/tests/security_audit/test_phase5_focused_security_review.py \
&& uv run ruff format --check \
  apps/runner/tests/security_audit/test_phase5_focused_security_review.py
```

Exit: `0`.

The stopped API audit draft later received formatting/import-order correction
only. It was not executed and supplies no security conclusion.

Final allowed-file static check before checkpoint:

```text
uv run ruff check \
  apps/api/tests/test_phase5_focused_security_review.py \
  apps/runner/tests/security_audit/test_phase5_focused_security_review.py \
&& pnpm exec prettier --check \
  docs/exec-plans/phase-5-governed-validation-focused-review.md \
  docs/security/audits/phase-5-governed-validation-focused-review.md \
  docs/evidence/phase-5-governed-validation-focused-review-verification.md \
  docs/status/project-status.md
```

Exit: `1`.

Ruff passed both audit-test files. Prettier reported only this report and the
audit report required formatting. The exact two documents were formatted:

```text
pnpm exec prettier --write \
  docs/security/audits/phase-5-governed-validation-focused-review.md \
  docs/evidence/phase-5-governed-validation-focused-review-verification.md
```

Exit: `0`. No production file was included.

## First focused behavior run

Command:

```text
uv run pytest \
  apps/runner/tests/security_audit/test_phase5_focused_security_review.py \
  --no-cov -q
```

Exit: `1`.

Count and complete summary:

```text
....FF                                                                   [100%]
2 failed, 4 passed in 2.08s
```

Observed assertion summaries:

```text
P5-AUD-002:
assert completed_before_audit_watchdog is True
actual: False

P5-AUD-003:
assert fake.cancelled_calls == 0
actual: 1
```

Classification:

- the four `P5-AUD-001` parameters reached the strict candidate Protocol model
  and passed;
- both failures reached candidate production methods;
- neither failure was an audit harness exception;
- no production change was made after either failure.

## Stability rerun ledger

Each failed test was independently selected twice more without changing the
test or candidate.

| Command                                                                                                        | Run | Exit |                  Count | Result                    |
| -------------------------------------------------------------------------------------------------------------- | --: | ---: | ---------------------: | ------------------------- |
| `uv run pytest apps/runner/tests/security_audit/test_phase5_focused_security_review.py -k aud_002 --no-cov -q` |   2 |    1 | 1 failed, 5 deselected | same production assertion |
| same exact `P5-AUD-002` command                                                                                |   3 |    1 | 1 failed, 5 deselected | same production assertion |
| `uv run pytest apps/runner/tests/security_audit/test_phase5_focused_security_review.py -k aud_003 --no-cov -q` |   2 |    1 | 1 failed, 5 deselected | same production assertion |
| same exact `P5-AUD-003` command                                                                                |   3 |    1 | 1 failed, 5 deselected | same production assertion |

One of the two concurrently launched `P5-AUD-003` pytest invocations emitted
a pytest temporary-directory garbage-collection warning caused by concurrent
pytest root cleanup. It did not alter the assertion result, production
repository, Git state, or the injected in-memory lifecycle fixture. No Finding
is derived from that pytest warning.

Stable totals:

```text
P5-AUD-002: 3 failures / 3 runs; exit 1 each
P5-AUD-003: 3 failures / 3 runs; exit 1 each
```

## Finding evidence matrix

| Finding         | Test         | Trigger condition                                                                                                              | Expected                                                                                                  | Actual                                                                                                 | Severity        | Test quantity | Exit code | Evidence persistence                                      |
| --------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | --------------- | ------------: | --------- | --------------------------------------------------------- |
| `VE-P5-FSR-001` | `P5-AUD-002` | A validation process leader completes while a descendant remains attached and ignores initial termination beyond the deadline. | Bounded deadline handling terminates/reaps the exact process group and returns before the audit watchdog. | The production collector does not complete before the audit watchdog; exact audit cleanup is required. | blocking Medium |    3/3 stable | `1` each  | Assertion and full reproduction remain in the audit test. |
| `VE-P5-FSR-002` | `P5-AUD-003` | `cancel_requested` is observed and validation execution reports typed cleanup failure.                                         | No clean cancellation acknowledgement; preserve typed failure/recovery.                                   | Candidate lifecycle acknowledges cancellation and does not submit the typed cleanup failure.           | blocking Medium |    3/3 stable | `1` each  | Assertion and full reproduction remain in the audit test. |

## `VE-P5-FSR-001` detailed technical evidence

Production path:

```text
visual_engineer_runner.validation_executor.ValidationExecutor._collect
```

The reproduction creates one audit-owned session/process group in the pytest
temporary directory. Its leader starts a descendant, waits until the
descendant is ready, and exits. The descendant retains the captured
descriptors and ignores the initial termination signal. Candidate collection
is invoked directly with a monotonic `0.1` second execution timeout and a
separate `1.25` second audit watchdog.

Expected:

1. the governed deadline is observed;
2. TERM is applied to the complete process group;
3. a bounded grace interval is followed by KILL if required;
4. the group is absent/reaped; and
5. collection returns before the independent watchdog.

Actual on all three runs:

```text
completed_before_audit_watchdog = False
```

The audit `finally` block sends KILL only to that exact audit-owned process
group, waits for its leader, and waits for the collector future to return.
This prevents the failing test from leaving a live audit child.

Static correlation after the dynamic failure:

- the collection loop can wait for captured streams after the leader exits;
- termination escalation is conditional on the leader still appearing live;
- the required group-level escalation/absence proof is therefore not
  independent of leader state.

No production fix was attempted.

## `VE-P5-FSR-002` detailed technical evidence

Production path:

```text
visual_engineer_runner.lifecycle.RunnerLifecycle._execute_assignment
```

The reproduction uses a strict, valid Phase 5 validation Job, permission
envelope, grant, assignment, and consumed permit. A minimal fake Control Plane
requests cancellation during the production lifecycle. The execution
substitute waits for the real lifecycle cancellation event, then reports the
typed candidate cleanup failure:

```text
validation_cleanup_failed
```

Expected:

```text
cancelled calls: 0
failure codes: ["validation_cleanup_failed"]
```

Actual on all three runs:

```text
cancelled calls: 1
failure codes: []
```

Static correlation after the dynamic failure:

- cancellation awaits the execution task;
- a Workspace execution error on that path is discarded;
- the lifecycle then submits the cancellation acknowledgement.

The fixture is in-memory except for pytest-owned Runner settings paths. It
does not invoke a real Workspace manager, mutate a canonical Workspace, or
contact a network service. Pytest and monkeypatch cleanup restore all patched
state.

No production fix was attempted.

## Cleanup and persistent-side-effect evidence

| Surface                        | Evidence                                                                         | Result                                  |
| ------------------------------ | -------------------------------------------------------------------------------- | --------------------------------------- |
| `P5-AUD-002` process group     | exact `killpg` in `finally`, leader `wait`, collector-future `result`            | cleanup completed on every run          |
| `P5-AUD-003` lifecycle fixture | in-memory fake client, pytest monkeypatch restoration, no real Workspace manager | cleanup completed                       |
| Repository production boundary | candidate-relative diff checked on exact production allowlist                    | unchanged                               |
| Git index                      | no staging before administrative checkpoint                                      | no unintended staged state              |
| Docker                         | no current-review Docker command                                                 | no container/network/volume side effect |
| Network / external services    | no current-review network probe or external request                              | no external side effect                 |
| CreativeDeploy                 | content never accessed                                                           | no side effect                          |

The only persistent intended side effect is the local Git audit checkpoint
containing audit tests and audit/governance documents.

## Third candidate boundary

**NOT VERIFIED.**

The planned boundary covered Runner result budget, Attempt, Lease, Grant,
Permit, inner result identity, and fixed-argv binding. Audit tests
`P5-AUD-004`–`P5-AUD-006` were drafted, but no behavior command was run.

Reason:

1. two blocking Medium Findings already made the focused Gate FAIL; and
2. the user explicitly directed the reviewer to stop expansion and record the
   third boundary as `NOT VERIFIED`.

Test quantity: `0 executed`.

Exit code: `NOT RUN`.

No Finding or PASS is inferred from source review or drafted tests.

## Checks intentionally not run

| Check                                                  | Status                 | Reason                                     |
| ------------------------------------------------------ | ---------------------- | ------------------------------------------ |
| third candidate API/PostgreSQL behavior tests          | NOT RUN / NOT VERIFIED | explicit stop after conclusive FAIL        |
| complete arbitrary-command API/database/runtime matrix | NOT RUN                | Gate already FAIL                          |
| canonical Workspace mutation/traversal matrix          | NOT RUN                | Gate already FAIL                          |
| real network/credential probes                         | NOT RUN                | Gate already FAIL                          |
| necessary Phase 4 regression set                       | NOT RUN                | no reopening after conclusive Phase 5 FAIL |
| migration roundtrip / real PostgreSQL suite            | NOT RUN                | stopped third boundary                     |
| Web unit/build                                         | NOT RUN                | cannot close focused Findings              |
| E2E / accessibility                                    | NOT RUN                | cannot close focused Findings              |
| Docker runtime / isolation                             | NOT RUN                | cannot close focused Findings              |
| Runner/Workspace smoke                                 | NOT RUN                | cannot close focused Findings              |
| Chaos                                                  | NOT RUN                | cannot close focused Findings              |
| broad Security / Eval                                  | NOT RUN                | cannot close focused Findings              |
| final `make verify`                                    | NOT RUN                | focused PASS prerequisite false            |
| PASS sealing commit                                    | NOT CREATED            | focused and final Gates did not pass       |
| remote CI / deployment / Customer 0                    | NOT VERIFIED / NOT RUN | outside authorization                      |

## CreativeDeploy and Docker ledger

Current review:

- CreativeDeploy content access: `NO`;
- parent/sibling filesystem discovery: `NO`;
- unfiltered global Docker diagnostic: `NO`;
- Docker inspect/logs/exec: `NO`;
- Docker start/stop/remove: `NO`.

Preserved historical implementation-era boundary events:

1. `find ..` exposed only a sibling path name;
2. an unfiltered Docker inventory exposed only a CreativeDeploy container
   name/status.

This review did not repeat either event and did not inspect the referenced
content or container.

## CONFIRMED / INFERRED / NOT VERIFIED

### CONFIRMED

- Main/candidate identity, parent, ancestry, and single-commit candidate range.
- Clean candidate starting state and independent audit branch origin.
- Four Protocol negative-input cases pass.
- Two blocking Medium production-path Findings are stable `3/3`.
- Exact audit-owned cleanup completed for the two Findings.
- No production code was edited.
- No current-review Docker command, CreativeDeploy content access, remote,
  push, merge, PR, or tag.

### INFERRED

- Resource-window and operator-recovery impacts described in the audit report
  follow from the confirmed local behaviors. Fleet/customer impact was not
  tested.

### NOT VERIFIED

- The stopped third boundary and all intentionally unexecuted checks in the
  table above.
- Remote CI, deployment, production, customer repository, or hostile
  multi-tenant behavior.

## Decision

```text
PHASE 5 FOCUSED SECURITY REVIEW FAIL — REMEDIATION REQUIRED
```
