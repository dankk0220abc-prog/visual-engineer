# Phase 6 Delivery Cancel-Mutation Arbitration Remediation

## Goal

Close the single Phase 6 Second Slice Finding in which a successful user
cancellation could race the pre-mutation local-delivery path and leave a real
commit/ref inconsistent with cancelled PostgreSQL state.

## Scope

- Exact candidate: `9bef907f78ca482da1a06a8ff7e2ce3d3c2e1c9d`.
- Branch: `fix/phase-6-delivery-cancel-mutation-arbitration`.
- Reuse the Runner Job/Attempt state machine, PostgreSQL row locks, exact
  `git_commit` Side-effect Permit, and managed-mirror lock.
- Add deterministic cancel-first, mutation-first, simultaneous-competition,
  Grant-revoke, and Runner no-executor regressions.

## Non-goals

- Manifest/digest, migration, remote, API schema, Web behavior, dependency,
  timeout, TTL, retry-count, or process-local ownership changes.
- Phase 5 deadlock attribution, Workspace Chaos, complete `make verify`,
  sealing, main integration, push, PR, tag, or deployment.

## Design

The existing `acquire_side_effect_permit` transaction already locks and
revalidates the exact Job, Attempt, Dispatch, Authorization, Grant, Workspace,
and Permit binding. Treat its committed consumed Git Permit as the mutation
ownership decision.

`cancel_job` locks the same Job first and reads the exact Attempt-bound Git
Permit. With no consumed Permit it may commit cancellation; a later Permit
request observes `cancel_requested` and fails before Git execution. With a
consumed Permit it returns the existing `runner_job_terminal` conflict without
state mutation. Grant revoke retains its existing bounded-revocation contract:
it waits in `revoke_requested` while the Git Permit is consumed.

Runner handles the cancel-first `stale_lease` at Permit acquisition by an
authoritative renew. It acknowledges only an observed `cancel_requested` state
and returns before creating the executor task.

## Deterministic concurrency evidence

Two forced-order PostgreSQL tests pause the winning transaction immediately
before commit while it holds the Job row lock. The competing backend must be
visible as a `Lock` waiter whose `pg_blocking_pids` contains the winner. A third
test releases both operations through one barrier and accepts only the two
legal single-winner outcomes. No sleep determines the outcome.

## Progress

- **done**: exact repository, candidate/main, clean tree, ancestry, and branch
  creation verified.
- **done**: production arbitration and cancel-first Runner acknowledgement
  implemented without a contract, migration, Manifest, or Web change.
- **done**: new Runner test passes `1/1`; real PostgreSQL arbitration/revoke
  tests pass `4/4`.
- **done**: Phase 6 API lifecycle passes `14/14`; focused Runner/Protocol passes
  `12/12`; related PostgreSQL lifecycle passes `11/11`; focused Security and
  Runner lifecycle pass `10/10` plus the static Runner security check.
- **done**: full requested format/format-check, lint, typecheck, source
  invariance, and `git diff --check` pass; the final tracked/untracked scope is
  limited to the three production files, two new regression files, and five
  directly related architecture/security/plan/evidence documents.
- **done**: the task-owned isolated PostgreSQL `test-db` was stopped and
  removed; pre-existing development API/DB/Runner/Web containers were not
  changed.
- The one local remediation commit follows this evidence freeze; its exact
  hash is reported in the final Git handoff.

## Rollback

Revert only this remediation commit. Do not reset, clean, rewrite a governed
ref, modify source repositories, or remove unrelated Docker state.

## Completion condition

Both legal ownership orders are proven, impossible mixed outcomes are denied,
all requested focused gates pass, one local commit is created, and the branch
is clean and ready only for independent focused re-review.
