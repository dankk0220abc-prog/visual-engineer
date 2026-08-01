# Web Console zh-CN / en-US Localization Slice

## Goal

Internationalize the complete existing Web Console UI for `zh-CN` and
`en-US` while preserving language-neutral API contracts, immutable technical
evidence, and every existing authority boundary.

## Scope and boundaries

- Use one App Router-compatible i18n layer with semantic message keys, ICU
  interpolation, key-parity enforcement, server rendering, and client hooks.
- Detect a first-visit locale from `Accept-Language`, persist the resolved
  locale in an HTTP-only same-site Cookie, and use that Cookie as the durable
  server/client source after selection.
- Keep the current non-prefixed internal routes. A locale change reloads the
  current route so server-rendered content and `<html lang>` change together.
- Localize all current routes and shared Web components on desktop and narrow
  layouts, including stable code/status/action-key mappings and safe unknown
  fallbacks that preserve the raw diagnostic value.
- Preserve UUIDs, SHAs, digests, paths, refs, commands, user input, raw error
  codes, AuditEvent payloads, Plans, Trace payloads, and Evidence content.
- Do not change API schemas, persistence, migrations, Provider behavior,
  Prompt binding, request digests, deterministic replay, or Evals.
- Do not use a real Provider, Provider SDK/network, API key, remote Git, push,
  PR, merge, tag, deploy, or `main` integration.

## Design decisions

1. Use `next-intl` as the single i18n library because the repository uses
   Next.js App Router and React Server/Client Components. Request config reads
   the locale server-side and the root layout supplies the same messages to
   client components.
2. Keep `zh-CN` and `en-US` as the only accepted locale identifiers. Invalid
   Cookie and request values fail safely to browser negotiation, then `en-US`.
3. A small Next.js proxy sets the first-visit Cookie from `Accept-Language`.
   The language switcher posts to a same-origin route that validates and sets
   the Cookie, then reloads the exact current URL.
4. Locale resources use stable domain keys rather than source sentences. A
   parity test recursively compares both locale trees and fails on missing or
   extra keys.
5. UI-facing API errors and statuses are mapped from stable raw identifiers.
   Unknown identifiers use a localized fallback and render the original code.
6. The current AI request contract has no output locale. This slice labels the
   distinction between interface language and immutable AI output; adding an
   output locale is deferred because it must bind Prompt, digest, fixture
   replay, and system-owned Eval contracts together.

## Progress

- 2026-08-02 CST — **done**: exact repository/main baseline and clean state
  verified; `AGENTS.md`, App Router architecture, package/test configuration,
  Phase 7 AI boundaries, and Provider request schema inspected; feature branch
  created from `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`.
- 2026-08-02 CST — **done**: `next-intl` foundation, locale negotiation and
  Cookie persistence, semantic en/zh resources, glossary, all current Web
  routes/shared component conversion, stable error/status/Eval mappings, and
  AI output-language boundary.
- 2026-08-02 CST — **done**: 78 focused Web unit tests, formatting, lint,
  TypeScript, production build, four desktop/narrow bilingual Playwright
  smokes, source invariance, and diff whitespace passed.
- 2026-08-02 CST — **not verified**: isolated Docker Playwright against real
  API/PostgreSQL stopped twice before startup because registry downloads timed
  out at 509/511 packages. The full aggregate remains for independent Final
  Gate; this infrastructure failure is preserved in Evidence.

## Verification and evidence

Record commands, counts, exit codes, preserved first failures, browser locale
and layout observations, source invariance, and final Git identity in
`docs/evidence/web-console-i18n-zh-en-verification.md`.

Run focused Web tests first, then formatting, lint, TypeScript, production
build, source invariance, English and Chinese Playwright core flows on desktop
and narrow viewports, and `git diff --check`. Contracts run only if the API
contract changes; this plan explicitly avoids such a change.

## Rollback

Revert only this branch's reviewed local checkpoint. Do not reset, clean,
rewrite `main`, modify environment files, or remove unrelated runtime state.

## Completion conditions

- Both locale trees have exact key parity and all focused locale tests pass.
- First visit, Cookie persistence, refresh, navigation, `<html lang>`, and the
  keyboard-accessible language switcher behave consistently without a visible
  mixed-language hydration state.
- All current core routes and shared components render localized UI chrome in
  both languages while raw technical and immutable evidence values remain
  unchanged.
- Focused unit, quality, build, source-invariance, and bilingual real-browser
  gates pass, one local checkpoint is created, and the preview is left running
  with an exact safe stop command.
