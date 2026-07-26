# Local Runner Threat Model

## Scope

This threat model covers the Phase 3 local, single-user Control Plane, Runner
Protocol v1, PostgreSQL queue, independent outbound Runner, credential volume,
and the two repository-free Job kinds. Browser, protocol, database JSON, local
files, and container state are treated as untrusted at their boundaries.

The model does not claim hostile multi-tenant isolation or production
hardening. No LLM, repository access, shell, worktree, Git, Docker socket,
public network, deployment, or external integration exists in Phase 3.

## Assets

- Bootstrap and per-Runner tokens;
- Runner identity and liveness;
- immutable Permission Envelopes and policy hashes;
- Job/Attempt state, lease fencing identity, cancellation, and retry budget;
- typed results and RunnerJobEvent evidence;
- Control Plane and source-tree integrity.

## Threats and controls

| Threat                            | Phase 3 control                                                                                                                | Residual / future requirement                             |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| Bootstrap credential disclosure   | Generated into ignored mode-0600 local file; never printed, logged, persisted in DB, or sent to Web                            | Enterprise secret manager and audited provisioning        |
| Runner Token disclosure           | Returned once, digest-only DB storage, mode-0600 credential file in dedicated volume, no body/auth logging                     | Rotation, short-lived credentials, workload identity      |
| Offline token guessing            | At least 256 random bits; SHA-256 digest is safe for high-entropy input; constant-time comparison                              | mTLS or workload identity                                 |
| Runner impersonation              | Bearer identity plus body Runner ID equality; stable 401/403                                                                   | Mutual authentication and device attestation              |
| Revoked Runner continues          | Every authenticated request checks revocation; active work receives cancellation                                               | Rotation/revocation propagation SLO                       |
| Duplicate claim                   | PostgreSQL transaction, `FOR UPDATE SKIP LOCKED`, active-attempt unique index                                                  | Queue partitioning only if measured scale needs it        |
| Stale Runner overwrites result    | Runner/Attempt/Lease triple, active pointer, deadline, row lock, `409 stale_lease`                                             | Cryptographic signed leases are not needed locally        |
| Cancellation races success        | Locked transition table; `cancel_requested` rejects completion; cancellation acknowledgement is typed                          | Distributed-clock and multi-region concerns are absent    |
| Envelope expansion/tamper         | Server-derived immutable row, DB trigger, canonical hash, Runner-side revalidation, literal authority fields                   | Signed policy issued by enterprise identity               |
| Arbitrary code execution          | Closed Pydantic Job union and in-process typed executors; no shell/subprocess executor, command string, plugin, or import hook | Future tools need separate isolation and policy           |
| Repository/customer data exposure | Runner has no repository locator, mount, filesystem tool, developer-directory mount, or CreativeDeploy access                  | Phase 4 must introduce an isolated worktree separately    |
| DB/Web lateral access             | Runner joins only internal `runner-control`; it has no DB/Web network or published port                                        | Production network policy and egress proxy                |
| Public egress                     | Docker internal network leaves only the API peer reachable                                                                     | Host-level Docker/network compromise remains out of scope |
| Container privilege escalation    | Non-root, read-only rootfs, all capabilities dropped, no-new-privileges, no Docker/SSH mount, tmpfs `/tmp`                     | A container alone is not a hostile-code sandbox           |
| Result or event exfiltration      | Closed result schemas, key/value classifiers, byte limits, metadata allowlist                                                  | Broader DLP and retention policy                          |
| Payload/event DoS                 | 64 KiB protocol request bound, strict field limits, result bound, heartbeat coalescing                                         | Global rate limits and quotas before public exposure      |
| Reaper double-processing          | PostgreSQL advisory lock and locked deadline recheck                                                                           | Dedicated worker only when operational isolation warrants |
| Retry storm                       | Bounded polling; capped exponential backoff with jitter; finite attempts                                                       | Fleet-wide admission control at scale                     |
| Log leakage                       | Structured identifiers use short hints; no body, token, auth header, environment, hostname, username, or full exception path   | Central redaction and access control                      |

## Security invariants

1. Plan approval never dispatches a Runner Job.
2. The user submits a Job kind and typed parameters, never an Envelope.
3. Runner authority cannot exceed repository none, shell false, and
   Control-Plane-only network.
4. Only one active Attempt can exist for a Job.
5. A stale Lease cannot renew, report progress, fail, cancel, or complete.
6. Cancellation cannot later become success.
7. A heartbeat cannot create unbounded events.
8. Tokens cannot appear in read APIs, job events, logs, screenshots, or
   plaintext database columns.
9. Runner results cannot contain hostname, username, IP, environment, path,
   file, package inventory, or secret-like values.
10. Phase 3 never mounts, scans, reads, or modifies CreativeDeploy.

## Verification

Unit and PostgreSQL integration tests cover invalid/empty credentials,
impersonation, revocation, concurrent claim, attempt/lease mismatch, stale
renew/complete, Envelope tamper/expiry/authority expansion, unsupported
capability, extra metadata, payload/result limits, sensitive results,
cancellation, terminal immutability, lease expiry, retries, and heartbeat
growth.

Real Docker/Playwright checks cover both Job kinds, persistence, cancellation,
desktop/390 px, axe, and overflow. `make runner-chaos-check` forcibly stops
only its isolated Runner, proves offline/expiry/requeue/new Attempt, submits an
old completion and receives `409 stale_lease`, restores the Runner, and waits
for success.

## Residual risk and production upgrades

Local bearer tokens are not the final enterprise identity model. Production
requires mTLS or workload identity, a Secret Manager, rotation, audit
retention, authentication/authorization, tenant isolation, CSRF/rate limits,
TLS, host hardening, resource quotas, incident response, backups, and
production network policy. PostgreSQL polling is suitable for this bounded
local queue; a broker is justified only by measured fan-out, throughput,
delayed scheduling, independent scaling, or operational availability needs.
