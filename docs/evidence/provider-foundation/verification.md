# Model-neutral Provider Foundation Verification

## Candidate identity and authority

- Authoritative repository: the VisualEngineer Developer checkout
- Baseline `main`: `aaa9dc6df6082bffe5f7a7038dc0166524db058a`
- Baseline tree: `41c0b78885a2db59761fd0eaeb79bff9250af8b1`
- Candidate branch: `codex/feat/model-neutral-multi-provider-foundation`
- Screenshotted application commit: `9cc6c9022f74abf2da069a3192c90c1e35e71e02`
- Authority: local implementation, mock HTTP contracts, synthetic real-stack
  browser evidence, commit/push/draft PR, and Fast/Heavy CI only. No real
  Provider call, merge, tag, release, deployment, License, or Dependabot work.

Preflight confirmed that local `main`, `origin/main`, and GitHub `main` matched
the requested baseline; the worktree, index, untracked set, stash, and Git
operation state were clean; PR #14/#15 and the requested historical CI state
matched; source branches were deleted and backup refs remained.

The security-remediation preflight on 2026-08-08 separately confirmed candidate
HEAD `f59a0425cb3eb7a91b002991b2cd5dc5917d1514`, tree
`f661d3cfd5641135186aadbf86e9b600d8d34a2f`, a clean worktree/index/untracked
set and stash, no active Git operation, the two existing backup refs, and
candidate parity with `origin`. Candidate was `0` behind and `4` ahead of the
unchanged requested `main`. PR #16 was OPEN, DRAFT, MERGEABLE/CLEAN against
`main`; its then-current Fast and Heavy checks were successful.

The round-2 security-remediation preflight on 2026-08-08 confirmed candidate
HEAD `881b1901be387c2c74b0a575bd49dc2b87bba669`, tree
`057d867591cc624be4f4b834dee48e195b7d1430`, a clean worktree/index/untracked
set and stash, no active Git operation, the same two backup refs, and exact
local/origin/GitHub parity. Candidate was `0` behind and `5` ahead of unchanged
`main`. PR #16 was OPEN, DRAFT, MERGEABLE/CLEAN with no reviews, review threads,
requested changes, or review requests. Fast `31259595598` and Heavy
`31259595588` were attempt-1 successes on that exact pre-remediation candidate.

## Preserved independent security review failures

The first independent final security review concluded `FAIL — REMEDIATION
REQUIRED` with three Blocking Medium findings:

- `VE-MPF-FSR-001`: the claimed total deadline and cancellation boundary did
  not cover response-body reads or normalization.
- `VE-MPF-FSR-002`: the production HTTPX client inherited ambient proxy and TLS
  environment configuration.
- `VE-MPF-FSR-003`: a Playwright negative matcher could serialize a checked
  Secret and received DOM on failure.

The earlier statement that the adapters already had bounded total deadlines and
cancellation checks was not true for response-body reading and normalization.
That original claim and the first review failure are preserved here rather than
being removed or softened.

The second independent final re-review also concluded `FAIL — REMEDIATION
REQUIRED` with three separate Blocking Medium findings:

- `VE-MPF-FSR-001`: outer `Task.cancel()` could arrive after semaphore acquire
  consumed the permit but before the invocation recorded ownership, leaking the
  only permit permanently.
- `VE-MPF-FSR-002`: `ssl.create_default_context()` inherited ambient
  `SSLKEYLOGFILE`, allowing the process environment to enable Provider TLS key
  logging despite the fixed CA/proxy boundary.
- `VE-MPF-FSR-003`: Playwright retries and automatic trace, screenshot, video,
  and error-context artifacts could retain a Secret already present in the DOM
  even though the helper threw only a fixed error code.

These are preserved as the second independent FAIL history. This record does
not claim that either review's contracts had always been satisfied.

## Implemented boundary

The registry is closed and ordered: Deterministic Fixture, Zhipu GLM, Qwen,
DeepSeek, Doubao, and Kimi. Fixture is configured, enabled, and the default.
All five real Providers are disabled. With no local secret they report
`missing_local_api_key`; secret presence alone changes only the safe status to
`live_validation_not_performed` and does not enable a Provider.

Secrets are centralized as server-only `SecretStr` settings. The discovery API
returns only safe booleans, Provider/model identity, fixed documentation links,
explicit capability states, and disable reasons. It does not return key names,
values, prefixes/suffixes, paths, headers, or authentication material. No secret
is accepted from the browser, persisted, logged, traced, or included in
Evidence.

The five explicit adapters create one monotonic absolute deadline at the
outer invocation boundary. The same deadline covers queueing for the one-call
semaphore, request/response headers, each blocking response chunk, the byte cap,
JSON parsing, normalization, and the final result checkpoint. Cancellation and
deadline expiry cancel the pending await, actively close an obtained response,
release the slot in `finally`, do not retry, and discard any body or normalized
result. Semaphore acquisition now uses a tracked permit lease: the acquisition
task records ownership immediately after `Semaphore.acquire()` and before it
can complete, with no intervening await. Outer cancellation therefore observes
either a pending non-owner or an owned lease; the invocation's synchronous,
idempotent finalizer releases an owned permit exactly once. Cancellation cleanup
is shielded and fully awaited even when the outer task is cancelled again, so no
controlled-await task is left pending and capacity cannot become zero or two.

The output-token contract has a public hard maximum of `4096`: `4096` is
accepted, `4097` is rejected by policy validation, and Provider-specific request
overrides cannot replace the protected output field. The production client has
no configurable transport input and fixes `trust_env=False`,
`follow_redirects=False`, and a direct `SSLContext(PROTOCOL_TLS_CLIENT)` with
hostname checking and certificate verification required. It loads only the
locked `certifi` bundle. `SSLKEYLOGFILE`, proxy, and ambient CA variables do not
alter the context; `keylog_filename` remains `None` without changing the host
environment.

Provider Evidence is excluded from both ordinary Playwright projects and runs
only in two dedicated projects with `retries=0`, `trace=off`,
`screenshot=off`, and `video=off`. A fixed-code reporter converts a caught
Provider Evidence failure to a non-sensitive failed run without allowing the
original error or DOM into Playwright's automatic failure pipeline. The
synthetic-leak negative proof uses real Chromium, puts a fixed synthetic Secret
and private marker in the DOM, calls the production helper, and requires child
exit 1 while checking one attempt, zero attachments, empty per-test stdout and
stderr, and an absent-or-empty output directory.

MockTransport assertions cover request mapping, normalization, deterministic
semaphore/header/chunk cancellation, the completed-acquire ownership-transfer
race, outer cancellation before acquire and during request/body reads, competing
deadline/token cancellation, repeated cancellation during cleanup,
exactly-once release, subsequent request reuse, no pending tasks, output-token
bounds, redirect denial, and fixed network trust. They are not live validation.

Provider selection still creates only a governed Plan proposal. Unknown,
unconfigured, and configured-but-unvalidated Provider requests fail before
creating an AI Plan artifact. Tests assert zero Execution Grants, Review
Decisions, and Delivery Authorizations. No adapter exposes tools, Runner, shell,
Workspace mutation, custom base URL, custom headers, or automatic fallback.

## Migration decision

No migration was created. The existing `AIPlanRequest.provider_id` carries the
stable registry ID and existing JSON metadata can retain fixture invocation
metadata. Real invocation/persistence remains disabled. The later live-validation
package must separately decide how real request IDs, usage, and cost semantics
become durable before enabling a real Provider.

`make migration-check` passed the existing single-head upgrade/downgrade/upgrade
matrix through `20260801_0015` with no new revision.

## Verification matrix

| Boundary                             | Result                                                                                                                                                                             |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Provider transport focused           | Round 2: `42 passed`; includes deterministic completed-acquire/outer-cancel barriers, request/body cancellation, repeated-cancel cleanup, exact capacity, and TLS keylog isolation |
| Provider/Planning/PostgreSQL focused | Round 2: `65 passed`; includes the transport set plus governed Planning and PostgreSQL-backed boundary tests                                                                       |
| Web remediation focused              | Round 2: safety helper/policy `6 passed`; current complete Web unit run `107 passed`                                                                                               |
| Python format/lint/type              | Ruff format/check passed; mypy passed `135` source files                                                                                                                           |
| Web format/lint/type                 | Prettier, ESLint, and `tsc --noEmit` passed                                                                                                                                        |
| Contract                             | `make contracts-check` passed after source-first OpenAPI and TypeScript generation                                                                                                 |
| Historical focused browser           | Before this remediation, `4 passed` on the screenshotted application commit                                                                                                        |
| Round-2 synthetic browser negative   | `1 passed`; real Chromium child exited 1 as expected with fixed code, retry 0, zero attachments/output, and no trace/screenshot/video/error-context/retry artifact                 |
| Round-2 Provider real-stack browser  | `NOT VERIFIED`; no-build run safely failed four product cases through the fixed reporter while the synthetic negative passed; no local image rebuild or retry was performed        |
| Historical canonical aggregate       | One original `make test` run passed: Python `383 passed` at `84.66%`; Web `101 passed` at `73.10%` functions                                                                       |
| Remediation canonical aggregate      | `NOT RUN`; correctly gated because current-code focused browser validation could not complete                                                                                      |
| Migration                            | `make migration-check` passed; no migration added                                                                                                                                  |
| Secret scan                          | Existing high-confidence secret scan passed                                                                                                                                        |
| UI craft detector                    | Impeccable detector returned `[]`                                                                                                                                                  |
| UI finish review                     | Fresh read-only Impeccable reviewer returned `disposition: ship`; no actionable blockers remained after semantics, mobile density, recovery, and hierarchy fixes                   |
| Evidence scan                        | Passed on five unchanged PNGs, five minimal capture records, manifest, and two Markdown records; `13` artifacts, five records, and zero Provider environment values checked        |
| Whitespace                           | `git diff --check` passed                                                                                                                                                          |

The first isolated adapter subset executed 15 successful assertions but exited 1
because the repository-wide coverage gate saw only the selected file
(`37% < 80%`). It was not reported as a passing command. The complete focused
boundary above later passed with coverage intentionally delegated to the one
canonical aggregate.

The first Provider Playwright run passed 1/4 and failed three new test locators:
one ambiguous text locator, one additional Next route-announcer alert, and a
locale-switch race while Snapshot generation was still in progress. Locators
and the readiness barrier were corrected without Playwright retries, sleeps,
serialization, or timeout changes; the focused matrix then passed 4/4.

A later complete local image rebuild stopped before browser execution because
the Debian security mirror returned `502 Bad Gateway` during the unchanged API
image `apt-get update`. The current Web production image had already built
successfully. This external build attempt remains failed/NOT VERIFIED and was
not retried. The final browser capture used the repository's no-build path with
the previously successful exact API/Runner images and current Web image; its
4/4 product result is reported separately from the failed rebuild.

For this remediation, the first no-build Provider-only Playwright invocation
used the locally available stale Web image: `/providers` returned the old 404
page and the Run Console had no Provider selector, so all four cases failed.
Source/workspace invariance and zero-residual-resource cleanup passed. This was
not retried as a product test. The corrective two-image API/Web build then
stopped before application layers when the pinned Node and Python base-image
metadata requests returned `DeadlineExceeded`; the Runner image was not rebuilt.
No timeout, retry, registry, dependency, or test setting was changed. Therefore
current-code browser validation is `NOT VERIFIED`, and the remediation
`make test` aggregate was not run because the required focused matrix had not
fully passed.

For round 2, deterministic backend tests used `asyncio.Event`, explicit
barriers, and controlled tasks only; no sleep, probability loop, flaky retry,
or timeout increase was used. The focused Provider file passed `42` tests, and
the Provider plus governed Planning set passed `65`. Ruff format/check, mypy
over `135` source files, Prettier, ESLint, TypeScript, the six-test Web safety
subset, and the current complete `107`-test Web unit run passed.

The round-2 real Chromium synthetic-leak harness passed independently and again
inside the real-stack invocation. Its child had the required non-zero exit and
fixed error code; JSON reporter output proved one result at retry zero with no
attachments or captured stdout/stderr, and the dedicated output directory was
empty before task-owned cleanup. The accompanying no-build real-stack run
passed that harness but safely failed the four product cases through only
`VE_PROVIDER_EVIDENCE_SAFE_FAILURE`. Source/workspace invariance and zero
residual containers, networks, volumes, and fixture directories all passed. No
raw failure or DOM was exposed. Because this work package explicitly avoided a
redundant three-image local rebuild and the existing local image mismatch was
already documented, those four current-code product cases remain `NOT
VERIFIED`; no retry or timeout change was used. Fresh Fast/Heavy CI on the
published round-2 HEAD is the canonical build/browser gate.

Draft PR #16 preserved its initial CI result. Fast run `30988834061` failed
only because this verification record had not yet been normalized by Prettier;
its Python, Runner, contract, and repository-policy jobs passed. Heavy run
`30988833959` passed security/evals, a fresh three-image Docker build,
migration, Playwright, and Workspace Chaos on the same application candidate.
The evidence record was then formatted without changing product behavior; the
failed Fast run was not rerun.

## Screenshot evidence

The manifest is [`manifest.json`](./manifest.json). It binds five curated PNGs
to commit `9cc6c9022f74abf2da069a3192c90c1e35e71e02`, fixed routes and viewports,
locales, SHA-256 digests, timestamps, `fixture_mock_not_live` classification,
and passed capture/post-capture scan state.

The screenshots were not regenerated for this non-UI remediation. Their five
SHA-256 values remain identical to the manifest and remain bound to the recorded
application commit. Capture records now retain only rule ID, checked-value
count, pass/fail result, and a fixed error category. They retain no DOM, Secret,
hash, length, prefix, or suffix. The E2E path does not read Provider key
environment values, so `provider_environment_values_checked=0`; this proves the
synthetic/static rules only and is not a claim that real keys were scanned.

The set contains desktop English and 390 px Chinese registry views, desktop
Chinese and 390 px English selector views with Fixture visibly selected, and a
Chinese safe unconfigured-Provider error. Every screenshot says Fixture/Mock
Evidence and not a live-provider call. Synthetic test resources were removed,
and the E2E project ended with zero containers, networks, volumes, or fixture
directories.

## Live-validation status

Live validation was not performed for Zhipu, Qwen, DeepSeek, Doubao, or Kimi.
No key was requested or consumed. Adapter model availability, account access,
quality, price, quota, and upstream compatibility remain NOT VERIFIED. Fixture
remains the only enabled/default Provider, and no automatic Provider fallback
exists.

Upstream request ID persistence, real usage/cost/latency semantics,
`AIProviderTrace` billing status, any Migration, and a real Zhipu call remain
`DEFERRED TO ZHIPU LIVE VALIDATION CONTRACT DECISION`. Before any live
validation, a separate `ZHIPU LIVE TRACE AND AUDIT CONTRACT DECISION` work
package must decide the immutable trace contract. This remediation did not read
or call any real Provider key and made no real Provider network request.

`ZHIPU LIVE VALIDATION REMAINS BLOCKED PENDING TRACE/AUDIT CONTRACT DECISION`.
