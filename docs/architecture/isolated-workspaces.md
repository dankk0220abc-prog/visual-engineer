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
closed. The adapter rejects links, alternates, HTTP alternates,
graft/replacement metadata, malformed refs/objects, and unsupported
indirection.

Starting only from the exact authorized commit, the adapter walks bounded
commit ancestry and tree/blob references. It parses canonical loose objects
and pack-index-v2/pack-v2-or-v3 normal/OFS-delta/REF-delta entries, validating
pack/index hashes, entry CRCs, object IDs/types/declared and decompressed
lengths, cycles, depth, tree entries, references, graph size, and cumulative
object/storage budgets. A gitlink is validated only as inert superproject
metadata: its target commit is not opened or imported and submodule recursion
stays disabled. Other refs, unreachable loose objects, unreachable packed
objects, and source dirty/untracked bytes do not join the closure.

Only the validated closure is materialized as mode-0600 Runner-owned loose
objects under new inodes; source zlib bytes are not blindly copied and no
source alternate is created. Existing mirror config, object format,
indirection paths, packs, loose objects, top-level metadata, exact detached
`HEAD`, and empty loose/packed ref namespace must already match the managed
identity and exact closure before reuse. New mirrors use an explicitly empty
template rather than host or source metadata. All Git subprocesses then
operate only on Runner-owned state. The adapter invokes one fixed Git
executable with argument arrays, `--no-replace-objects`,
`GIT_NO_REPLACE_OBJECTS=1`, and
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
4. verifies the exact approved commit exists and derives its source-less
   path/type/Git-mode/size/SHA-256 checkout manifest while charging every
   expanded path, including repeated paths through a shared tree, before an
   over-limit entry or its blob digest is created;
5. creates one unpredictable detached worktree below the workspace volume;
6. independently derives a descriptor-rooted no-follow Workspace manifest and
   requires exact equality, isolating any mismatch without recursive deletion;
   and
7. records root device/inode, source fingerprint, initial tree fingerprint,
   policy hash, and write ledger in a descriptor-validated registry.

Dirty tracked and untracked source content is not imported. Hooks do not run,
gitlink targets are not imported or recursively checked out, and Git LFS
pointers are not fetched.

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
unknown entries.

Before deletion it durably writes a domain-separated signed `pending` proof
that additionally binds Job/operation, Permit ID/sequence, Attempt, Lease,
current/proposed/job/operation digests, authorization timestamps, root
identity, and a proof nonce. After deletion it durably transitions that proof
to `completed` before the registry becomes terminal. A crash retry can
reconcile only those exact state combinations. Missing proof produces
`recovery_required`; signature/state/binding/replay contradiction produces
`quarantined`; expiry remains a typed Permit failure. Every terminal replay
also proves the expected root and original inode are absent. All rejection
paths preserve the Workspace or moved/replaced root, mirror, source, and
siblings. Exact authorized discard is idempotent.

An expired Workspace has a ten-minute cleanup window before its Grant expires.
If the Grant itself is revoked or expired, every new Runner operation is
rejected, including discard; operators must not bypass that fence. Automated
privileged garbage collection is not implemented in Phase 4.

## Phase 5 disposable validation sandbox

Validation never runs inside or writes to the canonical Workspace. One
validation-scoped Grant binds an exact sealed Checkpoint, revision, Workspace,
Profile/version, policy digest, run budget, and resource limits. Immediately
before dispatch, the Control Plane and Runner revalidate those bindings and the
Runner derives the exact current Workspace fingerprint.

A Suite-scoped Grant binds the same exact baseline to one immutable Suite and
its fixed Profile references. The Control Plane creates one disposable child
sandbox at a time; there is no shared Suite sandbox. Cancel, timeout, failure,
or cleanup uncertainty prevents the next sandbox from being created. Retry
requires a fresh Grant and creates new sandboxes only for incomplete steps;
successful immutable Evidence is reused without touching the canonical
Workspace.

Runner creates a UUID-addressed root below the dedicated validation volume and
copies only the fixed Profile's bounded, descriptor-opened, no-follow regular
inputs. Scratch and output directories exist only inside that root. The
system-owned child receives no user argv/cwd/environment and runs with
`python -I -S`; Linux Landlock limits filesystem access to the copied input and
per-run writable directories, and seccomp denies network syscalls. Absence of
either enforcement fails closed.

Output is streamed under one aggregate ceiling. Cancellation and the monotonic
deadline apply bounded process-group TERM/KILL, reap, pipe closure, and group-
absence verification. Artifacts are inventoried against the fixed
zero-artifact budget. The exact validation root must be removed and its
absence proved before a result can succeed. A process or sandbox cleanup
failure becomes `recovery_required`; it never authorizes recursive cleanup
outside the exact UUID-bound validation root. Canonical Workspace state and
fingerprints remain unchanged for pass, non-zero result, timeout, cancellation,
and recovery.

## Platform limitations

Python's portable standard library does not expose Linux `openat2` resolution
flags or `renameat2` compare-and-swap. The implementation therefore relies on
descriptor walks, no-follow opens, inode/link-count checks, an exclusive
same-directory temp, and fail-closed conflicts. The Runner is the only process
with the workspace volume, which removes the intended same-UID hostile writer
from the deployed local threat model, but this is not a hostile multi-tenant
sandbox guarantee.

Git combined output is streamed from nonblocking pipes into a fixed ceiling.
A monotonic deadline remains live until leader, pipe, and process-group
evidence are all terminal; timeout/overflow applies bounded group-wide TERM,
KILL, absence verification, reap, and pipe closure. Mirror import has explicit
pack, delta, tree, graph, reference, object-count, single-object,
decompressed-byte, pack-byte, expanded checkout-manifest path, and aggregate
destination ceilings. The manifest bound is inclusive and is enforced during
recursive construction rather than after a complete list exists. Compose also
bounds Runner CPU, memory, PIDs, and open files. These are local fixture
controls, not production quotas or hostile multi-tenant isolation.
Case-collision coverage is conditional on the source filesystem.

Historical audit FAIL decisions remain preserved for their inspected
revisions. Phase 4 is complete in local `main`; the Phase 5 fixture validation
sandbox is an implementation checkpoint pending independent focused review,
not a production or hostile multi-tenant sandbox claim.
