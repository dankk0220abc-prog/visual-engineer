# Threat Model v0

## Scope and assumptions

This model covers the local single-user Web/API/PostgreSQL system, the
read-only Repository Scanner, deterministic planning, approval persistence,
optional exact-repository bind mounts, Runner Control Plane, and repository-free
Local Runner. Browser/API/protocol input and every repository byte are
untrusted. There is no LLM, repository tool executor, target write,
credentialed external integration, or production deployment.

## Threats, controls, and residual risk

| Threat                             | Phase 2 control                                                                                                 | Residual / future requirement                                               |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Prompt injection                   | Repository instructions are untrusted provenance; risky classes are recorded but never followed. No LLM exists. | Future model context must preserve provenance and independent policy.       |
| Path traversal or root confusion   | Canonical absolute path, resolved allowlist, non-symlink root, local `.git`, exact top-level equality.          | Future archives/worktrees need descriptor-based safe path access.           |
| Symlink escape                     | Tree symlinks are classified from bounded committed metadata and never followed.                                | Future writers need safe open/write primitives and race resistance.         |
| Shell injection                    | Fixed subprocess arrays only; no `shell=True` or arbitrary command API.                                         | Future tools require closed schemas and validated arguments.                |
| Git hook/alias/credential abuse    | Global/system config disabled; hooks redirected; prompt and network protocols disabled; fixed built-ins only.   | Future remote Git requires isolated config and least-privilege credentials. |
| Dirty/untracked data leak          | Facts read from `HEAD` object IDs; worktree status is bounded paths only.                                       | Future write stage must isolate from user-owned work.                       |
| Sensitive file/value leak          | Name denylist before read, selected-content canaries, sanitized API/DB/audit/log assertions.                    | Broader classifiers, retention, and incident response are future work.      |
| Binary/oversized denial of service | Known/detected binary skip; tracked, selected, per-file, total, symlink metadata, path, and timeout budgets.    | OS/container CPU and memory quotas are still limited.                       |
| Dependency lifecycle execution     | Script names parsed as data; no install/import/build/test; dependency trees skipped.                            | Future Level 2 needs registry and lifecycle policy in isolation.            |
| Submodule/LFS network access       | Gitlink and pointer recorded only; protocols disabled; no init/fetch.                                           | Future opt-in fetch needs destination and integrity policy.                 |
| Snapshot tampering                 | One per Run, fingerprint binding, database trigger rejects update/delete.                                       | Backup/restore and retention are not implemented.                           |
| Stale or duplicate Plan decision   | Latest-version gates, Run/Plan row locks, one-decision uniqueness, stable conflict, identical replay.           | Multi-user attribution/signature/expiry are future work.                    |
| Approval confusion                 | UI and schema state `execution_available=false`; approved is terminal with no executor.                         | Future elevation needs a distinct permission grant and expiry.              |
| Audit/source leakage               | Metadata allowlist; no comments, source corpus, secret matches, full exception, or host path.                   | Central retention/access controls are future work.                          |
| Docker privilege or mount spread   | API/Web non-root; API-only read-only target mount; no socket/privileged; exact root.                            | Containers are not a hostile-code sandbox; future execution needs one.      |
| SSRF / remote locator              | Local absolute path required; `protocol.allow=never`; no fetch.                                                 | Future integrations need scheme/host/IP revalidation and egress control.    |
| Unauthorized external write        | No write tool or execution transition; read-only Customer 0 mount.                                              | Future isolated writer needs capability tokens, checkpoints, and audit.     |
| Destructive Git                    | Scanner uses a fixed read-only command set; no target checkout/reset/clean/stash.                               | Future Git levels need protected templates and recovery proof.              |
| Public/API abuse                   | Loopback-oriented local deployment and bounded fields.                                                          | Authn/authz, CSRF, rate limits, tenancy, TLS, and public hardening absent.  |
| Runner credential theft            | Random token, returned once, digest-only DB storage, dedicated mode-0600 volume, no body/auth logging.          | Replace local bearer token with mTLS/workload identity and rotation.        |
| Duplicate/stale Runner execution   | `SKIP LOCKED`, one-active index, Runner/Attempt/Lease fencing, deadlines, advisory-locked reaper.               | Multi-region scheduling is out of scope.                                    |
| Runner permission expansion        | Server-derived immutable canonical-hash Envelope; Runner-side validation; repository none/shell false.          | Future repository tools need separate isolation and authorization.          |
| Runner lateral movement            | Internal API-only network, no port, DB/Web/default network, repository, Docker socket, SSH, or public egress.   | Production network policy and host hardening remain future.                 |

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

## Adversarial validation

The synthetic fixture covers prompt injection in root/nested instruction
files, fake environment/key files, an escaping symlink, oversized and binary
content, dependency trees, malicious lifecycle names, gitlink, dirty tracked
and untracked files, traversal/outside/root-symlink/network locators, timeout,
and count/byte budgets.

Tests assert committed-object provenance, stable fingerprints under worktree
changes, non-execution, no symlink/submodule/LFS follow, stable failure codes,
Snapshot immutability, API/DB/audit/log redaction, and unchanged target state.
Playwright exercises planning and real Runner success/cancellation against the
real Web/API/PostgreSQL/Runner stack on desktop and 390px with axe. Chaos
exercises abrupt Runner loss, expiry, requeue, fencing, recovery, and success.
The detailed execution-plane analysis is in
[Local Runner Threat Model](runner-threat-model.md).

## Residual risk

Phase 3 remains a local prototype. It has no user authentication, hostile
multi-user isolation, hardened code sandbox, production workload identity,
credential rotation, production monitoring, backup/restore, or incident
response. The Foundation plan validator cannot authorize Runner dispatch or
repository work. The Runner must stay repository-free and the system must stay
local and read-only toward target repositories.
