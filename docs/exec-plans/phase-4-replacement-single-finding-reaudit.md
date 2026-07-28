# Phase 4 Independent Single-Finding Re-Audit — Git Replacement Metadata

- Started: 2026-07-29T03:09:07+08:00
- Branch: `audit/phase-4-replacement-single-finding-max`
- Candidate / Round 3 repair:
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`
- Base / focused re-audit checkpoint:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Historical Security Gate: **FAIL — PRESERVED**
- Current status:
  `SINGLE-FINDING RE-AUDIT COMPLETE — VE-P4-FREAUD-001 FAIL — REMEDIATION REQUIRED`

## Goal

Independently decide only whether Round 3 closes `VE-P4-FREAUD-001`:
replacement metadata must not make an exact authorized revision, `HEAD`, and
object closure materialize different Workspace bytes.

A PASS requires both fail-closed mirror metadata handling and exact
Workspace-to-authorized-tree semantics. This review cannot approve unrelated
Phase 4 findings, merge `main`, authorize Customer 0, or begin Phase 5.

## Scope

Permitted changes are limited to:

- additive independent audit tests for `VE-P4-FREAUD-001`;
- this ExecPlan;
- `docs/security/audits/phase-4-replacement-single-finding-reaudit.md`;
- `docs/evidence/phase-4-replacement-single-finding-reaudit-verification.md`;
  and
- `docs/status/project-status.md`.

The reviewer may read the complete Round 3 diff and directly related history,
run synthetic Git/object/Workspace tests, run the specified focused
Runner/Protocol and invariance targets, and create one local audit-only
checkpoint.

## Non-goals

- No Runner, API, Protocol, migration, Compose, infrastructure, Web, or other
  production implementation change.
- No re-audit of the already independently passing discard, process-group
  timeout, or Side-effect Permit findings.
- No repair of a reproduced defect and no weakening, deletion, skip, or
  `xfail` of an existing test.
- No complete `make verify`, Web E2E, full Chaos, full Docker Gate, Customer 0,
  CreativeDeploy access, LLM, Agents SDK, Git delivery, deployment, remote,
  push, pull request, merge, or tag.

## Constraints and safety

- Operate only in `/Users/danke/Developer/VisualEngineer`.
- Stop before overwriting work if candidate identity, exact parent, one-commit
  ancestry, protected refs, worktree/index/untracked inventory, remote, stash,
  or disclosed history cannot be reconciled.
- Treat implementer evidence as navigation only; rerun every decisive check.
- Use only generated synthetic repositories and repository-owned test
  fixtures. Never use a customer repository.
- Preserve every historical FAIL report and every unexpected/quarantined byte.
- If a production defect is reproduced, add only the smallest secure-
  expectation audit test, record FAIL, and do not repair production.
- Create at most one local checkpoint after final scope, production
  invariance, protected-ref, and staged-diff review.

## Trusted baseline

The following are **CONFIRMED** before the first audit edit:

- repository root: `/Users/danke/Developer/VisualEngineer`;
- starting branch: `fix/phase-4-security-remediation-3`;
- candidate and starting `HEAD`:
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`;
- the candidate's sole parent:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`;
- the focused-checkpoint-to-candidate range contains exactly one commit and
  passes `git diff --check`;
- `main` remains
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`;
- tracked worktree, index, and untracked inventory were empty;
- remote, stash, and tag inventories were empty;
- the audit branch did not pre-exist and was created directly from the full
  candidate hash; and
- no CreativeDeploy host path, Git configuration, or Compose mount is
  configured. A historical Customer 0 script contains only a static
  CreativeDeploy-labelled API payload and was not run.

The frozen production boundary contains 72 tracked files under
`apps/api/src`, `apps/runner/src`, `packages/runner-protocol/src`,
`apps/api/alembic`, `compose.yaml`, `infra`, and the API/Runner Dockerfiles.

| Evidence                                      | SHA-256                                                            |
| --------------------------------------------- | ------------------------------------------------------------------ |
| Initial current-content manifest              | `3a9c6e71e25c1ab39022eaf1556500937afb453278397dd44a75a8e20aed8e5b` |
| Candidate Git-tree listing                    | `93a9ce4302f1c58a54c68b6ab4abefecd90cec0fb4cff86fb65999d672c7ad3c` |
| Protected-ref set excluding this audit branch | `bceb29fd3bd2e67b7598326fc06af2c5f0d594b341eca1b0070024c966785507` |

## Current progress

### 2026-07-29

- DONE: read the complete work order and identify the real repository.
- DONE: reconcile the required Git baseline, exact parent, ancestry,
  one-commit range, refs, remote, stash, tag, and clean worktree/index.
- DONE: create the audit branch from the exact Round 3 candidate.
- DONE: read all mandatory governance, historical finding, repair, production,
  test, architecture, ADR, evidence, and threat-model material.
- DONE: review the complete Round 3 diff.
- DONE: freeze the 72-file production boundary and protected refs.
- DONE: run the unchanged original packed-replacement reproduction; it passes
  `1/1`.
- DONE: add and run a distinct late-injection packed-replacement test through
  the actual Workspace prepare path; it passes `1/1`.
- DONE: reproduce an over-budget source-less manifest from a compact shared
  Git subtree; preserve the additive secure-expectation test without changing
  production.
- DONE: classify the later complete manager path: typed budget rejection, one
  quarantine, canonical path absent, and no registry.
- DONE: run the specified security/invariance/Runner focus. Existing
  replacement/object/Workspace gates pass; the complete blocking and
  Runner/Protocol files fail only on the additive budget assertion.
- DONE: write the audit report, verification evidence, and status update.
- DONE: final scoped Ruff/Prettier checks and repository
  `make format-check`, `make lint`, and `make typecheck` pass.
- DONE: repeat pre-checkpoint production/ref/scope closure; the 72-file
  content digest, candidate tree digest, protected refs, and exact five-path
  audit scope match the frozen values.
- PENDING: create one audit-only checkpoint and verify the final
  worktree/index.

## Decisions

1. **Use a late packed-ref interposition scenario.** Inject
   `packed-refs` after `prepare_mirror` has completed validation but before the
   actual production worktree checkout. This differs from the repairer's
   direct loose-ref `_run` test and the original pre-existing packed-ref
   reproduction.
2. **Require two observable properties.** The in-flight checkout must contain
   exact approved bytes despite the late replacement, and the polluted mirror
   must fail closed on the next prepare rather than become accepted state.
3. **Exercise host-environment resistance.** The test sets hostile Git
   environment variables outside the fixed adapter environment; the actual
   Runner call must neither inherit them nor target the synthetic source as a
   Git directory/object database.
4. **Keep production frozen.** Only audit tests and the five authorized
   audit/status documents may differ from the candidate.
5. **Do not prune explained unreachable objects.** Reflogs identify
   `f8bd4190d79dca8989fc59f534fef503cb469021` as the same-parent pre-amend
   Round 3 checkpoint; it is not a ref, stash, or alternate candidate branch.
6. **Treat expanded-manifest capacity as part of this finding's acceptance
   boundary.** The work order explicitly requires capacity and stability. A
   source-less manifest that can exceed its configured path-entry limit before
   the later Workspace scanner is a Blocking Medium even though the later
   manager path still quarantines the minimal case.
7. **Preserve a FAIL test without repairing production.** The secure
   expectation accepts a typed budget rejection or a manifest within the
   configured limit. Current production returns eight entries under a limit
   of five, so the failure is not implementation-specific.

## Risks

| Risk                                                          | Impact          | Mitigation / next action                                                                  |
| ------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------- |
| A late replacement ref bypasses mirror validation             | Critical        | Exercise the actual prepare-to-checkout path and require exact approved bytes.            |
| A later Git path omits command or environment replacement off | Critical        | Inspect every `_run` call and central subprocess construction; run replacement tests.     |
| Manifest expectation depends on Git replacement output        | Critical        | Trace it to the source-less parser and compare raw path/type/mode/size/digest semantics.  |
| Semantic mismatch remains normally addressable                | High            | Verify typed rejection, canonical path absence, quarantine preservation, and no registry. |
| Shared Git trees expand the expected manifest past its budget | Blocking Medium | Add a bounded shared-subtree reproduction; require pre-return enforcement and no repair.  |
| Source/object closure regresses                               | Critical        | Run the exact source-invariance and focused object-closure checks.                        |
| Audit additions drift into production                         | Critical        | Repeat 72-file content digest and candidate-path diff before staging.                     |

## Discoveries

- Round 3 has exactly three production changes:
  `git_object_store.py`, `git_ops.py`, and the prepare call site in
  `workspace_manager.py`.
- Every production Git subprocess is created only by `GitOperations._run`;
  its fixed argv contains `--no-replace-objects`, its replacement environment
  contains `GIT_NO_REPLACE_OBJECTS=1`, and it uses `shell=False`.
- The source is read only by direct no-follow parsing; no production
  subprocess receives it as a working directory, Git directory, worktree,
  object database, alternate, or fetch source.
- New mirrors use an empty template, detached exact `HEAD`, exact config, and
  an empty `refs/{heads,tags}` namespace. Pre-existing `packed-refs`, extra
  top-level metadata, or any loose ref fails closed before Git interpretation.
- The expected checkout manifest comes from the source-less object parser;
  the actual manifest uses descriptor-rooted no-follow traversal and compares
  raw path bytes, type, Git mode, size, and SHA-256 before ownership/registry
  creation.
- `git fsck --full --no-reflogs --unreachable` lists four unreachable commit
  objects. Three are previously documented pre-amend predecessors. Reflog and
  direct parent/diff inspection identify the fourth, `f8bd419...`, as the
  Round 3 pre-amend predecessor with the same focused checkpoint parent and
  only two documentation differences from the final candidate.
- One initial repository search named a nonexistent
  `apps/runner/tests/conftest.py` and exited `2`; the corrected search over
  `apps/runner/tests` exited `0`.
- `_walk_tree` charges a shared tree only once, while the new
  `_walk_checkout_manifest` expands it once per path without a counter. A
  five-entry unique-tree case returns an eight-entry `PreparedMirror`
  manifest. The permanent secure-expectation test fails identically twice.
- A complete manager-path probe later returns typed
  `mirror_budget_exceeded`, creates one quarantine, leaves no canonical
  Workspace, and creates no registry. The blocker is therefore pre-enforcement
  expected-manifest availability/stability, not an unauthorized registered
  Workspace.
- The unchanged original packed replacement, distinct late replacement,
  six-case Round 3 matrix, 19-case object/ref/manifest focus, strict source
  invariance, and 58-case Workspace/Protocol target all pass.

## Verification

No result is `VERIFIED` until its exact current-worktree command exits zero.
Detailed commands, exit codes, counts, first failures, corrections, and
reruns belong in the verification evidence file.

| Check                                          | Status                                   |
| ---------------------------------------------- | ---------------------------------------- |
| Git baseline and audit branch                  | VERIFIED                                 |
| Complete Round 3 diff review                   | VERIFIED                                 |
| Original packed-replacement reproduction       | VERIFIED — 1 PASS                        |
| Independent late packed-replacement scenario   | VERIFIED — 1 PASS                        |
| Mirror metadata and replacement dual-disable   | VERIFIED                                 |
| Workspace semantic fields/quarantine           | VERIFIED                                 |
| Workspace manifest capacity                    | FAIL — BLOCKING MEDIUM                   |
| Source and exact object-closure invariance     | VERIFIED                                 |
| Complete blocking file                         | FAIL — 1 FAILED, 11 PASSED               |
| Workspace/Protocol target                      | VERIFIED — 58 PASS                       |
| Complete Runner/Protocol target                | FAIL — 1 FAILED, 76 PASSED; SAME BLOCKER |
| Final format/lint/type checks                  | VERIFIED                                 |
| Final diff/scope/hash checks                   | VERIFIED — PRE-CHECKPOINT                |
| Aggregate `make verify` / E2E / Chaos / Docker | NOT RUN — OUT OF SCOPE                   |
| Final production/ref closure                   | VERIFIED — PRE-CHECKPOINT                |
| Final checkpoint/worktree closure              | NOT YET VERIFIED                         |

## Rollback

- Audit changes remain isolated on the dedicated branch until one final local
  checkpoint.
- Do not reset, clean, stash, prune, force-update, or overwrite any ref or
  user state.
- Focused tests create only temporary synthetic repositories and clean them
  through pytest fixtures.
- If a blocker is reproduced, preserve the audit-only test and evidence; do
  not modify production to make it pass.

## Completion conditions

PASS would require:

1. the original packed-replacement reproduction passes;
2. the independent late-injection adversarial scenario passes;
3. source/destination replacement metadata cannot change approved bytes;
4. every Runner Git path has both replacement defenses and cannot inherit a
   caller override;
5. exact source-less/Workspace manifest semantics, mismatch rejection, and
   quarantine pass;
6. source invariance and exact authorized object closure pass;
7. all specified focused, format, lint, type, and diff checks exit zero;
8. no production path differs from the candidate and no existing test is
   weakened;
9. no new Critical, High, or blocking Medium finding exists;
10. protected refs remain unchanged and the local audit checkpoint contains
    only authorized audit paths; and
11. the final worktree/index is clean with no remote, push, merge, PR, tag,
    CreativeDeploy access, Customer 0 action, or Phase 5 action.

Conditions 5 and 9 are not met. FAIL completion instead requires:

1. preserve the smallest additive secure-expectation reproduction;
2. record the passing replacement paths and the manifest-capacity failure
   without changing production;
3. prove source and frozen production-boundary invariance;
4. preserve protected refs and historical FAIL reports;
5. create one audit-only local checkpoint; and
6. finish with a clean worktree/index and no remote, customer, merge,
   delivery, deployment, or Phase 5 action.

## Outcome and follow-ups

`SINGLE-FINDING RE-AUDIT COMPLETE — VE-P4-FREAUD-001 FAIL — REMEDIATION REQUIRED`

The only eligible next milestone is a narrow production remediation that
charges every expanded source-less manifest path before materialization,
followed by another independent single-finding review. This outcome does not
authorize `main` merge, Customer 0, or Phase 5.
