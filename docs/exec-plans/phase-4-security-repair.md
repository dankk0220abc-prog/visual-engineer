# Phase 4 Security Repair Sprint

- Started: 2026-07-28T16:17:38+08:00
- Branch: `fix/phase-4-security-remediation`
- Repair base / audit commit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4 implementation:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main baseline: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Security Gate at repair start: `FAIL`
- Status: REPAIR COMPLETE — READY FOR INDEPENDENT RE-AUDIT

## Goal

Close all six findings from the independent Phase 4 Workspace security audit
without changing the product boundary. Restore strict synthetic source
invariance, add current pre-side-effect Grant/Lease/Attempt authorization,
fail closed when Runner Workspace ownership cannot be proven, bound Runner
resources and Git output, pin supply-chain references, turn the four blocking
observations into permanent denial regressions, and leave one clean repair
checkpoint for a different auditor.

The repair implementer does not have authority to change the independent
Security Gate to PASS. The strongest possible local outcome is:
`REPAIR COMPLETE — READY FOR INDEPENDENT RE-AUDIT`.

## Scope

- Harden the Runner's fixed Git source adapter and managed Git subprocess
  boundary.
- Add a typed, short-lived, attempt-bound, single-use Side-effect Permit for
  Workspace prepare, text create/replace, baseline rollback, and discard.
- Add an explicit Grant revocation lifecycle with requested and effective
  states that accounts for in-flight permits.
- Add PostgreSQL persistence, constraints, indexes, and migration history for
  permits and revocation/recovery state.
- Add Runner-local signed Workspace ownership evidence and fail-closed
  quarantine/recovery behavior.
- Preserve descriptor-rooted file operations, atomic writes, expected hashes,
  budgets, and the closed typed job union.
- Add strict source-invariance, finding-regression, security-repair, chaos,
  runtime-isolation, migration, contract, frontend, and real-stack evidence.
- Update the API, Runner protocol, generated contract, Web status surfaces,
  Make/CI entry points, architecture, threat models, runbooks, and status.

## Non-goals

- No CreativeDeploy or any customer repository access or mount.
- No arbitrary shell, target-repository command, target build/test, LLM,
  Agents SDK, Git delivery, remote, push, pull request, tag, merge, deployment,
  authentication, or multi-tenancy.
- No change to `main`, the Phase 4 implementation branch, or the audit branch.
- No claim of hostile multi-tenant isolation, portable `openat2`/`renameat2`
  pathname CAS, or removal of the current single-Writer assumption.
- No deletion or weakening of the independent audit findings or reproductions.

## Trusted baseline

The following are CONFIRMED in this repair worktree before production edits:

- repository root resolves from `~/Developer/VisualEngineer`; the
  host-specific absolute path is intentionally not committed;
- audit branch head and repair base:
  `a560509b2018f86693e38e3646409f9e33841829`;
- Phase 4 implementation is the direct repair-base ancestor at
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`;
- `main` remains
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`;
- the audit, Phase 4, and main histories contain no unknown local commit;
- the pre-branch worktree was clean;
- no Git remote is configured;
- repository-local author name and email are present;
- the repair branch did not already exist and was created directly from the
  full audit hash;
- base Compose API, PostgreSQL, Runner, and Web services were running healthy;
- `docker compose config` rendered successfully; and
- `make workspace-security-audit` reproduced the four blocking observations:
  `4 passed`.

The exact audit diff is also CONFIRMED: it changed six files, adding 861 lines
and removing 20 lines. It added the audit test and three audit/evidence
documents and modified only `Makefile` and the project-status document outside
those additions.

## Findings repair matrix

| Finding         | Severity | Confirmed behavior and root cause                                                                                                                                                                                                                                                                               | Unauthorized side effect / blocking status                                                                                             | Production files currently affected                                                                                        | Existing reproduction                                                        | Planned repair                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Required regression and acceptance                                                                                                                                                                                                                                                                                                                        | Local status                                                     |
| --------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `VE-P4-AUD-001` | Critical | `GitOperations.inspect_source` runs working-tree Git commands while the source local config and per-tree attributes remain in scope. The closed fixtures prove source-configured fsmonitor and clean-filter helpers execute. Local-path `fetch` also makes source-side Git behavior part of mirror preparation. | Harmless external marker creation is CONFIRMED; Gate blocking.                                                                         | `apps/runner/src/visual_engineer_runner/git_ops.py`, Workspace registration/preparation callers                            | Two tests in `test_phase4_blocking_reproductions.py`                         | Stop invoking Git in the untrusted source. Read a narrowly validated ordinary `.git` object/ref snapshot without following links or alternates, copy objects byte-for-byte into Runner storage with new inodes, and run a fixed hardened Git command set only against Runner-owned mirror/worktree state. Conservatively report source dirty metadata as unknown rather than reading dirty/untracked content.                                                                                        | Hooks, filters, fsmonitor, external diff/textconv, credential helpers, LFS, submodule helpers, URL rewrites, and network markers remain absent; mirror has no alternates/shared inodes; dirty/untracked content is not imported; source file and `.git` manifests are exact.                                                                              | LOCAL REPAIR VERIFIED; INDEPENDENT RE-AUDIT REQUIRED             |
| `VE-P4-AUD-002` | Critical | `RunnerLifecycle` starts the typed executor after `start`; the first renewal may occur only after the file operation has already committed. Control Plane checks at start/renew/complete therefore are not transactionally before the durable Workspace side effect.                                            | A revoked Grant still permits a file replacement before completion is rejected; CONFIRMED and Gate blocking.                           | Runner lifecycle/client/manager, protocol, API Runner/Workspace services, models, repositories, migration, API/Web schemas | One in-process revocation test in `test_phase4_blocking_reproductions.py`    | Add PostgreSQL-backed Side-effect Permits acquired in one locked transaction over Runner, Job, Attempt, Lease, Grant, Workspace, Repository Handle, policy, operation, path, precondition, content digest, and budget. Permits are immutable, attempt/lease bound, short-lived, operation-digest bound, and single-use. Runner validates the permit immediately before any job-owned disk mutation and binds its ID to the local registry, result, Event, and Checkpoint.                            | Revoked/expired Grant, stale Lease/Attempt, cancellation before permit, wrong path/content/precondition, expired permit, and replay produce zero file side effects. One accepted permit maps to at most one disk operation and matching Event/Checkpoint. Crash retry does not repeat writes or budget. `revoke_effective` permits no later side effects. | LOCAL REPAIR VERIFIED; INDEPENDENT RE-AUDIT REQUIRED             |
| `VE-P4-AUD-003` | High     | When the registry is missing, discard treats a Git-clean worktree as owned. The status call excludes ignored entries, so unknown ignored content is invisible and `worktree remove --force` deletes it. No independent signed ownership proof exists.                                                           | Unknown ignored content and its Workspace are deleted; CONFIRMED and Gate blocking.                                                    | Runner Workspace registry/manager/Git discard, API Workspace states/events, migration, Web                                 | One missing-registry discard test in `test_phase4_blocking_reproductions.py` | Generate a Runner-only HMAC key in the credential volume. Create a canonical signed ownership manifest separate from the mutable registry and bind Workspace, Runner, Grant, Repository Handle, revision, policy, nonce, and root device/inode. Require DB/Permit, registry, signature, root identity, state, and a complete deletion inventory before discard. Missing proof enters `recovery_required`; inconsistent/tampered proof or unknown content enters `quarantined`; neither path deletes. | Missing/corrupt registry or manifest, tampering, wrong Runner/Workspace, wrong device/inode, unknown content, sibling Workspace, repeat/interrupted discard, and source/mirror confusion all fail closed with zero unintended deletion. Normal discard remains functional.                                                                                | LOCAL REPAIR VERIFIED; INDEPENDENT RE-AUDIT REQUIRED             |
| `VE-P4-AUD-004` | Critical | The strict audit manifest found mtime drift on the source root `.git` directory and nested submodule metadata directory. The exact production call responsible is NOT FULLY VERIFIED, but the invariance acceptance condition is disproved.                                                                     | Source Git metadata mutation is CONFIRMED; attribution remains NOT FULLY VERIFIED; Gate blocking.                                      | Source Git adapter, source fingerprint harness, smoke/E2E/chaos scripts                                                    | Audit before/after manifest evidence                                         | The `VE-P4-AUD-001` source-less Git design removes source Git processes. Add a no-follow, type-aware repeatable synthetic harness that compares branch, HEAD, refs, config, hooks, index, object inventory/inodes, tracked/untracked hashes, counts, and lstat metadata before/after.                                                                                                                                                                                                                | `make source-invariance-check` returns nonzero on any difference and PASS only on an exact before/after source and `.git` manifest. No runtime hashes or absolute paths are committed.                                                                                                                                                                    | LOCAL SOURCE INVARIANCE VERIFIED; RE-AUDIT REQUIRED              |
| `VE-P4-AUD-005` | Medium   | Runtime inspection found no explicit Runner CPU, memory, or PID limits; one Git path captures child output before applying a result-size check.                                                                                                                                                                 | Resource exhaustion was not demonstrated; the control gap is CONFIRMED. Non-blocking in the original audit but required in this batch. | `compose.yaml`, Workspace override, Git subprocess adapter, config/security checks                                         | Runtime inspection; no closed exploit fixture                                | Add explicit Runner CPU, memory, PID and file-descriptor limits to every applicable Compose profile. Replace unbounded Git capture with a streaming combined-output ceiling, timeout, and closed failure. Add bounded mirror-copy count/byte limits.                                                                                                                                                                                                                                                 | Rendered config and live `docker inspect` show limits; oversized output/mirror input fails closed without unbounded capture or partial ownership adoption.                                                                                                                                                                                                | LOCAL REPAIR VERIFIED; INDEPENDENT RE-AUDIT REQUIRED             |
| `VE-P4-AUD-006` | Low      | Compose image references and GitHub Actions use mutable tags/major references.                                                                                                                                                                                                                                  | Supply-chain substitution was not demonstrated; reproducibility gap is CONFIRMED.                                                      | `compose.yaml`, `.github/workflows/ci.yml`, relevant docs/checks                                                           | Configuration review                                                         | Pin external container and Action references to verified immutable digests/commit SHAs while retaining readable version comments. Add a local immutable-reference check.                                                                                                                                                                                                                                                                                                                             | No unpinned external image or `uses:` reference remains in the in-scope Compose/CI files; rendered Compose succeeds. Remote CI remains NOT VERIFIED.                                                                                                                                                                                                      | LOCAL REPAIR VERIFIED; REMOTE CI NOT VERIFIED; RE-AUDIT REQUIRED |

## Side-effect authorization design

The implemented mechanism is `SideEffectPermit`.

Each permit will bind:

- permit ID and monotonic per-Workspace sequence;
- Runner, Job, Attempt, Lease, Grant, Workspace, and Repository Handle IDs;
- source revision and policy hash;
- operation kind and normalized relative path or fixed Workspace scope;
- expected-current value (`absent`, file SHA-256, or current tree hash);
- proposed content or operation digest;
- canonical complete operation digest, including immutable state and the
  issued/consumed/expiry authorization window;
- issued, consumed, expiry, and terminal timestamps; and
- explicit state (`consumed`, `completed`, `failed`, `cancelled`, or
  `expired`).

The acquire endpoint creates and consumes the permit in one PostgreSQL
transaction after locking and checking the active identity and all authority
rows. It will reject cancellation, Grant revocation request/effect, expiry,
binding drift, operation mismatch, path mismatch, content/precondition
mismatch, budget failure, or idempotency conflict. The permit expiry will not
outlive the current Lease, Grant, Permission Envelope, or configured
short-lived permit window.

The Runner recomputes the canonical operation digest, validates every
binding and expiry immediately before the first job-owned disk mutation, and
pass the immutable permit into `WorkspaceManager`. A mutating manager call
without a matching permit will fail closed. Result completion will atomically
mark the permit completed and persist its ID on the corresponding Workspace
Event and Checkpoint. Typed failure/cancellation will terminalize the permit;
crashed in-flight permits expire and are never reusable by a later Attempt.

### Revocation semantics

Absolute instantaneous revocation across the Control Plane and a remote
Runner is not claimed.

- `revoke_requested`: blocks every new Side-effect Permit immediately in the
  committed Control Plane transaction.
- A permit already consumed is explicitly visible as in flight and remains
  bounded by its exact operation and short expiry.
- `revoked` / revoke effective: is set only after every permit for the Grant is
  completed, failed, cancelled, or expired, including the configured safety
  window needed for the Runner's pre-side-effect expiry check.
- Once effective, the Control Plane will never issue another permit and the
  Runner will reject every old permit. The local acceptance harness must prove
  zero side effects after the effective state.

This is a bounded fencing contract, not a claim that distributed revocation
can erase an operation already authorized and in flight.

## Workspace ownership and recovery design

The implemented ownership proof combines:

1. the locked PostgreSQL Workspace/Grant/Runner/Repository binding checked
   during permit acquisition;
2. the existing Runner registry, extended with Runner ID, creation nonce,
   permit lineage, and explicit local state;
3. a separate canonical ownership manifest signed with HMAC-SHA-256;
4. a key generated with system randomness, mode `0600`, and stored only in the
   Runner credential volume;
5. the exact Workspace root device/inode and managed-root boundary; and
6. a complete no-follow deletion inventory that includes ignored and unknown
   entries.

The key, signature input containing local paths, full source path, and file
content will not enter PostgreSQL, API responses, events, logs, or Git.

Missing proof is not reconstructed from a clean Git status or UUID-like
directory name. It becomes `recovery_required`. Contradictory proof, signature
failure, root-identity mismatch, or unknown content becomes `quarantined`.
Both states are visible and non-deleting. A future controlled recovery action
must establish new authority; this repair will not add a broad automatic
garbage collector.

## Data and migration plan

Create a new Alembic revision after the existing Phase 4 revision. Do not edit
old migrations.

Planned persistent changes:

- `execution_grants`: revocation-request timestamp and effective timestamp;
- `side_effect_permits`: all identity bindings, operation/precondition/content
  digests, sequence, state, timestamps, and unique idempotency constraints;
- `workspaces`: `recovery_required` and `quarantined` states plus recovery
  reason metadata if needed;
- `workspace_events`: permit/revocation/recovery/quarantine event types and a
  nullable permit reference;
- `workspace_checkpoints`: nullable permit reference.

The migration must use UTC-aware timestamps, explicit checks and indexes, and
support upgrade/downgrade/upgrade against real PostgreSQL. Concurrency tests
must use independent transactions.

## Protocol and contract plan

- Keep API persistence models out of the Runner protocol package.
- Add strict Pydantic Side-effect Permit acquire/response types and canonical
  operation-digest helpers.
- Reject extra fields and keep the 64 KiB protocol ceiling.
- Add permit IDs to mutating results/checkpoints and typed failure/cancel
  coordination only where required.
- Represent source dirty metadata conservatively as unknown without importing
  dirty or untracked source content.
- Regenerate OpenAPI and TypeScript from FastAPI source and require a no-drift
  repeat.
- Keep the closed typed job union and protocol prefix unless implementation
  proves a breaking version bump is required; record any such decision before
  changing it.

## Source invariance

`make source-invariance-check` will create a unique synthetic repository and
Runner state outside tracked source. A pure no-follow manifest will snapshot:

- root, branch, HEAD, porcelain-equivalent state metadata;
- tracked and untracked file hashes without committing generated evidence;
- `.git` HEAD, refs, packed refs, config, hooks, index, objects, worktree
  metadata, file counts, directory counts, inodes, link counts, modes,
  ownership, sizes, and nanosecond timestamps; and
- source-directory lstat metadata.

The harness will run registration, mirror preparation, a normal authorized
Workspace lifecycle, denial fixtures for untrusted Git extensions, and
discard. Any source difference is a nonzero result. The harness must never
access CreativeDeploy.

## Test plan

Narrow tests will run before aggregate gates.

1. Convert all four audit observations in place from proof of unsafe behavior
   to proof of denial and zero side effect while preserving Finding IDs.
2. Add Git adapter tests for hooks, filters, fsmonitor, LFS, submodules,
   credentials, URL/network helpers, source `.git` invariance, loose-ref
   parent symlinks, independent mirror objects, alternates rejection,
   opened-descriptor size races, aggregate destination-mirror ceilings, and
   bounded output/copy.
3. Add real-PostgreSQL permit tests for revoked/expired Grant, stale
   Lease/Attempt, cancellation, wrong path/content/precondition, expiry,
   replay, duplicate acquire, concurrency, budget, Event/Checkpoint binding,
   crash retry, and revoke effectiveness.
4. Add registry/manifest tests for missing/corrupt/tampered/wrong identity,
   inode/device drift, unknown/ignored content, sibling Workspace, repeated
   discard, interruption, quarantine, and normal closure.
5. Add Web unit and real-stack Playwright coverage for revoke-before-write,
   ownership mismatch/recovery UI, normal write, diff, checkpoint, rollback,
   discard, desktop, 390 px, axe, and horizontal overflow.
6. Extend Workspace chaos for permit-before-write, post-rename/pre-result,
   Grant revocation, Lease expiry, registry/manifest failure, stale Attempt,
   and source invariance.
7. Inspect rendered and live Docker CPU/memory/PID/FD, mounts, identity,
   capabilities, ports, private volumes, networks, egress, and credential-key
   location.

All PostgreSQL behavior will use PostgreSQL, not SQLite. Real-stack E2E will
not mock API or Runner.

## Safety assumptions and residual limitations

- Runner and its private credential/mirror/workspace/registry volumes remain
  trusted execution-plane state.
- API/Runner transport and local bearer credentials are development controls,
  not production identity.
- The Runner remains the sole Writer to each Workspace volume.
- Python still lacks portable `openat2` and `renameat2` pathname-CAS support;
  descriptor-rooted no-follow checks and the single-Writer boundary remain.
- No target repository code, hook, filter, submodule, LFS process, build,
  test, or shell is authorized.
- Only the committed synthetic fixture is in scope.

## Failure and correction ledger

| Time           | Classification          | Failure / invalid first method                                                                                                                               | Root cause                                                                                                                                        | Correction and rerun                                                                                                                          |
| -------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| repair start   | CONFIRMED historical    | Independent source invariance failed                                                                                                                         | Source `.git` directory mtimes changed; exact lifecycle attribution was not isolated                                                              | Preserve as open `VE-P4-AUD-004`; replace source Git execution and add a repeatable strict harness                                            |
| repair start   | CONFIRMED reproduction  | `make workspace-security-audit` reports `4 passed`                                                                                                           | The audit tests intentionally assert current unsafe observations                                                                                  | Convert the same Finding tests to denial assertions only after the production repair                                                          |
| implementation | TEST FAILURE            | First `make test-api` run could not truncate the new permit table safely                                                                                     | `side_effect_permits` was absent from test fixture cleanup ordering                                                                               | Add the permit table first in every exact PostgreSQL `TRUNCATE`; rerun focused API tests: PASS                                                |
| implementation | INVALID FIRST COMMAND   | A direct API test rerun could not connect to the test database                                                                                               | The prior test harness intentionally stopped its exact disposable `test-db` service                                                               | Start the exact Compose test profile and pass the active `TEST_DATABASE_URL`; rerun focused API tests: PASS                                   |
| implementation | TEST FAILURE            | Web Workspace surface test expected `Create text`                                                                                                            | The default fixture renders the existing `Replace text` action                                                                                    | Assert the actual default action label; rerun Web tests: 7 files and 41 tests PASS                                                            |
| implementation | COMMAND FAILURE         | Direct `uv run python scripts/check_source_invariance.py` could not import Runner packages                                                                   | This monorepo exposes Runner and protocol sources through explicit test paths rather than an installed root package                               | Set the two source roots in the stable Make target; `make source-invariance-check`: PASS                                                      |
| implementation | TEST FAILURE            | Permit digest denial test expected HTTP 403 but received typed HTTP 422                                                                                      | Policy/binding validation errors intentionally map to the API policy status                                                                       | Correct only the expected transport status while retaining the exact error-code assertion; focused API file: 8 tests PASS                     |
| implementation | CHECK FAILURE           | First static Finding check reported the required next-milestone label missing                                                                                | The initialized ExecPlan stated the re-audit boundary but did not include the exact milestone name                                                | Add the exact sole next milestone below and rerun the Finding check                                                                           |
| implementation | MIGRATION CHECK FAILURE | First downgrade after adding the Permit immutability trigger could not drop a trigger absent from the already-running local form of the uncommitted revision | The disposable database had been upgraded from an earlier worktree form of the same not-yet-committed migration                                   | Use `DROP TRIGGER IF EXISTS` in downgrade; rerun downgrade/upgrade against real PostgreSQL: PASS                                              |
| implementation | E2E TEST FAILURE        | Security E2E timed out clicking `Replace text` after effective revocation                                                                                    | The product correctly disabled destructive controls; the test tried to click a control whose disabled state was itself required evidence          | Assert disabled browser controls, issue a direct API write, require `409 execution_grant_inactive`, and inspect unchanged Runner volume       |
| implementation | E2E COMMAND FAILURE     | Security E2E Compose inspection lacked `E2E_REPOSITORY_PATH`                                                                                                 | Playwright received the Workspace fixture path but not the separate temporary adversarial API fixture path required by the rendered Compose files | Pass both exact temporary fixture paths into Playwright and the helper; script syntax/type/lint checks pass                                   |
| implementation | E2E TEST FAILURE        | Narrow-view old Phase 4 flow encountered strict-locator ambiguity after security flow retained multiple durable Grant records                                | Repeated project execution correctly displayed multiple identical policy values                                                                   | Scope the existing-value assertions to the first visible matching Grant policy without weakening the required text; full E2E rerun: 14 passed |
| implementation | CHAOS TEST FAILURE      | First repaired chaos run expected stale-Lease HTTP 409 but received protocol validation before the service fence                                             | The synthetic late write result generated distinct random Permit IDs for the result and its nested Checkpoint, so it was intentionally invalid    | Bind one synthetic Permit ID consistently, retain strict protocol validation, and rerun: PASS with three stale leases fenced and source exact |
| verification   | COMMAND RACE            | First `make format-check` failed while it ran concurrently with `make contracts-check`                                                                       | It observed generated `openapi.json` after export and before the contract target's Prettier step                                                  | Run contract generation and format checking sequentially; both then PASS                                                                      |
| verification   | INVALID FIRST COMMAND   | First runtime `docker compose ps -q` probe failed interpolation                                                                                              | Required synthetic `WORKSPACE_FIXTURE_REPOSITORY_PATH` was omitted                                                                                | Pass the exact generated `.runtime/workspace-fixture` path; render and live probes PASS; failed interpolation changed no container            |
| verification   | TEST FAILURE            | Permit-window test directly changed `expires_at` and expected an expired error                                                                               | The completed full-window digest binding correctly classified that mutation as tampering                                                          | Assert `SIDE_EFFECT_PERMIT_INVALID`; separately recompute a schema-valid past Permit and assert `SIDE_EFFECT_PERMIT_EXPIRED`; 38+8 tests PASS |
| verification   | INVALID FIRST COMMAND   | First combined pre-checkpoint artifact scan was rejected before execution                                                                                    | It included temporary-file deletion, which the command safety policy disallowed                                                                   | Replace it with pure read-only pipelines; Secret, type, size, binary, absolute-path, and runtime-artifact scans PASS                          |
| review         | PATCH CONTEXT FAILURE   | First multi-file no-follow patch application matched no context                                                                                              | The patch omitted the second file-update header and was rejected before changing either file                                                      | Reapply with explicit file headers; focused parent-symlink denial test PASS                                                                   |

New command failures, root causes, patches, and reruns will be appended here
without deleting earlier failures.

## Verification ledger

No command below is considered passed until it runs in this repair worktree
and exits zero.

| Command                                | Current status                                                                                                                                           |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make format`                          | PASS — 97 Python files unchanged; Prettier applied                                                                                                       |
| `make format-check`                    | PASS — Ruff format and Prettier drift checks                                                                                                             |
| `make lint`                            | PASS — Ruff and ESLint                                                                                                                                   |
| `make typecheck`                       | PASS — mypy 72 source files; TypeScript `tsc --noEmit`                                                                                                   |
| `make test`                            | PASS — 119 API/Runner/Protocol plus 41 Web tests; backend 81.63%; Web statements 72.35%, branches 67.12%, functions 71.89%, lines 74.22%                 |
| `make build`                           | PASS — Next.js 16.2.12 production build, seven routes                                                                                                    |
| `make contracts-check`                 | PASS — OpenAPI/TypeScript regenerate, format, and no drift                                                                                               |
| `make migration-check`                 | PASS — real PostgreSQL upgrade/downgrade/upgrade through `20260728_0005`                                                                                 |
| `make phase4-findings-check`           | PASS — six Findings, original FAIL preserved, production/regression/re-audit controls present                                                            |
| `make source-invariance-check`         | PASS — 119 source entries, 10 Git objects, 2 status records; zero difference/marker/alternate/shared inode                                               |
| `make workspace-security-check`        | PASS — 35 tests plus static security checks                                                                                                              |
| `make workspace-security-repair-check` | PASS — 39 Runner/Protocol plus 8 real-PostgreSQL API tests; one upstream warning                                                                         |
| `make security-check`                  | PASS — secret/static/Finding checks, 7 repository-scanner tests, 56 Runner security tests; upstream warnings preserved                                   |
| `make eval`                            | PASS — 58 deterministic cases/4 datasets plus 7 repository-scanner tests                                                                                 |
| `make e2e`                             | PASS — 14 real-stack browser tests, desktop and 390 px                                                                                                   |
| `make workspace-smoke`                 | PASS — authorized lifecycle, four denials, discard true, source exact                                                                                    |
| `make workspace-chaos-check`           | PASS — pre/post-commit crash recovery, three stale leases, budget replay false, effective-revoke side effects zero                                       |
| `make verify`                          | PASS — complete pre-checkpoint aggregate including contracts, migration, Docker config, E2E, chaos, security, Eval, invariance, Findings, and diff check |
| `docker compose config`                | PASS — exact synthetic fixture path supplied                                                                                                             |
| live `docker inspect` repair profile   | PASS — four healthy services; Runner resource, identity, mount, capability, network, key-mode, read-only, DNS, route, and egress controls confirmed      |
| `git diff --check`                     | PASS — pre-checkpoint diff clean                                                                                                                         |
| post-checkpoint required reruns        | Recorded only in final handoff after the immutable checkpoint; this committed plan cannot recursively record its own final hash                          |

Remote CI is NOT VERIFIED and will not be claimed.

## Documentation plan

Update the audit report and audit evidence without erasing the original FAIL,
and create separate repair evidence. Update `README.md`, `AGENTS.md`,
`PLANS.md`, `SECURITY.md`, architecture, threat models, tool permissions,
state/data models, Runner protocol, Workspace lifecycle/recovery runbooks,
project status, and the next actual ADR sequence for:

- hardened source Git snapshot adapter;
- Side-effect Permit and bounded revocation; and
- signed Workspace ownership and fail-closed quarantine.

Every document will distinguish original independent findings, local repair
evidence, and the still-required independent re-audit.

## Deviations

No authorized scope deviation occurred. During review, two conservative
refinements were added: the Permit digest covers its complete local
authorization window, and mirror budgets cover the opened source descriptor
plus all existing destination objects. Final review also made loose-ref
parent-directory no-follow validation explicit. Command-orchestration and
patch-context failures and their corrected reruns are recorded above; no
production boundary was expanded.

## Rollback

- The repair branch is isolated at the exact audit commit.
- Do not reset, clean, stash, rewrite, delete, merge, or modify the Phase 4,
  audit, or main branches.
- Code changes are recoverable through the final single repair commit; no
  remote exists and no push is authorized.
- Database changes use a new reversible migration. No production database or
  customer data is in scope.
- Runtime cleanup may stop/remove only exact repair-owned Compose projects and
  volumes created by repository scripts; never delete unknown directories or
  source/mirror/workspace data to manufacture a clean result.

## Completion conditions

1. All six findings have a concrete production change, regression, local
   result, remaining risk, and re-audit disposition.
2. All three Critical and the High original behaviors are denied.
3. Strict source invariance passes with zero source or `.git` difference.
4. Unauthorized filesystem side effect is zero for pre-permit revocation,
   expiry, stale Lease/Attempt, cancellation, bad binding, stale permit, and
   replay.
5. Revoke effective is not reached with an in-flight permit, and no operation
   is accepted after it becomes effective.
6. Unprovable Workspace ownership produces recovery/quarantine evidence and
   zero deletion.
7. Normal write, diff, checkpoint, rollback, and discard remain functional.
8. PostgreSQL migration/concurrency, protocol/contracts, Docker isolation,
   E2E, chaos, security, Eval, and aggregate verify all pass.
9. One commit named
   `fix(security): close phase 4 workspace audit findings` exists on the repair
   branch; the worktree is clean; no remote, push, main merge, customer access,
   or runtime artifact exists.
10. The final status is no stronger than
    `REPAIR COMPLETE — READY FOR INDEPENDENT RE-AUDIT`.

## Only permitted next milestone

Phase 4 Independent Security Re-Audit.

## Independent re-audit requirement

A different reviewer must freeze the repair commit, reread the preserved
findings, rerun every mandatory command and strict source/runtime proof, inspect
the full production diff and Docker runtime, and decide the Security Gate.
This repair work must stop before that review and must not update `main`.
