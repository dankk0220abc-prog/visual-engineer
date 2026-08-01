# Phase 6 Second Vertical Slice — Governed Local Delivery Lifecycle

## Goal

Turn an approved First Slice Delivery Authorization into an inspectable,
explicitly confirmed, recoverable local-only delivery lifecycle. The operator
must review one immutable server-derived manifest before dispatch, every
dispatch attempt must be keyed and durable, and a failed or cancelled attempt
may be retried only against the same still-fresh authorization and manifest.

## Scope

- Add an immutable local-delivery manifest/preview derived from the authorized
  Checkpoint, including bounded diff evidence and explicit zero-remote fields.
- Add durable Delivery Dispatch attempts with confirmation digest,
  idempotency, linear retry lineage, terminal state/error, Runner Job binding,
  and a maximum of three dispatches per Authorization.
- Bind the manifest and Dispatch identity through API, Runner Protocol, Permit
  job digest, Runner revalidation, terminal result, LocalDelivery proof, Web,
  AuditEvent, and generated contracts.
- Add browser-first preview, confirmation, cancellation, history, terminal
  error, and safe-retry controls.
- Add focused Protocol/Runner/API/PostgreSQL/security/Web/browser coverage and
  update architecture, security, ADR, evidence, roadmap, and Project Status.

## Non-goals

- Remote Git, push, pull request, merge, tag, deployment, source write, or
  user-supplied ref/message/command/argv/cwd/environment/identity.
- Real repositories, CreativeDeploy, Customer 0, LLMs, Agents SDK, Providers,
  credentials, authentication, multi-tenancy, or arbitrary target commands.
- A third Phase 6 slice, general Git history browsing, branch deletion, or
  delivery cleanup.

## Constraints and safety

- Exact base is clean local `main`
  `79fa63f5d911a9e13ad388f270fdd18bf9084d22`; branch is
  `feat/phase-6-governed-local-delivery-lifecycle`.
- The manifest is server-derived from immutable Authorization and Checkpoint
  fields and independently recomputed by Runner from the current Workspace.
- Dispatch requires an exact manifest digest confirmation and a unique
  `Idempotency-Key`. PostgreSQL locking permits only one active attempt.
- Retry is allowed only after the latest Dispatch is `failed` or `cancelled`,
  with exact `retry_of_dispatch_id`, no LocalDelivery, active authorities,
  fresh Review evidence, unchanged Workspace/Checkpoint, and remaining
  dispatch budget.
- The existing deterministic commit timestamp/ref/message make a retry either
  reproduce the exact commit/ref or fail closed; no cleanup or ref replacement
  is authorized.
- Stop before any new external, remote, real-repository, command, credential,
  destructive migration, or main-integration boundary.

## Current progress

- 2026-08-01 CST — **done**: exact root, branch, HEAD/main, clean status/diff,
  empty remote/stash, and sole Alembic head `20260731_0013` verified.
- 2026-08-01 CST — **done**: First Slice plan/evidence/ADR/final gate, product,
  architecture, security, roadmap, migration, API, Protocol, Runner, Web, and
  focused tests inspected.
- 2026-08-01 CST — **done**: highest-value adjacent gap selected: First Slice
  has no explicit final confirmation, immutable dispatch proof, concurrent
  keyed dispatch, attempt history, or terminal recovery path.
- 2026-08-01 CST — **done**: feature branch created from the exact baseline.
- 2026-08-01 CST — **done**: reversible Dispatch migration, canonical manifest
  Protocol, API transaction/guards, Runner revalidation/result binding, Web
  preview/history/recovery, generated contracts, and focused tests implemented.
- 2026-08-01 CST — **done**: Runner/Protocol `110`, final PostgreSQL lifecycle
  `10`, Web `55`, migration roundtrip, contracts,
  static/types/build, focused real Chromium, desktop/narrow manual browser,
  source-invariance wrapper evidence, and task-owned Docker cleanup pass.
- 2026-08-01 CST — **done**: exactly one full `make verify` reached `309/310`
  Python tests and exited `2` on one unchanged historical Phase 5 Suite
  concurrency deadlock; the exact test then passed `1/1` in isolation. No
  Phase 5 code/test or authority was changed and the aggregate was not repeated.
- 2026-08-01 CST — **done**: final tracked/untracked diff and prohibited-boundary
  scan contain only the scoped migration/API/Protocol/Runner/Web/tests/docs;
  no dependency, environment, CI, remote, customer, command, or credential
  surface changed. Evidence is frozen for the clean local checkpoint reported
  in the handoff.

## Decisions

1. Preserve one immutable Delivery Authorization and one final LocalDelivery;
   represent operational recovery as a linear series of Delivery Dispatches.
2. Use the manifest digest as the browser confirmation token. The manifest
   includes only bounded Checkpoint metadata/diff evidence and literal denied
   remote effects; it contains no path, credential, environment, or source
   corpus outside the existing bounded diff artifact.
3. Keep Runner Job internal retry and add at most three user-visible Dispatch
   attempts. Cross-Job retry remains the same deterministic Git operation and
   never grants a new ref or message.
4. Keep terminal Dispatch records append-only except for their closed
   dispatched-to-terminal transition. Authorization may re-enter dispatched
   only from failed/cancelled under the retry checks above.

## Risks

- Confirmation replay or concurrent double click: unique keyed request hash,
  Authorization row lock, one active Dispatch index, and linear attempt number.
- Ref exists after an uncertain prior result: Runner revalidates the complete
  mirror and accepts only the exact deterministic commit/ref binding.
- Stale authority between preview and mutation: preview is advisory; dispatch,
  claim/lease, Permit acquisition, and result acceptance each revalidate.
- Historical databases contain First Slice deliveries without Dispatch rows:
  the additive migration preserves them as legacy proof and requires Dispatch
  binding for all newly created results.
- The one full aggregate observed a PostgreSQL deadlock in an unchanged Phase
  5 same-key Suite concurrency test. Its exact isolated rerun passed; this is
  recorded for independent Final Gate rather than expanding this slice into a
  Phase 5 concurrency remediation.

## Discoveries

- First Slice already exposes list/detail and deterministic commit proof, but
  `POST .../dispatch` has neither a request body nor `Idempotency-Key`.
- `DeliveryRepository.job()` returns only the latest Job and dispatch returns
  any existing Job, making terminal failure/cancellation permanently
  unrecoverable even while the Authorization remains fresh.
- `WorkspaceCheckpoint` already stores bounded changed paths, byte count, diff
  artifact, tree fingerprint, and diff hash, so preview requires no new source
  read or Runner capability.
- Runner Git plumbing is already deterministic and exact-ref idempotent because
  retries retain the Authorization creation timestamp and reject any differing
  existing ref.

## Verification

Exact commands, first failures, counts, exit codes, source invariance, Docker
projects, and cleanup will be recorded in
`docs/evidence/phase-6-governed-local-delivery-lifecycle-verification.md`.
Focused checks run before one final `make verify`, and the aggregate runs only
after the candidate has no known blocker.

## Rollback

Before the checkpoint, revert only this branch's reviewed patch. Migration
`20260801_0014` will be additive and reversible: downgrade removes only the
new Dispatch table/guards and restores First Slice transition/audit guards.
Never reset, clean, stash, delete a governed local ref, change a source
repository, or remove unrelated Docker state.

## Completion conditions

- Preview deterministically represents the exact immutable reviewed diff and
  explicit zero-remote operation.
- Dispatch without exact confirmation/key, stale authority, replay conflict,
  concurrent loser, invalid retry lineage, or exhausted budget creates no Job,
  Permit, ref, LocalDelivery, or success AuditEvent.
- Successful first attempt or safe retry stores one exact LocalDelivery bound
  to Dispatch, Job, Attempt, Permit, manifest, commit/tree/parent, and result
  digest; all terminal attempts remain visible.
- API/Protocol/Runner/Web, PostgreSQL migration, focused security, real browser,
  contracts/quality/build, source invariance, and required cleanup pass.
- One complete `make verify` runs only after focused closure. Any unrelated
  stopped gate remains explicit and is not rewritten as aggregate PASS; final
  diff is reviewed, one local checkpoint exists, and the worktree is clean.

## Outcome and follow-ups

`PHASE 6 SECOND SLICE IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT FOCUSED REVIEW`

The candidate's aggregate limitation is the unchanged Phase 5 concurrency
deadlock recorded above; the exact test passed in isolation. The next action
is an independent focused review of manifest integrity, concurrent dispatch,
terminal recovery, Permit fencing, deterministic ref replay, source
invariance, and zero-remote behavior. A third slice and every remote action
remain unauthorized.
