# Playwright Locale Contract Remediation Verification

- Date: 2026-08-03 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/playwright-locale-contracts-and-isolation`
- Baseline: `01811c47738bbf2abdd1ff3827181a249c0fe141`
- Main: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Status: **COMPLETE - READY FOR INDEPENDENT FINAL GATE RE-REVIEW**
- Remote CI: **NOT VERIFIED**

## Git preflight

| Check                    | Result                                                         |
| ------------------------ | -------------------------------------------------------------- |
| physical and Git root    | exact `/Users/danke/Developer/VisualEngineer`                  |
| initial branch / HEAD    | candidate checkout at exact `01811c4`                          |
| expected refs            | candidate `01811c4`; main `450b660`                            |
| ancestry                 | main is an ancestor of candidate; candidate is 9 commits ahead |
| worktree/index/untracked | clean before branch creation                                   |
| remotes / stash          | no configured remote; empty stash                              |
| remediation branch       | created without force from exact candidate                     |

No reset, overwrite, clean, merge, rebase, main movement, fetch, push, pull
request, tag, deploy, or remote configuration occurred.

## Original failure classification

The existing `make-verify.log`, screenshots, videos, and traces recorded 28
Playwright cases: 18 failed, 7 passed, and 3 skipped.

| Category                             | Count | Evidence summary                                                                                                                                                 |
| ------------------------------------ | ----: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| direct locale/text contract mismatch |    15 | en-US scenarios waited for Chinese copy; zh-CN Phase 7 waited for English; localized statuses were compared with raw `ready`; one stale English heading was used |
| cascade state pollution              |     3 | Phase 4 assertion abort left an active workspace; later Phase 5 and narrow workspace creation returned `409`                                                     |
| independent product failure          |     0 | no independent product defect was present in the original 18 failures                                                                                            |

Trace state also proved that Phase 4 successfully created its workspace before
the status assertion failed, Phase 5 received the subsequent `409`, and Phase 7
was rendering `zh-CN` when the old English locator timed out.

## Implemented contracts

- `setUiLocale` requires a fresh context before navigation, verifies the
  Playwright browser locale, and writes `ve_locale` with the exact local test
  host and `/` path. `expectUiLocale` verifies cookie scope, switcher value, and
  `<html lang>`.
- Every E2E spec declares `en-US` or `zh-CN` explicitly. i18n tests continue to
  exercise real bilingual text and persisted switching.
- Workflow state uses role, label, entity ID, URL, API response, or
  `data-status`; raw diagnostic timeline codes remain visible where they are
  part of the operational evidence.
- The automatic resource fixture runs cleanup in `finally`, cancels or waits
  for active jobs/runs, settles and discards test workspaces, and revokes exact
  test grants. Phase 4 security restores only its own temporarily hidden
  registry and revoked grant before generic teardown.

## Verification ledger

| Gate                                       | Exit | Result                                                      |
| ------------------------------------------ | ---: | ----------------------------------------------------------- |
| representative locale mismatch selection   |    0 | `4/4` passed                                                |
| same-worker Phase 4 -> security -> Phase 5 |    0 | `3/3` passed; no workspace `409`                            |
| Phase 3 cancellation desktop/narrow        |    0 | `4/4` passed                                                |
| Phase 3/4/5/7 desktop+narrow subset        |    0 | `14` passed, `2` expected project skips                     |
| complete Playwright suite                  |    0 | `25` passed, `3` expected project skips, `0` failed         |
| i18n desktop/narrow focused                |    0 | `5` passed, `1` expected desktop skip                       |
| complete Web unit/component                |    0 | 15 files, `98/98` tests                                     |
| format-check                               |    0 | Ruff and both Prettier passes                               |
| lint                                       |    0 | Ruff and ESLint pass with zero warnings                     |
| TypeScript                                 |    0 | `tsc --noEmit`                                              |
| Next production build                      |    0 | 14 App routes plus Proxy                                    |
| source invariance                          |    0 | 119 entries, 10 Git objects, 2 status records, zero markers |
| final `git diff --check`                   |    0 | pass                                                        |

The first Phase 5 continuation run reached the previously hidden old button
name and timed out; subsequent runs exposed three more stale en-US strings.
Each was corrected to the current resource text, and the final Phase 5 flow and
same-worker chain passed. An initial full-suite narrow i18n attempt returned the
API's correct `422` because the newly unique title exceeded 120 characters;
the final unique fixture remains within the contract and the final full suite
passed. The first lint attempt reported the Playwright fixture callback named
`use` as a React Hook; renaming the callback parameter to `provide` resolved
the false classification and the final lint run passed.

## Runtime preservation and exclusions

The pre-existing `ve-web-bounded-fetch-20260803` builder, BuildKit cache,
`visualengineer-localization-web-build-finalgate:01811c4` image, and healthy
localization runtime were not cleaned, replaced, or stopped. The first
canonical E2E invocation rebuilt only changed source/application layers while
dependency-fetch layers were cached; later invocations used the retained E2E
images. No registry dependency re-download was requested.

Full `make verify`, Python/Runner full suites, Workspace Chaos, security/eval
aggregates, migration roundtrip, real Provider, Provider network, API key,
sealing, remote CI, push, pull request, tag, and deploy were not run. The local
checkpoint hash is reported in the final handoff after creation.
