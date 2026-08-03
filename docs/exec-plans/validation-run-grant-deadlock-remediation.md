# Validation Run Grant Deadlock Remediation

- Started: 2026-08-03 +0800
- Repository: `/Users/danke/Developer/VisualEngineer`
- Baseline: `c310dab795d01a29c2ca8c5fe4aaeaeb8179bd4a`
- Branch: `fix/validation-run-grant-deadlock`
- Status: `LOCAL VERIFICATION PASSED — PUBLICATION PENDING`

## Goal

Remove the PostgreSQL deadlock exposed by Fast CI run `30825107370`, job
`91724618472`, while preserving the existing one-Suite-per-Grant and exact
idempotent replay contracts. The repair must use a deterministic database
competition point, keep the loser response stable, roll back partial child
dispatch state, and leave the candidate as an independent Draft PR for a
separate focused review.

## Scope

Allowed production changes are limited to the shared Validation/Suite service
transaction boundary needed to make child Validation Run and Runner Job
creation atomic. Tests may add deterministic PostgreSQL barriers and rollback
injection. This plan and the matching verification Evidence are the only
documentation additions.

No migration is planned: the database already enforces unique Suite
idempotency, one Suite Run per Execution Grant, one root/attempt, child
Validation idempotency, and one Runner Job per Validation Run.

## Non-goals

- No deadlock retry, sleep, serial test conversion, `SKIP LOCKED`, isolation
  increase, timeout expansion, or exactly-once weakening.
- No Provider, model, API key, credential, license, tag, deploy, or production
  work.
- No modification, close, merge, force-push, or readiness transition for
  Draft PR #14.
- No merge of this remediation PR; independent focused review remains
  mandatory.

## Confirmed failure evidence

- Fast CI ran SHA `df68becd7474c8fbc7fd6401abd59560677ece1c` and failed only
  `make test-api-direct`: 350 passed, 1 failed.
- PostgreSQL process 780 waited for `ShareLock` on transaction 4573, blocked
  by process 779. Process 779 waited for `ShareLock` on transaction 4572,
  blocked by process 780.
- Process 780 was executing the child-idempotency
  `SELECT ... FROM validation_runs WHERE idempotency_key = ... FOR UPDATE`.
- Process 779 was executing
  `UPDATE validation_runs SET version = ..., updated_at = now() WHERE id = ...`.
- PostgreSQL reported tuple `(0,1)` in relation `validation_runs`.

## Pre-repair transaction analysis

The winning Suite create transaction locks the exact validation Grant and its
single Checkpoint/Workspace/Handle context, inserts the Suite and fixed steps,
and commits the durable Grant-to-Suite consumption. First-child dispatch then
locks the same Grant, Suite, and ordered steps.

Inside that locked dispatch, `ValidationService.create()` currently inserts a
Validation Run and step, then calls `RunnerService.create_workspace_job()`
with its default `commit=True`. That nested commit exposes a child
`validation_runs` row before `runner_job_id`, queued state, and version are
bound by the following Validation-service commit. A concurrent exact replay
can enter the same fixed child idempotency key during this split window.

SQLAlchemy Sessions use `autoflush=True` and `expire_on_commit=True`. No ORM
relationship loader or SQLAlchemy event hook exists in the API source/tests.
The dirty Suite update is currently autoflushed by the first child query; the
child insert has an explicit flush, the Runner helper flushes and commits, and
the final child binding is flushed by the later commit.

## Implemented repair

1. Make Validation-owned Runner Job creation non-committing so the child
   Validation Run, fixed step, Permission Envelope, Runner Job, creation
   event, and final `runner_job_id`/state/version binding become visible in one
   Validation-service commit.
2. Make Suite and child flush points explicit before nested queries/commit.
3. Roll back the dispatch transaction before recording a typed
   `recovery_required` Suite outcome when child dispatch raises, preventing a
   later recovery commit from persisting a half-created child/job.
4. Keep the existing exact Grant row lock plus database uniqueness as the
   single competition point; do not add a migration or retry.

## Deterministic verification design

- Synchronize two independent PostgreSQL Sessions immediately before the
  exact Grant `FOR UPDATE`, not before thread creation.
- Run same-key replay and different-key loser contracts in both submission
  orders.
- Assert exactly one Suite, two fixed Suite steps, one child Validation Run,
  and one Runner Job, with no duplicate/partial bindings.
- Inject a Runner dispatch failure after its non-committing flush and prove an
  independent Session cannot observe partial state; after rollback, retain
  only the existing recovery Suite/steps and consume the Grant once.
- Hold one exact Grant lock and prove a request using a disjoint Grant can
  complete before release, excluding a global serialization repair.
- Retain existing revoked, expired, stale, consumed, retry, lifecycle, and
  PostgreSQL direct tests.

## Progress

- done — fail-closed repository/baseline/authentication preflight
- done — independent branch created from the exact baseline
- done — PR #14 confirmed Draft and limited to `scripts/run-e2e.sh`
- done — raw CI job log saved outside the repository and hashed
- done — failure SQL, PIDs, XIDs, relation, tuple, stack, transaction split,
  autoflush, relationship, and event-hook investigation
- done — deterministic regressions and narrow transaction repair
- done — targeted tests and deterministic 30-iteration repeat
- done — related authorization/lifecycle/PostgreSQL subsets
- done — Ruff, mypy, diff, and source-invariance checks
- done — one final `make test-api-direct`: 355 passed, 84.44% coverage
- pending — scoped commit, push, independent Draft PR, Fast/Heavy CI terminal

## Stop conditions

Stop without expanding scope for any baseline drift, unrelated user change,
new Security/Eval/Chaos/Migration/product failure, required schema redesign,
or more than one transient external CI rerun. Never merge or mark ready.
