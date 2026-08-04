# E2E Workspace Payload Manifest Remediation

## Status

LOCAL IMPLEMENTATION VERIFIED; PUBLICATION NOT YET PERFORMED. This plan is
limited to PR #14's E2E workspace-tree postcondition,
its dedicated helper and tests, and verification evidence. It does not authorize
product, PostgreSQL transaction, workflow timeout/retry, Provider, API key,
license, tag, deployment, readiness, or merge changes.

## Baseline and failure

- Repository: `/Users/danke/Developer/VisualEngineer`
- `main` and `origin/main`: `c310dab795d01a29c2ca8c5fe4aaeaeb8179bd4a`
- PR #14 original head: `df68becd7474c8fbc7fd6401abd59560677ece1c`
- PR #15 original head: `8d660e0e9ad1535c08037e62c9d7f826ce0dfc8d`
- Both PRs were confirmed OPEN and DRAFT; PR #15 was based on
  `fix/ci-e2e-post-gate`; the worktree was clean.
- Heavy runs `30836566657` and `30837421817` reached successful Playwright and
  explicit HEAD/status/lifecycle checks, then failed only `workspace-tree`.
  Their recorded digest pairs were respectively `d0004af11da1318938329c402d8349ea257ce0e9d29681d887e9c8453fa9d830`
  to `0c4746b24b0380c236df795f93fb2be8afc5db8d0a5728e607bf5f1b9b1c5590`
  and `02f417d2532808e8ab01d5eb648739bc5bccb0653fc9b28bcbfc14dc3fd04eeb`
  to `d8edd132eacbcf67e625661278d8930198553fa567aff940405492de4185474b`.
- The historical digest-only check cannot identify the exact changed `.git`
  child, so this plan does not attribute the failure to a guessed subpath.

## Root cause and contract

The old E2E check reused `scripts/tree_fingerprint.py`, which recursively hashes
the complete workspace including top-level `.git`. Git transaction metadata is
not workspace payload and is already governed by the separate workspace
HEAD/status checks. Hashing it couples the payload postcondition to Git's
internal index/log/ref/worktree activity.

The replacement writes a canonical manifest outside the workspace. It excludes
only the root's direct `.git` entry, whether directory, file, or symlink. It
includes all other tracked, untracked, ignored, hidden, and nested `.git`-named
entries; directories including empty directories; symlinks; logical size; mode;
relative path; and file content SHA-256 or symlink target. Paths are encoded by
canonical JSON and byte-sorted, so line breaks do not become record delimiters.
It excludes timestamps, inode, ownership, absolute root, and traversal order.

## Implementation and validation plan

1. Add the dedicated manifest writer/digest/comparator.
2. Change only the E2E workspace-tree postcondition to use before/after
   manifests created under its external temporary fixture directory.
3. On mismatch, retain the digest failure and emit bounded added, removed, and
   changed entry metadata without file bodies.
4. Add a temporary-Git-fixture self-test for deterministic repeats, `.git`-only
   mutations, ignored/untracked/tracked changes, mode, symlink, empty directory,
   control-character paths, top-level `.git` forms, and timestamp/root absence.
5. Run `sh -n`, `bash -n`, `dash -n`, focused tests and injections, one
   `CI=true make e2e`, source invariance, and `git diff --check`. Do not run
   full `make verify`.
6. Commit and ordinary-push PR #14. Only after local success and push, rebase
   PR #15 onto the new base under the exact authorized force-with-lease.
7. Keep both PRs DRAFT and wait for focused independent re-review after stacked
   CI is green.

## Local outcome

- The dedicated helper and ten temporary-fixture tests are implemented.
- `sh -n`, `bash -n`, `dash -n`, Ruff format/lint, focused tests, source
  invariance, and diff whitespace checks pass.
- The single authorized `CI=true make e2e` passed with `25 passed`, `3 skipped`,
  unchanged fixture/workspace HEAD and status, unchanged payload manifest
  digest `4bac1f7730f2fd7f1ff11e7de14f502c1bf3d7d8671de185187150e2b808731a`,
  all lifecycle checks, and zero cleanup residue.
- No second E2E and no full `make verify` were run.
- Commit, push, PR #14 remote CI, PR #15 rebase, and stacked CI remain pending.

## Rollback

Before publication, revert only this plan's allowlisted files. After publication,
revert the dedicated PR #14 remediation commit with a normal follow-up commit.
Do not reset, clean, or force-push PR #14.
