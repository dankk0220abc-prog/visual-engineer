# Zhipu Safe Transport Observability and Owner-Key Isolation Evidence

Classification: `live_provider_attempt_failed_outcome_unknown`

## Truthful historical record

The first and only real Zhipu Invocation has safe correlation
`59bd943ccb99`, Provider `zhipu`, requested model `glm-5.2`, lifecycle
`outcome_unknown`, and `transport_error / provider_transport_error`. Client
total elapsed time is 10,501 ms. Usage is unavailable and billing remains
unknown. The attempt sent one request, had no retry or fallback, produced no
Plan, Eval, Approval, Execution Grant, Review, Delivery Authorization, Runner
job, or Workspace mutation, and remains unchanged.

Diagnosis `H` means the Provider HTTP layer was reachable but the root transport
exception was unavailable. The new taxonomy is prospective only and does not
retroactively reinterpret this row. This evidence is not a Live Validation
PASS and no Live PASS screenshot may be derived from it.

The machine-readable companion is
`live-provider-attempt-failed-outcome-unknown.json`.

## Prospective transport taxonomy

The classifier preserves `error_category` and stores only bounded fixed codes:

| Safe condition | Fixed error code | Category | Safe phase |
| --- | --- | --- | --- |
| DNS resolution | `provider_dns_resolution_failed` | `transport_error` | `connect` |
| Connection refused | `provider_connection_refused` | `transport_error` | `connect` |
| Network unreachable | `provider_network_unreachable` | `transport_error` | `connect` |
| Other TCP/connect failure | `provider_connect_failed` | `transport_error` | `connect` |
| TLS certificate verification | `provider_tls_certificate_verification_failed` | `transport_error` | `connect` |
| TLS handshake | `provider_tls_handshake_failed` | `transport_error` | `connect` |
| Connect timeout | `provider_connect_timeout` | `timeout` | `connect` |
| Read timeout | `provider_read_timeout` | `timeout` | `read` |
| Write interruption | `provider_write_interrupted` | `transport_error` | `write` |
| Response read interruption | `provider_response_read_interrupted` | `transport_error` | `read` |
| Remote protocol error | `provider_remote_protocol_error` | `transport_error` | `response` |
| Generic network error | `provider_network_error` | `transport_error` | `transport` |
| Unknown transport fallback | `provider_transport_error` | `transport_error` | `transport` |

Write/pool timeout and generic timeout retain dedicated bounded timeout codes;
the separately reviewed total deadline remains
`provider_total_deadline_exceeded`. Every post-dispatch timeout or transport
ambiguity remains `outcome_unknown`, with retry and fallback fixed at zero.

## Secret and owner-key boundary

The classifier reads no exception message, representation, arguments, URL,
headers, Authorization material, request/response body, or Prompt. Durable logs
use a fixed event name and only correlation, Provider, category/code, safe
phase, elapsed milliseconds, and lifecycle; they do not attach exception info.

General product settings no longer define or ingest any real Provider key.
Provider discovery and ordinary planning always treat real Providers as lacking
a user credential. The maintainer `ZHIPU_API_KEY` can be read only by the local
live-canary loader after repository, database, Provider-disablement, explicit
authorization, and secret-safety gates. No owner-key fallback exists.

## Validation status

Focused PostgreSQL validation passed 184 tests with 1 deselected. This aggregate
covered the 12-case classifier matrix, nested exception secret-negative
surfaces, fixed-field logging with no exception info, canary lifecycle,
request-count/no-retry/no-fallback behavior, governance zero-side-effects,
ordinary disabled-Zhipu planning, and owner-key value-read count zero.

Changed-scope Ruff format/check and mypy passed. Generated OpenAPI contract
drift passed without a generated diff. The fail-closed secret scanner and its
missing-dependency regression passed, as did `git diff --check`.

The backend canonical aggregate ran exactly once against the same isolated
PostgreSQL lifecycle: 528 tests passed with 85.03% coverage. The isolated
database was then stopped and removed. No real Provider key was read and the
implementation phase sent zero live Provider requests.

## Screenshot evidence preservation

Screenshot count is zero. The existing canary request payload contains
`scenario_id`, `scenario_version`, `response_contract`, and
`response_instruction`, which the unchanged ordinary AI Plan response schema
does not accept. Therefore the current real Web Console cannot truthfully render
this failed canary record through its existing source route. Per the screenshot
contract, the product UI was not changed or imitated merely to obtain a failure
image. No manifest is generated when there is no image, and screenshot
generation caused zero outbound Provider requests.

This is a truthful failure-evidence limitation, not a Live Validation PASS
claim. A future successful canary screenshot set remains mandatory and must be
read from one successful Invocation without another Provider request.

Exact remote Draft PR head and naturally triggered Fast/Heavy attempt-1 results
remain `NOT YET VERIFIED` until publication.
