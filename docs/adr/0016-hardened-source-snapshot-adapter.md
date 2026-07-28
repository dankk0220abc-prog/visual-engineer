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

From the exact authorized commit, the adapter computes the bounded reachable
commit-ancestor/tree/blob closure itself. It parses canonical loose objects
and index-v2 plus pack-v2/v3 normal/OFS-delta/REF-delta entries without asking
Git to interpret source state. Pack/index checksums, CRC, object
type/hash/declared/decompressed length, delta/tree/graph depth, entry/reference
counts, cycles, pack bytes, selected-object bytes, and destination storage are
validated. Tag roots fail closed. Gitlinks are validated as inert
superproject tree entries, but their target commit is never opened, imported,
or recursively checked out.

Only selected objects are materialized as canonical mode-0600 Runner-owned
loose objects with new inodes; unreachable loose/packed objects and objects
reachable only from other refs are excluded. Existing mirror config,
indirection locations, object format, packs, and loose objects must already
match the exact managed identity and authorized closure. The mirror has no
alternate back-reference. All later Git subprocesses operate only on
Runner-owned state through one fixed plumbing adapter with:

- fixed argument arrays and no shell;
- managed config and a fixed environment;
- disabled hooks, filters, fsmonitor, external diff/textconv, credentials,
  prompts, optional locks, LFS, submodule recursion, URL rewrites, and network
  protocols;
- nonblocking-pipe, monotonic complete-process-group deadlines with bounded
  TERM/KILL/reap verification even after leader exit; and
- streaming combined-output bounds.

Source dirty status is reported as intentionally unknown. Dirty and untracked
source content is not imported or inspected.

## Consequences

- Source-controlled Git extension points cannot execute during registration,
  preparation, operation, rollback, or discard.
- Exact source and `.git` lstat/content/inode manifests can remain unchanged.
- Valid source and mirror objects may have different zlib bytes but must have
  identical canonical decompressed Git bytes, object IDs, types, and sizes.
- Unusual Git layouts fail closed instead of being normalized or repaired.
- The adapter supports only the committed synthetic fixture boundary; it is
  not a general repository importer.
- Any future source layout or Git command expansion requires a new security
  review and source-invariance regression.
