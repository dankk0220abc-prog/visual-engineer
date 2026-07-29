# Local Runner Threat Model

## Scope

This threat model covers the Phase 3/4 local, single-user Control Plane, Runner
Protocol v1, PostgreSQL queue, independent outbound Runner, credential volume,
the two repository-free Job kinds, and Phase 4's fixture-only closed Workspace
Jobs. Browser, protocol, database JSON, repository content, local files, and
container state are treated as untrusted at their boundaries.

The model does not claim hostile multi-tenant isolation or production
hardening. Phase 4 adds only one read-only synthetic source, a no-source-Git
snapshot adapter, and a Runner-owned Workspace. No LLM, CreativeDeploy, source
write, shell, target command, Docker socket, public network, Git delivery,
deployment, or external integration exists.

## Assets

- Bootstrap and per-Runner tokens;
- Runner identity and liveness;
- immutable Permission Envelopes and policy hashes;
- Job/Attempt state, lease fencing identity, cancellation, and retry budget;
- Side-effect Permit authority, state, expiry, and revocation ordering;
- Runner-local Workspace ownership HMAC key and authenticated local evidence;
- typed results and RunnerJobEvent evidence;
- Control Plane and source-tree integrity.

## Threats and controls

| Threat                                                    | Current control                                                                                                                                                            | Residual / future requirement                                   |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Bootstrap credential disclosure                           | Generated into ignored mode-0600 local file; never printed, logged, persisted in DB, or sent to Web                                                                        | Enterprise secret manager and audited provisioning              |
| Runner Token disclosure                                   | Returned once, digest-only DB storage, mode-0600 credential file in dedicated volume, no body/auth logging                                                                 | Rotation, short-lived credentials, workload identity            |
| Offline token guessing                                    | At least 256 random bits; SHA-256 digest is safe for high-entropy input; constant-time comparison                                                                          | mTLS or workload identity                                       |
| Runner impersonation                                      | Bearer identity plus body Runner ID equality; stable 401/403                                                                                                               | Mutual authentication and device attestation                    |
| Revoked Runner continues                                  | Every authenticated request checks revocation; active work receives cancellation                                                                                           | Rotation/revocation propagation SLO                             |
| Grant revoked during mutation                             | Requested/effective lifecycle; new Permits blocked immediately; effective waits for consumed Permit terminal/expiry                                                        | Already consumed exact operation has a bounded window           |
| Duplicate claim                                           | PostgreSQL transaction, `FOR UPDATE SKIP LOCKED`, active-attempt unique index                                                                                              | Queue partitioning only if measured scale needs it              |
| Stale Runner overwrites result                            | Runner/Attempt/Lease triple, active pointer, deadline, row lock, `409 stale_lease`                                                                                         | Cryptographic signed leases are not needed locally              |
| Runner forges Validation result identity                  | Control Plane reconstructs a versioned envelope from locked Job/Run/step/Attempt/Lease/Grant/Profile/Checkpoint/policy/Permit records and compares canonical digests       | Local bearer Runner and transport remain trusted                |
| Runner understates Validation output/artifacts            | Control Plane recomputes UTF-8 output bytes, truncation, manifest entries/count/single/total bytes, manifest digest, and evidence digest before any terminal success write | Non-zero artifact content upload remains future authority       |
| Stale Runner mutates filesystem                           | Current single-use Permit binds Runner/Job/Attempt/Lease/Grant/Workspace/digest/deadline and is checked immediately before mutation                                        | Runner/API clock and transport remain trusted locally           |
| Cancellation races success                                | Locked transition table; `cancel_requested` rejects completion; cancellation acknowledgement is typed                                                                      | Distributed-clock and multi-region concerns are absent          |
| Envelope expansion/tamper                                 | Server-derived immutable row, DB trigger, canonical hash, Runner-side revalidation, literal authority fields                                                               | Signed policy issued by enterprise identity                     |
| Arbitrary code execution                                  | Closed Pydantic Job union; no shell/general subprocess, command string, plugin, import hook, or target command                                                             | Future validation needs separate isolation and policy           |
| Repository/customer data exposure                         | Opaque local Handle for exact synthetic read-only bind only; no parent/customer/CreativeDeploy mount; Control Plane sees no path                                           | Real repositories require a new audit and authority             |
| Source-configured helper or extra object enters authority | No Git process targets source; bounded no-follow loose/pack parser computes only the exact authorized closure; exact managed Runner-only Git configuration                 | Narrow ordinary Git layout only; unusual layouts denied         |
| Replacement ref reinterprets an approved object ID        | Empty-template mirror, detached exact `HEAD`, empty raw ref namespace, command/environment replacement disabling, and independent source-tree/Workspace manifest equality  | Existing legacy mirrors fail closed and require manual recovery |
| DB/Web lateral access                                     | Runner joins only internal `runner-control`; it has no DB/Web network or published port                                                                                    | Production network policy and egress proxy                      |
| Public egress                                             | Docker internal network leaves only the API peer reachable                                                                                                                 | Host-level Docker/network compromise remains out of scope       |
| Container privilege escalation                            | Non-root, read-only rootfs, all capabilities dropped, no-new-privileges, no Docker/SSH mount, tmpfs `/tmp`                                                                 | A container alone is not a hostile-code sandbox                 |
| Result or event exfiltration                              | Closed result schemas, key/value classifiers, byte limits, metadata allowlist                                                                                              | Broader DLP and retention policy                                |
| Payload/event DoS                                         | 64 KiB protocol request bound, strict field limits, result bound, heartbeat coalescing                                                                                     | Global rate limits and quotas before public exposure            |
| Runner resource/process escape                            | CPU 1, memory 512 MiB, 128 PIDs, 256 open files, Git streaming-output and complete-group deadlines plus pack/delta/tree/graph/object/mirror bounds                         | Host-wide quotas and fleet admission remain future              |
| Reaper double-processing                                  | PostgreSQL advisory lock and locked deadline recheck                                                                                                                       | Dedicated worker only when operational isolation warrants       |
| Retry storm                                               | Bounded polling; capped exponential backoff with jitter; finite attempts                                                                                                   | Fleet-wide admission control at scale                           |
| Log leakage                                               | Structured identifiers use short hints; no body, token, auth header, environment, hostname, username, or full exception path                                               | Central redaction and access control                            |

## Security invariants

1. Plan approval never dispatches a Runner Job.
2. The user submits a Job kind and typed parameters, never an Envelope.
3. Repository-free Runner authority remains none; Workspace authority cannot
   exceed its exact isolated Grant. Shell remains false and transport remains
   Control-Plane-only.
4. Only one active Attempt can exist for a Job.
5. A stale Lease cannot renew, report progress, fail, cancel, or complete.
6. Cancellation cannot later become success.
7. A heartbeat cannot create unbounded events.
8. Tokens cannot appear in read APIs, job events, logs, screenshots, or
   plaintext database columns.
9. Runner results cannot contain hostname, username, IP, environment, path,
   file, package inventory, or secret-like values.
10. Phase 3/4 never mounts, scans, reads, or modifies CreativeDeploy.
11. Workspace Jobs revalidate Grant status/expiry, Runner, Workspace, Handle,
    revision, and policy hash at claim and every Lease mutation.
12. Every mutating Workspace Job also validates a current exact Side-effect
    Permit immediately before mutation. Effective revocation has zero accepted
    later side effects.
13. Only `git_ops.py` invokes subprocess, only fixed Git against Runner-owned
    state; no Git process targets source. Source and sibling Workspace
    integrity are mandatory.
14. Unprovable Workspace ownership or discard completion never authorizes
    deletion or idempotent success.
15. A Git subprocess is complete only when leader, pipes, and process-group
    evidence are terminal; timeout cleanup failure is itself a typed failure.
16. Approved revision identity is insufficient by itself: the no-follow
    Workspace manifest must exactly equal the source-less authorized
    path/type/mode/size/content-digest manifest before registration.
17. A Validation completion is untrusted until its full persisted execution
    envelope, Permit fence, output arithmetic, artifact manifest, and evidence
    digest are independently reconstructed and matched by the Control Plane.
18. Rejected Validation completion cannot store a succeeded Result, complete
    a Permit, emit a success event, create terminal Evidence, or charge replay
    state.
19. Typed cleanup failure after `cancel_requested` atomically becomes
    `recovery_required`; it cannot be acknowledged as `cancelled`.

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

Phase 4 adds Permit/digest/revocation, descriptor/path/atomicity,
ownership/quarantine, exact loose/packed source closure, and complete
process-group adversarial tests plus a real fixture browser flow. Round 2 adds
real PostgreSQL concurrent Permit acquisition and injected terminal-transaction
rollback with committed-disk idempotent retry. `make workspace-chaos-check` covers
pre-commit and post-rename interruption, stale Lease/Attempt/Permit denial,
budget replay, concurrent revocation, recovery, rollback, and disposal. The
strict source harness compares the full no-follow source plus `.git` manifest.
See
[`workspace-threat-model.md`](workspace-threat-model.md) for filesystem
residuals.

Phase 5 adds unchanged focused result-binding tests plus real-PostgreSQL
permanent regressions for inner identity/profile/revision/checkpoint/policy,
argv/cwd/environment/schema/Permit fencing, exact and over-limit output,
artifact/evidence mismatch, side-effect-free rejection, idempotent success,
and cancellation-to-recovery persistence.

## Residual risk and production upgrades

Local bearer tokens are not the final enterprise identity model. Production
requires mTLS or workload identity, a Secret Manager, rotation, audit
retention, authentication/authorization, tenant isolation, CSRF/rate limits,
TLS, host hardening, resource quotas, incident response, backups, and
production network policy. PostgreSQL polling is suitable for this bounded
local queue; a broker is justified only by measured fan-out, throughput,
delayed scheduling, independent scaling, or operational availability needs.

The original audit, independent re-audit, and focused re-audit remain Security
Gate FAIL. These Round 3 controls are a single-finding repair candidate for a
new independent focused re-audit, not a security certification.
