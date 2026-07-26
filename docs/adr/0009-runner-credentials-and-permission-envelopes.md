# ADR 0009: Local Runner Credentials and Immutable Permission Envelopes

- Status: Accepted
- Date: 2026-07-26

## Context

The local Runner needs unattended registration and narrowly scoped work without
committing a secret or letting browser input define execution authority.

## Decision

Local startup generates an ignored, high-entropy Bootstrap Token with
restrictive permissions. Registration returns one independent random Runner
Token once; PostgreSQL stores only its SHA-256 digest and comparisons are
constant-time. Runner persists the token in its dedicated Docker volume and
uses Bearer authentication.

For each Job the Control Plane derives and immutably stores a Permission
Envelope. Canonical serialization produces a tamper-evident policy hash. In
Phase 3 the Envelope literally fixes repository access to none, shell to
false, and network to Control Plane only. Browser and Deployment Pack cannot
submit or expand it. Runner revalidates it before execution.

## Consequences

- Startup requires no manual secret entry and does not print the token.
- Database or browser reads cannot recover Runner credentials.
- Revocation is immediate at the API boundary.
- Job authority is reviewable, durable, and independent of Plan approval.
- A leaked long-lived local token remains a risk; automatic rotation is not
  implemented.

Production must replace the local scheme with mTLS or workload identity,
enterprise Secret Manager storage, rotation, and audited provisioning.
