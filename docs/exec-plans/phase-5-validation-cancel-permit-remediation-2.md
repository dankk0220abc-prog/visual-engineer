# Phase 5 Validation Cancel Permit Remediation 2

- Started: 2026-07-30 (Asia/Shanghai)
- Branch: `fix/phase-5-validation-cancel-permit-remediation-2`
- Base: `4ce5a1a8e63ec530517f17ae82fc3aeb7747c4de`
- Candidate predecessor:
  `8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9`
- Main baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Status: `VERIFIED — LOCAL CHECKPOINT PREPARED`

## Goal

Close only `VE-P5-FREAUD-001` and the focused-audit mypy governance
nonconformance. Successful active Validation cancellation must atomically
terminalize the exact consumed Permit with the cancelled Job, Attempt,
Validation Run, and step. Independent Phase 5 audit and remediation tests
must remain in strict mypy discovery.

## Scope

Permitted implementation changes are limited to:

- Validation cancellation and exact Permit terminal handling;
- necessary cancellation binding and transaction checks;
- directly related PostgreSQL regression tests;
- mypy module discovery and necessary audit-test annotations; and
- this ExecPlan, verification evidence, architecture/status documentation.

Result identity, output/artifact budget revalidation, leader-first timeout,
sandbox, Profile Catalog, Web product behavior, Phase 4, LLM/Agents SDK,
CreativeDeploy, Git delivery, later Phase 5 slices, and Phase 6 remain
unchanged.

## Progress

- done — exact repository, Git baseline, ancestry, checkpoint contents, clean
  inventory, remote/stash/tag/lock, and target-branch preflight
- done — branch created directly from the independent FAIL checkpoint
- done — required audit/report/evidence/status/test/Runner/model/repository/
  migration/mypy review
- done — original real-PostgreSQL Finding reproduced unchanged `5/5`
- done — mypy duplicate-module and wrong-module-resolution failures reproduced
- done — minimal production repair and direct PostgreSQL regressions
- done — focused API `48/48`, Runner/Protocol `21/21`, and Runner/API
  relevant `23/23`
- done — strict mypy checks 90 files and verbose discovery names both
  historical focused files, both re-audit files, and remediation regressions
- done — empty-PostgreSQL base/head/base/head migration roundtrip
- done — repository format, lint, typecheck, aggregate test, build, contracts,
  source/canonical Workspace invariance, and `git diff --check`
- done — exact remediation-owned Compose cleanup with zero container, network,
  or volume residue
- done — documentation finalization and allowed-write review
- prepared — the single authorized local checkpoint; its object ID and final
  clean inventory are reported after commit

## Decisions

1. Reuse the active Runner/Job/Attempt/Lease lock and the existing exact
   `job_id + attempt_id + job_digest` Permit lookup. Do not accept a
   Runner-supplied Permit identifier during cancellation.
2. Lock and validate the persisted Validation Run and step before changing the
   Permit. A mismatched Run, step, Grant, Workspace, Checkpoint, Profile,
   policy digest, or budget aborts before any terminal mutation.
3. Update Permit, Job, Attempt, Validation Run, and step in the one
   `RunnerService.cancelled` transaction and commit once after the cancellation
   event.
4. Preserve cleanup failures in the existing failed/`recovery_required`
   transaction; successful cancellation does not catch or reclassify them.
5. Resolve the two same-named historical audit modules through explicit mypy
   package bases plus the API test import base. Remove both exclusions and the
   `ignore_errors` override; do not lower strictness or add an ignore.
6. Add only type annotations/casts to historical audit helpers. Their runtime
   assertions remain unchanged.
7. Do not run final `make verify`; it remains reserved for the independent
   single-finding re-audit.

## Failure ledger

| Stage                         | First result                                             | Classification                                  | Correction / retained result                                                                 |
| ----------------------------- | -------------------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Finding baseline              | `1 failed`, exit `1`, repeated five times                | production defect                               | actual Permit `consumed` without terminal timestamp; secure expectation unchanged            |
| configured mypy baseline      | 3 wrong-module attribute errors, 87 files, exit `1`      | governance/configuration defect                 | remove exclusions/override and establish distinct module names                               |
| explicit historical pair      | duplicate module, exit `2`                               | governance/configuration defect                 | explicit package bases plus API test import base                                             |
| mypy after exclusions removed | 2 missing annotations, 89 files, exit `1`                | test typing debt previously hidden              | exact response/callable annotations only                                                     |
| first new stale/mismatch run  | `1 failed, 1 passed`, exit `1`                           | test expectation classification                 | cross-Runner identity is `403`; stale Attempt/Lease remain `409`; denial assertions retained |
| first focused format check    | Runner service required mechanical layout, exit `1`      | formatting only                                 | Ruff formatting; behavior unchanged                                                          |
| first migration roundtrip     | downgrade rejected live `validate` Permit rows, exit `2` | disposable database contained focused-test data | recreate only the exact remediation database; empty-database base/head/base/head passed      |
| first repository format check | two new Markdown files required Prettier, exit `2`       | formatting only                                 | scoped Prettier formatting; complete rerun passed                                            |

## Verification strategy

1. Run the permanent Finding before and after the repair.
2. Prove direct post-acknowledgement PostgreSQL state without relying on a
   later Validation GET synchronization.
3. Prove cleanup-failure non-regression, stale Attempt/Lease/Runner denial,
   mismatched Validation Run denial, unrelated Permit preservation,
   cancellation replay idempotency, and late completion rejection.
4. Run historical focused, permanent remediation, new re-audit, Runner,
   Protocol, and normal non-Validation cancellation suites.
5. Prove mypy discovery from verbose `BuildSource` records and record the
   complete file count.
6. Run migration upgrade/downgrade/re-upgrade, format, lint, typecheck, test,
   build, contracts drift, source invariance, and `git diff --check`.
7. Confirm unchanged main, exact source/canonical Workspace invariance, no
   CreativeDeploy access, no remote/push/merge/PR/tag, and clean final Git
   inventory after one local checkpoint.

## Rollback

Stop and remove only the exact remediation-owned Compose project. Do not
reset, clean, stash, force, rewrite history, move main, or overwrite a branch.
Before the checkpoint, revert only this remediation's reviewed paths if the
secure expectations cannot pass.

## Completion condition

Success means the narrow implementation and all required non-aggregate gates
pass locally, documentation is current, one local commit exists with subject
`fix(validation): finalize permit on cancelled validation`, and the repository
is clean. This implementer may report readiness for a fresh independent
single-finding re-audit, but may not declare Security Gate PASS.

All pre-checkpoint completion conditions pass. The exact checkpoint and clean
post-commit inventory are administrative facts reported after this plan is
committed.
