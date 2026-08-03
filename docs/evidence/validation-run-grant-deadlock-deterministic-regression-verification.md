# Validation Run Grant Deadlock Deterministic Regression Verification

- Date: 2026-08-04 +0800
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/validation-run-grant-deadlock`
- Red product baseline: `c310dab795d01a29c2ca8c5fe4aaeaeb8179bd4a`
- Green product candidate: `31c7149d20c8c20fdd5107d9f19caaf0a83dd058`
- Draft PR: `#15`, base `fix/ci-e2e-post-gate`, head
  `fix/validation-run-grant-deadlock`
- Database: `[REDACTED_LOCAL_TEST_DATABASE]`
- Outcome: `LOCAL DETERMINISTIC REGRESSION GATE PASS — REMOTE CI PENDING`

## Scope and source identity

This verification adds only a focused PostgreSQL regression test and this
evidence record. It does not change the production service or repository.

The exact same test bytes were executed against both product versions:

- Test: `apps/api/tests/test_validation_run_grant_deadlock_regression.py`
- SHA-256: `702e6810293ee193e0b6ae3bcb5cd099c7f9e4f974b4c3cd396647044f911f66`
- Baseline copy comparison: byte-for-byte identical before the formal matrix
- PostgreSQL source: the repository's existing dedicated local test database
  configuration
- Timing control: bounded `threading.Event` barriers and observed PostgreSQL
  lock state; no `time.sleep`, randomized delay, or retry

The regression also orders the final Suite-step verification explicitly by
`ValidationSuiteStepRun.sequence`; it does not rely on PostgreSQL's unspecified
row-return order.

## Transaction diagnosis

The test records a structured trace containing transaction IDs, backend PIDs,
visibility at the Runner return seam, the competition stage, blockers,
PostgreSQL wait events, worker outcomes, and SQLSTATE.

On the Red baseline, the nested Runner helper commits before the child binding
is complete. An independent observer therefore sees both the child Validation
Run and Runner Job. The replay transaction reaches the child row competition;
the observed waiter reports a `transactionid` lock against the winner backend,
and PostgreSQL resolves the resulting cycle with SQLSTATE `40P01`.

On the Green candidate, Runner creation remains within the outer Validation
transaction (`commit=false`). The independent observer sees neither child nor
job. The replay transaction waits on the atomic outer transaction before it
can enter the partially bound-child window. Both calls complete with one Suite,
one child, one job, two ordered Suite steps, and zero unbound children.

## Formal Red matrix

Every Red invocation exited `1` because the regression observed a real
PostgreSQL deadlock (`DeadlockDetected`, SQLSTATE `40P01`).

| Run | Winner PID / XID | Runner-return XID | Loser PID / XID | Visible child/job | Competition  | Waiter -> blocker | Wait event    | Result    |
| --: | ---------------- | ----------------- | --------------- | ----------------- | ------------ | ----------------- | ------------- | --------- |
|   1 | 11083 / 8154     | 8156              | 11084 / 8157    | true / true       | child select | 11084 -> 11083    | transactionid | 40P01 Red |
|   2 | 11095 / 8179     | 8181              | 11096 / 8182    | true / true       | child select | 11096 -> 11095    | transactionid | 40P01 Red |
|   3 | 11107 / 8202     | 8204              | 11108 / 8205    | true / true       | child select | 11108 -> 11107    | transactionid | 40P01 Red |
|   4 | 11119 / 8227     | 8229              | 11120 / 8230    | true / true       | child select | 11120 -> 11119    | transactionid | 40P01 Red |
|   5 | 11131 / 8252     | 8254              | 11132 / 8255    | true / true       | child select | 11132 -> 11131    | transactionid | 40P01 Red |
|   6 | 11144 / 8275     | 8277              | 11145 / 8278    | true / true       | child select | 11145 -> 11144    | transactionid | 40P01 Red |
|   7 | 11163 / 8300     | 8302              | 11164 / 8303    | true / true       | child select | 11164 -> 11163    | transactionid | 40P01 Red |
|   8 | 11175 / 8325     | 8327              | 11176 / 8328    | true / true       | child select | 11176 -> 11175    | transactionid | 40P01 Red |
|   9 | 11187 / 8350     | 8352              | 11188 / 8353    | true / true       | child select | 11188 -> 11187    | transactionid | 40P01 Red |
|  10 | 11199 / 8375     | 8377              | 11200 / 8378    | true / true       | child select | 11200 -> 11199    | transactionid | 40P01 Red |

Red result: `10/10 deterministic expected failures`.

## Formal Green matrix

Every Green invocation exited `0`, returned the same Suite to both callers,
and recorded no database exception or deadlock.

| Run | Winner PID / XID | Runner-return XID | Loser PID / XID | Visible child/job | Competition       | Waiter -> blocker | Wait event    | Result |
| --: | ---------------- | ----------------- | --------------- | ----------------- | ----------------- | ----------------- | ------------- | ------ |
|   1 | 11254 / 8398     | 8399              | 11255 / 8400    | false / false     | outer transaction | 11255 -> 11254    | transactionid | Green  |
|   2 | 11266 / 8422     | 8423              | 11267 / 8424    | false / false     | outer transaction | 11267 -> 11266    | transactionid | Green  |
|   3 | 11271 / 8446     | 8447              | 11272 / 8448    | false / false     | outer transaction | 11272 -> 11271    | transactionid | Green  |
|   4 | 11283 / 8470     | 8471              | 11284 / 8472    | false / false     | outer transaction | 11284 -> 11283    | transactionid | Green  |
|   5 | 11288 / 8494     | 8495              | 11289 / 8496    | false / false     | outer transaction | 11289 -> 11288    | transactionid | Green  |
|   6 | 11300 / 8518     | 8519              | 11301 / 8520    | false / false     | outer transaction | 11301 -> 11300    | transactionid | Green  |
|   7 | 11310 / 8542     | 8543              | 11312 / 8544    | false / false     | outer transaction | 11312 -> 11310    | transactionid | Green  |
|   8 | 11316 / 8566     | 8567              | 11317 / 8568    | false / false     | outer transaction | 11317 -> 11316    | transactionid | Green  |
|   9 | 11328 / 8590     | 8591              | 11329 / 8592    | false / false     | outer transaction | 11329 -> 11328    | transactionid | Green  |
|  10 | 11333 / 8614     | 8615              | 11334 / 8616    | false / false     | outer transaction | 11334 -> 11333    | transactionid | Green  |

Green result: `10/10 deterministic passes`.

## Verification ledger

| Gate                                          |            Exit | Result                                 |
| --------------------------------------------- | --------------: | -------------------------------------- |
| Ruff format check, focused regression file    |               0 | already formatted                      |
| Ruff lint, focused regression file            |               0 | all checks passed                      |
| `make typecheck-api`                          |               0 | 132 source files passed                |
| Red baseline formal matrix                    | expected 1 each | 10/10 real PostgreSQL `40P01` failures |
| Green candidate formal matrix                 |          0 each | 10/10 passes; no database exception    |
| Targeted regression + Suite remediation tests |               0 | 12 passed, 1 warning                   |
| `make test-api-direct`                        |               0 | 356 passed, 1 warning; 84.44% coverage |

## First remote attempt and focused correction

Commit `4631ccd02c7bd0642e72f6468612b356f5702087` triggered the first stacked
CI attempt:

- Six jobs passed.
- Fast Python failed at `make typecheck-api` with five nullable-value errors in
  the new regression test. The focused correction adds only two explicit
  non-null assertions; final local `make typecheck-api` passes all 132 files.
- Heavy Playwright/Workspace Chaos failed because the pre-existing Web E2E
  locator for the `Read text` button resolved to two elements. Neither the
  focused correction nor this candidate changes Web or E2E product code.

The final Red/Green matrices and every local ledger entry above were rerun after
the focused type correction, using the final test hash recorded in this file.

## Publication and cleanup state

- PR #15 remains Draft.
- PR #14 was not modified.
- No merge, mark-ready, tag, deployment, or `main` movement was performed.
- Remote stacked Fast/Heavy CI is pending the focused commit and ordinary push.
- Temporary baseline worktree and raw local logs must be removed after the
  evidence has been reviewed and the commit is created; they are not candidate
  artifacts.
