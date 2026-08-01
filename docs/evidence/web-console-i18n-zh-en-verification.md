# Web Console zh-CN / en-US Localization Verification

## Candidate identity and authority

- Repository: `/Users/danke/Developer/VisualEngineer`
- Baseline: `main` at `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Candidate branch: `feat/web-console-i18n-zh-en`
- Baseline tracked diff, index, and untracked set: clean
- API contract, migration, real Provider, API key, remote Git, push, PR, tag,
  deployment, and `main` integration: not authorized and not used

## Implemented localization boundary

- One `next-intl` App Router integration supplies server and client messages
  from the same resolved locale without adding locale-prefixed routes.
- Supported locales are exactly `zh-CN` and `en-US`. `Accept-Language` selects
  the first visit; the HTTP-only `ve_locale` Cookie is authoritative after a
  selection. The root layout renders the resolved `<html lang>`.
- The global native `select` switcher posts a validated locale to the
  same-origin `/api/locale` route and reloads the current URL. It has an
  accessible name, keyboard-native operation, pending status, and error alert.
- Semantic ICU resources cover Dashboard, Tasks, Runs, Repository
  Intelligence, Runner, Execution Grants, Workspaces, Validation, Review and
  Release Readiness, Delivery Lifecycle, governed AI Planning, shared states,
  forms, dialogs, error feedback, navigation, and narrow layouts.
- Stable frontend mappings localize statuses, error codes, decisions, verdicts,
  actions, and Evals. Unknown error codes use localized fallback copy while the
  original diagnostic code and request ID remain visible.
- UUIDs, SHAs, digests, paths, refs, commands, user input, AuditEvent data,
  Provider Trace fields, Plan content, and immutable Evidence remain unchanged.
- The Provider request schema has no output locale. UI locale and AI output
  language are explicitly separated; Provider, Prompt binding, request digest,
  deterministic replay, and system-owned Eval contracts were not changed.

## Focused verification

| Boundary                           | Command/result                                           | Exit |
| ---------------------------------- | -------------------------------------------------------- | ---: |
| Translation resources and Web unit | `vitest run`: 14 files, 78 tests passed                  |    0 |
| Format                             | Web Prettier write and final check                       |    0 |
| Lint                               | Web ESLint, zero warnings                                |    0 |
| TypeScript                         | Web `tsc --noEmit`                                       |    0 |
| Production build                   | Next.js 16.2.12, 14 dynamic App routes plus Proxy        |    0 |
| Browser smoke                      | local production build: 4/4 desktop/narrow en/zh tests   |    0 |
| Source invariance                  | 119 source entries, 10 Git objects, status `PASS`        |    0 |
| Diff whitespace                    | `git diff --check`                                       |    0 |
| Contracts                          | Not run; API contract and generated schema are unchanged |  N/A |

## Preserved first failures

- Initial plain pnpm verification stopped before TypeScript because an
  install-generated native-build policy placeholder was unresolved. The
  placeholder was removed rather than approved; the repository's original
  allowlist remains unchanged. Final dependency policy verification passed.
- The first full Web unit run exposed missing `next-intl` test context and old
  mixed-language string assertions. A deterministic bilingual test translator
  and explicit locale assertions fixed the harness; final result is 78/78.
- First lint run reported seven warnings: five hook dependency warnings and two
  misplaced client directives. The directives and dependencies were repaired;
  final lint is clean.
- Two identical isolated Docker E2E attempts stopped in Web image dependency
  download after lockfile policy verification, at 509/511 packages, with
  registry timeout exit 1. Playwright never started in that environment.
- The first local production Playwright run exposed a non-exact heading query
  and an ineffective per-page locale header; the second retained the locale
  fixture issue. Tests now use Playwright browser locale contexts and exact
  headings. Final local production result is 4/4.

## Browser and source invariance

- `make source-invariance-check`: `PASS`, exit 0.
- Local production Playwright exercised both locales in desktop Chromium and a
  390 x 844 narrow viewport. It checked browser detection, Cookie persistence,
  refresh, language switching, `<html lang>`, seven core routes, accessible
  switcher labels, and horizontal overflow.
- Because isolated Docker image download failed externally before container
  startup, the new bilingual Playwright spec against real API/PostgreSQL and
  its script-owned fixture invariance remains `NOT VERIFIED`. It is not counted
  as a browser PASS.

## Aggregate and checkpoint

- Full aggregate Final Gate: intentionally deferred to independent review.
- Local checkpoint: this evidence is sealed with the candidate checkpoint on
  `feat/web-console-i18n-zh-en`.
- Preview: `http://127.0.0.1:3000`, backed by local API and PostgreSQL on the
  standard development ports; no Runner or Provider was started.
