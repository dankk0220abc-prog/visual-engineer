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

The five explicit adapters use code-owned endpoint/model allowlists, bounded
connect/read/total deadlines, a streamed response byte cap, fixed maximum output,
one-call concurrency, cancellation checks, zero automatic retries, structured
normalization, optional provider request ID and usage, unconfigured cost, and
sanitized typed failures. MockTransport assertions cover request mapping and
normalization; they are not live validation.

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

| Boundary | Result |
| --- | --- |
| Provider/Planning/PostgreSQL focused | `44 passed`; registry/configuration, five adapters, redaction, timeout/cancel/concurrency/byte/retry/endpoint bounds, API discovery, and failure-state zero-side-effect coverage |
| Web component/i18n focused | `34 passed`; selector/status states, en-US/zh-CN, generated status/error registry completeness, and Run Console request binding |
| Python format/lint/type | Ruff format/check passed; mypy passed `135` source files |
| Web format/lint/type | Prettier, ESLint, and `tsc --noEmit` passed |
| Contract | `make contracts-check` passed after source-first OpenAPI and TypeScript generation |
| Focused real-stack browser | `4 passed`; desktop/390 px, en-US/zh-CN, axe WCAG A/AA, containment, Fixture default, five disabled real Providers, DOM-tamper API 422, and zero persisted AI Plan |
| Canonical aggregate | One `make test` run passed: Python `383 passed` at `84.66%`; Web `101 passed` at `73.10%` functions |
| Migration | `make migration-check` passed; no migration added |
| Secret scan | Existing high-confidence secret scan passed |
| UI craft detector | Impeccable detector returned `[]` |
| UI finish review | Fresh read-only Impeccable reviewer returned `disposition: ship`; no actionable blockers remained after semantics, mobile density, recovery, and hierarchy fixes |
| Evidence scan | Passed on five PNGs, five capture-time DOM scan records, manifest, and two Markdown records; `13` artifacts total |
| Whitespace | `git diff --check` passed |

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

## Screenshot evidence

The manifest is [`manifest.json`](./manifest.json). It binds five curated PNGs
to commit `9cc6c9022f74abf2da069a3192c90c1e35e71e02`, fixed routes and viewports,
locales, SHA-256 digests, timestamps, `fixture_mock_not_live` classification,
and passed capture/post-capture scan state.

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
