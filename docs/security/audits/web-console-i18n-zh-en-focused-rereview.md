# Web Console zh-CN / en-US Localization Focused Re-review

- Review date: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Candidate: `23dd0d5c89ccf11631e6da8da156a284949c6c30`
- Main baseline: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Review branch: `codex/audit-i18n-zh-en-final-rereview-20260802`
- Independence: the reviewer did not change production code, locale resources,
  dependencies, or existing tests
- Status: **COMPLETE - FAIL - REMEDIATION REQUIRED**
- Canonical isolated Playwright: **NOT VERIFIED - EXTERNAL REGISTRY BLOCKED**
- Remote CI: **NOT VERIFIED**

## Verdict

`VISUALENGINEER ZH-CN / EN-US LOCALIZATION FOCUSED RE-REVIEW FAIL — REMEDIATION REQUIRED`

The permanent message contract and exact AI authority presentation pass their
focused automated and controlled-negative checks. Static review also confirms
that the candidate does not translate or change the API, database, AuditEvent,
or persisted machine-value contracts.

The focused gate nevertheless fails for one independently reproduced blocking
UI issue: at a real 390 px viewport, the approved AI Plan Run page becomes 450
px wide in both locales. The Input context manifest and its long digest/context
values extend beyond the viewport and introduce page-level horizontal
scrolling. This is inside the explicitly requested Impeccable narrow-screen
scope and blocks human visual acceptance.

Canonical Compose/Playwright was also attempted with candidate-matching images.
Both the initial command and the one allowed clean retry stopped in the frozen
Web dependency installation before PostgreSQL, API, Web, fixture seeding, or
Playwright started. That result is an environmental `NOT VERIFIED`, not a
product failure and not a pass.

Per the stop rule, full `make verify`, sealing, human visual acceptance, main
movement, Provider/API key configuration, and every remote action were not
performed.

## Finding `VE-I18N-RR-UI-001`

- Severity: **blocking P1 / Major**
- Trigger: open the approved governed AI Plan Run
  `/runs/ca463d44-2a32-491e-aa18-4ff4b65a4bb6` at a 390 x 844 viewport in
  `zh-CN` or `en-US`.
- Expected: the full page remains within the 390 px viewport; long digest,
  context, UUID, SHA, and code values remain verbatim but wrap or scroll only
  inside their bounded evidence surface.
- Actual: `document.documentElement.clientWidth` is 390 while
  `document.documentElement.scrollWidth` is 450. The Input context manifest
  section, heading, digest paragraph, list, list items, and summary spans extend
  to approximately x=450.
- Impact: narrow-screen operators must horizontally pan the complete Run page;
  content is visually clipped at the right edge and the page no longer meets
  the required no-overflow responsive boundary.
- Location: `apps/web/src/components/ai-plan-console.tsx`, especially the
  context/evaluation grid and Input context manifest at lines 302-336.
- Recommendation: constrain the grid child with a zero minimum inline size and
  apply bounded wrapping to long digest/evidence values, then add a permanent
  390 px approved-Run assertion that page `scrollWidth` never exceeds viewport
  width in either locale.

`git blame` shows the basic context-manifest layout predates the remediation
commit, so this review does not attribute introduction of the defect to
`23dd0d5`. It is still a confirmed real product issue in the candidate and the
brief explicitly makes blocking Impeccable findings gate the result.

## Three Finding dispositions

| Finding                   | Disposition                                   | Evidence                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Status/error localization | **AUTOMATED PASS; CANONICAL UI NOT VERIFIED** | Status registry includes `sealed`, `not_ready`, `skipped`, and `superseded`; Delivery authorization/baseline/readiness/confirmation/dispatch/retry/stale Review/result-binding codes have bilingual resources; known and unknown fallbacks retain raw code/request ID; API/database/AuditEvent source is unchanged. Real isolated lifecycle rendering did not start because of registry timeout. |
| Permanent test validity   | **PASS**                                      | Current focused selection passed 47/47. Isolated controlled mutations independently forced exit 1 for a key missing from both locales, a nonexistent source key, a wrong namespace, missing status/error/Eval registry entries, invalid ICU in an unused leaf, and mismatched interpolation variables.                                                                                           |
| AI authority prompt       | **PASS**                                      | Both locale component tests and the real localhost approved Run display the actual `execution_available=false` contract and explicitly deny automatic Execution Grant, Review Approval, Delivery Authorization, and Side-effect Permit issuance. The backend authority model is unchanged.                                                                                                       |

## Impeccable focused audit

### Implementation integrity verdict

**PASS for product-specific implementation integrity; FAIL for responsive
release readiness.** The one required detector run returned `[]`. The rendered
authority language is specific, contractual, and tied to actual values rather
than decorative copy. The confirmed 390 px page overflow is a separate
responsive blocker.

| Dimension                |     Score | Key evidence                                                                                                                                                  |
| ------------------------ | --------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Accessibility            |       3/4 | Semantic landmarks and native locale select are present; keyboard focus ring was visible; no browser console warning/error was recorded in the sampled pages. |
| Performance              |       3/4 | No blocking rendering or interaction defect was observed in the bounded pass; no full performance profile was in scope.                                       |
| Responsive design        |       1/4 | Approved Run is 450 px wide at a 390 px viewport in both locales.                                                                                             |
| Theming                  |       3/4 | Changed surfaces use the incumbent tokenized Tailwind palette; no blocking contrast defect was observed.                                                      |
| Implementation integrity |       4/4 | Detector returned `[]`; authority and technical evidence remain product-specific and truthful.                                                                |
| **Focused total**        | **14/20** | **Good overall craft, but one P1 responsive blocker fails this gate.**                                                                                        |

Positive findings to preserve:

- `execution_available=false` and all downstream non-authority statements fit
  within the 390 px callout without overflow.
- Locale switching on the non-root Run URL preserves the exact URL and entity,
  survives refresh, updates `<html lang>`, and retains UUID/SHA/digest/code
  values verbatim.
- The Chinese and English Delivery empty states fit at 390 px, navigation wraps
  without overlap, the locale control has a visible focus ring, and no sampled
  browser console warning/error occurred.

## Gate disposition

- Focused re-review: **FAIL - REMEDIATION REQUIRED**.
- Canonical isolated bilingual E2E: **NOT VERIFIED - EXTERNAL REGISTRY
  TIMEOUT BEFORE STARTUP**.
- Impeccable blocking review: **FAIL - ONE P1 RESPONSIVE FINDING**.
- Full `make verify`: **NOT RUN**.
- Preview: **STARTED TEMPORARILY FOR AUDIT, THEN SAFELY STOPPED**.
- Human visual acceptance: **NOT REQUESTED**.
- Sealing and main movement: **NOT PERFORMED**.
- Push, PR, tag, deploy, real Provider, and API key: **NOT PERFORMED**.
