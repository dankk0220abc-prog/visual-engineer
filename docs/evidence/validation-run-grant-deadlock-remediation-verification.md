# Validation Run Grant Deadlock Remediation Verification

- Date: 2026-08-03 +0800
- Baseline: `c310dab795d01a29c2ca8c5fe4aaeaeb8179bd4a`
- Branch: `fix/validation-run-grant-deadlock`
- Candidate: required branch tip (commit recorded in the Draft PR)
- Outcome: `LOCAL PASS — PUBLICATION PENDING`

## Evidence classification

### CONFIRMED

- Repository root, `main`, `HEAD`, and `origin/main` matched the required
  baseline; the worktree/index/untracked inventory was clean and no
  merge/rebase/cherry-pick state existed.
- Draft PR #14 remains open at
  `df68becd7474c8fbc7fd6401abd59560677ece1c`; its only changed path is
  `scripts/run-e2e.sh`.
- Fast CI run `30825107370` failed job `91724618472` in
  `make test-api-direct`; the result was 350 passed / 1 failed.
- The failed test was
  `test_concurrent_suite_create_consumes_one_grant_exactly_once[True]`.
- PostgreSQL deadlock detail:
  - process 780 waits for `ShareLock` on transaction 4573, blocked by 779;
  - process 779 waits for `ShareLock` on transaction 4572, blocked by 780;
  - relation `validation_runs`, tuple `(0,1)`;
  - process 780 current SQL: child idempotency `SELECT ... FOR UPDATE`;
  - process 779 current SQL: `UPDATE validation_runs SET version = ...`.
- Raw job log: `/tmp/visualengineer-validation-deadlock-job.log`, 143,697
  bytes, SHA-256
  `57ebdf84350a3116c5f3bad577d2182fe52fc70884f9acf96834d97fd2a80290`.
- SQLAlchemy Session defaults in this repository are `autoflush=True` and
  `expire_on_commit=True`. No relationship mapping or Session event hook was
  found in the API source/tests.
- A single local exact test passed functionally, and 20 additional baseline
  iterations passed with `--no-cov`. This confirms the failure is intermittent;
  it does not clear the CI deadlock.
- The repair makes Runner Job creation non-committing in
  `ValidationService.create()`, explicitly flushes the fully bound child, and
  publishes Validation Run, fixed step, Permission Envelope, Runner Job/event,
  and final Runner binding in one commit.
- Suite dispatch now explicitly flushes its state before the child query and
  rolls back a failed child dispatch before recording the durable
  `recovery_required` outcome.
- The deterministic PostgreSQL regression synchronizes both Sessions directly
  before the exact Grant `FOR UPDATE` and orders each worker as the first lock
  holder in turn. Same-key replay, different-key denial, rollback injection,
  and disjoint-Grant progress all passed.
- The repaired exact same-key node passed 30/30 iterations without a deadlock.
- Related Suite, authorization, lifecycle, and PostgreSQL-direct subsets passed
  36/36 and 40/40 tests.
- The one authorized final `make test-api-direct` invocation passed all 355
  tests with 84.44% total coverage; the aggregate was not rerun.
- The dedicated `test-db` container used for verification was stopped and
  removed; its PostgreSQL data lived only on the service tmpfs.
- Ruff format/lint, mypy, source invariance, and `git diff --check` passed.

### INFERRED FROM CONFIRMED SQL AND SOURCE ORDER

The CI victim stack is the losing Suite-create request after the post-Grant
idempotency recheck. It enters `_sync()`, finds no active bound Suite step,
and calls `_dispatch_next()`. The concurrent winning dispatch has already
crossed the nested Runner commit and is updating the partially visible child
Validation Run. The loser holds the fixed Grant/Suite dispatch context and
tries to lock that child by its deterministic idempotency key. PostgreSQL
detects the transaction-ID wait cycle on the child tuple.

The enabling defect is not missing uniqueness and is not PR #14's shell diff.
It is the nested `RunnerService.create_workspace_job(commit=True)` inside a
larger Validation creation transaction. That commit splits child creation
from its Runner binding and permits the replay path to observe/lock the
intermediate row.

### NOT YET VERIFIED

- Remote Draft PR Fast/Heavy CI.

## Pre-repair lock graph

```text
Transaction A — winning first-child dispatch
  exact Grant/Checkpoint/Workspace/Handle FOR UPDATE
    -> Suite row FOR UPDATE
    -> ordered Suite-step rows FOR UPDATE
    -> INSERT child ValidationRun/ValidationStep
    -> Runner helper COMMIT (prematurely releases outer locks and exposes child)
    -> UPDATE exposed child ValidationRun binding/version
    -> wait on transaction B

Transaction B — exact Suite replay / duplicate dispatch
  exact Grant/Checkpoint/Workspace/Handle FOR UPDATE
    -> Suite row FOR UPDATE
    -> ordered Suite-step rows FOR UPDATE
    -> SELECT exposed child ValidationRun by deterministic idempotency FOR UPDATE
    -> wait on transaction A
```

The CI log confirms the final two waiting SQL statements and both transaction
IDs. Earlier held-lock edges are reconstructed from the victim stack and the
source-level transaction sequence and will be exercised by the deterministic
barrier regression.

## Intended post-repair order

```text
Grant -> Suite -> ordered Suite steps
  -> child ValidationRun + fixed step + Envelope + Runner Job
  -> final child Runner binding
  -> one Validation-service commit
  -> Suite-step child binding
```

A concurrent request blocks at the exact Grant row and cannot observe a
partially bound child. Exact replay returns the one Suite; a different key
gets `validation_suite_grant_already_consumed`.

## Migration and external-boundary statement

- Migration: `NO` (confirmed by final diff review).
- Provider/API key: not connected or changed.
- License/tag/deploy: not changed or performed.
- PR #14: not modified, closed, merged, or force-pushed.

## Verification ledger

| Command                                                    | Exit | Result                                                                                |
| ---------------------------------------------------------- | ---: | ------------------------------------------------------------------------------------- |
| exact baseline test (repository coverage enabled)          |    1 | test passed; global 80% coverage gate failed as expected for one selected test        |
| exact baseline test, 20 iterations, `--no-cov`             |    0 | 20/20 functionally passed; intermittent CI failure retained as authoritative evidence |
| remediation regression file, `--no-cov`                    |    0 | 11 passed, including ordered same/different-key races, rollback, and disjoint Grants  |
| repaired exact same-key test, 30 iterations, `--no-cov`    |    0 | 30/30 passed without deadlock                                                         |
| related Suite/authorization/lifecycle subset, `--no-cov`   |    0 | 36 passed                                                                             |
| related shared Validation/control-plane subset, `--no-cov` |    0 | 40 passed                                                                             |
| `make format-check-api`                                    |    0 | 168 files already formatted                                                           |
| `make lint-api`                                            |    0 | all checks passed                                                                     |
| `make typecheck-api`                                       |    0 | 131 source files passed                                                               |
| `make source-invariance-check`                             |    0 | PASS; 119 entries and 10 Git objects compared                                         |
| `git diff --check`                                         |    0 | no whitespace errors                                                                  |
| `make test-api-direct` (single final invocation)           |    0 | 355 passed; 84.44% coverage; no deadlock                                              |
