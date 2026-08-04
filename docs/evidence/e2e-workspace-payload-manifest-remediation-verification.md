# E2E Workspace Payload Manifest Remediation Verification

## Scope

This evidence covers only PR #14's deterministic workspace payload
postcondition. Production/API/Runner/Web transaction logic and PostgreSQL
regression semantics are unchanged.

## Confirmed remote failure evidence

| Heavy run     | Playwright                                          | Stable postconditions                                           | Workspace digest pair                                                                                                                    | Cleanup                        |
| ------------- | --------------------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `30836566657` | `24 passed`, `1 flaky`, `3 skipped`, suite exit `0` | fixture/workspace HEAD and status plus lifecycle markers passed | `d0004af11da1318938329c402d8349ea257ce0e9d29681d887e9c8453fa9d830` to `0c4746b24b0380c236df795f93fb2be8afc5db8d0a5728e607bf5f1b9b1c5590` | all four cleanup checks passed |
| `30837421817` | `25 passed`, `3 skipped`, suite exit `0`            | fixture/workspace HEAD and status plus lifecycle markers passed | `02f417d2532808e8ab01d5eb648739bc5bccb0653fc9b28bcbfc14dc3fd04eeb` to `d8edd132eacbcf67e625661278d8930198553fa567aff940405492de4185474b` | all four cleanup checks passed |

The first run's Playwright retry is reported exactly rather than rewritten as
`25 passed`. Both runs independently establish that the wrapper's sole final
failure was the black-box workspace-tree digest. Because the old output had no
entry diff, the precise changed `.git` subpath is NOT VERIFIED.

## Contract boundary

- Excluded: only the workspace root's direct `.git`, for directory, file, and
  symlink forms.
- Included: tracked, untracked, ignored, hidden, nested `.git`-named paths,
  directories including empty ones, symlinks, relative paths, logical sizes,
  modes, content SHA-256, and symlink targets.
- Not recorded: mtime, ctime, inode, uid, gid, absolute runner/workspace path,
  file body, traversal order, or locale sorting.
- Git correctness remains independently checked by the existing workspace HEAD
  and porcelain status hashes. Ignored and untracked residue remains payload
  and therefore still fails the workspace-tree gate.

## Verification ledger

| Command or case                                                                                               | Result                                                            | Exit |
| ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ---- |
| Preflight exact refs, PR state/base/head, clean worktree                                                      | VERIFIED                                                          | `0`  |
| `sh -n scripts/run-e2e.sh`                                                                                    | VERIFIED                                                          | `0`  |
| `bash -n scripts/run-e2e.sh`                                                                                  | VERIFIED                                                          | `0`  |
| `dash -n scripts/run-e2e.sh`                                                                                  | VERIFIED                                                          | `0`  |
| `uv run ruff format --check scripts/workspace_payload_manifest.py scripts/test_workspace_payload_manifest.py` | VERIFIED after formatting                                         | `0`  |
| `uv run ruff check scripts/workspace_payload_manifest.py scripts/test_workspace_payload_manifest.py`          | VERIFIED after import ordering                                    | `0`  |
| `uv run python scripts/test_workspace_payload_manifest.py -v`                                                 | ten focused cases VERIFIED                                        | `0`  |
| `.git`-only mutation keeps payload digest                                                                     | VERIFIED by focused fixture                                       | `0`  |
| ignored/untracked/tracked/mode/symlink/empty-directory injections                                             | VERIFIED by focused fixtures                                      | `0`  |
| only root `.git` excluded; nested `.git`-named paths included                                                 | VERIFIED by focused fixtures                                      | `0`  |
| manifest excludes absolute root and mtime and refuses in-root output                                          | VERIFIED by focused fixture                                       | `0`  |
| `CI=true make e2e`                                                                                            | `25 passed`, `3 skipped`; all postconditions and cleanup VERIFIED | `0`  |
| `make source-invariance-check`                                                                                | 119 source entries and 10 Git objects compared; PASS              | `0`  |
| `git diff --check`                                                                                            | VERIFIED                                                          | `0`  |

The successful local E2E payload digest was
`4bac1f7730f2fd7f1ff11e7de14f502c1bf3d7d8671de185187150e2b808731a`
before and after. Fixture HEAD/status, workspace HEAD/status, all three lifecycle
markers, residual containers, networks, volumes, and the temporary fixture
directory each reported explicit PASS. `E2E_RESULT` was
`primary_exit=0 cleanup_verification_exit=0 final_exit=0`.

## PR #14 remote verification

Commit `f611e5e891c3aaf901ccff816eb567631810f89a` was ordinary-pushed. Heavy run
`30913072675` completed successfully on that exact head:

- Docker build, Compose, and migration: PASS.
- Security and deterministic evals: PASS.
- Playwright: `25 passed`, `3 skipped`, raw exit `0`.
- Fixture HEAD/status, workspace HEAD/status, all lifecycle markers: PASS.
- Workspace payload digest:
  `dd4cdcc07036d5e60ae0d53c7250695ce16d342485086134a11a7cc262e0fd93`
  before and after; `workspace-tree` PASS.
- Cleanup containers, networks, volumes, and temporary fixture directory:
  PASS; final exit `0`.
- Workspace Chaos: PASS; source repository and `.git` fingerprint unchanged.

Fast run `30913072708` had two independently attributed failures:

- Python direct tests reproduced the existing PR #15 deadlock in
  `test_concurrent_suite_create_consumes_one_grant_exactly_once[True]`:
  `1 failed`, `350 passed`, tuple `(0,1)` in `validation_runs`. PR #14 does not
  modify or rerun around this product failure.
- Web format-check identified only this newly added evidence file as
  unformatted. This in-scope documentation issue is corrected in a normal
  follow-up commit and requires a fresh CI run.

Documentation-only commit `91a272560511882d96acf0957ec4e10be69cffb5`
corrected that formatting without changing the helper, wrapper, or tests. On
that exact head, Fast run `30913943585` passed all five jobs and Heavy run
`30913943104` passed all three jobs:

- Playwright reported `24 passed`, `1 flaky` successful retry, and `3 skipped`;
  the suite raw exit was `0`.
- Fixture HEAD/status, workspace HEAD/status, and all lifecycle markers passed.
- Workspace payload digest
  `dd4cdcc07036d5e60ae0d53c7250695ce16d342485086134a11a7cc262e0fd93`
  matched before and after.
- Cleanup containers, networks, volumes, and temporary fixture directory
  passed with final exit `0`.
- Workspace Chaos passed with the source repository and `.git` fingerprint
  unchanged.

The child PR's rebased head and stacked workflow state are live GitHub state
reported separately after the final base head is published; they are not
embedded here because doing so would require changing the base again.

## Tooling corrections retained in the record

- The GitHub CI inspection helper was first invoked with unavailable `python`
  and exited `127`; the same read-only inspection under `python3` completed and
  identified the failing Heavy run. This did not mutate the repository.
- Ruff format checks exited `1` twice during implementation for mechanical
  line wraps, including once after strengthening a test assertion. After
  formatting, the first lint check exited `1` for import ordering; Ruff applied
  that mechanical fix and the final format/lint checks exited `0`.
- `uv run python -m unittest -v scripts/test_workspace_payload_manifest.py`
  exited `1` because module-mode execution did not add `scripts/` to the import
  path. The intended direct-script command above ran all cases and exited `0`.
- The first PR #14 Fast run exited nonzero for the known PostgreSQL deadlock
  and this Evidence file's Prettier formatting. The database behavior is left
  to PR #15; the documentation formatting is corrected without rewriting PR
  #14 history.

## Changed files and authority

- `scripts/run-e2e.sh`: replaces only the workspace-tree subcheck and preserves
  every existing suite, HEAD/status, lifecycle, primary-exit, and cleanup gate.
- `scripts/workspace_payload_manifest.py`: dedicated deterministic manifest,
  digest, and bounded mismatch diagnostics.
- `scripts/test_workspace_payload_manifest.py`: helper-only temporary fixture
  tests.
- This ExecPlan and evidence file.

Production business logic and existing product/PostgreSQL tests were not
modified. One dedicated helper test file was added. No retry, serial mode,
timeout change, ignored-file exemption, or CI skip was added.

No Provider or API key was connected. No license, tag, deploy, readiness,
merge, main movement, or remote branch deletion was performed.

## 2026-08-04 fail-closed race remediation evidence

### Exact preflight

- Physical root and Git top-level were both
  `/Users/danke/Developer/VisualEngineer`.
- The starting branch was `fix/validation-run-grant-deadlock` at
  `5a12a359ab1e33a5edbc69b3659e3e36ad9547a0`; tracked, staged, and untracked
  changes were empty. Stash and merge/rebase/cherry-pick/revert/bisect/
  sequencer state were empty.
- Local and remote `main` were
  `c310dab795d01a29c2ca8c5fe4aaeaeb8179bd4a` (ahead/behind `0/0`). Local,
  cached remote, live remote, and GitHub PR #14 heads were
  `a2281f956db6ef5354ee0fd0a4becc876392b03a` (ahead/behind `0/0`). The same
  four PR #15 observations were
  `5a12a359ab1e33a5edbc69b3659e3e36ad9547a0` (ahead/behind `0/0`).
- Backup refs were exact:
  `backup/pr15-pre-fingerprint-sync` at
  `8d660e0e9ad1535c08037e62c9d7f826ce0dfc8d` and
  `backup/pr15-pre-final-evidence-sync` at
  `95db82413418f7b6c216f05f10e4210bc170c837`.
- GitHub authentication was active. PR #14 was OPEN/DRAFT, based on `main`;
  PR #15 was OPEN/DRAFT, based on `fix/ci-e2e-post-gate`.
- The latest starting PR #14 Heavy run `30916010775` was successful. Fast run
  `30916017016` failed and remains a historical input to the post-push exact
  failure-attribution check.
- After the baseline passed, the checkout switched to
  `fix/ci-e2e-post-gate`; local HEAD and GitHub PR #14 HEAD matched exactly.

### Frozen PR #15 child identity

| Child path                                                                             | Starting blob                              |
| -------------------------------------------------------------------------------------- | ------------------------------------------ |
| `apps/api/src/visual_engineer_api/services/validation.py`                              | `0ff24a3c9fcc2e28ee25b1a88c461846758a0d17` |
| `apps/api/src/visual_engineer_api/services/validation_suite.py`                        | `a40065d5dd1909a600802ee0043d2b4850f13dee` |
| `apps/api/tests/test_phase5_validation_suites_remediation.py`                          | `a29d946f10a7e95916ee0629816d3b447aa143a3` |
| `apps/api/tests/test_validation_run_grant_deadlock_regression.py`                      | `0ed0e4ecb0f9d4419c58288e1d6445bfeb866c58` |
| `docs/evidence/validation-run-grant-deadlock-deterministic-regression-verification.md` | `2117e34fc6f38ef0fc695810683720c2fe28a7a2` |
| `docs/evidence/validation-run-grant-deadlock-remediation-verification.md`              | `e6f601664411c04bc3f1eb2aa5476491717d460f` |
| `docs/exec-plans/validation-run-grant-deadlock-remediation.md`                         | `026246f53f116ade7456a9a655cde1572a4df39e` |

The starting stable patch-id was
`7d8c499328266ce0959b54dbbbdae30817874b9e`. The dedicated regression test
SHA-256 was
`702e6810293ee193e0b6ae3bcb5cd099c7f9e4f974b4c3cd396647044f911f66`.

### Implementation checkpoint

- `UnsupportedWorkspaceEntryError` now rejects every entry outside the closed
  directory/regular-file/symlink union. The root `.git` byte name is removed
  before classification.
- Descriptor-pinned traversal compares `st_dev`, `st_ino`, full `st_mode`,
  `st_size`, `st_mtime_ns`, and `st_ctime_ns` at the required pre, descriptor,
  read, rescan, and post-path stages.
- Exactly two scans must match in canonical bytes and internal metadata. These
  identity fields are not serialized into the manifest.
- Diagnostics are globally capped at 20 deterministic records. Summary output
  includes the total and omitted count, while symlink targets are represented
  only by type, byte length, and SHA-256.
- `scripts/run-e2e.sh` is unchanged because its existing manifest-write error
  path already turns a typed helper failure into a failed workspace-tree
  postcondition without swallowing the nonzero exit.

### Validation ledger

| Command or case                                                                                                | Result                                                                          | Exit |
| -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ---- |
| `uv run python -m py_compile scripts/workspace_payload_manifest.py scripts/test_workspace_payload_manifest.py` | PASS                                                                            | `0`  |
| `bash -n scripts/run-e2e.sh`                                                                                   | PASS; wrapper unchanged                                                         | `0`  |
| `uv run python scripts/test_workspace_payload_manifest.py -v`                                                  | 22 PASS, 0 skip                                                                 | `0`  |
| real FIFO and Unix domain socket                                                                               | typed rejection; relative safe diagnostics                                      | `0`  |
| root `.git` file/directory/symlink                                                                             | excluded before classification                                                  | `0`  |
| pre-`lstat` to open replacement                                                                                | `WorkspaceSnapshotChangedError`                                                 | `0`  |
| descriptor-read in-place mutation                                                                              | `WorkspaceSnapshotChangedError`                                                 | `0`  |
| directory snapshot then add/delete/replace                                                                     | three typed fail-closed cases                                                   | `0`  |
| symlink replacement during `readlink`                                                                          | `WorkspaceSnapshotChangedError`                                                 | `0`  |
| processed file changed before overall completion                                                               | global two-snapshot mismatch                                                    | `0`  |
| opposite creation-order trees                                                                                  | canonical bytes and SHA-256 exact                                               | `0`  |
| diagnostic cap and target/body redaction                                                                       | 20 emitted of 25; 5 omitted                                                     | `0`  |
| `make source-invariance-check`                                                                                 | PASS; 118 source entries, 10 Git objects, 2 status records, 0 extension markers | `0`  |
| `git diff --check` before E2E                                                                                  | PASS                                                                            | `0`  |
| `CI=true make e2e`                                                                                             | 25 passed, 3 skipped; all postconditions and cleanup PASS                       | `0`  |

The two independently rooted creation-order manifests both produced
`0c7200f335b15c61752848ad8303165c6b85234ba7081f79de70482f8f3da343`.
Neither absolute root nor mtime/ctime was serialized.

The single local E2E produced `25 passed`, `3 skipped` in 1.9 minutes with no
flaky retry. Its workspace payload expected and actual digests were both
`4bac1f7730f2fd7f1ff11e7de14f502c1bf3d7d8671de185187150e2b808731a`.
Fixture HEAD/status, workspace HEAD/status, and all lifecycle-marker checks
passed. Compose-down and fixture removal passed; residual containers,
networks, volumes, and the fixture directory were all absent.
`E2E_RESULT` was
`primary_exit=0 cleanup_verification_exit=0 final_exit=0`. This was the only
local E2E run; full `make verify`, API-direct, historical repetition, broad
security/eval/migration, and a second E2E were not run.

During test development, the first Unix socket location exceeded the platform
AF_UNIX pathname bound and the 22-case run reported 21 PASS / 1 capability
skip. The fixture was narrowed to a real short `/tmp` root; the dedicated
socket case then passed and the final full 22-case run had no skip. No product
failure was rerun, and no timeout, retry, or assertion was relaxed.

The two Python files were mechanically normalized with
`uv run ruff format scripts/workspace_payload_manifest.py scripts/test_workspace_payload_manifest.py`;
the two documentation files were normalized with a path-limited
`pnpm exec prettier --write` invocation. Both formatter commands exited `0`.
Python compile/import and all 22 helper cases passed again on the formatted
files. Final `git diff --check`, exact four-path scope, and PR #15 blob,
patch-id, and regression-hash checks also exited `0`.

Commit/push, PR #14 exact-head CI, and stacked PR #15 synchronization remain
NOT YET VERIFIED.
