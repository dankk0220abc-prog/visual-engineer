# Phase 5 Validation Suites Focused Re-Audit Verification

- Date: 2026-07-30 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `audit/phase-5-validation-suites-reaudit-max`
- Main baseline: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Original focused-review FAIL checkpoint:
  `d325fa197e1fdad2c522fdf76f11b738682a86ca`
- Remediation candidate:
  `b6d53ba0275933e18919ceb2d90152e5ae8efcac`
- Status: `COMPLETE — PASS`
- FR-001: `PASS`
- FR-002: `PASS`
- Required budget/race/cleanup: `PASS`
- Final complete aggregate: `PASS`, exit `0`
- Remote CI: `NOT VERIFIED`

## Evidence boundary

This evidence decides only:

1. `VE-P5-SUITES-FR-001` — Suite Grant single-root lineage, idempotency,
   fresh-Grant retry, and concurrent consumption;
2. `VE-P5-SUITES-FR-002` — trusted execution chain and complete,
   catalog-ordered Evidence for successful aggregation; and
3. the explicitly stopped combined-output, cancellation, retry-race,
   cleanup-recovery, and source/canonical-invariance boundaries.

The review does not reopen Phase 4, the sealed Phase 5 first slice, the entire
Suite architecture, Customer 0, another Phase 5 slice, or Phase 6.

## Git preflight

| Check                                  | Exit | Confirmed result                              |
| -------------------------------------- | ---: | --------------------------------------------- |
| `pwd`                                  |    0 | exact Developer repository                    |
| `git rev-parse --show-toplevel`        |    0 | exact authorized root                         |
| initial branch                         |    0 | `fix/phase-5-validation-suites-remediation-1` |
| initial `HEAD`                         |    0 | exact candidate `b6d53ba...`                  |
| `git rev-parse main`                   |    0 | exact `f547091...`                            |
| status/diff/index/untracked            |    0 | clean                                         |
| remote/stash/tag                       |    0 | empty                                         |
| worktrees                              |    0 | one                                           |
| Git lock scan                          |    0 | none                                          |
| candidate/checkpoint object type       |    0 | both `commit`                                 |
| candidate parent                       |    0 | exact `d325fa1...`                            |
| ancestor check                         |    0 | true                                          |
| checkpoint-to-candidate count          |    0 | exactly one commit                            |
| candidate subject                      |    0 | exact declared remediation subject            |
| candidate `git diff --check`           |    0 | no whitespace error                           |
| target audit branch existence          |    1 | absent as required                            |
| original audit test blob comparison    |    0 | byte-identical                                |
| skip/xfail scan in original audit test |    1 | no marker                                     |

The audit branch was created without force directly from the exact candidate.
The original focused test SHA-256 is:

```text
47d9623ce5aab2e0de18e14fc473970f828c312f2d27ad167574be72c0bb350d
```

The hash is identical at the original FAIL checkpoint, remediation candidate,
and audit worktree.

## Read and diff review

The following classes of material were read completely:

- historical focused report, evidence, ExecPlan, and unchanged tests;
- remediation ExecPlan, evidence, permanent regressions, and full one-commit
  diff;
- Suite Grant/Run/step/result/Evidence models, repositories, schemas, and
  service;
- Workspace Grant creation, retry authority, Runner Job lifecycle, Attempt,
  Lease, Permit, validation completion, and cleanup paths;
- Migration 0009 constraints and triggers;
- Suite state machine, API routes, runner protocol, Runner validation worker
  and executor;
- budget, cancellation, retry, race, cleanup, and invariance tests; and
- ADR 0017 and the validation Suite runbook.

The candidate diff adds Migration 0009 and closes the two focused Findings
through immutable lineage fields, uniqueness/transition/Evidence constraints,
Grant row locking and idempotency recheck, fresh retry authority, and
server-side reconstruction of catalog-ordered trusted Evidence.

No static blocker was found before behavior testing. This is supporting
evidence only; runtime and database results below determine the verdict.

## Real PostgreSQL environment

Focused Compose project:

`ve-p5-suites-reaudit-max`

Published PostgreSQL port:

`35730`

The exact project, port, containers, networks, and volumes were checked before
startup. No listener or pre-existing project resource existed. The repository
`test-db` service became healthy. All focused API selections used a redacted
URL of the form:

`postgresql+psycopg://visualengineer:<redacted>@127.0.0.1:35730/visualengineer_test`

No SQLite or mock persistence was used.

## Focused command ledger

| Selection / command                           | Exit | Result              |
| --------------------------------------------- | ---: | ------------------- |
| unchanged focused-review file                 |    0 | `2 passed`          |
| new independent re-audit file                 |    0 | `4 passed`          |
| original + new + remediation + Suite controls |    0 | `23 passed`         |
| focused Protocol/Runner selection             |    0 | `6 passed`          |
| fresh isolated `make migration-check`         |    0 | base/head/base/head |
| `make contracts-check`                        |    0 | no generated drift  |
| standalone `make source-invariance-check`     |    0 | PASS                |
| pre-aggregate production path comparison      |    0 | empty diff          |
| pre-aggregate `git diff --check`              |    0 | clean               |

The combined `23 passed` selection is:

```text
apps/api/tests/test_phase5_validation_suites_focused_review.py
apps/api/tests/test_phase5_validation_suites_focused_reaudit.py
apps/api/tests/test_phase5_validation_suites_remediation.py
apps/api/tests/test_phase5_validation_suites.py
```

The focused Protocol/Runner selection covers the closed immutable Suite
catalog, rejection of free command authority, and cancellation cleanup-failure
reporting.

## Independent audit tests

New file:

`apps/api/tests/test_phase5_validation_suites_focused_reaudit.py`

SHA-256:

`54876328bddf32f25a749082afd0464ed52ef4d268f13871253819e4fef0b4fd`

### Retry versus old completion race

Test:

`test_reaudit_retry_and_late_old_completion_race_preserves_one_lineage`

Trigger:

- cancel and acknowledge an active old child;
- approve a fresh retry Grant;
- release retry creation and the old child's completion concurrently from
  independent sessions; and
- replay the retry exactly.

Expected and actual:

| Boundary                   | Expected                            | Actual        |
| -------------------------- | ----------------------------------- | ------------- |
| retry lineage              | one attempt two under original root | one           |
| old completion             | rejected                            | `stale_lease` |
| old Evidence               | zero                                | zero          |
| old Permit completion      | zero                                | zero          |
| retry replay changes       | zero                                | zero          |
| duplicate execution/charge | zero                                | zero          |
| canonical Workspace        | unchanged                           | unchanged     |

### Foreign retry Grant

Test:

`test_reaudit_foreign_retry_grant_has_zero_success_side_effects`

An approved retry Grant belonging to another Suite root is rejected. Durable
Suite Run/step/Job/Attempt/Lease/Permit/Result/Evidence/event/charge counts and
the canonical Workspace remain unchanged.

### Coherent foreign ordered Evidence

Test:

`test_reaudit_coherent_foreign_ordered_evidence_cannot_authorize_result`

The supplied two-step Evidence chain is internally coherent and correctly
ordered but belongs entirely to another Suite execution. The target Suite
cannot create a succeeded Result or success event. It cannot complete a
Permit, create Evidence, charge budget, create execution identities, or mutate
the Workspace.

### Legal aggregate digest, replay, and terminal fence

Test:

`test_reaudit_trusted_aggregate_digest_terminal_fence_and_replay`

A legitimate two-step execution succeeds. The test independently recomputes
the aggregate digest from trusted persisted bindings and confirms exact root,
Suite/version/definition, revision/checkpoint, Grant, policy, budget, and
ordered Evidence references. Two exact result replays add no Result, Evidence,
event, or charge. Terminal step Evidence and terminal Suite result references
cannot be replaced.

## FR-001 matrix

| Boundary                          | Result                | Durable side effects on denial/replay |
| --------------------------------- | --------------------- | ------------------------------------- |
| same Grant + same idempotency key | original Suite Run    | none                                  |
| same Grant + different key        | denied                | none                                  |
| same Grant concurrent create      | at most one success   | no second lineage                     |
| stale/revoked/expired Grant       | denied                | none                                  |
| mismatched/foreign Grant          | denied                | none                                  |
| old Grant retry                   | denied                | none                                  |
| fresh retry Grant bindings        | exact                 | one legal attempt                     |
| retry vs late old completion      | old completion denied | no old Evidence/Permit completion     |
| exact retry replay                | idempotent            | none                                  |

Confirmed zero on every relevant rejection/replay: extra Suite Run, step,
Job, Attempt, Lease, Permit, Result, Evidence, event, charge, and canonical
Workspace change.

## FR-002 matrix

| Boundary                                 | Result          | Success-side effects |
| ---------------------------------------- | --------------- | -------------------- |
| succeeded step state without proof       | denied          | zero                 |
| zero Evidence references                 | denied          | zero                 |
| missing Evidence                         | denied          | zero                 |
| foreign Evidence                         | denied          | zero                 |
| duplicate Evidence                       | denied          | zero                 |
| reordered Evidence                       | denied          | zero                 |
| stale Evidence                           | denied          | zero                 |
| mismatched step key/index/Profile        | denied          | zero                 |
| mismatched Run/Job/Attempt/Lease/Grant   | denied          | zero                 |
| failed/timed_out/cancelled/recovery step | denied          | zero                 |
| legal two-step proof                     | succeeded       | one trusted Result   |
| aggregate digest                         | recomputed      | exact match          |
| terminal Evidence/Result replacement     | denied          | zero                 |
| exact aggregate replay                   | original Result | zero duplicates      |

For every denial, succeeded Suite Result, Suite success event, erroneous Permit
completion, new Evidence, duplicate charge, unexpected Job/Attempt/Lease, and
canonical Workspace mutation are zero.

## Required budget, race, and cleanup boundaries

| Boundary                                    | Result                                        |
| ------------------------------------------- | --------------------------------------------- |
| exact combined retained output 10,000 bytes | success                                       |
| combined retained output 10,001 bytes       | denied                                        |
| cancel before next dispatch                 | pending child never dispatched                |
| cancel wins after old child completion      | next child not dispatched                     |
| Suite timeout                               | active child cancelled before terminalization |
| step timeout                                | fail-fast terminalization                     |
| retry versus old completion                 | old completion fenced                         |
| cleanup failure                             | failed / `recovery_required`                  |
| process remains after cleanup               | failed / `recovery_required`                  |
| source repository                           | invariant                                     |
| canonical Workspace                         | invariant                                     |

No boundary was broadened beyond the task's enumerated list.

## Fresh migration and contracts

The database `visualengineer_reaudit_migration_0730` was confirmed absent,
created under the already-owned focused PostgreSQL project, and used only for
the fresh migration check:

```text
base -> 0001 -> 0002 -> 0003 -> 0004 -> 0005 -> 0006 -> 0007 -> 0008 -> 0009
0009 -> 0008 -> ... -> base
base -> ... -> 0009
exit 0
```

The exact database was dropped afterward and its absence was confirmed.
`make contracts-check` regenerated OpenAPI and TypeScript schema output and
left no diff.

## Local image identity

To avoid unrelated registry instability, the final aggregate reused local
completed-source images through the repository's `E2E_SKIP_BUILD=1` and
`CHAOS_SKIP_BUILD=1` controls.

Image IDs:

| Service      | Image ID                                                           |
| ------------ | ------------------------------------------------------------------ |
| E2E API      | `db981571b56e15d74ab47165e29eae727f9a25acdf09eb36e20a5953a2112b26` |
| E2E Web      | `95ccc73799eca5b09f8dfd278e6be287d4977d32f3d2fb4ca47c0d04433964be` |
| E2E Runner   | `a8d795195ad8802facb7c1265c0f065cca3fc29adda46c8b8923f7ee35a835d2` |
| Chaos API    | `79f4922630580e3f18bd110266568239355f0af66e21e7e6f0697377e777b0a8` |
| Chaos Runner | `db0e4d75b9e111ddd98c0d32ae2d2f69b87322e07a25086087d4b6d75b6c6126` |

Candidate and image source-tree checks:

```text
API + migrations + Protocol:
e62976f11b8478d748af44963674924c098dff1de86cd605b0ef293df42527c8
64 non-bytecode files, exact match

Runner + Protocol:
3407dc104bc58644868d74626cfe357fa07d6a637a68eeb034cc4b0de54db152
22 non-bytecode files, exact match
```

The Web runtime bundle contains
`http://127.0.0.1:38640`; final Playwright `16/16` independently exercises the
Web/API/Runner image set against that binding.

## Aggregate attempts and preserved failures

### Attempt 1 — audit document formatting

Command: final aggregate environment plus `make verify`.

Result: exit `2` at `format-check-web`.

First failure:

```text
docs/exec-plans/phase-5-validation-suites-focused-reaudit.md
Code style issues found
```

No test, migration, build, Docker, E2E, Chaos, Security, or Eval stage ran.
Prettier mechanically formatted only the new audit ExecPlan. Production files
remained unchanged.

### Attempt 2 — reused Web image port mismatch

The complete rerun passed contracts, format, lint, typecheck, Python `252`,
Web `47`, build, Docker config, migration, permanent controls, source
invariance, and Workspace repair. E2E then mapped API port `38741`, but the
reused Web bundle was compiled for `38640`.

One browser case failed and two timed out before the task-owned process was
interrupted. The aggregate exited `130` and the official trap cleaned the E2E
project. Bundle inspection then confirmed the exact mismatch. No production
file or configuration was edited.

### Final complete rerun — PASS

Preflight confirmed:

- new main project `ve-p5-suites-reaudit-final-rerun` absent;
- exact E2E and Chaos projects absent;
- ports `35743`, `35640`, `38640`, `39640`, `35641`, and `38641` free; and
- all five required local image tags present.

Environment:

```text
COMPOSE_PROJECT_NAME=ve-p5-suites-reaudit-final-rerun
TEST_POSTGRES_PUBLISHED_PORT=35743
E2E_COMPOSE_PROJECT_NAME=ve-p5-suites-reaudit-final-e2e
E2E_DB_PORT=35640
E2E_API_PORT=38640
E2E_WEB_PORT=39640
E2E_SKIP_BUILD=1
WORKSPACE_CHAOS_COMPOSE_PROJECT_NAME=ve-p5-suites-reaudit-final-chaos
WORKSPACE_CHAOS_DB_PORT=35641
WORKSPACE_CHAOS_API_PORT=38641
CHAOS_SKIP_BUILD=1
make verify
```

Result: exit `0`.

The extra invocations are a recorded deviation from the intended one-pass
aggregate. The final result is from a complete rerun of every target.

## Final aggregate ledger

| Stage                      | Exit | Result                                                             |
| -------------------------- | ---: | ------------------------------------------------------------------ |
| contracts                  |    0 | no drift                                                           |
| format                     |    0 | Ruff 128 files; Prettier matched                                   |
| lint                       |    0 | Ruff and ESLint                                                    |
| typecheck                  |    0 | mypy 97 files; TypeScript                                          |
| Python/API/Runner/Protocol |    0 | `252 passed`, `83.33%`                                             |
| Web unit                   |    0 | `47 passed`                                                        |
| Web coverage               |    0 | statements 71.04%, branches 68.15%, functions 70.71%, lines 72.75% |
| Next.js production build   |    0 | all routes built                                                   |
| Docker Compose config      |    0 | all configured variants                                            |
| Migration                  |    0 | base/head/base/head                                                |
| Phase 4 permanent controls |    0 | controls present; historical FAIL preserved                        |
| Runner security audit      |    0 | `22 passed`                                                        |
| source invariance          |    0 | PASS, 119 entries, 10 objects, 2 status, 0 markers                 |
| Workspace repair           |    0 | `86 passed` plus `14 passed`                                       |
| Playwright E2E             |    0 | `16 passed`                                                        |
| Workspace Chaos            |    0 | atomic/revoke/stale-lease/recovery PASS                            |
| Workspace Security         |    0 | `64 passed`; static isolation PASS                                 |
| Validation Security        |    0 | Landlock/seccomp/Profile boundaries PASS                           |
| Runner Security            |    0 | `111 passed`; scanner `7 passed`                                   |
| Eval                       |    0 | 67 deterministic cases; scanner `7 passed`                         |
| final `git diff --check`   |    0 | clean                                                              |

The recurring FastAPI/Starlette deprecation warning is non-failing and
pre-existing. No warning threshold was relaxed.

## Source and canonical Workspace invariance

A standalone source-invariance check and the aggregate check both pass. The
standalone run compared 118 source entries; the aggregate fixture compared 119. Both compare 10 Git objects and two status records with zero extension
markers.

Every new independent denial/replay case captures and rechecks the canonical
Workspace. The legal success case also retains the canonical Workspace. No
source or canonical mutation was observed.

## Production-code invariance

The final diff from candidate
`b6d53ba0275933e18919ceb2d90152e5ae8efcac` is empty for:

- `apps/api/src` and API migrations;
- `apps/runner/src`;
- `packages/runner-protocol/src`;
- `apps/web/src` and Web E2E;
- generated API contracts;
- API/Runner/Web Dockerfiles;
- `compose.yaml` and `infra`;
- `scripts`, `Makefile`, `pyproject.toml`, lockfiles, and package
  configuration.

The sealing scope contains only:

- one independent audit test;
- the focused re-audit ExecPlan;
- the focused re-audit report;
- this verification evidence;
- project status; and
- the necessary active-plan update in `PLANS.md`.

Historical FAIL reports and original focused tests remain unchanged.

## Exact cleanup

Focused and final PostgreSQL projects were stopped and removed using exact
project names and their matching published ports. E2E and Chaos used the
repository cleanup traps. Exact label-filter inventories after cleanup:

```text
ve-p5-suites-reaudit-max containers=0 networks=0 volumes=0
ve-p5-suites-reaudit-final containers=0 networks=0 volumes=0
ve-p5-suites-reaudit-final-rerun containers=0 networks=0 volumes=0
ve-p5-suites-reaudit-final-e2e containers=0 networks=0 volumes=0
ve-p5-suites-reaudit-final-chaos containers=0 networks=0 volumes=0
```

Listener probes:

```text
35730 absent
35740 absent
35743 absent
35640 absent
38640 absent
39640 absent
35641 absent
38641 absent
```

Five task-created image aliases were removed. Their underlying image IDs remain
available under the original remediation tags. No unknown container, network,
volume, image, port owner, or process was stopped or removed.

## Findings and limitations

- Critical: `0`
- High: `0`
- blocking Medium: `0`
- new non-blocking production Finding: `0`
- unresolved local aggregate blocker: `0`

Remote CI, artifact transport, deployment, hostile multi-user execution,
Customer 0, another Phase 5 slice, and Phase 6 are `NOT VERIFIED` or out of
scope. They do not become authorized by this local seal.

## Pre-sealing Git reconciliation

Before staging:

- branch is `audit/phase-5-validation-suites-reaudit-max`;
- candidate is still the branch parent;
- `main` remains `f547091307c52df8f20fc69bac4b4826cbbc74ad`;
- production diff is empty;
- all untracked/modified files are within the authorized sealing list;
- remote, stash, tag, merge, push, pull request, and Git locks remain absent;
  and
- exact Docker runtime inventories are empty.

The reserved subject is:

`chore: seal phase 5 governed validation suites`

The final commit ID and clean post-commit state are reported in the
administrative handoff because a commit cannot include its own stable object
ID.
