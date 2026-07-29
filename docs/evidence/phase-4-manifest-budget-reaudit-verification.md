# Phase 4 Independent Budget Re-Audit Verification

- Date: 2026-07-29
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `audit/phase-4-manifest-budget-reaudit-max`
- Candidate:
  `03f774827afbafd7f0eb991f5abf2c6fee66cd17`
- Candidate parent:
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8`
- Decision:
  **BUDGET RE-AUDIT COMPLETE — FINDING CLOSED — READY FOR FINAL PHASE 4
  INTEGRATION GATE**

## Evidence rules

- `CONFIRMED` means the current independent reviewer observed the command or
  inspected the current candidate.
- `INFERRED` follows only from identified confirmed facts.
- `NOT VERIFIED` means the check was not run in this review.
- Implementer evidence was navigation only.
- First failures, audit-test corrections, exit codes, and reruns are retained.

## Baseline and repository identity

Every command in this table ran before the first audit edit.

| Command                                                                                                          | Exit | CONFIRMED result                                                                |
| ---------------------------------------------------------------------------------------------------------------- | ---: | ------------------------------------------------------------------------------- |
| `pwd`                                                                                                            |    0 | `/Users/danke/Developer/VisualEngineer`.                                        |
| `git rev-parse --show-toplevel`                                                                                  |    0 | Exact same repository root.                                                     |
| `git branch --show-current`                                                                                      |    0 | Starting branch `fix/phase-4-security-remediation-4`.                           |
| `git rev-parse HEAD`                                                                                             |    0 | `03f774827afbafd7f0eb991f5abf2c6fee66cd17`.                                     |
| `git status --porcelain=v2 --branch`                                                                             |    0 | Exact branch/HEAD; tracked worktree, index, and untracked inventory were empty. |
| `git diff --stat`                                                                                                |    0 | Empty.                                                                          |
| `git diff --cached --stat`                                                                                       |    0 | Empty.                                                                          |
| `git remote -v`                                                                                                  |    0 | Empty.                                                                          |
| `git show-ref --heads`                                                                                           |    0 | Disclosed main, Phase 4, audit, and repair refs matched their reported hashes.  |
| `git log --oneline --decorate --graph --all -20`                                                                 |    0 | Disclosed linear history; Round 4 is the sole commit after its audit base.      |
| `git cat-file -t 2656733aad60d9824db4334b9ef6ba7eb1d677b8`                                                       |    0 | `commit`.                                                                       |
| `git cat-file -t 03f774827afbafd7f0eb991f5abf2c6fee66cd17`                                                       |    0 | `commit`.                                                                       |
| `git show --stat --oneline 03f774827afbafd7f0eb991f5abf2c6fee66cd17`                                             |    0 | Eight paths; 805 insertions and 19 deletions.                                   |
| `git merge-base --is-ancestor 2656733aad60d9824db4334b9ef6ba7eb1d677b8 03f774827afbafd7f0eb991f5abf2c6fee66cd17` |    0 | Audit base is an ancestor.                                                      |
| `git rev-list --count 2656733aad60d9824db4334b9ef6ba7eb1d677b8..03f774827afbafd7f0eb991f5abf2c6fee66cd17`        |    0 | `1`.                                                                            |
| `git diff --check 2656733aad60d9824db4334b9ef6ba7eb1d677b8..03f774827afbafd7f0eb991f5abf2c6fee66cd17`            |    0 | No whitespace error.                                                            |
| `git rev-parse 03f774827afbafd7f0eb991f5abf2c6fee66cd17^`                                                        |    0 | Exact parent `2656733aad60d9824db4334b9ef6ba7eb1d677b8`.                        |
| `git rev-parse refs/heads/main`                                                                                  |    0 | `7590f9dcecbf06371936ac0265cecb9f7a4438ca`.                                     |
| `git stash list`                                                                                                 |    0 | Empty.                                                                          |
| `git tag --list`                                                                                                 |    0 | Empty.                                                                          |
| `git ls-files --others --exclude-standard`                                                                       |    0 | Empty.                                                                          |
| audit-branch existence check                                                                                     |    1 | Expected no-match; branch did not pre-exist.                                    |
| `git switch -c audit/phase-4-manifest-budget-reaudit-max 03f7748...`                                             |    0 | Branch created directly from the exact candidate without force.                 |

Candidate `03f7748...` changes exactly:

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

Only `git_object_store.py` is production code. The other seven paths are its
direct tests and security/architecture/status records.

## Complete diff and static review

The reviewer read the complete
`2656733aad60d9824db4334b9ef6ba7eb1d677b8..03f774827afbafd7f0eb991f5abf2c6fee66cd17`
diff and the required governance, historical audit, remediation evidence,
blocking test, parser, manifest, object/tree/graph budget, Workspace manager,
Git adapter, architecture, and threat-model material.

Static inspection **CONFIRMED**:

- one shared mutable counter spans the full source-less manifest walk;
- each recursive tree traversal receives a new pending directory marker, even
  when the underlying object ID is shared;
- leaf accounting includes all uncharged materialized ancestor directories;
- `new_count > max_tree_entries` is checked before count mutation, blob read,
  digest, gitlink construction, or manifest append;
- equality is accepted;
- regular, symlink, and inert gitlink leaves are all charged;
- only non-empty materialized directories are charged and appended;
- no completed unbounded manifest is generated before a final length check;
- source/parser entry fields remain raw bytes, type, Git mode, size, and
  SHA-256 digest;
- Git adapter, Workspace scanner, registry, ownership, Permit, discard,
  process-group timeout, API, database, Web, Compose, and CI production code
  are unchanged by Round 4 except the scoped parser file; and
- the reviewer has no production-code diff from the exact candidate.

## Commands, exit codes, and counts

| Seq. | Command / check                                         | Exit | CONFIRMED result                                                               |
| ---: | ------------------------------------------------------- | ---: | ------------------------------------------------------------------------------ |
|    1 | Unchanged original shared-tree test                     |    0 | `1 passed in 0.23s`.                                                           |
|    2 | New independent three-parent test, first run            |    0 | `1 passed in 0.22s`.                                                           |
|    3 | Complete blocking reproduction file                     |    0 | Initial `13 passed in 3.17s`; final `13 passed in 3.23s`.                      |
|    4 | Manifest/object-closure focus                           |    0 | `24 passed, 34 deselected in 3.35s`.                                           |
|    5 | `make source-invariance-check`                          |    0 | PASS; 119 entries, 10 Git objects, 2 status records, 0 extension markers.      |
|    6 | `make workspace-security-check`                         |    0 | `63 passed in 9.68s`; static isolation passed.                                 |
|    7 | `make test-runner`                                      |    0 | Initial `83 passed in 12.94s`; final `83 passed in 12.97s`.                    |
|   8a | First `make format-check`                               |    2 | Only two Ruff layout changes in the new audit test.                            |
|   8b | Second `make format-check`                              |    2 | Ruff passed; only the new ExecPlan needed Prettier formatting.                 |
|   8c | Pre-documentation complete `make format-check`          |    0 | 98 Python files and root/Web Prettier checks passed.                           |
|   8d | Post-documentation `make format-check`                  |    2 | Only the new audit report and evidence needed Prettier formatting.             |
|   8e | Complete `make format-check` after scoped formatting    |    0 | 98 Python files and root/Web Prettier checks passed.                           |
|   8f | Post-status-update `make format-check`                  |    2 | Only the updated ExecPlan and evidence needed Prettier formatting.             |
|   8g | Final complete `make format-check`                      |    0 | 98 Python files and root/Web Prettier checks passed.                           |
|    9 | `make lint`                                             |    0 | Ruff and Web ESLint passed; final rerun also passed.                           |
|  10a | First `make typecheck`                                  |    2 | Three mypy errors in the audit spy's `**kwargs: object` forwarding annotation. |
|  10b | `make typecheck` after audit-only annotation correction |    0 | mypy 73 files and Web `tsc --noEmit` passed; final rerun passed.               |
|   11 | Final independent test after exact-five tightening      |    0 | `1 passed in 0.25s`.                                                           |
|   12 | `git diff --check`                                      |    0 | No whitespace errors after final documentation formatting.                     |
|   13 | Post-checkpoint Git closure                             |    0 | Exact parent/candidate, five-path scope, empty worktree/index, no remote.      |

The exact object/manifest selection was:

```bash
/opt/homebrew/bin/uv run pytest apps/runner/tests/test_workspace_tools.py \
  --no-cov -q \
  -k 'source_read_only_verification or source_loose_ref or git_output_and_mirror_object_budgets or reachable_packed_delta_closure or existing_mirror or source_packed_replacement_metadata or runner_git_subprocess or checkout_manifest or semantically_different_checkout or source_object_indirection or gitlink_is_inert or malformed_loose_object or expanded_manifest_budget'
```

## Original reproduction

The existing
`test_single_finding_checkout_manifest_enforces_expanded_entry_budget` was not
modified. Its synthetic source uses limit `5`, a three-file tree shared by
`left` and `right`, and a possible expanded manifest of eight entries.

Current independent run: exit `0`, `1 passed in 0.23s`. Production returns
typed `mirror_budget_exceeded` rather than an over-budget manifest.

## Independent exact-limit and limit-plus-one result

The single additive test is
`test_budget_reaudit_three_parent_shared_tree_charges_each_expanded_path`.

**CONFIRMED**:

- an exact revision expands to five paths under limit `5` and succeeds with
  exactly five entries;
- the same single-file tree under three parents could expand to six entries;
- limit `5` returns `SourceObjectError` and manager
  `WorkspaceExecutionError`, both with `MIRROR_BUDGET_EXCEEDED`;
- a manifest-phase read spy counts the shared blob exactly twice, so the third
  parent path is charged and rejected before its blob read;
- because SHA-256 follows the blob read in the inspected production branch,
  **INFERRED**: the third path also performs no digest work;
- checkout returns no over-budget tuple;
- actual manager failure leaves no Workspace, registry, or ownership record;
- the managed mirror remains a directory;
- a sibling marker survives; and
- source HEAD and status remain exact.

The test invokes the manager once and supplies one Permit. No retry, lifecycle
Permit acquisition, or additional manager execution occurs. **CONFIRMED**:
there is no extra Permit consumption in this audit path.

## First failures and corrections

| Event                         | Classification             | Correction and rerun                                                                       |
| ----------------------------- | -------------------------- | ------------------------------------------------------------------------------------------ |
| First format check exit `2`   | Audit-test formatting      | Ruff formatted only the audit test; the independent test reran `1 passed`.                 |
| Second format check exit `2`  | New ExecPlan formatting    | Prettier formatted only the new ExecPlan; the next complete check passed.                  |
| Documentation format exit `2` | New audit-doc formatting   | Prettier formatted only the new report and evidence; the complete check passed.            |
| Status-update format exit `2` | Updated audit-doc layout   | Prettier corrected only the two audit documents; final complete rerun passed.              |
| First typecheck exit `2`      | Audit-test annotation only | Changed spy forwarding from `object` to `Any`; independent test, lint, and typecheck pass. |
| Exact-boundary wording review | Audit assertion tightening | Same single test now proves exact `5`, not only exact `6`; targeted/full/Runner reran.     |

No production failure occurred. No test was deleted, weakened, skipped,
marked `xfail`, or changed to accommodate production. The permanent audit
reproduction is byte-for-byte unchanged from the candidate.

## Production, source, object, and replacement invariance

**CONFIRMED**:

- `git diff 03f7748... --` over the frozen production paths is empty;
- the only audit code change is the additive security test;
- `make source-invariance-check` reports PASS with the exact current synthetic
  fixture counts;
- the 24-case object/manifest selection passes;
- the 13-case blocking file passes and retains both existing replacement
  scenarios;
- Workspace/Protocol passes 63 cases plus its static isolation check; and
- no remote exists and protected refs were unchanged before the audit edits.

The replacement and exact-closure results are regression evidence only; those
findings were not reopened or re-decided.

## Scope and prohibited actions

Expected audit checkpoint paths:

```text
apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py
docs/evidence/phase-4-manifest-budget-reaudit-verification.md
docs/exec-plans/phase-4-manifest-budget-reaudit.md
docs/security/audits/phase-4-manifest-budget-reaudit.md
docs/status/project-status.md
```

**CONFIRMED**: no production, remote, push, merge, pull request, tag, Customer
0, full `make verify`, Web E2E, full Chaos, full Docker Gate, or Phase 5 action
occurred. No command opened or traversed the prohibited CreativeDeploy path.

## CONFIRMED / INFERRED / NOT VERIFIED ledger

### CONFIRMED

- Exact Git baseline, parent, ancestry, protected refs, clean start, and no
  remote.
- Candidate implementation and complete diff.
- Exact-five success and pre-sixth-entry typed rejection.
- Per-path shared-tree charging and no third blob read.
- No returned over-budget manifest or usable/registered partial Workspace.
- One supplied Permit and no extra execution/acquisition.
- Source, mirror, sibling, production, object-closure, and replacement
  regression results.
- All specified focused commands and the final diff check have the results
  recorded above.
- The audit-only checkpoint has the exact candidate parent and a clean
  post-commit worktree/index; its final hash is reported in the handoff.

### INFERRED

- The rejected third blob has no SHA-256 work because the inspected digest
  call follows the blob read that the independent spy proves did not occur.
- With recursive pre-entry charging and no full-list post-check, expanded
  manifest memory is bounded by the configured entry limit.

### NOT VERIFIED

- Full `make verify`, Web E2E, full Chaos, full Docker Gate, Customer 0,
  remote CI, deployment, hostile multi-tenant isolation, and Phase 5.
- Final integration-gate outcome.

## Decision

No new Critical, High, or blocking Medium finding was discovered.

`BUDGET RE-AUDIT COMPLETE — FINDING CLOSED — READY FOR FINAL PHASE 4
INTEGRATION GATE`

This is a narrow finding decision, not a Phase 4 Security Gate PASS.
