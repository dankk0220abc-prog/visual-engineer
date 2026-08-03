# Playwright Locale Contract Remediation Verification

- Date: 2026-08-03 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Candidate branch: `fix/playwright-locale-contracts-and-isolation`
- Independent Final Gate branch: `codex/localization-web-final-gate-20260803`
- Baseline: `01811c47738bbf2abdd1ff3827181a249c0fe141`
- Candidate: `4182cd60823aff7ee9a4b65d3da2287662ff48b0`
- Main: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Status: **INDEPENDENT FINAL GATE PASS - LOCAL SEAL AUTHORIZED**
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

## Independent Localization and Web Build Final Gate

The independent reviewer started from exact Candidate
`4182cd60823aff7ee9a4b65d3da2287662ff48b0` with local `main` fixed at
`450b660f1ab9e82993cfe1780a1967e5d6bf72cd`. The repository root was exact,
`main` was an ancestor of Candidate, worktree/index/untracked state was clean,
remote and stash were empty, and no merge, rebase, cherry-pick, revert, or
sequencer state existed. The reviewer created
`codex/localization-web-final-gate-20260803` directly from Candidate without
reset, overwrite, or main movement.

### Test-integrity review

- The 14 Playwright tests still produce 28 desktop/narrow result positions.
  The four existing conditional `test.skip` calls are byte-for-byte unchanged
  from the parent and produce the expected three runtime skips; no test or
  suite was disabled.
- No core business assertion was deleted or reduced to generic existence.
  Task persistence, plan approval/rejection, Runner cancellation events,
  workspace denial/rollback/discard, security fail-closed state, validation
  evidence, delivery denial boundaries, AI redaction, and human approval/
  rejection assertions remain.
- No serial mode, infinite retry, Playwright timeout-policy expansion, or
  ignored business `409` was introduced. Teardown alone tolerates a cancellation
  `409` after a terminal-state race, while the security scenario still asserts
  the expected `409` and structured error body.
- Ordinary flows use role, label, exact entity ID/API response, URL, timeline
  code, or `data-status`. The i18n scenarios retain real English and Chinese
  visible-copy assertions and persisted language switching.
- `setUiLocale` rejects a previously navigated context, verifies
  `navigator.language`, writes the exact localhost-scoped `ve_locale` Cookie
  before first navigation, and `expectUiLocale` verifies the Cookie, switcher,
  and `<html lang>`.
- Automatic fixture cleanup executes in `finally`; test-owned runs, jobs,
  workspaces, and grants are tracked independently of execution order. The
  security scenario restores only its exact temporary control-state mutations
  in its own nested `finally` before generic teardown.
- The sole production-source change in `4182cd6` is the non-visual
  `data-status` attribute on `StatusPill`. Rendered copy, tone classes, and
  state semantics are unchanged. The remediation commit does not change the
  Dockerfile, pnpm policy, dependencies, lockfile, Playwright config, or locale
  resources.

### Single aggregate execution

`make verify` was run exactly once on 2026-08-03 and exited `0`. No aggregate
rerun was performed.

| Gate                            | Result                                                                                                                                                          |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| contracts                       | generated OpenAPI/TypeScript drift check passed                                                                                                                 |
| format / lint / typecheck       | Ruff, Prettier, ESLint zero warnings, mypy 131 source files, and `tsc --noEmit` passed                                                                          |
| Python tests / coverage         | `351 passed`; `84.32%` total coverage, above the required 80%                                                                                                   |
| Web tests / coverage            | 15 files, `98 passed`; statements `74.44%`, branches `73.56%`, functions `72.70%`, lines `75.89%`                                                               |
| production build                | Next.js `16.2.12` optimized build passed; 14 App routes plus Proxy                                                                                              |
| Docker configuration            | base, test, workspace, E2E, and Customer 0 render checks passed                                                                                                 |
| migration                       | PostgreSQL empty upgrade, full downgrade, and full re-upgrade through `20260801_0015` passed                                                                    |
| Phase 4 / source invariance     | audit `25 passed`; repair `95 passed` plus PostgreSQL `14 passed`; 119 source entries, 10 Git objects, 2 status records, zero extension markers                 |
| Playwright                      | `25 passed`, `3` expected skipped, `0 failed` in 1.8 minutes; no locale locator mismatch or cascade workspace `409`                                             |
| Workspace Chaos                 | atomic precommit/postrename recovery, three stale leases fenced, revoke concurrency with zero post-revoke side effects, and unchanged source/`.git` fingerprint |
| Workspace / validation security | workspace and protocol `70 passed`; descriptor boundaries and Landlock/seccomp validation sandbox passed                                                        |
| Security                        | no high-confidence secrets; Runner/Compose static checks passed; Runner security `121 passed`; review security `20 passed`                                      |
| Eval                            | 94 deterministic cases across seven datasets plus repository scanner `7 passed`                                                                                 |
| final checks                    | aggregate `git diff --check` passed; final exit `0`                                                                                                             |

### Web build and runtime evidence

The lockfile SHA-256 is
`1910825c0e44fcb0c0d49bfda5087340071d9b6bec50bead184fd223411ac045`,
matching the Dockerfile assertion and cache ID. The Dockerfile pins Node
`24.18.0-alpine3.23` and pnpm `11.14.0`; dependency installation is
`--network=none`, `--offline`, and `--frozen-lockfile`. The retained dedicated
builder was healthy with BuildKit `v0.31.2` and 4.589 GB of task cache before
post-seal cleanup. The production, deny-first, and final-gate tags all resolved
to image `sha256:bf9ca91723478d086a17afb66c74ee4064946bd372966e3e83ac963f70768ef7`.
The retained production runtime was healthy and its mapped HTTP endpoint
returned success. Aggregate E2E reused cached dependency layers; it did not
prepare Web dependencies from zero.

### Final boundaries

The reviewer changed only this evidence file, the active ExecPlan, and Project
Status before sealing. Production code, tests, locale resources, Dockerfile,
pnpm policy, dependencies, and lockfile were not modified by the reviewer.
No remote was configured, no Provider was connected, and no API key was
configured. There was no fetch, push, pull request, tag, deploy, or main
movement. The local sealing subject is
`chore: seal localization and web build reproducibility`; its hash and exact
post-seal cleanup result are reported in the final handoff.

`VISUALENGINEER LOCALIZATION AND WEB BUILD FINAL GATE PASS - SEALED AND AWAITING EXPLICIT USER AUTHORIZATION FOR LOCAL FAST-FORWARD MAIN`
