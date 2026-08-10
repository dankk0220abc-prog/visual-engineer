# Zhipu response-path classification Evidence

Classification: `prospective_response_path_classification_not_live_pass`

## Frozen historical evidence

The first and second real Zhipu Invocations, correlations `59bd943ccb99` and
`b7e92fd81760`, remain Provider `zhipu`, requested model `glm-5.2`,
classification `live`, lifecycle `outcome_unknown`, and
`transport_error / provider_transport_error`. Each has retry zero, fallback
zero, unavailable usage, unknown live billing, and no successful Zhipu live
result.

External Provider monthly account evidence indicates GLM-5.2 inference usage
within the month. It does not establish which Invocation produced that usage,
and exact per-Invocation attribution remains unknown. The response-path
diagnosis therefore remains `G — insufficient evidence`. In particular,
`httpx.DecodingError` is only a medium-confidence leading candidate and is not
a proven explanation for either historical row.

This remediation is prospective only. It does not rewrite lifecycle,
error category/code, status, usage, billing, effective model, or upstream
request identity for either historical Invocation.

## Prospective closed response-path taxonomy

| Proven boundary/family                       | Fixed code                                | Existing category       |
| -------------------------------------------- | ----------------------------------------- | ----------------------- |
| HTTP 4xx rejection not otherwise specialized | `provider_request_rejected`               | `request_rejected`      |
| HTTP 5xx                                     | `provider_upstream_server_error`          | `upstream_server_error` |
| Unexpected non-success 1xx/3xx               | `provider_unexpected_http_status`         | `invalid_response`      |
| Response decoding                            | `provider_response_decoding_failed`       | `transport_error`       |
| Response stream state                        | `provider_response_stream_state_error`    | `transport_error`       |
| Response body unknown processing             | `provider_response_body_processing_error` | `transport_error`       |
| Remote protocol                              | `provider_remote_protocol_error`          | `transport_error`       |
| Local protocol                               | `provider_local_protocol_error`           | `transport_error`       |
| General protocol                             | `provider_protocol_error`                 | `transport_error`       |
| True unknown before response                 | `provider_transport_error`                | `transport_error`       |

No exception message, exception chain, URL, header, Authorization value,
request body, response bytes, or encoding detail is persisted or logged. The
new post-header transport classifications remain conservatively
`outcome_unknown`. Existing structured-output, typed-validation, response-cap,
timeout, retry/fallback, and governance contracts remain unchanged.

## Validation and live-work facts

- Deterministic A-L, response-stage uniqueness, complete HTTP status handling,
  secret-negative surfaces, lifecycle, no retry/fallback, and governance
  zero-side-effect: `VERIFIED`, `187 passed`, exit `0`.
- The first focused aggregate recorded `175 passed / 12 failed`, exit `1`.
  Its first root cause was a synthetic test-harness misuse of zero-argument
  HTTPX stream exceptions plus incompatible logger capture, not a production
  classification defect. The single corrective aggregate is the passing
  result above.
- Backend canonical aggregate: `VERIFIED ONCE`; `553 passed`, coverage
  `85.10%`, exit `0`.
- Changed-scope Ruff format/check, mypy over 145 source files, OpenAPI contract
  drift, fail-closed secret scan, and `git diff --check`: `VERIFIED`, exit `0`.
  The Evidence Markdown had one initial Prettier check failure and was
  mechanically formatted before the final passing check.
- Post-validation database verification: `VERIFIED UNCHANGED`; live count two,
  succeeded count zero, Alembic `20260809_0016`, and both immutable row
  fingerprints identical to preflight.
- Screenshot count: `0`.
- Live Provider request count during implementation: `0`.
- Real Provider key reads during implementation: `0`.

## Recorded commands

| Scope              | Command                                                                                                                                                                           | Result                                    |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| Focused            | `TEST_DATABASE_URL=... uv run pytest apps/api/tests/test_zhipu_live_canary.py apps/api/tests/test_provider_foundation.py apps/api/tests/test_provider_invocations.py --no-cov -q` | corrective run exit `0`; `187 passed`     |
| Backend canonical  | `make test-api`                                                                                                                                                                   | exit `0`; `553 passed`; `85.10%` coverage |
| Python format/lint | `uv run ruff format --check <four changed Python paths>` and `uv run ruff check <four changed Python paths>`                                                                      | exit `0`                                  |
| Types              | `uv run mypy`                                                                                                                                                                     | exit `0`; 145 source files                |
| Contract           | `./scripts/check-contract-drift.sh`                                                                                                                                               | exit `0`; no generated diff               |
| Secrets            | `./scripts/check-secrets.sh`                                                                                                                                                      | exit `0`; no high-confidence pattern      |
| Patch integrity    | `git diff --check`                                                                                                                                                                | exit `0`                                  |

This Evidence is not a Live Validation PASS. A future successful screenshot
must reuse one already successful Invocation and must not trigger an additional
Provider request.
