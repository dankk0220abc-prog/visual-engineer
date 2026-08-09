# Zhipu live Trace/Audit contract implementation

Status: IMPLEMENTATION COMPLETE — INDEPENDENT REVIEW REQUIRED, LIVE CALL BLOCKED

## Goal

Replace the fixture-only `AIProviderTrace` persistence contract with one durable
`AIProviderInvocation` per Provider dispatch attempt. Establish the database,
lifecycle, adapter, API, and minimal bilingual UI boundaries needed before any
separately authorized live Provider call.

## Safety boundary

- Do not read, accept, print, persist, or transmit a real Provider credential.
- Do not enable Zhipu, Qwen, DeepSeek, Doubao, or Kimi.
- Do not send a live Provider request. Adapter integration uses only
  `httpx.MockTransport` and a synthetic credential.
- Keep Plan approval authority-free: no Execution Grant, Review Approval,
  Delivery Authorization, Runner operation, Git side effect, deployment, or
  Workspace mutation may result from Provider failure, cancellation, or an
  ambiguous outcome.
- Do not move `main`, merge, mark a PR ready, tag, release, or deploy.

## Baseline

- Repository: `/Users/danke/Developer/VisualEngineer`
- Base branch/HEAD: `main` at
  `deb5f166cca6904b1d9b0b6b6cd23aca51452241`
- Base tree: `d64cf3468f54e6115ea3219ba455a05635cee1ef`
- Working branch: `codex/feat/zhipu-live-trace-audit-contract`
- Local main, origin/main, `git ls-remote`, and live GitHub main matched.
- Ahead/behind was `0/0`; worktree, index, untracked set, stash, and Git
  operation state were clean.
- Alembic had one head, `20260801_0015`.
- Deterministic Fixture was the only enabled Provider. All five real Providers
  were disabled with live validation `not_performed`.
- Canonical Fast `31272546489` and Heavy `31272546490` were attempt 1 successes
  on the exact base SHA.

## Implementation plan

1. Add revision `20260809_0016` to rename/backfill `ai_provider_traces` as
   `ai_provider_invocations`, install closed checks/indexes and guarded lifecycle
   transitions, and make lossy downgrade paths fail closed.
2. Replace the ORM/repository/schema contract with typed invocation identity,
   lifecycle, model/upstream identity status, nullable usage, integer monotonic
   latency, billing, bounded errors, digests, and safe upstream fingerprinting.
3. Persist prepared, dispatching, and terminal states in separate transactions;
   add stale-dispatch reconciliation with no retry; connect real adapters only
   through injected MockTransport tests.
4. Regenerate OpenAPI/TypeScript contracts and minimally update the existing AI
   Plan audit panel and both locales without redesigning the Provider page.
5. Close `VE-MPF-R2-OBS-001` by making the secret scanner fail closed when `rg`
   is unavailable.
6. Run focused migration/model/lifecycle/adapter/API/Web/scanner tests, one real
   PostgreSQL upgrade/downgrade/upgrade round trip, relevant canonical API
   aggregate, quality/contract checks, and `git diff --check`.
7. Record evidence as `mock_contract_not_live`, create at most three logical
   commits, push normally, open a draft PR, and wait for CI. Stop before the
   independent review gate.

## Decisions

- `AIProviderInvocation.id` remains VisualEngineer internal identity; upstream
  request identity is separate and never returned in full by the ordinary API.
- Durable elapsed values are integer milliseconds measured from a monotonic
  client clock. Adapter-reported timing cannot overwrite them.
- Timeout, connection loss, or cancellation after the dispatch-intent commit is
  `outcome_unknown`; it is never retried automatically.
- Raw outbound bodies, raw malformed/error bodies, authorization material,
  Prompt text copies, and stack traces are outside the invocation table.

## Progress log

- Preflight completed and matched the authorized baseline.
- Existing model, migration, service, adapter, API, UI, generated contract, and
  Provider registry boundaries inspected. Migration is required.
- Revision `20260809_0016` renames/backfills the old Trace table and installs
  the closed Invocation contract, indexes, immutable identity/lifecycle guards,
  terminal immutability, and lossy-downgrade refusal.
- The governed Fixture path and injected-MockTransport adapter contract use
  durable prepared/dispatching/terminal commits, no automatic retry, explicit
  ambiguous outcome, stale dispatch reconciliation, and terminal-first Plan
  continuation.
- OpenAPI/TypeScript and the existing bilingual AI Plan audit panel now expose
  only the safe typed projection; the full upstream request ID remains excluded.
- `VE-MPF-R2-OBS-001` is closed: missing `rg` fails non-zero without a clean
  message, the regression is in `security-check`, and Heavy explicitly installs
  the required dependency.
- Core commits `748e277` and `9cff728` were pushed normally. Draft PR #17 was
  opened and left draft.

## Validation record

- VERIFIED: focused migration/Invocation/adapter/governance tests (`107 passed`)
  and post-review hardening subset (`67 passed`), including real PostgreSQL
  triggers and fail-closed downgrade paths.
- VERIFIED: canonical backend aggregate (`445 passed`, `84.94%` coverage), Web
  unit/component (`107 passed`), Ruff, mypy (139 source files), Prettier, ESLint,
  TypeScript, generated-contract drift, secret scan, and missing-`rg` regression.
- VERIFIED: clean real PostgreSQL `base -> head -> base -> head` migration
  roundtrip, historical Fixture backfill, and live/mock/outcome downgrade refusal.
- NOT VERIFIED locally: focused 390 px Playwright could not start services
  because Debian returned HTTP 502 while the Runner image fetched `libldap`;
  isolated cleanup passed and the run was not repeated.
- REMOTE CI CODE CANDIDATE: Fast `31289647121` attempt 1 passed. Heavy
  `31289647064` attempt 1 preserved two first failures: missing `rg` in the
  security job and a strict-locator collision in Phase 7 Playwright. Both have
  narrow remediation in the final evidence/CI commit; its check results belong
  to draft PR #17 and the final handoff.

## Rollback

Before publication, reverse only this branch's scoped files. After publication,
revert its commits. Never reset, clean, force-push, rewrite shared migration
history, alter `main`, or delete Provider audit rows.
