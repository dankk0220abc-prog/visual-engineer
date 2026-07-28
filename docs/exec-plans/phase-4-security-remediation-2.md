# Phase 4 Security Remediation Round 2

- Started: 2026-07-28T23:43:08+08:00
- Branch: `fix/phase-4-security-remediation-2`
- Repair base / independent re-audit:
  `b457b614bde6630fb50ff9546c92a4d6925ad38a`
- First repair:
  `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c`
- Original audit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4 implementation:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Independent Security Gate at start: **FAIL**
- Status:
  `REMEDIATION ROUND 2 COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`

## Goal

Close only the three independently reproduced Phase 4 production defects and
complete the missing real-PostgreSQL Side-effect Permit closure matrix:

1. import only the exact authorized revision's validated reachable Git object
   closure;
2. require trusted signed terminal proof before treating missing registry and
   Workspace root as an idempotent discard success;
3. enforce a monotonic deadline over the complete subprocess group even after
   its leader exits; and
4. independently exercise the full Side-effect Permit concurrency,
   revocation, fencing, and crash-retry matrix, repairing only defects inside
   that Finding if current tests expose one.

The implementer cannot decide the Security Gate. The strongest possible local
outcome is:
`REMEDIATION ROUND 2 COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`.

## Scope

Production and permanent regressions may change only where necessary for:

- `VE-P4-AUD-001` / `VE-P4-REAUD-001`: source object closure and mirror
  identity/budget validation;
- `VE-P4-AUD-003` / `VE-P4-REAUD-002`: authenticated pending-discard
  completion, recovery, quarantine, and strict idempotency;
- `VE-P4-AUD-005` / `VE-P4-REAUD-003`: complete process-group lifetime,
  timeout, termination, kill, reap, pipe, and output-bound handling; and
- `VE-P4-AUD-002`: real PostgreSQL Side-effect Permit closure evidence and
  any narrowly proven Permit defect.

Permitted supporting work is limited to additive regressions, exact generated
contracts or migrations if a proven in-scope production correction requires
them, the specified ExecPlan/evidence/status documents, and directly affected
architecture/security/runbook material.

## Non-goals

- No feature expansion, target-repository command, shell, build/test executor,
  LLM, Agents SDK, Git delivery, commit/push/PR capability, deployment, or
  Phase 5 work.
- No CreativeDeploy or other customer-repository access, mount, scan, read,
  write, build, test, or cleanup.
- No merge, remote, push, pull request, tag, or modification of `main`, Phase
  4, original-audit, first-repair, or re-audit refs.
- No rewrite of either preserved audit FAIL.
- No claim of hostile multi-tenant, hostile-code, production, remote-CI, or
  Security Gate safety.

## Constraints and safety

- Stop on baseline drift, dirty or concurrent user changes, unknown ownership,
  a new out-of-scope Critical/High defect, source mutation, sibling mutation,
  or inability to prove exact cleanup ownership.
- Use only generated synthetic repositories and exact repository-owned
  disposable PostgreSQL/Compose resources.
- Never run Git against a source fixture or use it as a Git directory,
  worktree, object database, alternate, or fetch source.
- Preserve the independent re-audit tests and secure assertions. Do not add
  skips, `xfail`, weaker assertions, mock substitutes for required
  PostgreSQL/Docker/disk evidence, or cleanup that removes the object under
  test.
- Record every first failure with command, exit code, expected/actual result,
  root cause, correction, focused rerun, and aggregate rerun.
- Create exactly one reviewed local checkpoint only after every mandatory
  local gate passes. No staging or checkpoint occurs before the final diff and
  evidence review.

## Trusted baseline

The following are **CONFIRMED** from current Git before the branch was created:

- repository root: `/Users/danke/Developer/VisualEngineer`;
- starting branch/HEAD:
  `audit/phase-4-security-reaudit-max` at
  `b457b614bde6630fb50ff9546c92a4d6925ad38a`;
- exact linear ancestry:
  `7590f9d` -> `53dc2f5` -> `a560509` -> `e3d6530` -> `b457b61`;
- the re-audit commit's sole parent is the first repair;
- the re-audit commit changes only one audit test and audit/status documents;
- `main` remains the Phase 3 commit;
- tracked worktree, index, and untracked inventory were clean;
- no remote, stash, tag, extra worktree, target repair branch, or undisclosed
  ref was present; and
- base Compose rendering contains no CreativeDeploy source.

The new branch was created directly from the full re-audit hash and initially
remained clean.

## Current progress

### 2026-07-28

- DONE: read the complete remediation work package.
- DONE: compare the desktop attachment workspace with the instructed real
  repository and select only the real repository.
- DONE: execute the required Git baseline, ancestry, parent, diff, ref,
  remote, stash, worktree, and untracked checks.
- DONE: create `fix/phase-4-security-remediation-2` from the exact re-audit
  checkpoint without changing another ref.
- DONE: read all required audit, repair, re-audit, ADR, architecture,
  threat-model, runbook, protocol, production, migration, and test sources.
- DONE: ran the unmodified complete re-audit test file; it produced the exact
  preserved baseline `3 failed, 4 passed` with exit 1.
- DONE: implemented and narrowly verified the three confirmed production
  remediations without editing the re-audit assertions.
- DONE: added and ran the real-PostgreSQL Permit closure matrix, including
  independent concurrent sessions and disk-before-database crash/retry.
- DONE: reran the combined repair gate: Runner/Protocol `59 passed`,
  PostgreSQL Workspace API `12 passed`, source invariance PASS, and the
  checker reports `independent_gate=FAIL_PRESERVED`.
- DONE: ran every named non-aggregate Make gate, including format, lint,
  typecheck, contracts, test, build, migration, security, Eval, E2E, both
  smoke targets, and both chaos targets.
- DONE: captured live Docker isolation evidence from a uniquely named
  Round-2-only Compose project, then removed its exact containers, volumes,
  and networks and verified zero residue.
- DONE: updated only affected architecture, security, recovery, status,
  evidence, and planning documents.
- DONE: the first post-documentation aggregate stopped at Markdown formatting;
  after the recorded correction, the complete `make verify` rerun exited 0.
- DONE: final diff review found and repaired one in-scope pack-directory
  enumeration budget gap; its first failure and focused/full subsystem reruns
  are recorded below.
- DONE: the post-correction complete `make verify` exited 0.
- FINAL HANDOFF: create the one authorized local checkpoint, recheck all
  protected refs, and verify the clean worktree/index.

## Decisions

1. **Use the exact re-audit checkpoint as both test source and repair base.**
   This preserves the independently authored secure expectations in the
   branch history.
2. **Treat all prior green totals as historical only.** Every claimed result
   must be rerun in this worktree.
3. **Keep object import independent of source Git.** The repair will parse and
   validate the supported loose/pack representation from no-follow
   descriptors and materialize only a computed reachable closure into
   Runner-owned objects.
4. **Do not infer discard completion from absence.** Only an authenticated,
   exact, unexpired, non-replayed pending-discard record coordinated with
   durable state may make an absent root idempotently complete.
5. **Model process completion as group/resource completion.** Leader exit is
   one observation, not the terminal condition while descendants, pipes, or
   the process group remain live.
6. **Validate an existing mirror before changing it.** A previously managed
   mirror must already have the exact mode-0600 managed config, object format,
   empty indirection locations, and authorized object set. Preparation never
   rewrites an unknown config into apparent validity.
7. **Make discard proof state monotonic relative to registry state.** A
   pending proof is accepted only with the exact pending registry operation;
   a completed replay additionally requires the exact completed operation,
   Permit lineage, absent expected root, absent original inode, and completed
   proof.
8. **Do not change Permit production behavior without a reproduced defect.**
   The real-PostgreSQL matrix confirmed the existing locked acquisition,
   terminal accounting, and retry ordering; Round 2 therefore adds permanent
   integration evidence only for `VE-P4-AUD-002`.

## Risks

| Risk                                                    | Impact   | Mitigation / next action                                                                               |
| ------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------ |
| Git parser accepts malformed or indirect object state   | Critical | strict type/length/hash/tree/depth/budget checks and additive malformed fixtures                       |
| Packed-object support copies extra objects              | Critical | select authorized object IDs first and extract only validated selected objects                         |
| Existing mirror object bypasses authorization or budget | Critical | validate identity/type/size/hash and include every destination object in budgets                       |
| Missing discard state is mistaken for completion        | High     | authenticated terminal proof plus database/local/root-identity consistency                             |
| Process-group cleanup kills a reused group              | High     | retain stable leader/group identity evidence and use conservative bounded checks                       |
| Permit matrix becomes nondeterministic                  | High     | independent PostgreSQL transactions, explicit barriers, bounded waits, and fresh observer transactions |
| Test cleanup reaches unrelated state                    | Critical | unique synthetic fixtures and exact owned-resource cleanup only                                        |

## Discoveries

- The independent re-audit's three secure assertions still target production
  paths in `git_ops.py` and `workspace_manager.py`; they have not been edited
  in this branch.
- The current adapter documentation claims an exact committed object closure,
  while the re-audit proves the first repair copies objects outside that
  closure.
- The current discard contract already names authenticated pending-discard
  evidence, but the registry-missing fallback does not enforce it.
- The current timeout contract is group-wide, while the collector uses leader
  state in a way that can terminate monitoring too early.
- Git pack/index parsing must validate both cryptographic trailers, the pack
  filename identity, index CRCs, object IDs/types/declared and decompressed
  sizes, OFS/REF delta chains, and tree/graph/reference budgets before
  Runner-owned loose-object materialization.
- A signed pending-discard proof is durable before registry pending state and
  deletion; the signed completed transition is durable after deletion and
  before the registry becomes terminal. This ordering covers both crash
  windows without treating bare absence as proof.
- A terminal registry row alone is insufficient for repeat discard: the
  completed proof and disk/root-inode facts are revalidated on every replay.
- The Side-effect Permit closure matrix found no new in-scope production
  defect. Real PostgreSQL rolled back the injected completion-event failure
  while the already committed disk write remained replayable without inode
  replacement or a second budget charge.
- The live Runner container has UID/GID `10001`, a read-only root filesystem
  and source bind, zero effective capabilities, no-new-privileges, no Docker
  socket, no published port, no default route, and API-only DNS on its
  internal control network. Its ownership key is a 32-byte regular file at
  the configured path with mode `0600` and owner `10001:10001`.

## Failure and correction ledger

| Time                          | Classification                          | Command / failure                                                                                                                                                 | Root cause                                                                                                                                                                                                                      | Correction and required rerun                                                                                                                                                                                               |
| ----------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| investigation                 | INVALID FIRST PATH                      | `wc -l .../20260728_0005_add_side_effect_permits.py` exited 1 because the file does not exist                                                                     | a historical description was mistaken for the real migration filename                                                                                                                                                           | `rg --files apps/api/alembic/versions` identified `20260728_0005_close_phase4_security_findings.py`; read the real file and retain this failure                                                                             |
| pre-repair reproduction       | EXPECTED PRODUCTION DEFECT BASELINE     | `/opt/homebrew/bin/uv run pytest apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py --no-cov -vv` exited 1 with exactly 3 failed and 4 passed | mirror import includes an unreachable source object; absent registry/root returns discard success without proof; leader exit lets group monitoring miss the deadline                                                            | preserve the unmodified assertions, repair the three production paths, rerun each focused test and the complete file                                                                                                        |
| focused static check          | IMPLEMENTATION DEFECT                   | targeted `ruff check` exited 1 with five `B904` findings in strict packed-ref parsing                                                                             | new fail-closed raises were nested under the packed-ref `FileNotFoundError` handler without an explicit exception cause                                                                                                         | add `from None` to intentional validation failures; targeted Ruff and mypy rerun exited 0                                                                                                                                   |
| source harness invocation     | INVALID COMMAND ENVIRONMENT             | direct `uv run python scripts/check_source_invariance.py` exited 1 with `ModuleNotFoundError: visual_engineer_runner`                                             | the repository target intentionally supplies the package `PYTHONPATH`; the direct command omitted it                                                                                                                            | run the declared `make source-invariance-check`; it exited 0 and reported source comparison PASS                                                                                                                            |
| source harness semantics      | IMPLEMENTATION / TEST ASSUMPTION DEFECT | the first closure-aware source harness run rejected its gitlink and a subsequent comparison rejected recompressed destination bytes                               | the first implementation chose rejection although the established fixture policy treats gitlink as inert metadata; valid Runner-owned loose materialization can use a different zlib encoding for the same canonical Git object | intermediate runs separated the fixture; the later E2E failure required final inert handling without target import/recursion, restored gitlink success coverage, and retained canonical-byte plus distinct-inode comparison |
| expanded Workspace regression | TEST HELPER DEFECT                      | an early expanded Workspace file run exited 1 with 44 passed and 1 failed                                                                                         | the new proof fixture did not retain the original signed pending proof required for its replay branch                                                                                                                           | retain and restore the exact proof in that test; later full-file reruns pass                                                                                                                                                |
| terminal replay regression    | TEST BASELINE DEFECT                    | `pytest apps/runner/tests/test_workspace_tools.py --no-cov -q` exited 1 with `46 passed, 1 failed`                                                                | the test captured mirror state before the legitimate first discard, so expected worktree-administration cleanup was misclassified as replay damage                                                                              | capture mirror state immediately after the authorized discard; focused rerun passed 1 and aggregate rerun passed 47                                                                                                         |
| formal full test              | IMPLEMENTATION DEFECT                   | first `make test` exited 2 after backend `142 passed, 1 failed`; single-object overflow returned `repository_unavailable` instead of `mirror_budget_exceeded`     | the loose-object decompression/declared-size branch used the generic source failure classification                                                                                                                              | classify an actual configured single-object overflow as the stable budget failure; focused rerun passed and full `make test` passed backend 143 plus Web 41                                                                 |
| formal E2E                    | IMPLEMENTATION DEFECT                   | first `make e2e` exited 2 with Playwright `10 passed, 4 failed`; both Phase 4 prepare paths ended `repository_unavailable`                                        | explicit gitlink rejection broke the versioned fixture's established inert-submodule boundary                                                                                                                                   | treat gitlink as validated inert superproject metadata without target object import or submodule recursion; restored focused coverage and full rerun passed `14/14`                                                         |
| Docker evidence command       | INVALID INSPECTION TEMPLATE             | the first multi-container `docker inspect --format` exited 1 after printing API/Web/DB facts because Runner has no `Config.ExposedPorts` map                      | the Go template dereferenced an intentionally absent optional map entry                                                                                                                                                         | rerun Runner inspection without that optional field; it exited 0, and separate runtime probes confirmed port bindings are empty                                                                                             |
| final aggregate, first run    | DOCUMENT FORMAT DRIFT                   | first post-documentation `make verify` exited 2 after contracts passed because `format-check` named the two new Round 2 Markdown files                            | the latest evidence and ExecPlan additions had not yet been normalized by repository Prettier                                                                                                                                   | `make format` exited 0 and formatted exactly those documents; rerun `format-check`, then rerun the complete aggregate                                                                                                       |
| final diff pack-budget review | IMPLEMENTATION DEFECT                   | additive budget case exited 1 because six orphan pack sidecars under `mirror_max_pack_files=1` did not raise                                                      | pack/root/destination scans first materialized whole directory listings, and orphan `.keep`/`.bitmap`/`.rev` files were not counted or tied to a real pack                                                                      | stream every directory scan; bound every supported pack entry; require sidecars to belong to a pack; focused rerun 1 passed, complete Runner/Protocol 52 passed, source invariance PASS                                     |

New first failures remain in this table after correction.

## Verification

No entry is PASS until the exact command runs in this worktree and exits zero.

| Command or evidence                                      | Current result                                                                                 |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| complete re-audit test file before repair                | EXPECTED FAIL — exit 1; 3 failed, 4 passed; exact three blockers reproduced                    |
| object-closure focused tests                             | VERIFIED in `test_workspace_tools.py`; complete file exit 0, 47 passed                         |
| source invariance                                        | VERIFIED; exit 0, 119 entries, 10 object comparisons, 2 status records, zero extension markers |
| ownership/discard focused tests                          | VERIFIED in `test_workspace_tools.py`; complete file exit 0, 47 passed                         |
| process-group timeout focused tests                      | VERIFIED in Runner file plus preserved re-audit; both exit 0                                   |
| real PostgreSQL Permit closure matrix                    | VERIFIED; exit 0, 12 passed against PostgreSQL on `127.0.0.1:55433`                            |
| protocol/API/contracts/migration regressions             | VERIFIED; contracts have no drift; PostgreSQL downgrade/upgrade cycle exited 0                 |
| `make format` / `make format-check`                      | VERIFIED; both formal targets exited 0                                                         |
| `make lint` / `make typecheck`                           | VERIFIED; both formal targets exited 0                                                         |
| `make test` / `make build`                               | VERIFIED; backend 143, Web 41, production Web build 10 routes                                  |
| `make workspace-security-check`                          | VERIFIED; exit 0, 52 passed plus static checker                                                |
| `make phase4-findings-check`                             | VERIFIED; exit 0, 7 passed and `FAIL_PRESERVED`                                                |
| `make workspace-security-repair-check`                   | VERIFIED; exit 0, 59 Runner/Protocol and 12 PostgreSQL API tests                               |
| `make security-check` / `make eval`                      | VERIFIED; 76 security tests; 58 Eval cases in 4 datasets plus 7 scanner tests                  |
| `make e2e`                                               | VERIFIED on final policy; exit 0, Playwright 14 passed                                         |
| `make workspace-smoke` / `make runner-smoke`             | VERIFIED in exact isolated Compose project; both exited 0                                      |
| `make runner-chaos-check` / `make workspace-chaos-check` | VERIFIED; both exited 0 and exact Compose resources were removed                               |
| real Docker isolation probes                             | VERIFIED in live isolated Runner/API/Web/DB containers; exit 0                                 |
| `git diff --check`                                       | VERIFIED in the completed final aggregate; exit 0                                              |
| final `make verify`                                      | VERIFIED; post-review correction complete rerun exited 0                                       |
| production/source invariance manifests                   | VERIFIED by strict source harness and scoped Git inventory                                     |

Remote CI is **NOT VERIFIED** and will not be claimed.

## Rollback

- The branch is isolated at the exact re-audit commit.
- Do not reset, clean, stash, overwrite, delete, or alter another branch.
- Before the final checkpoint, every scoped source/document edit is visible in
  one working-tree diff.
- Database changes, if a proven Permit defect requires one, must use a new
  reversible migration and disposable PostgreSQL only.
- Stop/remove only exact repository-owned disposable Compose projects and
  fixtures through their supported cleanup paths. Preserve unknown local
  Workspace, mirror, registry, source, and sibling state.

## Completion conditions

1. All three re-audit secure assertions pass without being weakened.
2. Additive tests cover loose/packed closure, valid reachable objects,
   malformed and budget cases, destination validation, source invariance, and
   mirror exclusion of every unauthorized object ID.
3. Discard tests cover missing/tampered/mismatched/replayed proof, root
   identity drift, legitimate idempotent completion, and zero source/mirror/
   sibling effects.
4. Timeout tests cover leader-first exit, inherited and closed pipes, multiple
   descendants, normal completion, no residual PID, overflow/timeout race,
   repeated cleanup, and explicit termination failure.
5. The complete real-PostgreSQL Permit matrix proves acquisition, single
   consumption, all bindings, revocation, expiry, tamper/mismatch/replay,
   stale identities, cancellation, crash windows, idempotent retry, common
   Permit lineage, ordering, and zero rejected disk side effects.
6. Migration upgrade/downgrade/re-upgrade, contracts, API/Protocol, Docker,
   source invariance, E2E, smoke, chaos, security, Eval, and final
   `make verify` all exit zero.
7. The full diff remains inside this work package; historical FAIL documents
   remain preserved.
8. One local commit named
   `fix(security): close phase 4 re-audit blockers` exists; all protected refs
   remain unchanged; the final worktree/index are clean.
9. No CreativeDeploy access, remote, push, PR, merge, tag, Phase 5, or
   Security Gate PASS claim occurs.

## Outcome and follow-ups

`REMEDIATION ROUND 2 COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`

The single checkpoint containing this finalized record uses
`fix(security): close phase 4 re-audit blockers`. Its exact hash is necessarily
reported in the Git handoff rather than embedded in its own commit tree.

The only allowed next milestone is
**Phase 4 Independent Focused Security Re-Audit**.
