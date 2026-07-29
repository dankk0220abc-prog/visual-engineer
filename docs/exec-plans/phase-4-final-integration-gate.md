# Phase 4 Final Integration Gate

- Started: 2026-07-29T16:38:40+08:00
- Branch: `integration/phase-4-final-gate`
- Candidate:
  `38afe4b0c8eefa4c34b58e0b9d30cb74ca931501`
- Candidate parent / Round 4 repair:
  `03f774827afbafd7f0eb991f5abf2c6fee66cd17`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Status: COMPLETE — FINAL INTEGRATION GATE PASS
- Remote CI: NOT VERIFIED

## Goal

Independently run the single final local integration gate over the complete
Phase 4 candidate, preserve historical audit FAIL decisions and their later
closure evidence, and create one local sealing checkpoint only if every
current engineering, database, browser, Runner, Workspace, Chaos, Docker,
security, Eval, source-invariance, production-invariance, cleanup, and Git
condition passes.

The strongest successful outcome is:

`PHASE 4 FINAL INTEGRATION GATE PASS — READY FOR USER-AUTHORIZED MAIN INTEGRATION`

This gate does not authorize integration into `main`.

## Scope

Permitted work is limited to:

- current local verification against repository-owned synthetic fixtures;
- investigation of a first failure;
- narrowly scoped non-production test infrastructure, formatting, or
  documentation correction if required;
- this ExecPlan, final verification evidence, project status, and genuinely
  required governance updates; and
- one reviewed local sealing commit after a strict PASS.

Production code remains frozen unless a separately identified and authorized
non-production-only correction proves necessary. Any production Critical,
High, or blocking Medium result makes the gate fail and stops broad repair.

## Non-goals

- No Phase 5 capability, LLM, Agents SDK, shell, target command, Git delivery,
  customer repository, or production deployment.
- No CreativeDeploy or Customer 0 access, mount, scan, build, test, read,
  write, cleanup, or runtime use.
- No `main` checkout, fast-forward, merge, push, pull request, tag, release, or
  remote creation.
- No weakening, deletion, skip, or `xfail` of a security test.
- No rewrite of any historical audit or re-audit FAIL.

## Constraints and stop conditions

- Stop before overwriting work if the exact candidate, ancestry, protected
  refs, worktree, index, untracked inventory, or remote boundary cannot be
  reconciled.
- Preserve the first failure, actual exit code, root cause, correction, and
  focused/final reruns.
- A production Critical, High, blocking Medium, source mutation, production
  drift, unexplained residual resource, mandatory command failure, or
  undisclosed blocker makes the final decision FAIL.
- Use PostgreSQL, the real local Web/API/Runner stack, and generated synthetic
  repositories where required; do not substitute mocks for an integration
  claim.
- Cleanup only exact repository-owned disposable resources. Unknown state is
  preserved and reported.
- Do not repeat an expensive sub-gate already covered by the successful final
  aggregate unless a focused failure investigation requires it.

## Trusted baseline

The pre-branch investigation confirmed:

- the instructed repository and Git top level are the same real repository;
- starting branch
  `audit/phase-4-manifest-budget-reaudit-max` was clean at the exact candidate;
- `main` remains the Phase 3 commit above;
- Round 4 is the candidate's exact sole parent and the range contains one
  commit;
- the complete ref-reachable Phase 4 range contains ten single-parent commits
  from `main` through implementation, audit, four repairs, and four independent
  audit checkpoints;
- no remote, stash, tag, replace ref, submodule, shallow history, extra
  worktree, staged file, tracked diff, or untracked file existed;
- five unreachable commits are reconciled by repository reflogs as pre-amend
  predecessors; the latest `2bd9290...` has the same Round 4 parent as the
  candidate and differs from the final candidate only in two audit documents,
  with no production diff;
- the integration branch did not pre-exist and was created without force from
  the exact candidate; and
- the frozen production boundary contains 72 tracked files with current
  content-manifest SHA-256
  `09f951a175c3d9bb55ce109c229c0468dabbd287b8b734d75c14958afee3e43b`
  and Git-tree-listing SHA-256
  `048b8a302fff5a9c2edab82ca4fbc4dba4b1a2028da9c7ed3cbff53180305424`.

The protected-head set before branch creation has SHA-256
`50f62c7e5a796cec490bedb1f67f1f3c06dcb96ada364b21afdd4e8fd62e6650`.
The only permitted ref addition before sealing is the integration branch.

## Verification coverage map

| Required area                                       | Final `make verify` coverage | Separate final action                                 |
| --------------------------------------------------- | ---------------------------- | ----------------------------------------------------- |
| Contract, format, lint, Python/TypeScript typecheck | Covered                      | None                                                  |
| API/Runner/Protocol/Web tests and coverage          | Covered                      | Record exact totals                                   |
| Production Web build                                | Covered                      | Record routes/build result                            |
| Compose rendering                                   | Covered                      | Runtime topology is separate                          |
| PostgreSQL migration roundtrip                      | Covered                      | Record upgrade/downgrade result                       |
| Historical Phase 4 Finding regressions              | Covered                      | Record exact current counts                           |
| Source invariance                                   | Covered                      | Repeat only final hashes, not the expensive lifecycle |
| Workspace security and repair matrix                | Covered                      | None                                                  |
| Real Web/API/PostgreSQL/Runner Playwright           | Covered                      | Record both viewports and accessibility               |
| Workspace Chaos                                     | Covered                      | None                                                  |
| Security scanners and deterministic Eval            | Covered                      | Check skip/xfail inventory                            |
| Git diff check                                      | Covered                      | Repeat after final documentation                      |
| Named Runner and Workspace smoke targets            | Not covered                  | Run both against an isolated fresh Compose project    |
| Runner offline/requeue Chaos                        | Not covered                  | Run `make runner-chaos-check` once                    |
| Live Docker isolation and ownership-key probes      | Not covered                  | Run one exact disposable runtime inspection           |
| Final resource cleanup                              | Partially covered by traps   | Inspect exact Compose labels/resources                |
| Production/protected-ref/worktree closure           | Not covered                  | Repeat exact hashes and Git inventory                 |

## Current progress

### 2026-07-29

- DONE: independently reconcile the full Git candidate, branch, ancestry,
  parents, refs, reflogs, unreachable pre-amend objects, worktree, index,
  untracked, remote, stash, tags, and production boundary.
- DONE: read the repository governance, Make/CI, complete Phase 4 audit,
  re-audit, repair, verification, architecture, ADR, threat-model, protocol,
  permissions, and recovery material.
- DONE: create `integration/phase-4-final-gate` from the exact candidate.
- DONE: inspect the initial Docker/port/resource state and run the final
  aggregate once; `make verify` exited `0`.
- DONE: run the uncovered named smoke targets, Runner Chaos gate, and live
  Docker isolation probes.
- DONE: verify exact test-owned cleanup and frozen source, production, and
  protected-ref boundaries.
- DONE: write final evidence/status, review the complete diff, and decide
  PASS.
- DONE: authorize one local sealing checkpoint; its resulting hash and
  post-commit clean-state proof belong in the final handoff because a commit
  cannot embed its own hash.

## Decisions

1. **Use the full budget re-audit checkpoint as the integration baseline.**
   Audit tests and closure evidence remain in the integrated candidate.
2. **Treat five pre-amend commits as explained object history, not candidate
   ancestry.** Reflogs, same-parent checks, and production diffs reconcile
   them; no object is pruned.
3. **Use one final successful aggregate.** Focused checks are reserved for
   investigating an actual failure; expensive passing targets are not run
   twice.
4. **Supplement only uncovered capabilities.** Named Runner/Workspace smoke,
   Runner offline/requeue Chaos, live Docker kernel/runtime isolation, exact
   cleanup, and Git/production closure are outside `make verify`.
5. **Freeze production.** Final gate documents may change; production source,
   migrations, contracts, Compose, infra, and Dockerfiles must retain the
   candidate content unless an authorized stop-and-report decision says
   otherwise.

## Risks

| Risk                                         | Impact   | Mitigation / next action                                                 |
| -------------------------------------------- | -------- | ------------------------------------------------------------------------ |
| Stale Docker state masks a current failure   | High     | Initial inventory, isolated project names, live IDs, final label cleanup |
| Aggregate failure loses its first evidence   | High     | Capture complete terminal output and exit before focused investigation   |
| Documentation formatting forces full rerun   | Medium   | Format/check documents before the one final aggregate                    |
| Runtime probe mutates unknown resources      | Critical | Inspect exact candidate-owned projects; preserve unknown state           |
| Production changes during evidence writing   | Critical | Repeat 72-file content/tree hashes and exact candidate diff              |
| New branch obscures protected-ref comparison | Medium   | Compare the pre-branch ref set excluding only the integration branch     |

## Discoveries

- `make verify` includes the expensive real E2E and Workspace Chaos targets,
  so they must not be rerun separately after a successful aggregate.
- `make verify` does not include `runner-chaos-check`, full live Docker
  identity/mount/network/resource probes, or final label-based residue checks.
- The migration target performs base/upgrade/base/upgrade on real PostgreSQL.
- The E2E wrapper builds and runs the real Web/API/PostgreSQL/Runner stack,
  uses desktop and 390-pixel Chromium projects, and fingerprints both source
  fixtures before and after.
- The final aggregate passed on its single run: 161 Python tests at 81.79%
  coverage, 41 Web tests, the production build, real PostgreSQL migrations,
  14 Playwright cases, Workspace Chaos, security, and Eval.
- The uncovered Runner Chaos target passed offline, expiry, requeue, stale
  fencing, recovery, final-success, and source-integrity assertions.
- The first Workspace smoke attempt used the pre-existing default database
  and failed closed with `workspace_state_invalid`. The default state was
  preserved. Both named smoke targets then passed unchanged in a disposable
  project with fresh PostgreSQL state; the Workspace was rolled back,
  discarded, and removed while source remained invariant.
- A live disposable Runner proved effective UID/GID 10001, read-only root and
  source, dropped capabilities, no-new-privileges, declared resource limits,
  no published port, internal API-only reachability, blocked external TCP,
  mode-0600 ownership key, and exact fixture invariance.
- The first live probe assumed Docker would render the numeric image user.
  Docker rendered the declared name `runner`; a focused diagnostic confirmed
  the topology and the corrected probe retained the effective numeric
  UID/GID assertion.

## Verification ledger

Detailed commands, exits, counts, first failures, runtime facts, and final
classification belong in
`docs/evidence/phase-4-final-integration-gate-verification.md`.

| Check                               | Status                                 |
| ----------------------------------- | -------------------------------------- |
| Git and history preflight           | VERIFIED                               |
| Production baseline freeze          | VERIFIED                               |
| Docker/port/residue preflight       | VERIFIED                               |
| Final `make verify`                 | VERIFIED — exit 0                      |
| Named Runner and Workspace smoke    | VERIFIED — both exit 0                 |
| Runner Chaos                        | VERIFIED — exit 0                      |
| Live Docker isolation               | VERIFIED — exit 0                      |
| Final source/production/ref closure | VERIFIED                               |
| Final documentation and diff review | VERIFIED                               |
| Sealing checkpoint                  | AUTHORIZED — hash in final Git handoff |

## Rollback

- Stop only exact integration-owned Compose projects through their declared
  Compose down commands.
- Preserve unknown containers, networks, volumes, Workspaces, mirrors,
  registries, and source data.
- Before the sealing commit, reverse only final-gate documentation through
  targeted patches if the user requests it. Never reset, clean, stash, prune,
  or force-update another ref.
- The integration branch remains outside `main`; no external state exists to
  roll back.

## Completion conditions

PASS requires every condition in the work order, including:

1. final `make verify` exit 0 with all named engineering, PostgreSQL, browser,
   Runner, Workspace, Chaos, security, Eval, and source gates passing;
2. the uncovered Runner Chaos and live Docker isolation checks pass;
3. no Critical, High, blocking Medium, hidden skip/xfail, residual marker
   resource, source drift, production drift, or undisclosed blocker exists;
4. final documentation distinguishes historical FAIL, remediation,
   independent closure, and the current final decision;
5. `main` and every pre-existing protected ref are unchanged;
6. remote, push, merge, PR, tag, Customer 0, CreativeDeploy, production, and
   Phase 5 actions remain absent;
7. one local commit named
   `chore: seal phase 4 isolated workspace gate` contains only authorized
   final-gate material; and
8. the post-commit worktree, index, and untracked inventory are clean.

## Outcome and follow-ups

`PHASE 4 FINAL INTEGRATION GATE PASS — READY FOR USER-AUTHORIZED MAIN INTEGRATION`

All current local mandatory gates passed. Historical audit FAIL reports remain
unchanged, and the successful current closure evidence is recorded separately
in
`docs/evidence/phase-4-final-integration-gate-verification.md`.

The local sealing checkpoint uses the required subject
`chore: seal phase 4 isolated workspace gate`. Its resulting hash and
post-commit clean-state proof are reported in the final handoff. The next
action remains a separate explicit user authorization to integrate into
`main`.
