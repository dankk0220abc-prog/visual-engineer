# Zhipu Live Trace/Audit Implementation Evidence

Classification: `mock_contract_not_live`

## Candidate identity and authority

- Repository: `/Users/danke/Developer/VisualEngineer`
- Authorized baseline: `main` at
  `deb5f166cca6904b1d9b0b6b6cd23aca51452241`, tree
  `d64cf3468f54e6115ea3219ba455a05635cee1ef`.
- Candidate branch: `codex/feat/zhipu-live-trace-audit-contract`.
- Core implementation commits: `748e277` and `9cff728`.
- Draft PR: <https://github.com/dankk0220abc-prog/visual-engineer/pull/17>.
- Migration: revision `20260809_0016`, revising `20260801_0015`; one Alembic
  head.
- Authority ends at implementation, tests, evidence, normal push, draft PR,
  and CI. Independent review, ready-for-review, merge, tag, release, deploy,
  and every live Provider call remain blocked.

No real Provider API key was entered, read, printed, persisted, or transmitted.
No Zhipu, Qwen, DeepSeek, Doubao, or Kimi live request was sent. The
Deterministic Fixture remains the only enabled/default Provider; all five real
Providers remain disabled with live validation `not_performed`.

## Independent review failure retained

The first independent review ended with:

`VISUALENGINEER LIVE TRACE/AUDIT INDEPENDENT REVIEW FAIL — REMEDIATION REQUIRED`

It found `MIGRATION-BACKFILL-001 — Blocking High`: the initial unpublished
`20260809_0016` migration converted legacy `cancelled` to
`cancelled_before_dispatch`, converted legacy `timeout` to `failed`, and used
the old Trace `created_at` as `dispatch_started_at`. Those conversions changed
unknown historical dispatch/cancellation facts into definite v1 facts. The
review also found four blocking Medium issues:

- `DB-CONTRACT-001`: a prepared-to-terminal UPDATE could inject impossible
  Provider response, identity, usage, or billing facts.
- `USAGE-001`: MockTransport usage was persisted as Provider-reported usage.
- `RECOVERY-001`: stale recovery used `created_at`, accepted an unsafe age, and
  had no production caller.
- `SECRET-DIAGNOSTIC-001`: a positive scanner match printed the full matching
  line, including secret material.

This failure is permanent evidence. The migration was not lossless from the
start. The first corrective implementation replaced the false backfill with
versioned legacy evidence semantics and attempted to close the four Medium
findings without enabling a Provider or sending a live request. A later narrow
review proved that `DB-CONTRACT-001` was not fully closed.

## Final narrow re-review failure retained

The final narrow re-review confirmed Historical v0 truthfulness, exact
downgrade/v1 refusal, the classification/usage/billing matrix, Mock usage,
recovery threshold/anchor/startup/concurrency, the secret scanner, and exact CI.
It nevertheless ended `FAIL` with one remaining Blocking Medium finding:

`DB-CONTRACT-001 remained open because PostgreSQL accepted live_cost_reported before dispatch.`

Specifically, PostgreSQL accepted a valid v1 live `prepared` row with
`billing_status=live_cost_reported` and valid amount/currency, and also accepted
the same billing facts while moving `prepared -> dispatching`. The reviewed
candidate was `4bc348854156e30e829698ed24d0ca4aa5adf7b0`; Fast
`31307148684` and Heavy `31307148821` were exact-SHA attempt 1 successes. Green
CI did not override the database exploit. This temporal billing contract was
therefore not complete from the start.

## Temporal billing remediation

The unpublished `20260809_0016` migration now installs the explicitly named
PostgreSQL CHECK `ck_ai_provider_invocations_v1_temporal_billing`. For v1,
`live_cost_reported` requires `classification=live`, `status=succeeded`, a
non-NULL `dispatch_started_at`, and paired non-NULL non-negative NUMERIC amount
plus an uppercase three-character currency. Every non-reported billing status
requires both cost fields to remain NULL. The same CHECK leaves v0 historical
rows intact, while the existing update trigger remains the second-layer guard
for pre-dispatch terminal transitions.

Real PostgreSQL direct-SQL tests now prove prepared INSERT rejection,
`prepared -> dispatching` same-UPDATE rejection, pre-dispatch failed/cancelled
rejection, post-dispatch failed/`outcome_unknown` rejection, succeeded billing-
unknown acceptance, succeeded reported-cost acceptance with `Decimal`, missing
amount/currency rejection, and non-reported amount/currency injection rejection.
All cases that reach a CHECK assert the exact constraint name. The earlier
false-positive case that assigned `billing_status` twice in one UPDATE no
longer exists; its replacement assigns reported billing exactly once and
asserts the existing PostgreSQL trigger rejection.

## Migration and schema evidence

Revision `20260809_0016` renames `ai_provider_traces` to
`ai_provider_invocations` and preserves the existing UUID identity. Historical
rows are now `contract_version=0`, `classification=fixture`, Provider
`deterministic-fixture`, and retain their exact legacy terminal status:
`succeeded`, `failed`, `timeout`, or `cancelled`. All v0
`dispatch_started_at`, queue, Provider-elapsed, and client-total fields are
NULL. No upstream request identity, effective model, dispatch boundary, live
billing, or live classification is invented.

The original floating-point latency, old token columns, synthetic cost basis,
retryability, timestamps, error fields, and digests remain in v0-only legacy
provenance columns where necessary for exact downgrade. V1 rows must keep every
legacy provenance column NULL. A legacy success may expose its contract-proven
synthetic usage; failed, timeout, and cancelled rows expose
`usage_status=unavailable` with NULL tokens even though the old NOT NULL schema
stored zeroes. The zeroes remain downgrade-only evidence, not a claim of actual
zero usage.

The v1 row is one dispatch attempt and is always created as
`contract_version=1`. Its immutable identity binds request,
attempt, contract version, classification, closed Provider ID, adapter version,
requested model, canonical outbound request digest, Provider metadata,
redactions, and creation time. After the temporal billing remediation,
PostgreSQL checks close lifecycle, reported-value, usage, billing, error,
digest, latency, and terminal combinations. The foreign key is `ON DELETE
RESTRICT`; recovery and reported-upstream partial indexes are present.

The downgrade permits only v0 historical rows. Any v1 row, including fixture,
live, mock, prepared, dispatching, `outcome_unknown`, new usage/billing facts,
upstream identity, or reported cost, causes PostgreSQL to fail with:

`downgrade would lose provider invocation audit semantics`

The four real old-schema statuses complete `upgrade -> downgrade -> upgrade`
with exact UUID, status, floating latency, token, cost, retryability, error,
digest, and timestamp restoration. V0 rows cannot be inserted after migration,
transitioned, updated, or deleted.

## Lifecycle and audit truthfulness

The implementation uses three durable boundaries:

1. insert `prepared` with immutable identity and commit before dispatch;
2. wait for the concurrency slot, measure monotonic queue time, commit
   `dispatching`, then permit transport send;
3. classify and commit the terminal result before creating Plan/Eval artifacts.

There is no automatic retry in this governed invocation path. Pre-dispatch
cancellation is `cancelled_before_dispatch` and sends no HTTP request.
Post-dispatch timeout, transport loss, cancellation, or internal ambiguity is
`outcome_unknown`; definite HTTP/provider/validation outcomes are `failed` or
`succeeded`. Stale reconciliation scans only v1 `dispatching` rows with a
non-NULL `dispatch_started_at`, anchors age to that dispatch boundary, writes
`outcome_unknown` with bounded code `provider_dispatch_stale_recovered`,
preserves the row, invents no elapsed value, and never dispatches or retries.

The minimum recovery age is 180 seconds: the maximum configured Provider total
deadline of 150 seconds plus an explicit 30-second safety margin. Smaller ages
raise instead of clamping. API startup performs one reconciliation pass before
serving; database failure follows existing fail-closed startup behavior, and no
background polling loop was added. Concurrent reconcilers use
`FOR UPDATE SKIP LOCKED`, so one row transitions once.

PostgreSQL insert/update/delete triggers require a v1 `prepared` insert,
enforce only legal transitions, reject same-UPDATE identity mutation, prevent
immutable identity/redaction mutation, and reject every update or delete after
a terminal state. A v1 pre-dispatch `failed` or
`cancelled_before_dispatch` row must have unavailable/NULL response identity,
effective model, upstream ID, usage, tokens, Provider latency, and cost, with
`billing_status=not_dispatched`; direct SQL injection is rejected for fixture,
mock, and live classifications.

## Digests, identity, usage, latency, and billing

- V1 `request_digest` hashes the actual canonical safe outbound JSON structure,
  including requested model, structured messages/request structure, output
  limit, structured-output controls, and non-secret options. No outbound body
  copy, API key, Authorization header, or secret header is stored. V0
  `request_digest_kind=legacy_generation_request` identifies the old stored
  `AIPlanGenerationRequest` digest; it is never described as an outbound body.
- V1 `response_digest` exists only after typed Plan validation and hashes the safe
  normalized envelope: Plan, reported/unavailable effective model,
  reported/unavailable upstream request identity, and normalized usage. Raw
  malformed/error bodies are neither hashed as a recoverable copy nor stored.
  V0 uses `legacy_provider_response` provenance for its original digest.
- Requested and effective model identity are separate. Upstream request identity
  uses explicit `reported`/`unavailable` pairing. Ordinary API responses omit
  the full upstream value and expose only a stable 24-hex SHA-256 prefix.
- Nullable token fields preserve complete, partial, invalid, and unavailable
  reporting without manufacturing zeroes. Fixture usage is
  `synthetic_complete`, never reported. Mock persistence permits only controlled
  `synthetic_complete` or `unavailable`; partial/invalid synthetic mock payloads
  are unavailable. Adapter-normalizer tests retain their separate reported
  usage parsing contract for future live responses.
- Queue, Provider, and client-total elapsed values are non-negative `BIGINT`
  milliseconds from a monotonic client clock; adapter-reported latency does not
  overwrite them.
- A database truth table rejects reported usage for fixture/mock, synthetic
  usage for live, and classification-incompatible billing states.
- Billing uses `NUMERIC(20,8)` plus uppercase three-character currency. Fixture
  and mock are explicitly non-billable. Live defaults to
  `live_billing_unknown`; no estimate or price table exists.

## MockTransport and governance evidence

Real Provider adapters are connected to the lifecycle only through an injected
`httpx.MockTransport` and a synthetic credential. The executor rejects both a
production client and an injected non-MockTransport before preparing an audit
row. Tests cover successful typed Plan creation, 401, 403, 429, 503, timeout,
transport loss, cancellation, malformed and oversized responses, usage/model/
upstream variants, stable fingerprinting, no retry, and no raw body or secret
persistence.

Failure, cancellation, and ambiguous outcomes create no Plan and issue no
Execution Grant, Review Decision, Delivery Authorization, Runner operation,
Git side effect, or Workspace mutation. Successful MockTransport validation
commits the terminal Invocation before its test-only Plan callback. These tests
do not enable a real Provider.

## Safe API and UI projection

Generated OpenAPI and TypeScript schemas expose classification, lifecycle,
Provider, requested/effective model semantics, upstream status and fingerprint,
nullable typed usage, integer latency, billing/cost when reported, and
timestamps. Closed digest provenance and dispatch-boundary status distinguish
v0 legacy evidence from v1 dispatch evidence. They do not expose the full
upstream request ID, Provider body, Authorization material, keys, or private
Prompt text.

The existing AI Plan console received only a minimal bilingual audit-panel
update. It renders `FIXTURE`/`MOCK`/`LIVE`, internal short correlation,
requested/effective identity, upstream status/fingerprint, non-null tokens,
three elapsed measures, billing, timestamp, and bounded error facts. Responsive
wrapping is explicit at narrow widths. V0 renders `Legacy Cancelled` or
`Legacy Timeout`, states that the dispatch boundary is unavailable, labels the
old latency as a legacy measurement, and never renders it as
`Cancelled Before Dispatch` or `Outcome Unknown`. The Provider registry page
was not redesigned.

## VE-MPF-R2-OBS-001 closure

`scripts/check-secrets.sh` now checks `command -v rg` before scanning. If the
dependency is absent it writes exactly `secret scanner dependency missing: rg`
to stderr, exits non-zero, and never prints the clean conclusion. The executable
regression script proves both the installed and missing-`rg` branches and is
part of `make security-check`. Heavy CI now installs the required scanner
dependency explicitly; scanner behavior remains fail closed if installation or
resolution fails. Positive matches now use `rg --files-with-matches` and emit
only a fixed finding plus path. A synthetic positive-match regression proves
stdout/stderr contain neither the credential, the matching line, nor a secret
prefix/suffix. An inaccessible scan root also fails safely instead of emitting
the clean conclusion.

## Verification record

| Boundary                            | Result                                                                                                                                          |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Temporal billing direct SQL         | `12 passed`: exact prepared/dispatching/terminal/value matrix; reachable CHECK failures assert `ck_ai_provider_invocations_v1_temporal_billing` |
| Related Invocation/billing service  | `23 passed`: existing constraint/lifecycle paths plus Fixture, Mock, Live reported cost, and Live MockTransport billing-unknown behavior        |
| Temporal v0 historical regression   | `1 passed`: four exact legacy statuses, PostgreSQL constraint introspection, downgrade, and re-upgrade                                          |
| Final focused migration/invocation  | `62 passed`: four-status v0 history, exact downgrade, v1 refusal, DB facts/truth table, mock usage, recovery threshold/concurrency/startup      |
| Associated governed API focused set | `24 passed`                                                                                                                                     |
| Canonical backend aggregate         | `478 passed`; total coverage `85.06%`; one run, no retry/rerun                                                                                  |
| Real PostgreSQL migration           | clean `base -> head -> base -> head`; v0 history and downgrade behavior unchanged                                                               |
| Web unit/component                  | 17 files, `108 passed`, including legacy timeout projection                                                                                     |
| Python quality                      | Ruff format/check passed; mypy passed for 139 source files                                                                                      |
| Web quality                         | Prettier, ESLint, and TypeScript passed                                                                                                         |
| Generated contracts                 | `make contracts-check` passed                                                                                                                   |
| Secret scanner                      | clean scan, missing-`rg`, inaccessible-root, and redacted positive synthetic match passed                                                       |
| Diff integrity                      | `git diff --check` passed before commits                                                                                                        |
| Local focused browser               | `NOT RERUN`: unchanged product logic does not justify local Playwright; remote Heavy remains the browser/Docker/Eval/Security authority         |

The first remote code-candidate CI on exact SHA
`9cff7280ceb0dfd32f2b4df99508f9f30ada4451` recorded:

- Fast `31289647121`, attempt 1: `SUCCESS`.
- Heavy `31289647064`, attempt 1: `FAILURE`. Docker/Compose/Migration passed;
  security stopped because the runner lacked `rg`, and Playwright found an
  ambiguous locator after the same Provider ID became visible in both the
  existing Provider summary and new audit panel. Both are narrowly remediated
  in the evidence/CI commit: explicit Heavy dependency installation and an
  exact count assertion. All E2E source/workspace invariance and cleanup checks
  in the failed run passed.

The later pre-remediation candidate HEAD
`81efd52323c7baa918f3c7e5885c3fc7164211e4` had Fast `31303183735` and Heavy
`31303183748` successful, but that green CI did not override the subsequent
independent-review failure above. In particular, it did not prove historical
backfill truthfulness, same-UPDATE terminal facts, mock usage provenance,
deadline-safe startup recovery, or positive-match secret redaction.

The historical-integrity candidate HEAD
`4bc348854156e30e829698ed24d0ca4aa5adf7b0` had Fast `31307148684` and Heavy
`31307148821` successful on attempt 1, but the subsequent final narrow re-review
found the temporal billing exploit recorded above. Those green runs are not
evidence for the corrected CHECK.

The CI result for the temporal billing remediation commit is necessarily
recorded on draft PR #17 and in the implementation handoff because CI starts
only after this document is committed. That exact-SHA Fast/Heavy result is the
remaining candidate evidence; this document does not pre-claim it.

## Explicit non-claims

- No live Provider behavior, availability, model identity, upstream request
  identity, usage, billing, latency, or cost has been validated.
- No screenshot is labeled or stored as live evidence.
- This implementation is not an independent review PASS, merge approval,
  publication readiness verdict, release, or deployment authorization.
