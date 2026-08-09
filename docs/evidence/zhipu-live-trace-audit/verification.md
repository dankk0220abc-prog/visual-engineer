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

## Migration and schema evidence

Revision `20260809_0016` renames `ai_provider_traces` to
`ai_provider_invocations` and preserves the existing UUID identity. Historical
rows are honestly backfilled as `classification=fixture`,
`usage_status=synthetic_complete`, and
`billing_status=not_billable_fixture`, with no upstream request identity, live
model identity, live billing, or live classification invented.

The new row is one dispatch attempt. Its immutable identity binds request,
attempt, contract version, classification, closed Provider ID, adapter version,
requested model, canonical outbound request digest, Provider metadata,
redactions, and creation time. PostgreSQL checks close lifecycle, reported-value,
usage, billing, error, digest, latency, and terminal combinations. The foreign
key is `ON DELETE RESTRICT`; recovery and reported-upstream partial indexes are
present.

The downgrade first inspects every row. Live, mock, prepared, dispatching,
`outcome_unknown`, new usage/billing facts, upstream identity, reported cost,
or any other state that cannot be faithfully represented by the old Fixture
Trace causes PostgreSQL to fail with:

`downgrade would lose provider invocation audit semantics`

Compatible historical Fixture data completes `upgrade -> downgrade -> upgrade`
without losing the old Trace evidence semantics.

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
`succeeded`. Stale `dispatching` reconciliation writes `outcome_unknown` with a
bounded recovery code, preserves the row, invents no elapsed value, and never
re-dispatches.

PostgreSQL insert/update/delete triggers require a `prepared` insert, enforce
only legal transitions, reject forged dispatch fields on a direct pre-dispatch
terminal transition, prevent immutable identity/redaction mutation, and reject
every update or delete after a terminal state.

## Digests, identity, usage, latency, and billing

- `request_digest` hashes the actual canonical safe outbound JSON structure,
  including requested model, structured messages/request structure, output
  limit, structured-output controls, and non-secret options. No outbound body
  copy, API key, Authorization header, or secret header is stored.
- `response_digest` exists only after typed Plan validation and hashes the safe
  normalized envelope: Plan, reported/unavailable effective model,
  reported/unavailable upstream request identity, and normalized usage. Raw
  malformed/error bodies are neither hashed as a recoverable copy nor stored.
- Requested and effective model identity are separate. Upstream request identity
  uses explicit `reported`/`unavailable` pairing. Ordinary API responses omit
  the full upstream value and expose only a stable 24-hex SHA-256 prefix.
- Nullable token fields preserve complete, partial, invalid, and unavailable
  reporting without manufacturing zeroes. Fixture usage is
  `synthetic_complete`, never reported.
- Queue, Provider, and client-total elapsed values are non-negative `BIGINT`
  milliseconds from a monotonic client clock; adapter-reported latency does not
  overwrite them.
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
timestamps. They do not expose the full upstream request ID, Provider body,
Authorization material, keys, or private Prompt text.

The existing AI Plan console received only a minimal bilingual audit-panel
update. It renders `FIXTURE`/`MOCK`/`LIVE`, internal short correlation,
requested/effective identity, upstream status/fingerprint, non-null tokens,
three elapsed measures, billing, timestamp, and bounded error facts. Responsive
wrapping is explicit at narrow widths; the Provider registry page was not
redesigned.

## VE-MPF-R2-OBS-001 closure

`scripts/check-secrets.sh` now checks `command -v rg` before scanning. If the
dependency is absent it writes exactly `secret scanner dependency missing: rg`
to stderr, exits non-zero, and never prints the clean conclusion. The executable
regression script proves both the installed and missing-`rg` branches and is
part of `make security-check`. Heavy CI now installs the required scanner
dependency explicitly; scanner behavior remains fail closed if installation or
resolution fails.

## Verification record

| Boundary                                         | Result                                                                                                                                                     |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Focused migration/invocation/provider regression | `107 passed`; later contract-hardening subset `67 passed`; explicit 401/403/429/503 matrix `8 passed`                                                      |
| Canonical backend aggregate                      | `445 passed`; total coverage `84.94%`                                                                                                                      |
| Real PostgreSQL migration                        | clean `base -> head -> base -> head`; backfill and lossy-downgrade rejection passed                                                                        |
| Web unit/component                               | 17 files, `107 passed`                                                                                                                                     |
| Python quality                                   | Ruff format/check passed; mypy passed for 139 source files                                                                                                 |
| Web quality                                      | Prettier, ESLint, and TypeScript passed                                                                                                                    |
| Generated contracts                              | `make contracts-check` passed                                                                                                                              |
| Secret scanner                                   | clean scan passed; missing-`rg` fail-closed regression passed                                                                                              |
| Diff integrity                                   | `git diff --check` passed before each commit                                                                                                               |
| Local focused browser                            | `NOT VERIFIED`: Debian returned HTTP 502 for `libldap` while building Runner before service startup; task resources and Compose objects were fully cleaned |

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

The CI result for the final evidence/CI-remediation commit is necessarily
recorded on draft PR #17 and in the implementation handoff because CI starts
only after this document is committed. That final check set is the publication
candidate evidence; this document does not pre-claim its result.

## Explicit non-claims

- No live Provider behavior, availability, model identity, upstream request
  identity, usage, billing, latency, or cost has been validated.
- No screenshot is labeled or stored as live evidence.
- This implementation is not an independent review PASS, merge approval,
  publication readiness verdict, release, or deployment authorization.
