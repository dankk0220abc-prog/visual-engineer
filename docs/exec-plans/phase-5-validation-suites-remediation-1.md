# Phase 5 Validation Suites Targeted Remediation 1

- Started: 2026-07-30 +0800
- Repository: `/Users/danke/Developer/VisualEngineer`
- Main baseline: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Implementation candidate: `10399722e37f3209fa08e5e7edc25f31b429aaad`
- Focused-review FAIL checkpoint:
  `d325fa197e1fdad2c522fdf76f11b738682a86ca`
- Branch: `fix/phase-5-validation-suites-remediation-1`
- Status:
  `PHASE 5 SUITES TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`

## Goal

Close only `VE-P5-SUITES-FR-001` and `VE-P5-SUITES-FR-002`.
One approved Suite Grant must authorize exactly one Suite execution lineage,
and successful Suite aggregation must be reconstructed from exact ordered
current-lineage Validation Evidence rather than mutable Suite-step summaries.

The completion state is local implementer evidence:
`PHASE 5 SUITES TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`.
It is not a Security Gate PASS.

## Scope

Allowed changes are limited to:

- one additive Alembic migration and matching SQLAlchemy models;
- Suite Grant request/response and hashed policy bindings;
- Suite repository/service orchestration and trusted aggregation;
- generated OpenAPI/TypeScript contract artifacts;
- permanent API, migration, Protocol, Runner, and Web regressions required by
  the two Findings;
- the `/validations` retry flow needed to request lineage-bound authority;
- this ExecPlan, verification evidence, status, and directly affected
  architecture/security/runbook/governance documents.

## Non-goals

- Re-designing Phase 5 or reopening Phase 4/the sealed Phase 5 first slice.
- LLM, Provider, Customer 0, CreativeDeploy, non-zero artifacts, arbitrary
  command, package install, source/canonical Workspace mutation, Git delivery,
  deployment, or Phase 6.
- Remote, push, merge, pull request, tag, or main movement.
- Editing the historical focused-review FAIL report or weakening its tests.

## Constraints and safety

- All repository operations remain anchored at the exact Developer repository.
- Use only the unique Compose project
  `ve-p5-suites-remediation-1` or exact project-label filters.
- Preserve the original focused tests byte-for-byte.
- Add migration history; never edit `20260730_0008`.
- Keep Suite/Profile catalogs source-owned and command-free.
- A rejected path must not create a second Suite, child Validation Run, Job,
  Attempt, Lease, Permit, Result, Evidence, event, or budget charge.
- Stop for any Critical/High Finding, data damage, source/canonical Workspace
  mutation, unsafe residue, or required scope expansion.

## Finding matrix

| Finding               | Trusted state                                                                                     | Untrusted input/state                                                                          | Lock/transaction boundary                                                                 | Production repair                                                                                                      | Database invariant                                                                                                                                  | Regression                                                                                                                                         | Zero-success side effects                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `VE-P5-SUITES-FR-001` | immutable Suite definition, exact approved lineage-bound Grant, existing Suite row                | new idempotency key, concurrent root create, stale/revoked/expired/mismatched Grant            | lock exact Grant before consumption; unique Grant-to-Suite binding; lock root/retry rows  | bind Grant policy to Suite digest/root/source/attempt/one allowed Suite Run; reject Grant reuse; preserve exact replay | one Suite Run per Grant plus closed lineage/attempt checks                                                                                          | replay, different key, concurrency, old/new retry Grant, stale authority, late completion                                                          | unchanged Suite/step/Validation/Job/Attempt/Lease/Permit/Result/Evidence/event/charge counts |
| `VE-P5-SUITES-FR-002` | catalog order, Validation Run/Job/Attempt/Lease/Permit, immutable Evidence and recomputed digests | mutable step state/summaries and injected/foreign/missing/duplicate/reordered/stale references | lock Suite/steps and query exact execution rows before terminal Result/state/event commit | independently reconstruct ordered trusted step proofs and aggregate digest                                             | guarded legal step transitions; succeeded step requires exact successful execution/Evidence; succeeded Suite/Result requires complete ordered proof | zero/missing/foreign/duplicate/reordered/stale Evidence, step injection, binding mismatch, failed states, legal success, replay, terminal mutation | no succeeded Suite Result/event/Permit completion/new Evidence/charge/dispatch on rejection  |

## Current progress

- done — exact Git/root/branch/main/checkpoint/ancestry/ref/cleanliness
  preflight; no remote, stash, tag, lock, or other worktree
- done — branch created directly from the exact focused-review checkpoint
- done — original review, evidence, ExecPlan, status, implementation plan and
  evidence, models, migration, API, service, repository, Runner Protocol,
  state machine, permissions, threat model, ADR, runbook, and tests inspected
- done — original audit file hash recorded
- done — first unchanged real-PostgreSQL reproduction: `2 failed`, exit `1`
- done — two unchanged focused reruns per Finding; each Finding is stable
  `3/3`, exit `1` each
- done — additive schema, lineage policy, trusted aggregation, browser retry
  binding, generated contract, and permanent regression implementation
- done — unchanged Findings pass `2/2`; original controls and permanent
  PostgreSQL lineage/Evidence/concurrency matrix pass
- done — focused Protocol/Runner `12/12`, Web `47/47`, Web typecheck/build,
  migration downgrade/re-upgrade, strict Ruff/mypy, and contract drift pass
- done — full backend `147/147`, E2E `16/16`, Chaos, Security `111/111`,
  Eval 67, source/canonical invariance, and exact filtered cleanup
- done — first final aggregate preserved an external `ghcr.io` token-fetch
  `EOF` after all gates before E2E; no product test failed
- done — the single allowed full rerun reused completed-source local images
  and passed `make verify`: Python `248/248` at `83.27%`, Web `47/47`, E2E
  `16/16`, Chaos, Security `111/111`, Eval 67, migration, contracts, build,
  invariance, and final diff check
- done — exact filtered Docker cleanup, audit hash/ref reconciliation,
  documentation/evidence closeout, exact diff review, and one local checkpoint

## Decisions

1. A Suite-scoped Grant is single-use at the Suite lineage boundary even when
   child Validation budget remains. Database uniqueness is authoritative;
   service checks provide a stable typed response.
2. A retry Grant is created for one explicit terminal source Suite Run. The
   server derives and policy-hashes root lineage, retry source, next attempt,
   immutable Suite definition digest, and allowed Suite Run count.
3. Successful aggregation does not consume persisted step summaries as proof.
   It re-queries and validates catalog definition, Suite lineage, Validation
   Run, Job, Attempt, Lease, Grant, Permit, Evidence, cleanup, budgets, and
   digests in ordered form under lock.
4. Database triggers remain a second enforcement layer for legal transitions
   and successful Suite/Result insertion. Historical migration `0008` remains
   unchanged.

## Discoveries

- Root create currently locks the Grant only for validity and has no
  Grant-consumption lookup or uniqueness constraint.
- Suite Grant policy hashing currently excludes Suite identity and lineage.
- Suite Grant child-run budget is `max_attempts * step_count`, allowing a
  reused root Grant to dispatch additional children.
- The step trigger protects definition and terminal immutability but has no
  legal nonterminal transition matrix or successful Evidence requirement.
- Aggregate success currently accepts all persisted steps marked
  `succeeded`, while `evidence_id` is optional.
- A real two-session test must close the fixture Session transaction before
  worker Sessions start; otherwise PostgreSQL correctly waits on setup-owned
  row locks rather than exercising the intended production race.
- Retry aggregates must retain the original child Grant in reused Evidence
  references, while the retry Suite Result separately binds the fresh retry
  Grant.
- Null-safe database proof comparison requires `IS DISTINCT FROM`; ordinary
  `<>` can let missing JSON fields evaluate to SQL unknown.

## Risks

- A cyclic Grant/Suite lineage reference can complicate downgrade. Mitigation:
  add nullable retry-lineage Grant references only after Suite tables exist,
  then drop those constraints/columns first on downgrade.
- Concurrent exact replay and conflicting Grant reuse can race. Mitigation:
  lock the exact Grant, recheck idempotency after the lock, and retain a unique
  database constraint.
- Retry Evidence reuse must remain legal without treating the new Grant as the
  original child Grant. Mitigation: require an exact trusted source step in
  the same root lineage and preserve its immutable original execution proof.
- Database success guards can drift from service logic. Mitigation: permanent
  direct-SQL negative tests plus legal two-step and retry controls.

## Verification

The ordered verification ledger, commands, exit codes, test counts, coverage,
first failures, migration/contract results, filtered Docker cleanup, and
source/canonical Workspace digests are maintained in
`docs/evidence/phase-5-validation-suites-remediation-1-verification.md`.

The final aggregate is run once only after all focused gates pass. A genuine
first aggregate failure is preserved and repaired narrowly; at most one final
aggregate rerun is allowed.

## Rollback

Stop and remove only the exact remediation Compose project and its project
volumes. Revert only reviewed uncommitted remediation patches if required.
Do not reset, clean, stash, force, rewrite history, edit historical migrations,
or touch source/canonical Workspace state.

## Completion conditions

- Both unchanged focused-review tests pass.
- All lineage, aggregation, transition, retry/cancel/race, budget, cleanup,
  invariance, migration, contract, Runner, Web, E2E, Security, Eval, Chaos,
  Docker, formatting, lint, type, build, and aggregate gates pass.
- Final `make verify` exits `0`.
- `main`, implementation, and audit refs remain unchanged.
- The exact audit test hash is unchanged.
- One local commit uses
  `fix(validation): enforce suite grant lineage and trusted aggregation`.
- Worktree, index, and untracked inventory are clean after the checkpoint.

## Outcome and follow-ups

`PHASE 5 SUITES TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`.

The two scoped Findings are closed by current local implementer evidence.
The first final aggregate's only failure was an external `ghcr.io` token-fetch
`EOF`; the one permitted full rerun exited `0` using completed-source local
images. There are no new Critical or High Findings and no required scope
expansion. Historical review decisions remain unchanged. The final checkpoint
hash is supplied in the handoff after commit creation; the next milestone is a
fresh independent focused re-audit of only the two repaired Findings.
