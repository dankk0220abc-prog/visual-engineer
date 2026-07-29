# Phase 5 Governed Validation Independent Focused Security Review

- Review date: 2026-07-29 (Asia/Shanghai)
- Candidate:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Main baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Review branch: `audit/phase-5-governed-validation-focused-max`
- Independence: no Phase 5 production implementation was changed
- Status: **COMPLETE**
- Focused Security Gate: **FAIL**
- Required next state: **REMEDIATION REQUIRED**

## 1. Completion status

The independent focused review is administratively complete. Two blocking
Medium production-path failures are preserved as unchanged secure-expectation
tests. Each failed on the first focused run and on two independent focused
reruns (`3/3` stable).

The user stopped expansion after the Gate was conclusively FAIL. The third
candidate boundary, Runner-result budget and identity binding, is therefore
`NOT VERIFIED`; drafted tests for that boundary were not executed and do not
support a Finding.

## 2. Focused Security Review

**FAIL.**

Confirmed:

- Critical: 0
- High: 0
- blocking Medium: 2
- non-blocking new Findings: 0

The verdict does not rely on an implementation report or an aggregate result.
It follows from independent tests reaching candidate production code.

## 3. Final Integration Gate

**NOT RUN.**

The original contract permits the final aggregate only after all six focused
boundaries pass with no blocker. That prerequisite is false. `make verify`,
final E2E, Chaos, broad Docker, Security, Eval, and PASS sealing were not run.

## 4. Git baseline and branch

The independently confirmed baseline is:

`main 928a89d2055d172bbd7c6670b42f668d103dcb03`
→
`candidate 1b6481156337c9f615240bf10dcca3f1e6833400`

The candidate parent is exactly main and `main..candidate` contains exactly
one commit. The candidate Git tree is
`c0960ab6a75c974917d75cff7f5a5acdadd3cb85`.

The audit branch was created directly from the exact candidate without force:

`audit/phase-5-governed-validation-focused-max`

No remote, stash, tag, Git lock, replace ref, hidden remote-tracking ref, or
additional worktree was found during preflight.

## 5. Independence and production-code invariance

The frozen production boundary contains 157 tracked entries and has candidate
`git ls-tree` digest:

`b5f8175c2b353870d9b1995a3ddccb369bbe79c81a9f6a60fa7184e934ef153d`

It covers:

- `apps/api/src`
- `apps/api/alembic/versions`
- `apps/api/Dockerfile`
- `apps/runner/src`
- `apps/runner/Dockerfile`
- `apps/web/src`
- `apps/web/e2e`
- `apps/web/Dockerfile`
- `packages/runner-protocol/src`
- `compose.yaml`
- `infra`
- `scripts`
- `Makefile`

Review changes are confined to independent audit tests, the focused ExecPlan,
this audit report, verification evidence, and project status. No production
file was edited.

## 6. Arbitrary-command prevention

**Focused independent negative test: PASS (`4/4`). Complete boundary:
NOT VERIFIED.**

The independent Protocol test rejects added `command`, `argv`, `env`, and
`cwd` authority. Static review also found typed profile-only request and Job
models. The broader API/database/runtime matrix required by the original
boundary was not completed after the Gate failed, so this section is not a
complete boundary PASS.

## 7. Sandbox and canonical Workspace isolation

**NOT VERIFIED as a complete boundary.**

Static review covered the Phase 5 disposable validation path. The focused
timeout Finding used an audit-owned temporary execution fixture and completed
exact cleanup, but no complete independent canonical-Workspace mutation,
traversal, success/failure/cancel/timeout digest matrix was run after the stop
direction. No broader PASS is inferred.

## 8. Network and credential isolation

**NOT VERIFIED.**

No current-review real runtime network or credential probe was executed.
Candidate implementation evidence and static configuration review are not
promoted to independent dynamic proof. No Docker command was required for the
two confirmed Findings.

## 9. Lease, fencing, cancel, and timeout

**FAIL.**

`VE-P5-FSR-001` independently demonstrates a blocking timeout/termination
failure on the production validation result collector. The exact
secure-expectation test is preserved.

`VE-P5-FSR-002` independently demonstrates that the production lifecycle can
acknowledge cancellation after a cleanup failure instead of preserving the
typed failure/recovery outcome. The exact secure-expectation test is
preserved.

Stale Attempt, stale Lease, revoked Grant, result replay, and full
PostgreSQL-backed completion fencing were part of the stopped third candidate
work and are `NOT VERIFIED` in this review.

## 10. Output and artifact budgets

**NOT VERIFIED.**

The candidate boundary was statically reviewed and audit tests were drafted,
but the user explicitly stopped its dynamic execution after the Gate was
already FAIL. No test result, Finding, or PASS is claimed for combined output,
artifact count, artifact bytes, partial Evidence, or replay accounting.

## 11. Cleanup, recovery, and invariance

**FAIL for cancel cleanup/recovery; PASS for audit-owned fixture cleanup;
production-code invariance PASS.**

The cancellation reproduction fails the required recovery assertion and maps
to `VE-P5-FSR-002`. The audit-owned temporary resources used by both confirmed
reproductions were cleaned after every run. No residual audit process,
sandbox, container, network, or volume was intentionally left.

Canonical Workspace/source/mirror/registry/credential runtime invariance was
not broadly re-executed after the stop direction. Production Git-boundary
invariance is independently confirmed.

## 12. Phase 4 regression status

**NOT RUN.**

The review did not reopen Phase 4. Necessary Phase 4 regressions were scheduled
only if they would materially distinguish or close the Phase 5 focused
boundary. After two stable Phase 5 blockers and an explicit stop direction,
running them would not change the Gate decision.

## 13. Final `make verify`

**NOT RUN.**

The Phase 5 implementation report's earlier `make verify` is historical
implementer evidence. It is not an independent aggregate result for this
review and cannot override the focused failures.

## 14. Tests, coverage, and build

Independent executed test results:

- first focused Runner audit file: `4 passed, 2 failed`, exit `1`;
- `VE-P5-FSR-001`: first failure plus two single-test failures, `3/3`,
  each exit `1`;
- `VE-P5-FSR-002`: first failure plus two single-test failures, `3/3`,
  each exit `1`;
- audit-test static formatting/lint correction: exit `0` after audit-only
  corrections.

Coverage was disabled with `--no-cov` for the focused reproductions and no
coverage percentage is inferred. Full tests and production build were not
run.

## 15. PostgreSQL, Migration, API, and Protocol

Protocol negative-input evidence is `4/4 PASS`.

Real PostgreSQL, migration roundtrip, the drafted API result-binding tests, and
the complete API/Protocol suite are `NOT RUN` in this independent review after
the stop direction. Static review is recorded as review context only.

## 16. Web, E2E, and accessibility

**NOT RUN / NOT VERIFIED.**

No Web code was changed. The implementer's earlier browser evidence remains
historical and is not restated as an independent result.

## 17. Docker, Chaos, Security, and Eval

**NOT RUN / NOT VERIFIED.**

No current-review Docker command was executed, filtered or otherwise. In
particular, no unfiltered global Docker inventory, inspect, logs, or exec was
run. No current-review container, network, or volume exists to clean.

Chaos, broad Security, and Eval were not run after the focused Gate failed.

## 18. First failures, root causes, fixes, and reruns

The first behavior run selected six independent Runner audit cases. Four
negative-input cases passed and both secure-expectation production-path cases
failed.

Before behavior execution, the new audit file received an audit-only wait-loop
correction and mechanical formatting/lint corrections. Those were audit
harness changes, not production fixes. The first production failures required
no harness correction: each reproduced unchanged on two later focused runs.

No assertion was weakened, removed, skipped, or converted to `xfail`. No
production root cause was repaired.

## 19. New Findings

| Finding         | Boundary                                     | Trigger condition                                                                               | Expected                                                                                                                         | Actual                                                                                            | Severity        | Stable tests | Exit codes | Persistent side effect                                                         |
| --------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | --------------- | -----------: | ---------- | ------------------------------------------------------------------------------ |
| `VE-P5-FSR-001` | Validation timeout and process-group cleanup | The execution leader finishes while a descendant remains attached beyond the governed deadline. | The collector completes bounded TERM/grace/KILL handling, reaps the group, and returns within the audit deadline.                | The production collector remains blocked until the audit watchdog performs exact cleanup.         | blocking Medium |        `3/3` | `1, 1, 1`  | No; exact audit-owned group cleanup completed each run.                        |
| `VE-P5-FSR-002` | Cancellation cleanup/recovery                | Cancellation is requested and execution reports a typed validation cleanup failure.             | The lifecycle preserves the cleanup failure and enters typed failure/recovery handling without acknowledging clean cancellation. | The production lifecycle acknowledges cancellation and does not submit the typed cleanup failure. | blocking Medium |        `3/3` | `1, 1, 1`  | No; injected state was in-memory/audit-temporary and pytest cleanup completed. |

The minimal reproduction and unchanged assertions are in:

`apps/runner/tests/security_audit/test_phase5_focused_security_review.py`

The complete command and output ledger is in:

`docs/evidence/phase-5-governed-validation-focused-review-verification.md`

## 20. Remaining non-blocking limitations

These are unverified boundaries, not additional Findings:

- Runner-result budget, Attempt, Lease, Grant, Permit, inner identity, and
  fixed-argv binding;
- full arbitrary-command database/API/runtime closure;
- canonical Workspace/source/mirror/registry/credential runtime invariance;
- real network and credential isolation;
- PostgreSQL/migration completion and replay behavior;
- Phase 4 necessary regression set;
- Web/E2E/accessibility;
- Docker/Chaos/Security/Eval and aggregate verification;
- remote CI, production deployment, hostile multi-tenant execution, and
  customer repositories.

## 21. Git audit checkpoint

This report belongs to a local FAIL audit checkpoint, not the reserved PASS
sealing commit. A Git commit cannot embed its own final object ID without
changing that ID; the exact checkpoint hash is therefore reported in the
post-commit administrative handoff.

The reserved PASS subject
`chore: seal phase 5 governed validation first slice` is not used.

## 22. Worktree, index, and untracked inventory

The candidate started clean. Before checkpoint, all review changes are limited
to the allowed audit/test/document inventory. After the local checkpoint, the
worktree, index, and untracked inventory must be empty; the post-commit
administrative verification is authoritative for that final fact.

## 23. CreativeDeploy metadata/content access ledger

CreativeDeploy content was not accessed, read, mounted, scanned, built,
tested, modified, stopped, or cleaned by this review.

The required historical ledger remains unchanged:

1. an implementation-era `find ..` exposed only a sibling path name;
2. an implementation-era unfiltered Docker inventory exposed only a
   CreativeDeploy container name/status.

Neither event was repeated. This review ran no unfiltered global Docker
diagnostic.

## 24. Remote, push, merge, PR, and tag status

- Remote: none
- Push: none
- Merge / fast-forward main: none
- Pull request: none
- Tag: none
- Customer 0: not run
- Later Phase 5 slice / Phase 6: not started

## 25. CONFIRMED / INFERRED / NOT VERIFIED ledger

### CONFIRMED

- Exact main and candidate hashes, exact parent, and one-commit range.
- Independent audit branch was created from the exact candidate.
- Two blocking Medium Findings are stable `3/3`.
- Their secure expectations remain unchanged.
- Audit-owned cleanup completed with no intentional persistent side effect.
- Production code is unchanged relative to the candidate.
- No current-review Docker command or unfiltered global Docker diagnostic.
- CreativeDeploy content was not accessed.
- No remote, push, merge, PR, or tag.

### INFERRED

- A missed governed timeout can extend resource use beyond the declared
  execution window. The broader operational/fleet effect is inferred; only
  the bounded local production-path behavior is confirmed.
- A clean cancellation acknowledgement can suppress operator-visible
  recovery action after cleanup failure. Broader operational impact is
  inferred from the confirmed lifecycle outcome.

### NOT VERIFIED

- The stopped third candidate boundary.
- Complete PASS for focused boundaries A, B, C, and E.
- The unexecuted portions of D and F.
- Phase 4 regressions, aggregate, E2E, Chaos, Docker runtime, Security, Eval,
  PostgreSQL/migration, build, and coverage.
- Remote CI, production, deployment, or customer behavior.

## 26. Recommended next action

Create a new production remediation branch from the Phase 5 candidate. Close
both blocking Medium Findings without changing their audit assertions, then
request a fresh independent focused review. That review must also dynamically
complete the currently stopped Runner-result budget and identity boundary
before any aggregate or PASS sealing is eligible.

**PHASE 5 FOCUSED SECURITY REVIEW FAIL — REMEDIATION REQUIRED**
