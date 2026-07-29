# Phase 5 Cancel-Permit Single-Finding Re-Audit Verification

- Date: 2026-07-30 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `audit/phase-5-cancel-permit-single-finding-max`
- Candidate: `c9e5268f1287f49ac0ba5c5d26045395b8e72dc0`
- FAIL checkpoint: `4ce5a1a8e63ec530517f17ae82fc3aeb7747c4de`
- Main: `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Status: COMPLETE — OVERALL FAIL
- Single-Finding: PASS
- mypy governance: PASS
- Final aggregate: FAIL, exit `2`
- Remote CI: NOT VERIFIED

## Evidence boundary

This evidence covers only:

1. `VE-P5-FREAUD-001` successful active Validation cancellation and exact
   Permit terminalization; and
2. strict mypy discovery of Phase 5 focused-review, focused re-audit,
   remediation, and current audit security tests.

The remediation report was used for navigation only. Current verdicts rely on
independent Git inspection, source review, real PostgreSQL, configured mypy
discovery, current-worktree static gates, exact Docker cleanup, and the one
final aggregate.

## Git preflight

| Check                                      | Exit | Confirmed result                                   |
| ------------------------------------------ | ---: | -------------------------------------------------- |
| `pwd` / repository root                    |    0 | exact authorized repository                        |
| initial branch                             |    0 | remediation branch                                 |
| initial HEAD                               |    0 | exact candidate `c9e5268...`                       |
| `git rev-parse main`                       |    0 | exact `928a89d...`                                 |
| candidate/checkpoint object types          |    0 | both `commit`                                      |
| candidate parent                           |    0 | exact `4ce5a1a...`                                 |
| checkpoint ancestor check                  |    0 | true                                               |
| checkpoint-to-candidate commit count       |    0 | exactly `1`                                        |
| candidate commit subject                   |    0 | exact declared remediation subject                 |
| initial worktree/index/untracked           |    0 | empty                                              |
| remote/stash/tag/Git lock                  |    0 | empty                                              |
| worktree inventory                         |    0 | one worktree                                       |
| candidate `git diff --check`               |    0 | no whitespace error                                |
| original independent test Git blob compare |    0 | byte-identical at FAIL and remediation checkpoints |
| target audit branch existence              |    1 | absent as required                                 |

The independent branch was created without force from the exact candidate.

## Remediation diff review

The complete one-commit diff contains:

```text
9 files changed, 724 insertions(+), 23 deletions(-)
```

Production changes are confined to the Validation cancellation path and mypy
configuration. Existing test changes add exact annotations/casts and remove
one obsolete point ignore; no business assertion changes. The original
independent re-audit test is byte-identical.

Static cancellation review confirms:

- active Runner/Job/Attempt/Lease validation precedes mutation;
- the stored `ValidationExecuteJobSpec` is parsed;
- exact Validation Run and step rows are locked;
- Run/Job/Grant/Workspace/Checkpoint/Profile/policy/budget bindings are
  compared before Permit mutation;
- the Permit is selected by exact Job, Attempt, and canonical stored-spec
  digest;
- Permit, Attempt, Job, Validation Run, and step change in one transaction;
- one cancellation acknowledgement is emitted before the single commit; and
- cleanup-failure handling remains a separate failed/`recovery_required`
  transaction.

## Real PostgreSQL setup

Focused project:

`visualengineer-phase5-single-reaudit-20260730`

Published test port: `55435`.

Migration project:

`visualengineer-phase5-single-reaudit-migration-20260730`

Published test port: `55436`.

Both projects used the repository `test-db` service. Alembic head was applied
by the API fixture. No SQLite or mock persistence was used.

## Original Finding and independent case

The unchanged permanent reproduction:

```text
apps/api/tests/test_phase5_validation_control_plane_reaudit.py::
test_reaudit_successful_active_cancel_terminalizes_consumed_permit
```

Result: `1 passed`, exit `0`.

The additive independent file contains exactly one test. It:

1. creates a governed Validation execution and captures its active identity;
2. requests and acknowledges cancellation;
3. records Permit terminal timestamp, Validation Run version, and total event
   count;
4. replays cancellation with the terminal Attempt/Lease;
5. submits one mismatched Lease replay;
6. submits late completion with the old exact Attempt/Lease; and
7. rereads all durable records.

Result: `1 passed`, exit `0`.

Confirmed after replay:

```text
Job = cancelled, Result = NULL
Attempt = cancelled
Validation Run = cancelled, version unchanged
Validation step = cancelled
Permit = cancelled, terminal_at unchanged
Validation Evidence count = 0
total Runner Job event count = unchanged
cancel_acknowledged count = 1
job_succeeded count = 0
side_effect_permit_completed count = 0
Workspace fingerprint = unchanged
```

Exact cancellation replay is idempotent. Mismatched Lease replay and late
completion return typed `stale_lease` conflict responses.

## Focused PostgreSQL command ledger

| Selection                              | Exit |       Count |
| -------------------------------------- | ---: | ----------: |
| original Finding                       |    0 |  `1 passed` |
| independent boundary case              |    0 |  `1 passed` |
| normal cancellation matrix             |    0 |  `3 passed` |
| cleanup-failure matrix                 |    0 |  `2 passed` |
| stale/replay/idempotency matrix        |    0 |  `4 passed` |
| complete Phase 5 Control Plane focused |    0 | `49 passed` |
| focused Runner/Protocol                |    0 | `21 passed` |
| relevant Runner/Workspace API          |    0 | `23 passed` |

The complete Control Plane focused selection includes historical focused
security tests, permanent remediation tests, independent re-audit tests,
cancel-Permit remediation tests, and the current additive test.

## Cancellation terminal matrix

| Record / effect                 | Expected                 | Actual                   |
| ------------------------------- | ------------------------ | ------------------------ |
| Job                             | cancelled, no Result     | cancelled, no Result     |
| Attempt                         | cancelled                | cancelled                |
| Validation Run                  | cancelled                | cancelled                |
| Validation step                 | cancelled                | cancelled                |
| Side-effect Permit              | cancelled, timestamp set | cancelled, timestamp set |
| Permit late use                 | denied                   | denied                   |
| cancellation replay             | idempotent               | idempotent               |
| Validation Evidence             | zero                     | zero                     |
| `job_succeeded`                 | zero                     | zero                     |
| `side_effect_permit_completed`  | zero                     | zero                     |
| replay-created total events     | zero                     | zero                     |
| canonical Workspace fingerprint | unchanged                | unchanged                |

## Cleanup-failure non-regression

Real-PostgreSQL selections cover:

- `validation_cleanup_failed`; and
- `validation_process_remained`.

Result: `2 passed`, exit `0`.

Both produce:

```text
Job = failed, Result = NULL
Attempt = failed
Permit = failed
Validation Run = recovery_required
Validation step = recovery_required
cancel_acknowledged count = 0
job_succeeded count = 0
side_effect_permit_completed count = 0
Validation Evidence count = 0
Workspace fingerprint = unchanged
```

Failure replay remains idempotent.

## Stale, mismatch, and replay matrix

Result: `4 passed`, exit `0`.

The selection independently covers:

- stale Attempt;
- stale Lease;
- cross-Runner identity;
- mismatched persisted Validation Run;
- unrelated Permit preservation;
- exact cancellation replay;
- stale terminal Lease replay; and
- late completion.

No rejected request changes the target or unrelated Permit. No replay creates
a Result, Evidence, success/completion event, or Workspace mutation.

## mypy discovery evidence

Configured verbose mypy emitted `BuildSource` records for:

```text
apps/api/tests/test_phase5_focused_security_review.py
apps/runner/tests/security_audit/test_phase5_focused_security_review.py
apps/api/tests/test_phase5_validation_control_plane_reaudit.py
apps/runner/tests/security_audit/test_phase5_validation_runner_reaudit.py
apps/api/tests/test_phase5_control_plane_remediation.py
apps/runner/tests/test_phase5_remediation.py
apps/api/tests/test_phase5_validation_cancel_permit_remediation.py
apps/api/tests/test_phase5_cancel_permit_single_finding_reaudit.py
```

The API historical module has base directory `apps/api/tests`; the Runner
historical module is named through its repository package path. No duplicate
module collision appears.

Result:

```text
Success: no issues found in 91 source files
exit 0
```

Independent source/config inspection confirms:

- `strict = true`;
- `explicit_package_bases = true`;
- no mypy `exclude`;
- no mypy `ignore_errors`;
- no disabled error code or relaxed untyped option;
- no targeted or new blanket `# type: ignore`; and
- candidate count 90 plus exactly one current audit file equals 91.

## Aggregate-precondition gates

| Command / check                      | Exit | Result                                       |
| ------------------------------------ | ---: | -------------------------------------------- |
| `make format-check`                  |    0 | Ruff 120 files; Prettier matched             |
| `make lint`                          |    0 | Ruff and ESLint                              |
| `make typecheck`                     |    0 | mypy 91 files; TypeScript                    |
| fresh `make migration-check`         |    0 | base/head/base/head                          |
| `make source-invariance-check`       |    0 | 119 entries, 10 objects, 2 status, 0 markers |
| candidate production-tree comparison |    0 | empty working-tree diff                      |
| pre-aggregate `git diff --check`     |    0 | no whitespace error                          |
| focused PostgreSQL project cleanup   |    0 | zero container/network/volume residue        |
| migration PostgreSQL project cleanup |    0 | zero container/network/volume residue        |

Candidate frozen production/gate inventory:

```text
entries = 163
git ls-tree SHA-256 =
beae532e006bcf280a9b05a76e4286eaa344c1cffe3622a7a837c9cc00c018b5
```

## Final `make verify` ledger

The command was invoked exactly once.

| Aggregate stage                          | Result                                   |
| ---------------------------------------- | ---------------------------------------- |
| contracts drift                          | PASS                                     |
| format                                   | PASS, Ruff 120 files                     |
| lint                                     | PASS                                     |
| typecheck                                | PASS, mypy 91 files                      |
| Python/API/Runner/Protocol               | PASS, 227 tests, 82.95% coverage         |
| Web unit                                 | PASS, 44 tests                           |
| Next.js production build                 | PASS                                     |
| Docker Compose rendering                 | PASS                                     |
| PostgreSQL migration roundtrip           | PASS                                     |
| Phase 4 permanent Finding controls       | PASS                                     |
| Runner security audit                    | PASS, 22 tests                           |
| source invariance                        | PASS                                     |
| Phase 4 workspace security repair target | PASS, 85 plus 14 tests                   |
| E2E setup                                | FAIL, fixed API host port already in use |
| Playwright                               | NOT RUN                                  |
| Workspace Chaos                          | NOT RUN                                  |
| Workspace Security                       | NOT RUN                                  |
| Validation Security                      | NOT RUN                                  |
| later broad Security                     | NOT RUN                                  |
| Eval                                     | NOT RUN                                  |
| aggregate final `git diff --check`       | NOT REACHED                              |

Final command result:

```text
E2E API bind target = 127.0.0.1:18000
failure class = port already in use
make e2e exit = 2
make verify exit = 2
```

The owner of the occupied port was not inspected, stopped, or modified. No
second aggregate was run.

## Audit-document formatting ledger

The first post-report `make format-check` found only the two new audit/evidence
Markdown files; exit `2`. Prettier was applied only to those exact documents.
The complete format, lint, and typecheck rerun then passed with Ruff 120 files,
mypy 91 files, ESLint, and TypeScript; exit `0`. No test or production source
changed during that correction.

## Docker cleanup and existing-platform ledger

Exact audit-owned resource checks after cleanup:

| Compose project                                           | Containers | Networks | Volumes |
| --------------------------------------------------------- | ---------: | -------: | ------: |
| `visualengineer-phase5-single-reaudit-20260730`           |          0 |        0 |       0 |
| `visualengineer-phase5-single-reaudit-migration-20260730` |          0 |        0 |       0 |
| `visualengineer-e2e`                                      |          0 |        0 |       0 |

The current-repository default platform has four services reporting 8–31
hours uptime:

```text
visualengineer-db-1
visualengineer-api-1
visualengineer-web-1
visualengineer-runner-1
```

They predate this minutes-long review and were left running and untouched.
They are not classified as audit-owned residue.

## Source, Workspace, and production invariance

Source invariance passed both before and inside the aggregate:

```text
source_entries_compared = 119
source_git_objects_compared = 10
source_status_records = 2
extension_markers = 0
status = PASS
```

Every independent real-PostgreSQL case asserts the canonical Workspace
fingerprint. The production/gate diff from the exact candidate remains empty.

## New Finding and blocker classification

```text
Critical = 0
High = 0
blocking Medium = 0
new production security Findings = 0
aggregate environment blockers = 1
```

The port collision blocks sealing but is not a production security Finding.

## Final allowed-write and Git checks

The intended checkpoint allowlist is:

```text
apps/api/tests/test_phase5_cancel_permit_single_finding_reaudit.py
docs/exec-plans/phase-5-cancel-permit-single-finding-reaudit.md
docs/security/audits/phase-5-cancel-permit-single-finding-reaudit.md
docs/evidence/phase-5-cancel-permit-single-finding-reaudit-verification.md
docs/status/project-status.md
```

No production path is permitted in the checkpoint. Final format, lint,
typecheck, diff, production-invariance, main/ref, and clean-state checks are
recorded before and after the local FAIL checkpoint.

## CONFIRMED / INFERRED / NOT VERIFIED

### CONFIRMED

- Exact baseline, candidate ancestry, branch, main, and original test
  integrity.
- Single-Finding, cleanup-failure, stale/mismatch/replay, and mypy governance
  focused gates pass.
- Real PostgreSQL, strict configured mypy, format, lint, typecheck, migration,
  source/canonical Workspace, production-tree invariance, and focused cleanup
  evidence above.
- The one final aggregate passes every recorded stage before E2E setup and
  returns exit `2` on the fixed API port.
- Audit-owned E2E resources clean to zero.
- No production change, remote, push, merge, pull request, tag, or
  CreativeDeploy access occurred.

### INFERRED

- Existing default platform resources predate the review based on reported
  uptime.
- The port conflict is external local state rather than candidate behavior.

### NOT VERIFIED

- A complete exit-0 final aggregate.
- Playwright and aggregate targets after E2E.
- Remote CI, deployment, production, customer, hostile multi-tenant behavior,
  later Phase 5 slices, or Phase 6.

**PHASE 5 SINGLE-FINDING RE-AUDIT FAIL — REMEDIATION REQUIRED**
