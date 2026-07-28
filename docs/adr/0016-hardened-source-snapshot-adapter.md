# ADR 0016: Hardened Source Snapshot Adapter Without Source Git Execution

- Status: Accepted for repair candidate
- Date: 2026-07-28

## Context

Running Git against an untrusted source working tree allowed repository-local
configuration and attributes to influence helper execution. It also changed
source Git-directory metadata, violating the exact source-invariance
requirement.

## Decision

The Runner invokes no Git process with the source repository as its working
tree, `--git-dir`, worktree, object database, or local fetch endpoint. A
no-follow snapshot reader accepts only a narrowly validated ordinary `.git`
directory, direct symbolic/detached `HEAD`, ordinary loose or packed refs, and
ordinary object files. It rejects links, alternates, replacement/graft
metadata, malformed refs/objects, unsupported layouts, and configured
indirection. Loose refs are traversed component by component and any symbolic
link in their parent directories fails closed.

Committed objects are copied byte-for-byte into a new Runner-owned bare mirror
under explicit object-count and byte budgets. The adapter checks the size of
the opened source descriptor, not only its prior directory entry, and applies
the ceilings to all existing destination objects so repeated snapshots cannot
accumulate unbounded stale data. Objects use new inodes and the mirror has no
alternate back-reference. All later Git subprocesses operate only on
Runner-owned state through one fixed plumbing adapter with:

- fixed argument arrays and no shell;
- managed config and a fixed environment;
- disabled hooks, filters, fsmonitor, external diff/textconv, credentials,
  prompts, optional locks, LFS, submodule recursion, URL rewrites, and network
  protocols;
- process-group timeout termination; and
- streaming combined-output bounds.

Source dirty status is reported as intentionally unknown. Dirty and untracked
source content is not imported or inspected.

## Consequences

- Source-controlled Git extension points cannot execute during registration,
  preparation, operation, rollback, or discard.
- Exact source and `.git` lstat/content/inode manifests can remain unchanged.
- Unusual Git layouts fail closed instead of being normalized or repaired.
- The adapter supports only the committed synthetic fixture boundary; it is
  not a general repository importer.
- Any future source layout or Git command expansion requires a new security
  review and source-invariance regression.
