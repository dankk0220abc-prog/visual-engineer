# Model-neutral multi-Provider foundation

Status: IMPLEMENTATION COMPLETE — DRAFT PR/CI PENDING

## Goal

Add a closed, model-neutral planning Provider registry for Deterministic Fixture,
Zhipu GLM, Qwen, DeepSeek, Doubao, and Kimi. Keep the Fixture as the only enabled
runtime Provider in this slice, expose secret-safe configuration status, add
explicit real-Provider adapters verified only with mock HTTP, and surface the
status in the bilingual Web Console.

## Safety boundary

- No real Provider request is permitted in this work package.
- No API key is accepted by the browser, API payloads, database, logs, Trace,
  Evidence, screenshots, fixtures, or Git.
- Provider endpoints and model identifiers are code-owned allowlist values.
- A configured real Provider remains disabled until a later, separately
  authorized live-validation package.
- Provider generation can create only a typed governed Plan proposal. Approval
  still creates no Execution Grant, Review Approval, Delivery Authorization,
  Side-effect Permit, Runner operation, Git authority, or deployment authority.
- No fallback may disguise a real-Provider failure as Fixture success.

## Baseline

- Repository: `/Users/danke/Developer/VisualEngineer`
- Base branch/HEAD: `main` at
  `aaa9dc6df6082bffe5f7a7038dc0166524db058a`
- Base tree: `41c0b78885a2db59761fd0eaeb79bff9250af8b1`
- Working branch: `codex/feat/model-neutral-multi-provider-foundation`
- Preflight: local main, origin/main, and GitHub main matched; worktree/index/
  untracked and stash were clean; no active Git operation; PR #14/#15 were
  merged with their head branches deleted; required backup refs remained; Fast
  run `30937365381` and Heavy run `30937365798` were attempt 1 successes.

## Schema decision

No migration is required. `AIPlanRequest.provider_id` already stores the stable
Provider ID, while immutable `provider_metadata` stores the model identifier and
invocation capability metadata. Real Providers are not invoked or persisted in
this slice, so the existing fixture-only Trace cost constraint remains intact.
The later live-validation package must reassess persistence of upstream request
IDs and real usage/cost semantics before enabling durable real-provider calls.

## Implementation plan

1. Add closed Provider IDs, public configuration/capability status, centralized
   secret presence checks, and safe disable reasons.
2. Add explicit Zhipu, Qwen, DeepSeek, Doubao, and Kimi adapters over an internal
   allowlisted HTTP helper with typed request/response/error normalization,
   cancellation, bounded timeouts, zero automatic retries, and redacted errors.
3. Extend AI Plan creation with a closed Provider selection. Reject unknown,
   unconfigured, or disabled real Providers before persistence or HTTP.
4. Export the safe discovery contract, regenerate OpenAPI/TypeScript, and add a
   bilingual Provider status page and run-scoped selector.
5. Add registry, adapter mock-contract, redaction, state-machine, API, component,
   i18n, accessibility, responsive Playwright, screenshot-manifest, and Evidence
   safety tests.
6. Run focused gates, one necessary canonical aggregate, inspect the full diff,
   create scoped commits, push, and open a draft PR. Do not merge, tag, release,
   deploy, or mark ready.

## External API documentation used for adapter constants

- Zhipu: official BigModel Chat Completions documentation.
- Qwen: official Alibaba Cloud Model Studio OpenAI-compatible Chat documentation.
- DeepSeek: official Chat Completions API documentation.
- Doubao: official Volcengine Ark model invocation documentation.
- Kimi: official Kimi Open Platform Chat Completions documentation.

These sources establish request shapes only. Mock contract tests are not live
validation and do not establish model availability, quality, price, or account
compatibility.

## Progress log

- Preflight completed and matched the requested baseline.
- Existing AI Planning persistence and authority boundaries inspected.
- No-migration path selected and the existing `provider_id`/JSON metadata
  boundary retained.
- Closed six-Provider registry, five explicit allowlisted adapters, safe
  configuration discovery, and Provider-selectable Plan request implemented.
- Generated OpenAPI/TypeScript contracts updated; bilingual desktop/390 px UI,
  accessibility coverage, focused real-stack browser denial path, and five-image
  Evidence workflow completed.
- Focused backend matrix: 44 passed. Focused Web/i18n matrix: 34 passed. Focused
  Playwright: 4 passed with source/workspace invariance and zero residual E2E
  resources. Canonical `make test`: Python 383 passed and Web 101 passed.
- Current Web Docker production build completed. A later all-image local rebuild
  stopped before tests on an external Debian security mirror `502`; the failure
  is preserved and was not retried. The focused browser matrix then reused the
  already-built exact API/Runner images plus the current Web image through the
  repository's no-build path.
- Draft PR creation and Fast/Heavy CI inspection remain pending. No live Provider
  request, key handling, merge, tag, release, deployment, License work, or
  Dependabot work was performed.

## Rollback

Before publication, delete only this branch's added files and reverse its scoped
edits. After publication, revert the branch commits. Never reset, clean, force
push, rewrite shared migration history, or alter `main`.
