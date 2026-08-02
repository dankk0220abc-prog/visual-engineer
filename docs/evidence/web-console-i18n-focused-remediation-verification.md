# Web Console Localization Focused Remediation Verification

- Date: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/web-console-i18n-focused-remediation`
- Baseline: `1ed1ecb0bbccd5171c1182e86f9359ba29dc0386`
- Production candidate: `5f3ef6cf3bf21a4521124007ef5aa363075c4327`
- Main: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Status: **COMPLETE - READY FOR INDEPENDENT FOCUSED RE-REVIEW**
- Remote CI: **NOT VERIFIED**

## Git preflight

| Check                    | Result                                                     |
| ------------------------ | ---------------------------------------------------------- |
| physical and Git root    | exact `/Users/danke/Developer/VisualEngineer`              |
| initial branch / HEAD    | audit checkpoint at exact `1ed1ecb`                        |
| expected refs            | candidate `5f3ef6c`; main `450b660`                        |
| ancestry                 | main ancestor of candidate; candidate ancestor of baseline |
| worktree/index/untracked | clean before branch creation                               |
| remediation branch       | created without force from exact audit checkpoint          |

No reset, overwrite, clean, stash, merge, rebase, main movement, fetch, push,
pull request, tag, deploy, or remote configuration occurred.

## Finding remediation

### `VE-I18N-FR-001` - stable status and error projection

- `localizedStatusKeys` now covers the generated Web-rendered API
  status/state/verdict set, including `sealed`, `not_ready`, `skipped`, and
  `superseded`, with explicit `zh-CN` and `en-US` messages.
- `localizedErrorKeys` is the single typed error registry. It covers generated
  protocol failures and current Delivery errors, including authorization,
  baseline/readiness, confirmation, dispatch/retry, stale Review, and local
  result-binding failures.
- Known codes render specific localized copy plus the raw diagnostic code and
  request ID when available. Unknown codes use a localized fallback while
  preserving the unknown code and request ID.
- Dynamic action and mandatory Eval labels use typed registries. API values,
  persisted states, AuditEvents, and business comparisons remain unchanged.
- Delivery authorization, preview, and dispatch surfaces now use the shared
  error projection; Task details localizes the former `Committed HEAD` label.

### `VE-I18N-FR-002` - permanent message contract

- A TypeScript AST scan finds production translators created by static
  `useTranslations(...)` and `getTranslations(...)` calls, requires literal
  call keys, and verifies every call independently against both locale trees.
  Negative tests remove the same key from both trees and inject a typo, so
  parity alone cannot mask a missing call key.
- Every leaf in both message resources is compiled through `next-intl`,
  including unused messages. An intentionally invalid unused ICU message must
  fail. Interpolation variable sets must match across locales.
- Dynamic status/error/action/Eval registries are checked against generated
  API schema enums or the authoritative mandatory Eval source and every
  registry entry must have both locale resources. The regression set fixes
  `sealed`, `not_ready`, `skipped`, Delivery lifecycle codes, and unknown-code
  fallback behavior without a third translation catalog.

### `VE-I18N-FR-003` - exact AI execution boundary

- Plan Review renders the actual contract value as
  `execution_available=false` in a persistent localized callout, including for
  an approved governed AI Plan.
- Both locales state that AI Plan Approval is not an Execution Grant and does
  not automatically issue Review Approval, Delivery Authorization, or a
  Side-effect Permit.
- Plan, Prompt, Trace, Eval, and immutable Evidence content remains unmodified
  and untranslated.

## Verification ledger

| Gate                                          | Exit | Result                                                        |
| --------------------------------------------- | ---: | ------------------------------------------------------------- |
| focused i18n/status/error/AI UI selection     |    0 | 4 files, `47/47` tests                                        |
| translation key parity                        |    0 | included; exact bilingual leaf-key equality                   |
| static production call-key completeness       |    0 | included; more than 600 literal calls, zero missing/dynamic   |
| dynamic registry mapping coverage             |    0 | included; status/error/action/Eval resources complete         |
| full-message ICU compilation                  |    0 | included; every bilingual leaf plus invalid-unused regression |
| status/error fallback                         |    0 | included; raw code and request ID retained                    |
| AI `execution_available=false` UI             |    0 | included; approved governed Plan in `zh-CN` and `en-US`       |
| complete Web unit/component                   |    0 | 14 files, final count recorded as `96/96`                     |
| format-check                                  |    0 | Prettier root and Web pass                                    |
| lint                                          |    0 | ESLint, zero warnings                                         |
| TypeScript                                    |    0 | `tsc --noEmit`                                                |
| Next production build                         |    0 | 14 dynamic App routes plus Proxy                              |
| source invariance                             |    0 | 119 entries, 10 Git objects, 2 status records, zero markers   |
| exact local bilingual browser smoke           |    0 | `4/4`; desktop and 390px narrow in both locales               |
| Impeccable changed-surface detector           |    0 | no blocking or obvious findings (`[]`)                        |
| final `git diff --check`                      |    0 | pass                                                          |
| candidate-matching isolated Docker Playwright |    - | not run; current matching image requires a registry rebuild   |

The first format-check attempt exited `1` on
`workspace-detail-console.tsx`; formatting that file and every subsequent
format-check passed with exit `0`.

## Browser and Impeccable evidence

The repository already had Web dependencies and a Playwright Chromium binary,
so the exact existing localization smoke was run directly against current
source for `en-US` and `zh-CN` in desktop and `390px` narrow projects. All four
cases passed, including the suite's locale and horizontal-overflow assertions.
Focused component tests separately exercise the changed status, Delivery
error, and approved AI callout surfaces in both languages.

Impeccable context and its one required changed-surface detector run covered
the directly modified UI components and returned an empty result. No blocking
or obvious wrapping, truncation, focus, contrast, or narrow-layout defect was
found, so no aesthetic-only change was added.

An initial incorrectly scoped `pnpm` browser command started the broader
24-test suite and was interrupted with exit `130`. Its failures occurred on
unrelated locale/port assumptions before writes; read-only API checks found no
created `E2E Foundation` task. It is not counted as product evidence. Only its
exact task-owned `test-results` and `playwright-report` directories were
removed. The corrected exact four-case command then passed.

## Excluded Docker and authority scope

Canonical isolated Docker Playwright was not run. The locally present Web
image predates this remediation, while producing a candidate-matching image
would repeat the prior audit's registry-blocked build. No dependency version,
network timeout, production code, or E2E rigor was changed to bypass that
condition. Real isolated API/PostgreSQL Playwright is left to the next
independent focused re-review.

No full `make verify`, unrelated Python/Runner/Delivery aggregate, Workspace
Chaos, migration roundtrip, real Provider, Provider network, API key, sealing,
main movement, remote Git, push, PR, tag, or deploy was used. Pre-existing API
and PostgreSQL services were not changed. The local checkpoint hash is
reported in the final handoff after creation.
