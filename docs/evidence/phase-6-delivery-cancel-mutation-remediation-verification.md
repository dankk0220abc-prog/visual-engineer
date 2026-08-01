# Phase 6 Delivery Cancel-Mutation Arbitration Verification

## Identity and scope

- Repository: `/Users/danke/Developer/VisualEngineer`
- Candidate: `9bef907f78ca482da1a06a8ff7e2ce3d3c2e1c9d`
- Main: `79fa63f5d911a9e13ad388f270fdd18bf9084d22`
- Branch: `fix/phase-6-delivery-cancel-mutation-arbitration`
- Migration/API schema/Web/Manifest/digest: unchanged

Preflight confirmed the exact candidate and main, clean tracked/untracked
state, `main` as exact merge-base and ancestor, and an unused target branch.

## Arbitration evidence

The real PostgreSQL tests use independent sessions and a commit barrier while
the winner owns the Job row lock. `pg_stat_activity.wait_event_type = 'Lock'`
and `pg_blocking_pids` identify the expected blocking backend before release.

| Case                         | Winner                            | Loser                                | Durable result                                                              |
| ---------------------------- | --------------------------------- | ------------------------------------ | --------------------------------------------------------------------------- |
| cancel first                 | cancel commits `cancel_requested` | Permit returns `stale_lease`         | cancellation acknowledged; no Permit or LocalDelivery                       |
| mutation first               | consumed Git Permit commits       | cancel returns `runner_job_terminal` | success terminalizes Job/Attempt/Permit/Dispatch/Authorization consistently |
| simultaneous                 | exactly one of the above          | exactly one conflict                 | no double success and no cancelled/success contradiction                    |
| Grant revoke after ownership | consumed Git Permit               | cancellation conversion is skipped   | Grant waits `revoke_requested`, then finalizes after success                |

The Runner regression independently proves cancel-first performs one Permit
attempt, one authoritative renew, and one cancellation acknowledgement while
never invoking the Git executor or creating mirror/workspace/registry state.

## Verification completed

| Command group                                                    | Result                  | Exit |
| ---------------------------------------------------------------- | ----------------------- | ---: |
| Runner cancel-first regression                                   | `1 passed`              |    0 |
| real PostgreSQL arbitration and revoke regression                | `4 passed`              |    0 |
| Phase 6 API lifecycle plus arbitration                           | `14 passed`             |    0 |
| Phase 6 Runner/Protocol and real Git focused tests               | `12 passed`             |    0 |
| related PostgreSQL cancel/lease/Permit/revoke/crash/budget tests | `11 passed`             |    0 |
| Runner lifecycle plus Phase 6 focused Security                   | `10 passed`             |    0 |
| `scripts/check_runner_security.py`                               | passed                  |    0 |
| `uv run mypy`                                                    | 118 source files passed |    0 |
| `make format`                                                    | passed                  |    0 |
| `make format-check`                                              | passed                  |    0 |
| `make lint`                                                      | Ruff + ESLint passed    |    0 |
| `make typecheck`                                                 | mypy + Web tsc passed   |    0 |
| `make source-invariance-check`                                   | PASS                    |    0 |
| `git diff --check`                                               | passed                  |    0 |

The only emitted test warning is the existing Starlette `httpx` deprecation
warning. The first task-owned format check exited `1` because three newly
edited files required formatting; the targeted formatter was run, followed by
successful targeted lint and all affected focused tests. The final source
invariance result compared 119 source entries and 10 source Git objects, with
zero extension markers and status `PASS`.

## Final scope and cleanup

Tracked plus untracked enumeration contains only:

- three production files for control-plane cancellation/revocation and Runner
  cancel-first acknowledgement;
- two additive deterministic regression files; and
- five directly related architecture, security, ExecPlan, and evidence files.

No Manifest/digest, migration, remote boundary, API schema, Web, dependency,
environment, CI, fixture source, or generated contract file changed. The
task-owned isolated PostgreSQL `test-db` on port 55433 was stopped and removed.
The pre-existing development API/DB/Runner/Web containers remain running and
untouched. The exact local commit and clean post-commit Git identity are
reported in the handoff because this evidence file is part of that commit.

## Explicitly not run

Complete `make verify`, Workspace Chaos, Phase 5 deadlock attribution, complete
Migration roundtrip, unrelated Phase 0-5/Phase 6 First Slice suites, contracts,
Web unit/build/browser, and sealing. Contracts/Web are skipped because no API
schema or Web behavior changed.
