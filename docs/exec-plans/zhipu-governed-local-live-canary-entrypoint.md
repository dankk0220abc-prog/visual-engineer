# Zhipu governed local live-canary entrypoint

Status: IMPLEMENTATION COMPLETE — INDEPENDENT SECURITY REVIEW REQUIRED

## Goal

Add one reviewed, one-shot, local server-side Zhipu-only entrypoint that can be
used in a later separately authorized phase for the first real Provider
validation. This package must not read a real key, send a real request, enable
any real Provider, generate live evidence, merge, release, or deploy.

## Safety boundary

- Exact fixed scenario `zhipu_live_canary_v1`, version `1`.
- Exact Zhipu adapter, endpoint, `glm-5.2`, JSON-object structured output,
  non-streaming, thinking disabled, 1024 output tokens, retry zero, concurrency
  one, and one outbound request maximum.
- Explicit process-only `VISUALENGINEER_LIVE_VALIDATION_AUTHORIZED=1` gate,
  separate from Provider enablement and checked before Secret access.
- `preflight` never reads `ZHIPU_API_KEY`, constructs an adapter, writes the
  database, creates an Invocation/Plan, or performs network I/O.
- The production factory has no arguments and rejects injected transport.
- The normal registry keeps Zhipu, Qwen, DeepSeek, Doubao, and Kimi disabled.
- Runtime results stay in PostgreSQL and are not mixed with Git/Evidence
  mutation.

## Baseline

- Authoritative repository: `/Users/danke/Developer/VisualEngineer`.
- Base `main`: `569fc39ad7d2b0e36432d14c50af93ee950b0a78`.
- Base tree: `ec0ce4c3478ff8b253b0a0b855981f19c950fbc2`.
- Alembic repository head: `20260809_0016`.
- Canonical base Fast `31311718732` and Heavy `31311718708` passed on the exact
  base SHA.
- Working branch: `codex/feat/zhipu-live-canary-entrypoint`.

## Implementation plan

1. Add a fixed public scenario and compact typed Provider response contract;
   normalize it into the existing server-owned `AIPlanContract`.
2. Add Secret-blind repository/database preflight, authorization ordering,
   fixed adapter checks, and a no-argument production factory.
3. Reuse `AIProviderInvocation` prepared/dispatching/terminal commits and
   persist typed Plan/Eval state only after validation.
4. Add the closed CLI and Make targets with safe output.
5. Cover authorization, Secret order, production/test separation, lifecycle,
   definite and ambiguous failures, request count, typed Plan, authority-zero,
   and redaction with synthetic credentials and MockTransport only.
6. Record `pre_live_entrypoint_not_live` Evidence, run focused and one relevant
   backend aggregate, publish a draft PR, and stop before independent review.

## Decisions

- No migration is needed. The canary reuses revision `20260809_0016` and its
  immutable Invocation lifecycle.
- The Provider authors a small closed content object. Server-owned Prompt,
  Provider identity, context, operations, authority boundary, and canonical
  digest are added only after that object validates.
- Each command creates an independent synthetic public Task/Run/Snapshot and
  `AIPlanRequest`; it never scans a repository or accepts a locator.
- `failed` is used for definite HTTP/schema/budget failures.
  `outcome_unknown` is used for timeout, transport ambiguity, or cancellation
  after the dispatch commit. No branch retries or falls back.
- A successful canary produces a generated `AIPlanRequest` plus system-policy
  Eval rows. It does not create the separately approved `plans` handoff row.

## Progress log

- Fail-closed Git/GitHub/Alembic/Provider/adapter/scanner baseline matched.
- Local database health passed; its retained developer volume remained at the
  historical `20260801_0015` and was deliberately not auto-migrated.
- Fixed scenario, preflight, authorization, service/factory, CLI, tests, and
  documentation implemented.
- Initial PostgreSQL Red run exposed the existing request insert guard; the
  canary now commits `requested` before the separate `generating` transition.
- Focused canary tests passed `36/36`; the canary plus system-owned governed AI
  Eval subset passed `53/53` after Provider-capability binding hardening.
- Combined canary, Invocation, Provider Foundation, and ordinary governed AI
  planning tests passed `170/170` before the additive binding regression.
- The one canonical backend aggregate passed `514/514` with `84.75%` coverage.
- Scoped implementation commit: `07adc9b35fcf5c5ba0b0d9e6211475bfb15d37bf`.

## Remaining gates

- Secret scan, generated contract drift, Ruff, mypy (144 source files),
  Prettier, ESLint, TypeScript, and `git diff --check` passed.
- Exact-path commit, ordinary push, draft PR, and remote CI.
- Independent final focused security review. No merge is authorized here.

## Rollback

Before publication, reverse only the scoped branch files. After publication,
revert the scoped commits. Never reset, clean, force-push, rewrite migration
history, move `main`, or delete runtime Invocation evidence.
