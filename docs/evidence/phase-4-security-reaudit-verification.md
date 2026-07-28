# Phase 4 Independent Security Re-Audit Evidence

- Date: 2026-07-28 (Asia/Shanghai)
- Re-audit branch: `audit/phase-4-security-reaudit-max`
- Repair commit:
  `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c`
- Original audit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Remote: none
- Status: COMPLETE — SECURITY GATE FAIL
- Coverage: not collected for focused `--no-cov` runs; no coverage percentage
  is inferred

## Evidence boundary

This evidence was produced independently from current Git, filesystem,
PostgreSQL, Docker, API, Protocol, and test execution. Repair documentation and
repair test totals were used only to locate claimed controls.

No production source, migration, contract, Docker production configuration, or
repair branch file was modified. CreativeDeploy was not accessed.

The frozen 71-file production boundary is:

`apps/api/src`, `apps/runner/src`, `packages/runner-protocol/src`,
`compose.yaml`, `infra`, `apps/api/alembic`, `apps/api/Dockerfile`, and
`apps/runner/Dockerfile`.

Initial current-worktree SHA-256 content-manifest digest:

`3d86a5d2d423a73a3819d06e45289a6e1050d09b96595577f16c4aee94fc3147`

Repair Git-tree listing digest:

`eacd9a8f554c63832c67b17ea43a23657ce9fee25e23cf606d23870a2ebe89a8`

## Stable production-defect evidence

Detailed reproduction code is confined to:

`apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py`

This ledger intentionally records conditions and outcomes without restating a
step-by-step attack procedure.

| Test                                                                        | Trigger condition                                                                                      | Expected result                             | Actual result                                                         | Finding                             | Severity        | Stable exit | Production hash |
| --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------- | --------------------------------------------------------------------- | ----------------------------------- | --------------- | ----------: | --------------- |
| `test_reaudit_unreachable_uncommitted_object_is_not_imported_into_mirror`   | A source object is outside the approved revision's reachable closure.                                  | Runner mirror excludes the object.          | Runner mirror contains the object; Workspace file remains absent.     | `VE-P4-AUD-001` / `VE-P4-REAUD-001` | Critical        |           1 | unchanged       |
| `test_reaudit_registry_loss_and_absent_root_requires_signed_recovery_proof` | Mutable registry and expected root are absent with no trusted signed pending-discard completion proof. | Recovery-required or quarantine error.      | Discard reports success; the safely preserved synthetic root remains. | `VE-P4-AUD-003` / `VE-P4-REAUD-002` | High            |           1 | unchanged       |
| `test_reaudit_timeout_kills_process_group_after_leader_exits`               | Process leader exits while a descendant keeps output pipes open past the deadline.                     | Timeout error and terminated process group. | No timeout error; descendant continues past the deadline.             | `VE-P4-AUD-005` / `VE-P4-REAUD-003` | Blocking Medium |           1 | unchanged       |

All fixtures are generated under pytest temporary directories. The third test
has bounded cleanup; the child naturally exits and no process remains after
the test.

## Focused test execution ledger

| Command / selection                                                                                                           | Exit |                    Count | Result                                                                            |
| ----------------------------------------------------------------------------------------------------------------------------- | ---: | -----------------------: | --------------------------------------------------------------------------------- |
| `uv run pytest apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py -k 'reaudit_' --no-cov -vv` (first run) |    1 | 3 selected, 4 deselected | two production assertion failures; third test stopped with audit-test `NameError` |
| same file, third re-audit test only, after import correction                                                                  |    1 |                 1 failed | no `NameError`; production did not raise the required timeout error               |
| same file, `-k 'reaudit_'`, after import correction                                                                           |    1 |   3 failed, 4 deselected | all three production defects reproduced                                           |
| same file, `-k 'not reaudit_'`                                                                                                |    0 |   4 passed, 3 deselected | preserved repair regressions still pass                                           |
| same complete file, final stable rerun                                                                                        |    1 |       3 failed, 4 passed | exact three-defect result reproduced again                                        |

The failed assertions are the intended secure expectations. They are not
converted to `xfail`, skipped, weakened, or treated as a passing Gate.

## First failure and audit-test correction

First third-test failure:

`NameError: name 'GitOperationError' is not defined`

Classification: audit test error, not a production defect.

Root cause: the audit test imported `GitOperations` but not the exception class
used by its expected-failure assertion.

Correction:

`from visual_engineer_runner.git_ops import GitOperationError, GitOperations`

Only the independent test import changed. The immediate single-test rerun
reached production behavior and failed with:

`Failed: DID NOT RAISE ... GitOperationError`

The later three-test and complete-file reruns produced the same production
failure and no `NameError`.

The first post-writing `make format-check` also exited 2 because Ruff would
mechanically collapse two multiline expressions in the new audit tests. Ruff
was run on exactly that test file and Prettier on exactly the four changed
audit/status documents. The repeated `make format-check` exited 0. This was a
formatting correction only and did not change any production file.

## Git baseline command ledger

| Command / check                                                    | Exit | Confirmed result                                                                           |
| ------------------------------------------------------------------ | ---: | ------------------------------------------------------------------------------------------ |
| `pwd`; `git rev-parse --show-toplevel`                             |    0 | both resolve to `/Users/danke/Developer/VisualEngineer`                                    |
| initial branch/HEAD/status/diffs/remotes                           |    0 | `fix/phase-4-security-remediation` at exact repair commit; clean worktree/index; no remote |
| `git show-ref --heads`; graph/log review                           |    0 | main, Phase 4, original audit, and repair refs match claimed hashes                        |
| four `git cat-file -t` checks                                      |    0 | all four objects are commits                                                               |
| first variable-grouped `git merge-base` batch                      |  128 | invalid zsh argument grouping; no repository state change                                  |
| explicit two-argument merge-base/ancestor rerun                    |    0 | exact main → Phase 4 → audit → repair ancestry                                             |
| `git rev-list --count audit..repair`                               |    0 | exactly `1`                                                                                |
| repair metadata/parent check                                       |    0 | expected subject and exact audit parent                                                    |
| `git diff --stat audit..repair`                                    |    0 | 68 files, 7,501 insertions, 571 deletions                                                  |
| `git diff --check audit..repair`                                   |    0 | no whitespace error                                                                        |
| stash/submodule/worktree/replace/special-ref/fsck checks           |    0 | no undisclosed local state; repository not shallow                                         |
| create `audit/phase-4-security-reaudit-max` from exact repair hash |    0 | independent branch created without changing other refs                                     |
| initial production-boundary diff and hashes                        |    0 | no diff; 71 files; digests recorded above                                                  |

The first merge-base command failure was methodological, not a repository
defect. Quoted zsh variables did not split into the two intended commit
arguments. Explicit arguments corrected the command; all ancestry checks then
passed.

## Current independent verification commands

| Command / probe                                                    | Exit | Count / result                                                                         |
| ------------------------------------------------------------------ | ---: | -------------------------------------------------------------------------------------- |
| `make source-invariance-check`                                     |    0 | PASS; 119 source entries, 10 source Git objects, 2 status records, 0 extension markers |
| `make workspace-security-check`                                    |    0 | 35 tests passed; descriptor/static isolation check passed                              |
| direct `scripts/check_phase4_findings.py`                          |    0 | six controls detected; historical independent Gate remains `FAIL_PRESERVED`            |
| `make contracts-check`                                             |    0 | OpenAPI/TypeScript regeneration produced no drift                                      |
| `make migration-check`                                             |    0 | real PostgreSQL downgrade/upgrade/re-upgrade passed; disposable test DB removed        |
| real PostgreSQL `apps/api/tests/test_workspace_api.py --no-cov -q` |    0 | 8 passed; 1 upstream Starlette deprecation warning                                     |
| original four repair regressions                                   |    0 | 4 passed                                                                               |
| `make docker-config`                                               |    0 | base, test, Workspace, E2E, and Customer 0 configurations render                       |
| first `make format-check` after audit writing                      |    2 | one additive audit-test file required Ruff formatting                                  |
| exact audit-test/document formatting                               |    0 | only allowed audit test/document paths formatted                                       |
| corrected `make format-check`                                      |    0 | 97 Python files and all Prettier inputs formatted                                      |
| `make lint`                                                        |    0 | Ruff and ESLint pass                                                                   |
| `make typecheck`                                                   |    0 | mypy 72 source files and TypeScript pass                                               |
| `docker compose ps --all`                                          |    0 | API/DB/Web healthy; Runner running                                                     |
| live API `/health/live` from host and Runner                       |    0 | HTTP 200 / `{"status":"ok"}`                                                           |
| immutable image/Action reference search                            |    0 | Postgres digest and full Action SHAs; no added skip/xfail and no deleted test          |
| Docker inspect and in-container isolation probes                   |    0 | runtime facts below                                                                    |

The PostgreSQL API tests exercise focused trigger/constraint, Permit binding,
replay, two-session acquisition/revocation, wait/cancel, and expiry behavior.
They support the repair but do not substitute for the complete separately
authored adversarial matrix required to close `VE-P4-AUD-002`.

## Source invariance

**PASS for the dedicated independent synthetic lifecycle.**

`make source-invariance-check` returned:

`{"branch":"main","extension_markers":0,"source_entries_compared":119,"source_git_objects_compared":10,"source_status_records":2,"status":"PASS"}`

This proves no observed source/source-`.git` drift for that harness. It does
not prove that every object copied into the mirror belongs to the approved
revision; `VE-P4-AUD-001` independently disproves that authorization boundary.

## PostgreSQL, API, Protocol, and contracts

- PostgreSQL migration upgrade/downgrade/re-upgrade: **PASS**.
- Focused real PostgreSQL Workspace API tests: **8 PASS**.
- Complete independent Side-effect Permit closure: **NOT VERIFIED**.
- Live API health, host and Runner control network: **PASS**.
- Runner tool and pure Protocol focused tests: **35 PASS**.
- OpenAPI and generated TypeScript contract drift: **PASS / no drift**.
- Full API, Web, browser, and aggregate project suite: **NOT RUN after Gate
  failure**.

## Docker runtime

Independent live inspection confirmed:

| Property               | Result                                                                |
| ---------------------- | --------------------------------------------------------------------- |
| Runner identity        | UID/GID 10001                                                         |
| root filesystem        | read-only write probe rejected                                        |
| capabilities           | `CapEff=0`; `cap_drop=ALL`                                            |
| privilege escalation   | `NoNewPrivs=1`                                                        |
| CPU                    | 1 CPU                                                                 |
| memory                 | 536,870,912 bytes                                                     |
| PID                    | 128                                                                   |
| FD                     | soft/hard 256                                                         |
| temporary filesystem   | `/tmp` writable, noexec/nosuid/nodev, 16 MiB                          |
| fixture source         | Runner-only bind, read-only; write probe rejected                     |
| Runner private volumes | credential, mirror, Workspace, and registry volumes; no Docker socket |
| API/Web mounts         | none                                                                  |
| DB mount               | only PostgreSQL data volume                                           |
| ports                  | Runner none; API/DB/Web bound to `127.0.0.1`                          |
| network                | Runner only on `runner-control`; DB/Web DNS isolated                  |
| default route          | none                                                                  |
| API reachability       | permitted, HTTP 200                                                   |
| ownership key          | credential volume, mode 0600, UID/GID 10001, 32 bytes                 |

The resource configuration is present, but the process-group timeout
reproduction makes `VE-P4-AUD-005` fail.

## Checks stopped after Security Gate failure

| Check                                  | Current re-audit status | Stop reason                                                                               |
| -------------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------- |
| full `make test` and `make build`      | NOT RUN                 | cannot close the three stable security failures                                           |
| browser `make e2e`                     | NOT RUN                 | no UI claim is needed to establish current Gate FAIL                                      |
| `make workspace-smoke`, `runner-smoke` | NOT RUN                 | broader lifecycle expansion stopped after stable blockers                                 |
| runner/workspace chaos                 | NOT RUN                 | not required to reconfirm the three minimal defects                                       |
| `workspace-security-repair-check`      | NOT RUN                 | implementer aggregate cannot override failing independent assertions                      |
| full `security-check` and `eval`       | NOT RUN                 | downstream non-closing checks stopped                                                     |
| `make phase4-findings-check`           | not treated as a PASS   | its independent-test component necessarily fails on the three preserved secure assertions |
| final `make verify`                    | NOT RUN                 | PASS is impossible while the independent blocking tests fail                              |
| remote CI                              | NOT VERIFIED            | no remote configured; no push authorized                                                  |

## CONFIRMED / INFERRED / NOT VERIFIED

### CONFIRMED

- Exact Git ancestry, baseline hashes, one-commit repair, no remote, and clean
  initial repair state.
- Three production defects are stable across corrected reruns.
- `VE-P4-AUD-001` and `VE-P4-AUD-003` remain open.
- `VE-P4-AUD-005` is a blocking Medium under the declared local Runner
  resource boundary.
- Dedicated source invariance, focused PostgreSQL/API/Protocol/contracts, and
  live Docker topology results stated above.
- No production implementation was edited.
- The final pre-checkpoint production diff is empty and the production
  content/tree digests remain exactly
  `3d86a5d2d423a73a3819d06e45289a6e1050d09b96595577f16c4aee94fc3147`
  and
  `eacd9a8f554c63832c67b17ea43a23657ce9fee25e23cf606d23870a2ebe89a8`.
- CreativeDeploy was not accessed.
- No merge, push, or pull request occurred.

### INFERRED

- Importing unreachable objects can retain unapproved or sensitive content in
  Runner storage even if that content is not checked out. This impact follows
  from the confirmed object-copy behavior; no real sensitive data was used.
- A false discard-success result can cause the Control Plane/operator to
  suppress needed recovery. The local Runner result is confirmed; broader
  operational impact is inferred.

### NOT VERIFIED

- Complete independent closure of `VE-P4-AUD-002`.
- Full browser/E2E/smoke/chaos/security/Eval/aggregate verification for this
  re-audit branch.
- Remote CI, hostile-code, hostile multi-tenant, production, fleet-quota, or
  customer-repository safety.

## Final Gate

**RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED**
