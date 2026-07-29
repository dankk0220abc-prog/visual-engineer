# ADR 0017: Compose fixed Validation Runs with system-owned Suites

- Status: Accepted for the Phase 5 second-slice implementation candidate
- Date: 2026-07-30

## Context

The sealed first Phase 5 slice can execute one immutable, fixed fixture
Validation Profile with independent Grant, Runner Job, Attempt, Lease, Permit,
result, Evidence, sandbox cleanup, and canonical-Workspace invariance. The
next slice needs deterministic multi-step validation without adding arbitrary
commands or weakening those fences.

## Decision

Keep versioned Suite definitions in source. API clients select only a Suite
ID/version and an approved Suite-scoped Grant; they cannot submit steps or
execution fields. The Control Plane materializes the ordered catalog steps and
dispatches exactly one existing fixed-Profile Validation Run at a time.

The first Suite, `fixture-integrity-suite-v1:v1`, runs the fixed contract
Profile followed by the fixed manifest/digest Profile. It is fail-fast, has a
30-second total timeout, a 10,000-byte combined retained-output cap, zero
artifacts, and at most two Suite attempts. A retry requires a fresh Grant,
reuses successful immutable Evidence without redispatch or recharge, and
creates fresh child execution identities for remaining steps.

## Consequences

- Every executed step retains the first-slice execution and cleanup fences.
- Aggregate state, budgets, idempotency, cancellation, retry lineage, and
  Evidence references require additive PostgreSQL entities and triggers.
- Suite cancellation/timeout must cancel an active child before terminalizing
  and must never dispatch a later pending step.
- Runner Protocol gains one closed Profile/step literal but no generic Suite,
  shell, command, environment, cwd, network, package, or artifact authority.
- This candidate requires an independent focused review of Suite immutability,
  injection prevention, state consistency, races, budgets, aggregation,
  cleanup, and invariance.

## Rejected alternatives

- Caller-defined steps or commands: violates the execution boundary.
- One monolithic Runner Suite job: loses independent child Attempts, Leases,
  Permits, results, and reusable Evidence.
- Rerun every step on retry: duplicates successful execution and budget
  charging.
