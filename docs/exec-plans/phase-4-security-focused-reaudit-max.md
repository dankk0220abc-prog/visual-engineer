# Phase 4 Independent Focused Security Re-Audit

- Started: 2026-07-29T01:45:13+08:00
- Closed: 2026-07-29T02:03:49+08:00
- Branch: `audit/phase-4-security-focused-reaudit-max`
- Candidate / Round 2 repair:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`
- Base / preserved independent re-audit:
  `b457b614bde6630fb50ff9546c92a4d6925ad38a`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Initial Security Gate: **FAIL — PRESERVED**
- Current status:
  `FOCUSED RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED`

## Goal

Independently decide whether the Round 2 candidate closes only the four
authorized Phase 4 blocker scopes:

1. `VE-P4-AUD-001` / `VE-P4-REAUD-001`: exact authorized Git object closure;
2. `VE-P4-AUD-003` / `VE-P4-REAUD-002`: authenticated discard proof;
3. `VE-P4-AUD-005` / `VE-P4-REAUD-003`: complete process-group deadline; and
4. `VE-P4-AUD-002`: real-PostgreSQL Side-effect Permit closure.

Only if all four independently pass may the final complete Gate and live
Docker isolation Gate run. This review cannot merge, push, open a pull
request, begin Phase 5, or authorize a customer repository.

## Scope

Permitted changes are limited to:

- additive independent audit tests;
- this focused re-audit ExecPlan;
- `docs/security/audits/phase-4-security-focused-reaudit.md`;
- `docs/evidence/phase-4-security-focused-reaudit-verification.md`; and
- `docs/status/project-status.md`.

The reviewer may read all repository code and history and may run synthetic
Git/workspace/process fixtures, repository-owned PostgreSQL, Docker, API,
Web, browser, E2E, smoke, chaos, security, and Eval checks.

## Non-goals

- No Runner, API, Web, Protocol, migration, Compose, infrastructure, or other
  production implementation change.
- No repair of a reproduced production defect.
- No deletion, weakening, skip, or `xfail` of an existing test.
- No threat-model expansion, shell capability, target-repository command,
  build/test execution, Git delivery, LLM, Agents SDK, deployment, or Phase 5.
- No merge, remote, push, pull request, or tag.
- No customer-repository access, mount, read, scan, build, test, or write.

## Constraints and safety

- Stop before writing if the candidate baseline, ancestry, protected refs,
  worktree, index, untracked inventory, remote, stash, or disclosed commit
  relationship does not reconcile.
- Stop focused execution on a stable Critical, High, or blocking Medium
  failure. Preserve the smallest audit-only reproduction and do not run
  downstream aggregate checks that cannot close it.
- Use only generated synthetic repositories and exact repository-owned
  disposable PostgreSQL and Compose resources.
- Do not execute Git against a source fixture through the production adapter,
  use the source as a Git directory/object database/worktree/alternate/fetch
  source, or recurse into a gitlink.
- Preserve source, mirror, workspace sibling, unknown/quarantined data, and
  unrelated resources on every rejection path.
- Record every first failure, audit-test error, correction, focused rerun,
  command, exit code, count, and final disposition.
- Create at most one local audit checkpoint and only after final scope,
  production-invariance, ref, and staged-diff review.

## Trusted baseline

The following are **CONFIRMED** before the first audit edit:

- repository root: `/Users/danke/Developer/VisualEngineer`;
- starting branch:
  `fix/phase-4-security-remediation-2`;
- starting HEAD and candidate:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`;
- exact linear one-commit steps:
  `7590f9d` -> `53dc2f5` -> `a560509` -> `e3d6530` -> `b457b61` ->
  `cb799bc`;
- the candidate's sole parent is the re-audit checkpoint;
- tracked worktree, index, and untracked inventory were clean;
- no remote, stash, tag, or pre-existing focused re-audit branch existed;
- all six candidate hashes are commit objects;
- the Round 2 diff passes `git diff --check`; and
- the branch was created directly from the full candidate hash.

`git fsck --full --no-reflogs --unreachable` reported three unreachable
commit objects. The repository reflog independently identifies each as the
pre-amend predecessor of a disclosed Phase 2, Phase 3, or original-audit
commit. None is a ref, stash, extra Round 2 commit, or alternate candidate
history.

The frozen production boundary contains 72 tracked files under
`apps/api/src`, `apps/runner/src`, `packages/runner-protocol/src`,
`compose.yaml`, `infra`, `apps/api/alembic`, and the API/Runner Dockerfiles.
Its initial current-content manifest digest is:

`3ca1448901c572da082a75fb002da81b73b347974c753e8ef7b28f5a167787d3`

Its candidate Git-tree listing digest is:

`be07a14623a65593d5f0c8ddd1a22219b3b7aa3f30f8ee7794206282f312c707`

## Current progress

### 2026-07-29

- DONE: read the complete user work order and identify the real repository.
- DONE: run and record the required Git baseline, object, parent, ancestry,
  one-commit, diff, ref, remote, stash, reflog, and worktree checks.
- DONE: explain the three historical pre-amend unreachable commits without
  changing or pruning repository objects.
- DONE: create the focused re-audit branch from the exact Round 2 candidate.
- DONE: read `AGENTS.md`, `PLANS.md`, `SECURITY.md`, `README.md`, project
  status, both historical audit reports, all four required evidence records,
  the Round 2 ExecPlan, and the complete preserved blocking-reproduction file.
- DONE: freeze the 72-file production boundary.
- DONE: review the complete Round 2 diff and all affected Git object,
  ownership/discard, process execution, Permit, and threat-model code.
- DONE: add independent adversarial cases that differ from the implementer
  matrix.
- DONE: run the complete preserved re-audit file, focused object/discard/
  process tests, real-PostgreSQL Permit matrix, and source invariance.
- NOT RUN: the single final full Gate and live Docker isolation checks because
  the object-closure scope has a stable new Critical failure.
- DONE: complete the report/evidence/status, final invariant review, and
  scoped local checkpoint.

## Decisions

1. **Treat implementer evidence as navigation only.** No stated PASS, count,
   or runtime fact is accepted without a current independent run.
2. **Explain, do not delete, historical unreachable objects.** Their reflog
   provenance reconciles the baseline; pruning would be destructive and is
   outside scope.
3. **Freeze production before audit edits.** Git path comparison and an
   independent SHA-256 content digest will be repeated before checkpoint.
4. **Use additive tests with secure expectations.** A failure is a Gate
   failure, not a reason to weaken or mark the test expected-failing.
5. **Sequence focused checks before aggregates.** A stable blocker ends the
   useful execution phase and preserves resources for evidence capture.

## Risks

| Risk                                                          | Impact          | Mitigation / next action                                                                              |
| ------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------- |
| Parser accepts an object outside the authorized closure       | Critical        | Independently compare exact object-ID sets and add a distinct packed/ref-shaping adversarial fixture. |
| Existing destination state bypasses validation or budget      | Critical        | Review and test pre-existing object/config/pack paths before mutation.                                |
| Discard infers completion from mutable or replayed state      | High            | Exercise root replacement or proof replay while fingerprinting source, mirror, root, and sibling.     |
| Descendant outlives declared deadline                         | Blocking Medium | Exercise a leader-first child that closes output and survives, then prove group/PID absence.          |
| Permit concurrency test observes a cached PostgreSQL snapshot | Critical        | Use independent sessions and fresh transactions or explicit snapshot clearing for each observation.   |
| Cleanup reaches unrelated resources                           | Critical        | Use unique fixture/project identifiers and exact supported cleanup; preserve unknown resources.       |

## Discoveries

- The candidate is exactly one commit after the preserved independent
  re-audit and changes 25 files.
- Three unreachable commit objects are historical pre-amend predecessors,
  fully explained by local reflogs rather than hidden candidate history.
- The repository contains historical Customer 0 documentation and commands,
  but no customer path has been used as this review's test source.
- The prior re-audit stopped broad checks after three stable blockers; this
  focused review must independently close the omitted Permit matrix before it
  can decide PASS.
- `VE-P4-FREAUD-001` is a new Critical path within `VE-P4-AUD-001`: existing
  mirror validation does not reject replacement refs encoded in
  `packed-refs`, and later Git subprocesses interpret them.
- The Critical reproduction preserves the approved commit ID and exact
  destination object set but checks out an ancestor's content. Object-set
  equality therefore does not prove exact authorized revision semantics.
- The discard, process-group, and real-PostgreSQL Permit focused scopes pass
  their preserved and independent variations.
- The work order's stop rule makes the final full Gate and complete live
  Docker Gate intentionally not run and not inferred.

## Verification

No focused or aggregate result is recorded as PASS until the exact command
runs in this worktree and exits zero. Detailed commands, exit codes, counts,
first failures, reruns, and runtime facts belong in
`docs/evidence/phase-4-security-focused-reaudit-verification.md`.

Current verification status:

| Check                               | Status              |
| ----------------------------------- | ------------------- |
| Git baseline and branch             | VERIFIED            |
| Production-boundary freeze          | VERIFIED            |
| Complete Round 2 diff review        | VERIFIED            |
| Exact authorized Git object closure | FAIL — CRITICAL     |
| Authenticated discard proof         | PASS                |
| Complete process-group deadline     | PASS                |
| Real-PostgreSQL Permit closure      | PASS                |
| Source invariance                   | PASS                |
| Final full Gate                     | NOT RUN — STOP RULE |
| Live Docker isolation and cleanup   | NOT VERIFIED        |
| Contracts and migrations            | NOT VERIFIED        |
| Final production invariance         | VERIFIED            |

## Rollback

- Audit additions remain isolated on the focused branch until one final
  checkpoint.
- Do not reset, clean, stash, force-update, prune, or overwrite any ref or
  user state.
- Stop only exact repository-owned disposable services through their
  supported Make/Compose teardown target.
- If a focused blocker fails, preserve the audit-only reproduction and
  evidence; do not revert or repair production.

## Completion conditions

The PASS completion conditions are not met: the object-closure scope has one
stable Critical failure. The final full Gate and full Docker Gate are
therefore ineligible. FAIL completion instead requires:

1. preserve the additive Critical reproduction without changing production;
2. record focused PASS/FAIL evidence and every first failure/correction;
3. prove source and frozen production-boundary invariance;
4. preserve historical audit conclusions and protected refs;
5. create one audit-only local checkpoint with a clean final worktree/index;
   and
6. perform no customer-repository access, remote, push, merge, PR, tag, target
   command, delivery, deployment, or Phase 5 action.

## Outcome and follow-ups

`FOCUSED RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED`

`VE-P4-FREAUD-001` remains open at Critical severity. The only safe next
milestone is a narrowly scoped production remediation followed by a fresh
independent focused read-only security re-audit. This result does not
authorize merge, push, PR, Customer 0, or Phase 5.

The closing scoped formatter/lint and diff checks pass. The six changed paths
are exactly the two additive audit-test files and four authorized audit/status
documents. The final 72-file current-content digest and candidate Git-tree
digest equal their frozen values, production paths have no candidate diff,
protected refs are unchanged, and remote/stash/tag inventories remain empty.
The final handoff records the audit checkpoint hash externally because a
commit cannot contain its own hash.
