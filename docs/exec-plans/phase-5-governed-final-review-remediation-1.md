# Phase 5 governed final review targeted remediation 1

## Goal

Close only `VE-P5-REVIEW-FR-001` through `VE-P5-REVIEW-FR-005` by making
Review Package freshness, canonical digest reconstruction, Decision
idempotency/generation fencing, review AuditEvent immutability, and zero
blocking-Finding readiness independently enforceable by PostgreSQL and the
Control Plane. Preserve the independent focused-review FAIL and its unchanged
security tests. The completed candidate may be handed to a fresh independent
focused re-review; this implementer cannot declare Gate PASS.

## Scope

- Add one reversible Alembic migration after `20260730_0010`.
- Extend Review Package, Decision, readiness, freshness, blocker-summary, and
  review-event persistence without rewriting historical migrations.
- Reconstruct package, manifest, Decision, blocker-summary, and readiness
  digests from trusted PostgreSQL facts.
- Add keyed Decision idempotency and optimistic generation fencing.
- Invalidate old packages when later validation, Evidence, policy, Grant,
  revision, tree/diff, or blocker facts change.
- Update the Review API, generated OpenAPI/TypeScript contract, `/reviews`
  workflow, permanent regressions, architecture/security/runbook/status
  documents, and verification evidence.

## Non-goals

- Redesigning the Third Slice or re-reviewing Phase 4 or earlier Phase 5
  slices.
- LLMs, Providers, Agents SDK, Customer 0, CreativeDeploy, production
  credentials, public deployment, or hostile multi-tenant hardening.
- Git commit/push/pull-request/merge/tag delivery authority or a delivery
  Grant.
- Main integration, remote delivery, sealing, or a Gate PASS decision.

## Constraints and safety

- Operate only in `/Users/danke/Developer/VisualEngineer`.
- Baseline is audit checkpoint
  `5371495b1dd27db2ff3bbca4ddc12eaee47e7982`; local `main` must remain
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`.
- The historical focused-review report and assertions remain unchanged.
- All reject paths must leave zero approved Decision, effective ready verdict,
  readiness-success event, delivery Grant, Git action, duplicate event,
  Workspace/source/Evidence mutation, and duplicate charge.
- Stop for a new Critical/High, data damage, unpreventable stale approval,
  unprovable Evidence/readiness, mutable review history, or required expansion
  into a prohibited capability.
- Use task-owned PostgreSQL/E2E/Chaos projects and remove only their exact
  resources. Never stop an unknown port owner.

## Current progress

- 2026-07-30 CST — **done**: exact repository, Git refs, ancestry, checkpoint
  scope, clean worktree/index/untracked state, absent remote/stash/tag/locks,
  and absent remediation branch verified.
- 2026-07-30 CST — **done**: remediation branch created from exact audit
  checkpoint.
- 2026-07-30 CST — **done**: focused report/evidence/plan, Third Slice
  plan/evidence, status, ADR, models, migration, service, API, trusted Suite
  reconstruction, tests, contracts, and Web workflow inspected.
- 2026-07-30 CST — **done**: unchanged independent audit reproduction run
  against task-owned PostgreSQL; exit `1`, `4 failed, 2 passed`.
- 2026-07-30 CST — **done**: additive migration, schema-v2 Package,
  freshness/blocker state, server/database canonical digest reconstruction,
  sequenced append-only review events, expected-generation keyed Decision,
  readiness zero-blocker proof, API/contracts/Web, and permanent regressions.
- 2026-07-30 CST — **done**: focused `20/20`, migration roundtrip, API
  `272/272` at `83.43%`, Web `50/50`, build, desktop+390px Playwright/axe
  `16/16`, Security/Eval/invariance/chaos, and exact task-project cleanup.
- 2026-07-30 CST — **done**: the one permitted final `make verify` aggregate
  exited `0` without a rerun; evidence closeout and exact task-project cleanup
  completed.
- 2026-07-30 CST — **done**: one local checkpoint with the required subject
  and final clean-state verification.

## Repair matrix

| Finding  | Trusted source                                                                                                               | Current gap                                                 | Transaction/locking boundary                                                                          | Database invariant                                                                                                                         | Production repair                                                                            | Permanent regression                                                                                                 | Zero-success-side-effect proof                                                                                      |
| -------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `FR-001` | exact validation/Suite/Evidence/Grant/Workspace/Checkpoint scope generation                                                  | later negative or changed facts do not stale old ready      | lock package plus freshness scope; fact change advances scope and invalidates in the same transaction | old generation cannot receive approve/ready; immutable old decision remains historical                                                     | explicit generation plus automatic invalidation/effective-stale derivation                   | rerun/failure/Evidence/checkpoint/policy/Grant/blocker changes                                                       | denied stale approve has no new decision, ready row/event, delivery authority, Workspace/Evidence change, or charge |
| `FR-002` | locked Suite Result plus reconstructed ordered Evidence and PostgreSQL canonical-digest functions                            | digest shape/bindings are checked, canonical values are not | package/decision/readiness insert guards lock exact source rows                                       | manifest/package/decision/readiness digests must equal database recomputation; zero/missing/foreign/duplicate/reordered Evidence is denied | complete manifest/package payload and canonical server/database digest chain                 | forged package/result/manifest/readiness summaries plus legal package                                                | first forged insert fails; no later decision/readiness/event can exist                                              |
| `FR-003` | review AuditEvent package binding and monotonically allocated package sequence                                               | `audit_events` accepts update/delete                        | package lock serializes sequence allocation; freshness trigger uses the same scope/package locks      | review event binding/sequence is unique and all AuditEvents reject update/delete                                                           | add review package/sequence fields, insert guard, unique index, append-only trigger          | direct UPDATE/DELETE, replay, order, old/new package separation                                                      | exact replay adds no event; mutation attempts change no event bytes/count                                           |
| `FR-004` | immutable package version/generation/digest/policy plus normalized Decision payload                                          | no expected generation or independent keyed request hash    | package and freshness scope locks precede idempotency lookup and one-winner insert                    | unique Decision key; same key requires same hash; one terminal decision per package; current generation required                           | persisted expected generation, key, request hash, policy and Decision digest                 | exact replay, key conflict, mismatch/stale generation, concurrent approve/reject, terminal mutation, old/new package | losing/conflicting request adds no decision or event and cannot alter winner                                        |
| `FR-005` | immutable server-derived blocker summary over append-only scoped Finding facts and trusted result/Evidence/policy/generation | readiness assumes security blockers are zero                | package locks scope and blocker facts; readiness rechecks frozen summary under the same transaction   | ready requires present/matching summary and Critical/High/blocking-Medium counts all zero                                                  | versioned blocker source, counts/digest on package/readiness, automatic stale on new blocker | each nonzero/missing/mismatch case plus legitimate all-zero package                                                  | denied ready creates no effective ready row/event or delivery authority                                             |

## Decisions

- Keep Review rows immutable. Freshness changes create a separate invalidation
  and advance a scope generation; historical decisions and verdicts are never
  rewritten.
- Use database canonical JSON digest functions as the shared source for values
  that PostgreSQL must independently verify.
- Store a frozen blocker summary on each package. It is derived only from
  append-only system-owned scoped Finding facts; Review API callers cannot
  provide counts.
- Retain compatibility for historical callers that omit a Decision
  idempotency header by binding a generated request key, while explicit keyed
  calls receive exact-key/exact-payload replay semantics.
- Permit multiple package generations for a Suite Result but at most one
  package for the same Suite Result and freshness generation.

## Risks

- Broad freshness triggers could invalidate on unrelated facts. Mitigation:
  resolve and compare exact Plan/Workspace/Checkpoint scope before advancing.
- Canonical JSON differences between Python and PostgreSQL could split digest
  semantics. Mitigation: generate security-bound digests through one
  PostgreSQL function and test direct SQL forgery.
- Audit sequencing can race with approve/readiness/freshness. Mitigation:
  allocate sequence only while the package or scope is locked and enforce a
  partial unique index.
- Existing test fixtures truncate an explicit table list. Mitigation: extend
  each affected list without `CASCADE` and retain independent FK checks.
- Legacy review rows are protected by immutable triggers. Mitigation: disable
  only the exact three legacy review triggers inside the transactional
  backfill, rebuild Decision/readiness digests, conservatively invalidate v1
  Packages, and re-enable protection before migration completion.

## Discoveries

- The original package guard validates many identities but only digest shape;
  its package payload also omits generation, policy, Grant lineage,
  Checkpoint diff digest, and blocker proof.
- Freshness chooses the latest successful Suite Result and therefore ignores a
  later failed fixed-Profile Validation on the same baseline.
- Existing application approve/reject concurrency has one winner, but there is
  no persisted keyed replay contract or expected-generation field.
- Review table immutability does not include the shared `audit_events` table.
- No trusted security-blocker summary is representable in the candidate.
- Empty-database roundtrip alone cannot exercise legacy immutable-row
  backfill. Static migration review found and corrected the exact trigger
  window and legacy verdict-digest rebinding before final verification.
- Source policy and Validation Evidence are already immutable. Replacement
  attempts therefore fail at the source boundary; any accepted new
  validation/Evidence fact advances the freshness scope.

## Verification

- Pre-repair independent audit:
  `TEST_DATABASE_URL=... uv run pytest apps/api/tests/test_phase5_governed_final_review_focused_audit.py --no-cov -q`;
  exit `1`, `4 failed, 2 passed`.
- Focused candidate + unchanged audit + permanent remediation:
  exit `0`, `20 passed`.
- Real PostgreSQL migration `base -> head -> base -> head`: exit `0`.
- Complete API/Runner/Protocol: exit `0`, `272 passed`, coverage `83.43%`.
- Web: exit `0`, `50 passed`; production build and contracts pass.
- Real browser desktop + 390px with axe: exit `0`, `16 passed`; fixture and
  canonical Workspace HEAD/status/tree remain unchanged.
- Security, `74` deterministic Eval cases, source invariance, Workspace chaos,
  and exact task-project cleanup: pass.
- Final `make verify`: exit `0` on the single permitted run; no rerun.

Exact commands, first failures, fixes, counts, coverage, and zero-side-effect
evidence are recorded in
[`docs/evidence/phase-5-governed-final-review-remediation-1-verification.md`](../evidence/phase-5-governed-final-review-remediation-1-verification.md).

## Rollback

Stop and remove only task-owned Compose projects. Before the checkpoint,
reverse only this plan's additive migration/files and scoped edits; do not
reset, clean, stash, or modify unrelated history. Migration downgrade removes
only remediation triggers/functions/indexes/columns/tables and restores the
`20260730_0010` constraints.

## Completion conditions

- All unchanged independent audit tests pass.
- Permanent freshness/digest/Decision/audit/readiness matrices pass against
  real PostgreSQL.
- Migration upgrade/downgrade/re-upgrade, generated contracts, Web/browser,
  accessibility, source/canonical Workspace invariance, Security, Eval,
  Docker cleanup, and final `make verify` exit `0`.
- Local `main` and implementation/audit refs are unchanged; no remote, push,
  merge, pull request, tag, CreativeDeploy, Customer 0, or delivery authority
  is used.
- One local commit has subject
  `fix(review): enforce freshness and readiness integrity`, and the final
  worktree/index/untracked inventory is clean.

## Outcome and follow-ups

**COMPLETED.** The successful completion label is
`PHASE 5 FINAL REVIEW TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-REVIEW`.
It is not Gate PASS, sealing, main integration, or later-phase authorization.
