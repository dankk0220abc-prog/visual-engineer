# Phase 4 Security Remediation Round 3 Verification

- Date: 2026-07-29
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/phase-4-security-remediation-3`
- Base / focused re-audit checkpoint:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`
- Candidate parent / Round 2 repair:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`
- Historical decision:
  **FOCUSED RE-AUDIT COMPLETE — SECURITY GATE FAIL — PRESERVED**
- Current remediation status:
  `REMEDIATION ROUND 3 COMPLETE — READY FOR INDEPENDENT SINGLE-FINDING RE-AUDIT`

## Evidence rules

- `CONFIRMED` means an exact command or current file was observed on this
  branch.
- `INFERRED` is identified and follows only from confirmed evidence.
- `NOT VERIFIED` means the command has not yet run successfully in the current
  candidate.
- First failures, test-setup mistakes, exit codes, counts, and corrections are
  preserved.
- This implementer evidence cannot decide the independent Security Gate.

## Baseline and branch

Every required baseline command ran before the first edit.

| Command / observation                                        | Exit | CONFIRMED result                                                                                                |
| ------------------------------------------------------------ | ---: | --------------------------------------------------------------------------------------------------------------- |
| `pwd`                                                        |    0 | `/Users/danke/Developer/VisualEngineer`                                                                         |
| `git rev-parse --show-toplevel`                              |    0 | Exact same real repository root.                                                                                |
| `git branch --show-current`                                  |    0 | `audit/phase-4-security-focused-reaudit-max`                                                                    |
| `git rev-parse HEAD`                                         |    0 | `8985fa0356e636602d1414a3ade9d9a7888c624a`                                                                      |
| `git status --porcelain=v2 --branch`                         |    0 | Clean tracked worktree/index and no untracked records.                                                          |
| worktree/cached `git diff --stat`                            |    0 | Both empty.                                                                                                     |
| `git remote -v` and `git stash list`                         |    0 | Both empty.                                                                                                     |
| `git show-ref --heads`                                       |    0 | All disclosed main/Phase 4/audit/repair refs matched their reported hashes.                                     |
| `git log --oneline --decorate --graph --all -20`             |    0 | Disclosed linear Phase 4 history; no later hidden candidate commit.                                             |
| `git cat-file -t 8985fa...`                                  |    0 | `commit`                                                                                                        |
| `git show --stat --oneline 8985fa...`                        |    0 | Only two audit-test files and four audit/evidence/plan/status documents.                                        |
| `git merge-base --is-ancestor cb799bc... 8985fa...`          |    0 | Round 2 is the focused checkpoint's ancestor.                                                                   |
| `git rev-list --parents -n 1 8985fa...`                      |    0 | Sole parent is exactly `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`.                                              |
| `git diff --check cb799bc...8985fa...`                       |    0 | No checkpoint whitespace error.                                                                                 |
| `git ls-files --others --exclude-standard`                   |    0 | Empty.                                                                                                          |
| `git branch --list fix/phase-4-security-remediation-3`       |    0 | Empty output; branch did not pre-exist.                                                                         |
| `git switch -c fix/phase-4-security-remediation-3 8985fa...` |    0 | Created directly from the full focused checkpoint.                                                              |
| exact-path/config/Compose CreativeDeploy search              |  0/1 | No host-path, configuration, or Compose mount. Historical static Customer 0 API payload exists and was not run. |

The protected ref baseline is:

| Ref                                          | Hash                                       |
| -------------------------------------------- | ------------------------------------------ |
| `main`                                       | `7590f9dcecbf06371936ac0265cecb9f7a4438ca` |
| `feat/phase-4-isolated-workspace-tools`      | `53dc2f5016e9b76e1f39c6306fe116ee4091b302` |
| `audit/phase-4-workspace-security-max`       | `a560509b2018f86693e38e3646409f9e33841829` |
| `fix/phase-4-security-remediation`           | `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c` |
| `audit/phase-4-security-reaudit-max`         | `b457b614bde6630fb50ff9546c92a4d6925ad38a` |
| `fix/phase-4-security-remediation-2`         | `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1` |
| `audit/phase-4-security-focused-reaudit-max` | `8985fa0356e636602d1414a3ade9d9a7888c624a` |

The frozen production boundary contains 72 tracked files.

| Evidence                                      | SHA-256                                                            |
| --------------------------------------------- | ------------------------------------------------------------------ |
| Initial 72-file current-content manifest      | `3ca1448901c572da082a75fb002da81b73b347974c753e8ef7b28f5a167787d3` |
| Focused-checkpoint Git-tree listing           | `be07a14623a65593d5f0c8ddd1a22219b3b7aa3f30f8ee7794206282f312c707` |
| Initial three-file source-adapter content set | `80770c5cb290fbaa1d83906681212d931329667677494a78c2e05dac7793012d` |

## Preserved first failure

The unchanged independent test ran twice before production edits:

```bash
/opt/homebrew/bin/uv run pytest \
  apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py::test_focused_existing_mirror_packed_replace_cannot_change_checkout \
  --no-cov -q
```

Both runs reproduced:

```text
actual:   "original\n"
expected: "approved second revision\n"
1 failed
EXIT_CODE: 1
```

The approved commit, requested `HEAD`, and exact object inventory remained
unchanged while a packed `refs/replace/<approved>` entry caused checkout to
materialize an ancestor.

## Root cause

`CONFIRMED`:

1. managed mirror validation rejected only the loose
   `refs/replace` path and did not reject `packed-refs`;
2. the fixed Runner Git command omitted `--no-replace-objects`;
3. the fixed Runner environment omitted `GIT_NO_REPLACE_OBJECTS=1`; and
4. post-checkout validation compared only Git-interpreted `HEAD` and status,
   not an independent authorized-tree content manifest.

`INFERRED`: object-ID equality cannot detect replacement indirection when the
approved commit and replacement target are both already in the approved
ancestry closure.

## Production repair

### Mirror metadata and refs

- New mirrors use `git init --bare --template=` under the already fixed
  environment, so no host/system template hook, attributes, description, log,
  or ref is inherited.
- Runner writes the exact managed config and a mode-`0600` detached `HEAD`
  containing only the authorized object ID.
- Accepted top-level entries are exactly `HEAD`, `config`, `objects`, `refs`,
  and optional Runner-generated `worktrees`.
- `refs` must contain only empty `heads/` and `tags/` directories.
  `packed-refs`, loose refs, hooks, top-level `info`, logs, shallow metadata,
  alternates, HTTP alternates, and every other extra entry fail closed.
- Existing mirror metadata is validated before any repository-interpreting Git
  command. It is not silently normalized.

### Replacement disabling

Every Runner-owned Git command now has both:

```text
git --no-replace-objects ...
GIT_NO_REPLACE_OBJECTS=1
```

The argument vector remains fixed, `shell=False` remains unchanged, and no Git
process targets the source.

### Workspace-to-revision semantic proof

The source-less object parser derives the authorized checkout manifest from the
approved commit:

- raw relative path bytes;
- entry type (`directory`, `regular`, `symlink`, inert `gitlink`);
- Git mode;
- size; and
- SHA-256 of regular-file bytes, symlink target bytes, or the empty inert
  gitlink materialization.

The Workspace scanner:

- starts from an opened Workspace root;
- walks each directory with descriptor-relative `O_DIRECTORY` and
  `O_NOFOLLOW`;
- refuses special files, linked regular files, unstable inode/size/mtime
  snapshots, over-budget entries/bytes, missing or unsafe generated `.git`,
  and directory inventory races;
- hashes file bytes from stable opened descriptors;
- reads symlink targets without following them; and
- treats a gitlink only as the exact expected empty directory without opening
  its target commit.

Expected and actual ordered entries plus their domain-separated canonical
manifest digest must be exactly equal before ownership or registry creation.
A mismatch atomically renames the new checkout within the Workspace root to a
non-addressable quarantine name. It is not recursively deleted.

## Exact manifest evidence

The first standalone probe exited `1` before product import because its shell
omitted the repository's local `PYTHONPATH`; no product method ran. The
corrected command used:

```bash
PYTHONPATH="apps/runner/src:packages/runner-protocol/src" \
  /opt/homebrew/bin/uv run python -
```

It exited `0` and reported:

```text
expected_manifest_digest=0e93f034eaf9465aa0f0ba7e50d279f055cc638d6444e873b689096b4345c4a8
actual_manifest_digest=0e93f034eaf9465aa0f0ba7e50d279f055cc638d6444e873b689096b4345c4a8
entry_count=5
loose_ref_files=[]
packed_refs_exists=false
mirror_head=source_revision
```

Canonical entries:

| Path                   | Type      |   Mode | Size | SHA-256                                                            |
| ---------------------- | --------- | -----: | ---: | ------------------------------------------------------------------ |
| `sandbox`              | directory | 040000 |    0 | —                                                                  |
| `sandbox/inert-module` | gitlink   | 160000 |    0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `sandbox/script.sh`    | regular   | 100755 |   17 | `306c6ca7407560340797866e077e053627ad409277d1b9da58106fce4cf717cb` |
| `sandbox/tracked-link` | symlink   | 120000 |   11 | `19033232c7f966831bfb0468dac9c2ca87b30cc955dec1752b3287f367cf5643` |
| `sandbox/tracked.txt`  | regular   | 100644 |   17 | `324e0c94c599a9942cc5a296f42bd6f707add5c10611fb4dc0fd73f05260d522` |

## New permanent regressions

`apps/runner/tests/test_workspace_tools.py` adds:

1. loose destination `refs/replace/<approved>` rejection;
2. arbitrary extra destination ref rejection;
3. source packed replacement metadata is not imported;
4. a Runner Git subprocess ignores an injected loose replacement ref;
5. empty mirror ref namespace plus regular/executable/symlink/gitlink manifest
   equality;
6. same-HEAD semantic content tamper is rejected and quarantined before
   registration; and
7. full source/`.git` synthetic snapshots remain unchanged on rejection.

The focused re-audit's independent packed replacement test is unchanged.

## Command and failure ledger

| Command / scope                                                             | Exit | Result                                                                                   |
| --------------------------------------------------------------------------- | ---: | ---------------------------------------------------------------------------------------- |
| unchanged independent packed replacement test before repair, twice          |    1 | `1 failed`; actual ancestor content, expected approved content                           |
| unchanged independent packed replacement test after repair                  |    0 | `1 passed`                                                                               |
| first six-case additive regression run                                      |    1 | `4 passed, 2 failed`; new assertions counted empty `refs/heads` and `refs/tags` as refs  |
| corrected six-case additive regression run                                  |    0 | `6 passed, 47 deselected`                                                                |
| complete `test_phase4_blocking_reproductions.py`                            |    0 | `10 passed`                                                                              |
| Git source/ref/object/manifest focused selection                            |    0 | `19 passed, 34 deselected`                                                               |
| `make source-invariance-check`                                              |    0 | JSON `PASS`; 119 entries, 10 Git objects, 2 status records, 0 extension markers          |
| first `make workspace-security-check`                                       |    2 | pytest `57 passed, 1 failed`; empty-template test-fixture parent assumption              |
| corrected existing ignored-inventory target                                 |    0 | `1 passed`                                                                               |
| repeated `make workspace-security-check`                                    |    0 | `58 passed`; static Workspace isolation check passed                                     |
| `make test-runner`                                                          |    0 | `75 passed`                                                                              |
| first standalone manifest probe                                             |    1 | local module import error from missing `PYTHONPATH`; no product logic ran                |
| corrected standalone manifest probe                                         |    0 | expected/actual digest equal; 5 entries; exact detached HEAD; no loose/packed ref        |
| scoped Ruff format/check and `git diff --check` before broader verification |    0 | production/tests formatted; Ruff passed; diff check passed                               |
| first `make format-check`                                                   |    2 | Python `98 files` passed; four Round 3 Markdown files needed Prettier                    |
| scoped Prettier write plus repeated/final `make format-check`               |    0 | all Python and Markdown files matched format                                             |
| final `make lint`                                                           |    0 | Ruff and Web ESLint passed                                                               |
| final `make typecheck`                                                      |    0 | mypy passed 73 source files; Web `tsc --noEmit` passed                                   |
| first two full `make test` attempts                                         |    2 | backend `152 passed, 1 failed`; coverage-loaded timeout fixture raced before child ready |
| isolated timeout case                                                       |    0 | `1 passed`; production process-group behavior remained correct                           |
| deterministic timeout fixture plus complete blocking file                   |    0 | `10 passed`; secure timeout/group/marker assertions unchanged                            |
| final `make test`                                                           |    0 | backend `153 passed`, 81.79% coverage; Web 7 files / 41 tests passed                     |
| final focused replacement/manifest sequence                                 |    0 | independent 1, additive 6, blocking 10, object/ref/manifest 19 all passed                |
| final Workspace/Runner/Protocol sequence                                    |    0 | source invariance PASS, Workspace/Protocol 58, Runner/Protocol 75                        |

The first Workspace security failure was corrected only by creating the
synthetic `mirror/info` parent before that existing test injects
`info/exclude`. Its discard quarantine, unknown-content preservation, and
sibling preservation assertions were unchanged.

The full coverage run exposed a separate pre-existing timing race in the
focused process-group fixture: the 100 ms deadline could begin before the
child Python process wrote its PID file. No timeout production code changed.
The audit test now waits, with a bounded one-second fixture deadline, for the
PID marker and leader exit before starting the original 100 ms
complete-process-group check. The typed timeout, process-group absence, and
delayed-marker non-creation assertions are unchanged. The independent packed
replacement test was not edited.

## Source and production invariance

`CONFIRMED`:

- strict source invariance passes with
  `extension_markers=0`, `source_entries_compared=119`,
  `source_git_objects_compared=10`, and `source_status_records=2`;
- all replacement/manifest regressions use generated synthetic repositories;
- no Git process in production receives a source path;
- the independent rejection tests compare the synthetic source and `.git`
  snapshots before and after; and
- current production edits are limited to the Git object parser, Git
  subprocess/mirror/checkout adapter, and the Workspace prepare call site.

Final production closure before staging is **CONFIRMED**:

- changed production paths are exactly:
  `git_object_store.py`, `git_ops.py`, and `workspace_manager.py`;
- `git diff --exit-code` for every other frozen production path exits `0`;
- final 72-file current-content digest is
  `51e0ab28617e4ce951b4a8ad69c1dab78ecd407c8d9c1d0db9616fa5ba479aa2`;
- focused-checkpoint Git-tree listing digest remains
  `be07a14623a65593d5f0c8ddd1a22219b3b7aa3f30f8ee7794206282f312c707`;
- main and every pre-existing protected Phase 4/audit/repair ref are
  unchanged;
- remote, stash, and tag inventories are empty; and
- repository-owned `test-db` has no remaining service row.

## Remaining limitations and intentionally unrun checks

- A legacy mirror from before this repair fails closed because it does not
  match the new empty-template/detached-HEAD/empty-ref identity. Manual
  operator recovery is required; no automatic destructive migration exists.
- Same-UID hostile concurrent Workspace mutation remains outside the declared
  local sole-Runner-writer model; descriptor stability checks and quarantine
  are defense in depth, not a multi-tenant sandbox.
- Remote CI, complete E2E/browser, complete Chaos, aggregate `make verify`,
  customer repository behavior, and the independent Security Gate are
  **NOT VERIFIED**.
- The one local checkpoint uses
  `fix(security): reject Git replacement metadata in phase 4 mirror`; its
  final hash and clean worktree/index are recorded externally because a commit
  cannot contain its own hash.

No complete E2E/browser/Chaos or aggregate `make verify` is authorized for this
Round 3 implementer run.

`REMEDIATION ROUND 3 COMPLETE — READY FOR INDEPENDENT SINGLE-FINDING RE-AUDIT`
