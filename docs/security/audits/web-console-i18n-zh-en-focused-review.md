# Web Console zh-CN / en-US Localization Independent Focused Review

- Review date: 2026-08-02 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Candidate: `5f3ef6cf3bf21a4521124007ef5aa363075c4327`
- Main baseline: `450b660f1ab9e82993cfe1780a1967e5d6bf72cd`
- Review branch: `codex/audit-web-console-i18n-zh-en-focused-20260802`
- Independence: no production code, message resource, dependency, or existing
  test was changed
- Status: **COMPLETE - FAIL - REMEDIATION REQUIRED**
- Real isolated Playwright: **NOT VERIFIED - REGISTRY BLOCKED BEFORE STARTUP**
- Remote CI: **NOT VERIFIED**

## Verdict

`VISUALENGINEER ZH-CN / EN-US LOCALIZATION FOCUSED REVIEW FAIL — REMEDIATION REQUIRED`

Three blocking Medium Findings are confirmed independently of the Docker
registry failure. The Web console leaks valid machine statuses and Delivery
error codes instead of localizing them, does not present the exact
`execution_available=false` AI authority fact, and lacks the permanent
translation-contract and isolated-browser assertions required by this slice.

The real isolated stack was attempted twice with the repository's canonical
script and candidate source. Both attempts stopped in the Web image's frozen
dependency install at 509/511 and 508/511 packages. PostgreSQL, API, Web, and
Playwright never started. Those external timeouts are `NOT VERIFIED`, not a
candidate product failure and not a pass.

Per the stop rule, the full `make verify` aggregate was not run, no preview was
left running, no sealing commit was created, and `main` was not moved.

## Finding VE-I18N-FR-001

- Severity: **blocking Medium**
- Trigger: render valid `WorkspaceState=sealed`,
  `ReleaseReadinessVerdict=not_ready`, or
  `ValidationSuiteStepState=skipped` in `zh-CN`; alternatively render a
  Delivery dispatch containing a stable `error_code`.
- Expected: UI labels are localized from stable code/status keys while the raw
  code remains available as diagnostic evidence.
- Actual: `StatusPill` returns the raw child when the value is absent from
  `localizedStatusKeys`; `sealed`, `not_ready`, and `skipped` are absent from
  both that list and `common.status`. Delivery history renders
  `dispatch.error_code` directly with no localized mapping or fallback label.
- Finding: the machine-to-UI localization map is not exhaustive for machine
  values that the current Web console renders. This violates the explicit
  global status/error mapping contract and is visible in core Workspace,
  Validation, Review/Release Readiness, and Delivery surfaces.
- Additional scope symptom: the Task detail Run row still contains the raw UI
  label `Committed HEAD` instead of a localized label.

The API and persisted values remain language-neutral, which is correct. The
defect is the incomplete UI projection of those stable values.

## Finding VE-I18N-FR-002

- Severity: **blocking Medium**
- Trigger: remove the same used key from both locale trees, introduce a typo in
  a translation call outside an exercised render path, or introduce invalid
  ICU/interpolation syntax in an unrendered message.
- Expected: a permanent focused test fails for missing/wrong source keys and
  invalid ICU/interpolation, and isolated Playwright covers the ten required
  bilingual runtime boundaries.
- Actual: the only resource-integrity test compares the two locale key sets.
  `next-intl` `AppConfig.Messages` is not augmented, so message calls are not
  statically key-safe. There is no permanent full-resource ICU/placeholder or
  source-reference test. The candidate i18n Playwright spec checks locale,
  headings, overflow, refresh, switching, and one English revision value, but
  does not assert entity URL/context preservation, AI authority copy,
  Delivery status/error mapping, immutable Evidence/path/digest values in
  both languages, or a non-root Cookie switch.
- Finding: current resources pass an independent one-time key/ICU diagnostic,
  but the required regression contract is absent and the existing isolated
  spec cannot detect the product gaps in `VE-I18N-FR-001` or the authority gap
  below.

The independent diagnostic found 740 equal message leaves, zero current ICU
parse errors, zero placeholder-set mismatches, and zero missing keys across
1,016 literal translation calls. Those current-data PASS results do not prove
future invalid changes are test-fenced.

## Finding VE-I18N-FR-003

- Severity: **blocking Medium**
- Trigger: inspect an approved governed AI Plan in either locale.
- Expected: the UI clearly presents that the switched setting is UI language,
  AI output language is out of scope, the approved Plan remains
  `execution_available=false`, and no downstream authority is automatically
  issued.
- Actual: the UI correctly distinguishes interface language from immutable AI
  output and says that separate downstream decisions remain required, but the
  `execution_available=false` field appears only in test fixture/API contract
  data and is never rendered or named in Web messages/components.
- Finding: the prose is directionally correct but omits one exact authority
  fact explicitly required for this slice. An operator cannot verify the
  machine flag from the localized Plan UI.

The distinct terms Plan Approval, Execution Grant, Review Approval, Delivery
Authorization, and Side-effect Permit otherwise remain differentiated in both
message trees.

## Confirmed architecture and focused results

- One formal `next-intl` App Router integration supplies request locale and
  messages to SSR and the client provider; no second production translation
  mechanism or production `locale === ...` branch was found.
- Routes remain non-prefixed. The locale switch POSTs a validated value and
  reloads the current URL. Cookie source inspection confirms `HttpOnly`,
  `SameSite=Lax`, path `/`, one-year max age, and conditional `Secure`.
- `zh-CN` and `en-US` contain the same 740 leaf keys. Current ICU syntax and
  placeholders parse in both locales, and no paragraph-style source-string
  keys were found.
- Web unit `78/78`, format, lint, TypeScript, production build, source
  invariance, and candidate/worktree `git diff --check` pass.
- Raw AI Plan, Prompt, Trace, Eval summaries, AuditEvent metadata, and Evidence
  content remain unmodified by locale presentation in inspected components.
- No API schema, migration, Provider runtime, Provider SDK, API key, remote
  Git, or persistent business contract changed in the candidate range.

These narrower PASS results do not override the Findings or the unverified
real isolated browser gate.

## Narrow remediation boundary

1. Make the machine-status/error mapping exhaustive for every currently
   rendered API enum and Delivery failure code; localize the label/fallback
   while retaining raw code and request ID where available.
2. Add both locale messages and negative regressions for at least `sealed`,
   `not_ready`, `skipped`, Delivery known/unknown errors, and other schema/UI
   set differences. Localize remaining UI labels such as `Committed HEAD`.
3. Add strict `next-intl` message typing or an equivalent source-reference
   gate, full ICU parse and placeholder parity tests, and missing/wrong-key
   negative tests.
4. Render the exact `execution_available=false` AI Plan fact in both locales
   while retaining the existing downstream-authority distinctions.
5. Extend the canonical isolated Playwright spec to cover all ten required
   bilingual boundaries, then rerun it from candidate-matching images after
   registry access is reliable.

No Provider, API key, dependency-version change, API contract change, locale
URL prefix, or authority expansion is required.

## Gate disposition

- Focused review: **FAIL**.
- Real isolated desktop/narrow bilingual E2E: **NOT VERIFIED - ENVIRONMENT
  BLOCKED BEFORE STARTUP**.
- Full `make verify`: **NOT RUN by focused-review stop rule**.
- Human visual acceptance: **NOT REQUESTED**.
- Preview: **NOT STARTED**.
- Sealing: **NOT PERFORMED**.
- Main movement, remote access, push, PR, tag, deploy, real Provider, and API
  key use: **NOT PERFORMED**.
