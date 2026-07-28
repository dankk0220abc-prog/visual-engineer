# Phase 4 Independent Single-Finding Re-Audit Verification

- Date: 2026-07-29
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `audit/phase-4-replacement-single-finding-max`
- Candidate:
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`
- Candidate parent:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`
- Decision:
  **SINGLE-FINDING RE-AUDIT COMPLETE — VE-P4-FREAUD-001 FAIL —
  REMEDIATION REQUIRED**

## Evidence rules

- `CONFIRMED` means the current independent reviewer observed the exact
  command or inspected the current candidate.
- `INFERRED` follows only from identified confirmed facts and is labelled.
- `NOT VERIFIED` means the check was not run in this review.
- Implementer evidence is navigation, not approval.
- Exit codes, selected/test counts, first failures, audit-test mistakes,
  corrections, and reruns are preserved.
- A failing additive secure-expectation test is a production Gate result, not
  an `xfail` or a reason to weaken the assertion.

## Baseline and repository identity

Every baseline command below ran before the first audit edit.

| Command                                                                                                          | Exit | CONFIRMED result                                                                                 |
| ---------------------------------------------------------------------------------------------------------------- | ---: | ------------------------------------------------------------------------------------------------ |
| `pwd`                                                                                                            |    0 | `/Users/danke/Developer/VisualEngineer`                                                          |
| `git rev-parse --show-toplevel`                                                                                  |    0 | Exact same repository root.                                                                      |
| `git branch --show-current`                                                                                      |    0 | Starting branch `fix/phase-4-security-remediation-3`.                                            |
| `git rev-parse HEAD`                                                                                             |    0 | `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`.                                                      |
| `git status --porcelain=v2 --branch`                                                                             |    0 | Exact branch/HEAD; no tracked, staged, or untracked records.                                     |
| `git diff --stat`                                                                                                |    0 | Empty.                                                                                           |
| `git diff --cached --stat`                                                                                       |    0 | Empty.                                                                                           |
| `git remote -v`                                                                                                  |    0 | Empty.                                                                                           |
| `git show-ref --heads`                                                                                           |    0 | Every disclosed main/Phase 4/audit/repair ref matched its reported hash.                         |
| `git log --oneline --decorate --graph --all -20`                                                                 |    0 | Disclosed linear Phase 4 history; Round 3 is the only ref-reachable commit after the checkpoint. |
| `git cat-file -t 8985fa0356e636602d1414a3ade9d9a7888c624a`                                                       |    0 | `commit`.                                                                                        |
| `git cat-file -t 6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`                                                       |    0 | `commit`.                                                                                        |
| `git show --stat --oneline 6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`                                             |    0 | 15 paths, 1,604 insertions, 117 deletions; three production paths.                               |
| `git merge-base --is-ancestor 8985fa0356e636602d1414a3ade9d9a7888c624a 6cce662bf4cf34961c7d3f0d16741952cd2c1fd2` |    0 | Focused checkpoint is an ancestor.                                                               |
| `git rev-list --count 8985fa0356e636602d1414a3ade9d9a7888c624a..6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`        |    0 | `1`.                                                                                             |
| `git diff --check 8985fa0356e636602d1414a3ade9d9a7888c624a..6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`            |    0 | No whitespace error.                                                                             |
| `git rev-parse 6cce662bf4cf34961c7d3f0d16741952cd2c1fd2^`                                                        |    0 | Exact parent `8985fa0356e636602d1414a3ade9d9a7888c624a`.                                         |
| `git rev-parse refs/heads/main`                                                                                  |    0 | `7590f9dcecbf06371936ac0265cecb9f7a4438ca`.                                                      |
| `git stash list`                                                                                                 |    0 | Empty.                                                                                           |
| `git tag --list`                                                                                                 |    0 | Empty.                                                                                           |
| `git ls-files --others --exclude-standard`                                                                       |    0 | Empty.                                                                                           |
| `git show-ref --verify --quiet refs/heads/audit/phase-4-replacement-single-finding-max`                          |    1 | Expected no-match exit; audit branch did not pre-exist.                                          |
| `git switch -c audit/phase-4-replacement-single-finding-max 6cce662...`                                          |    0 | Branch created directly from the exact full candidate hash.                                      |

Protected refs at baseline:

| Ref                                          | Hash                                       |
| -------------------------------------------- | ------------------------------------------ |
| `main`                                       | `7590f9dcecbf06371936ac0265cecb9f7a4438ca` |
| `feat/phase-4-isolated-workspace-tools`      | `53dc2f5016e9b76e1f39c6306fe116ee4091b302` |
| `audit/phase-4-workspace-security-max`       | `a560509b2018f86693e38e3646409f9e33841829` |
| `fix/phase-4-security-remediation`           | `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c` |
| `audit/phase-4-security-reaudit-max`         | `b457b614bde6630fb50ff9546c92a4d6925ad38a` |
| `fix/phase-4-security-remediation-2`         | `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1` |
| `audit/phase-4-security-focused-reaudit-max` | `8985fa0356e636602d1414a3ade9d9a7888c624a` |
| `fix/phase-4-security-remediation-3`         | `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2` |

## Unreachable-object reconciliation

`git fsck --full --no-reflogs --unreachable` exited `0`. It listed four
unreachable commits plus their trees/blobs:

- `286300ca4ef79f5dc10c8d133dcebc172c9c6fb3`;
- `b3e3138f99183b4fc2d8a63e28f226631dffb56d`;
- `a8a5061b69e762d7f3cec8338a6d486488a017f2`; and
- `f8bd4190d79dca8989fc59f534fef503cb469021`.

The first three are the previously documented pre-amend predecessors of the
Phase 2, Phase 3, and original audit commits. Current reflogs independently
identify the fourth as the Round 3 pre-amend commit:

```text
f8bd419... commit: fix(security): reject Git replacement metadata in phase 4 mirror
6cce662... commit (amend): fix(security): reject Git replacement metadata in phase 4 mirror
```

`git show --no-patch` confirms `f8bd419...` has the exact focused checkpoint
parent. `git diff --stat f8bd419... 6cce662...` exits `0` and shows only ten
insertions/seven deletions across the Round 3 plan and verification evidence.
It is not a ref, stash, second candidate branch, or extra ref-reachable commit.
No object was deleted or pruned.

## CreativeDeploy, configuration, and remote boundary

No command opened or traversed the prohibited CreativeDeploy repository.
Searches were restricted to tracked files inside VisualEngineer.

| Command / scope                                                                                    | Exit | Result                                                                            |
| -------------------------------------------------------------------------------------------------- | ---: | --------------------------------------------------------------------------------- |
| `git grep -n -I -i -e CreativeDeploy -- compose.yaml Makefile scripts infra .github apps packages` |    0 | Historical `infra/README.md` text and static Customer 0 API payload strings only. |
| exact `/Users/danke/.../CreativeDeploy` path search outside docs                                   |    1 | Expected no-match; no exact host path.                                            |
| `git config --local --show-origin --list`                                                          |    0 | No remote, include, alternate, worktree, or CreativeDeploy configuration.         |
| Round 3 diff under Compose/config/infra/scripts                                                    |    0 | Empty.                                                                            |
| `git remote -v`                                                                                    |    0 | Empty.                                                                            |

The literal label `CreativeDeploy` does exist in the historical
`scripts/run_customer0_case.py` static request title/description and display
name. This was disclosed by the Round 3 plan and was not changed or executed.
There is no host-path/configuration/Compose mount, and no Customer 0 command
ran. The stronger literal statement that no script mentions CreativeDeploy
would be false; the security-relevant no-access/no-mount boundary is
**CONFIRMED**.

## Frozen production boundary

The frozen production boundary is:

```text
apps/api/src
apps/runner/src
packages/runner-protocol/src
apps/api/alembic
apps/api/Dockerfile
apps/runner/Dockerfile
compose.yaml
infra
```

It contains 72 tracked files.

| Evidence                                      | SHA-256                                                            |
| --------------------------------------------- | ------------------------------------------------------------------ |
| Initial current-content manifest              | `3a9c6e71e25c1ab39022eaf1556500937afb453278397dd44a75a8e20aed8e5b` |
| Candidate Git-tree listing                    | `93a9ce4302f1c58a54c68b6ab4abefecd90cec0fb4cff86fb65999d672c7ad3c` |
| Protected-ref set excluding this audit branch | `bceb29fd3bd2e67b7598326fc06af2c5f0d594b341eca1b0070024c966785507` |

The initial worktree digest includes Round 3 production content and must equal
the repeated pre-checkpoint digest. Production paths must also have no
worktree or staged diff from `6cce662...`.

## Complete review and static replacement proof

The reviewer read in full:

- `AGENTS.md`, `SECURITY.md`, `PLANS.md`, and project status;
- the focused re-audit report/evidence/ExecPlan;
- the Round 3 report/evidence/ExecPlan;
- the complete preserved blocking-reproduction file;
- complete `git_object_store.py`, `git_ops.py`, and `workspace_manager.py`;
- the directly related Workspace/object/ref/manifest tests; and
- affected ADR, architecture, Runner threat-model, and Workspace threat-model
  documents.

The complete `8985fa0..6cce662` diff was reviewed. Static inspection
**CONFIRMED**:

- `git_ops.py` is the only production subprocess user;
- all fifteen production Git call sites converge on `_run`;
- command argv contains `--no-replace-objects`;
- the replacement environment contains `GIT_NO_REPLACE_OBJECTS=1` and does
  not inherit caller Git variables;
- `shell=False`;
- source paths do not reach Git as a working directory, Git directory,
  worktree, object database, alternate, or fetch source;
- new mirror initialization uses an empty template;
- top-level metadata, exact config/HEAD, object layout, and empty raw refs are
  validated before mirror reuse;
- `packed-refs`, every loose ref, replacement/graft/alternate metadata,
  hooks, logs, shallow state, and other top-level entries fail closed;
- the expected manifest is derived by the source-less parser rather than Git
  output; and
- the actual manifest compares raw path bytes, type, Git mode, size, and
  digest through descriptor-rooted no-follow traversal before registration.

## Original reproduction

Command:

```bash
/opt/homebrew/bin/uv run pytest \
  apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py::test_focused_existing_mirror_packed_replace_cannot_change_checkout \
  --no-cov -q
```

Exit `0`: `1 passed in 0.27s`.

The unchanged original attack is denied before the second Workspace exists.
Source HEAD and approved bytes remain exact.

## Independent late replacement scenario

The additive test is
`test_single_finding_late_packed_replace_is_ignored_then_rejected`.

It injects a packed replacement after actual `prepare_mirror` validation and
before actual worktree checkout, while hostile host Git environment variables
attempt to redirect Git and re-enable replacement interpretation.

First isolated run:

```text
EXIT_CODE: 0
1 passed in 0.27s
```

Observed assertions:

- the in-flight Workspace contains `independently approved revision\n`;
- a valid registry is created;
- packed replacement metadata remains present as evidence;
- the next prepare returns typed `workspace_state_invalid`;
- no second canonical Workspace exists;
- the first Workspace and source HEAD/status/bytes remain unchanged; and
- the hostile host Git variables did not override the fixed adapter
  environment.

After scoped formatting, the combined independent pair reports
`1 failed, 1 passed`; the passing case remains this late replacement test and
the sole failure remains the manifest-capacity test.

## Manifest-capacity blocker

### Standalone discovery probe

A temporary source-less production-method probe used a shared subtree:

```text
configured_tree_entry_limit=5
prepared_manifest_entries=8
paths=left,left/a.txt,left/b.txt,left/c.txt,right,right/a.txt,right/b.txt,right/c.txt
```

The decisive counts were emitted by production `prepare_mirror`, and the probe
exited `0`.

No production file was changed. The probe used a temporary directory removed
by `TemporaryDirectory`.

### Permanent secure-expectation test

The additive test
`test_single_finding_checkout_manifest_enforces_expanded_entry_budget` accepts
either typed `mirror_budget_exceeded` or a returned manifest at or below the
configured limit. It does not require a particular implementation.

First run:

```text
EXIT_CODE: 1
assert 8 <= 5
1 failed in 0.25s
```

Exact immediate rerun:

```text
EXIT_CODE: 1
assert 8 <= 5
1 failed in 0.24s
```

This is a stable production-boundary failure, not an audit-test import,
fixture, formatting, or assertion-shape error.

### Complete manager-path classification probe

A second temporary probe executed the complete Workspace manager path with
the same five-entry limit:

```text
manager_failure=mirror_budget_exceeded
canonical_workspace_exists=False
quarantine_count=1
registry_exists=False
```

Exit `0`. This confirms that integrity/registration still fails closed after
checkout. It also locates the defect precisely: expected-manifest construction
can exceed the limit before the later Workspace scan enforces it.

### Root cause

`CONFIRMED`:

1. `_walk_tree` charges each unique tree object only once because a cached
   tree returns before repeated path expansion;
2. `_walk_checkout_manifest` recursively constructs one list entry per
   expanded path but has no expanded-entry counter;
3. `prepare_mirror` constructs that manifest before object materialization,
   Git checkout, or the actual Workspace scanner; and
4. only `_scan_workspace_directory` charges actual expanded entries to
   `mirror_max_tree_entries`.

`INFERRED`: a binary shared-tree chain can produce
`3 * 2^n - 2` manifest entries from only `2n + 1` unique tree entries. At
depth `20`, `41` unique entries can produce `3,145,726` manifest entries.
This can exhaust the declared Runner memory/Permit boundary before the
enforcement point and can leave a newly initialized mirror without its final
managed detached `HEAD`.

Severity is **Blocking Medium**: availability and stable recovery are
affected, but no source mutation, unauthorized registered Workspace content,
customer access, or cross-boundary code execution was reproduced.

## Focused command matrix

| Command / scope                                                     | Exit | Result                                                                        |
| ------------------------------------------------------------------- | ---: | ----------------------------------------------------------------------------- |
| Original packed-replacement reproduction                            |    0 | `1 passed`.                                                                   |
| Independent late packed-replacement test                            |    0 | `1 passed`.                                                                   |
| Standalone expected-manifest budget probe                           |    0 | Limit `5`, returned entries `8`.                                              |
| Permanent budget secure-expectation test, first run                 |    1 | `1 failed`; `8 <= 5`.                                                         |
| Exact budget-test rerun                                             |    1 | `1 failed`; same assertion.                                                   |
| Complete manager-path classification probe                          |    0 | Typed budget failure, canonical path absent, one quarantine, no registry.     |
| Complete `test_phase4_blocking_reproductions.py --no-cov -q`        |    1 | Initial run: `1 failed, 11 passed in 3.12s`; only manifest budget failed.     |
| Round 3 replacement/manifest selection in `test_workspace_tools.py` |    0 | `6 passed, 47 deselected in 1.00s`.                                           |
| Source/object/ref/manifest focus in `test_workspace_tools.py`       |    0 | `19 passed, 34 deselected in 2.65s`.                                          |
| `make source-invariance-check`                                      |    0 | JSON `PASS`; 119 entries, 10 objects, 2 status records, 0 extension markers.  |
| `make workspace-security-check`                                     |    0 | `58 passed in 9.00s`; static isolation check passed.                          |
| `make test-runner`                                                  |    2 | Pytest `1 failed, 76 passed in 12.11s`; only the additive budget test failed. |
| combined two independent tests after scoped formatter               |    1 | `1 failed, 1 passed`; same budget failure, late replacement still passes.     |
| initial scoped `ruff format --check` on additive audit file         |    1 | Test-only formatting differences; no behavior or assertion failure.           |
| scoped `ruff format`                                                |    0 | `1 file reformatted`.                                                         |
| repeated scoped `ruff format --check`                               |    0 | `1 file already formatted`.                                                   |
| scoped `ruff check`                                                 |    0 | All checks passed.                                                            |
| first scoped Prettier check of four authorized documents            |    1 | Three new audit documents needed formatting; project status already matched.  |
| scoped Prettier write of those three new documents                  |    0 | Only the three named audit documents were reformatted.                        |
| `make format-check`                                                 |    0 | Ruff: 98 files; root/Web Prettier checks passed.                              |
| `make lint`                                                         |    0 | Ruff and Web ESLint passed with zero warnings.                                |
| `make typecheck`                                                    |    0 | mypy passed 73 source files; Web `tsc --noEmit` passed.                       |
| initial `git diff --check`                                          |    0 | No whitespace error.                                                          |
| final original-plus-late replacement pair                           |    0 | `2 passed in 0.51s`.                                                          |
| final complete blocking file                                        |    1 | `1 failed, 11 passed in 3.18s`; only the stable budget assertion failed.      |

The exact 19-case object/ref/manifest command was:

```bash
/opt/homebrew/bin/uv run pytest apps/runner/tests/test_workspace_tools.py \
  --no-cov -q \
  -k 'source_read_only_verification or source_loose_ref or git_output_and_mirror_object_budgets or reachable_packed_delta_closure or existing_mirror or source_packed_replacement_metadata or runner_git_subprocess or checkout_manifest or semantically_different_checkout or source_object_indirection or gitlink_is_inert or malformed_loose_object'
```

The exact six-case Round 3 command was:

```bash
/opt/homebrew/bin/uv run pytest apps/runner/tests/test_workspace_tools.py \
  --no-cov -q \
  -k 'existing_mirror_rejects_every_loose_ref or source_packed_replacement_metadata_is_not_imported_into_mirror or runner_git_subprocess_does_not_interpret_loose_replacement_ref or checkout_manifest_proves_modes_symlink_gitlink_and_empty_ref_namespace or semantically_different_checkout_is_quarantined_before_registration'
```

## Failure and correction ledger

| Event                                                               | Classification                            | Disposition                                                                  |
| ------------------------------------------------------------------- | ----------------------------------------- | ---------------------------------------------------------------------------- |
| target branch `show-ref` exited `1`                                 | Expected no-match                         | Confirmed branch did not pre-exist.                                          |
| exact CreativeDeploy host-path search exited `1`                    | Expected no-match                         | Confirmed no exact path/config/mount.                                        |
| first `rg` budget search named nonexistent `tests/conftest.py`      | Audit command error                       | Recorded exit `2`; corrected search over `apps/runner/tests` exited `0`.     |
| `pytest --collect-only` printed no-coverage warnings but exited `0` | Non-test collection observation           | Used only to enumerate 53 Workspace tests; not reported as a Gate.           |
| standalone manifest probe returned 8 entries under a limit of 5     | Production security discovery             | Converted to additive secure-expectation test.                               |
| budget test failed `8 <= 5` twice                                   | Stable Blocking Medium production failure | Preserved; no production repair.                                             |
| complete blocking file failed once                                  | Consequence of open Finding               | `1 failed, 11 passed`; no `xfail`.                                           |
| `make test-runner` exited `2`                                       | Consequence of same open Finding          | Pytest `1 failed, 76 passed`; no second failure.                             |
| first scoped format check exited `1`                                | Audit-test formatting issue               | Ran scoped formatter only; behavior rerun preserved the same PASS/FAIL pair. |
| first scoped Markdown check exited `1`                              | Audit-document formatting issue           | Formatted only three named new documents; repository format check passes.    |

## Intentionally unrun checks

The following are **NOT VERIFIED** and are not inferred:

- aggregate `make verify`;
- complete `make test`;
- Web/browser E2E;
- full Chaos;
- full live Docker isolation Gate;
- Customer 0 or any real repository;
- remote CI;
- production deployment; and
- Phase 5.

They are outside this accelerated single-finding review, and the stable
Blocking Medium makes an integration PASS impossible.

## Final quality and invariant closure

The completed pre-checkpoint closure is:

| Check                                      | Status                                                                                                     |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| Audit Python formatting and lint           | PASS                                                                                                       |
| Audit Markdown formatting                  | PASS                                                                                                       |
| `make format-check`                        | PASS                                                                                                       |
| `make lint`                                | PASS                                                                                                       |
| `make typecheck`                           | PASS                                                                                                       |
| final `git diff --check`                   | PASS                                                                                                       |
| changed-path inventory                     | PASS — exactly the additive audit test and four authorized documents                                       |
| frozen production file count               | PASS — `72`                                                                                                |
| repeated current-content manifest          | PASS — `3a9c6e71e25c1ab39022eaf1556500937afb453278397dd44a75a8e20aed8e5b`                                  |
| candidate Git-tree listing                 | PASS — `93a9ce4302f1c58a54c68b6ab4abefecd90cec0fb4cff86fb65999d672c7ad3c`                                  |
| candidate-to-worktree production diff      | PASS — empty                                                                                               |
| protected refs excluding this audit branch | PASS — `bceb29fd3bd2e67b7598326fc06af2c5f0d594b341eca1b0070024c966785507`                                  |
| main / remote / stash / tag state          | PASS — main exact; remote, stash, and tags empty                                                           |
| local checkpoint and clean final state     | Recorded in the external handoff after the exact staged review because a commit cannot embed its own hash. |

## Evidence classification ledger

| Claim                                                                 | Classification                                    |
| --------------------------------------------------------------------- | ------------------------------------------------- |
| Candidate identity, exact parent, one-commit range, refs, clean base  | CONFIRMED                                         |
| Original packed replacement no longer changes checkout                | CONFIRMED                                         |
| Late packed replacement plus hostile host Git variables do not win    | CONFIRMED                                         |
| New mirror/ref namespace and source metadata non-import               | CONFIRMED                                         |
| Every production Git process has both replacement defenses            | CONFIRMED by complete static inspection           |
| Expected manifest is source-less and semantic fields compare exactly  | CONFIRMED                                         |
| Expanded expected-manifest entry limit is bypassed                    | CONFIRMED twice by runtime plus static inspection |
| Exponential resource amplification follows from shared-tree recursion | INFERRED from confirmed code and 5-to-8 runtime   |
| Later manager scan rejects/quarantines and creates no registry        | CONFIRMED                                         |
| Source and exact object-closure focused gates pass                    | CONFIRMED                                         |
| Full aggregate/E2E/Chaos/Docker/customer/remote/production behavior   | NOT VERIFIED                                      |

`SINGLE-FINDING RE-AUDIT COMPLETE — VE-P4-FREAUD-001 FAIL — REMEDIATION REQUIRED`
