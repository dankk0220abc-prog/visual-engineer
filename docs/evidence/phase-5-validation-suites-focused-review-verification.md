# Phase 5 Governed Validation Suites Focused Review Evidence

- Date: 2026-07-30 (Asia/Shanghai)
- Main: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Candidate: `10399722e37f3209fa08e5e7edc25f31b429aaad`
- Audit branch: `audit/phase-5-validation-suites-focused-max`
- Status: COMPLETE — FOCUSED SECURITY REVIEW FAIL
- Coverage: not collected for focused `--no-cov` runs
- Final aggregate: NOT RUN; exit N/A

## Evidence boundary

This independent evidence covers only the second Phase 5 governed multi-step
Validation Suite slice. Candidate implementation evidence was read to locate
controls; it does not award an independent PASS.

No production source, migration, Protocol, Web, Compose, infrastructure,
script, generated contract, or `Makefile` content was changed. Writes are
limited to one independent test, focused review/governance documents, evidence,
and status.

## Git baseline ledger

Preflight ran at the exact repository root before the audit branch was created.

| Check                                                   | Exit | Confirmed result                           |
| ------------------------------------------------------- | ---: | ------------------------------------------ |
| `pwd`                                                   |    0 | `/Users/danke/Developer/VisualEngineer`    |
| `git rev-parse --show-toplevel`                         |    0 | exact repository root                      |
| original `git branch --show-current`                    |    0 | `feat/phase-5-governed-validation-suites`  |
| original `git rev-parse HEAD`                           |    0 | exact candidate                            |
| `git rev-parse main`                                    |    0 | exact baseline                             |
| status, unstaged diff, staged diff, untracked inventory |    0 | all clean/empty                            |
| remote, stash, tag inventory                            |    0 | empty                                      |
| worktree inventory                                      |    0 | one exact VisualEngineer worktree          |
| local refs and graph inspection                         |    0 | disclosed history; no hidden candidate ref |
| `git cat-file -t` for main and candidate                |    0 | both `commit`                              |
| candidate parent inspection                             |    0 | parent is exactly main                     |
| `git rev-list --count main..candidate`                  |    0 | `1`                                        |
| `git merge-base --is-ancestor main candidate`           |    0 | exact ancestry                             |
| `git diff --check main..candidate`                      |    0 | no whitespace error                        |
| `.git` lock, replace, notes, special-ref inspection     |    0 | none                                       |

Candidate change summary:

```text
58 files changed, 9192 insertions(+), 1589 deletions(-)
candidate tree: 45a4d666eafd6a4e17bddfaef05cafaa67715d59
```

Branch creation:

```text
git switch -c audit/phase-5-validation-suites-focused-max \
  10399722e37f3209fa08e5e7edc25f31b429aaad
```

Exit: `0`. No branch was overwritten.

`git fsck --no-reflogs --unreachable` exited `0` and disclosed seven
historical unreachable commits plus related trees/blobs. No ref points to
them, none is part of the candidate history, and the review did not delete or
otherwise alter them.

```text
286300ca4ef79f5dc10c8d133dcebc172c9c6fb3
b3e3138f99183b4fc2d8a63e28f226631dffb56d
73b5a6b384bc658273e85ba082e4ad4ba39b4792
a8a5061b69e762d7f3cec8338a6d486488a017f2
50d6feebb79fa8d4d43834af0d6516705b2877f9
2bd929033705f0a15ec1b668f9cd21e38c434bf8
f8bd4190d79dca8989fc59f534fef503cb469021
```

## Frozen production boundary

Frozen paths:

```text
apps/api/src
apps/api/alembic/versions
apps/api/Dockerfile
apps/runner/src
apps/runner/Dockerfile
apps/web/src
apps/web/Dockerfile
packages/runner-protocol/src
packages/api-contract
compose.yaml
infra
scripts
Makefile
```

Candidate inventory:

```text
tracked entries: 159
git ls-tree SHA-256:
7df6b3b54aceb945c3f2bbb9c6a33c93060aa3b4f58237a2f8badfab286d432d
```

The pre-checkpoint comparison:

```text
git diff --exit-code \
  10399722e37f3209fa08e5e7edc25f31b429aaad \
  -- <frozen production paths>
```

Exit: `0`.

## Static review ledger

The independent review read the required governance and implementation
surface, including:

- `AGENTS.md`, `PLANS.md`, `README.md`, `SECURITY.md`, and `Makefile`;
- Phase 5 Suite plan and implementer evidence;
- ADR 0017 and the Suite runbook;
- data model, runner protocol, state machine, and permissions architecture;
- Suite catalog, migration, models, schemas, routes, repository, service, API
  contract, Runner/worker integration, Web console, and current Suite tests.

Static evidence consistent with `VE-P5-SUITES-FR-001`:

- `WorkspaceService` grants
  `max_attempts * len(suite.steps)` child Validation Runs;
- `ValidationSuiteService.create` checks global idempotency replay and Grant
  validity but does not reject an existing root Suite for the same Grant;
- `ValidationSuiteRun` has no one-root-Suite-per-Grant uniqueness constraint;
  and
- the Web starts each Suite with a new random idempotency key.

Static evidence consistent with `VE-P5-SUITES-FR-002`:

- the step trigger protects immutable definition fields and terminal rows but
  has no legal nonterminal state-transition matrix;
- synchronization finalizes success when every persisted step state is
  `succeeded`; and
- finalization includes Evidence only when optional `evidence_id` is present
  and does not require/reconstruct exact current-run Evidence for each
  successful step.

These root-cause statements are static inferences. The Findings themselves are
based on the dynamic results below.

## Independent audit test inventory

| Test                                                                          | Secure expectation                                                           | Status                                    |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------- |
| `test_p5_suites_aud_001_same_grant_cannot_create_a_second_suite_attempt`      | A Suite Grant is single-root-attempt authority; a retry needs a fresh Grant. | FAIL, stable `3/3`; `VE-P5-SUITES-FR-001` |
| `test_p5_suites_aud_002_missing_evidence_cannot_be_promoted_to_suite_success` | Persisted summaries cannot replace ordered exact Evidence.                   | FAIL, stable `3/3`; `VE-P5-SUITES-FR-002` |

Both remain ordinary failing assertions. Neither is skipped, weakened, marked
`xfail`, nor converted to expected-failure metadata.

## Isolated PostgreSQL setup

The review started only this exact Compose project:

```text
project: ve-p5-suites-focused-audit
service: test-db
published PostgreSQL port: 35633
```

Startup command:

```text
TEST_POSTGRES_PUBLISHED_PORT=35633 \
docker compose -p ve-p5-suites-focused-audit \
  --profile test up -d --wait test-db
```

Exit: `0`.

No unfiltered Docker inventory, global logs, global inspect, or unknown-resource
cleanup was performed.

## First focused behavior run

Command, with the local test credential redacted from this evidence:

```text
TEST_DATABASE_URL=<review-owned PostgreSQL on 127.0.0.1:35633> \
uv run pytest \
  apps/api/tests/test_phase5_validation_suites_focused_review.py \
  --no-cov -q
```

Exit: `1`.

Summary:

```text
2 failed, 1 warning in 0.79s
```

The fixture upgraded the clean review database through head, including
`20260730_0008`.

First observed assertion values:

```text
P5-SUITES-AUD-001:
same Grant created another Suite attempt: (201, 1, 2, 1, 2)

P5-SUITES-AUD-002:
missing Evidence was accepted as successful aggregate proof:
(200, "succeeded", "succeeded", 0)
```

Both failures reached candidate API/database production paths. Neither was a
test harness exception.

## Stability rerun ledger

Each failure was independently selected twice more with the same candidate and
unchanged test.

| Selection    | Run | Exit |                  Count | Result               |
| ------------ | --: | ---: | ---------------------: | -------------------- |
| `-k aud_001` |   2 |    1 | 1 failed, 1 deselected | same tuple/assertion |
| `-k aud_001` |   3 |    1 | 1 failed, 1 deselected | same tuple/assertion |
| `-k aud_002` |   2 |    1 | 1 failed, 1 deselected | same tuple/assertion |
| `-k aud_002` |   3 |    1 | 1 failed, 1 deselected | same tuple/assertion |

Stable totals:

```text
VE-P5-SUITES-FR-001: 3 failures / 3 runs; exit 1 each
VE-P5-SUITES-FR-002: 3 failures / 3 runs; exit 1 each
```

## Candidate control selection

The unchanged candidate Suite test file was run as the minimal control:

```text
TEST_DATABASE_URL=<review-owned PostgreSQL on 127.0.0.1:35633> \
uv run pytest apps/api/tests/test_phase5_validation_suites.py --no-cov -q
```

Exit: `0`.

Summary:

```text
10 passed, 1 warning in 2.99s
```

This confirms that the candidate's expected Suite paths still pass on the same
real PostgreSQL environment. It does not close the independent Findings or
establish a broad Security Gate PASS.

## Finding evidence matrix

| Finding               | Trigger                                                                                         | Expected                                                                     | Actual                                                                             | Severity        | Test quantity | Exit     | Evidence location                    |
| --------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------- | ------------: | -------- | ------------------------------------ |
| `VE-P5-SUITES-FR-001` | Same approved Suite Grant, same Suite definition, fresh idempotency key.                        | Typed denial and unchanged Suite/child counts; retry requires a fresh Grant. | HTTP `201`; counts change from one to two for both Suite and child Validation Run. | blocking Medium |  `3/3` stable | `1` each | preserved audit test and this ledger |
| `VE-P5-SUITES-FR-002` | Mark both pre-execution steps successful without Evidence, then synchronize through detail API. | Database or Control Plane rejects success.                                   | HTTP `200`; Suite/Result `succeeded`; zero Evidence references.                    | blocking Medium |  `3/3` stable | `1` each | preserved audit test and this ledger |

No persistent audit-owned database side effect remains because each test uses
transactional fixtures and the exact Compose project was removed.

## Focused static quality check

The independent test was formatted and linted:

```text
uv run ruff format \
  apps/api/tests/test_phase5_validation_suites_focused_review.py

uv run ruff check \
  apps/api/tests/test_phase5_validation_suites_focused_review.py
```

Both exit `0`.

No production file was included.

## Exact cleanup ledger

Cleanup command:

```text
TEST_POSTGRES_PUBLISHED_PORT=35633 \
docker compose -p ve-p5-suites-focused-audit \
  --profile test down -v --remove-orphans
```

Exit: `0`.

Post-cleanup checks used only the exact Compose project label:

| Inventory  | Exit | Result |
| ---------- | ---: | ------ |
| containers |    0 | empty  |
| networks   |    0 | empty  |
| volumes    |    0 | empty  |

No other Docker resource or host process was modified.

## Stop-condition ledger

After the two blockers were stable, the following were deliberately not run:

- `make verify`;
- complete Python/API/Runner/Protocol/Web test and coverage gates;
- Web build, browser/E2E, and accessibility;
- full migration base/head/base/head roundtrip;
- broad Docker isolation;
- Chaos, broad Security, and Eval;
- complete historical Phase 5 first-slice and Phase 4 regressions; and
- full runtime source/canonical Workspace invariance.

Final aggregate status: `NOT RUN`; exit code: `N/A`.

## Pre-checkpoint governance checks

The pre-checkpoint review confirms:

- exactly six allowed audit test/evidence/governance/status paths;
- focused Ruff and document formatting exit `0`;
- `git diff --check` exits `0`;
- the candidate production-path diff is empty;
- the production inventory remains 159 entries with digest
  `7df6b3b54aceb945c3f2bbb9c6a33c93060aa3b4f58237a2f8badfab286d432d`;
- main remains `f547091307c52df8f20fc69bac4b4826cbbc74ad`; and
- exact filtered review-owned container/network/volume inventories are empty.

The checkpoint cannot embed its own final object ID. Its exact hash and final
clean worktree state are reported in the post-commit administrative handoff.
