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
  -> short-lived single-use Side-effect Permit before mutation
```

Each link can narrow the preceding authority and none can widen it. Browser
input never supplies a host path, Git argument, command, Permission Envelope,
or arbitrary Runner Job parameters. Repository instructions, model-like text,
and Deployment Pack content are data only.

## Repository Handle

The Control Plane stores an opaque handle, display metadata, Runner identity,
closed capabilities, exact committed revision, a conservative
`source_status=unknown`, and verification time. It does not run source
working-tree status or import dirty/untracked content. The opaque handle is
registered only from the Runner's local configuration. The host path is
neither accepted by user APIs nor returned by API/Web responses.

The fixture profile maps `fixture-repository-v1` to the exact read-only
`/repositories/fixture` mount inside Runner. Web, API, and PostgreSQL receive no
source, mirror, workspace, SSH, or Docker-socket mount.

## Mirror and detached worktree

`GitOperations` is the Runner's only subprocess boundary, but no Git process
is invoked against the source repository. A no-follow reader validates a
narrow ordinary `.git` layout, direct HEAD/ref data, and ordinary committed
objects. Loose-ref parent components are type-checked and symbolic links fail
closed. The adapter rejects links, alternates, graft/replacement metadata,
malformed refs/objects, and unsupported indirection.

Committed objects are copied byte-for-byte under object/byte budgets into a
new Runner-owned bare mirror with new inodes and no source alternate. The
opened source descriptor is rechecked against its byte ceiling, and existing
destination objects count toward aggregate ceilings across repeated
snapshots. All Git subprocesses then operate only on Runner-owned state. The
adapter invokes one fixed Git executable with argument arrays and
`shell=False`, a managed environment/configuration, process-group timeouts,
bounded streaming output, and disabled prompts, hooks, filters, fsmonitor,
external diff/textconv, credential helpers, LFS, submodule recursion, URL
rewrites, system/global configuration, and network protocols.

The Runner:

1. validates the configured path as an exact ordinary Git root and relies on
   the read-only container mount as an independent runtime boundary;
2. reads `HEAD`, branch, direct refs, and bounded committed object metadata
   without source Git execution;
3. copies the exact committed object closure into a Runner-owned bare mirror
   without alternates or shared inodes;
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

## Current mutation authority and revocation

Prepare, create/replace, rollback, and discard require a
`SideEffectPermit`. The Control Plane acquires it only after locking and
checking the current Runner, Job, Attempt, Lease/deadline, Grant, Workspace,
Repository Handle, revision, policy, operation, path/precondition/content
digest, and budget. The Runner recomputes the digest and checks the exact
binding, state, issued/consumed/expiry window, and expiry immediately before
the first durable mutation.

`revoke_requested` blocks every new permit. A consumed exact permit is exposed
as in flight and must become completed, failed, cancelled, or expired before
the Grant becomes effectively `revoked`. Effective revocation accepts no new
mutation and no old permit.

## Rollback and disposal

Phase 4 rollback supports only the initial commit baseline. Fixed Git restore
handles tracked changes; the Runner removes only same-Workspace created files
recorded with their expected hashes. It then requires clean status and the
original tree fingerprint.

Discard accepts only a Workspace ID plus a current exact permit. Before
removing anything it requires an authenticated registry, a separate valid
signed ownership manifest, matching Runner/Grant/Handle/revision/policy/nonce,
the exact Workspace root device/inode, an allowed local state, the managed
root boundary, and a complete no-follow inventory including ignored and
unknown entries. Missing proof produces `recovery_required`; contradictory
proof or unknown content produces `quarantined`. Both preserve the Workspace,
mirror, source, and siblings. Exact normal discard is idempotent.

An expired Workspace has a ten-minute cleanup window before its Grant expires.
If the Grant itself is revoked or expired, every new Runner operation is
rejected, including discard; operators must not bypass that fence. Automated
privileged garbage collection is not implemented in Phase 4.

## Platform limitations

Python's portable standard library does not expose Linux `openat2` resolution
flags or `renameat2` compare-and-swap. The implementation therefore relies on
descriptor walks, no-follow opens, inode/link-count checks, an exclusive
same-directory temp, and fail-closed conflicts. The Runner is the only process
with the workspace volume, which removes the intended same-UID hostile writer
from the deployed local threat model, but this is not a hostile multi-tenant
sandbox guarantee.

Git combined output is streamed into a fixed ceiling and the process group is
terminated on overflow or timeout. Mirror import has explicit object-count and
byte ceilings at the opened source descriptor and aggregate destination
levels. Compose also bounds Runner CPU, memory, PIDs, and open files. These
are local fixture controls, not production quotas or hostile multi-tenant
isolation. Case-collision coverage is conditional on the source filesystem.

The independent Phase 4 audit remains **Security Gate: FAIL**. This repair
design requires a Phase 4 Independent Security Re-Audit before merge,
CreativeDeploy, Customer 0, or Phase 5.
