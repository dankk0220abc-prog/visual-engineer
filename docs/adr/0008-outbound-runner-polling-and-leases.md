# ADR 0008: Outbound Runner Polling and Fenced PostgreSQL Leases

- Status: Accepted
- Date: 2026-07-26

## Context

The local Runner must stay behind the Control Plane boundary, tolerate
temporary API loss, prevent duplicate claims, and recover work after process
loss without Redis, Kafka, Celery, or Temporal.

## Decision

Runner makes outbound authenticated heartbeat and bounded short-poll requests;
it exposes no HTTP server. PostgreSQL is the Phase 3 durable queue.

Claim uses `SELECT ... FOR UPDATE SKIP LOCKED` inside a transaction. Each claim
creates a new Attempt and random Lease UUID. Every mutation binds Runner,
Attempt, and Lease identity and rechecks the deadline under lock. A partial
unique index permits one active Attempt. A Control Plane reaper with a
PostgreSQL advisory lock expires leases, requeues within budget, and fails
exhausted work.

## Consequences

- Two concurrent Runners have one claim winner.
- A recovered stale Runner cannot overwrite a newer Attempt.
- Process loss is visible as offline, `lease_expired`, and requeue/failure.
- Polling and relational locks are simple and adequate for bounded local
  throughput.
- API availability affects scheduling; a future independent reaper worker can
  improve operational separation without changing protocol.

A broker becomes justified only by measured high throughput, fan-out, delayed
scheduling, cross-region operation, or independently scaled queue workers.
