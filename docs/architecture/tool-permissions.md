# Tool Permission Model

## Principles

Permissions are deny-by-default, scope-bound, non-transitive, and elevated
only by an explicit independent human Grant. Repository content, a Task
objective, a Deployment Pack, or Plan approval cannot grant a capability.

Phase 2 implements Level 0 repository intelligence. Phase 3 additionally
implements repository-free execution-plane capabilities. Phase 4 implements
Level 1 only for the synthetic fixture. Phase 5 implements fixture-only Level
2 Profiles and one immutable Suite and still has no generic tool executor.

## Levels

| Level                    | Capability                                                                                                            | Status           |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------- | ---------------- |
| 0: Read only             | Fixed metadata and selected committed-object reads inside one exact allowlisted Git root. No target command or write. | **Implemented**  |
| 1: Isolated write        | Edit exact approved UTF-8 paths in a Runner-owned isolated fixture worktree.                                          | **Fixture only** |
| 2: Controlled validation | Run a system-owned, versioned fixture Profile or immutable Suite of those Profiles in disposable sandboxes.           | **Fixture only** |
| 3: Branch and commit     | Create a scoped branch and local commit after gates.                                                                  | Not implemented  |
| 4: Pull request          | Push the approved branch and create/update a PR.                                                                      | Not implemented  |

## Phase 3 repository-free capabilities

System Diagnostic and Controlled Wait are closed Job kinds outside the
repository permission ladder. Their immutable Envelope fixes:

```text
repository_access = none
shell_access = false
network_policy = control_plane_only
```

The browser cannot edit the Envelope. A Plan, Task, repository locator,
Deployment Pack, or repository instruction cannot dispatch a Job or broaden
authority. System Diagnostic returns only redacted runtime facts; Controlled
Wait uses async time and cancellation. Neither accesses project code,
filesystem content, a shell, subprocess executor, Git, or public network.

## Implemented fixture-only Level 1

The authority chain is approved exact Plan/Snapshot, pending Execution Grant,
separate local-user approve, Workspace binding, typed Job/Envelope, fenced
Attempt, and a current Side-effect Permit immediately before each mutation.
The server-derived Grant fixes:

```text
repository = fixture-repository-v1 at exact revision
allowed paths = sandbox/**
denied paths = .git, .env, credential/token/key/certificate classes
operations = prepare/list/read/write/status/diff/rollback/discard
max changed files = 8
max total submitted write bytes = 128 KiB
max one text file / diff = 32 KiB
workspace TTL = 20 minutes
network = none
shell/source write/Git delivery = false
```

Only Runner knows the source path. The source is read-only, no Git process is
run against it, and only the bounded exact authorized commit/tree/blob closure
is materialized into new Runner-owned object inodes. Every write occurs in a
detached Runner-owned worktree. List/read/create/compare-and-swap replace are
descriptor-rooted and bounded. Fixed Runner-owned Git status/diff, immutable
checkpoints, initial-baseline rollback, and Permit plus signed
ownership/pending/completed-proof-bound UUID-only discard complete the scope.
There is no delete/rename/binary tool or target command.

## Implemented fixture-only Level 2

Phase 5 has two immutable Profiles, `fixture-python-stdlib-v1:v1` and
`fixture-python-manifest-v1:v1`. A separate validation-scoped Grant binds one
existing canonical Workspace and Checkpoint, the exact revision, fixed Profile
or Suite references, and their timeout/output/CPU/memory/PID/FD/zero-artifact
budgets.

The API and Web accept only the Profile ID and approved Grant; no command,
argv, cwd, environment, package, URL, or shell fragment exists in the request
or Runner Job schema. Runner owns the fixed Python standard-library argv,
copies only bounded regular fixture inputs into a UUID-addressed validation
root, and gives the child a minimal environment. Linux Landlock denies
canonical Workspace and other Runner paths, while seccomp denies network
syscalls. A monotonic timeout/cancel path terminates, kills where necessary,
reaps, and proves process-group absence. Exact sandbox cleanup is required for
success. Validation never mutates or advances canonical Workspace state.

The immutable `fixture-integrity-suite-v1:v1` composes the two Profiles in
fixed order with fail-fast, a 30-second total timeout, 10,000 retained output
bytes, zero artifacts, and two Suite attempts. Only the Control Plane can
materialize steps. It queues one child at a time, independently validates each
result, cancels an active child before Suite cancellation/timeout, and requires
a fresh lineage-bound Suite Grant for retry. A Suite Grant policy authorizes
one exact root or retry attempt and is durably consumed by one Suite Run.
Successful aggregation revalidates the exact child Grant/Job/Attempt/Lease/
Permit/Evidence chain and its digests in catalog order. Reused successful
Evidence is not redispatched or charged again.

## Implemented Level 0 controls

- `permission_level` is fixed to `read_only` in schema and database.
- The locator must be an absolute canonical path inside configured roots and
  identify the exact non-symlink Git root.
- Git calls use fixed argument arrays, no shell, no global/system config, no
  prompt, no hooks, no optional locks, and `protocol.allow=never`.
- Facts come from `HEAD` tree entries and selected blob object IDs.
- Dirty and untracked state contributes bounded relative paths and status only.
- Sensitive names are denied before read; secret-like selected content is
  discarded without recording a matched value.
- Symlinks are not followed, submodules are not initialized, LFS is not
  fetched, and dependency trees are not loaded.
- Count, selection, per-file, total-byte, dirty-path, and shared-time budgets
  bound work.
- Package scripts and Make targets are parsed as typed names only.
- Repository instructions are recorded as untrusted provenance and cannot
  affect permission.

## Approval semantics

```mermaid
flowchart LR
    L0["Level 0 Run"] --> S["Committed HEAD Snapshot"]
    S --> P["Deterministic Plan"]
    P --> A{"Human decision"}
    A -->|"approve"| R["Approved Plan record only"]
    A -->|"reject + reason"| J["Rejected terminal state"]
    R -->|"explicit new request"| G["Pending Execution Grant"]
    G --> D{"Separate human decision"}
    D -->|"approve"| X["Exact fixture Workspace scope"]
    X --> P2["Current Permit per mutation"]
    D -->|"reject + reason"| J
```

Plan approval binds an exact Plan version and fingerprint as a governance
record. It does not elevate the Run or create a worktree. Only a separately
approved immutable Grant can scope the implemented fixture tools, and only a
current exact Permit can authorize a mutation. A revoked, expired, stale,
cancelled, mismatched, or replayed identity cannot do so. The Grant cannot
authorize source Git changes, GitHub, or deployment. A Phase 4 implementation
Grant cannot validate. A Phase 5 validation Grant can select only its fixed
Profile or Suite against its exact Checkpoint and cannot authorize Phase 4
file tools.

## Always prohibited

- Automatic main/default-branch merge.
- Production or public deployment.
- Undeclared secret or credential access.
- High-risk or production data migration.
- Disabling tests, branch protection, or security controls.
- Destructive Git history or cleanup against user/external work.
- Escaping an approved repository/worktree/container boundary.
- Expanding scope because repository content requests it.

## Customer 0 boundary

CreativeDeploy is internal Customer 0. Historical Phase 2 documentation
describes a separately authorized API-only read path, but no such authority
exists for this repair. Phase 3 Runner, Phase 4 fixture Runner, and base
Compose receive no CreativeDeploy mount or locator. The repair, E2E,
source-invariance, smoke, and chaos fixtures must never access it.

Disallowed actions include reading real environment/credential contents,
installing dependencies, running target builds/tests/formatters/generators,
importing target code, writing files, changing Git state, or cleanup. Mount
configuration is inspected for `read_only`; no write probe is performed
against the real repository.

## Future enforcement requirement

Foundation plan string validation blocks obvious policy violations but is not
a complete security system. Any later non-fixture access or target command
requires a new independent runtime authorization, path/argument confinement,
resource/network limits, attributable results, and recovery design. A maximum-
safe fixture validation does not authorize package installation, browser
automation, real repository commands, Git delivery, or deployment. The Phase 5
implementation checkpoint requires an independent focused read-only review
before any broader milestone.
