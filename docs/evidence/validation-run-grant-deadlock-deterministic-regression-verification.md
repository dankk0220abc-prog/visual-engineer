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
- SHA-256: `87054e14a144eab676a4000a6dcc0a1997a2e07e9f1e2f1862a246d39805e5af`
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
|   1 | 8134 / 2178      | 2180              | 8135 / 2181     | true / true       | child select | 8135 -> 8134      | transactionid | 40P01 Red |
|   2 | 8152 / 2203      | 2205              | 8153 / 2206     | true / true       | child select | 8153 -> 8152      | transactionid | 40P01 Red |
|   3 | 8164 / 2228      | 2230              | 8165 / 2231     | true / true       | child select | 8165 -> 8164      | transactionid | 40P01 Red |
|   4 | 8176 / 2253      | 2255              | 8177 / 2256     | true / true       | child select | 8177 -> 8176      | transactionid | 40P01 Red |
|   5 | 8188 / 2278      | 2280              | 8189 / 2281     | true / true       | child select | 8189 -> 8188      | transactionid | 40P01 Red |
|   6 | 8200 / 2303      | 2305              | 8201 / 2306     | true / true       | child select | 8201 -> 8200      | transactionid | 40P01 Red |
|   7 | 8212 / 2326      | 2328              | 8213 / 2329     | true / true       | child select | 8213 -> 8212      | transactionid | 40P01 Red |
|   8 | 8224 / 2351      | 2353              | 8225 / 2354     | true / true       | child select | 8225 -> 8224      | transactionid | 40P01 Red |
|   9 | 8237 / 2376      | 2378              | 8238 / 2379     | true / true       | child select | 8238 -> 8237      | transactionid | 40P01 Red |
|  10 | 8249 / 2399      | 2401              | 8250 / 2402     | true / true       | child select | 8250 -> 8249      | transactionid | 40P01 Red |

Red result: `10/10 deterministic expected failures`.

## Formal Green matrix

Every Green invocation exited `0`, returned the same Suite to both callers,
and recorded no database exception or deadlock.

| Run | Winner PID / XID | Runner-return XID | Loser PID / XID | Visible child/job | Competition       | Waiter -> blocker | Wait event    | Result |
| --: | ---------------- | ----------------- | --------------- | ----------------- | ----------------- | ----------------- | ------------- | ------ |
|   1 | 8288 / 2424      | 2425              | 8289 / 2426     | false / false     | outer transaction | 8289 -> 8288      | transactionid | Green  |
|   2 | 8300 / 2448      | 2449              | 8301 / 2450     | false / false     | outer transaction | 8301 -> 8300      | transactionid | Green  |
|   3 | 8305 / 2472      | 2473              | 8306 / 2474     | false / false     | outer transaction | 8306 -> 8305      | transactionid | Green  |
|   4 | 8317 / 2496      | 2497              | 8318 / 2498     | false / false     | outer transaction | 8318 -> 8317      | transactionid | Green  |
|   5 | 8322 / 2520      | 2521              | 8323 / 2522     | false / false     | outer transaction | 8323 -> 8322      | transactionid | Green  |
|   6 | 8334 / 2544      | 2545              | 8335 / 2546     | false / false     | outer transaction | 8335 -> 8334      | transactionid | Green  |
|   7 | 8347 / 2568      | 2569              | 8348 / 2570     | false / false     | outer transaction | 8348 -> 8347      | transactionid | Green  |
|   8 | 8352 / 2592      | 2593              | 8353 / 2594     | false / false     | outer transaction | 8353 -> 8352      | transactionid | Green  |
|   9 | 8364 / 2616      | 2617              | 8365 / 2618     | false / false     | outer transaction | 8365 -> 8364      | transactionid | Green  |
|  10 | 8369 / 2640      | 2641              | 8370 / 2642     | false / false     | outer transaction | 8370 -> 8369      | transactionid | Green  |

Green result: `10/10 deterministic passes`.

## Verification ledger

| Gate                                          |            Exit | Result                                 |
| --------------------------------------------- | --------------: | -------------------------------------- |
| Ruff format check, focused regression file    |               0 | already formatted                      |
| Ruff lint, focused regression file            |               0 | all checks passed                      |
| Red baseline formal matrix                    | expected 1 each | 10/10 real PostgreSQL `40P01` failures |
| Green candidate formal matrix                 |          0 each | 10/10 passes; no database exception    |
| Targeted regression + Suite remediation tests |               0 | 12 passed, 1 warning                   |
| `make test-api-direct`                        |               0 | 356 passed, 1 warning; 84.44% coverage |

## Publication and cleanup state

- PR #15 remains Draft.
- PR #14 was not modified.
- No merge, mark-ready, tag, deployment, or `main` movement was performed.
- Remote stacked Fast/Heavy CI is pending the focused commit and ordinary push.
- Temporary baseline worktree and raw local logs must be removed after the
  evidence has been reviewed and the commit is created; they are not candidate
  artifacts.
