# Phase 7 First Vertical Slice — Governed AI Planning

## Goal

Add one complete fixture-only path from bounded Repository Intelligence to a
strictly typed plan produced by a deterministic Provider, independently
evaluated, reviewed by a local human, and handed to the existing governed Plan
chain without issuing any execution, review, delivery, remote, or deployment
authority.

## Scope

- A model-neutral Provider protocol, capability metadata, deterministic fixture
  implementation, cancellation token, timeout, bounded retry, stable error
  taxonomy, and exact replay.
- A typed AI Plan contract covering requirement summary, repository findings,
  assumptions, expected files/components, proposed typed operations,
  validation suites, risks, acceptance criteria, unresolved questions,
  context references, Prompt/Provider metadata, authority boundary, and digest.
- Durable AI Plan request state, redacted Prompt/request/response, bounded
  context manifest, attempt Trace, synthetic usage/cost metadata, independent
  deterministic Eval evidence, human decision, and approved handoff Plan.
- Freshness revalidation against the exact committed repository revision and
  Snapshot fingerprint; stale Plans cannot be approved.
- Browser-first generation, structured review, context/Prompt/Trace/Eval,
  approve/reject, refresh, cancellation, and terminal-state presentation on
  desktop and narrow screens.
- Reversible PostgreSQL migration, generated API contract, focused unit,
  PostgreSQL, security, Eval, Web, and real-browser verification.

## Non-goals and stop boundary

- Real Provider SDKs, model/network calls, API keys, credentials, or provider-
  specific runtime names.
- CreativeDeploy, Customer 0, real customer repositories, non-fixture Runner
  expansion, arbitrary shell, dependency execution, or wider permissions.
- Automatic Execution Grant, Review Approval, Delivery Authorization, Git
  delivery, remote, push, PR, merge, tag, or production deployment.
- Authentication, multi-tenancy, queues, background model workers, or an
  irreversible migration.

## Verified baseline

- Repository: `/Users/danke/Developer/VisualEngineer`.
- Branch/HEAD/main before branching: `main` and
  `9c282e91a42a87ea553171d5aa55a0f77564bb14`.
- Worktree, index, and untracked set: clean; remote and stash: empty.
- Sole Alembic head: `20260801_0014`.
- Feature branch: `codex/phase-7-governed-ai-planning-first-slice`.
- The checked-in Project Status still described the pre-fast-forward Phase 6
  state even though real `main` contains the sealed Second Slice; this batch
  will correct that documentation drift without reopening Phase 0-6.

## Design decisions

1. `AIPlanRequest` is the Provider lifecycle and audit aggregate. It is bound
   to one Run, immutable Snapshot fingerprint, source revision, Prompt digest,
   context digest, Provider capabilities, and request hash.
2. The Provider returns only `AIPlanContract`. It has no approval, grant,
   review, delivery, filesystem, Git, shell, network, or credential field.
3. Prompt construction includes a redacted requirement plus structured facts
   and selected manifest metadata only. It never contains selected blob text,
   dirty/untracked contents, denied paths, secret findings, or paths beyond the
   fixed context count/byte budget.
4. A separate deterministic policy evaluator produces trusted evidence. The
   Provider cannot submit Eval results or declare itself safe.
5. Approval row-locks the request, re-scans the allowlisted committed HEAD,
   requires every mandatory Eval to pass, and creates one existing `Plan` with
   `source = governed_ai`, status `approved`, and `execution_available = false`.
   Rejection creates no downstream Plan. Both are one-winner durable decisions.
6. The approved handoff makes the Plan eligible for the existing later
   governance request path only. No Grant, Workspace, Validation, Review, or
   Delivery object is created by AI Plan approval.
7. Synthetic usage and zero cost are labeled `synthetic_not_billable`; they
   are fixture observability, not a real Provider invoice or benchmark.

## Progress

- 2026-08-01 CST — **done**: governed preflight and current architecture,
  product, security, deterministic planning, approval, status, and Eval seams
  inspected; exact baseline verified and feature branch created.
- 2026-08-01 CST — **done**: reversible migration, model-neutral Provider
  protocol, deterministic fake, strict Plan contract, Prompt registry,
  redaction/context budget, Trace, system-owned Eval, freshness, audit, and
  one-winner authority-free Plan handoff implemented.
- 2026-08-01 CST — **done**: API/generated contracts and responsive Web review
  flow cover generation, structured Plan/context/Prompt/Trace/Eval inspection,
  refresh, cancel, approve/reject, and terminal-state presentation.
- 2026-08-01 CST — **done**: focused PostgreSQL/Eval `13/13`, Web `60/60`, and
  rebuilt real-browser desktop/narrow approve/reject `4/4` pass. The first
  locator failure and real scroll-region keyboard failure are preserved in
  evidence.
- 2026-08-01 CST — **done**: contract, format, lint, typecheck, build,
  reversible Migration, security, Eval, source invariance, full Browser
  `20/20`, Workspace chaos, and exact Docker cleanup pass. The sole complete
  `make verify` exit `2` at the pre-remediation `69.89%` Web function coverage
  is preserved; focused coverage now passes at `71.42%` and the aggregate was
  not rerun. Diff review and the local checkpoint complete this batch; the
  checkpoint hash is reported in the handoff.

## Risks

- A synchronous fake returns quickly, so `generating` is mainly visible in the
  durable timeline; cancellation remains a real Provider protocol boundary and
  terminal request action, not a claim of a production worker architecture.
- Repository Snapshot metadata is rich but does not persist selected source
  text. The first slice intentionally plans from structured facts and manifest
  references rather than adding a new source-content persistence boundary.
- Existing approved Plan consumers must continue to work with both
  `deterministic_policy` and `governed_ai` sources; the migration and regression
  tests must preserve old rows and flows.

## Verification and evidence

Run focused tests first. Record exact commands, counts, exit codes, failures,
source invariance, Docker ownership/cleanup, and final Git state in
`docs/evidence/phase-7-governed-ai-planning-first-slice-verification.md`.
Run one complete `make verify` only after the candidate and focused gates have
no known blocker.

## Rollback

Revert only this branch's reviewed checkpoint. Migration `20260801_0015` is
additive and downgrade removes only AI-planning entities and restores the
original Plan source constraint. Do not reset, clean, edit environment files,
touch a real repository, or remove unrelated Docker resources.

## Completion conditions

- Valid deterministic generation persists a strict contract, Prompt/request/
  response, bounded context, Trace, metadata, and all mandatory Eval evidence.
- Invalid schema/reference/fact/operation/leakage/budget/acceptance/freshness/
  replay/injection/approval-boundary cases fail closed with stable evidence.
- Replay is exact and idempotent; approve/reject races yield one decision;
  stale, failed, or cancelled requests cannot enter the handoff.
- Approval creates no execution or delivery authority and the fixture source
  HEAD/status/content remain invariant.
- API/Web/migration/contracts/quality/build/focused browser gates pass; if the
  aggregate runs, its exact outcome is preserved; one clean local checkpoint
  is created without push, PR, tag, deploy, or merge to main.
