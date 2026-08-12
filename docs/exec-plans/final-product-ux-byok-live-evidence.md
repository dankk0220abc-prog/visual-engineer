# Final Product UX + BYOK + Live Evidence Closure

## Goal

Close the remaining product-quality gaps in the existing Web Console without
changing its established light-blue visual system. Deliver natural bilingual
copy, portfolio-safe task projections, session-only BYOK, a bounded successful
Live Provider Evidence projection and UI, honest Runner recovery, responsive
and accessible presentation, real-browser screenshots, and one Draft PR whose
exact candidate passes Fast and Heavy.

## Authorized scope

- Read/write repository: `/Users/danke/Developer/VisualEngineer`.
- Read/write Evidence Vault: `/Users/danke/Documents/VisualEngineer-Evidence`.
- No access to CreativeDeploy or parent/sibling enumeration.
- No new real Provider request, no live canary, and no maintainer credential
  read. Tests use fake credentials and injected `httpx.MockTransport` only.
- Preserve the existing visual language, repository and Runner authority
  boundaries, immutable historical Invocation facts, and all prior failure
  evidence.

## Verified baseline

- Repository, local `main`, local `origin/main`, remote `refs/heads/main`, and
  GitHub default `main`: `d9be1313969fcbf6dca9ff9c4ea730c81bb16b7f`.
- Worktree, index, and untracked set clean; no stash or active Git operation.
- Branch: `codex/final-product-ux-byok-evidence`.
- Baseline code and database Alembic head: `20260809_0016`; implementation
  migration `20260810_0017` is now applied locally and verified current.
- Successful Invocation `3a9c354f7a58`: `succeeded`, `zhipu`, `glm-5.2`,
  usage `1362 / 654 / 2016`, Provider `11543 ms`, client `11553 ms`, billing
  unknown. Failures `59bd943ccb99`, `b7e92fd81760`, and `082b7af7750f`
  remain `outcome_unknown`.
- The ordinary AI Plan detail endpoint returns 500 for the successful canary
  because its request has a deliberately narrower canary shape. The remedy is
  a separate safe Evidence projection, not a relaxed ordinary schema.
- Runner registry reads succeed and report the sole Runner as `offline`.
  Runner Job listing fails on immutable pre-Permit Workspace side-effect
  results missing the later-required `side_effect_permit_id`; the 500 loses
  CORS headers and the browser misclassifies it as `network_error`.

## Frozen contracts

1. Task provenance receives durable classification from its trusted creation
   path, never from untrusted task text. Default product lists show user/demo
   tasks; system validation, security fixture, and live canary tasks are
   separately disclosed. Risk-bearing content is projected as a sanitized
   summary without changing provenance. The raw durable rows and security tests
   remain.
2. BYOK credentials are process-local, memory-only, bounded, expiring, and
   keyed by a random HttpOnly session cookie. They are never persisted,
   returned, logged, evidenced, placed in browser storage, or replaced by an
   owner credential. Disconnect and expiry overwrite the in-memory bytes.
3. Provider status separates adapter support, current-session credential, and
   historical live validation. A connected credential permits the existing
   closed real adapter for that session only; the fixture remains the default.
4. Live Evidence reads only successful, classified live Provider records and
   emits a typed allowlist: short correlation, Provider/model, lifecycle,
   nullable usage/cost semantics, latency, safe fingerprints/digests, typed Plan
   projection, trusted Eval summaries, public task classification, and actual
   governance relations. It never emits raw prompts, requests, responses,
   upstream IDs, credentials, cookies, or private paths.
5. Historical Runner results are never mutated or granted invented Permit
   evidence. An incompatible legacy result is projected as unavailable with a
   stable technical code so the remaining registry and job history can load.
6. IDs use short monospace presentation with an explicit copy control and full
   value available only through accessible disclosure/tooltip where warranted.

## Progress

- 2026-08-10 CST — **done**: exact Git/GitHub, DB/Alembic, service, UI, Runner,
  and four-Invocation preflight completed; contracts above frozen.
- 2026-08-10 CST — **done**: additive task classification and safe projection,
  ephemeral session-only BYOK, closed real-adapter product path, successful
  Live Evidence APIs, canary detail compatibility projection, and bounded
  legacy pre-Permit Runner result projection implemented.
- 2026-08-10 CST — **done**: Provider/Live Evidence, task grouping, dynamic
  repository locator help, natural offline Runner state, compact technical IDs,
  and bilingual resources implemented; focused API and Web checks pass.
- 2026-08-11 CST — **in progress**: PR #23 CI remediation separates canonical
  Runner DOM status from localized copy and task provenance from content-risk
  projection; targeted validation and amended-head CI remain pending.
- **in progress**: final focused verification and real local stack inspection.
- **pending**: canonical gates,
  real-browser inspection, Evidence Vault update, commit, Draft PR, Fast/Heavy.

## Verification

Run one concentrated changed-risk focused batch after implementation, then one
necessary backend canonical and one Web canonical. Use the real local
PostgreSQL/API/Web stack for final desktop and 390 px inspection. Record exact
test counts, browser errors, overflow measurements, secret-negative results,
screenshots and SHA-256 values in the final handoff and Evidence Vault.

## Rollback

Revert the single reviewed implementation commit. Downgrade only the additive
task-classification migration if explicitly required. Never rewrite Invocation
or Runner history, reset/clean the worktree, or touch `main`.

## Completion boundary

One logical commit, ordinary push, Draft PR, naturally triggered exact Fast and
Heavy with no manual rerun. Do not merge and do not perform the independent
Final Product Closure review in this task.
