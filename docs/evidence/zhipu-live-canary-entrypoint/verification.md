# Zhipu Live-Canary Entrypoint Verification

Classification: `pre_live_entrypoint_not_live`

Status: LOCAL CI REMEDIATION GREEN — NEW-CANDIDATE FAST/HEAVY RESEAL PENDING

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
| Remote CI for final corrective candidate           | PENDING — no rerun of failed run     |

The implementation run used only the explicit synthetic credential
`synthetic-zhipu-live-canary-credential-only` inside tests. Test setup clears
all real Provider environment variables before constructing controlled test
configuration. MockTransport request counters prove the zero/one request
boundary; no public network transport is used.

## CI environment dependency remediation

### Preserved prior CI evidence

- Fast `31314553818` failed on candidate
  `4d2fe752c9080ab46b1ed301b9daa727f7f5df6f`: its backend job ran
  `make test-api-direct` and reported `1 failed, 513 passed`. The failing test
  was `test_preflight_is_secret_blind_read_only_and_network_free`.
- The failure was a real fail-closed result, not a Provider product failure:
  Fast had no `rg` runtime prerequisite, while canary preflight correctly
  rejects an unavailable Secret scanner with `secret_scanner_unavailable`.
  No skip, warning, mock, PATH workaround, retry, or relaxation of the
  scanner/preflight contract was used.
- Heavy `31314553827` succeeded for the prior candidate. Its `security-eval`
  job explicitly installed Debian package `ripgrep` using `apt-get`, then ran
  `rg --version` before `make security-check`. This successful old run is
  retained as provenance only; it cannot seal the corrective candidate.
- The failed Fast run was not rerun. The remedy is a new commit and new Fast
  and Heavy runs bound to that commit.

### Corrective CI contract

The Fast `backend` job now uses the identical, already-canonical Heavy
provisioning mechanism before API checks: `apt-get update`,
`apt-get install --yes --no-install-recommends ripgrep`, and `rg --version`.
The two canonical jobs that require this dependency are therefore explicit:
Fast `backend` runs the canary preflight test; Heavy `security-eval` invokes
`scripts/check-secrets.sh` through `make security-check`.

The scanner remains fail closed: missing `rg` emits its fixed
dependency-missing error and exits nonzero without a clean conclusion. There
is no existing workflow-contract test framework in this repository, so this
minimal workflow change is protected by YAML parsing, the existing CI policy
check, scanner tests, and new remote Fast/Heavy evidence rather than a new
text-coupled parser.

### Local remediation validation

- `./scripts/check-secrets.sh`: PASS with `rg` present.
- `./scripts/test-check-secrets.sh`: PASS for missing-`rg`, inaccessible-root,
  clean, and synthetic-positive cases; it verified nonzero failure and no
  secret-body disclosure for the synthetic match.
- Original Fast failure test: PASS — `1 passed`.
- Canary focused PostgreSQL/MockTransport suite: PASS — `36 passed`.
- Both workflow YAML files parsed successfully; the existing
  `check_phase4_findings.py` policy check reported repair controls present;
  `git diff --check` passed.
- The focused test database was the repository's isolated tmpfs `test-db`.
  No full backend aggregate, Web suite, Playwright run, Docker image build,
  migration roundtrip, or live-canary command was repeated for this
  CI-environment-only diff.
- Real Provider API Key access: `0`; live Provider outbound requests: `0`;
  registry activation changes: `0`. Fixture remains the sole enabled/default
  Provider and Zhipu, Qwen, DeepSeek, Doubao, and Kimi remain disabled.

### Secret-scan and repository isolation record

A previous root Secret scan read ignored runner configuration within its scan
scope. It did not print or persist any value and found no Provider Key
material. This remediation does not directly open `.env.runner.local`; a root
scanner may process ignored local configuration within its defined scan scope,
but it does not print matching values.

No CreativeDeploy content was listed or read in this remediation. A prior
session did observe the path name `CreativeDeploy/AGENTS.md` without reading
its contents. This metadata deviation is retained here and must not be
restated as though CreativeDeploy metadata had never been observed.
