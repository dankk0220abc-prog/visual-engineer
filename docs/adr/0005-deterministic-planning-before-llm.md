# ADR 0005: Deterministic Planning Before LLM Integration

- Status: Accepted
- Date: 2026-07-26

## Context

The Phase 2 product needs a real reviewable Plan workflow, but no LLM, Agent
Runtime, model evaluation, prompt boundary, or production credential is
authorized. Presenting templated logic as Agent reasoning would overstate the
system and make repeatability harder.

## Decision

Generate Plans with a versioned deterministic policy using only the Task,
immutable Snapshot, selected delivery package, and explicit product rules.
Persist `source = deterministic_policy`, bind the Snapshot fingerprint,
compute a canonical content hash, use closed typed validation-step schemas,
and set `execution_available = false`.

Allow the user to revise only documented text/list fields. Apply bounded
Foundation policy validation before a revision is accepted and before a Plan
is submitted.

## Consequences

- Identical governed inputs produce explainable policy output without model
  cost or nondeterminism.
- Current evaluations measure contract and policy behavior, not model quality.
- String policy blocks obvious boundary violations but is not a complete
  security system.
- Any future LLM requires explicit provenance, held-out evals, unsupported-
  claim controls, and the same independent policy gates.
