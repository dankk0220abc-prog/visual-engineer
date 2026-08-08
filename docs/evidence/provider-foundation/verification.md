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

## Preserved independent security review failure

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

The five explicit adapters now create one monotonic absolute deadline at the
outer invocation boundary. The same deadline covers queueing for the one-call
semaphore, request/response headers, each blocking response chunk, the byte cap,
JSON parsing, normalization, and the final result checkpoint. Cancellation and
deadline expiry cancel the pending await, actively close an obtained response,
release the slot in `finally`, do not retry, and discard any body or normalized
result. JSON/Pydantic normalization is bounded to at most 1 MiB of in-memory
bytes and performs hard checks immediately before and after its synchronous CPU
work.

The output-token contract has a public hard maximum of `4096`: `4096` is
accepted, `4097` is rejected by policy validation, and Provider-specific request
overrides cannot replace the protected output field. The production client has
no configurable transport input and fixes `trust_env=False`,
`follow_redirects=False`, and an `SSLContext` created from the locked `certifi`
bundle with hostname checking and certificate verification required.

MockTransport assertions cover request mapping, normalization, deterministic
semaphore/header/chunk cancellation, absolute-deadline expiry, response closure,
slot reuse, output-token bounds, redirect denial, and fixed network trust. They
are not live validation.

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

| Boundary                             | Result                                                                                                                                                                      |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Provider transport focused           | `34 passed`; async queue/header/chunk cancellation, absolute deadline, close/release/reuse, byte/token limits, TLS/proxy policy, request mapping, and normalization         |
| Provider/Planning/PostgreSQL focused | `57 passed`; includes the transport set plus registry/configuration and zero Plan/Grant/Review/Delivery side effects                                                        |
| Web remediation focused              | `23 passed` across the Secret-safe helper, Provider components, and Run Console; helper-only subset was `5 passed`                                                          |
| Python format/lint/type              | Ruff format/check passed; mypy passed `135` source files                                                                                                                    |
| Web format/lint/type                 | Prettier, ESLint, and `tsc --noEmit` passed                                                                                                                                 |
| Contract                             | `make contracts-check` passed after source-first OpenAPI and TypeScript generation                                                                                          |
| Historical focused browser           | Before this remediation, `4 passed` on the screenshotted application commit                                                                                                 |
| Remediation focused browser          | `NOT VERIFIED`; no-build used a stale image, then the required API/Web image build was blocked on base-image registry metadata                                              |
| Historical canonical aggregate       | One original `make test` run passed: Python `383 passed` at `84.66%`; Web `101 passed` at `73.10%` functions                                                                |
| Remediation canonical aggregate      | `NOT RUN`; correctly gated because current-code focused browser validation could not complete                                                                               |
| Migration                            | `make migration-check` passed; no migration added                                                                                                                           |
| Secret scan                          | Existing high-confidence secret scan passed                                                                                                                                 |
| UI craft detector                    | Impeccable detector returned `[]`                                                                                                                                           |
| UI finish review                     | Fresh read-only Impeccable reviewer returned `disposition: ship`; no actionable blockers remained after semantics, mobile density, recovery, and hierarchy fixes            |
| Evidence scan                        | Passed on five unchanged PNGs, five minimal capture records, manifest, and two Markdown records; `13` artifacts, five records, and zero Provider environment values checked |
| Whitespace                           | `git diff --check` passed                                                                                                                                                   |

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
