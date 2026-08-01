# Phase 6 governed local delivery lifecycle verification

- Date: 2026-08-01 +08:00
- Repository: `/Users/danke/Developer/VisualEngineer`
- Main baseline: `79fa63f5d911a9e13ad388f270fdd18bf9084d22`
- Branch: `feat/phase-6-governed-local-delivery-lifecycle`
- Migration head: `20260801_0014`
- Candidate status:
  `PHASE_6_SECOND_SLICE_IMPLEMENTATION_COMPLETE_READY_FOR_INDEPENDENT_FOCUSED_REVIEW`
- Independent security decision: not made by this implementer

## Baseline and scope

Minimum AGENTS preflight confirmed the exact Developer repository root, local
`main`, HEAD/main at the declared baseline, clean worktree/index/untracked
state, empty remote and stash, and sole migration head `20260731_0013`. No
reset, overwrite, push, PR, tag, deploy, or main merge occurred.

Repository inspection found that the sealed/integrated first slice already
created one exact local commit and durable proof, but dispatch had no request
body or key, no manifest confirmation, no durable attempt identity/history,
and no recovery after failure or cancellation. The second slice therefore
implements one adjacent lifecycle closure rather than reopening Phase 0-5 or
starting a third slice.

## Implemented closure

Migration `20260801_0014` adds `delivery_dispatches`, one active-attempt and
linear-attempt constraints, exact manifest/confirmation equality, immutable
authority/lineage triggers, closed terminal transitions, retry-aware
Authorization transitions, and sequenced failed/cancelled AuditEvents. Its
downgrade removes only the new table/guards and restores first-slice guards.

The API derives a canonical `LocalDeliveryManifest` and bounded diff preview,
requires exact digest confirmation plus `Idempotency-Key`, serializes dispatch
on the Authorization row, records one concurrent winner, and permits only a
latest failed/cancelled attempt to retry under the same fresh authority and a
three-attempt budget. Revoked/expired implementation authority is visible in
preview and is rechecked at dispatch, claim, Permit acquisition, and result.

Protocol, Runner assignment, Permit binding, terminal result, LocalDelivery,
and AuditEvent carry Dispatch ID, attempt number, and manifest digest. Runner
recomputes the manifest from the current Workspace immediately before fixed
Git plumbing. The Web console provides preview, exact confirmation,
cancellation, terminal error, attempt history, Runner evidence, and safe retry.

## Verification ledger

| Boundary               | Result                                                                                                                                                   |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Runner and Protocol    | `make test-runner`: `110 passed`, exit `0`                                                                                                               |
| PostgreSQL lifecycle   | exact test DB final: `10 passed`, exit `0`; includes keyed concurrency, revoke, recovery, legacy no-lineage denial, and three-attempt budget             |
| Migration              | empty base -> `20260801_0014` -> base -> `20260801_0014`, exit `0`; sole head confirmed                                                                  |
| Web component          | `55 passed`, exit `0`; unknown-response replay reuses one deterministic preview/attempt/manifest key                                                     |
| Contracts/static/types | contracts, format, Ruff, ESLint, mypy `116` files, TypeScript all exit `0`                                                                               |
| Build                  | production Next.js/Docker API/Runner/Web images build; `/deliveries` emitted, exit `0`                                                                   |
| Real browser           | first run found one strict locator ambiguity after success; corrected rerun, live-stack rerun, and final-source isolated rerun each `1 passed`, exit `0` |
| Manual browser         | desktop and `390x844` show terminal attempt, manifest digest, Runner evidence, commit proof and no-remote text; browser console errors `0`               |
| Source invariance      | 119 entries, 10 Git objects, 2 status records, 0 extension markers; exit `0`                                                                             |
| Docker cleanup         | all three task-owned Compose projects and `test-db` have zero containers, volumes, and networks after exact cleanup                                      |
| Complete aggregate     | exactly one `make verify`: `309 passed`, one unchanged Phase 5 Suite concurrency deadlock, exit `2`; stopped at `test-api`                               |

The formal E2E wrapper compared adversarial source and canonical Workspace
HEAD, status hashes, and Workspace tree fingerprint before/after the focused
flow. It also rejected lifecycle extension markers. No real repository or
remote was mounted.

## First failures and recovery

Failures and invalid attempts are retained and are not counted as passes:

1. A combined Protocol/Runner pytest invocation used the API coverage config;
   all selected behavior tests passed, but the command exited `1` for zero API
   coverage. The repository `make test-runner` target then passed `110/110`.
2. The first direct API run found no PostgreSQL on `55433` and exited `1` with
   four setup errors. The exact `test-db` fixture was started before rerun.
3. A subsequent focused wrapper reached `4 passed`, but its zsh cleanup used
   reserved variable `status` and exited `1`; it was marked `INVALID_ATTEMPT`,
   exact cleanup was confirmed, and a POSIX-shell run passed `8/8`.
4. The first lint chain stopped only on import ordering and one unused test
   import. Scoped Ruff autofix was applied; lint/typecheck then exited `0`.
5. The first real Chromium flow reached a successful delivery but the new
   attempt history made `succeeded` appear twice under one card. The assertion
   was scoped to the top-level first status and the exact isolated flow passed.
6. A cleanup inspection attempted Compose interpolation without required
   fixture variables and produced no state change. Label-based zero-resource
   inspection was used instead.
7. The first manual cleanup command was rejected before execution because it
   contained `rm -rf`. Exact Compose resources were removed normally and the
   validated temporary fixture was deleted with a bounded depth-first delete.
8. The single complete aggregate stopped at one PostgreSQL deadlock in
   unchanged historical test
   `test_concurrent_suite_create_consumes_one_grant_exactly_once[True]` while
   locking a child `validation_runs` idempotency row. The then-current Phase 6
   tests passed `8/8` inside that run; the final focused file passes `10/10`.
   The test and its Suite/Validation service/repository have zero diff from
   `main`; the exact parameter then passed `1/1`, exit `0`,
   in an isolated real-PostgreSQL rerun. No Phase 5 code or test was changed
   and the full aggregate was not repeated.
9. The first new Web idempotency regression expected a raw JavaScript error
   message, while the product intentionally renders a generic non-API error.
   The assertion was aligned with the existing redaction contract; final Web
   tests pass `55/55` and confirm both dispatch calls use the same deterministic
   Authorization/attempt/manifest key.

No authority, TTL, retry budget, timeout, or expected state was widened to
make a test pass.

The aggregate limitation is an unrelated concurrency-instability risk for the
independent Final Gate, not evidence of a Phase 6 lifecycle failure. Gates
after `test-api` were not reached by that aggregate; their directly relevant
focused equivalents above passed independently.

## Boundary and next review

This is implementer evidence. It is not an independent focused-review PASS,
Security Gate PASS, sealing decision, main integration, remote delivery,
production readiness, or authorization for a third slice. Independent review
should concentrate on manifest reconstruction, keyed concurrency, retry
lineage/budget, terminalization, revoke/expiry races, deterministic ref replay,
source invariance, and zero remote/source effects.

The checkpoint hash and final clean branch/HEAD/main/worktree state are
reported in the handoff because a commit cannot contain its own hash.
