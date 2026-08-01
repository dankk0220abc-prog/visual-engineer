# Project Status

- Phase: Phase 7 First Vertical Slice — Governed AI Planning with
  Deterministic Provider
- Overall status: `FINAL_GATE_PASS_SEALING_PREPARED`
- Governance qualifier: INDEPENDENT FINAL GATE PASS; FIXTURE-ONLY LOCAL SEAL;
  MAIN FAST-FORWARD REQUIRES EXPLICIT USER AUTHORIZATION
- Last updated: 2026-08-02
- Current local `main`: `9c282e91a42a87ea553171d5aa55a0f77564bb14`
- Reviewed candidate: `8003c835284343be8c4046f868ec6d1f66369cef`
- Final audit branch: `codex/audit-governed-ai-planning-final-20260802`
- Final-gate Plan:
  [`phase-7-governed-ai-planning-first-slice-final-gate.md`](../exec-plans/phase-7-governed-ai-planning-first-slice-final-gate.md)
- ADR: [`ADR 0021`](../adr/0021-governed-ai-plan-handoff.md)
- Final-gate Evidence:
  [`phase-7-governed-ai-planning-first-slice-final-gate-verification.md`](../evidence/phase-7-governed-ai-planning-first-slice-final-gate-verification.md)
- Final audit:
  [`phase-7-governed-ai-planning-first-slice-final-gate.md`](../security/audits/phase-7-governed-ai-planning-first-slice-final-gate.md)
- Scope: bounded committed-Snapshot context, versioned Prompt, strict typed
  Provider request/response, exact generation and repository-fact grounding,
  deterministic fake replay, twelve system-owned Evals, freshness, human
  approve/reject, and authority-free Plan handoff.
- Finding: `VE-P7-AIP-FR-001 PASS`; the permanent consistent-tamper regression
  fails binding and grounding while replay remains deterministic.
- Independent focused results: original Finding `1/1`, complete AI
  Eval/PostgreSQL `34/34`, prompt-injection scanner `1/1`, Web blocked state
  `1/1`, desktop+narrow real stack `2/2`, Eval manifest `94` cases, secret
  scan, source invariance, format, lint, typecheck, and diff checks PASS.
- Explicit denials: real Provider SDK/network/key/billing, CreativeDeploy,
  Customer 0, real repository, broader Runner permission, arbitrary shell,
  Execution Grant auto-issue, Review/Delivery auto-approval, remote Git, push,
  PR, merge, tag, and deployment.
- Fresh aggregate: exactly one `make verify`, exit `0`; Python `351/351` at
  `84.32%` coverage, Web `61/61` at `71.49%` function coverage, Playwright
  `20/20`, Migration, Security, Workspace Chaos, Eval, source invariance, and
  final diff PASS.
- Docker cleanup: all focused and aggregate project containers, networks, and
  volumes are zero; unique focused image tags removed; pre-existing aggregate
  image-tag namespaces retained.
- Reviewer scope: only final-gate Evidence, ExecPlan, audit report, and this
  Project Status changed; production code, existing tests, and historical FAIL
  artifacts remain unchanged.
- Sealing subject: `chore: seal governed ai planning first slice`; exact hash
  is reported in the post-commit handoff.
- Next action: wait for explicit user authorization before any local
  fast-forward of `main`.

`GOVERNED AI PLANNING FIRST SLICE FINAL GATE PASS — SEALED AND AWAITING EXPLICIT USER AUTHORIZATION FOR LOCAL FAST-FORWARD MAIN`

## Preserved Phase 6 completion

Phase 0-6 First and Second Slices are integrated in local `main` at
`9c282e91a42a87ea553171d5aa55a0f77564bb14`. The Phase 6 final seal is
`chore: seal phase 6 governed delivery lifecycle`, with parent candidate
`fd132832b394927b7d00c188a895bf7b5b5e6ce4`. Historical independent evidence,
findings, remediation, and final-gate PASS remain preserved and are not
reopened or counted as Phase 7 review.

## Preserved Phase 5 completion

Phase 0–5 are integrated in local `main` at
`962b72ec92329de929ca5f9381b5324a68a18dde`. The historical Phase 5
independent reviews, remediation records, and local seals below remain
unchanged and do not count as Phase 6 approval.

- Final independent re-review branch:
  `audit/phase-5-review-revision-freshness-final-rereview`
- Final independent re-review candidate:
  `7450d4665d682db808692347860a602809bfa080`
- Final independent re-review plan:
  [`docs/exec-plans/phase-5-review-revision-freshness-final-rereview.md`](../exec-plans/phase-5-review-revision-freshness-final-rereview.md)
- Final independent re-review evidence:
  [`docs/evidence/phase-5-review-revision-freshness-final-rereview-verification.md`](../evidence/phase-5-review-revision-freshness-final-rereview-verification.md)
- Local sealing subject:
  `chore: seal phase 5 governed final review`
- Local sealing hash: reported in the post-commit handoff
- Current final narrow remediation branch:
  `fix/phase-5-review-revision-freshness-remediation-3`
- Final narrow remediation base / independent FAIL checkpoint:
  `a1dd0a9b68c73a45e4aa8b8754e51c385f3bad95`
- Final narrow remediation plan:
  [`docs/exec-plans/phase-5-review-revision-freshness-remediation-3.md`](../exec-plans/phase-5-review-revision-freshness-remediation-3.md)
- Final narrow remediation evidence:
  [`docs/evidence/phase-5-review-revision-freshness-remediation-3-verification.md`](../evidence/phase-5-review-revision-freshness-remediation-3-verification.md)
- Current independent single-Finding re-review branch:
  `audit/phase-5-review-revision-freshness-single-finding-rereview`
- Reviewed revision-freshness candidate:
  `efeecda57109ff8c3470f83a2aeb659e7ead31be`
- Independent single-Finding re-review plan:
  [`docs/exec-plans/phase-5-review-revision-freshness-single-finding-rereview.md`](../exec-plans/phase-5-review-revision-freshness-single-finding-rereview.md)
- Independent single-Finding audit:
  [`docs/security/audits/phase-5-review-revision-freshness-single-finding-rereview.md`](../security/audits/phase-5-review-revision-freshness-single-finding-rereview.md)
- Independent single-Finding evidence:
  [`docs/evidence/phase-5-review-revision-freshness-single-finding-rereview-verification.md`](../evidence/phase-5-review-revision-freshness-single-finding-rereview-verification.md)
- Current revision-freshness remediation branch:
  `fix/phase-5-review-revision-freshness-remediation-2`
- Revision-freshness remediation base / independent FAIL checkpoint:
  `cce04d460a40416bc01f6ca2b44ee71948775c88`
- Revision-freshness remediation plan:
  [`docs/exec-plans/phase-5-review-revision-freshness-remediation-2.md`](../exec-plans/phase-5-review-revision-freshness-remediation-2.md)
- Revision-freshness remediation evidence:
  [`docs/evidence/phase-5-review-revision-freshness-remediation-2-verification.md`](../evidence/phase-5-review-revision-freshness-remediation-2-verification.md)
- Current focused re-review branch:
  `audit/phase-5-governed-final-review-reaudit-max`
- Reviewed remediation candidate:
  `3eddb9623550227a30013df6dbc6dc7a17d5315c`
- Focused re-review Finding:
  `VE-P5-REVIEW-RR-001` — blocking Medium
- Current focused-review branch:
  `audit/phase-5-governed-final-review-focused-max`
- Reviewed Third Slice candidate:
  `c2054469c8d10441bcab8ade89c52de1f9aa893f`
- Third Slice focused Findings:
  `VE-P5-REVIEW-FR-001` through `VE-P5-REVIEW-FR-005` — blocking Medium
- Third Slice remediation branch:
  `fix/phase-5-governed-final-review-remediation-1`
- Third Slice remediation base:
  `5371495b1dd27db2ff3bbca4ddc12eaee47e7982`
- Preserved independent re-review plan:
  [`docs/exec-plans/phase-5-governed-final-review-focused-rereview.md`](../exec-plans/phase-5-governed-final-review-focused-rereview.md)
- Phase 5 second-slice remediation branch:
  `fix/phase-5-validation-suites-remediation-1`
- Phase 5 second-slice remediation candidate:
  `b6d53ba0275933e18919ceb2d90152e5ae8efcac`
- Phase 5 second-slice remediation base:
  `d325fa197e1fdad2c522fdf76f11b738682a86ca`
- Phase 5 second-slice focused-review branch:
  `audit/phase-5-validation-suites-focused-max`
- Phase 5 second-slice reviewed candidate:
  `10399722e37f3209fa08e5e7edc25f31b429aaad`
- Phase 5 second-slice focused Findings:
  `VE-P5-SUITES-FR-001`, `VE-P5-SUITES-FR-002` — blocking Medium
- Phase 5 single-finding re-audit branch:
  `audit/phase-5-cancel-permit-single-finding-max`
- Phase 5 single-finding re-audit candidate:
  `c9e5268f1287f49ac0ba5c5d26045395b8e72dc0`
- Phase 5 aggregate-environment FAIL checkpoint:
  `61151bd7f2fe68f8076af45dfec9977858f51e04`
- Phase 5 final targeted remediation 2 branch:
  `fix/phase-5-validation-cancel-permit-remediation-2`
- Phase 5 final targeted remediation 2 base:
  `4ce5a1a8e63ec530517f17ae82fc3aeb7747c4de`
- Phase 5 focused re-audit branch:
  `audit/phase-5-validation-remediation-focused-max`
- Phase 5 focused re-audit candidate:
  `8ca5c9ef99ac2bfe6ce88916ca3b3b16671ce5f9`
- Phase 5 focused re-audit Finding:
  `VE-P5-FREAUD-001` — successful active Validation cancellation leaves the
  consumed Permit open
- Phase 5 remediation branch:
  `fix/phase-5-governed-validation-remediation-1`
- Phase 5 remediation base:
  `cd980582e9d950cb0176eae46ffaedd528ce0afe`
- Phase 5 focused-review branch:
  `audit/phase-5-governed-validation-focused-max`
- Phase 5 reviewed candidate:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Final integration branch: `integration/phase-4-final-gate`
- Final integration baseline:
  `38afe4b0c8eefa4c34b58e0b9d30cb74ca931501`
- Budget re-audit branch: `audit/phase-4-manifest-budget-reaudit-max`
- Independently audited Round 4 candidate:
  `03f774827afbafd7f0eb991f5abf2c6fee66cd17`
- Round 4 branch: `fix/phase-4-security-remediation-4`
- Round 4 base / single-finding audit:
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8`
- Single-finding audit branch:
  `audit/phase-4-replacement-single-finding-max`
- Audited Round 3 candidate:
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`
- Round 3 branch: `fix/phase-4-security-remediation-3`
- Round 3 base / focused re-audit checkpoint:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`
- Focused re-audit branch: `audit/phase-4-security-focused-reaudit-max`
- Focused candidate:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`
- Round 2 branch: `fix/phase-4-security-remediation-2`
- Round 2 base / independent re-audit:
  `b457b614bde6630fb50ff9546c92a4d6925ad38a`
- Re-audit branch: `audit/phase-4-security-reaudit-max`
- Re-audited repair commit:
  `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c`
- Repair branch: `fix/phase-4-security-remediation`
- Repair base / audit commit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4 implementation:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main: `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Remote: none
- Remote CI: not run

## Phase 5 Third Slice final independent re-review and seal

`VE-P5-REVIEW-RR-001` is **PASS** at exact candidate
`7450d4665d682db808692347860a602809bfa080`.

The byte-unchanged independent file has SHA-256 `438acf30...` and passes
`11/11`. A deterministic supporting concurrency test observes the second
transaction in PostgreSQL `Lock/advisory` wait. For two identical trusted
revision registrations:

- both inputs and both returned revisions are identical;
- both callers observe final generation `2`;
- persisted generation is exact `1 -> 2`, never `3`;
- invalidation and invalidation AuditEvent counts are `1 / 1`; and
- historical Decision/readiness remain immutable while effective readiness
  becomes stale.

Two different concurrent revisions remain distinct transitions and finish at
generation `3`. Sequential same-revision replay advances only once.
Approve-first and revision-first orderings pass with real advisory waits.
Forced failure rolls revision, generation, invalidation, and AuditEvent back
together. Stale direct Decision/readiness writes, old-generation keyed replay,
and AuditEvent update/delete remain fail closed.

Current independent verification:

- remediation-3 concurrent identical/different cases: `2/2`;
- original Finding/remediation matrix: `8/8`;
- unchanged independent single-Finding file: `11/11`;
- focused Review matrix: `28/28`;
- affected Workspace/Validation matrix: `37/37`;
- populated and clean migration roundtrips plus migration pytest: pass;
- contracts, format, lint, typecheck, build, source invariance, and
  `git diff --check`: pass;
- exactly one complete `make verify`: exit `0`, including Backend/Runner/
  Protocol `293/293`, Web `50/50`, and Playwright `16/16`; and
- exact audit, E2E, and Chaos project cleanup: zero containers, networks, and
  volumes, with cleanup replay and final port bind probes passing.

The reviewer changed no production code and preserved the earlier independent
FAIL artifacts. Main remains
`50dcc05ce48d042882bcdf199ae1bee662a83af6`. No remote, push, pull request,
merge, tag, deployment, delivery, CreativeDeploy, Customer 0, later slice, or
Phase 6 action occurred.

Detailed final artifacts:

- [`docs/exec-plans/phase-5-review-revision-freshness-final-rereview.md`](../exec-plans/phase-5-review-revision-freshness-final-rereview.md)
- [`docs/evidence/phase-5-review-revision-freshness-final-rereview-verification.md`](../evidence/phase-5-review-revision-freshness-final-rereview-verification.md)

`PHASE 5 THIRD SLICE FINAL GATE PASS — SEALED AND AWAITING EXPLICIT USER AUTHORIZATION FOR LOCAL FAST-FORWARD MAIN`

## Phase 5 Review revision-freshness final narrow remediation 3

The production implementer has closed only the concurrent identical-revision
replay defect within `VE-P5-REVIEW-RR-001`. The trusted registration path
retains its existing PostgreSQL transaction-level advisory lock and Handle
row lock, but its locked query now forces a reload of the already-loaded
SQLAlchemy identity. A waiting transaction therefore compares the committed
post-lock revision instead of the pre-wait ORM attribute.

The unchanged independent concurrent reproduction first failed before repair
with generation `1 -> 3`, two equal returned revisions, one invalidation, one
AuditEvent, and zero Decision/ready rows. After the one-line production
repair, that unchanged test passes with exact generation `1 -> 2`.

An additive permanent `2/2` regression observes PostgreSQL
`Lock/advisory`: identical concurrent callers both return the same revision
and observe generation `2`; different concurrent revisions remain two real
transitions and finish at generation `3`. Historical ready remains immutable
but effectively stale, invalidation/AuditEvent remain `1/1`, no duplicate
ready or blocker summary appears, and no generation gap remains.

Current implementer verification:

- original Finding plus remediation-2 matrix: `8/8`;
- unchanged independent single-Finding file: `11/11`;
- focused Review and `FR-002`/`FR-003`/`FR-004`/`FR-005`: `28/28`;
- affected Workspace/Validation: `37/37`;
- forced rollback, stale direct Decision/readiness fencing, keyed replay,
  approve-first/revision-first lock order, and append-only AuditEvent: pass;
- populated `0012 -> 0011 -> 0012`, clean
  `base -> head -> base -> head`, one migration head, and migration pytest:
  pass;
- contracts, format, lint, Python/TypeScript typecheck, Web production build,
  and source invariance: pass; and
- exact task Compose cleanup: zero containers, networks, and volumes; cleanup
  replay succeeds and the task port is free.

No migration or contract changed. Full `make verify`, final aggregate, E2E,
Chaos, broad Security/Eval, sealing, and main integration were not run.
Detailed implementer artifacts:

- [`docs/exec-plans/phase-5-review-revision-freshness-remediation-3.md`](../exec-plans/phase-5-review-revision-freshness-remediation-3.md)
- [`docs/evidence/phase-5-review-revision-freshness-remediation-3-verification.md`](../evidence/phase-5-review-revision-freshness-remediation-3-verification.md)

This implementer result is ready only for a fresh independent single-Finding
re-review after the exact local checkpoint. It is not Security Gate PASS,
sealing, main integration, delivery, or later-phase authorization.

## Phase 5 Review revision-freshness independent single-Finding re-review

`VE-P5-REVIEW-RR-001` remains **FAIL / REMEDIATION REQUIRED** at candidate
`efeecda57109ff8c3470f83a2aeb659e7ead31be`.

The exact Git/candidate preflight passed, historical FAIL evidence and the
original independent test remain byte-identical, and the unchanged original
Finding plus permanent remediation matrix passes `8/8`. The candidate
successfully fences stale direct approve/reject/readiness writes, rejects
`changes_requested`, rolls back revision/generation/invalidation/event
together, invalidates historical ready state after one trusted revision
change, and serializes both approve-first and revision-first transaction
orders.

The independent final matrix is `10 passed, 1 failed`. The sole failure
deterministically synchronizes two trusted transactions at the production
initial Handle lookup, then submits the same new revision. Both registrations
return that revision, but the freshness generation advances from `1` to `3`
instead of `2`. Invalidation and invalidation AuditEvent counts remain
`1 / 1`, and Decision/ready counts remain `0 / 0`. The same secure assertion
failed in two focused invocations and again in the final matrix.

This violates the required replay idempotency and no-generation-gap
invariants. The blocker stop applies: the `28/28` Review matrix, `37/37`
Workspace/Validation matrix, dynamic migration roundtrips, final
`make verify`, E2E/accessibility, Security/Eval/Chaos, Final Gate cleanup
probe, and sealing were **NOT RUN**.

Only the exact audit-owned PostgreSQL project was removed. Its filtered
container/network/volume inventories are empty, cleanup replay succeeds, and
port `62941` is free. Production code remains unchanged from the candidate.
Main remains `50dcc05ce48d042882bcdf199ae1bee662a83af6`. No remote, push, pull
request, merge, tag, deployment, CreativeDeploy, sibling repository, Customer
0, later slice, or Phase 6 action occurred.

Detailed independent artifacts:

- [`docs/exec-plans/phase-5-review-revision-freshness-single-finding-rereview.md`](../exec-plans/phase-5-review-revision-freshness-single-finding-rereview.md)
- [`docs/security/audits/phase-5-review-revision-freshness-single-finding-rereview.md`](../security/audits/phase-5-review-revision-freshness-single-finding-rereview.md)
- [`docs/evidence/phase-5-review-revision-freshness-single-finding-rereview-verification.md`](../evidence/phase-5-review-revision-freshness-single-finding-rereview-verification.md)

## Phase 5 Review revision-freshness targeted remediation 2

The implementer candidate reported `VE-P5-REVIEW-RR-001` closed and ready for
independent single-Finding re-review. The later independent decision above is
the governing result; this section remains preserved implementer history.

The sole trusted Repository Handle revision writer is the authenticated Runner
registration transaction. It now acquires a shared PostgreSQL
revision-authority mutex and Handle row lock, persists the revision/status
change, advances every affected freshness scope, invalidates old Packages and
effective readiness, and appends the immutable invalidation AuditEvent before
one commit. Decision and readiness paths acquire the same mutex, lock the
trusted Handle, revalidate the frozen revision and current generation before
write, and revalidate generation/freshness before an exact keyed replay.
Additive database insert guards reject a stale direct approve/reject or ready
row even after an out-of-band Handle table update.

Current implementer verification:

- unchanged independent Finding plus permanent regression matrix: `8/8`;
- focused Review API and `FR-002`/`FR-003`/`FR-004`/`FR-005` non-regression:
  `28/28`;
- affected Workspace/Validation API tests: `37/37`;
- clean migration pytest: `1/1`;
- populated `0012 -> 0011 -> 0012` and clean
  `base -> head -> base -> head`: pass;
- contracts, lint, Python/TypeScript typecheck, Web build, source invariance,
  formatting, and `git diff --check`: pass; and
- source invariance compares `119` entries, `10` Git objects, and `2` status
  records with status `PASS`.

No full `make verify`, full E2E, Chaos, Security, Eval, browser expansion, or
final aggregate was run in this remediation. No API schema or HTTP contract
changed. `changes_requested` remains outside the closed Third Slice terminal
Decision domain and is rejected with `422`; approve/reject remain the only
terminal Decisions. Approval and readiness still create no Git, pull-request,
merge, tag, deployment, command, or later-phase authority.

Detailed implementer artifacts:

- [`docs/exec-plans/phase-5-review-revision-freshness-remediation-2.md`](../exec-plans/phase-5-review-revision-freshness-remediation-2.md)
- [`docs/evidence/phase-5-review-revision-freshness-remediation-2-verification.md`](../evidence/phase-5-review-revision-freshness-remediation-2-verification.md)
- [`docs/runbooks/final-review-readiness.md`](../runbooks/final-review-readiness.md)

## Phase 5 Third Vertical Slice independent focused re-review decision

The remediation candidate remains **not approved** for PASS sealing, main
integration, Customer 0, a later Phase 5 slice, or Phase 6.

The exact remediation baseline and one-commit ancestry pass preflight. The
original focused test and historical FAIL documents remain unchanged. The
unchanged original real-PostgreSQL focused matrix passes `6/6`.

One distinct independent secure expectation fails on its first run and one
unchanged rerun. `VE-P5-REVIEW-RR-001` is blocking Medium: after a trusted
repository revision-authority change, the Package read path reports stale but
the freshness generation and durable invalidation remain unchanged. The
database accepts one approved Decision and one durable `ready` row for the old
generation. Workspace/Evidence remain unchanged, no readiness-success event or
Git-delivery authority is created, and the API continues to mask the verdict
as effective stale. That masking does not satisfy the database
zero-approved-decision/readiness invariant.

The five-Finding disposition is FR-001 **FAIL**, FR-002/FR-003/FR-004 **PASS
within the executed original scope**, and FR-005 **FAIL downstream** for
approved-readiness correctness. Critical/High/blocking Medium counts are
`0 / 0 / 1`.

The blocker stop applies. Remaining expanded focused checks, final
`make verify`, migration roundtrip, browser/accessibility expansion, broad
Security/Eval/Chaos, post-aggregate cleanup probe, and PASS sealing are
**NOT RUN**. Historical implementer results are not promoted into this
independent decision.

Production code remains unchanged from
`3eddb9623550227a30013df6dbc6dc7a17d5315c`. Exact audit-owned Compose
projects have zero container/network/volume residue. Main remains
`50dcc05ce48d042882bcdf199ae1bee662a83af6`. No CreativeDeploy, sibling
repository, remote, push, pull request, merge, tag, Customer 0, later slice, or
Phase 6 action occurred.

Detailed independent artifacts:

- [`docs/exec-plans/phase-5-governed-final-review-focused-rereview.md`](../exec-plans/phase-5-governed-final-review-focused-rereview.md)
- [`docs/security/audits/phase-5-governed-final-review-focused-rereview.md`](../security/audits/phase-5-governed-final-review-focused-rereview.md)
- [`docs/evidence/phase-5-governed-final-review-focused-rereview-verification.md`](../evidence/phase-5-governed-final-review-focused-rereview-verification.md)

## Phase 5 Third Vertical Slice targeted remediation 1

The implementer candidate addresses only the five blocking Medium Findings
from the preserved independent focused-review FAIL. It adds a locked
freshness generation and automatic fact-change invalidation, schema-v2
canonical Package/Decision/readiness reconstruction in PostgreSQL, immutable
package-local event sequences, expected-generation keyed Decision replay, and
a frozen trusted blocker source/version/digest with
Critical/High/blocking-Medium counts.

Current verification:

- unchanged focused audit plus candidate and permanent remediation:
  `20/20`;
- real PostgreSQL migration `base -> head -> base -> head`: pass;
- complete API/Runner/Protocol: `272/272`, coverage `83.43%`;
- Web: `50/50`; contracts/typecheck/build: pass;
- real browser desktop + 390px with axe: `16/16`;
- Security, `74` Eval cases, source/canonical Workspace invariance, and
  Workspace chaos: pass; and
- the single permitted final `make verify`: exit `0`, no rerun; and
- exact remediation and aggregate project cleanup: zero
  containers/networks/volumes.

The targeted remediation is ready for a fresh independent focused re-review.
This evidence is implementer evidence, not an independent focused re-review,
Gate PASS, sealing, or integration decision. Historical focused-review FAIL
records below remain unchanged.

Detailed artifacts:

- [`docs/exec-plans/phase-5-governed-final-review-remediation-1.md`](../exec-plans/phase-5-governed-final-review-remediation-1.md)
- [`docs/evidence/phase-5-governed-final-review-remediation-1-verification.md`](../evidence/phase-5-governed-final-review-remediation-1-verification.md)
- [`docs/runbooks/final-review-readiness.md`](../runbooks/final-review-readiness.md)

## Phase 5 Third Vertical Slice independent focused-review decision

The Third Slice candidate is **not approved** for PASS sealing, main
integration, Customer 0, a later Phase 5 slice, or Phase 6.

The independent seven-boundary matrix fails Review Package digest integrity,
freshness/stale invalidation, Evidence completeness, keyed Decision
idempotency/generation fencing, deterministic readiness, and audit
immutability. Approval/Git-delivery separation passes its independent focused
test.

Five blocking Medium Findings are confirmed:

- `VE-P5-REVIEW-FR-001`: a later failed fixed-Profile Validation on the exact
  baseline leaves the old Package fresh and old ready effective;
- `VE-P5-REVIEW-FR-002`: PostgreSQL accepts a forged Package/Decision/ready
  digest chain;
- `VE-P5-REVIEW-FR-003`: review AuditEvents can be updated and deleted;
- `VE-P5-REVIEW-FR-004`: no freshness generation, expected-generation
  Decision field, or keyed Decision idempotency exists; and
- `VE-P5-REVIEW-FR-005`: readiness has no trusted
  Critical/High/blocking-Medium inventory or zero-count proof.

The unchanged candidate focused suite passes `7/7`. The final independent
real-PostgreSQL/API matrix is `4 failed, 2 passed`: the concurrency case proves
one approve/reject winner and one event, and the Git/PR/delivery injection case
fails closed. Corrected `FR-001` is stable `2/2`; `FR-002` and `FR-003` repeat
unchanged. Critical and High counts are zero.

Final `make verify`, migration roundtrip, browser E2E/accessibility, broad
Security/Eval/Chaos, the post-aggregate Docker probe, and PASS sealing are
**NOT RUN** because the blocking stop condition applies. Historical
implementer results are not promoted into this decision.

No production code changed from
`c2054469c8d10441bcab8ade89c52de1f9aa893f`. All exact audit-owned Compose
projects have zero container/network/volume residue. Main remains
`50dcc05ce48d042882bcdf199ae1bee662a83af6`. No CreativeDeploy, sibling
repository, remote, push, pull request, merge, tag, Customer 0, later slice, or
Phase 6 action occurred.

Detailed independent artifacts:

- [`docs/exec-plans/phase-5-governed-final-review-focused-review.md`](../exec-plans/phase-5-governed-final-review-focused-review.md)
- [`docs/security/audits/phase-5-governed-final-review-focused-review.md`](../security/audits/phase-5-governed-final-review-focused-review.md)
- [`docs/evidence/phase-5-governed-final-review-focused-review-verification.md`](../evidence/phase-5-governed-final-review-focused-review-verification.md)

## Phase 5 Third Vertical Slice authorization

The Second Vertical Slice completed its independent focused re-audit, was
sealed, and was integrated into local `main` by pure fast-forward at
`50dcc05ce48d042882bcdf199ae1bee662a83af6`. The historical focused-review
FAIL, targeted remediation, and sealing records below remain unchanged and
continue to describe the exact revisions they inspected.

The completed local implementation is **Phase 5 Third Vertical Slice —
Governed Final Review & Release Readiness**. It adds an immutable Review
Package, freshness and stale invalidation, an immutable local-user Review
Decision, a deterministic Release Readiness Verdict, exact Evidence Manifest
bindings, PostgreSQL/Alembic/API/generated-contract/browser workflows,
concurrency and idempotency fencing, and full local verification. Approval
remains a governance decision and never grants Git commit, push, pull request,
merge, tag, or deployment authority. This result is ready for independent
focused review; it is not that review, sealing, or main integration.

Before this task, neither a later Phase 5 slice nor Phase 6 had started.
CreativeDeploy and Customer 0 remain out of scope and must not be accessed.

## Phase 5 Validation Suites independent focused re-audit and sealing decision

The narrow independent decisions are:

- `VE-P5-SUITES-FR-001`: **PASS**;
- `VE-P5-SUITES-FR-002`: **PASS**;
- required combined-output/race/cancel/cleanup/invariance boundaries:
  **PASS**;
- new Critical/High/blocking Medium Findings: **0 / 0 / 0**; and
- final complete aggregate and local sealing gate: **PASS**.

The unchanged historical focused tests pass `2/2` on real PostgreSQL. Four new
independent cases pass `4/4`: retry versus late old completion, foreign retry
Grant, coherent foreign ordered Evidence, and legal trusted digest/replay/
terminal fencing. The combined focused Suite matrix passes `23/23`, and
focused Protocol/Runner passes `6/6`.

FR-001 now has independent evidence that one approved Grant produces at most
one root/retry attempt, exact replay is idempotent, retry requires a fresh
lineage-bound Grant, and late old completion cannot contaminate the new
attempt. Denials and replays produce no extra Suite Run, step, Job, Attempt,
Lease, Permit, Result, Evidence, event, charge, or canonical Workspace change.

FR-002 now has independent evidence that a coherent but foreign ordered
Evidence chain cannot authorize success, while a legal two-step execution
binds a recomputed digest and exact root/Suite/version/revision/checkpoint/
Grant/policy/budget/Evidence chain. Missing, foreign, duplicate, reordered,
stale, mismatched, non-success, or replace-after-terminal proof is denied with
zero success side effects.

The exact 10,000-byte combined output succeeds and 10,001 bytes fails closed.
Cancel-before-next-dispatch, retry/old-completion competition, cleanup
failure-to-`recovery_required`, and source/canonical invariance pass.
Migration 0009 base/head/base/head and contract drift checks pass.

The final complete `make verify` exits `0`: Python/API/Runner/Protocol
`252/252` at `83.33%`, Web `47/47`, E2E `16/16`, Workspace repair `86/86`
plus API `14/14`, Workspace Security `64/64`, Runner Security `111/111`,
Eval 67, migration, contracts, build, Docker, Chaos, sandbox security, source
invariance, and final diff check pass.

First failures remain disclosed. One new-test Ruff failure and one new
ExecPlan Prettier failure were audit-only. A reused Web image was initially
mapped to an API port different from its build-time `38640` binding, causing
browser failures/timeouts; the task-owned run was cleaned. Bundle inspection
confirmed the environment mismatch, and a complete rerun using the
repository's formal port/skip-build controls passed. No production
configuration was changed.

Production code is unchanged from
`b6d53ba0275933e18919ceb2d90152e5ae8efcac`. All five focused/final/E2E/Chaos
project inventories are zero containers, networks, and volumes, and all
published ports are free. `main` remains
`f547091307c52df8f20fc69bac4b4826cbbc74ad`. No remote, push, merge, pull
request, tag, Customer 0, later slice, or Phase 6 action occurred.

The local sealing subject is
`chore: seal phase 5 governed validation suites`. This seal is ready only for
an explicitly user-authorized local main integration.

Detailed independent artifacts:

- [`docs/exec-plans/phase-5-validation-suites-focused-reaudit.md`](../exec-plans/phase-5-validation-suites-focused-reaudit.md)
- [`docs/security/audits/phase-5-validation-suites-focused-reaudit.md`](../security/audits/phase-5-validation-suites-focused-reaudit.md)
- [`docs/evidence/phase-5-validation-suites-focused-reaudit-verification.md`](../evidence/phase-5-validation-suites-focused-reaudit-verification.md)

## Phase 5 Validation Suites targeted remediation 1

The narrow implementation candidate addresses only
`VE-P5-SUITES-FR-001` and `VE-P5-SUITES-FR-002`. It does not revise or
supersede the independent focused-review FAIL at
`d325fa197e1fdad2c522fdf76f11b738682a86ca`.

The additive `20260730_0009` migration and matching models bind every Suite
Grant to the immutable Suite-definition digest, exact root/source/attempt
lineage, and one allowed Suite Run. PostgreSQL enforces one Suite Run per
Grant and one attempt per root; service locks and idempotency rechecks give
typed exact replay and concurrent-consumption denial. A retry Grant must name
the latest terminal non-success source and gets a server-derived root and next
attempt.

Successful Suite aggregation no longer trusts mutable step summaries. The
Control Plane reconstructs catalog-ordered proof from the exact Validation
Run, Job/spec/result, Attempt, Lease, original lineage Grant and policy,
completed Permit, immutable Evidence, recomputed digests, cleanup, zero
artifacts, budgets, and source/canonical Workspace invariance. PostgreSQL
triggers independently reject illegal step/Suite transitions and missing,
foreign, duplicate, reordered, null, or stale aggregate references.

The original unchanged Findings first reproduced `3/3` each on real
PostgreSQL, then pass `2/2` after remediation. Permanent two-session and
direct-SQL regressions cover same/different idempotency keys, Grant
consumption, revoked/expired/stale authority, cross-Suite Run/Job/Attempt/
Lease/Evidence binding, definition injection, and malformed aggregate
references with unchanged durable counts. Focused Protocol/Runner, migration
downgrade/re-upgrade, generated contracts, strict Ruff/mypy, and Web
typecheck/`47/47`/build pass.

Full related verification and the final aggregate are complete. The first
aggregate passed all gates before E2E, then exited `2` on an external
`ghcr.io` token-fetch `EOF`. The single allowed full rerun reused the exact
completed-source local images and exited `0`: Python `248/248` at `83.27%`,
Web `47/47`, E2E `16/16`, Runner security `111/111`, migration, contracts,
build, Eval 67, source/canonical invariance, Chaos, and exact Docker cleanup
pass. The completion label is
`PHASE 5 SUITES TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`.
It is not a Security Gate PASS, sealing decision, main-integration
authorization, Customer 0 authorization, or later-phase authorization.

## Phase 5 governed multi-step Validation Suites candidate

The second-slice implementation candidate adds one source-owned immutable
Suite, `fixture-integrity-suite-v1:v1`, over the two fixed fixture Profiles.
The Control Plane materializes the two ordered steps and serially dispatches
the sealed first-slice Validation Run unit. Every executed step retains an
independent Runner Job, Attempt, Lease, Permit, result, Evidence, disposable
sandbox, zero-artifact boundary, cleanup proof, and canonical-Workspace
invariance.

The additive `20260730_0008` migration introduces Suite Run, ordered step, and
aggregate result entities plus Suite-scoped Grant references, closed checks,
foreign keys, uniqueness/indexes, and immutable/transition triggers. The API
adds catalog and Suite create/list/detail/timeline/result/cancel/retry routes.
The browser renders Suite definition/limits, Grant approval, serial state,
bounded per-step Evidence, aggregate result, cancellation, fresh-Grant retry,
disabled reasons, and recovery state without a command or step editor.

The Suite is fail-fast with a 30-second total timeout, 10,000-byte combined
retained-output cap, zero artifacts, and two attempts. Exact output limit is
allowed; limit plus one cannot create a successful aggregate. Cancellation
and Suite timeout cancel an active child before terminalizing and never
dispatch a pending child. Retry requires a new approved Suite Grant, reuses
successful immutable Evidence without redispatch or recharge, and creates
fresh execution identities for remaining work.

Focused real-PostgreSQL Suite tests pass `10/10`. Final aggregate `make verify`
exits `0`: Python/API/Runner/Protocol `239/239` at 83.35% coverage, Web
`47/47` above every configured coverage threshold, desktop/390 px E2E
`16/16`, Migration, Chaos, Docker isolation, Security `111/111`, Eval 67, and
invariance pass. These are implementer results. Only the local checkpoint and
clean-tree reconciliation remain administrative steps. The implementer does
not declare Security Gate PASS.
The independent focused review described below supersedes the pending-review
state. These implementer results remain historical context only.

## Phase 5 governed multi-step Validation Suites focused-review decision

The second-slice candidate is **not approved** for PASS sealing, main
integration, Customer 0, a later Phase 5 slice, or Phase 6.

**CONFIRMED**:

- the review started from exact candidate
  `10399722e37f3209fa08e5e7edc25f31b429aaad`, whose exact parent is unchanged
  main `f547091307c52df8f20fc69bac4b4826cbbc74ad`;
- two independent real-PostgreSQL secure-expectation tests failed on their
  first run and on two unchanged focused reruns each (`3/3` stable);
- `VE-P5-SUITES-FR-001` proves the same approved Suite Grant creates a second
  root Suite attempt when only the idempotency key changes;
- `VE-P5-SUITES-FR-002` proves persisted successful step summaries without
  Evidence can become a succeeded Suite and aggregate Result with zero
  Evidence references;
- both new production Findings are blocking Medium; Critical and High counts
  are zero;
- the unchanged candidate Suite control file passes `10/10`;
- the exact review-owned PostgreSQL Compose project has zero
  container/network/volume residue after cleanup; and
- no production file changed, main remains unchanged, and no delivery action
  occurred.

The seven-boundary focused matrix fails Suite/Grant attempt authority, step
transition/injection, Suite/step consistency, fresh-Grant retry fencing, and
aggregate Evidence integrity. Exact review-owned cleanup and production Git
invariance pass. Full budget, cancellation-race, runtime invariance, migration
roundtrip, historical regression, Web/E2E, Chaos, broad Docker, Security, Eval,
coverage, and aggregate gates remain unverified.

Final `make verify` is **NOT RUN** with exit `N/A` because the blocker stop
condition applies. Historical implementer aggregate results are not promoted
to independent evidence.

The next eligible milestone is a narrow remediation that enforces one root
Suite attempt per approved Grant and exact legal step/Evidence binding before
successful aggregation, followed by a fresh independent focused re-review.

Detailed independent artifacts:

- [`docs/exec-plans/phase-5-validation-suites-focused-review.md`](../exec-plans/phase-5-validation-suites-focused-review.md)
- [`docs/security/audits/phase-5-validation-suites-focused-review.md`](../security/audits/phase-5-validation-suites-focused-review.md)
- [`docs/evidence/phase-5-validation-suites-focused-review-verification.md`](../evidence/phase-5-validation-suites-focused-review-verification.md)

## Phase 5 independent single-finding re-audit decision

The narrow independent decisions are:

- `VE-P5-FREAUD-001`: **PASS**;
- strict mypy governance: **PASS**;
- new Critical/High/blocking Medium Findings: **0**; and
- final first-slice aggregate/sealing Gate: **PASS**.

Real PostgreSQL proves normal active cancellation now atomically terminalizes
Job, Attempt, Validation Run, step, and the exact Permit as `cancelled`, with
the Permit terminal timestamp set. No succeeded Result, Validation Evidence,
`job_succeeded`, or `side_effect_permit_completed` exists, and the canonical
Workspace is unchanged.

The one additive independent test retains the terminal Attempt/Lease, replays
cancellation, attempts a stale Lease replay and late completion, and confirms
that the Permit timestamp, Validation Run version, total event count, Result,
Evidence, and Workspace remain unchanged. The complete Phase 5 Control Plane
focused selection passes `49/49`; Runner/Protocol passes `21/21`; relevant
Runner/Workspace API passes `23/23`. Cleanup failure passes `2/2` and remains
failed/`recovery_required`.

Configured verbose mypy discovers all historical focused-review, re-audit,
remediation, cancel-Permit remediation, and current audit files as distinct
modules. Strict mypy passes 91 source files. No targeted exclusion,
`ignore_errors`, new blanket ignore, or strictness reduction exists.

The first final `make verify` attempt passes all stages before E2E setup, then
stops with exit `2` because fixed host port `127.0.0.1:18000` is already in
use. Historical FAIL checkpoint
`61151bd7f2fe68f8076af45dfec9977858f51e04` preserves that result.

After explicit project-control authorization, retry preflight finds no current
listener on `18000`; the historical owner cannot be safely attributed, and no
process or service is stopped. The repository's formal E2E environment inputs
use bind-probed isolated ports `25432/28000/23000`.

The one authorized Final Aggregate Retry exits `0`. It passes contracts,
format, lint, typecheck, Python/API/Runner/Protocol `227/227` at 82.95%
coverage, Web `44/44`, build, Docker config, migration, permanent Finding
controls, Runner security audit `22/22`, source invariance, workspace repair
`85/85` plus API `14/14`, Playwright `16/16`, Workspace Chaos, Workspace
Security `63/63`, Validation Security, broad Runner Security `109/109`, Eval
58 cases, and final `git diff --check`.

The exact audit-owned PostgreSQL, E2E, and Chaos Compose projects have zero
container/network/volume residue. Four current-repository platform services
predate the review and remain untouched.

No production code changed. Main remains unchanged. No CreativeDeploy or
sibling repository content was accessed; no remote, push, merge, pull request,
tag, Customer 0, later Phase 5 slice, or Phase 6 action occurred.

The reserved local PASS subject is now eligible:
`chore: seal phase 5 governed validation first slice`. Even after sealing,
main is not moved. The next eligible action is user-authorized main
integration. Remote CI, push, pull request, tag, deployment, Customer 0, later
Phase 5 slices, and Phase 6 remain separate authorizations.

Detailed independent artifacts:

- [`docs/exec-plans/phase-5-cancel-permit-single-finding-reaudit.md`](../exec-plans/phase-5-cancel-permit-single-finding-reaudit.md)
- [`docs/security/audits/phase-5-cancel-permit-single-finding-reaudit.md`](../security/audits/phase-5-cancel-permit-single-finding-reaudit.md)
- [`docs/evidence/phase-5-cancel-permit-single-finding-reaudit-verification.md`](../evidence/phase-5-cancel-permit-single-finding-reaudit-verification.md)

## Phase 5 final targeted remediation 2

The narrow implementer candidate for `VE-P5-FREAUD-001` and the focused-audit
mypy governance nonconformance is implemented and locally verified.

**CONFIRMED**:

- the original real-PostgreSQL Finding remains unchanged and failed `5/5`
  before the repair with Permit `consumed` and no terminal timestamp;
- successful active Validation cancellation now locks and validates the exact
  persisted Run/step binding, terminalizes the exact consumed Permit, and
  cancels Job, Attempt, Run, and step in one commit;
- cleanup failure remains failed/`recovery_required`;
- stale Attempt/Lease, cross-Runner identity, and mismatched Validation Run
  cannot close the target or an unrelated Permit;
- cancellation replay is idempotent, late completion is rejected, no Result,
  Evidence, success event, duplicate billing effect, or canonical Workspace
  mutation occurs;
- historical API focused, permanent remediation, independent re-audit, and new
  cancellation regressions pass `48/48`;
- focused Runner/Protocol passes `21/21`; relevant Runner/Workspace API files
  pass `23/23`; and
- both targeted mypy exclusions and the shared-module ignore override are
  removed. Strict mypy now discovers the historical focused, re-audit, and
  remediation files as distinct modules and passes 90 source files;
- empty-PostgreSQL base/head/base/head migration, format, lint, typecheck,
  build, contracts drift, and source invariance pass;
- aggregate `make test` passes Python/API/Runner/Protocol `226/226` at 82.92%
  coverage and Web `44/44`; and
- all exact remediation-owned Compose container/network/volume inventories
  are zero after cleanup.

This is implementer evidence only. The single local checkpoint is prepared;
its hash and final clean state are reported administratively after commit.
Final `make verify` is deliberately reserved for a fresh independent
single-finding re-audit. This implementer does not declare Security Gate PASS.

Detailed in-progress artifacts:

- [`docs/exec-plans/phase-5-validation-cancel-permit-remediation-2.md`](../exec-plans/phase-5-validation-cancel-permit-remediation-2.md)
- [`docs/evidence/phase-5-validation-cancel-permit-remediation-2-verification.md`](../evidence/phase-5-validation-cancel-permit-remediation-2-verification.md)

## Phase 5 independent focused re-audit decision

The targeted remediation candidate is **not approved** for PASS sealing, main
integration, Customer 0, a later Phase 5 slice, or Phase 6.

The independent focused matrix is:

- `VE-P5-FSR-001`: **PASS** — unchanged historical Runner checks pass `6/6`;
  an additive two-descendant/early-pipe-close reproduction plus a legal
  control pass `3/3`; complete Runner security-audit selection passes `22/22`;
- `VE-P5-FSR-002`: **FAIL** — typed cleanup failure correctly persists one
  atomic `recovery_required` outcome, but successful active cancellation
  leaves the exact consumed Validation Permit without a terminal state or
  timestamp;
- `P5-AUD-005`: **PASS** within the focused scope — an independently forged
  envelope digest with recomputed evidence digest is rejected twice with zero
  success side effects; and
- `P5-AUD-006`: **PASS** within the focused scope — independent UTF-8 exact
  limit/+1, artifact arithmetic, duplicate path, digest, rejection replay and
  legal replay checks pass.

New production Finding `VE-P5-FREAUD-001` is blocking Medium. A real
PostgreSQL sequence proves HTTP `200` cancellation and correct cancelled
Job/Attempt/Validation Run/step state, one cancellation acknowledgement, no
Result/Evidence/success event, and an unchanged Workspace. The Side-effect
Permit alone remains `consumed` with no `terminal_at`. The semantic secure
expectation failed on the first full run and four focused reruns.

Static review confirms the cancellation service terminalizes Permits for four
Workspace job specifications but omits `ValidationExecuteJobSpec` before it
commits the cancelled Job/Attempt and acknowledgement. The independent review
changed no production code and attempted no repair.

A separate blocking preflight governance nonconformance remains: both
historical focused-review test files are byte-identical and runtime-passing
(`8/8` API, `6/6` Runner), but the remediation candidate adds targeted mypy
exclusions and an ignore-errors override for their shared module. The strict
requirement that the original tests not be loosened is therefore not fully
satisfied. This is not counted as a second production security Finding.

Necessary current-review evidence includes real PostgreSQL, permanent Control
Plane remediation `31/31`, permanent Runner remediation `2/2`, focused
Protocol `5/5`, source invariance PASS with 119 source entries/10 Git
objects/2 status records/0 extension markers, exact Runner PID/process-group
cleanup, and filtered Compose container/network/volume residue of zero.

Final `make verify`, aggregate coverage, full migration roundtrip,
browser/E2E/accessibility, Web build, validation sandbox Docker probe, Chaos,
broad Security, Eval, and PASS sealing are **NOT RUN**. Historical implementer
results are not promoted to independent evidence.

Main remains unchanged. No remote, push, merge, pull request, tag,
CreativeDeploy content access, Customer 0, delivery, deployment, later Phase 5
slice, or Phase 6 action occurred.

The next authorized milestone is a narrow remediation that terminalizes the
Validation Permit during successful cancellation and restores static-analysis
coverage for both historical audit modules, followed by a fresh independent
focused re-audit.

Detailed independent artifacts:

- [`docs/exec-plans/phase-5-governed-validation-focused-reaudit.md`](../exec-plans/phase-5-governed-validation-focused-reaudit.md)
- [`docs/security/audits/phase-5-governed-validation-focused-reaudit.md`](../security/audits/phase-5-governed-validation-focused-reaudit.md)
- [`docs/evidence/phase-5-governed-validation-focused-reaudit-verification.md`](../evidence/phase-5-governed-validation-focused-reaudit-verification.md)

## Phase 5 targeted remediation 1 candidate

The narrow Runner corrections for independent findings `VE-P5-FSR-001` and
`VE-P5-FSR-002` are **locally implemented and focused verified**:

- the validation collector now binds its monotonic deadline and bounded
  TERM/grace/KILL sequence to the complete process group, independent of
  leader exit;
- the Runner lifecycle preserves a typed cleanup/process failure during
  cancellation and does not acknowledge clean cancellation;
- new permanent remediation regressions pass `2/2`; and
- the unchanged independent Runner audit file passes `6/6`.

This is implementer evidence only. The historical Findings are not
independently closed by this run.

The previously stopped third boundary's original real-PostgreSQL result is
preserved as `1 passed, 7 failed`, stable `3/3` for both failing scopes. With
the newly authorized Control Plane repair, the same unchanged audit file now
produces `8 passed`:

- `P5-AUD-004` outer Attempt/Lease/Permit fencing passed;
- `P5-AUD-005` now reconstructs and matches the complete trusted execution
  envelope before terminal persistence; and
- `P5-AUD-006` now independently recomputes output/artifact/evidence budgets
  and digests before terminal persistence.

Permanent real-PostgreSQL regressions pass `31/31`. They prove two repeated
rejections have no succeeded Result, completed Permit, success event or
Evidence; exact output limit and legal replay persist once; and a typed
cleanup failure after `cancel_requested` atomically stores Job/Permit failure
plus Validation Run/step `recovery_required` without cancellation
acknowledgement.

Complete focused API passes `118/118`; complete focused Runner/Protocol passes
`96/96`. The final aggregate collects and passes `214/214` backend/Runner/
Protocol tests at 82.82% coverage plus `44/44` Web tests.

Migration base/head/base/head, contracts, format/lint/typecheck, Web build,
sandbox/source invariance, Phase 4 regressions, E2E `16/16`, Chaos, Security
and Eval gates pass locally. Final `make verify` returns exit `0`; filtered
remediation/E2E/Chaos container, network and volume inventories are all zero.
The one authorized local checkpoint is created by this candidate.

Main remains unchanged. No remote, push, merge, pull request, tag,
CreativeDeploy, Customer 0, delivery, deployment, later Phase 5 slice, or
Phase 6 action occurred.

Detailed local implementer evidence:

- [`docs/exec-plans/phase-5-governed-validation-remediation-1.md`](../exec-plans/phase-5-governed-validation-remediation-1.md)
- [`docs/evidence/phase-5-governed-validation-remediation-1-verification.md`](../evidence/phase-5-governed-validation-remediation-1-verification.md)

## Phase 5 independent focused security review decision

The Phase 5 Governed Validation Execution first-slice candidate is **not
approved** for main integration, PASS sealing, Customer 0, a later Phase 5
slice, or Phase 6.

**CONFIRMED**:

- the independent review started from exact candidate
  `1b6481156337c9f615240bf10dcca3f1e6833400`, whose exact parent is unchanged
  main `928a89d2055d172bbd7c6670b42f668d103dcb03`;
- four strict Protocol negative-input cases pass;
- two new production-path secure-expectation tests fail on their first run and
  on two focused reruns (`3/3` stable each);
- both Findings are classified blocking Medium:
  `VE-P5-FSR-001` and `VE-P5-FSR-002`;
- the tests retain their original assertions and complete audit-owned cleanup;
- the independent reviewer changed no production code; and
- no CreativeDeploy content access, Docker command, remote, push, merge, pull
  request, tag, Customer 0, or later-phase action occurred.

The third candidate boundary—Runner result budget, Attempt, Lease, Grant,
Permit, fixed-argv, and inner-identity binding—is **NOT VERIFIED**. The user
explicitly stopped expansion after the Gate was conclusively FAIL. No Finding
or PASS is inferred from its drafted but unexecuted audit tests.

Final `make verify`, E2E, accessibility, PostgreSQL/migration execution, broad
Docker runtime verification, Chaos, Security, Eval, necessary Phase 4
regressions, and PASS sealing are **NOT RUN**. The Phase 5 implementation
report's earlier results remain historical implementer evidence only.

The next authorized milestone is a narrowly scoped production remediation of
the two blocking Medium Findings, followed by a fresh independent focused
review that also dynamically completes the stopped third boundary. No main
movement or integration is authorized.

Detailed independent artifacts:

- [`docs/exec-plans/phase-5-governed-validation-focused-review.md`](../exec-plans/phase-5-governed-validation-focused-review.md)
- [`docs/security/audits/phase-5-governed-validation-focused-review.md`](../security/audits/phase-5-governed-validation-focused-review.md)
- [`docs/evidence/phase-5-governed-validation-focused-review-verification.md`](../evidence/phase-5-governed-validation-focused-review-verification.md)

## Phase 5 implementation checkpoint

The first maximum-safe **Governed Validation Execution** vertical slice is
implemented and locally verified on
`feat/phase-5-governed-validation-execution`; independent focused review is
pending.

The slice contains one immutable `fixture-python-stdlib-v1:v1` Profile, a
separately decided validation-only Grant bound to an exact existing Workspace
Checkpoint/revision, strict Validation Run/step/evidence persistence, a
command-free Runner Protocol job, a disposable Landlock/seccomp-confined
validation sandbox, and the `/validations` browser flow.

Focused evidence currently passes API 167 tests at 82.39% coverage, Runner 88
tests, Web 44 tests in 8 files, real Playwright 16 tests at desktop and 390 px,
real PostgreSQL migration roundtrip, validation sandbox pass/fail and
filesystem/network denial, Workspace security 63 tests plus static isolation,
Runner security 98 tests plus 7 scanner tests and static checks, Workspace
Chaos, source invariance, contracts, formatting, lint, typecheck, production
build, Compose rendering, and Eval.

The complete local `make verify` also exited `0` with those gates composed in
the repository-defined order. This records implementation readiness for
independent focused review; it is not an independent review or Security Gate
approval.

This is implementation evidence only. Independent focused review, remote CI,
real/customer repositories, arbitrary commands, package lifecycle,
CreativeDeploy/Customer 0, LLM/Agents SDK/Providers/credentials, Git delivery,
deployment, and Phase 6 are not authorized or verified.

Detailed evidence is in
[`docs/evidence/phase-5-governed-validation-execution-verification.md`](../evidence/phase-5-governed-validation-execution-verification.md).

## Final Integration Gate decision

The complete local Phase 4 Final Integration Gate is **PASS**.

The explicitly authorized local fast-forward subsequently integrated the
sealed Phase 4 commit into `main` at
`928a89d2055d172bbd7c6670b42f668d103dcb03`. No remote, push, pull request, or
tag was involved. Phase 5 is now formally defined as **Governed Validation
Execution** and is limited to fixed system-owned Profiles against the trusted
synthetic fixture. It excludes LLMs, Agents SDK, providers, credentials,
Customer 0, arbitrary commands, package installation, Git delivery, and
deployment.

**CONFIRMED**:

- the exact independently audited candidate and its ten-commit linear Phase 4
  ancestry were reconciled from unchanged `main`;
- all historical Critical, High, and blocking Medium Findings have later
  remediation plus independent closure evidence in the candidate ancestry;
- one final `make verify` exited `0`;
- Python passed `161/161` at 81.79% coverage and Web passed `41/41`;
- contracts, format, lint, typecheck, Next.js production build, all Compose
  rendering, real PostgreSQL migration roundtrip, 14 real Playwright cases,
  Workspace Chaos, security, and Eval passed;
- the named Runner and Workspace smoke targets both exited `0` against an
  isolated fresh Compose project; the Workspace rolled back and discarded,
  four policy-denial classes held, and source remained exact;
- the separate Runner offline/requeue Chaos target exited `0`;
- a live disposable runtime proved non-root Runner identity, read-only root
  and source, dropped capabilities, no-new-privileges, resource limits,
  internal API-only networking, blocked external TCP, narrow mounts, and
  mode-0600 ownership key;
- strict source invariance passed with 119 entries, 10 Git objects, two status
  records, and zero extension markers;
- the 72-file frozen production boundary is byte-for-byte equal to the
  independently audited candidate; and
- all exact gate-owned disposable container, network, and volume inventories
  returned zero after cleanup.

The original audit, independent re-audit, focused re-audit, and
single-finding re-audit FAIL decisions remain unchanged and correct for their
inspected revisions. This current PASS records later closure plus complete
local integration evidence; it is not a retroactive rewrite.

Remote CI, production deployment, hostile multi-tenant use, Customer 0, LLM
or Agents SDK behavior, and Git delivery/PR are **NOT VERIFIED** or explicitly
outside the Phase 4 implementation. No merge, fast-forward, push, pull
request, tag, Customer 0, CreativeDeploy, Phase 5, or production action is
authorized by this status.

Detailed evidence is in
[`docs/evidence/phase-4-final-integration-gate-verification.md`](../evidence/phase-4-final-integration-gate-verification.md).

## Independent budget re-audit decision

The Round 4 Blocking Medium finding **Expanded checkout manifest bypasses
configured entry budget** is **CLOSED**.

**CONFIRMED** by the independent current-worktree review:

- the unchanged permanent shared-tree reproduction passes `1/1`;
- a distinct single-file subtree referenced by three parent directories is
  charged once per expanded path;
- with limit `5`, a five-entry manifest succeeds exactly;
- the possible sixth entry returns typed `mirror_budget_exceeded` before the
  third shared blob read or digest;
- the recursive walk does not first construct an over-budget complete list;
- actual manager rejection creates no Workspace, registry, or ownership
  record, consumes no additional Permit, and preserves the mirror, source,
  and a sibling marker;
- the complete blocking file passes `13/13`;
- manifest/object closure focus passes `24/24`;
- source invariance passes with 119 entries, 10 Git objects, 2 status records,
  and 0 extension markers;
- Workspace security passes `63/63` plus static isolation;
- Runner/Protocol passes `83/83`; and
- final format, lint, and type checks pass.

The independent reviewer changed no production code. No new Critical, High,
or blocking Medium finding was discovered. Historical FAIL reports remain
unchanged.

This is not a Phase 4 Security Gate PASS. Aggregate `make verify`, Web E2E,
full Chaos, full Docker Gate, Customer 0, remote CI, integration, merge,
CreativeDeploy, and Phase 5 remain unexecuted and unauthorized. The only next
milestone is the single final Phase 4 integration gate.

## Round 4 remediation candidate

**CONFIRMED** in the current Round 4 worktree:

- source-less checkout-manifest construction now shares one expanded-entry
  count across recursive paths;
- each regular file, symlink, or inert gitlink atomically charges itself and
  every pending ancestor directory before content processing or construction;
  empty Git trees retain their existing omission semantics;
- equality with `mirror_max_tree_entries` is accepted, while the next entry
  raises typed `mirror_budget_exceeded`;
- shared trees are charged again for every distinct path, without first
  constructing an unbounded complete manifest;
- raw path bytes, entry type, Git mode, size, digest, symlink, inert gitlink,
  replacement metadata, exact closure, semantic proof, quarantine, source
  invariance, process-group timeout, discard, and Permit production logic are
  unchanged.

The permanent five-entry shared-tree reproduction failed twice before the
repair with `8 <= 5`, then passed unchanged after the repair. Five additive
budget regressions pass: the sixth entry is rejected before its blob is reread,
the exact four-entry semantic boundary succeeds and registers a Workspace,
and deep, wide, and repeated-subtree over-limit cases create no Workspace,
registry, or ownership record while preserving the mirror, source, and
sibling.

Current focused evidence passes:

- permanent shared-tree reproduction: `1/1`;
- additive budget regressions: `5/5`;
- complete blocking reproduction file: `12/12`;
- manifest/object-closure focus: `24/24`;
- source invariance: 119 entries, 10 Git objects, 2 status records, and 0
  extension markers;
- Workspace security: `63/63` plus static isolation;
- complete Runner/Protocol: `82/82`;
- repository format, lint, and typecheck;
- complete backend/Runner/Protocol tests: `160/160`, 81.79% coverage; and
- Web unit tests: `41/41`.

The first format check found only the new test file's Ruff layout. After that
scoped correction, the next format check found only the new ExecPlan's
Prettier layout. A later post-tightening check found only the updated evidence
document's Prettier layout. All three are preserved as non-behavioral first
failures; the final complete format check passes.

This is implementer evidence only. The historical Security Gate remains FAIL,
and Round 4 does not authorize `main` merge, Customer 0, CreativeDeploy,
Phase 5, remote, push, pull request, tag, delivery, or deployment.

## Independent single-finding re-audit decision

`VE-P4-FREAUD-001` remains **FAIL / REMEDIATION REQUIRED**.

Round 3 closes the original packed `refs/replace` reproduction:

- the unchanged original test passes `1/1`;
- a distinct independent scenario inserts packed replacement metadata after
  final mirror validation and before actual worktree checkout while hostile
  host Git environment variables try to redirect and re-enable Git behavior;
- the actual Workspace still contains the exact approved bytes, creates its
  registry, and the polluted mirror fails closed on the next prepare;
- the Round 3 replacement/manifest matrix passes `6/6`;
- the source/object/ref/manifest focus passes `19/19`;
- strict source invariance passes; and
- the Workspace/Protocol target passes `58/58` plus its static isolation
  check.

The required Workspace semantic proof has one new stable Blocking Medium
capacity defect. A shared Git subtree is charged once by the authorized object
walk but expanded once per path by the new checkout-manifest walk. With
`mirror_max_tree_entries=5`, production `prepare_mirror` returns an eight-entry
manifest rather than rejecting it. The permanent secure-expectation test fails
`8 <= 5` twice. The complete blocking file is `1 failed, 11 passed`, and the
complete Runner/Protocol target is `1 failed, 76 passed`; both have the same
sole failure.

The later descriptor-rooted Workspace scanner does reject this minimal case
with typed `mirror_budget_exceeded`, quarantines the checkout, removes its
canonical address, and creates no registry. No unauthorized registered
Workspace bytes were reproduced. The blocker is that compact shared-tree DAGs
can expand expected-manifest CPU/memory exponentially before that enforcement
point, threatening the declared bounded Runner and leaving incomplete mirror
state requiring manual recovery.

No production code was modified. No existing test was weakened, skipped, or
marked expected-failing. No customer repository was accessed. No remote,
push, merge, pull request, tag, delivery, deployment, or Phase 5 action
occurred.

## Round 3 remediation candidate

The audited Round 3 branch narrowly implements the production correction for
`VE-P4-FREAUD-001` / `VE-P4-AUD-001`:

- new mirrors use `git init --bare --template=` followed by exact managed
  config, a detached authorized `HEAD`, and an empty loose/packed ref
  namespace;
- existing mirrors fail closed unless top-level metadata, config, object
  layout, detached `HEAD`, and empty refs match the managed template;
- every Runner-owned Git process uses both `--no-replace-objects` and
  `GIT_NO_REPLACE_OBJECTS=1`; and
- the source-less parser's path/type/Git-mode/size/SHA-256 authorized checkout
  manifest must exactly match an independent descriptor-rooted no-follow
  Workspace manifest before ownership or registry creation. A mismatch is
  atomically isolated without recursive deletion.

The unchanged independent packed-replacement test now passes. The current
ordered local runs also pass the six-case additive replacement/manifest
matrix, complete ten-test blocking reproduction file, 19-case Git
object/ref/manifest focus, strict source invariance, 58-test Workspace/Protocol
security target plus static isolation check, and complete 75-test
Runner/Protocol suite.

The first Workspace security run is preserved as `57 passed, 1 failed`: the
existing ignored-inventory test assumed the default Git template created
`info/`. Its synthetic setup was corrected to create that parent before
injecting `info/exclude`; the discard quarantine assertions were unchanged and
the targeted/full reruns pass.

Repository-wide format, lint, and typecheck pass. Final `make test` passes
backend `153` tests at 81.79% coverage and Web `41` tests. The first two full
test attempts exposed a coverage-load race in the already passing
process-group audit fixture; a bounded child-ready/leader-exit handshake made
the fixture deterministic without changing production timeout logic or its
secure assertions. The complete blocking file then passes `10/10`.

This remains historical implementer evidence. The later independent
single-finding decision above is the governing result.

## Focused re-audit decision

The Round 2 candidate remains **Security Gate: FAIL**. Three named blocker
scopes pass current independent focused checks:

- `VE-P4-AUD-003`: authenticated discard proof;
- `VE-P4-AUD-005`: complete process-group deadline; and
- `VE-P4-AUD-002`: real-PostgreSQL Side-effect Permit closure.

`VE-P4-AUD-001` fails on new Critical finding `VE-P4-FREAUD-001`. An existing
managed mirror can encode `refs/replace` in `packed-refs`. Current validation
does not reject that representation and the Runner-owned Git subprocesses
interpret it. The exact authorized object-ID set and requested `HEAD` can
remain intact while checkout materializes another reachable commit's tree.
This violates the exact authorized revision boundary.

The corrected complete blocking-reproduction file produces
`1 failed, 9 passed`; the sole failure is the packed replacement secure
assertion. The complete Runner/Protocol focused files produce `52 passed`.
The real-PostgreSQL Workspace API file produces `13 passed`, including an
independent five-session convergence test. The strict source-invariance target
passes.

Because one Critical blocker is stable, the final full Gate, aggregate
`make verify`, full Docker isolation Gate, browser/E2E, smoke, chaos,
security, and Eval are **NOT VERIFIED** in this review. They were not run or
inferred after the stop condition.

No production code was modified. No customer repository was accessed. No
remote, push, merge, pull request, tag, delivery, deployment, or Phase 5 action
occurred.

## Preserved pre-focused governance status

The independent re-audit of the isolated security-repair commit completed with
**Security Gate: FAIL**. Three production defects are independently stable:

- `VE-P4-AUD-001` remains open because the source-less adapter copies an
  unreachable, unapproved source object into the Runner mirror.
- `VE-P4-AUD-003` remains open because registry/root absence without trusted
  signed pending-discard completion proof is reported as successful discard.
- `VE-P4-AUD-005` is a blocking Medium because a descendant that retains the
  output pipes can continue past the Git operation timeout after the process
  leader exits.

The first two defects are Critical and High; either alone requires FAIL. The
third is independently Gate-blocking within the declared local Runner
resource boundary. `VE-P4-AUD-002` is not independently closed because the
complete new concurrency/adversarial matrix was stopped after the Gate had
already failed. `VE-P4-AUD-004` and local `VE-P4-AUD-006` checks pass.

The original audit FAIL and the repair implementer's evidence remain preserved
history. Neither is rewritten as the current result.

## Round 2 remediation candidate

Round 2 locally implements the three production corrections required by the
independent re-audit:

- exact authorized commit/ancestor/tree/blob closure parsing and
  Runner-owned loose-object materialization, including bounded loose and
  packed OFS/REF delta input, without Git execution against the source;
- domain-separated signed pending/completed discard proof with exact
  registry, ownership, root device/inode, operation, Permit, Attempt, Lease,
  digest, and time-window binding; and
- monotonic complete-process-group monitoring after leader exit, with
  nonblocking pipes, bounded TERM/KILL escalation, reaping, and explicit
  termination failure.

The unchanged re-audit file now passes `7/7` locally. Additive Runner,
Protocol, source-invariance, and real-PostgreSQL Permit regressions also pass
their focused Round 2 runs. Every named non-aggregate local target, including
Docker, E2E `14/14`, both smoke targets, both chaos targets, security, and
Eval, has exited zero. Live Runner isolation was inspected in a uniquely
named disposable Compose project and its exact resources were removed.
The corrected complete post-documentation `make verify` rerun exited zero.
Final diff review then closed one further in-scope pack-directory enumeration
budget gap; focused, complete Runner/Protocol, and source-invariance reruns
pass, and the final post-correction aggregate rerun exited zero. Remote CI is
not run.

`VE-P4-AUD-002` received the previously missing real-PostgreSQL concurrency,
revocation, binding, crash-ordering, retry, lineage, and budget matrix. No new
production Permit defect was reproduced, so Round 2 does not change Permit
production code.

These are implementer-candidate facts only. The historical Security Gate
remains FAIL until a new independent focused re-audit makes a new decision.

## Preserved re-audit disposition

- `VE-P4-AUD-001`: **FAIL / UNRESOLVED.** Source registration and mirror
  preparation no longer invoke Git against the source, but object copying is
  not restricted to the authorized revision's reachable object closure.
- `VE-P4-AUD-002`: PostgreSQL-backed Side-effect Permits bind the current
  Runner, Job, Attempt, Lease, Grant, Workspace, operation and canonical
  digest, including the immutable authorization time window, immediately
  before prepare, create/replace, rollback, or discard.
  `revoke_requested` blocks new permits; effective `revoked` waits for
  in-flight permits to become terminal or expire. Focused real PostgreSQL
  evidence passes; complete independent closure is **NOT VERIFIED**.
- `VE-P4-AUD-003`: **FAIL / UNRESOLVED.** Registry payloads and ownership
  manifests are authenticated in normal paths, but absence of both registry
  and expected root can still return idempotent success without trusted signed
  pending-discard evidence.
- `VE-P4-AUD-004`: **PASS** for the independently executed strict synthetic
  source-invariance harness.
- `VE-P4-AUD-005`: **FAIL / BLOCKING MEDIUM.** Live Runner CPU, memory, PID,
  FD, rootfs, capability and network controls pass, but timeout/process-group
  enforcement does not.
- `VE-P4-AUD-006`: in-scope external Compose images use immutable digests and
  GitHub Actions use full commit SHAs. Local configuration is **PASS**; remote
  CI is **NOT VERIFIED**.

The API, database migration, pure Runner Protocol, generated OpenAPI/
TypeScript contract, browser surfaces, E2E/chaos harnesses, Make targets, CI
definition, threat models, architecture, ADRs, and runbooks remain part of the
historical first-repair candidate. This section records the independent
re-audit result at `b457b61`; it is intentionally not rewritten by Round 2.

## Product boundary

Implemented Phase 4 remains fixture-only Level 1:

- independently decided exact Execution Grant;
- opaque synthetic Repository Handle;
- closed prepare/list/read/create/replace/status/diff/rollback/discard jobs;
- descriptor-rooted bounded UTF-8 operations;
- immutable Checkpoints and initial-baseline rollback;
- Runner-only private mirror/workspace/registry/credential volumes; and
- outbound API-only Runner control transport.

Explicitly absent: LLM, OpenAI Agents SDK, Agent Trace, shell, arbitrary
subprocess, target repository command/build/test, delete/rename/binary tool,
source write, Git delivery, branch/commit/push/PR, remote CI evidence,
authentication, multi-tenancy, public hosting, and production deployment.

CreativeDeploy is not authorized for this repair and was not mounted,
accessed, read, written, built, tested, or cleaned.

## Preserved re-audit verification status

The current re-audit evidence includes stable minimal filesystem/process
reproductions, a strict independent source-invariance run, real PostgreSQL
migration and eight-test Workspace API execution, 35 focused
Runner/Protocol tests, contract drift checks, Compose rendering, live Docker
isolation inspection, and final production-boundary hash comparisons.

The three-test first run also exposed a missing audit-test exception import.
That test-only `NameError` is preserved, classified separately, corrected only
in the audit test, and rerun. The corrected complete test file produces
`3 failed, 4 passed`: the failures are the three intended secure assertions
against current production behavior.

Full Web/browser/E2E/smoke/chaos/security/Eval and aggregate `make verify` were
not continued because the Critical, High, and blocking Medium reproductions
already make Security Gate PASS impossible. They are **NOT VERIFIED** in the
current re-audit and are not inferred from repair evidence.

Exact commands, exit codes, counts, first failures, root causes, corrections,
runtime facts, and stopped-check rationale are in
`docs/evidence/phase-4-security-reaudit-verification.md`.

Round 2 commands, counts, production/source invariance, PostgreSQL ordering,
Docker evidence, and final Git state are recorded separately in
`docs/evidence/phase-4-security-remediation-2-verification.md`.

## Remaining limitations

- The direct packed-replacement exploit is denied, but the Round 3
  Workspace semantic proof does not enforce its expanded path-entry budget
  during expected-manifest construction. `VE-P4-FREAUD-001` remains open.
- The Permit, discard, and process-group scopes pass this focused review, but
  those historical local PASS results do not override the current
  manifest-capacity blocker.
- Python does not expose portable `openat2`/`renameat2` pathname-CAS; the
  implementation retains descriptor-rooted no-follow checks and a sole
  Runner-Writer assumption.
- Local bearer credentials, HMAC ownership, Docker networking, PostgreSQL
  polling, and synthetic fixtures are development controls, not hostile
  multi-tenant or production identity/isolation.
- No privileged garbage collector or automatic quarantine adjudication exists.
- Filesystem quotas, fleet admission, production credential lifecycle,
  backup/restore, incident response, and public deployment remain future work.

## Recommended next milestone

**Perform a narrow Phase 4 remediation that bounds every expanded
source-less checkout-manifest path before materialization, followed by another
fresh independent single-finding read-only re-audit of
`VE-P4-FREAUD-001`.**

Do not merge `main`, access CreativeDeploy/Customer 0, push, create a pull
request, or begin Phase 5 before a fresh independent PASS.

`SINGLE-FINDING RE-AUDIT COMPLETE — VE-P4-FREAUD-001 FAIL — REMEDIATION REQUIRED`
