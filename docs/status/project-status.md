# Project Status

- Phase: Phase 5 — Governed Multi-Step Validation Suites
- Overall status:
  `FOCUSED_SECURITY_REVIEW_FAIL_REMEDIATION_REQUIRED`
- Governance qualifier: SECOND-SLICE CANDIDATE NOT APPROVED; FINAL AGGREGATE
  NOT RUN
- Last updated: 2026-07-30
- Current main / second-slice baseline:
  `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Current implementation branch:
  `feat/phase-5-governed-validation-suites`
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
