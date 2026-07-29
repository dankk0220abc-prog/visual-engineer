# Phase 4 Security Remediation Round 4 Verification

- Date: 2026-07-29
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/phase-4-security-remediation-4`
- Base / independent single-finding audit:
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8`
- Base parent / Round 3 repair:
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Implementer disposition:
  **REMEDIATION ROUND 4 COMPLETE — READY FOR INDEPENDENT BUDGET RE-AUDIT**
- Governance: **SECURITY GATE FAIL — PRESERVED**

## Evidence rules

- `CONFIRMED` means the exact current command exited with the recorded code or
  the current diff was directly inspected.
- `INFERRED` follows only from named confirmed facts and is labelled.
- `NOT VERIFIED` means the command or behavior was intentionally not run.
- A passing implementer gate is not independent Security Gate approval.
- First failures, corrections, reruns, exit codes, counts, Git hashes, and
  final-state checks are preserved.

## Git baseline

All baseline checks ran before the branch or any file changed.

| Command / fact                                                                | Exit | Classification and result                                               |
| ----------------------------------------------------------------------------- | ---: | ----------------------------------------------------------------------- |
| `pwd`                                                                         |    0 | CONFIRMED exact root `/Users/danke/Developer/VisualEngineer`.           |
| `git rev-parse --show-toplevel`                                               |    0 | CONFIRMED exact same root.                                              |
| `git branch --show-current`                                                   |    0 | CONFIRMED start branch `audit/phase-4-replacement-single-finding-max`.  |
| `git rev-parse HEAD`                                                          |    0 | CONFIRMED `2656733aad60d9824db4334b9ef6ba7eb1d677b8`.                   |
| `git status --short --branch --untracked-files=all`                           |    0 | CONFIRMED exact branch with no tracked, staged, or untracked records.   |
| `git diff --name-status`                                                      |    0 | CONFIRMED empty worktree diff.                                          |
| `git diff --cached --name-status`                                             |    0 | CONFIRMED empty index diff.                                             |
| `git remote -v`                                                               |    0 | CONFIRMED empty.                                                        |
| `git worktree list --porcelain`                                               |    0 | CONFIRMED one worktree at the exact repository root and audit HEAD.     |
| `git show -s --format='%H%n%P%n%D%n%s' 2656733...`                            |    0 | CONFIRMED sole exact parent `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`. |
| `git rev-parse refs/heads/main`                                               |    0 | CONFIRMED `7590f9dcecbf06371936ac0265cecb9f7a4438ca`.                   |
| `git rev-parse refs/heads/audit/phase-4-replacement-single-finding-max`       |    0 | CONFIRMED exact audit HEAD.                                             |
| three `git cat-file -t` checks                                                |    0 | CONFIRMED main, Round 3, and audit hashes are commit objects.           |
| two `git merge-base --is-ancestor` checks                                     |    0 | CONFIRMED main → Round 3 → audit ancestry.                              |
| `git show-ref --verify --quiet refs/heads/fix/phase-4-security-remediation-4` |    1 | Expected no-match; CONFIRMED repair branch did not pre-exist.           |
| `git switch -c fix/phase-4-security-remediation-4 2656733...`                 |    0 | CONFIRMED non-forced creation from the full audit hash.                 |

No command accessed, mounted, tested, built, or modified CreativeDeploy.
No remote, push, merge, pull request, tag, deployment, Customer 0, or Phase 5
action occurred.

## Mandatory review and root cause

The repairer read in full:

- `AGENTS.md`, `SECURITY.md`, `PLANS.md`, and project status;
- the complete single-finding audit report, evidence, and ExecPlan;
- the complete permanent blocking-reproduction file;
- the complete source-less Git object parser/materializer;
- manifest production, Workspace semantic-proof, object/tree/graph budget,
  and directly related Runner test paths; and
- the affected Workspace threat model and isolated-Workspace architecture
  text before updating them.

### CONFIRMED root cause

1. `SourceObjectClosure._walk_tree` charges entries once per unique tree
   object; a cached shared tree returns before charging its entries again.
2. `SourceObjectClosure._walk_checkout_manifest` expands that same tree for
   every distinct path but previously had no expanded-entry count.
3. `GitOperations._copy_source_objects` constructs the expected manifest
   before object materialization, Git checkout, and the descriptor-rooted
   actual Workspace scan.
4. The later Workspace scanner has a path-entry count but is too late to bound
   expected-manifest CPU and memory.

`INFERRED`: repeated shared-tree DAGs can amplify expected-manifest work far
beyond the unique object/tree count and exhaust the bounded Runner before the
later scanner.

## Preserved pre-fix failure

The permanent independent test was not edited.

Command:

```bash
/opt/homebrew/bin/uv run pytest \
  apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py::test_single_finding_checkout_manifest_enforces_expanded_entry_budget \
  --no-cov -q
```

| Run                   | Exit | CONFIRMED result                                                                   |
| --------------------- | ---: | ---------------------------------------------------------------------------------- |
| First pre-fix run     |    1 | Limit `5`; returned manifest entries `8`; `1 failed in 0.31s`; assertion `8 <= 5`. |
| Exact immediate rerun |    1 | Same limit and count; `1 failed in 0.24s`; same sole assertion.                    |

This was a stable production-boundary failure, not a fixture, import,
formatting, or assertion-shape error.

## Repair

The production change is limited to
`SourceObjectClosure.checkout_manifest`,
`SourceObjectClosure._walk_checkout_manifest`, and one direct charge helper.

### CONFIRMED behavior

- A fresh mutable count is local to each manifest construction.
- The same count is passed through every recursive path.
- A regular file or symlink atomically charges itself plus every not-yet-proven
  non-empty ancestor directory before its blob is reread and hashed.
- An inert gitlink applies the same atomic leaf-plus-ancestor charge before
  its manifest entry is constructed.
- A directory is charged only when its first actual leaf proves that Git will
  materialize it.
- Empty Git tree paths retain the pre-existing omission semantics.
- `count == limit` is accepted.
- Incrementing to `limit + 1` raises typed `mirror_budget_exceeded` before the
  over-limit entry is created.
- No complete unbounded manifest is first built for a final length check.

No configuration, API, migration, Permit, discard/ownership, process timeout,
Web, Compose, CI, or Phase 5 production logic changed.

## Additive regression evidence

Five tests were added to the ordinary Workspace tool suite; the independent
audit file remained byte-for-byte unchanged from the base.

| Coverage             | CONFIRMED result                                                                                                                                                      |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Limit 5, sixth entry | The manifest-phase spy sees shared `a.txt`, `b.txt`, and `c.txt` only once; the second-path `a.txt` blob is not reread before its directory-plus-leaf charge rejects. |
| Exact limit          | Four actual entries succeed, including the containing directory, regular file, symlink, and inert gitlink; Workspace semantic proof and registry creation succeed.    |
| Shared subtree       | Each `left/**` and `right/**` expansion consumes separate entry units.                                                                                                |
| Deep tree            | Over-limit nested expansion is rejected.                                                                                                                              |
| Wide tree            | The sixth wide entry is rejected.                                                                                                                                     |
| Repeated subtree     | Compact five-unique-entry input cannot return its eight-entry expanded manifest.                                                                                      |
| Entry semantics      | Path bytes, type, mode, size, SHA-256, symlink target, and inert gitlink assertions pass.                                                                             |
| Rejection state      | No canonical Workspace, registry, or ownership record; mirror and sibling remain; source and source `.git` snapshot are exact.                                        |

Initial additive command:

```bash
/opt/homebrew/bin/uv run pytest apps/runner/tests/test_workspace_tools.py \
  --no-cov -q -k 'expanded_manifest_budget'
```

Exit `0`: `5 passed, 53 deselected in 0.87s`.

After scoped formatting, the permanent plus additive selection exited `0`:
`6 passed, 64 deselected in 1.06s`. After the final mirror-preservation
assertion, the additive selection again exited `0`:
`5 passed, 53 deselected in 0.88s`.

## Required verification matrix

| Order | Command / scope                                              | Exit | CONFIRMED result                                                                |
| ----: | ------------------------------------------------------------ | ---: | ------------------------------------------------------------------------------- |
|     1 | Pre-fix permanent shared-tree test                           |    1 | Stable expected failure, `8 > 5`, preserved twice.                              |
|     2 | Post-fix permanent shared-tree test                          |    0 | `1 passed in 0.21s`.                                                            |
|     3 | Additive expanded-manifest regressions                       |    0 | `5 passed, 53 deselected`.                                                      |
|     4 | Complete `test_phase4_blocking_reproductions.py --no-cov -q` |    0 | Final `12 passed in 3.03s`.                                                     |
|     5 | Manifest/object-closure focus in `test_workspace_tools.py`   |    0 | Final `24 passed, 34 deselected in 3.35s`.                                      |
|     6 | `make source-invariance-check`                               |    0 | JSON PASS; 119 entries, 10 Git objects, 2 status records, 0 extension markers.  |
|     7 | `make workspace-security-check`                              |    0 | Final `63 passed in 9.84s`; static isolation passed.                            |
|     8 | `make test-runner`                                           |    0 | Final tightened implementation: `82 passed in 13.02s`.                          |
|    9a | First `make format-check`                                    |    2 | Only new `test_workspace_tools.py` Ruff layout differed.                        |
|    9b | Second `make format-check`                                   |    2 | Ruff passed; only new ExecPlan Prettier layout differed.                        |
|    9c | Pre-tightening complete `make format-check`                  |    0 | Ruff 98 files; root/Web Prettier passed.                                        |
|    9d | Post-tightening `make format-check`                          |    2 | Only the updated evidence document needed Prettier formatting.                  |
|    9e | Final `make format-check`                                    |    0 | Ruff 98 files; root/Web Prettier passed.                                        |
|    10 | `make lint`                                                  |    0 | Ruff and Web ESLint passed with zero warnings.                                  |
|    11 | `make typecheck`                                             |    0 | mypy passed 73 source files; Web `tsc --noEmit` passed.                         |
|    12 | `make test`                                                  |    0 | Final backend/Runner/Protocol `160 passed` at 81.79% coverage; Web `41 passed`. |
|    13 | `git diff --check`                                           |    0 | No whitespace error in the final pre-commit diff.                               |

The exact manifest/object-closure focus was:

```bash
/opt/homebrew/bin/uv run pytest apps/runner/tests/test_workspace_tools.py \
  --no-cov -q \
  -k 'source_read_only_verification or source_loose_ref or git_output_and_mirror_object_budgets or reachable_packed_delta_closure or existing_mirror or source_packed_replacement_metadata or runner_git_subprocess or checkout_manifest or semantically_different_checkout or source_object_indirection or gitlink_is_inert or malformed_loose_object or expanded_manifest_budget'
```

The complete blocking file includes the unchanged original packed-replacement
attack and the independent late-injection replacement scenario. The 24-case
focus includes exact object closure, source replacement metadata non-import,
loose replacement disabling, semantic mismatch quarantine, inert gitlink,
normal semantic manifest, malformed input, and the five new budget tests.

## Failure and correction ledger

| Event                                            | Classification                          | Disposition                                                                                                                   |
| ------------------------------------------------ | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Repair-branch `show-ref` exit 1                  | Expected no-match                       | Confirmed branch absence; created without force.                                                                              |
| Permanent budget test failed twice before repair | Blocking Medium production reproduction | Preserved unchanged; repaired production only.                                                                                |
| First `make format-check` exit 2                 | Test-only formatting                    | Formatted only `test_workspace_tools.py`; six budget tests still passed.                                                      |
| Second `make format-check` exit 2                | New-document formatting                 | Formatted only the new ExecPlan; final complete check passed.                                                                 |
| Post-tightening `make format-check` exit 2       | Updated-evidence formatting             | Formatted only the evidence document; final complete check passed.                                                            |
| Unsafe quoted `rg` pattern started `make test`   | Repairer command error                  | Interrupted immediately with exit 130; removed the exact temporary test DB container and verified it absent.                  |
| First final allowlist command exited 1           | Expected fail-closed scope block        | Three exact 53,248-byte SQLite coverage shards from that interrupted command were removed and verified absent before staging. |

No Critical or High finding was discovered. No existing test was deleted,
skipped, marked `xfail`, or weakened.

## Scope and final Git closure

The intended changed-path inventory is:

```text
SECURITY.md
apps/runner/src/visual_engineer_runner/git_object_store.py
apps/runner/tests/test_workspace_tools.py
docs/architecture/isolated-workspaces.md
docs/evidence/phase-4-security-remediation-4-verification.md
docs/exec-plans/phase-4-security-remediation-4.md
docs/security/workspace-threat-model.md
docs/status/project-status.md
```

`CONFIRMED` before the local checkpoint:

- the diff contains only the source-less manifest budget, direct tests, and
  required security/architecture/status/evidence documentation;
- the permanent independent audit test and every historical audit report are
  unchanged;
- `main` remains
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`;
- the audit base remains
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8`;
- remote, staged-outside-scope, push, merge, PR, and tag state remain absent;
  and
- CreativeDeploy was not accessed.

The checkpoint hash and post-checkpoint clean worktree/index are necessarily
recorded in the external handoff: a commit cannot contain its own final hash.

## Intentionally unrun

The following are `NOT VERIFIED` in Round 4 and are not inferred:

- aggregate `make verify`;
- Web E2E;
- full Chaos;
- complete Docker Gate;
- Customer 0 or any real repository;
- remote CI;
- deployment; and
- Phase 5.

They are explicitly outside the accelerated remediation scope. Full
integration verification remains deferred until an independent budget
re-audit passes.

## Evidence classification ledger

| Claim                                                                  | Classification                             |
| ---------------------------------------------------------------------- | ------------------------------------------ |
| Base, exact parent, ancestry, clean state, remote absence              | CONFIRMED                                  |
| Pre-fix limit 5 returned 8 entries twice                               | CONFIRMED                                  |
| Shared entry count now charges every expanded path                     | CONFIRMED by code inspection and runtime   |
| Sixth entry rejects before its blob reread                             | CONFIRMED by runtime spy                   |
| Exact-limit semantic Workspace succeeds                                | CONFIRMED                                  |
| Deep/wide/repeated over-limit states have no usable Workspace/registry | CONFIRMED                                  |
| Mirror, sibling, source, and source `.git` survive rejection           | CONFIRMED                                  |
| Replacement and exact object-closure regressions remain green          | CONFIRMED                                  |
| Source invariance and required accelerated gates pass                  | CONFIRMED                                  |
| Full verify/E2E/Chaos/Docker/customer/remote/production behavior       | NOT VERIFIED                               |
| Security Gate PASS                                                     | NOT CLAIMED; independent decision required |

`REMEDIATION ROUND 4 COMPLETE — READY FOR INDEPENDENT BUDGET RE-AUDIT`
