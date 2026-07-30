# Threat Model v0

## Scope and assumptions

This model covers the local single-user Web/API/PostgreSQL system, the
read-only Repository Scanner, deterministic planning, approval persistence,
optional exact-repository bind mounts, Runner Control Plane, and repository-free
Local Runner plus the Phase 4 synthetic-fixture isolated Workspace.
Browser/API/protocol input and every repository byte are untrusted. There is
no LLM, general tool executor, source/CreativeDeploy write, target command,
credentialed external integration, or production deployment.

## Threats, controls, and residual risk

| Threat                             | Current control                                                                                                                                                | Residual / future requirement                                                      |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Prompt injection                   | Repository instructions are untrusted provenance; risky classes are recorded but never followed. No LLM exists.                                                | Future model context must preserve provenance and independent policy.              |
| Path traversal or root confusion   | Scanner canonical root plus Workspace bounded descriptor-relative POSIX walk.                                                                                  | Production needs a maximum-depth Linux syscall audit.                              |
| Symlink escape                     | Scanner never follows tree links; Workspace uses `O_NOFOLLOW`, `fstat`, and race/conflict checks.                                                              | No portable `openat2`; hostile same-UID writer is outside scope.                   |
| Shell injection                    | Fixed subprocess arrays only; no `shell=True` or arbitrary command API.                                                                                        | Future tools require closed schemas and validated arguments.                       |
| Git hook/alias/credential abuse    | Global/system config disabled; hooks redirected; prompt and network protocols disabled; fixed built-ins only.                                                  | Future remote Git requires isolated config and least-privilege credentials.        |
| Dirty/untracked data leak          | Facts and mirror come from committed objects; detached Workspace excludes source dirty/untracked content.                                                      | Real repository authorization remains future work.                                 |
| Sensitive file/value leak          | Name denylist before read, selected-content canaries, sanitized API/DB/audit/log assertions.                                                                   | Broader classifiers, retention, and incident response are future work.             |
| Binary/oversized denial of service | Known/detected binary skip; tracked, selected, per-file, total, symlink metadata, path, and timeout budgets.                                                   | OS/container CPU and memory quotas are still limited.                              |
| Dependency lifecycle execution     | Script names parsed as data; no install/import/build/test; dependency trees skipped.                                                                           | Future Level 2 needs registry and lifecycle policy in isolation.                   |
| Submodule/LFS network access       | Gitlink and pointer recorded only; protocols disabled; no init/fetch.                                                                                          | Future opt-in fetch needs destination and integrity policy.                        |
| Snapshot tampering                 | One per Run, fingerprint binding, database trigger rejects update/delete.                                                                                      | Backup/restore and retention are not implemented.                                  |
| Stale or duplicate Plan decision   | Latest-version gates, Run/Plan row locks, one-decision uniqueness, stable conflict, identical replay.                                                          | Multi-user attribution/signature/expiry are future work.                           |
| Approval confusion                 | UI and schema state `execution_available=false`; approved is terminal with no executor.                                                                        | Future elevation needs a distinct permission grant and expiry.                     |
| Audit/source leakage               | Metadata allowlist; no comments, source corpus, secret matches, full exception, or host path.                                                                  | Central retention/access controls are future work.                                 |
| Docker privilege or mount spread   | API/Web non-root; API-only read-only target mount; no socket/privileged; exact root.                                                                           | Containers are not a hostile-code sandbox; future execution needs one.             |
| SSRF / remote locator              | Local absolute path required; `protocol.allow=never`; no fetch.                                                                                                | Future integrations need scheme/host/IP revalidation and egress control.           |
| Unauthorized external write        | Fixture-only Grant writes a Runner-owned worktree; sources and Customer 0 stay read-only/unmounted.                                                            | Any real target requires new authority and audit.                                  |
| Destructive Git                    | Scanner uses a fixed read-only command set; no target checkout/reset/clean/stash.                                                                              | Future Git levels need protected templates and recovery proof.                     |
| Public/API abuse                   | Loopback-oriented local deployment and bounded fields.                                                                                                         | Authn/authz, CSRF, rate limits, tenancy, TLS, and public hardening absent.         |
| Runner credential theft            | Random token, returned once, digest-only DB storage, dedicated mode-0600 volume, no body/auth logging.                                                         | Replace local bearer token with mTLS/workload identity and rotation.               |
| Duplicate/stale Runner execution   | `SKIP LOCKED`, one-active index, Runner/Attempt/Lease fencing, deadlines, advisory-locked reaper.                                                              | Multi-region scheduling is out of scope.                                           |
| Runner permission expansion        | Server-derived immutable Envelope; separate canonical-hash Grant; exact bindings; shell/source-write/delivery false.                                           | Target commands and real repositories need separate authorization.                 |
| Runner lateral movement            | Internal API-only network, no port, DB/Web/default network, customer/parent mount, Docker socket, SSH, or public egress.                                       | Production network policy and host hardening remain future.                        |
| Host repository path injection     | Runner-local opaque Handle map; user API and Control Plane never accept/store/return a source path.                                                            | Local mount/configuration administrator is trusted.                                |
| Source or dirty-state mutation     | Exact Runner-only read-only fixture bind; committed-object mirror; full source and `.git` fingerprints.                                                        | Host administrator and Git implementation remain trusted.                          |
| Workspace path/symlink escape      | Bounded POSIX parser, descriptor walk, `O_DIRECTORY`/`O_NOFOLLOW`, type/link-count checks, denied precedence.                                                  | No portable `openat2`; hostile same-UID workspace writer is outside scope.         |
| Partial or duplicated write        | Same-directory temp, fsync, atomic link/rename, expected hash/inode, deterministic retry reconciliation.                                                       | Filesystem durability semantics remain trusted.                                    |
| Grant or Workspace confusion       | Separate immutable Grant/decision, canonical hash, exact bindings, per-Lease revalidation, closed state machine.                                               | Enterprise identity and signed decisions are future.                               |
| Rollback/discard overreach         | Baseline-only restore, created-file hash ledger, UUID registry/root identity, sibling survival tests.                                                          | Privileged garbage collection after Grant expiry is not implemented.               |
| Stale final-review approval        | Locked freshness generation; validation/Suite/Evidence/Workspace/Checkpoint/Grant/blocker changes atomically invalidate old Packages and effective ready.      | Cross-service notification is pull-based; callers must read the effective verdict. |
| Forged readiness chain             | PostgreSQL reconstructs canonical Manifest, Package, Decision, blocker summary, and readiness digests from trusted rows; ready requires 0/0/0 blocking counts. | PostgreSQL role isolation and hostile multi-tenant hardening remain future work.   |
| Review-history rewriting           | Package-local event sequence, unique binding, immutable review records, and a database-wide append-only AuditEvent trigger.                                    | Audit retention, export, signatures, and external anchoring are not implemented.   |

## Abuse and reliability cases

- Equivalent mutation replay must not duplicate state; conflicting key reuse
  must return a stable conflict.
- A failed Snapshot stores only a stable code and public message and appends a
  redacted failure/policy event.
- Invalid transition, stale Plan, and different final decision must fail
  without changing durable state.
- Concurrent approve/reject must produce one decision row and one terminal Run
  status.
- Repository `HEAD`, status, and lifecycle marker paths must remain unchanged
  after synthetic end-to-end scanning.
- CreativeDeploy is observed before/after but never cleaned, reset, installed,
  built, tested, formatted, or write-probed.
- Concurrent Runner claim must create exactly one active Attempt.
- A lost Runner must become offline; expiry must requeue/fail predictably; an
  old Lease must receive `409` and cannot submit a result.
- `cancel_requested` cannot transition to success.
- A source fixture fingerprint mismatch must fail the gate; it is never
  repaired or cleaned in place.
- An interrupted atomic write must expose either the old or complete new file,
  never partial content, and its stale Attempt cannot commit.
- Rollback and discard must not affect the source or a sibling Workspace.

## Adversarial validation

The synthetic fixture covers prompt injection in root/nested instruction
files, fake environment/key files, an escaping symlink, oversized and binary
content, dependency trees, malicious lifecycle names, gitlink, dirty tracked
and untracked files, traversal/outside/root-symlink/network locators, timeout,
and count/byte budgets.

Tests assert committed-object provenance, stable fingerprints under worktree
changes, non-execution, no symlink/submodule/LFS follow, stable failure codes,
Snapshot immutability, API/DB/audit/log redaction, and unchanged target state.
Playwright exercises planning, Runner, Grant, Workspace, typed tool, diff,
checkpoint, rollback, and discard flows against real Web/API/PostgreSQL/Runner
on desktop and 390px with axe. Workspace chaos exercises abrupt loss during
prepare and atomic write, expiry, requeue, stale fencing, recovery, rollback,
disposal, and full source integrity. Detailed analyses are in the
[Local Runner Threat Model](runner-threat-model.md) and
[Workspace Threat Model](workspace-threat-model.md).

## Residual risk

Phase 4 remains a local prototype. It has no user authentication, hostile
multi-user isolation, hardened code sandbox, production workload identity,
credential rotation, production monitoring, backup/restore, or incident
response. The Foundation plan validator cannot authorize Runner dispatch or
repository work. The only Runner repository path is the read-only synthetic
fixture; real targets remain read-only and out of scope. A maximum-depth
security audit is mandatory before Phase 5.
