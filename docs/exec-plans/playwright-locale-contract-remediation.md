# Playwright Locale Contract and Isolation Remediation

- Date: 2026-08-03 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/playwright-locale-contracts-and-isolation`
- Remediation baseline: `01811c47738bbf2abdd1ff3827181a249c0fe141`
- Main baseline: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Status: **INDEPENDENT FINAL GATE PASS - LOCAL SEAL AUTHORIZED**

## Goal

Make every Playwright scenario declare and prove its UI locale, replace
language-independent workflow assertions with stable semantic selectors, and
guarantee failure-safe cleanup of test-owned grants, workspaces, jobs, runs,
and fixture mutations so one failure cannot contaminate the next scenario.

## Scope

- Add one browser-context locale helper that sets the Playwright locale and a
  correctly scoped `ve_locale` cookie before navigation, then verifies the
  cookie, language switcher, and `<html lang>` after navigation.
- Keep i18n scenarios responsible for real English and Chinese display text;
  retain at least one locale-specific visible assertion in every core flow.
- Expose raw status only as a non-visual `data-status` attribute while keeping
  the localized status label visible.
- Give created records unique test identifiers and track test-owned grants,
  jobs, runs, and workspaces in an automatic teardown fixture.
- Reuse the canonical cancellation, diff, discard, and revocation APIs; restore
  only the exact security-test fixture records that the scenario temporarily
  mutates so generic teardown can remove them.

## Decisions and discoveries

- The original 18 failures classified as 15 direct locale/text contract
  mismatches and 3 downstream workspace `409` failures caused by an active
  workspace left behind after an earlier assertion aborted. No independent
  product failure was found in the original failure set.
- After the `409` was removed, Phase 5 exposed four older en-US display
  assertions that had never been reached. They were updated to the actual
  accessible names and authority-boundary punctuation; the assertions were not
  deleted or weakened.
- Phase 3 cancellation can move from `cancel_requested` to `cancelled` between
  two DOM assertions. The stable contract is now the cancel POST response plus
  persisted `cancel_requested` and `cancel_acknowledged` timeline events, with
  the terminal localized status still asserted.
- The narrow i18n fixture keeps a unique long title within the API's documented
  120-character limit and reports the real response body if fixture creation
  fails.

## Boundaries

No API or persistence contract, authority state machine, migration,
dependency, locale routing architecture, Provider, remote Git, `main`, deploy,
or visible design change is in scope. The only production-source change is the
non-visual raw `data-status` attribute on `StatusPill`.

Full `make verify`, Python/Runner full suites, Workspace Chaos, security/eval
aggregates, migration roundtrip, registry re-download, real Provider/API key,
sealing, push, pull request, tag, and deploy are explicitly excluded.

## Outcome

- Representative locale contracts, the original Phase 3/4/5/7 subset, the
  complete Playwright suite, and the dedicated desktop/narrow i18n suite pass.
- The same-worker Phase 4 workspace, Phase 4 security, and Phase 5 chain passes
  without an active-workspace `409`.
- Web unit, formatting, lint, TypeScript, production build, source invariance,
  and whitespace checks pass.
- Existing dedicated builder, cache, production image, and runtime were not
  removed or replaced. Canonical E2E reused cached dependency layers.

## Rollback

Revert only the eventual local remediation checkpoint. Do not reset, clean,
move `main`, remove the dedicated builder/cache/image, or delete unrelated
runtime state.

`VISUALENGINEER PLAYWRIGHT LOCALE CONTRACT REMEDIATION COMPLETE - READY FOR INDEPENDENT FINAL GATE RE-REVIEW`

## Independent Final Gate closure

On 2026-08-03 an independent reviewer checked exact Candidate
`4182cd60823aff7ee9a4b65d3da2287662ff48b0` against unchanged local `main`
`450b660f1ab9e82993cfe1780a1967e5d6bf72cd` on branch
`codex/localization-web-final-gate-20260803`.

- Preflight passed with clean worktree/index/untracked state, empty
  remote/stash, valid ancestry, and no in-progress Git operation.
- Candidate Diff integrity review passed: core assertions, three expected
  runtime skips, bilingual copy, locale-before-navigation proof, stable
  semantic selectors, and failure-safe cleanup remain intact. There is no
  serial/retry/timeout masking or ignored business `409`.
- The latest commit changes no Dockerfile, pnpm policy, dependency, lockfile,
  or translation resource. Its sole production-source delta is non-visual
  `StatusPill` `data-status` metadata.
- The one authorized `make verify` invocation exited `0`: contracts, format,
  lint, typecheck, Python/Web tests and coverage, production build, Docker
  rendering, migration, source invariance, Playwright, Workspace Chaos,
  workspace/validation/security targets, Eval, and final whitespace passed.
- Playwright produced exactly `25 passed`, `3 skipped`, `0 failed`; neither a
  locale locator mismatch nor a cascade workspace `409` occurred.
- The already validated production image and its offline/frozen install
  policy were preserved through the aggregate. Task-owned builder/cache,
  images, runtime, E2E resources, and fixtures are authorized for exact
  post-seal cleanup only; global prune remains prohibited.
- No production code, tests, locale resources, dependency policy, dependency,
  or lockfile was changed by the reviewer. No remote, Provider, API key, push,
  pull request, tag, deploy, or main movement was introduced.

The branch is authorized only for the local sealing commit
`chore: seal localization and web build reproducibility`. Local fast-forward
of `main` remains a separate action requiring explicit user authorization.

`VISUALENGINEER LOCALIZATION AND WEB BUILD FINAL GATE PASS - SEALED AND AWAITING EXPLICIT USER AUTHORIZATION FOR LOCAL FAST-FORWARD MAIN`
