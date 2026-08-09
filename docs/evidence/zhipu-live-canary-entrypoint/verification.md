# Zhipu Live-Canary Entrypoint Verification

Classification: `pre_live_entrypoint_not_live`

Status: VE-ZLC-FSR-001 LOCAL REMEDIATION GREEN — NEW FAST/HEAVY SEAL PENDING

## Candidate identity

- Base `main`: `569fc39ad7d2b0e36432d14c50af93ee950b0a78`.
- Base tree: `ec0ce4c3478ff8b253b0a0b855981f19c950fbc2`.
- Branch: `codex/feat/zhipu-live-canary-entrypoint`.
- Implementation commit: `07adc9b35fcf5c5ba0b0d9e6211475bfb15d37bf`.
- Independently reviewed pre-remediation candidate:
  `8407589a19062cef0756b940c23bc8474cc69cb5`, tree
  `ffc1b468f878919badde4778d80c7c925a58dbc8`.
- Reviewed pre-remediation CI: Fast `31315473943` and Heavy `31315473954`,
  attempt 1, successful on that exact candidate. These runs preserve candidate
  provenance but cannot seal the corrective candidate.
- Security corrective implementation commit:
  `8cfee32007be768437aaff06fa14db358831299f`, tree
  `900b0507561d162654ada41b3ec9320cfa5bcf55`.
- Formatting follow-up candidate: the commit containing this Evidence update;
  exact SHA/tree are bound in PR #18 and the new Fast/Heavy sealing record.
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

### Preserved independent finding history

The first implementation and this Evidence originally stated that preflight
did not read Provider Secrets. Independent review then used a synthetic
environment value-access probe and proved that statement false:

- `_secret_blind_environment()` copied the complete process environment before
  deleting known Secret keys, so each copied Provider Secret value had already
  been read;
- pre-authorization `CanaryDatabaseSettings()` used the BaseSettings environment
  source, which enumerated the complete process environment even though the
  caller needed only `DATABASE_URL`.

This remains permanently recorded as blocking finding `VE-ZLC-FSR-001`. The
prior false assurance and its reviewed reproduction are not deleted or
reclassified by the remediation.

### Corrective contract

The production order is fixed:

1. exact command;
2. fixed scenario and closed CLI validation;
3. exact clean main checkout through Git subprocesses whose environments are
   built only from the fixed safe allowlist `PATH`, `HOME`, `TMPDIR`, `LANG`,
   `LC_ALL`, and `LC_CTYPE`, plus fixed Git safety variables;
4. local PostgreSQL health and Alembic revision through the database-only
   `CanaryDatabasePreflightConfig`, which reads only `DATABASE_URL`;
5. Zhipu and every other real Provider still disabled, plus fixed scenario,
   adapter, and scanner contracts;
6. read and validate `VISUALENGINEER_LIVE_VALIDATION_AUTHORIZED=1`;
7. only then use the Zhipu-only loader to read `ZHIPU_API_KEY` into
   `SecretStr`; no all-Provider Settings object is constructed;
8. construct the production Zhipu adapter and proceed toward one dispatch.

Unknown environment variables are denied by default; there is no copy-then-
filter path. `preflight` stops before steps 6 and 7, does not inspect either
value, and emits only `USER_SECRET_PROVISION_REQUIRED` plus the safe variable
name `ZHIPU_API_KEY` after all non-Secret gates pass. It does not report whether
the Secret is configured.

The deterministic probe mapping separately records key-existence checks and
value access through `__getitem__` and `.get()`. It fails with only
`PROVIDER_SECRET_VALUE_READ_BEFORE_AUTHORIZATION` and the safe key name; it
never includes the synthetic value.

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

## Preserved pre-remediation verification ledger

| Gate                                               | Result                                      |
| -------------------------------------------------- | ------------------------------------------- |
| New canary focused PostgreSQL/MockTransport matrix | PASS — `36 passed`                          |
| Canary plus governed system Eval subset            | PASS — `53 passed`                          |
| Canonical backend aggregate                        | PASS — `514 passed`, 84.75% coverage        |
| Contract/format/lint/type and Secret scanner       | PASS                                        |
| Real Provider credential access                    | CLAIMED `0` — disproved by `VE-ZLC-FSR-001` |
| Real Provider outbound requests                    | `0`                                         |
| Provider registry activation changes               | `0`                                         |
| Live screenshot/evidence generation                | `0`                                         |
| Remote CI for final corrective candidate           | PENDING — no rerun of failed run            |

The implementation run used only the explicit synthetic credential
`synthetic-zhipu-live-canary-credential-only` inside tests. Test setup clears
all real Provider environment variables before constructing controlled test
configuration. MockTransport request counters prove the zero/one request
boundary; no public network transport is used.

## VE-ZLC-FSR-001 remediation verification ledger

| Gate                                     | Result                                    |
| ---------------------------------------- | ----------------------------------------- |
| Fixed Git child-environment access probe | PASS — Provider reads `0`                 |
| Real database preflight access probe     | PASS — only `DATABASE_URL` read           |
| Full preflight production-order probe    | PASS — Provider reads `0`                 |
| Missing-authorization production probe   | PASS — Provider reads `0`                 |
| False-authorization production probe     | PASS — Provider reads `0`                 |
| Authorized missing-Zhipu-key probe       | PASS — Zhipu read `1`, other reads `0`    |
| Authorized synthetic-key MockTransport   | PASS — Zhipu read `1`, request `1`        |
| Other-Provider value reads               | PASS — Qwen/DeepSeek/Doubao/Kimi each `0` |
| Pre-authorization DB mutation / HTTP     | PASS — `0` / `0`                          |
| Canary focused suite                     | PASS — `37 passed`                        |
| Changed-scope static/security checks     | PASS                                      |
| One canonical backend aggregate          | PASS — `515 passed`, 85.04% coverage      |
| Corrective-candidate Fast / Heavy        | PENDING — new exact candidate required    |

No real Provider environment value is read by this verification. Synthetic
values are installed only in the access-probe mapping, and the mapping's
failure diagnostics contain only a fixed code and safe environment key name.

The successful synthetic-key production-order probe used the no-argument
production factory and replaced only the adapter's internal production-client
constructor with MockTransport. It produced one typed Plan and the reviewed
Invocation lifecycle. Database deltas were exactly one Task, Run, Snapshot,
AIPlanRequest, and AIProviderInvocation plus eight system-policy Eval rows;
Approval, Grant, Review, Delivery, Runner, Workspace, and Plan authority deltas
were all zero. Missing/false authorization, preflight, and authorized
missing-key cases each had zero database mutation and zero HTTP request.

The focused-batch attempt record is retained. Attempt 1 exposed a test-harness
scope error because the value-access mapping remained installed during pytest
teardown (`4 passed`, `67 errors`); no product assertion failed. Attempt 2
executed the production repository gate and exposed Git's platform-specific
absent-ref status (`32 passed`, `5 failed`): `show-ref --verify refs/stash`
returned 128 when no stash existed. The fail-closed repair uses
`for-each-ref --format=%(refname) refs/stash`, which returns empty success only
for absence, returns the ref when present, and still rejects Git command
failure. Attempt 3 passed `37/37`. No Provider value or live HTTP request was
used in any attempt.

Changed-scope validation passed Ruff format, Ruff lint, mypy for four changed
Python files, generated API contract drift, the root location-only Secret
scanner, the missing-rg fail-closed regression, and `git diff --check`. The one
canonical backend aggregate then passed `515/515` with 85.04% coverage and exit
code 0. No Web unit, ESLint, TypeScript, Playwright, migration roundtrip, Docker
rebuild, or live-canary command was run.

The first remote corrective candidate was not rerun. Fast `31320510992`,
attempt 1, completed `failure` on exact SHA
`8cfee32007be768437aaff06fa14db358831299f`. Its backend, contract, Runner, and
repository-policy jobs passed; the sole failure was
`make format-check-web`, which reported only this Evidence file as needing
Prettier formatting. Heavy `31320510988`, attempt 1, completed `success` on the
same exact SHA, but it cannot seal a candidate whose Fast run failed. Because
the commit had already been published by ordinary push, rewriting it would
require prohibited force push; the narrow follow-up contains this permanent
attempt record plus the mechanical Prettier result, with no production or test
change.

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
