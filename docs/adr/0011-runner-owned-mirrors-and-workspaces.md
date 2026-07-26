# ADR 0011: Runner-Owned Mirrors and Workspaces

- Status: Accepted
- Date: 2026-07-27

## Context

Source repositories must remain read-only while typed writes need an exact,
recoverable Git baseline. API, Web, and PostgreSQL must not gain filesystem
authority.

## Decision

Runner alone receives one exact read-only source bind. It copies committed Git
objects into a persistent managed bare mirror and creates one detached exact-
revision worktree in a separate Runner-owned volume per Workspace. Registry
records bind the Workspace UUID, Grant, Handle, revision, policy hash, source
fingerprint, root device/inode, write ledger, and completed operations.

Git is confined to one reviewed fixed-argument module with no shell, hooks,
helpers, credentials, external diff/textconv, submodule/LFS initialization, or
network protocols. Discard accepts a UUID and removes only the registered
worktree; mirrors are shared and preserved.

## Consequences

- Dirty/untracked source data is not imported and source `.git` is never
  changed.
- Mirror/workspace/registry volumes become sensitive Runner state requiring
  ownership, quota, retention, and recovery controls.
- Production use needs a maximum-depth audit and stronger garbage collection;
  Phase 4 is fixture-only.
