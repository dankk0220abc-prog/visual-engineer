# ADR 0007: Separate Control Plane and Execution Plane

- Status: Accepted
- Date: 2026-07-26

## Context

VisualEngineer needs browser orchestration and durable governance without
granting Web, API, or PostgreSQL customer-repository execution authority.
Phase 2's API-only read-only mount was a bounded historical investigation
mechanism, not a deployment architecture to extend.

## Decision

Web, API, and PostgreSQL form the Control Plane. They own intent, policy,
identity, scheduling, leases, cancellation, audit, and evidence indexes.

An independent outbound Local Runner forms the Execution Plane. In Phase 3 it
executes only repository-free typed diagnostics and controlled waits. It has
no repository, shell, worktree, Git, Docker socket, database network, Web
network, inbound port, or public network.

Plan approval and Runner Job dispatch remain distinct user actions and
authorities.

## Consequences

- Control Plane compromise does not automatically create a repository mount or
  shell executor.
- Execution policy has an explicit protocol and immutable Envelope.
- Runner lifecycle and credentials are independently testable and revocable.
- Local Compose needs a dedicated internal Runner network.
- Phase 4 repository work requires a new isolated-worktree decision; it cannot
  be smuggled into this Runner.

This is not a production sandbox or tenant-isolation claim.
