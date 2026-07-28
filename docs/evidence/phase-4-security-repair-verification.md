# Phase 4 Security Repair Verification Evidence

- Date: 2026-07-28 (Asia/Shanghai)
- Repair branch: `fix/phase-4-security-remediation`
- Repair base / independent audit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4 implementation:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main baseline: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Independent audit result preserved: **Security Gate: FAIL**
- Local repair status:
  **REPAIR COMPLETE — READY FOR INDEPENDENT RE-AUDIT**
- Remote CI: NOT RUN; no remote is configured

## Evidence boundary

This is implementer-produced local repair evidence. It is not an independent
audit, approval, certification, merge decision, or Security Gate PASS. The
strongest permitted final status is
`REPAIR COMPLETE — READY FOR INDEPENDENT RE-AUDIT`.

All fixtures are generated synthetic repositories. CreativeDeploy and every
customer repository are prohibited and are not mounted or accessed. No LLM,
Agents SDK, target build/test, shell, Git delivery, PR, deployment, or
production data is in scope.

## Baseline

The repair started from the full independent audit hash on a new isolated
branch. `main`, Phase 4 implementation, audit, and repair histories remain
separate. The pre-edit worktree was clean, repository-local Git identity was
available, no remote existed, and the independent four-test reproduction
target returned `4 passed`, meaning the original blocking behaviors were
reproducible.

## Finding disposition

| Finding         | Severity | Root cause                                                                            | Repair-candidate production control                                                                                                                                                                                        | Regression evidence                                                                                                                         | Local disposition                                              |
| --------------- | -------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `VE-P4-AUD-001` | Critical | Source-working-tree Git allowed source configuration/attributes to influence helpers  | No Git process targets source; no-follow HEAD/ref/object validation; descriptor-size and aggregate destination budget enforcement; byte-for-byte copy into new Runner mirror inodes; managed fixed Git subprocess boundary | Preserved Finding reproductions assert zero marker; source-extension matrix; mirror alternates/inode/budget checks                          | LOCAL REPAIR VERIFIED; INDEPENDENT RE-AUDIT REQUIRED           |
| `VE-P4-AUD-002` | Critical | Start/renew/complete fencing was not current immediately before durable disk mutation | Immutable short-lived single-use Side-effect Permit acquired under PostgreSQL locks and revalidated at the filesystem boundary; full authority-window digest; requested/effective revocation                               | Missing/expired/mismatched/replayed/tampered Permit, stale Lease/Attempt, cancellation, digest/budget, real two-session revoke, crash retry | LOCAL REPAIR VERIFIED; INDEPENDENT RE-AUDIT REQUIRED           |
| `VE-P4-AUD-003` | High     | Missing mutable registry plus incomplete Git status did not prove Workspace ownership | Authenticated registry, separate HMAC-signed manifest, exact identity/root/inventory checks, recovery/quarantine with zero deletion                                                                                        | Missing/corrupt/tampered/wrong-mode/wrong-inode/ignored/unknown/sibling/interrupted/normal disposal cases                                   | LOCAL REPAIR VERIFIED; INDEPENDENT RE-AUDIT REQUIRED           |
| `VE-P4-AUD-004` | Critical | Source `.git` directory metadata changed during lifecycle                             | Eliminate source Git execution and compare a complete no-follow source/`.git` manifest over registration through discard                                                                                                   | Dedicated strict source-invariance harness                                                                                                  | LOCAL SOURCE INVARIANCE VERIFIED; RE-AUDIT REQUIRED            |
| `VE-P4-AUD-005` | Medium   | No explicit CPU/memory/PID/FD limits; child output captured before rejection          | Runner Compose limits plus streaming combined-output, process-group timeout, opened-object and aggregate mirror object/byte ceilings                                                                                       | Static config, oversized output/mirror tests, rendered/live runtime inspection                                                              | LOCAL REPAIR VERIFIED; INDEPENDENT RE-AUDIT REQUIRED           |
| `VE-P4-AUD-006` | Low      | Mutable external image and Action references                                          | In-scope Compose images pinned by digest; Actions pinned to full SHAs                                                                                                                                                      | Local immutable-reference Finding check and Compose render                                                                                  | LOCAL REPAIR VERIFIED; REMOTE CI NOT VERIFIED; RE-AUDIT NEEDED |

No finding is independently closed by this document. “Ready for re-audit” is
decided only after every local command below passes and one clean repair commit
exists; the actual Gate remains for a different reviewer.

## Proven repair mechanisms

### Source and Git

- Source path validation uses no-follow filesystem reads and accepts only the
  bounded ordinary Git layout needed by the synthetic fixture. Every loose-ref
  parent component is type-checked and rejected if it is a symbolic link.
- Source local/system/global configuration, hooks, attributes, filters,
  fsmonitor, external diff/textconv, credentials, LFS, submodule helpers, URL
  rewrites, and protocols never become an execution input.
- Committed objects are copied into Runner-owned storage with explicit
  count/byte ceilings checked against both the opened source descriptor and
  the aggregate existing destination mirror. Objects have new inodes and no
  alternate back-reference.
- Runner-owned Git runs with fixed arguments, fixed environment/config,
  no shell, streaming output bounds, and process-group timeout termination.
- Source dirty state is intentionally `unknown`; dirty and untracked content is
  neither imported nor inspected.

### Current mutation authority

- The Permit binds Runner, Job, Attempt, Lease, Grant, Workspace, Repository
  Handle, source revision, policy, operation, normalized path, precondition,
  proposed content/operation, state, issued/consumed/expiry timestamps,
  canonical digest, and deadlines. Local authorization-window tampering
  invalidates the digest before mutation.
- Acquisition validates those identities under PostgreSQL row locks and
  consumes one Permit. Runner validates it immediately before mutation.
- Permit authority is immutable in PostgreSQL and terminal states cannot
  transition. Result, Event, and Checkpoint permit identities must match.
- `revoke_requested` prevents new Permit acquisition immediately. Effective
  `revoked` is delayed until consumed Permits are terminal or expired.
- Retry may coordinate an already committed exact operation, but it does not
  apply or charge it twice.

### Ownership and disposal

- A mode-`0600` HMAC key lives only in the Runner credential volume.
- The entire canonical registry payload and a separate ownership manifest are
  domain-separated and authenticated.
- Discard requires a current Permit, exact database/local state, signatures,
  binding/nonce/root device/inode, managed-root boundary, and complete
  no-follow inventory.
- Missing proof produces `recovery_required`; contradiction or unknown content
  produces `quarantined`. Both preserve Workspace, mirror, source, and sibling
  state.

## Verification ledger

This table is updated only from commands actually run in this worktree.

| Command or probe                                      | Exit | Result                                                                                                                                                        |
| ----------------------------------------------------- | ---: | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| preserved `make workspace-security-audit` at baseline |    0 | 4 original unsafe observations reproduced before repair                                                                                                       |
| `make format`                                         |    0 | 97 Python files unchanged; Prettier applied                                                                                                                   |
| `make format-check`                                   |    0 | Ruff format and Prettier drift checks passed                                                                                                                  |
| `make lint`                                           |    0 | Ruff and ESLint passed                                                                                                                                        |
| `make typecheck`                                      |    0 | mypy passed for 72 source files; TypeScript `tsc --noEmit` passed                                                                                             |
| `make test`                                           |    0 | 119 API/Runner/Protocol tests and 41 Web tests; backend coverage 81.63%; Web statements 72.35%, branches 67.12%, functions 71.89%, lines 74.22%               |
| `make build`                                          |    0 | Next.js 16.2.12 production build passed; seven routes emitted                                                                                                 |
| `make contracts-check`                                |    0 | OpenAPI and TypeScript regenerated, formatted, and stable                                                                                                     |
| `make migration-check`                                |    0 | real PostgreSQL full upgrade to `20260728_0005`, downgrade to base, and re-upgrade passed                                                                     |
| `make phase4-findings-check`                          |    0 | six IDs/severities, preserved FAIL, production controls, regressions, and sole re-audit milestone present                                                     |
| `make source-invariance-check`                        |    0 | 119 source entries and 10 source Git objects exact; 2 status records; zero markers, alternates, shared inodes, or source differences                          |
| `make workspace-security-check`                       |    0 | 35 tests plus static Workspace security checks passed                                                                                                         |
| `make workspace-security-repair-check`                |    0 | 39 Runner/Protocol security tests plus 8 real-PostgreSQL API tests passed; one upstream warning                                                               |
| `make security-check`                                 |    0 | secret/static/Finding checks, 7 repository-scanner tests, and 56 Runner security tests passed; upstream warnings preserved                                    |
| `make eval`                                           |    0 | 58 deterministic cases across 4 datasets plus 7 repository-scanner tests passed                                                                               |
| `make e2e`                                            |    0 | 14 real-stack tests passed across desktop and 390 px; Web/API/PostgreSQL/Runner, axe, overflow, normal and denial flows                                       |
| `make workspace-smoke`                                |    0 | authorized lifecycle and four denials passed; discard true; source unchanged                                                                                  |
| `make runner-smoke`                                   |    0 | typed Runner job completed successfully                                                                                                                       |
| `make runner-chaos-check`                             |    0 | offline, expiry, requeue, stale fencing, recovery, final success, and source integrity passed                                                                 |
| `make workspace-chaos-check`                          |    0 | 3 stale leases fenced; pre-commit/post-rename recovery; 4 Attempts/2 charges; budget replay false; effective-revoke side effects 0; no residual; source exact |
| `docker compose config`                               |    0 | exact repair configuration rendered with immutable image references and required fixture variables                                                            |
| live Docker inspection                                |    0 | four healthy services; Runner limits, read-only mounts/rootfs, empty capabilities, isolated network, key mode, and denied write/egress probes confirmed       |
| `make verify`                                         |    0 | full pre-checkpoint aggregate, including E2E, chaos, security, Eval, source invariance, migration, contracts, Docker config, and diff check, passed           |
| `git diff --check`                                    |    0 | pre-checkpoint diff passed                                                                                                                                    |
| post-checkpoint required reruns                       |  N/A | performed only after the immutable repair checkpoint; exact results belong in the final handoff                                                               |

## Failure and correction ledger

Failures are preserved even after a successful rerun.

| Failure                                                                   | Root cause                                                                                                                                                     | Correction                                                                                         | Required regression                         |
| ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| API test cleanup could not truncate Permit table                          | New table was missing from exact fixture cleanup ordering                                                                                                      | Add it first in PostgreSQL `TRUNCATE` ordering                                                     | focused real-PostgreSQL tests               |
| Direct API rerun could not connect                                        | Disposable test DB had been intentionally stopped                                                                                                              | Start exact test profile and use its active URL                                                    | focused API file                            |
| Web unit expected `Create text`                                           | Fixture defaults to existing-file replace                                                                                                                      | Assert actual `Replace text` label                                                                 | full Web unit suite                         |
| Direct source script import failed                                        | Monorepo source roots were not installed at root                                                                                                               | Stable Make target exports Runner and Protocol source roots                                        | source-invariance target                    |
| Permit digest denial expected 403, got 422                                | Typed policy/binding errors intentionally map to validation status                                                                                             | Retain exact code assertion and correct transport status                                           | focused API file                            |
| Finding check missed exact milestone label                                | ExecPlan used equivalent prose without the required exact name                                                                                                 | Add sole exact milestone                                                                           | Finding check                               |
| Migration downgrade first missed a trigger                                | Local DB had an earlier uncommitted form of the same revision                                                                                                  | Make downgrade safely drop the new trigger with `IF EXISTS`                                        | downgrade/upgrade round trip                |
| First security E2E timed out clicking Replace                             | Product correctly disables destructive controls after effective revocation                                                                                     | Assert disabled UI, issue direct API write, require 409/code, inspect unchanged volume             | both Playwright viewports                   |
| First security E2E Compose helper lacked a required fixture variable      | Playwright received Workspace fixture path but not the temporary adversarial API fixture path                                                                  | Pass both temporary paths explicitly; keep them untracked                                          | full real-stack E2E                         |
| Narrow old Phase 4 E2E had strict-locator conflicts after multiple Grants | Valid prior Grant records render duplicate policy text                                                                                                         | Select the first visible policy item without weakening its value assertion                         | full real-stack E2E                         |
| First repaired chaos run received 422 instead of stale-lease 409          | Synthetic late write result used different random Permit IDs at result and nested Checkpoint, so strict protocol validation rejected it before service fencing | Generate one synthetic Permit ID and bind it consistently through the schema-valid late result     | Ruff/mypy and complete chaos rerun          |
| First `make format-check` failed during parallel orchestration            | It read generated `openapi.json` between contract export and Prettier                                                                                          | Run contract generation and format checking sequentially; no product code change                   | sequential format/contract checks           |
| First runtime Compose probe failed interpolation                          | Required synthetic `WORKSPACE_FIXTURE_REPOSITORY_PATH` was omitted                                                                                             | Supply the exact generated `.runtime/workspace-fixture` path; failed render mutated no container   | Compose render and live inspection          |
| Permit-window regression expected expiry after mutating signed data       | Changing only `expires_at` now correctly invalidates the full Permit digest                                                                                    | Assert tampering is invalid; construct a separately recomputed schema-valid past Permit for expiry | 38 Runner/Protocol + 8 API tests            |
| First combined pre-checkpoint artifact scan was rejected before execution | It included temporary-file deletion, which the command safety policy disallowed                                                                                | Replace it with pure read-only pipelines                                                           | Secret/type/size/binary/path/artifact scans |
| First multi-file no-follow patch application matched no context           | The patch omitted the second file-update header and was rejected before changing either file                                                                   | Reapply with explicit file headers                                                                 | focused parent-symlink regression           |

## Docker evidence

Live inspection confirmed:

- API, PostgreSQL, Web, and Runner services are healthy;
- Runner user is 10001, root filesystem is read-only, capabilities are empty,
  and `no-new-privileges` is set;
- CPU is 1, memory is 512 MiB, PIDs are 128, and nofile is 256;
- only Runner has the exact synthetic source mounted read-only;
- only Runner has private credential/mirror/workspace/registry volumes;
- API, Web, and DB have none of those mounts;
- Runner has no Docker socket or published port;
- Runner joins only the internal API control network, has no public default
  route, and cannot resolve DB or Web;
- ownership key exists only in the credential volume with mode `0600`, owner
  UID 10001, and size 32 bytes;
- source/rootfs write probes fail with read-only filesystem; and
- direct public `1.1.1.1:443` connection fails and the Runner route table has
  no default route.

## Residual limitations

- Independent re-audit has not occurred.
- No LLM, Agents SDK, Agent Trace, or nondeterministic model evidence exists.
- No shell, target-repository build/test, Git delivery, PR, remote CI, or
  deployment exists.
- No CreativeDeploy access exists.
- Authentication, multi-tenancy, hostile-code sandboxing, production
  deployment, quotas, backup, and incident-response controls remain absent.
- Portable `openat2`/`renameat2` pathname-CAS is absent. Descriptor-rooted
  no-follow checks and the sole Runner-Writer assumption remain current.

## Only next milestone

**Phase 4 Independent Security Re-Audit**
