# Phase 4 Security Remediation Round 4 — Expanded Manifest Entry Budget

- Started: 2026-07-29T13:28:31+08:00
- Branch: `fix/phase-4-security-remediation-4`
- Base / single-finding audit:
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8`
- Round 3 repair:
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Historical Security Gate: **FAIL — PRESERVED**
- Current status:
  `REMEDIATION ROUND 4 COMPLETE — READY FOR INDEPENDENT BUDGET RE-AUDIT`

## Goal

Bound every path entry expanded by the source-less checkout-manifest walk,
including each path through a shared Git tree, before an over-limit entry is
created or its content is processed. The exact boundary is inclusive:
`entry_count == limit` succeeds and the next entry fails with typed
`mirror_budget_exceeded`.

The completed candidate may be handed only to a fresh independent budget
re-audit. This repair cannot declare the Security Gate PASS.

## Scope

Permitted implementation changes are limited to:

- source-less checkout-manifest materialization and its direct budget logic;
- directly related Runner tests;
- this ExecPlan;
- `docs/evidence/phase-4-security-remediation-4-verification.md`;
- `docs/status/project-status.md`; and
- security, threat-model, or architecture text only if the enforced boundary
  needs clarification.

## Non-goals

- No API route, database model, migration, Side-effect Permit production
  logic, discard/ownership, process-group timeout, Web, Compose, CI, Phase 5,
  LLM, Agents SDK, or Git-delivery change.
- No CreativeDeploy or Customer 0 access.
- No full `make verify`, Web E2E, full Chaos, complete Docker Gate, merge,
  remote, push, pull request, or tag.
- No deletion, weakening, skip, or `xfail` of the permanent independent audit
  test or any historical FAIL evidence.

## Constraints and safety

- Operate only in `/Users/danke/Developer/VisualEngineer`.
- Stop without overwriting work if the verified base, protected refs, clean
  state, or scope cannot be preserved.
- Count every actual expanded manifest path independently, including repeated
  shared subtrees, nested directories, regular files, symlinks, and inert
  gitlinks.
- Fail before constructing an over-limit manifest entry and before reading or
  hashing the over-limit file or symlink payload.
- Do not first build an unbounded complete list and check its final length.
- Preserve raw path bytes, type, Git mode, size, SHA-256, symlink, inert
  gitlink, exact object closure, replacement defenses, source invariance,
  quarantine/recovery, process-group timeout, and Permit semantics.

## Current progress

### 2026-07-29

- DONE: verify the exact repository, starting audit branch, audit `HEAD`,
  clean tracked/index/untracked state, empty remote, main hash, audit ref, and
  commit ancestry.
- DONE: confirm audit commit
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8` has the sole exact parent
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`.
- DONE: create `fix/phase-4-security-remediation-4` without force from the
  exact audit commit.
- DONE: read all mandatory governance, audit, evidence, plan, production, and
  directly related test material.
- DONE: run the unchanged shared-tree budget reproduction twice.
- DONE: preserve the stable pre-fix result: limit `5`, returned manifest
  entries `8`, exit `1` twice, one failed test each time.
- DONE: implement immediate expanded-entry charging and additive
  boundary/regression tests.
- DONE: run every accelerated verification target named in the work order.
- DONE: update security, architecture, evidence, and project status.
- PENDING: inspect the final exact diff and protected refs, create one local
  commit, and verify the clean worktree/index in the external handoff.

## Decisions

1. **Use the existing tree-entry limit as the manifest-entry limit.** The
   configured field already governs the independent Workspace scanner and the
   audit reproduction. No configuration or general budget framework is
   needed.
2. **Charge during recursive manifest construction.** A shared mutable count
   is passed through every path expansion. A leaf atomically reserves itself
   and every pending ancestor directory before content work; this prevents
   directory accounting from becoming a late post-child check.
3. **Preserve empty-tree semantics.** A tree path is charged only when its
   recursive result contains an actual materialized child, matching the
   existing omission of Git-unmaterialized empty directories.
4. **Keep the independent test unchanged.** Add implementation regressions in
   the ordinary Workspace tool test suite and use the permanent audit test
   only as an unchanged acceptance reproduction.

## Risks

| Risk                                        | Impact                         | Mitigation / next action                                                |
| ------------------------------------------- | ------------------------------ | ----------------------------------------------------------------------- |
| Shared trees are still charged once         | Blocking Medium remains        | Assert repeated paths exhaust the expanded counter.                     |
| The over-limit blob is read or hashed first | Resource boundary remains late | Spy on manifest-phase object reads and require rejection first.         |
| Exact-limit behavior becomes off by one     | Valid repositories rejected    | Test exact `count == limit` success and `limit + 1` typed failure.      |
| Entry semantics drift                       | Workspace proof regression     | Cover regular, symlink, gitlink, modes, size, digest, and normal proof. |
| Manager failure leaves usable state         | Recovery/integrity regression  | Assert no Workspace, registry, ownership, or sibling/source mutation.   |
| Scope expands into historical findings      | Governance failure             | Review tracked and untracked inventory against the explicit allowlist.  |

## Discoveries

- `SourceObjectClosure._walk_tree` charges each unique tree object only once
  because the cached-height path returns before the unique entry counter.
- Before the repair, `SourceObjectClosure._walk_checkout_manifest` expanded
  the same tree once per path without an expanded-entry counter.
- `GitOperations._copy_source_objects` constructs the expected manifest after
  closure collection but before object materialization.
- The later descriptor-rooted Workspace scanner has an expanded-entry
  counter, but that enforcement occurs only after Git has created a
  Workspace and therefore cannot protect expected-manifest construction.

## Verification

| Check                                                  | Status                         |
| ------------------------------------------------------ | ------------------------------ |
| Git baseline and repair branch                         | VERIFIED                       |
| Pre-fix shared-tree reproduction, first run            | CONFIRMED FAIL — exit 1; 8 > 5 |
| Pre-fix exact rerun                                    | CONFIRMED FAIL — exit 1; 8 > 5 |
| Post-fix permanent reproduction                        | VERIFIED — 1 PASS              |
| Additive budget regressions                            | VERIFIED — 5 PASS              |
| Complete blocking reproduction file                    | VERIFIED — 12 PASS             |
| Manifest/object-closure focus                          | VERIFIED — 24 PASS             |
| `make source-invariance-check`                         | VERIFIED — PASS                |
| `make workspace-security-check`                        | VERIFIED — 63 PASS + STATIC    |
| `make test-runner`                                     | VERIFIED — 82 PASS             |
| `make format-check`                                    | VERIFIED — FINAL PASS          |
| `make lint`                                            | VERIFIED — PASS                |
| `make typecheck`                                       | VERIFIED — PASS                |
| `make test`                                            | VERIFIED — 160 + 41 PASS       |
| `git diff --check`                                     | VERIFIED — PASS                |
| Full `make verify` / E2E / Chaos / Docker / Customer 0 | NOT RUN — OUT OF SCOPE         |

## Rollback

- Keep changes isolated on the dedicated repair branch.
- Do not reset, clean, stash, prune, force-update, or overwrite refs.
- If the scoped implementation cannot satisfy the permanent reproduction and
  additive regressions, preserve evidence and stop without expanding scope.
- Focused tests use only temporary synthetic repositories managed by pytest.

## Completion conditions

1. Every expanded manifest path is charged, with exact-limit success and
   pre-entry typed rejection of the next path.
2. Shared, deep, wide, and repeated trees cannot bypass the bound.
3. Regular, symlink, gitlink, directory, raw-path, mode, size, and digest
   semantics remain exact.
4. Rejection creates no registered or usable Workspace and preserves source,
   mirror/sibling deletion boundaries, Permit count, and recovery semantics.
5. The permanent audit reproduction and every accelerated required target
   pass in the final worktree.
6. Historical FAIL evidence and protected refs remain unchanged.
7. One scoped local commit exists; remote, push, merge, PR, tag, Customer 0,
   CreativeDeploy, and Phase 5 actions remain absent.
8. The final worktree and index are clean.

## Outcome and follow-ups

`REMEDIATION ROUND 4 COMPLETE — READY FOR INDEPENDENT BUDGET RE-AUDIT`

The only eligible follow-up is an independent narrow budget re-audit. A full
integration `make verify` remains deferred until that review passes. This
implementer record does not declare the Security Gate PASS.
