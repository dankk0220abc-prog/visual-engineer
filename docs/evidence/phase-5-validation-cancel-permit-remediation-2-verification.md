# Phase 5 Validation Cancel Permit Remediation 2 Verification

- Date: 2026-07-30 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/phase-5-validation-cancel-permit-remediation-2`
- Base: `4ce5a1a8e63ec530517f17ae82fc3aeb7747c4de`
- Main: `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Status: VERIFIED — LOCAL CHECKPOINT PREPARED
- Final `make verify`: NOT RUN by design
- Remote CI: NOT VERIFIED

## Git baseline

The initial worktree was the exact independent FAIL checkpoint on
`audit/phase-5-validation-remediation-focused-max`.

| Check                                      | Exit | Result                                                     |
| ------------------------------------------ | ---: | ---------------------------------------------------------- |
| `pwd` / `git rev-parse --show-toplevel`    |    0 | exact repository root                                      |
| initial branch / HEAD                      |    0 | audit branch at exact `4ce5a1a...`                         |
| `git rev-parse main`                       |    0 | exact `928a89d...`                                         |
| candidate/checkpoint object types          |    0 | both `commit`                                              |
| checkpoint parent                          |    0 | exactly `8ca5c9e...`                                       |
| candidate ancestor check                   |    0 | true                                                       |
| candidate-to-checkpoint `git diff --check` |    0 | clean                                                      |
| checkpoint content review                  |    0 | two independent tests plus audit/evidence/plan/status only |
| worktree/index/untracked                   |    0 | empty                                                      |
| remote/stash/tag/Git lock                  |    0 | empty                                                      |
| target branch existence check              |    1 | absent as required                                         |

The branch was created without force from the exact checkpoint. No baseline
inconsistency was found.

## Original stable failure

Real PostgreSQL ran in the exact Compose project
`visualengineer-phase5-cancel-remediation2` on loopback host port `55434`.
Alembic applied head.

The unchanged permanent reproduction was executed five times:

```text
apps/api/tests/test_phase5_validation_control_plane_reaudit.py::
test_reaudit_successful_active_cancel_terminalizes_consumed_permit
```

Every run exited `1` with `1 failed`. In all five:

```text
actual:   Permit ("consumed", terminal_at present = false)
expected: Permit ("cancelled", terminal_at present = true)
```

The assertions preceding the Permit check proved cancelled Job, Attempt,
Validation Run, and step; no Job Result; no Validation Evidence; no success
event; and unchanged canonical Workspace. No independent business assertion
was changed.

## Root cause

`RunnerService.cancelled` locked and verified the active Job/Attempt/Lease,
parsed the persisted Job spec, and terminalized a Permit only for four
Workspace mutation specs. `ValidationExecuteJobSpec` was omitted. The method
then cancelled Job and Attempt, emitted `cancel_acknowledged`, and committed.
A later Validation GET synchronized Run/step, leaving the consumed Permit
open.

## Production repair

The repaired path:

1. parses the persisted `ValidationExecuteJobSpec`;
2. locks the exact Validation Run and step;
3. checks the persisted Job, Run, Grant, Workspace, Checkpoint, Profile,
   policy digest, budget, and step bindings;
4. finds the Permit by exact Job, Attempt, and canonical stored-spec digest;
5. terminalizes only that active Permit as `cancelled`;
6. changes Attempt, Job, Validation Run, and step to `cancelled`; and
7. emits the acknowledgement and commits once.

The existing `_active_lease` and Permit helper retain Runner/Attempt/Lease
fencing and immutable terminal-state handling. There is no blanket exception
handler and no unconditional Permit closure.

## PostgreSQL terminal evidence

The permanent Finding passed immediately after the production change:
`1 passed`, exit `0`.

Two new direct PostgreSQL regressions then proved:

- Permit, Job, Attempt, Validation Run, and step are already cancelled after
  the Runner acknowledgement, before any synchronizing Validation GET;
- Permit `terminal_at` and Run/step completion timestamps are present;
- the exact revocation-requested Grant becomes revoked after its sole consumed
  Permit is terminal;
- an unrelated execution's Permit remains consumed;
- canonical Workspace fingerprint is unchanged;
- exact cancellation replay is idempotent and does not change Permit timestamp
  or Validation Run version;
- late completion is rejected;
- Evidence, `job_succeeded`, and `side_effect_permit_completed` remain absent;
  and
- only one `cancel_acknowledged` event exists.

First new regression run: `1 failed, 1 passed`, exit `1`, because the test
initially expected every mismatched identity to be `409`. Production correctly
classified a cross-Runner credential/identity mismatch as
`403 runner_identity_mismatch`; stale Attempt and Lease remained
`409 stale_lease`. The test expectation was corrected to the existing
protocol categories. Rerun: `2 passed`, exit `0`.

## Cleanup failure and stale/replay evidence

The unchanged cleanup-failure selections passed `2/2`, exit `0`:

- `validation_process_remained`; and
- `validation_cleanup_failed`.

Both retain failed Job/Attempt/Permit and `recovery_required` Run/step, with no
clean cancellation acknowledgement, Result, Evidence, success event, duplicate
terminal effect, or Workspace mutation.

The new denial regression proves stale Attempt, stale Lease, cross-Runner
identity, and mismatched persisted Validation Run cannot terminalize either
the target or an unrelated Permit. The target stays `cancel_requested` with a
running Attempt and consumed non-terminal Permit.

## Focused runtime ledger

| Selection                                                                    | Exit |     Count |
| ---------------------------------------------------------------------------- | ---: | --------: |
| permanent Finding after repair                                               |    0 |  1 passed |
| cleanup-failure selections                                                   |    0 |  2 passed |
| new cancellation regressions rerun                                           |    0 |  2 passed |
| historical API focused + permanent remediation + re-audit + new regression   |    0 | 48 passed |
| Phase 5 Runner focused/re-audit/remediation + Validation executor + Protocol |    0 | 21 passed |
| complete Runner API and Workspace API relevant files                         |    0 | 23 passed |

The final repository aggregate `make test` ran with a separate exact
remediation-owned PostgreSQL project:

- Python/API/Runner/Protocol: `226 passed`, 82.92% coverage, exit `0`;
- Web: 8 files, `44 passed`, exit `0`; and
- combined `make test`: exit `0`.

## mypy governance repair

Baseline configured mypy exited `1` after checking 87 files because the new
re-audit module resolved the shared test basename to the wrong historical
module. Explicitly checking both historical same-named files exited `2` with a
duplicate-module error.

The repair:

- removes both exact audit-test exclusions;
- removes the shared-module `ignore_errors` override;
- keeps global `strict = true`;
- enables `explicit_package_bases`;
- adds `apps/api/tests` as the API test import base; and
- removes the now-unused `# type: ignore`, adding only exact helper
  annotations/casts.

The first aggregate run after removal checked 89 files and exposed two missing
historical helper annotations; exit `1`. After annotation, mypy checked 90
files with no issues; exit `0`.

Verbose discovery records distinct modules for both historical focused files
and explicitly lists:

- API and Runner historical focused security review;
- API and Runner focused re-audit;
- API and Runner remediation tests; and
- the new cancellation remediation regression.

No blanket ignore, new `# type: ignore`, exclusion, or strictness reduction is
present.

## Migration and repository gates

The first migration roundtrip ran against the already populated focused-test
database. Downgrade from Phase 5 correctly could not install the older Phase 4
Permit-operation constraint while `validate` rows existed; exit `2`. No
migration was changed. Only the exact disposable remediation database was
removed and recreated. The empty-database roundtrip then completed
base → head → base → head; exit `0`.

The first repository format check found only the two new Markdown files; exit
`2`. Scoped Prettier formatting was applied. Complete rerun passed.

| Command                               | Exit | Confirmed result                                                   |
| ------------------------------------- | ---: | ------------------------------------------------------------------ |
| fresh-database `make migration-check` |    0 | base/head/base/head                                                |
| final `make format-check`             |    0 | Ruff 119 files; Prettier all matched                               |
| `make lint`                           |    0 | Ruff and ESLint                                                    |
| `make typecheck`                      |    0 | mypy 90 files; TypeScript                                          |
| final `make test`                     |    0 | Python 226; Web 44                                                 |
| `make build`                          |    0 | Next.js production build                                           |
| `make contracts-check`                |    0 | OpenAPI/TypeScript regeneration has no drift                       |
| `make source-invariance-check`        |    0 | 119 entries, 10 Git objects, 2 status records, 0 extension markers |
| `git diff --check`                    |    0 | no whitespace errors                                               |

Final `make verify` was intentionally not run.

## Source and canonical Workspace invariance

The strict source harness reports `PASS` with 119 source entries, 10 Git
objects, two status records, and zero extension markers. The direct
PostgreSQL cancellation, cleanup-failure, stale/mismatch, rejection, replay,
and success controls assert the canonical Workspace fingerprint is unchanged.

The frozen production/gate inventory diff from the independent checkpoint
contains only the authorized Runner cancellation service and `pyproject.toml`.
No migration, Runner executor, Protocol, result-identity, budget, timeout,
sandbox, Web, Compose, infrastructure, generated contract, Makefile, or
script change exists.

## Resource and Git pre-checkpoint state

Four exact remediation-owned Compose project names were removed. Filtered
post-cleanup checks report zero containers, labeled containers, networks, and
volumes for every name. No other project was inspected or cleaned.

The pre-checkpoint changed/untracked inventory is exactly:

```text
apps/api/src/visual_engineer_api/services/runner.py
apps/api/tests/test_phase5_control_plane_remediation.py
apps/api/tests/test_phase5_focused_security_review.py
apps/api/tests/test_phase5_validation_cancel_permit_remediation.py
docs/architecture/state-machine.md
docs/evidence/phase-5-validation-cancel-permit-remediation-2-verification.md
docs/exec-plans/phase-5-validation-cancel-permit-remediation-2.md
docs/status/project-status.md
pyproject.toml
```

All paths are inside the authorized remediation scope. Main remains
`928a89d2055d172bbd7c6670b42f668d103dcb03`. Remote, stash, tag, push, merge,
PR, and CreativeDeploy access remain absent. The exact local checkpoint hash
and clean worktree/index/untracked inventory are reported after the commit
containing this document.

## Classification ledger

### CONFIRMED

- Exact baseline and branch provenance.
- Original real-PostgreSQL failure stable `5/5`.
- Root-cause omission and one-transaction repair.
- Focused PostgreSQL cancellation, recovery, stale/mismatch, replay, and
  Workspace invariance results above.
- mypy exclusions/override removed and 90-file strict check passing.
- Migration, format, lint, typecheck, aggregate test, build, contracts, source
  invariance, resource cleanup, scope, and pre-checkpoint Git checks pass.

### INFERRED

- Closing the consumed Permit promptly prevents the historical deferred
  revocation window; the direct regression proves exact Grant finalization for
  the tested transaction.

### NOT VERIFIED

- Final independent single-finding decision and the reserved final
  `make verify`.
- Remote CI, deployment, customer behavior, later Phase 5 slices, or Phase 6.

**PHASE 5 FINAL TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT
SINGLE-FINDING RE-AUDIT**
