# Web Console Localization Focused Remediation

- Date: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/web-console-i18n-focused-remediation`
- Remediation baseline: `1ed1ecb0bbccd5171c1182e86f9359ba29dc0386`
- Production candidate: `5f3ef6cf3bf21a4521124007ef5aa363075c4327`
- Main baseline: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Status: **COMPLETE - READY FOR INDEPENDENT FOCUSED RE-REVIEW**

## Goal

Close the three focused localization Findings without changing the single
`next-intl` architecture, locale routing, API/persistence values, immutable
AI/Evidence content, or any authority semantics.

## Scope

- Complete centralized typed mappings for Web-rendered status, error, action,
  and mandatory Eval identifiers, including Delivery lifecycle failures.
- Preserve stable API values as diagnostic evidence while presenting a clear
  localized label and a localized unknown-code fallback.
- Add permanent static call-key, dynamic registry, full-resource ICU,
  placeholder, fallback, and exact AI authority UI regressions.
- Render the real `execution_available=false` Plan contract in both locales,
  including after approval, and retain the separation between Plan Approval,
  Execution Grant, Review Approval, Delivery Authorization, and Side-effect
  Permit.
- Use Impeccable only to check directly changed UI surfaces and correct only
  blocking or obvious layout issues.

## Boundaries

No API enum, database state, AuditEvent, migration, generated contract,
Provider, Prompt, Trace, Eval, Evidence, authority state machine, dependency,
locale route, remote Git, deployment, or `main` change is in scope. Full
`make verify`, unrelated Python/Runner/Delivery suites, Workspace Chaos,
migration roundtrip, isolated real-stack Playwright, Provider/API key use, and
sealing are explicitly excluded.

## Outcome

- Findings `VE-I18N-FR-001` through `VE-I18N-FR-003` have implementer-side
  remediations and permanent regressions.
- Focused Web tests, the complete Web unit suite, format, lint, TypeScript,
  production build, source invariance, exact bilingual desktop/narrow smoke,
  and whitespace checks pass.
- Canonical Docker E2E was not rerun because no current-candidate matching
  image was locally available without a rebuild, and the prior independent
  build was registry-blocked. That real API/PostgreSQL gate remains for the
  next independent review.

`VISUALENGINEER LOCALIZATION REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-REVIEW`

## Rollback

Revert only the eventual local remediation checkpoint. Do not reset, clean,
rewrite `main`, or remove unrelated runtime state.
