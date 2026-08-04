# E2E Workspace Payload Manifest Remediation

## Status

FAIL-CLOSED RACE REMEDIATION LOCALLY VERIFIED; PUBLICATION AND STACKED CI
PENDING. The original implementation and PR #14 remote-verification record
remains preserved below. This follow-up is limited to the same helper, its
focused tests, this plan, and its evidence. It does not authorize product,
PostgreSQL transaction, workflow timeout/retry, Provider, API key, license,
tag, deployment, readiness, or merge changes.

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
- Commit `f611e5e891c3aaf901ccff816eb567631810f89a` was ordinary-pushed to PR
  #14. Heavy run `30913072675` passed all three jobs, including remote
  Playwright `25 passed`, `3 skipped`, workspace-tree manifest equality,
  cleanup verification, and Workspace Chaos.
- Fast run `30913072708` exposed the known `validation_runs` PostgreSQL
  deadlock owned by PR #15 plus a Prettier failure in this new evidence file.
  The latter was corrected by documentation-only commit
  `91a272560511882d96acf0957ec4e10be69cffb5`; no PR #14 product/database fix
  was made.
- On that exact follow-up head, Fast run `30913943585` passed all five jobs and
  Heavy run `30913943104` passed all three jobs. The Heavy E2E reported
  `24 passed`, `1 flaky` successful retry, and `3 skipped`, with suite exit
  `0`; workspace-tree payload equality, all explicit postconditions, cleanup
  verification, and Workspace Chaos passed.
- PR #15 synchronization is performed only after publication of the final
  base head. Its resulting head and stacked workflow results are deliberately
  reported as live external state rather than embedded in this PR #14 plan.

## Rollback

Before publication, revert only this plan's allowlisted files. After publication,
revert the dedicated PR #14 remediation commit with a normal follow-up commit.
Do not reset, clean, or force-push PR #14.

## 2026-08-04 fail-closed race remediation

The final focused re-review identified three bounded gaps in the helper, not a
reason to reopen any prior product phase:

- `VE-SFFR-001`: FIFO, socket, device, and unknown entries were serialized as
  empty-content records instead of being rejected.
- `VE-SFFR-002`: a pathname-oriented, single-pass scan could miss replacement,
  read-time mutation, directory-entry mutation, or a change to an already
  processed file.
- `VE-SFFR-003`: the tests did not compare two separately created but
  semantically identical trees built in opposite creation order.

The narrow implementation contract is:

1. Admit only directory, regular-file, and symlink records. Exclude the exact
   root `.git` name before classification; reject every unsupported nested
   type with `UnsupportedWorkspaceEntryError` containing only a relative path,
   safe type/mode, and stage.
2. Traverse from pinned directory descriptors. Compare pathname pre-`lstat`,
   descriptor `fstat`, post-read `fstat`, post-path `lstat`, directory entry
   byte sets, and stable identity/metadata fields. Any inconsistency becomes
   `WorkspaceSnapshotChangedError`; there is no sleep or retry.
3. Build exactly two complete snapshots and require both canonical bytes and
   internal identity/metadata maps to match. Do not build a third snapshot.
4. Keep symlink target bytes fingerprint-sensitive in the canonical manifest,
   but replace raw targets in mismatch logs with byte length and SHA-256. Emit
   at most 20 deterministic entry diagnostics plus total and omitted counts.
5. Use real FIFO, Unix socket, file, directory, and symlink operations. Open
   race windows with `threading.Event`; do not mock a final manifest or typed
   exception.

Preflight matched the authorized baseline exactly: clean worktree and index;
no untracked files, stash, or in-progress Git operation; `main` at
`c310dab795d01a29c2ca8c5fe4aaeaeb8179bd4a`; PR #14 at
`a2281f956db6ef5354ee0fd0a4becc876392b03a`; PR #15 at
`5a12a359ab1e33a5edbc69b3659e3e36ad9547a0`; and both backup refs at their
expected SHAs. Both PRs were OPEN/DRAFT with the expected stacked bases. The
seven PR #15 paths, blob IDs, stable patch-id, and regression-test SHA-256 were
recorded before modification and must remain exact through the child rebase.

Local focused validation is VERIFIED: Python compile/import and Bash syntax;
22 focused helper tests with no skip; real FIFO and Unix socket rejection; all
required Event-synchronized race cases; creation-order equality; bounded,
redacted diagnostics; source invariance; and `git diff --check` passed. The
single authorized `CI=true make e2e` passed with `25 passed`, `3 skipped`, no
retry, exact workspace payload digest equality, all postconditions, and zero
cleanup residue. No second E2E and no full `make verify` were run.

Ordinary PR #14 publication, its exact-head Fast/Heavy contracts, and the
guarded PR #15 rebase and stacked CI remain NOT YET VERIFIED until completed
and recorded in the evidence file.
