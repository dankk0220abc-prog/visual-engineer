# Project Status

- Phase: Phase 3 — Browser-Orchestrated Local Runner Foundation
- Overall status: COMPLETE LOCALLY; REMOTE CI NOT RUN
- Last updated: 2026-07-26
- Branch: `feat/phase-3-browser-orchestrated-local-runner`
- Foundation base: `d136418158d9f5ffc4f2f8ba993ca48e837ed59b`
- Phase 2 closure on main: `336b46d`

## Product position

VisualEngineer is a governed AI design-engineering and delivery system for
enterprise frontend teams, limited to Design Implementation, Design-System
Migration, and Frontend Quality Remediation packages.

Phase 2 provides durable Level 0 repository investigation and deterministic
plan approval. Phase 3 separately provides a browser-orchestrated,
repository-free Local Runner for typed System Diagnostic and Controlled Wait.
It has no LLM, code writer, target command executor, worktree, Git/PR, or
deployment capability. Approval never dispatches a Runner Job.

CreativeDeploy is internal Customer 0 and Design Partner 0. It is not an
external enterprise customer and provides no production, adoption,
time-saving, or outcome data.

## Implemented

- PostgreSQL Run, RepositorySnapshot, Plan, ApprovalDecision, and AuditEvent
  entities with Alembic upgrade/downgrade.
- Closed Run/Plan state policy, immutable Snapshot trigger, optimistic version,
  idempotency, stale-version conflicts, rejection reason, and serialized final
  decision.
- Canonical allowlisted exact-Git-root validation and a fixed no-shell
  committed-object scanner.
- Dirty/untracked metadata-only handling; sensitive, secret-like, binary,
  dependency, symlink, submodule, LFS, file/count/byte, and timeout controls.
- Stable normalized Snapshot fingerprint and untrusted instruction provenance.
- Deterministic fingerprint-bound Plan creation, bounded revision, Foundation
  policy validation, typed display-only validation steps, and
  `execution_available = false`.
- Versioned `/api/v1` Run/Snapshot/Plan/decision/audit/cancel endpoints,
  request IDs, stable errors, structured governance logs, and generated
  TypeScript contract.
- Task Run history and Run console with repository intelligence, dirty/safety
  signals, deterministic Plan review/revision/submission/decision, conflict
  handling, explicit non-execution warnings, and Audit Timeline.
- API-only read-only synthetic and Customer 0 Compose overrides, non-root API
  image with Git, fixture generator, deterministic eval dataset, Make gates,
  and CI definitions.
- Pure Runner Protocol v1 with strict schemas, canonical Envelope hashing,
  typed results, error codes, and 64 KiB request bounds.
- Runner, immutable PermissionEnvelope, RunnerJob, RunnerJobAttempt, and
  RunnerJobEvent PostgreSQL entities and reversible Alembic migration.
- Dynamic high-entropy bootstrap, per-Runner digest-only token, constant-time
  authentication, credential volume, heartbeat-derived liveness, and
  revocation.
- Server-derived fixed-authority Envelopes, transactional `SKIP LOCKED` claim,
  one-active-attempt constraint, leases, fencing, cancellation, retry budget,
  advisory-locked reaper, offline and recovery.
- Independent outbound non-root Runner with in-process repository-free typed
  executors, renewal/progress/cancellation, bounded backoff, and graceful
  shutdown.
- Browser Registry, immutable Dispatch preview, Job/Attempt/lease evidence,
  progress, cancellation distinction, typed result, and Timeline.
- Internal Runner/API-only Docker network, no Runner port, database/Web
  network, repository/CreativeDeploy/developer/SSH/Docker-socket mount, shell,
  or public-network path.

## Current local evidence

- Backend/Runner/protocol: 76 tests on real PostgreSQL, 83.92% total API source
  coverage in the focused Phase 3 run.
- Frontend: 32 tests; 82.89% statements, 74.60% branches, 85.00% functions,
  and 84.36% lines.
- Scanner security: 7 focused cases, including stable fingerprint, total
  budget, timeout, and oversized symlink metadata.
- Eval records: 43 deterministic cases across three datasets, including
  Runner test mappings and no model scores.
- Playwright: ten real-stack flows across desktop and 390px. Phase 3 uses a
  real Runner for diagnostic success and controlled-wait cancellation, with
  persistence, axe WCAG 2 A/AA, and horizontal-overflow assertions.
- Approval concurrency: independent PostgreSQL approve/reject transactions
  produce one winner, one stable conflict, and one decision row.
- Migration: empty PostgreSQL upgrade/downgrade/upgrade coverage is present.
- Chaos: actual abrupt Runner loss produced offline, `lease_expired`, requeue,
  stale completion `409`, a second Attempt, recovery, success, and unchanged
  source status.
- Runtime isolation: Runner UID/GID 10001, read-only root filesystem,
  capability drop, no-new-privileges, no port, one 0600 credential volume, API
  readiness 200, and denied database/Web DNS and public HTTPS. Combined service
  logs contained no bootstrap token.
- Remote GitHub Actions have not run and are not represented as verified.

Exact final command results belong in
[`../evidence/phase-3-verification.md`](../evidence/phase-3-verification.md).

## Customer 0 state

- Task: `d71b708b-597e-448d-a41c-90df41c602f0`.
- Run: `447510d7-695c-46ec-baad-9a0f750ce965`.
- Snapshot fingerprint:
  `41c0ff6896e97d22b876e7bfe9d31f6f260998a74a2b0ddbcdb3620be1a53797`.
- Plan: v1, `deterministic_policy`, `rejected`.
- Run: `rejected`.
- Local page:
  `http://127.0.0.1:13001/runs/447510d7-695c-46ec-baad-9a0f750ce965`.

CreativeDeploy branch, `HEAD`, full status hash, and diff-stat hash were
identical before/after. The API ran non-root with the exact target mount
read-only; Web and database had no target mount.

The user subsequently rejected Plan v1 in the browser because CreativeDeploy
`HEAD` had advanced beyond the persisted Snapshot revision. Read-only API and
database checks verified one `local_user` rejection, the required non-empty
reason, matching rejected Run/Plan states, and a final `plan_rejected` Audit
Event. No execution, tool, write, Git, or pull-request event exists. The
rejection did not execute the Plan, and the closure neither rescanned nor
modified CreativeDeploy. See
[`../evidence/phase-2-human-rejection.md`](../evidence/phase-2-human-rejection.md).

## Known limitations

- No LLM or OpenAI Agents SDK.
- No Agent Trace, model planning, or autonomous coding Agent.
- Runner has no code-writing, generic shell, repository read/write, repository
  command, or target validation execution.
- No isolated worktree, checkpoint, repair loop, or rollback executor.
- No branch/commit/push/PR/merge or remote CI result.
- No authentication, authorization, tenancy, rate limiting, or public-safe
  exposure.
- No production migration release process, secrets service, backup/restore,
  hardened hostile-code sandbox, or production deployment.
- Local long-lived bearer tokens and Docker internal networking are not final
  enterprise workload identity, Secret Manager, rotation, or egress policy.
- PostgreSQL polling is intentionally bounded local scheduling, not a
  high-throughput or multi-region queue.
- Plan string policy is Foundation validation, not independent runtime
  enforcement.
- Approval does not grant future execution authority.
- No external enterprise customer, production usage, adoption, time saving, or
  measured outcome.

## Technical debt

- Track the upstream FastAPI/Starlette TestClient migration from `httpx` to
  `httpx2`; the suite has one non-failing deprecation warning.
- Pin GitHub Actions to immutable commit SHAs before a public/high-assurance
  release.
- Add authentication and deployment hardening before any network exposure.
- Define retention and classification only when future tool/artifact/trace
  entities have real behavior.

## Recommended next milestone

Phase 4 should design isolated-worktree readiness as a separate permission
elevation: exact repository authorization, worktree lifecycle, descriptor-safe
typed file reads/writes, independent runtime policy, checkpoints, resource and
network controls, and evidence. It must preserve Plan-versus-execution
separation and must not add shell, Git delivery, or broader repository access
without their own reviewed milestones.
