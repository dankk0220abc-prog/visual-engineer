# Web Console zh-CN / en-US Localization Focused Review Verification

- Date: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `codex/audit-web-console-i18n-zh-en-focused-20260802`
- Candidate: `5f3ef6cf3bf21a4521124007ef5aa363075c4327`
- Main: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Candidate tree: `fb0bd669779b5217766d73aef5a08bdcb8f2aa7b`
- Status: **FOCUSED REVIEW FAIL - REMEDIATION REQUIRED**
- Production changes by auditor: **none**
- Message resource changes by auditor: **none**
- Existing test changes by auditor: **none**
- Remote CI: **NOT VERIFIED**

## Git preflight

| Check                    | Confirmed result                                     |
| ------------------------ | ---------------------------------------------------- |
| physical and Git root    | exact `/Users/danke/Developer/VisualEngineer`        |
| initial branch / HEAD    | implementation branch at exact candidate             |
| candidate                | exact commit, one parent                             |
| local `main`             | exact expected baseline                              |
| ancestry                 | main is exact parent, merge-base, and ancestor       |
| worktree/index/untracked | empty before branch creation and before audit writes |
| remote / stash           | empty                                                |
| worktrees                | one expected worktree                                |
| merge/rebase state       | none                                                 |
| audit branch             | created without force directly from candidate        |

The candidate range contains 52 files, 4,366 insertions, and 1,100 deletions.
It changes Web code/tests/messages, the lockfile, and slice documentation; no
API source, migration, generated contract, Runner, or Provider source changes.

No reset, overwrite, clean, stash, rebase, cherry-pick, merge, fetch, push,
pull request, tag, deploy, remote configuration, or `main` movement occurred.

## Independent mapping evidence

The API schema enum comparison against `localizedStatusKeys` produced:

```text
PlanStatus: ... | missing=superseded
ReleaseReadinessVerdictResponse: ... | missing=not_ready
ValidationSuiteStepState: ... | missing=skipped
WorkspaceState: ... | missing=sealed
```

`StatusPill` translates a string only when `isLocalizedStatus` accepts it;
otherwise it returns the raw child. Current components feed Workspace state,
Plan status, Release Readiness verdict, and Validation step state through this
mapping. The valid missing values therefore remain raw in `zh-CN`.

Delivery history independently shows:

```tsx
{
  dispatch.error_code ? <p>{dispatch.error_code}</p> : null;
}
```

No Delivery-specific stable codes such as `delivery_authorization_expired`,
`delivery_confirmation_mismatch`, `delivery_authorization_stale`, or
`local_delivery_result_binding_mismatch` exist in the locale resources or the
stable error map. Raw code retention is correct; the missing localized
label/fallback is not.

## Independent message-contract evidence

Read-only diagnostics against the candidate reported:

```text
en-US namespaces=22 leaves=740
zh-CN namespaces=22 leaves=740
placeholder_mismatches=0
en-US translation_errors=0
zh-CN translation_errors=0
literal_calls_checked=1016 missing=0
```

Production source uses one `next-intl` dependency and no second i18n library.
No production locale equality branch was found. The only locale equality
branches occur in test translator setup.

The permanent locale resource test only compares the two key sets. There is
no `next-intl` `AppConfig.Messages` augmentation; the installed type fallback
is `Record<string, any>`. No permanent test enumerates source references,
parses all ICU messages, compares placeholder sets, or proves a wrong key is
rejected. The independent diagnostic proves current data only.

## Locale, Cookie, and authority source evidence

- Supported locales are exactly `zh-CN` and `en-US`; `en-US` is the default.
- Chinese language ranges resolve to `zh-CN`; unsupported/non-Chinese ranges
  fall back to `en-US`; a valid `ve_locale` Cookie takes precedence.
- Proxy and POST route use `HttpOnly`, `SameSite=Lax`, path `/`, max age
  31,536,000 seconds, and `Secure` for an HTTPS request URL.
- Request config resolves the locale once and imports that locale's message
  tree; root layout reads the same request config for `<html lang>` and the
  client provider.
- The switcher uses a native labeled select, validates the locale, POSTs to a
  same-origin route, and calls `window.location.reload()`, preserving the
  current browser URL.
- AI interface/output boundary and all five authority names are distinct in
  both locale resources.
- The API contract fixes `Plan.execution_available` to literal `false`, but
  Web production components/messages never render that field; its only Web
  occurrence is test fixture data.

Runtime Cookie attributes, persistence across a reopened browser, hydration
behavior, and URL/entity preservation remain `NOT VERIFIED` in the required
real isolated stack because Playwright did not start.

## Focused command ledger

| Gate / selection                        | Exit | Result                                                      |
| --------------------------------------- | ---: | ----------------------------------------------------------- |
| Web unit/component                      |    0 | 14 files, `78 passed`                                       |
| translation key parity                  |    0 | current trees equal, 740 leaves each                        |
| independent ICU parse                   |    0 | zero errors in both locales                                 |
| independent placeholder parity          |    0 | zero mismatches                                             |
| independent literal source-key check    |    0 | 1,016 calls, zero current misses                            |
| locale detection and Cookie route units |    0 | included in Web `78/78`                                     |
| API error fallback units                |    0 | known conflict/unknown code and request ID behavior pass    |
| Ruff/Prettier format checks             |    0 | Ruff 168 files; Prettier pass                               |
| Ruff/ESLint lint                        |    0 | pass                                                        |
| TypeScript                              |    0 | `tsc --noEmit`                                              |
| Next production build                   |    0 | 14 dynamic App routes plus Proxy                            |
| source invariance                       |    0 | 119 entries, 10 Git objects, 2 status records, zero markers |
| candidate/worktree `git diff --check`   |    0 | pass                                                        |
| canonical isolated Playwright attempt 1 |    1 | registry timeout at 509/511; Playwright not started         |
| canonical isolated Playwright retry     |    1 | registry timeout at 508/511; Playwright not started         |
| contracts                               |    - | not run; API/generated contract unchanged                   |
| full `make verify`                      |    - | not run by focused FAIL stop rule                           |

The production build completed with Next.js 16.2.12. The canonical isolated
command for both attempts was:

```text
E2E_COMPOSE_PROJECT_NAME=ve-i18n-focused-audit-20260802
E2E_DB_PORT=25482 E2E_API_PORT=28082 E2E_WEB_PORT=23082
BUILDKIT_PROGRESS=plain ./scripts/run-e2e.sh i18n-console.spec.ts
```

Attempt 1 passed frozen lockfile and 661-entry supply-chain policy checks, then
failed in Dockerfile line 11 with `TimeoutError` and exit 1 at 509/511.
Limited range probes for the failing Next, Playwright Core, and TypeScript
tarballs later returned HTTP 206, so the exact command was retried. Attempt 2
again passed the same lockfile policy and failed at the same Dockerfile line
with timeout exit 1 at 508/511. Neither attempt created a running product
container or reached fixture seeding/Playwright.

## Preserved invalid auxiliary attempts

- A read-only diff display used unsupported `git rev-list --decorate` and
  exited 129; the correct `git log --decorate` rerun passed.
- The first Docker resource check passed multiple image names to
  `docker image ls`; its usage error was masked by later shell commands. A
  `set -eu` per-image/per-port rerun passed before E2E.
- Two independent Node diagnostics initially ran from the monorepo root and
  could not resolve Web workspace modules. Rerunning from `apps/web` produced
  the recorded zero-error ICU/source results.
- One read-only `rg` command had invalid shell quoting. The corrected command
  confirmed no `next-intl` AppConfig augmentation.

None of these invalid auxiliary attempts changed repository or runtime state,
and none is counted as candidate evidence.

## Docker cleanup and final scope

Both failed canonical attempts invoked their cleanup trap. Postflight then
confirmed zero containers, networks, and volumes for
`ve-i18n-focused-audit-20260802`, removed each temporary adversarial fixture,
and removed only the exact audit-owned API/Runner image tags. No Web image was
created. The pre-existing VisualEngineer API/database and CreativeDeploy
PostgreSQL container IDs remained unchanged and running.

Audit writes are limited to this Evidence file, the independent audit report,
and the independent ExecPlan. No production repair, message/test edit, full
aggregate, preview, human visual acceptance, sealing, remote action, Provider,
or API key was used.
