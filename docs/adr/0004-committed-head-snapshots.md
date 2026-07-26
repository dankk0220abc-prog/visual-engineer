# ADR 0004: Committed-HEAD Repository Snapshots

- Status: Accepted
- Date: 2026-07-26

## Context

Customer repositories may be dirty, contain untracked work, symlinks,
dependency hooks, sensitive files, and adversarial instructions. Reading the
working tree would mix user-owned concurrent work into planning, make
fingerprints unstable, and enlarge disclosure and write risks.

## Decision

Phase 2 RepositorySnapshot facts are based exclusively on the verified current
Git `HEAD`. The scanner obtains the NUL-delimited tree, selects a bounded set
of entries, and reads committed blobs by object ID. Working-tree `status`
contributes only bounded relative-path/status metadata.

Sensitive files are denied before blob read. Symlinks are never followed,
submodules are never initialized, LFS objects are never fetched, and binary or
oversized content is not parsed. A canonical normalized payload produces the
fingerprint. One successful Snapshot may exist per Run, and PostgreSQL rejects
its update or delete.

## Consequences

- Dirty and untracked content cannot influence structured facts or
  fingerprint.
- Same `HEAD`, scanner, and policy inputs are reproducible.
- The Snapshot is intentionally incomplete; unselected source can contain
  constraints requiring later authorized inspection.
- Branch name and dirty metadata are observations, not fingerprint inputs.
- A changed `HEAD` requires a new Run/Snapshot rather than mutating history.
