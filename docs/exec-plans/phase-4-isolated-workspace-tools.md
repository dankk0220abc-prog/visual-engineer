# Phase 4 ExecPlan: Runner-Owned Isolated Workspace and Scoped Typed File Tools

- Started: 2026-07-27T02:00:05+08:00
- Branch: `feat/phase-4-isolated-workspace-tools`
- Baseline: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Intended checkpoint message: `feat: add isolated workspace and scoped file tools`
- Status: READY FOR CHECKPOINT — FULL PRE-CHECKPOINT VERIFY PASSES
- Remote CI: NOT RUN; this repository has no remote

## Goal

Deliver a browser-first, independently authorized Level 1 execution path in
which only the Local Runner receives one configured read-only fixture
repository, copies the exact approved commit into a Runner-owned bare mirror,
creates a detached isolated workspace, and exposes only closed typed text-file
operations. Every write must be confined, reviewable through bounded status
and diff evidence, checkpointed, reversible to the initial baseline, and
disposable without changing the source repository or another workspace.

The observable completion flow is:

1. the browser shows an opaque available fixture repository;
2. a local user creates and independently approves an Execution Grant bound to
   an approved, non-stale Plan and exact Snapshot/revision;
3. a Runner prepares a mirror and detached workspace;
4. the user lists, reads, creates, and compare-and-swap replaces allowed UTF-8
   text;
5. denied paths, traversal, symlinks, stale hashes, and exhausted budgets fail
   with stable codes;
6. status, bounded textual diff, and immutable Checkpoints are visible;
7. rollback restores the initial tree and removes only files created by that
   workspace;
8. discard removes only the registered Runner-owned workspace; and
9. source `HEAD`, status, tracked files, untracked files, hooks, and `.git`
   evidence are unchanged before and after the full flow.

## Scope

The batch may change:

- FastAPI schemas, routes, services, repositories, models, and one new Alembic
  migration for Repository Handle, Execution Grant, decision, Workspace,
  Workspace Event, and Checkpoint state;
- Runner Protocol closed job/spec/result unions and stable policy errors;
- Runner local handle configuration, fixed Git mirror/worktree/status/diff
  operations, descriptor-rooted filesystem primitives, checkpoint, rollback,
  recovery, and disposal;
- the Next.js Repository, Execution Grant, Workspace, tool, diff, checkpoint,
  rollback, discard, and timeline surfaces;
- an adversarial synthetic Git fixture and isolated Compose profile;
- deterministic tests, Eval cases, OpenAPI/TypeScript generated contracts,
  Make targets, CI verification, security checks, runbooks, architecture,
  security, product, status, evidence, and ADR documents.

## Non-goals

This phase does not add:

- an LLM, model call, OpenAI Agents SDK, prompt-selected tool, or autonomous
  permission choice;
- CreativeDeploy access, mount, isolated write, target command, or any other
  Customer 0 change;
- a general shell, arbitrary subprocess/command, target install, package
  lifecycle, format, lint, typecheck, test, build, browser command, or public
  network;
- Docker socket, SSH material, repository URL, fetch, submodule
  initialization, Git LFS fetch, or hook execution;
- source-repository write, file delete/rename tool, binary write, branch,
  commit, push, pull request, merge, deployment, or remote CI claim;
- authentication, multi-tenancy, production hardening, Kubernetes, Electron,
  Tauri, Redis, Celery, Temporal, or Kafka.

## Trust boundaries and constraints

1. Web, API, and PostgreSQL never receive a target repository, mirror, or
   workspace mount and never store a Runner host path.
2. Only Runner local configuration maps an opaque handle to a source path.
   The committed Compose configuration receives the host path through an
   uncommitted variable and mounts only the synthetic fixture, read-only.
3. Plan approval is a governance decision, not execution authority. A separate
   immutable Execution Grant begins pending and requires a separate local-user
   approve/reject decision.
4. A Grant may only narrow an approved, current Plan/Snapshot and platform
   policy. Repository content, Task text, browser fields, or a Deployment Pack
   cannot broaden it.
5. Network policy is `none`; shell, source write, and Git delivery are false.
6. Runner Git uses fixed argument arrays with `shell=False`, bounded timeouts,
   disabled credential prompts, hooks, external diff/textconv, optional locks,
   global/system config, and all network protocols.
7. The source mount is read-only. Mirror creation copies objects without
   hard-linking mutable storage back to the source. Workspaces use exact,
   detached source revisions and do not import source dirty/untracked content.
8. File access is rooted in a Workspace directory descriptor. Each directory
   component is opened with directory/no-follow semantics; symlinks and
   non-regular files fail closed. String `resolve()` followed by an ordinary
   write is not an authority primitive.
9. Creates and replacements use a same-directory temporary file, restrictive
   mode, flush/fsync, descriptor-relative atomic rename, and post-write hash
   verification. A replacement requires the caller's expected current hash.
10. Rollback may restore tracked files and remove only Registry-recorded files
    created by the same Workspace under allowed paths. It may not recursively
    clean an unknown directory.
11. Discard accepts a Workspace ID, never a path, and must prove the registry
    identity and root containment before removing only that Workspace and its
    mirror worktree metadata.
12. Existing Lease/Fencing/cancellation rules remain mandatory for every
    workspace job. A stale attempt cannot commit durable state.
13. Real or external secrets must not be read. Adversarial tests use only
    dynamically generated synthetic canaries.

### Stop conditions

Stop the dangerous portion and preserve safe work if any mandatory condition
cannot be proven, including source read-only enforcement, symlink confinement,
atomic replacement, safe rollback/disposal ownership, stale-lease fencing,
mandatory test success, migration safety, token containment, clean Git state,
or avoidance of CreativeDeploy, shell, public network, and Docker socket.

Never use reset-hard, clean, stash, sudo, Homebrew, global Git configuration,
or broad recursive deletion.

## Repository Handle design

`RepositoryHandle` is Control Plane metadata with UUID identity, Runner ID,
opaque handle, display name, `git` kind, available/unavailable/revoked state,
closed capabilities, optional committed revision/branch, dirty boolean and
bounded path count, verification time, metadata version, and timestamps.

The browser can select only a handle previously registered by a Runner from its
local configuration. Neither registration nor user APIs accept or expose an
absolute source path. The Runner re-verifies the configured path, mount
read-only condition, Git root, exact revision, and source metadata before
workspace preparation.

## Execution Grant design

`ExecutionGrant` is an immutable policy row bound to Plan, Repository Handle,
source revision, Snapshot fingerprint, operation/path allowlists and denylists,
byte/file/diff budgets, TTL, and literal no-network/no-shell/no-delivery/
no-source-write fields. Canonical JSON excluding its own hash produces the
SHA-256 policy hash.

Production creation requires an approved Plan whose bound immutable Snapshot is
still current for the repository revision and fingerprint. The adversarial E2E
uses a real approved synthetic Plan through the same state machine. Grant
creation does not approve the Grant. `ExecutionGrantDecision` records one
independent local-user approve or reasoned reject decision. Policy fields never
mutate; status changes only through decision, revocation, or expiry services.

Denied paths have precedence and always include `.git/**`, `.env`, `.env.*`,
credential, token, key, and certificate classes. Paths are normalized relative
POSIX paths or controlled globs; absolute paths, NUL, dot/dot-dot components,
unbounded repository-wide write defaults, and shell strings are rejected.

## Workspace lifecycle

The Control Plane state machine is:

```text
requested -> preparing -> ready -> active -> sealing -> sealed
                     \-> failed
ready/active/sealed -> rollback_requested -> rolled_back
sealed/rolled_back/failed/expired -> discard_requested -> discarded
requested/preparing/ready/active -> expired
```

The exact allowed transitions are enforced by typed services and independently
constrained in PostgreSQL. Workspace rows store identifiers,
source revision, fingerprints/tree hashes, counts, bytes, active Attempt,
expiry, timestamps, and sanitized failure only. They never store a Runner
workspace path.

`WorkspaceEvent` has monotonic per-Workspace sequence, request ID, closed event
type, strict metadata schema, and UTC time. It records Grant approval,
workspace/mirror preparation, typed tool start/success/denial, diff/checkpoint,
rollback, seal, discard, expiry, and sanitized failure.

## Runner-owned mirror and workspace

- The Runner local registry maps a handle to the one read-only mount.
- A dedicated persistent volume holds one managed bare mirror per handle.
- Initial mirror population copies exact local Git objects; no alternates or
  hard links point to the source.
- Fixed Git configuration disables hooks, prompts, external helpers/diffs,
  optional locks, and protocols.
- Each Workspace gets an unpredictable Runner-registry directory in the
  workspace volume and a detached worktree at the Grant source revision.
- Initial tracked-tree and workspace fingerprints are recorded before any tool
  runs.
- Submodules stay gitlink entries, LFS stays a pointer, dirty/untracked source
  content is absent, and source hooks never run.

## Descriptor-safe filesystem

The Linux Runner implementation:

- parses a bounded relative POSIX path and rejects blank, absolute, NUL, `.`,
  `..`, excessive bytes, or excessive components;
- opens the Workspace root and every intermediate component through `dir_fd`
  with `O_DIRECTORY | O_NOFOLLOW`;
- uses descriptor-relative `stat`/`open` with no-follow behavior and `fstat`
  type/link-count checks;
- rejects symlinks, hard-linked writable targets, sockets, FIFOs, devices,
  binary data, invalid UTF-8, sensitive paths, `.git`, and files over budget;
- creates a restrictive deterministic-operation temporary regular file in the
  destination directory, write/fsyncs it, atomically publishes create by
  no-clobber link or replace by descriptor-relative rename after inode
  revalidation, fsyncs the directory, reopens safely, and verifies SHA-256;
- cleans only the known temporary name after failure; and
- fails closed when the host Python/OS cannot provide a required descriptor or
  no-follow primitive. macOS development tests may skip Linux-only race
  assertions with an explicit reason; the acceptance path runs in Linux
  Runner containers.

## Typed tools

Runner Protocol remains a closed union and adds:

- `workspace_prepare_v1`
- `workspace_list_v1`
- `workspace_read_text_v1`
- `workspace_write_text_v1`
- `workspace_status_v1`
- `workspace_diff_v1`
- `workspace_rollback_v1`
- `workspace_discard_v1`

Control Plane endpoints construct Job specs from validated user actions. The
browser cannot submit arbitrary Job parameters. Every assignment binds Runner,
Grant, Workspace, source revision, policy hash, active Attempt, and Lease.
Runner revalidates all bindings, Grant status/expiry, path policy, and budgets
immediately before execution.

Create requires `expected_absent=true` and an existing safe parent. Replace
requires `expected_sha256`; mismatch is `content_conflict`. Neither mode
creates arbitrary parent trees, deletes, or renames a user path.

Status and diff use only fixed Git operations and return bounded relative
paths. Diff disables external diff and textconv, rejects binary output, applies
Grant path scope, enforces its byte budget, hashes the returned artifact, and
creates an immutable Checkpoint.

## Checkpoint, rollback, and disposal

Checkpoint rows store only stable fingerprints, source revision, bounded
changed paths/count, diff hash/size, and a bounded redacted textual artifact or
reference. No absolute path, denied-path content, secret, full binary, or
over-budget diff is retained.

Phase 4 rollback supports only the initial source baseline. It restores changed
tracked text through fixed Git/workspace operations, removes only files the
Workspace creation ledger proves it created under allowed paths, verifies
clean status and the initial tree hash, and records events.

Discard is idempotent after sealed, rolled-back, failed, or expired states. The
Runner validates Workspace registry identity, removes the exact worktree from
the managed mirror with fixed Git, deletes only the exact registered workspace
directory, preserves the shared mirror and every other workspace, and records
completion.

## Resource budgets

The implementation deliberately narrowed the initial design values:

| Budget                      | Phase 4 bound |
| --------------------------- | ------------: |
| relative path bytes         |           512 |
| path components             |            32 |
| list depth                  |             4 |
| list entries                |           500 |
| protocol payload/result     |        64 KiB |
| one text read/write         |        32 KiB |
| cumulative submitted writes |       128 KiB |
| changed files               |             8 |
| textual diff                |        32 KiB |
| Workspace TTL               |    20 minutes |
| Execution Grant TTL         |    30 minutes |
| Git operation timeout       |    15 seconds |

The server derives these values; a caller cannot raise them. Denied paths take
precedence over `sandbox/**`.

## Current progress

### 2026-07-27

- DONE: verified the specified repository path, Phase 3 branch/commit, clean
  worktree, absent remote, repository-local Git identity, Compose state, ports,
  and online Runner.
- DONE: independently ran Phase 3 `make verify`, `make runner-smoke`, and
  `make runner-chaos-check`; all returned exit 0.
- DONE: inspected Phase 3 commit ancestry/diff, docs, runtime mounts, user,
  rootfs/capabilities, internal Runner network, failed public egress, and
  redacted logs.
- DONE: fast-forwarded `main` from `336b46d376e2c70013fa098fe54e6135ec816cd3`
  to `7590f9dcecbf06371936ac0265cecb9f7a4438ca` with no merge commit.
- DONE: reran contract drift, Runner/protocol tests, and live Runner smoke
  after the fast-forward.
- DONE: created `feat/phase-4-isolated-workspace-tools` at the Phase 3 commit.
- DONE: implemented protocol schemas, canonical Grant hashing, stable failure
  taxonomy, Repository Handle, Grant/Decision, Workspace/Event/Checkpoint
  models, typed APIs, state/authorization service, and additive migration.
- DONE: implemented Runner-local opaque handle mapping, read-only source
  verification, managed bare mirror, detached worktree, descriptor-safe file
  primitives, typed tools, checkpoints, baseline rollback, disposal, and crash
  recovery.
- DONE: implemented Repository/Grant/Workspace browser surfaces, write
  preflight, diff/checkpoint/timeline views, and focused frontend tests.
- DONE: implemented the versioned adversarial source, Runner-only Compose
  override, full-tree source fingerprinting, real smoke, abrupt-loss chaos,
  static security checks, and deterministic workspace Eval dataset.
- VERIFIED: backend/API/Runner/Protocol tests (101, 82.29% coverage), frontend
  tests (39, all coverage thresholds), 12-test real browser E2E, production
  build, contract drift, migration round trip, Docker config, static and
  adversarial security, 58-case Eval, real workspace smoke, and abrupt-loss
  workspace chaos have passed in the current worktree.
- VERIFIED: smoke and chaos preserved exact source HEAD/status/full-tree plus
  `.git` fingerprints; smoke created three Checkpoints and chaos fenced two
  stale leases with two prepare and two write Attempts.
- DONE: final documentation/ADR/CI closure and aggregate `make verify`.
- IN PROGRESS: staged security review and the single Phase 4 checkpoint.
- PENDING: post-commit verification, clean final worktree, and running
  handoff.

## Decisions

1. **Phase 3 accepted and fast-forwarded before Phase 4.** The exact baseline
   passed all mandatory independent checks and main was a strict ancestor.
2. **Runner local registry is authoritative for paths.** Control Plane keeps
   opaque handles only, so a compromised browser cannot submit a mount path.
3. **Mirror and workspace are separate managed roots.** Mirrors persist for
   reuse; workspaces are per-Grant/per-Workspace and disposable.
4. **No generic repository executor.** Eight closed job kinds preserve the
   protocol's discriminated-union and fencing design.
5. **Baseline-only rollback.** Checkpoints provide evidence in Phase 4, but
   arbitrary checkpoint restore is deferred to avoid unsafe partial deletion.
6. **Linux container is the security acceptance platform.** Descriptor and
   no-follow behavior is tested locally where supported and obligatorily in
   the Runner container; unsupported semantics fail closed.
7. **Grant budgets are materially narrower than the draft.** One text/diff is
   32 KiB, cumulative writes are 128 KiB, and at most eight files may change.
   This keeps protocol/results inside 64 KiB and bounds the fixture risk.
8. **Interrupted writes use a deterministic operation temp.** Retry removes
   only its exact one-link regular temp or reconciles a fully committed
   requested hash. It never guesses from a directory scan.
9. **Full source fingerprint is acceptance evidence.** `HEAD` and porcelain
   status alone miss `.git` or dirty/untracked content mutation, so smoke,
   E2E, and chaos hash every lstat/content entry before and after.
10. **Grant fencing is not bypassed for cleanup.** Workspace TTL is ten minutes
    shorter than Grant TTL so an expired Workspace can be discarded while
    authorized. Once the Grant is revoked/expired, every Job is denied.

## Risks

| Risk                                                | Likelihood / impact | Mitigation / next action                                                            |
| --------------------------------------------------- | ------------------- | ----------------------------------------------------------------------------------- |
| symlink/path replacement race escapes root          | medium / critical   | descriptor walk, no-follow flags, race harness, fail closed                         |
| hard link aliases a file outside intended ownership | medium / high       | require regular file and link count one for writes                                  |
| mirror shares mutable objects with source           | low / critical      | no-local-hardlinks clone/copy plus inode and source hash tests                      |
| rollback deletes an unknown file                    | medium / critical   | persistent per-Workspace created-file ledger and exact-path unlink only             |
| discard escapes registry root                       | low / critical      | opaque ID lookup, inode/root containment, no user path, sibling survival test       |
| stale Runner commits a tool result                  | medium / critical   | preserve three-part Lease fencing and active Attempt checks                         |
| Control Plane accepts an expanded Grant             | medium / critical   | Plan/Snapshot/revision binding, platform maxima, immutable trigger, canonical hash  |
| diff or audit leaks synthetic secret                | medium / high       | denied-path filtering, content classifier, output bounds, log/DB/API scans          |
| source fixture becomes writable                     | low / critical      | read-only bind, mount inspection, write-denial probe on synthetic fixture only      |
| migration weakens existing data                     | low / high          | additive migration, real PostgreSQL upgrade/downgrade/upgrade and data preservation |

## Discoveries

- `main` was exactly one commit behind Phase 3 and fast-forwarded without a
  merge commit.
- Phase 3 Runner currently mounts only its credential volume and joins only the
  internal API/Runner network. Public TCP egress returned network unreachable.
- The repository already has real PostgreSQL, generated contracts, real
  Runner Playwright, and isolated abrupt-loss chaos harnesses to extend.
- Phase 3 has no Runner repository code or subprocess executor, so Phase 4 can
  add a narrow fixed Git module without preserving a latent generic command
  surface.
- The local `.env.runner.local` is ignored mode-restricted state and was not
  read or printed.

## Failures and fixes

| Failure                                                 | Root cause                                                                                                               | Fix and regression                                                                                                              |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| fixture seed import failed                              | script execution did not include API/Runner source roots                                                                 | added explicit repository source paths; real seed/smoke exercises it                                                            |
| first live prepare returned `policy_denied`             | Phase 3 evidence validator hard-coded repository access `none`                                                           | workspace specs now require exactly `isolated_workspace`; regression covers both envelopes                                      |
| Phase 4 migration failed to insert workspace Job        | inherited `repository_access VARCHAR(16)` could not hold `isolated_workspace`                                            | migration widens it to 32 and downgrade restores 16; migration/API tests cover it                                               |
| test cleanup hit foreign-key errors                     | a raw `TRUNCATE` list omitted new related tables/order                                                                   | fixture cleanup includes Phase 4 tables with safe restart identity/cascade behavior                                             |
| initial combined coverage was 69.38%                    | new API/Runner modules landed before behavior tests                                                                      | added API state/authority and Runner adversarial tests; threshold was not lowered                                               |
| one pytest invocation got connection refused            | it was launched after intentionally stopping the test DB                                                                 | reran through the database-owning Make target; no product change or false pass                                                  |
| first Phase 4 Playwright run had two failures           | Grant state was asserted before the create/decision sequence settled; route announcer and business alert shared one role | wait for exact pending/approved states and scope policy alerts to `main`; regression passes in both viewports                   |
| local follow-up E2E invalidated the running source bind | fixture generator destructively rebuilt an already-mounted valid directory                                               | generator now validates/reuses version/revision/status/required paths; regression is repeated platform/E2E startup              |
| chaos configuration was rejected three times            | test values were below declared lower bounds: reaper 0.20/0.25, online 2/3, heartbeat 0.4/0.5                            | aligned harness with schema minima; full abrupt-loss chaos then passed                                                          |
| restart after atomic commit could replay ambiguously    | registry recorded pending intent but temp naming was random                                                              | deterministic operation temp plus committed-hash reconciliation and orphan-temp cleanup; interruption tests and real chaos pass |
| policy denial disappeared during browser polling        | typed-action catch set the error, then durable-state refresh cleared it                                                  | refresh clears errors only on explicit loading/retry; unit regression and real `.env` denial pass                               |
| later Playwright diff assertion was ambiguous           | the browser-created text appeared in the textarea and multiple Checkpoint diffs                                          | scope the assertion to Checkpoint 3's bounded diff artifact; clean E2E passes 12/12                                             |
| first final lint run found three Ruff errors            | seed-script bootstrap imports needed ordering plus deliberate late-import annotation                                     | sorted imports and applied exact `E402` annotations; rerun exits 0                                                              |
| frontend function coverage fell to 68.24%               | new typed lifecycle callbacks lacked unit interaction coverage                                                           | added list/status/diff/rollback interaction coverage; 39 tests pass and function coverage is 71.89%                             |
| registry cache could exceed its own 1 MiB read limit    | 128 bounded results can collectively exceed the registry file parser's hard cap                                          | ordered eviction now enforces the same byte cap before atomic save; regression drives 40 large results                          |

The unchanged upstream Starlette/httpx deprecation warning remains visible.

## Eval plan

`evals/datasets/workspace-tools-v0.1.jsonl` contains 15 deterministic cases
with stable expected outcomes and explicit test mappings for Grant policy,
relative paths, sensitive paths, symlinks, hard links, hash conflict,
atomicity, file/count/byte/diff budgets, source isolation, Checkpoint, rollback,
discard, stale Lease, cancellation, and failure classification. `make eval`
validates version/schema/outcome/mapping only and does not create a model
score. The current validator observation is 58 cases across four datasets plus
7 scanner tests.

## Verification ledger

Individual Phase 4 commands and the aggregate gate below have exited zero on
the exact current worktree. The post-checkpoint gate remains pending until
run.

| Command / evidence                             | Status   | Result                                                    |
| ---------------------------------------------- | -------- | --------------------------------------------------------- |
| Phase 3 `make verify` before merge             | VERIFIED | exit 0; 76 backend, 32 frontend, 10 browser               |
| Phase 3 `make runner-smoke` before merge       | VERIFIED | online + diagnostic success                               |
| Phase 3 `make runner-chaos-check` before merge | VERIFIED | offline/expiry/requeue/fence/recovery                     |
| post-merge contract drift                      | VERIFIED | exit 0                                                    |
| post-merge Runner/protocol tests               | VERIFIED | 11 passed                                                 |
| post-merge live Runner smoke                   | VERIFIED | exit 0                                                    |
| `make format`                                  | VERIFIED | exit 0; 92 Python files and Prettier                      |
| `make format-check`                            | VERIFIED | exit 0                                                    |
| `make lint`                                    | VERIFIED | exit 0; Ruff and zero-warning ESLint                      |
| `make typecheck`                               | VERIFIED | exit 0; mypy 70 files and TypeScript                      |
| `make test`                                    | VERIFIED | backend 101 at 82.29%; frontend 39                        |
| `make build`                                   | VERIFIED | exit 0; production Next.js build                          |
| `make contracts-check`                         | VERIFIED | exit 0; no OpenAPI/TypeScript drift                       |
| `make migration-check`                         | VERIFIED | PostgreSQL upgrade/downgrade/upgrade                      |
| `make workspace-security-check`                | VERIFIED | 25 tests plus static descriptor/isolation scan            |
| `make security-check`                          | VERIFIED | secret/static/scanner/42-test Runner gate                 |
| `make eval`                                    | VERIFIED | 58 cases across 4 datasets plus 7 scanner tests           |
| `make e2e`                                     | VERIFIED | 12 passed in 50.9s; desktop and 390 px                    |
| `make workspace-smoke`                         | VERIFIED | three Checkpoints; lifecycle and source unchanged         |
| `make workspace-chaos-check`                   | VERIFIED | retry/fencing/recovery/disposal and source unchanged      |
| `make verify`                                  | VERIFIED | exit 0; complete aggregate pre-checkpoint gate            |
| `docker compose config`                        | VERIFIED | base/test/workspace/E2E/Customer 0 variants               |
| `git diff --check`                             | VERIFIED | current worktree passes                                   |
| source `HEAD`/status/files/`.git` before-after | VERIFIED | exact full fingerprints unchanged in smoke/E2E/chaos      |
| browser desktop/390 px/axe/no-overflow         | VERIFIED | real Web/API/PostgreSQL/Runner/fixture, no mocked service |

## Deviations

- The draft proposed 128-KiB files, 512-KiB cumulative writes/diffs, 20 files,
  and a 30-minute Workspace. Implementation narrowed these to 32 KiB,
  128 KiB, 32 KiB, eight files, and 20 minutes respectively; Grant TTL remains
  30 minutes.
- Create uses descriptor-relative hard-link-then-unlink for no-clobber atomic
  publication; replace uses descriptor-relative rename after inode/link/hash
  revalidation. Python exposes neither Linux `openat2` nor `renameat2` CAS, so
  the local deployment makes Runner the only workspace-volume writer and
  documents that it is not hostile multi-tenant isolation.
- Case-collision fixture creation is conditional on filesystem support.
  FIFO/UNIX socket/hard-link and races are created dynamically in Runner tests.
- Git diff is rejected before persistence/return when over budget, but the
  child output is captured before that check rather than streamed under an OS
  byte quota.
- Workspace expiry has a ten-minute authorized discard window. Phase 4 does
  not add a privileged cleanup authority after Grant revocation/expiry.

## Rollback

- Stop only the exact Phase 4 Compose/E2E/chaos project names; preserve other
  projects and volumes.
- Before the checkpoint commit, reverse only inspected Phase 4 files with
  targeted patches. Never use reset-hard, clean, stash, or broad deletion.
- The additive Alembic downgrade will remove only Phase 4 triggers, tables,
  indexes, constraints, and enums after testing against a disposable
  PostgreSQL database.
- Fixture workspaces and mirrors are disposable Runner-owned test data. Cleanup
  must resolve exact registered workspace identities, not accept a path.
- Do not modify or clean the fixture source to recover a failed test; compare
  and report its unchanged/changed state, then stop dangerous operations if
  integrity is lost.
- Phase 4 will remain unmerged on its feature branch. No remote, push, PR, tag,
  deployment, or CreativeDeploy action exists to roll back.

## Completion conditions

1. Repository Handle, immutable/independently decided Execution Grant,
   Workspace/Event, and Checkpoint schema and state are implemented with
   reversible PostgreSQL migration evidence.
2. The Runner alone maps the opaque fixture handle to an exact read-only mount,
   prepares a no-hardlink managed mirror and detached exact-revision workspace,
   and never imports dirty/untracked source data or executes hooks/submodules/
   LFS.
3. Descriptor-rooted list/read/create/replace reject traversal, symlink/races,
   hard links, sensitive paths, non-regular/binary/invalid/oversized data, and
   enforce all Grant budgets.
4. Status/diff/Checkpoint, baseline rollback, and idempotent exact disposal are
   implemented and cannot touch the source or sibling workspace.
5. Every operation uses the existing Lease/Fencing/cancellation protocol and
   revalidates Runner/Workspace/Grant/revision/policy identity.
6. Browser flows A-E pass against real Web/API/PostgreSQL/Runner/fixture at
   desktop and 390 px with axe and no horizontal overflow, without mocked API
   or Runner.
7. Unit, integration, migration, contract, security, adversarial, Eval, build,
   Docker, E2E, smoke, chaos, and aggregate commands return exit 0.
8. Source hashes, status, `.git`, hooks, dirty/untracked state are exactly
   unchanged; no CreativeDeploy path is mounted or accessed.
9. Documentation and ADRs accurately distinguish implemented/verified facts,
   Linux/platform limits, local-only security, and every remaining non-goal.
10. The reviewed staged diff contains no secret, absolute personal path,
    unapproved binary/large/generated artifact, runtime state, or unrelated
    change.
11. Exactly one Phase 4 implementation commit exists on the Phase 4 branch;
    main remains at the Phase 3 commit, no remote/push/PR exists, the worktree
    is clean, and the platform remains running for browser inspection.

## Outcome and follow-ups

IMPLEMENTED AND FULLY VERIFIED before checkpoint in the local worktree. The
reviewed checkpoint and post-checkpoint gate remain required before Phase 4 is
complete.

Before Phase 5, perform a dedicated maximum-depth security audit of the
descriptor filesystem, mirror ownership, workspace deletion, Grant
authorization, Lease fencing, and all isolation evidence. Phase 5 may consider
controlled validation commands only after separate approval; Git delivery
remains a later independent milestone.

## Remaining limitations

Even on successful Phase 4 closure the product will still have no LLM, OpenAI
Agents SDK, prompt-directed execution, CreativeDeploy write, general shell,
target-repository install/build/test/lint/typecheck execution, Git delivery,
push, pull request, remote CI evidence, authentication, multi-tenancy,
production hardening, or production deployment.
