# Web Console zh-CN / en-US Localization Independent Focused Review

- Started: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `codex/audit-web-console-i18n-zh-en-focused-20260802`
- Candidate: `5f3ef6cf3bf21a4521124007ef5aa363075c4327`
- Main baseline: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Status: `COMPLETE - FOCUSED REVIEW FAIL - REMEDIATION REQUIRED`
- Real isolated Playwright: `NOT VERIFIED - REGISTRY BLOCKED BEFORE STARTUP`
- Remote CI: `NOT VERIFIED`

## Goal

Independently audit the global Web Console `zh-CN` / `en-US` slice, excluding
AI output-language control and every real Provider/API-key capability.
Production code, message resources, dependencies, and existing tests are
read-only. Any focused localization, SSR/CSR, machine-contract, or authority
copy Finding requires an audit-only FAIL checkpoint and stops the aggregate.

## Scope and allowed writes

Allowed writes are limited to:

- this independent ExecPlan;
- the focused audit report; and
- the focused verification Evidence.

Candidate production code, locale messages, dependencies, API contracts,
migrations, generated artifacts, fixtures, and existing tests remain
unchanged.

## Constraints

- Anchor all work to `/Users/danke/Developer/VisualEngineer` and the exact
  candidate/main pair.
- Stop on Git baseline mismatch; do not reset, overwrite, stash, or force.
- Use the canonical real PostgreSQL/API/Web/Runner/fixture E2E flow and only
  candidate-matching application images.
- Do not weaken tests, use mocks in place of PostgreSQL/API, change dependency
  versions, or use `E2E_SKIP_BUILD` without a proven candidate image.
- Do not run `make verify` after a focused Finding.
- Do not seal, move main, fetch, push, create a PR, tag, deploy, connect a real
  Provider, or configure an API key on FAIL.
- Remove only exact task-owned Docker resources and image tags.

## Progress

- done - exact root, candidate, main, parent/ancestry, clean inventory, remote,
  stash, worktrees, and merge-state preflight
- done - independent branch created without force from the exact candidate
- done - candidate diff, i18n architecture, request/SSR/client message flow,
  Cookie, switcher, routes, machine mappings, AI boundary, and core surfaces
  inspected
- done - current key parity, ICU parse, placeholder parity, and source literal
  key diagnostics
- done - Web `78/78`, format, lint, TypeScript, production build, source
  invariance, and diff checks
- done - canonical real-stack Playwright attempted twice with unique project
  and ports; both registry-blocked before startup
- done - exact task-owned Docker cleanup after each failed attempt
- done - `VE-I18N-FR-001`, `VE-I18N-FR-002`, and `VE-I18N-FR-003` confirmed
- done - audit report, Evidence, and ExecPlan
- done - audit-only FAIL checkpoint recorded by this commit; commit ID reported
  externally

## Decision

The candidate has one coherent `next-intl` architecture and its current
resources pass parity/ICU/source diagnostics, but it does not satisfy the
focused contract:

1. current API machine values rendered by the Web UI are absent from the
   status/error mapping and leak as raw English/code in `zh-CN`;
2. the permanent tests do not fence source keys, all ICU/interpolation, or the
   required isolated browser behaviors; and
3. the approved AI Plan UI does not present the exact
   `execution_available=false` authority fact.

The repeated Docker registry timeout is an independent environmental blocker.
It leaves the real isolated runtime `NOT VERIFIED`; it neither causes nor
closes the source-confirmed Findings.

## Verification strategy outcome

All non-Docker focused gates requested for the Web slice pass. Contracts were
not run because the API/generated contract is unchanged. The canonical Docker
flow was used without build skipping, but both exact attempts stopped during
the frozen Web dependency layer before PostgreSQL/API/Web/Playwright startup.

The full aggregate is intentionally not run after focused Findings. Human
visual acceptance and preview are not eligible until remediation and a fresh
independent focused PASS.

## Rollback and cleanup

Remove only the three audit documents to roll back this audit checkpoint. Do
not revert or repair candidate production code. All exact audit Compose
resources, temporary fixtures, and task-owned image tags are removed;
pre-existing services remain untouched.

## Outcome

`VISUALENGINEER ZH-CN / EN-US LOCALIZATION FOCUSED REVIEW FAIL — REMEDIATION REQUIRED`

No sealing or main integration is authorized. The next eligible work is a
narrow machine-mapping, translation-contract, AI authority-copy, and isolated
E2E remediation followed by a fresh independent focused review from a new
candidate.
