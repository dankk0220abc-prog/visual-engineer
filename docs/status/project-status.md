# Project Status

- Phase: Phase 2 — Governed Read-Only Repository Intelligence
- Overall status: VERIFIED AND HUMAN-REJECTED FOR PHASE 2 LOCAL CHECKPOINT
- Last updated: 2026-07-26
- Branch: `feat/phase-2-readonly-repository-intelligence`
- Foundation base: `d136418158d9f5ffc4f2f8ba993ca48e837ed59b`

## Product position

VisualEngineer is a governed AI design-engineering and delivery system for
enterprise frontend teams, limited to Design Implementation, Design-System
Migration, and Frontend Quality Remediation packages.

Phase 2 provides durable Level 0 repository investigation and deterministic
plan approval. It has no LLM, Agent Runtime, code writer, target command
executor, worktree, PR, or deployment capability. Approval never executes
code.

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

## Current local evidence

- Backend: 55 tests on real PostgreSQL, 84.91% total coverage.
- Frontend: 21 tests; 87.38% statements, 73.87% branches, 90.65% functions,
  and 88.29% lines.
- Scanner security: 7 focused cases, including stable fingerprint, total
  budget, timeout, and oversized symlink metadata.
- Eval records: 29 deterministic cases across two datasets.
- Playwright: six real-stack flows, desktop and 390px, approve and reject,
  persistence, axe WCAG 2 A/AA, and horizontal-overflow assertions.
- Approval concurrency: independent PostgreSQL approve/reject transactions
  produce one winner, one stable conflict, and one decision row.
- Migration: empty PostgreSQL upgrade/downgrade/upgrade coverage is present.
- Remote GitHub Actions have not run and are not represented as verified.

Exact final command results belong in
[`../evidence/phase-2-verification.md`](../evidence/phase-2-verification.md).

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
- No Agent Runtime or complete Agent Trace.
- No code-writing, generic shell, repository command, or validation execution.
- No isolated worktree, checkpoint, repair loop, or rollback executor.
- No branch/commit/push/PR/merge or remote CI result.
- No authentication, authorization, tenancy, rate limiting, or public-safe
  exposure.
- No production migration release process, secrets service, backup/restore,
  hardened hostile-code sandbox, or production deployment.
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

Establish the separately approved Phase 3 browser-orchestrated Local Runner
foundation with no repository, shell, worktree, Git, or public-network access.
Its first jobs must remain typed diagnostics and controlled waits governed by
immutable permission envelopes, leases, fencing, cancellation, and browser
visibility.
