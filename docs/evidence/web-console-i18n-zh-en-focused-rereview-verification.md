# Web Console zh-CN / en-US Focused Re-review Verification

- Date: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Candidate: `23dd0d5c89ccf11631e6da8da156a284949c6c30`
- Main: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Review branch: `codex/audit-i18n-zh-en-final-rereview-20260802`
- Result: **FAIL - BLOCKING RESPONSIVE FINDING; CANONICAL E2E NOT VERIFIED**

## Git preflight

| Check                     | Result                                           |
| ------------------------- | ------------------------------------------------ |
| physical and Git root     | exact `/Users/danke/Developer/VisualEngineer`    |
| candidate object          | exact `23dd0d5c89ccf11631e6da8da156a284949c6c30` |
| local `main`              | exact `450b660f1ab9e82993cfe1780a1967e5d6bf72cd` |
| merge-base                | exact `450b660f1ab9e82993cfe1780a1967e5d6bf72cd` |
| ancestry                  | main is an ancestor of candidate, exit 0         |
| worktree/index/untracked  | clean before branch creation                     |
| remote                    | none configured                                  |
| stash                     | empty                                            |
| in-progress Git operation | none                                             |
| audit branch              | created without force from exact candidate       |

No reset, clean, overwrite, stash, merge, rebase, fetch, remote addition, push,
PR, tag, deploy, or `main` movement occurred.

## Candidate/source boundary

The candidate range changes Web production, locale resources, Web tests,
lockfile, and documentation. It does not change `apps/api`, migrations,
`packages/api-contract`, database models, AuditEvent definitions, or Provider
authority code. Locale projection remains a Web presentation concern; machine
enum/code values remain untranslated in API and persistence contracts.

## Verification ledger

| Gate                                      | Command/result                                                                                       |  Exit |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----: |
| focused status/error/message/AI selection | `vitest run` on four focused files, 47/47                                                            |     0 |
| full Web unit/component                   | `make test-web`, 14 files, 96/96                                                                     |     0 |
| key parity and AST static calls           | included in `config.test.ts`; >600 literal production calls, no missing/dynamic calls                |     0 |
| typed dynamic registry                    | API status/state/verdict, protocol failure, Delivery regression, action, and mandatory Eval coverage |     0 |
| all-resource ICU                          | every leaf in both resources compiled                                                                |     0 |
| interpolation parity                      | every bilingual leaf matched                                                                         |     0 |
| status/error fallback                     | known and unknown mapping plus raw code/request ID tests                                             |     0 |
| exact AI authority UI                     | approved governed AI Plan in both locales                                                            |     0 |
| format-check                              | `make format-check`, Ruff and Prettier                                                               |     0 |
| lint                                      | `make lint`, Ruff and ESLint with zero warnings                                                      |     0 |
| Python/TypeScript typecheck               | `make typecheck`, mypy 131 files and `tsc --noEmit`                                                  |     0 |
| production build                          | `make build`, Next 16.2.12, 14 dynamic routes plus Proxy                                             |     0 |
| source invariance                         | 119 entries, 10 Git objects, 2 status records, 0 extension markers                                   |     0 |
| candidate/worktree whitespace             | both `git diff --check` forms                                                                        |     0 |
| Impeccable detector                       | one run on the nine changed UI components, `[]`                                                      |     0 |
| Canonical isolated E2E                    | two candidate-matching build attempts; registry timeout before startup                               | 1 / 1 |
| Impeccable real 390 px responsive review  | page width 450 at viewport 390 on approved Run                                                       |  FAIL |

Full `make verify` was intentionally not run.

## Controlled negative mutation evidence

All mutations were applied only to ignored, task-owned archive copies under
`.runtime/i18n-audit-mutations`. The candidate worktree and existing tests were
never edited. Each copy used the candidate's permanent `config.test.ts` and the
already installed Vitest binary; every copy was deleted after evidence was
captured.

| Mutation                                                                                                | Expected detector                           | Actual                                                                    |
| ------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------- |
| remove `navigation.tasks` from both locale trees                                                        | AST call exists but both resources lack key | exit 1; missing `navigation.tasks` at `main-navigation.tsx:13`            |
| change source call to `t("tasks_typo")`                                                                 | nonexistent source key                      | exit 1; missing `navigation.tasks_typo`                                   |
| change translator namespace to `navigationTypo`                                                         | wrong namespace                             | exit 1; all nine `navigationTypo.*` calls reported                        |
| remove `sealed`, `delivery_authorization_expired`, and `approval_boundary_bypass` from typed registries | status, error, and mandatory Eval gaps      | exit 1; three independent registry tests failed with exact missing values |
| add an unused malformed plural message to both resources                                                | full-resource ICU compilation               | exit 1; `INVALID_MESSAGE: EXPECT_ARGUMENT_CLOSING_BRACE`                  |
| add an unused `{count}` / `{total}` bilingual pair                                                      | interpolation parity                        | exit 1; exact `count` versus `total` mismatch                             |

The permanent in-memory negative fixture also checks both languages
independently after the same used key is removed, so the first English failure
cannot mask the Chinese-side assertion.

## Canonical isolated Compose/Playwright

Exact command for both attempts:

```sh
E2E_COMPOSE_PROJECT_NAME=ve-i18n-final-rereview-20260802 \
E2E_DB_PORT=35482 E2E_API_PORT=38082 E2E_WEB_PORT=33082 \
BUILDKIT_PROGRESS=plain ./scripts/run-e2e.sh i18n-console.spec.ts
```

Attempt 1:

- exit `1`;
- frozen Web `pnpm install` reached 507/511, then timed out at build step
  `apps/web/Dockerfile:11` after approximately 2072 seconds;
- PostgreSQL, API, Web, fixture seeding, and Playwright never started;
- the script removed the exact Compose project, volumes, network, and temporary
  fixture.

Recovery check:

- exact `next`, `playwright-core`, and `prettier` tarball probes each returned
  HTTP 200 in approximately 1.3-1.4 seconds;
- this was treated as network recovery and authorized the one allowed clean
  retry.

Attempt 2:

- identical command, exit `1`;
- frozen Web `pnpm install` ended at 506/511 with registry socket stalls and
  `TimeoutError: The operation was aborted due to timeout` after approximately
  3438 seconds;
- PostgreSQL, API, Web, fixture seeding, and Playwright again never started;
- no third attempt was made.

Final cleanup removed the exact task Compose resources, temporary fixtures, and
the two task-owned image tags
`ve-i18n-final-rereview-20260802-api:latest` and
`ve-i18n-final-rereview-20260802-runner:latest`. No broad Docker prune or
pre-existing service change occurred.

Disposition: desktop/narrow bilingual canonical E2E, real Delivery lifecycle
error projection, and source-invariance assertions inside that script are
`NOT VERIFIED` for this review. The registry failure is not attributed to the
candidate.

## Bounded real localhost browser evidence

The current candidate production build was started temporarily at
`http://127.0.0.1:3000` against the already-running localhost-only API and real
PostgreSQL service. This was a read-only, non-isolated visual diagnostic and
does not replace Canonical E2E.

| Surface              | Locale / viewport    | Result                                                                                                                   |
| -------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| task console         | `zh-CN`, 1440 x 1000 | `<html lang="zh-CN">`; page `scrollWidth=1440`; no overflow; real task data visible                                      |
| approved Run         | `zh-CN`, desktop     | actual approved governed AI Plan and raw UUID/SHA/digests visible                                                        |
| approved Run         | `zh-CN`, 390 x 844   | exact authority callout fits; page `scrollWidth=450` -> **blocking overflow**                                            |
| approved Run         | `en-US`, 390 x 844   | locale switch preserves exact Run URL/entity; exact authority copy fits; page `scrollWidth=450` -> **blocking overflow** |
| approved Run refresh | `en-US`, 390 x 844   | locale Cookie persists; `<html lang="en-US">`; selected locale and Run URL remain unchanged                              |
| Delivery             | `en-US`, 390 x 844   | empty lifecycle state fits, `scrollWidth=390`                                                                            |
| Delivery             | `zh-CN`, 390 x 844   | translated empty lifecycle state fits, `scrollWidth=390`                                                                 |

Approved AI Plan evidence present in both locales:

- `execution_available=false` from the actual Plan response;
- AI Plan Approval is not an Execution Grant;
- Review Approval is not automatically issued;
- Delivery Authorization is not automatically issued;
- Side-effect Permit is not automatically issued.

The locale select retained a visible focus ring in the keyboard sample, and the
browser console had zero warning/error entries. UUIDs, SHAs, paths, digests,
Eval IDs, request IDs, and codes remained verbatim.

The confirmed overflow originates in the Input context manifest region of
`apps/web/src/components/ai-plan-console.tsx:302-336`. At 390 px, the section
and its long digest/context rows extend to approximately x=450 in both locales.

The temporary localhost preview was stopped with the expected interrupt exit
`130`; port 3000 was confirmed closed afterward.

## Final scope state before checkpoint

- production code changed by reviewer: **none**
- locale resources changed by reviewer: **none**
- existing tests changed by reviewer: **none**
- dependencies or lockfile changed by reviewer: **none**
- full `make verify`: **not run**
- sealing: **not performed**
- main/remote actions: **not performed**
