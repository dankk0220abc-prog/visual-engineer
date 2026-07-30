# Phase 5 Third Vertical Slice — Governed Final Review & Release Readiness

## Goal

Implement a browser-first, deterministic final-review workflow that creates an
immutable Evidence-backed Review Package for one successful trusted Validation
Suite result, accepts one immutable local-user Review Decision, and returns a
Release Readiness Verdict only while every exact baseline and evidence binding
is fresh. Approval must never imply Git or deployment authority.

## Scope

- Add PostgreSQL models and an additive Alembic migration for Review Package,
  stale invalidation, Review Decision, and Release Readiness Verdict state.
- Add exact Evidence Manifest construction and digest verification over the
  trusted Suite/Run/Job/Attempt/Lease/Grant/Permit/Evidence chain.
- Add idempotent and concurrency-safe API endpoints and generated OpenAPI /
  TypeScript contracts.
- Add a responsive, accessible `/reviews` browser workflow.
- Add PostgreSQL, API, Web, Playwright E2E, security, evaluation, Docker, and
  aggregate verification evidence.
- Reconcile the four governance status documents in the same final checkpoint.

## Non-goals

- LLMs, OpenAI Agents SDK, external Providers, credentials, or model calls.
- CreativeDeploy, Customer 0, any real repository, or source/canonical
  Workspace mutation.
- Shell, user command, argv, environment, cwd, package installation, or new
  Runner executor authority.
- Git commit/push/PR/merge/tag delivery authorization, production deployment,
  remote CI, or Phase 6.

## Constraints and safety

- Baseline is exact local `main`
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`; the implementation branch is
  `feat/phase-5-governed-final-review`.
- Review creation and approval lock and revalidate the current exact
  Run/Plan/source revision/Workspace/Checkpoint/Suite Result/Evidence chain.
- Missing, foreign, reordered, duplicate, modified, non-success, or stale
  evidence fails closed without a Review Decision or ready verdict.
- Package, invalidation, decision, and verdict authority fields are immutable
  in PostgreSQL. Exactly one final decision and one verdict may win.
- Critical/High findings, data corruption, source/canonical Workspace change,
  or inability to prove freshness/Evidence/readiness boundaries stops work.
- No remote, push, pull request, merge, tag, deployment, Customer 0, or Phase 6
  action is authorized.

## Current progress

- 2026-07-30 CST — **done**: exact repository, branch, HEAD/main, tracked,
  index, and untracked baseline verified clean.
- 2026-07-30 CST — **done**: new implementation branch created without
  overwriting an existing ref.
- 2026-07-30 CST — **done**: governance status reconciled while preserving all
  historical FAIL/remediation/sealing records.
- 2026-07-30 CST — **done**: data model, migration, service, API,
  generated contract, and browser workflow.
- 2026-07-30 CST — **done**: focused PostgreSQL/Web/security tests.
- 2026-07-30 CST — **done**: real-stack Playwright, Docker, Eval, and aggregate
  `make verify`.
- 2026-07-30 CST — **done**: evidence closeout and scope review.
- 2026-07-30 CST — **pending**: exact-tree final gate and one local checkpoint;
  these necessarily occur after this tracked plan is frozen.

## Decisions

- A Review Package is immutable and stores a canonical Evidence Manifest plus
  its SHA-256 digest; it does not copy raw stdout/stderr or artifact content.
- Freshness is derived from exact current baseline facts and permanently
  fenced by a first immutable invalidation record when a mismatch is observed.
- A Review Decision records governance intent only. The service and schema
  expose `git_authorization = false` and `deployment_authorization = false`.
- A Release Readiness Verdict is a deterministic snapshot. `ready` requires a
  fresh package, an `approve` decision whose package digest matches, a complete
  trusted manifest, and the closed no-delivery boundary. Rejected or stale
  packages return `not_ready`.
- Review APIs accept identifiers and decisions only; no execution or command
  fields are accepted.

## Risks

- **Stale approval race** — high impact; lock the package and baseline rows,
  recheck after lock, use immutable invalidation and one-winner constraints.
- **Evidence substitution** — high impact; reconstruct catalog order and exact
  execution identities, recompute the Suite aggregate and manifest digests.
- **Decision/readiness conflation** — medium impact; persist explicit false
  delivery-authority fields and assert them in API, database, and browser tests.
- **Migration trigger gaps** — high impact; direct-SQL mutation tests and
  base/head/base/head migration verification.

## Discoveries

- The Second Slice already reconstructs successful Suite proof from locked
  child execution rows and recomputed Evidence digests; the Third Slice will
  reuse that trusted path rather than accept stored summaries as authority.
- The repository has no pre-existing Third Slice implementation or conflicting
  approved later milestone.
- Local `main` points to the Second Slice sealing checkpoint and the worktree
  was clean before branch creation.
- Null-safe database self-review found that SQL `CHECK` and `<>` semantics
  needed explicit non-null rejection reasons and `IS DISTINCT FROM` freshness
  comparisons. The migration and direct-SQL tests now cover both boundaries.
- One full E2E attempt reached `cancelled` through `lease_expired` before the
  existing Phase 3 Runner could acknowledge cancellation. Its unchanged full
  rerun passed desktop and narrow `16/16`.

## Verification

- `make review-security-check`: **PASS**, 7 focused real-PostgreSQL cases.
- `make test`: **PASS**, Python 259/259 at 83.41% coverage and Web 50/50
  above every unchanged threshold.
- `make contracts-check`: **PASS**, generated OpenAPI/TypeScript no drift.
- `make migration-check`: **PASS**, base → head → base → head through
  `20260730_0010`.
- `make e2e`: **PASS**, desktop/narrow 16/16 with `/reviews`, axe, containment,
  source, and canonical Workspace invariance.
- `make security-check`: **PASS**, scanner 7/7, Runner/API/Protocol 111/111,
  Review 7/7, secrets/static boundaries.
- `make eval`: **PASS**, 74 deterministic cases across six datasets plus
  scanner 7/7.
- `E2E_SKIP_BUILD=1 CHAOS_SKIP_BUILD=1 make verify`: **PASS**, exit 0 using
  local exact-source images built and exercised earlier in the same run.

## Rollback

Stop only task-owned Compose projects through their existing cleanup paths.
Before the checkpoint, revert only this slice's additive files and edits; do
not reset, clean, or modify unrelated state. The new migration downgrades by
dropping Third Slice triggers/tables only. No source repository or canonical
Workspace cleanup is part of this slice.

## Completion conditions

- Immutable Review Package/Evidence Manifest, invalidation, Review Decision,
  and deterministic readiness behavior are implemented and covered.
- Concurrent/idempotent decisions have exactly one durable winner.
- A stale approval cannot produce or remain effectively `ready`.
- Approval and readiness expose no Git or deployment authority.
- Contracts, migration, PostgreSQL, Web, E2E, Security, Eval, Docker, and final
  `make verify` all exit 0.
- Local `main` remains the exact starting hash, CreativeDeploy is untouched,
  and no remote/delivery action occurs.
- One local checkpoint has the exact required subject and the final worktree is
  clean.

## Outcome and follow-ups

**COMPLETE — READY FOR INDEPENDENT FOCUSED REVIEW.** The only permitted report
is `PHASE 5 THIRD VERTICAL SLICE COMPLETE — READY FOR INDEPENDENT FOCUSED
REVIEW`. Independent focused review, sealing, local main integration, Git
delivery, and Phase 6 remain separate authorizations. The local checkpoint hash
is reported in the handoff because a commit cannot contain its own hash.
