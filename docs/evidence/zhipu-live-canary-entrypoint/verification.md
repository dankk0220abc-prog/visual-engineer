# Zhipu Live-Canary Entrypoint Verification

Classification: `pre_live_entrypoint_not_live`

Status: MOCK CONTRACT GREEN — INDEPENDENT SECURITY REVIEW REQUIRED

## Candidate identity

- Base `main`: `569fc39ad7d2b0e36432d14c50af93ee950b0a78`.
- Base tree: `ec0ce4c3478ff8b253b0a0b855981f19c950fbc2`.
- Branch: `codex/feat/zhipu-live-canary-entrypoint`.
- Implementation commit: `07adc9b35fcf5c5ba0b0d9e6211475bfb15d37bf`.
- Alembic head: `20260809_0016`; no migration added.
- Base canonical CI: Fast `31311718732`, Heavy `31311718708`, both successful
  on the exact base SHA.

## Official Zhipu dispatch contract

The repository's reviewed adapter contract expects:

- endpoint: `https://open.bigmodel.cn/api/paas/v4/chat/completions`;
- model: `glm-5.2`;
- authentication: `Authorization: Bearer <local ZHIPU_API_KEY>`;
- streaming: disabled;
- structured output: `response_format={"type":"json_object"}`;
- thinking: `{"type":"disabled"}`;
- output budget: fixed 1024 tokens;
- retry: zero; concurrency: one; fallback: none.

`LIVE VALIDATION NOT YET PERFORMED`. Account access, key type compatibility,
model availability, quota, quality, price, reported usage, upstream request ID,
and billing remain `NOT VERIFIED`. No key appears in this Evidence.

## Fixed scenario and CLI

Scenario `zhipu_live_canary_v1`, version `1`, asks for a safe accessible and
responsive task card with title, status, primary/secondary actions, keyboard
access, and no horizontal overflow at 390 px. Its context is synthetic and
public: no user/customer data, repository blob, local/private path, private
GitHub content, CreativeDeploy content, dynamic Prompt, or Secret is included.

Closed local commands:

```text
make zhipu-live-canary-preflight
make zhipu-live-canary-run
```

No CLI option can select Provider, model, endpoint, headers, Prompt, path,
request body, max tokens, transport, or output file.

## Authorization and Secret ordering

The production order is fixed:

1. exact command;
2. exact clean main checkout and app contract;
3. local PostgreSQL health and Alembic revision;
4. `VISUALENGINEER_LIVE_VALIDATION_AUTHORIZED=1`;
5. Zhipu and every other real Provider still disabled;
6. fixed scenario, adapter, scanner, and Settings field contracts;
7. only then read `Settings.zhipu_api_key` from `ZHIPU_API_KEY`.

`preflight` stops before steps 4 and 7, does not inspect either value, and
returns `USER_SECRET_PROVISION_REQUIRED` after all non-Secret gates pass. The
operator must provision the Secret only in the local terminal, never in chat or
a tracked `.env` file.

## Invocation and typed Plan contract

One run creates one independent `AIPlanRequest` and one
`AIProviderInvocation`. The Invocation commits `prepared`, then `dispatching`
immediately before the single send, then one terminal state. Success records
Zhipu/live classification, actual outbound digest, requested model, reported or
unavailable effective/upstream identity, nullable typed usage, monotonic queue/
Provider/total latency, normalized response digest, and
`live_billing_unknown` with null amount/currency.

The raw Provider text is never accepted as success. A compact closed response
must validate, contain no Secret-shaped material, normalize into the existing
typed Plan, and pass eight system-policy live-canary Evals. Only then is the
`AIPlanRequest` `generated`. Invalid structured output creates no Plan response
and no Eval. The run creates no approved handoff `Plan` row.

## Failure and authority evidence

- 401/403/429/5xx, malformed structured output, invalid typed content, and
  oversize response: `failed`.
- timeout, transport ambiguity, and post-dispatch cancellation:
  `outcome_unknown`.
- pre-dispatch cancellation: `cancelled_before_dispatch`, zero requests.
- every branch: request count exactly zero or one; never greater than one.
- every success/failure branch: no Plan Approval, AI Plan Decision, Execution
  Grant, Review Decision, Delivery Authorization, Runner Job, Workspace, Git,
  release, or deployment side effect.

Safe CLI output contains only scenario/provider, short internal correlation,
typed statuses, safe upstream fingerprint, nullable usage/latency, billing,
error code, and generated AI Plan request ID. It excludes credentials,
Authorization, Prompt, raw response, complete upstream ID, and raw error body.

## Verification ledger

| Gate                                               | Result                               |
| -------------------------------------------------- | ------------------------------------ |
| New canary focused PostgreSQL/MockTransport matrix | PASS — `36 passed`                   |
| Canary plus governed system Eval subset            | PASS — `53 passed`                   |
| Canonical backend aggregate                        | PASS — `514 passed`, 84.75% coverage |
| Contract/format/lint/type and Secret scanner       | PASS                                 |
| Real Provider credential access                    | `0`                                  |
| Real Provider outbound requests                    | `0`                                  |
| Provider registry activation changes               | `0`                                  |
| Live screenshot/evidence generation                | `0`                                  |
| Remote CI for final candidate                      | PENDING draft PR                     |

The implementation run used only the explicit synthetic credential
`synthetic-zhipu-live-canary-credential-only` inside tests. Test setup clears
all real Provider environment variables before constructing controlled test
configuration. MockTransport request counters prove the zero/one request
boundary; no public network transport is used.
