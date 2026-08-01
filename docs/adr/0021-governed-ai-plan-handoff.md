# ADR 0021: Governed AI Plan Request and Human Handoff

- Status: Accepted for Phase 7 first-slice implementation
- Date: 2026-08-01

## Context

The existing deterministic `Plan` is already the root of later Execution Grant
governance. Directly treating a Provider response as that Plan would collapse
generation, evaluation, human approval, and execution eligibility into one
ambiguous object. It would also make timeout/retry Trace and failed/cancelled/
stale generation state difficult to preserve without weakening the proven
Phase 2 approval flow.

## Decision

Introduce a separate `AIPlanRequest` aggregate. It binds an immutable
Repository Snapshot/revision to a versioned Prompt, redacted structured
Provider request, bounded context manifest, model-neutral Provider capability
metadata, validated response, attempt Traces, synthetic usage/cost fields, and
system-owned deterministic Eval results.

The deterministic fixture Provider implements the same protocol expected of a
future Provider but performs no network call and accepts no credential. Its
response is a closed typed `AIPlanContract`; explanatory strings are never an
execution contract. Proposed operations are a discriminated union and carry no
authority.

Only a `local_user` decision may approve or reject a generated, fresh,
mandatory-Eval-passing request. Approval atomically creates one existing
`Plan` handoff with `source = governed_ai`, an `ApprovalDecision`, and the
terminal approved Run state. Rejection creates no handoff. The existing
Execution Grant workflow may later consume the approved Plan through its own
independent request and decision, but approval itself creates no Grant,
Workspace, Review, Delivery Authorization, Git effect, or deployment effect.

## Consequences

- Provider generation and Eval evidence remain inspectable without pretending
  the Provider is a trusted evaluator or approver.
- Exact replay can be tested without a key, SDK, network, or billable call.
- Revision drift fences approval and marks the request stale.
- Existing deterministic Plans remain valid; only the Plan source constraint
  expands to the model-neutral `governed_ai` provenance.
- A future real Provider still requires explicit authority for SDK/network/key
  configuration, production isolation, and Provider-specific validation. This
  ADR does not grant any of those capabilities.
