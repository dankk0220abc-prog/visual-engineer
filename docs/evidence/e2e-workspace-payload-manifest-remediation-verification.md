# E2E Workspace Payload Manifest Remediation Verification

## Scope

This evidence covers only PR #14's deterministic workspace payload
postcondition. Production/API/Runner/Web transaction logic and PostgreSQL
regression semantics are unchanged.

## Confirmed remote failure evidence

| Heavy run | Playwright | Stable postconditions | Workspace digest pair | Cleanup |
| --- | --- | --- | --- | --- |
| `30836566657` | `24 passed`, `1 flaky`, `3 skipped`, suite exit `0` | fixture/workspace HEAD and status plus lifecycle markers passed | `d0004af11da1318938329c402d8349ea257ce0e9d29681d887e9c8453fa9d830` to `0c4746b24b0380c236df795f93fb2be8afc5db8d0a5728e607bf5f1b9b1c5590` | all four cleanup checks passed |
| `30837421817` | `25 passed`, `3 skipped`, suite exit `0` | fixture/workspace HEAD and status plus lifecycle markers passed | `02f417d2532808e8ab01d5eb648739bc5bccb0653fc9b28bcbfc14dc3fd04eeb` to `d8edd132eacbcf67e625661278d8930198553fa567aff940405492de4185474b` | all four cleanup checks passed |

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

| Command or case | Result | Exit |
| --- | --- | --- |
| Preflight exact refs, PR state/base/head, clean worktree | VERIFIED | `0` |
| `sh -n scripts/run-e2e.sh` | VERIFIED | `0` |
| `bash -n scripts/run-e2e.sh` | VERIFIED | `0` |
| `dash -n scripts/run-e2e.sh` | VERIFIED | `0` |
| `uv run ruff format --check scripts/workspace_payload_manifest.py scripts/test_workspace_payload_manifest.py` | VERIFIED after formatting | `0` |
| `uv run ruff check scripts/workspace_payload_manifest.py scripts/test_workspace_payload_manifest.py` | VERIFIED after import ordering | `0` |
| `uv run python scripts/test_workspace_payload_manifest.py -v` | ten focused cases VERIFIED | `0` |
| `.git`-only mutation keeps payload digest | VERIFIED by focused fixture | `0` |
| ignored/untracked/tracked/mode/symlink/empty-directory injections | VERIFIED by focused fixtures | `0` |
| only root `.git` excluded; nested `.git`-named paths included | VERIFIED by focused fixtures | `0` |
| manifest excludes absolute root and mtime and refuses in-root output | VERIFIED by focused fixture | `0` |
| `CI=true make e2e` | `25 passed`, `3 skipped`; all postconditions and cleanup VERIFIED | `0` |
| `make source-invariance-check` | 119 source entries and 10 Git objects compared; PASS | `0` |
| `git diff --check` | VERIFIED | `0` |

The successful local E2E payload digest was
`4bac1f7730f2fd7f1ff11e7de14f502c1bf3d7d8671de185187150e2b808731a`
before and after. Fixture HEAD/status, workspace HEAD/status, all three lifecycle
markers, residual containers, networks, volumes, and the temporary fixture
directory each reported explicit PASS. `E2E_RESULT` was
`primary_exit=0 cleanup_verification_exit=0 final_exit=0`.

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
