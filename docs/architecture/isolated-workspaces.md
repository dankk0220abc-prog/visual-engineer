# Isolated Workspaces

## Scope

Phase 4 implements one Level 1 execution path against the versioned synthetic
fixture only. The Control Plane authorizes work; the Local Runner alone owns
repository paths, mirrors, worktrees, and file descriptors. No source
repository write, CreativeDeploy access, shell, target-repository command, Git
delivery, or public-network capability is present.

## Authority chain

```text
approved immutable Snapshot
  -> approved exact Plan version
  -> pending Execution Grant
  -> separate local-user Grant decision
  -> immutable Grant policy hash
  -> Workspace bound to Runner + Handle + revision
  -> typed Job + immutable Permission Envelope
  -> fenced Runner Attempt
```

Each link can narrow the preceding authority and none can widen it. Browser
input never supplies a host path, Git argument, command, Permission Envelope,
or arbitrary Runner Job parameters. Repository instructions, model-like text,
and Deployment Pack content are data only.

## Repository Handle

The Control Plane stores an opaque handle, display metadata, Runner identity,
closed capabilities, exact committed revision, dirty boolean/count, and
verification time. The opaque handle is registered only from the Runner's
local configuration. The host path is neither accepted by user APIs nor
returned by API/Web responses.

The fixture profile maps `fixture-repository-v1` to the exact read-only
`/repositories/fixture` mount inside Runner. Web, API, and PostgreSQL receive no
source, mirror, workspace, SSH, or Docker-socket mount.

## Mirror and detached worktree

`GitOperations` is the Runner's only subprocess boundary. It invokes one fixed
Git executable with argument arrays and `shell=False`, a sanitized
environment, timeouts, disabled prompts, hooks, external diff/textconv,
credential helpers, system/global configuration, and network protocols.

The Runner:

1. verifies the configured path is the exact Git root and its filesystem is
   read-only;
2. records `HEAD`, branch, and only a bounded dirty path count;
3. fetches local committed objects into a Runner-owned bare mirror without
   alternates back to the source;
4. verifies the exact approved commit exists;
5. creates one unpredictable detached worktree below the workspace volume; and
6. records root device/inode, source fingerprint, initial tree fingerprint,
   policy hash, and write ledger in a descriptor-validated registry.

Dirty tracked and untracked source content is not imported. Hooks do not run,
submodules remain gitlinks, and Git LFS pointers are not fetched.

## Descriptor-rooted file access

All typed file tools start from an already opened Workspace directory. A
relative POSIX parser rejects empty/absolute/backslash/NUL/control-character,
dot/dot-dot, over-512-byte, and over-32-component paths. Each intermediate
directory is opened relative to its parent with `O_DIRECTORY`,
`O_NOFOLLOW`, `O_NONBLOCK`, and close-on-exec where available.

Leaf descriptors are rechecked with `fstat`; symlinks, hard-linked writable
targets, FIFOs, sockets, devices, binary data, invalid UTF-8, denied/sensitive
paths, and oversized content fail closed. `.git` is denied case-insensitively.

Create and replace use a mode-0600 same-directory temporary file, complete
write, `fsync`, and a descriptor-relative commit. Create links only if the
destination remains absent. Replace compares the previously opened file's
device/inode immediately before `rename`; an identity change becomes
`content_conflict`. The parent is synced and the result is reopened and
SHA-256 verified. A deterministic operation temp name supports safe retry
after interruption.

## Budgets and artifacts

The Phase 4 server-derived Grant fixes:

| Limit                            |           Value |
| -------------------------------- | --------------: |
| changed files                    |               8 |
| cumulative submitted write bytes |         128 KiB |
| one text file/read               |          32 KiB |
| one textual diff                 |          32 KiB |
| list entries/depth               |         500 / 4 |
| workspace / Grant TTL            | 20 / 30 minutes |
| workspace protocol result        |          64 KiB |

`sandbox/**` is the sole allowed path scope. Denied sensitive patterns take
precedence. Status and diff return bounded relative paths only. Each successful
write and diff yields immutable fingerprint/checkpoint evidence.

## Rollback and disposal

Phase 4 rollback supports only the initial commit baseline. Fixed Git restore
handles tracked changes; the Runner removes only same-Workspace created files
recorded with their expected hashes. It then requires clean status and the
original tree fingerprint.

Discard accepts only a Workspace ID. Registry identity and the workspace root
device/inode are checked before the exact managed worktree is removed. The
shared mirror, source, and sibling workspaces are preserved. Discard is
idempotent.

An expired Workspace has a ten-minute cleanup window before its Grant expires.
If the Grant itself is revoked or expired, every Runner Job is rejected,
including discard; operators must not bypass that fence. Automated privileged
garbage collection is not implemented in Phase 4.

## Platform limitations

Python's portable standard library does not expose Linux `openat2` resolution
flags or `renameat2` compare-and-swap. The implementation therefore relies on
descriptor walks, no-follow opens, inode/link-count checks, an exclusive
same-directory temp, and fail-closed conflicts. The Runner is the only process
with the workspace volume, which removes the intended same-UID hostile writer
from the deployed local threat model, but this is not a hostile multi-tenant
sandbox guarantee.

Git diff output is bounded before persistence/return, but the Git child can
briefly allocate output before the parent rejects an over-budget result. The
fixture and write budgets bound the current case; production resource
isolation remains future work. Case-collision coverage is conditional on the
source filesystem. A maximum-depth security audit is mandatory before Phase 5.
