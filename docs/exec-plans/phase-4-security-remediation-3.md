# Phase 4 Security Remediation Round 3 — Git Replacement Metadata

- Started: 2026-07-29T02:20:38+08:00
- Branch: `fix/phase-4-security-remediation-3`
- Base / focused re-audit checkpoint:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`
- Candidate parent / Round 2 repair:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Historical Security Gate: **FAIL — PRESERVED**
- Current status:
  `REMEDIATION ROUND 3 COMPLETE — READY FOR INDEPENDENT SINGLE-FINDING RE-AUDIT`

## Goal

Close only `VE-P4-FREAUD-001` / `VE-P4-AUD-001`: prevent source or
pre-existing Runner mirror Git replacement metadata from changing the bytes
materialized for an exact approved revision.

The candidate must:

1. initialize Runner-owned mirrors from an explicitly empty trusted template;
2. accept no source-provided mirror metadata or extra ref namespace;
3. disable replacement interpretation in both every Git command and its fixed
   environment;
4. independently compare the descriptor-rooted no-follow Workspace checkout
   manifest with the source-less parser's authorized commit-tree manifest; and
5. preserve the previously verified object-closure, Permit, discard,
   process-group, source-invariance, and isolation boundaries.

Completion can make this branch ready only for a new independent
single-finding read-only re-audit. It cannot decide the Security Gate.

## Scope

Permitted production changes are limited to:

- `apps/runner/src/visual_engineer_runner/git_object_store.py`;
- `apps/runner/src/visual_engineer_runner/git_ops.py`;
- `apps/runner/src/visual_engineer_runner/workspace_manager.py`; and
- directly necessary Runner configuration only if a bounded proof cannot be
  expressed with the existing object/tree budgets.

Permitted supporting changes are limited to directly related Runner security
tests, object-closure/workspace tests, this plan, Round 3 verification
evidence, project status, and directly affected ADR/security/threat-model
statements.

## Non-goals

- No redesign of Phase 4 or general Git feature.
- No Side-effect Permit, discard/ownership, process-group timeout, API route,
  database model/migration, Web, protocol, Phase 5, LLM, Agents SDK, Git
  delivery, deployment, CI, remote, push, pull request, merge, or tag change.
- No target-repository build/test/command and no customer repository access.
- No deletion, weakening, skip, `xfail`, or implementation-specific rewrite
  of the independent focused re-audit test.
- No full browser/E2E/Chaos or repeated aggregate `make verify`; final
  aggregate verification remains for post-re-audit integration closure.

## Constraints and safety

- Operate only in `/Users/danke/Developer/VisualEngineer`.
- Do not access, mount, scan, read, write, build, test, or clean
  CreativeDeploy.
- Preserve all historical audit and re-audit FAIL reports unchanged.
- Source remains a non-Git-execution target. Only the source-less parser may
  read its exact authorized object closure.
- Destination metadata that cannot be proven to match the minimal Runner
  template and empty ref namespace fails closed before checkout.
- Workspace semantic proof uses descriptor-relative no-follow traversal and
  cannot use Git output as its sole content authority.
- A failed semantic proof preserves unexpected bytes through isolation rather
  than broad deletion.
- Create at most one local checkpoint and only after the complete authorized
  verification sequence, scope review, protected-ref comparison, and staged
  diff review.

## Trusted baseline

The following are **CONFIRMED** before the first edit:

- repository root: `/Users/danke/Developer/VisualEngineer`;
- starting branch:
  `audit/phase-4-security-focused-reaudit-max`;
- starting HEAD:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`;
- the checkpoint's sole parent:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`;
- checkpoint changes are limited to two audit-test files and four
  audit/evidence/plan/status documents;
- main and every disclosed protected Phase 4 ref match the focused re-audit
  report;
- tracked worktree, index, untracked inventory, stash, remote, and tag
  inventories are empty;
- the Round 2-to-focused-checkpoint diff passes `git diff --check`;
- this Round 3 branch did not pre-exist and was created directly from the full
  focused checkpoint hash; and
- no CreativeDeploy host path or Compose/config mount is present. The
  repository's historical Customer 0 script contains only a static API
  payload and opaque container locator and was not run.

The frozen production boundary contains 72 tracked files under
`apps/api/src`, `apps/runner/src`, `packages/runner-protocol/src`,
`apps/api/alembic`, `compose.yaml`, `infra`, and the API/Runner Dockerfiles.

| Evidence                                      | SHA-256                                                            |
| --------------------------------------------- | ------------------------------------------------------------------ |
| Initial 72-file current-content manifest      | `3ca1448901c572da082a75fb002da81b73b347974c753e8ef7b28f5a167787d3` |
| Focused-checkpoint Git-tree listing           | `be07a14623a65593d5f0c8ddd1a22219b3b7aa3f30f8ee7794206282f312c707` |
| Initial three-file source-adapter content set | `80770c5cb290fbaa1d83906681212d931329667677494a78c2e05dac7793012d` |

## Current progress

### 2026-07-29

- DONE: read the complete Round 3 work order and identify the real repository.
- DONE: independently reconcile the required Git baseline, exact parent,
  ancestry, branch/ref, diff, remote, stash, tag, untracked, and worktree
  facts.
- DONE: create `fix/phase-4-security-remediation-3` from the exact focused
  re-audit checkpoint.
- DONE: read `AGENTS.md`, `SECURITY.md`, `PLANS.md`, project status, the full
  focused audit/report/plan/evidence, the preserved independent test, Git
  source adapter/object store/subprocess/worktree paths, directly related
  tests, ADRs, and threat models.
- DONE: run the unchanged independent
  `test_focused_existing_mirror_packed_replace_cannot_change_checkout` twice.
  Both runs produced `1 failed`; the recorded rerun exited `1`.
- DONE: implement empty-template/detached-HEAD/empty-ref mirror validation,
  dual Git replacement disabling, source-less authorized checkout manifest,
  descriptor-rooted no-follow Workspace manifest equality, and mismatch
  isolation.
- DONE: add the authorized permanent regression matrix without changing the
  independent focused test.
- DONE: create Round 3 evidence and update active plan, status, ADR,
  architecture, security policy, and threat models without altering
  historical FAIL.
- DONE: run the unchanged focused test, new regressions, complete blocking
  file, Git object/ref/manifest focus, source invariance, Workspace security,
  and complete Runner/Protocol tests successfully.
- DONE: run repository-wide format, lint, typecheck, and test gates.
- DONE: inspect exact diff, final source/unrelated-production invariance,
  protected refs, remote/stash/tag inventories, and disposable test-service
  cleanup before staging.
- DONE: stage the exact reviewed paths and create the one local checkpoint.
  Record its final hash and clean worktree/index externally because the
  checkpoint cannot contain its own hash.

## First failure

Command:

```bash
/opt/homebrew/bin/uv run pytest \
  apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py::test_focused_existing_mirror_packed_replace_cannot_change_checkout \
  --no-cov -q
```

Observed twice before production changes:

```text
actual:   "original\n"
expected: "approved second revision\n"
1 failed
EXIT_CODE: 1
```

The approved revision, requested `HEAD`, and exact reachable object set remain
unchanged. A packed `refs/replace/<approved>` entry in the existing mirror
causes Git checkout to materialize the approved commit's ancestor instead.

## Decisions

1. **Use an explicitly empty Git init template.** New mirrors will not inherit
   host/system template hooks, attributes, logs, refs, or other metadata.
2. **Use no mirror refs.** A detached mirror `HEAD` identifies the exact
   authorized object ID; loose refs and `packed-refs` are outside the minimal
   accepted namespace.
3. **Reject, do not normalize, unprovable existing metadata.** This preserves
   tamper evidence and avoids silently rewriting a destination whose ownership
   or provenance cannot be established.
4. **Disable replacements twice.** Every fixed Git invocation uses the
   command-level no-replacement option and the fixed environment's
   replacement-disable variable.
5. **Prove checkout bytes outside Git interpretation.** The source-less object
   parser derives path/type/Git-mode/size/SHA-256 entries. A descriptor-rooted
   no-follow scanner independently derives the Workspace equivalent and
   requires exact equality before ownership/registry creation.
6. **Isolate a semantic mismatch.** A newly created but unprovable checkout is
   atomically renamed inside the Workspace root to a non-addressable
   quarantine name; it is not recursively deleted.

## Risks

| Risk                                                    | Impact   | Mitigation / next action                                                                  |
| ------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------------- |
| Packed or loose ref representation escapes validation   | Critical | Enumerate raw `refs` and reject any `packed-refs`; do not ask Git to define allowed refs. |
| Local/host config re-enables replacement interpretation | Critical | Fixed command option plus fixed environment; retain exact managed config validation.      |
| Git reports approved HEAD but checkout bytes differ     | Critical | Independent source-parser versus descriptor-rooted Workspace manifest equality.           |
| Symlink, executable mode, empty tree, or gitlink gap    | High     | Model regular/symlink/Git-mode semantics and inert empty gitlink materialization tests.   |
| Failed proof deletes unexpected bytes                   | High     | Atomic same-root quarantine without recursive deletion.                                   |
| New proof exceeds existing object/tree budgets          | High     | Reuse already enforced object, byte, tree-depth, entry, and reference bounds.             |
| Regression disturbs discard/timeout/Permit boundaries   | Critical | Run preserved blocking file and complete directly related suites in the ordered gate.     |

## Discoveries

- Existing validation checks `refs/replace` only as a loose path and does not
  inspect or reject `packed-refs`.
- Existing fixed Git commands omit both `--no-replace-objects` and
  `GIT_NO_REPLACE_OBJECTS=1`.
- Exact destination object-ID equality cannot detect replacement when both
  commits are already inside the approved ancestry closure.
- `git init --bare --template=` produces only `HEAD`, `config`, empty
  `objects/{info,pack}`, and empty `refs/{heads,tags}` before objects are
  materialized.
- A detached checkout of an inert gitlink materializes an empty directory and
  does not open or import the gitlink target commit.

## Verification

No remediation claim becomes `VERIFIED` until the exact command has run in
this branch and exited zero. Detailed commands, exit codes, counts, manifest
digests, failure/rerun chronology, and invariant checks belong in
`docs/evidence/phase-4-security-remediation-3-verification.md`.

Current state:

| Check                                        | Status                           |
| -------------------------------------------- | -------------------------------- |
| Git baseline and Round 3 branch              | VERIFIED                         |
| Original independent packed-replacement test | PASS after preserved FAIL        |
| Production repair                            | IMPLEMENTED                      |
| Permanent regression matrix                  | VERIFIED — 6 PASS                |
| Workspace semantic manifest proof            | VERIFIED — exact digest equality |
| Source invariance                            | VERIFIED                         |
| Full related Runner/Protocol suites          | VERIFIED — 75 PASS               |
| Format/lint/type/test                        | VERIFIED                         |
| Aggregate `make verify`                      | NOT RUN — RESERVED FOR RE-AUDIT  |
| Independent Security Gate                    | FAIL — HISTORICAL, NOT REDECIDED |

## Rollback

- All work remains isolated on
  `fix/phase-4-security-remediation-3`.
- Do not reset, clean, stash, prune, force-update, or overwrite any ref or user
  work.
- Stop only exact disposable repository-owned test services if any focused
  check starts them.
- If a new Critical/High outside this finding is reproduced, preserve the
  smallest regression and stop without expanding the production repair.
- A semantic mismatch quarantines the new Workspace bytes; operator recovery
  remains manual and no authority-bypassing garbage collector is introduced.

## Completion conditions

1. The unchanged independent packed-replacement test passes.
2. Packed and loose replacement refs, source metadata non-import, pre-existing
   destination refs, fixed Git no-replacement behavior, semantic mismatch,
   normal checkout, exact manifest equality, rejection-path source
   invariance, and preserved blocker regressions all pass.
3. Mirror metadata is generated from the empty managed template and final
   accepted mirrors contain no loose or packed refs.
4. Every Runner-owned Git subprocess has both no-replacement defenses.
5. Workspace ownership/registry creation occurs only after exact independent
   manifest equality.
6. Ordered focused/complete related checks plus `make format-check`,
   `make lint`, `make typecheck`, `make test`, and `git diff --check` exit
   zero with recorded counts.
7. Only authorized production/test/document paths differ; protected refs,
   main, source fixtures, and unrelated production paths remain unchanged.
8. One local checkpoint uses
   `fix(security): reject Git replacement metadata in phase 4 mirror`.
9. Final worktree and index are clean; no remote, push, merge, PR, tag,
   CreativeDeploy access, target command, or Phase 5 action occurred.

## Outcome and follow-ups

All local completion conditions, including the one-commit checkpoint, have
passed. The checkpoint hash and final clean worktree/index are recorded
externally because the commit cannot embed its own final hash.

`REMEDIATION ROUND 3 COMPLETE — READY FOR INDEPENDENT SINGLE-FINDING RE-AUDIT`
