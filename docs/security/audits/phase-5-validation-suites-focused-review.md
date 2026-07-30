# Phase 5 Governed Validation Suites Independent Focused Security Review

- Review date: 2026-07-30 (Asia/Shanghai)
- Main baseline:
  `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Candidate:
  `10399722e37f3209fa08e5e7edc25f31b429aaad`
- Review branch: `audit/phase-5-validation-suites-focused-max`
- Independence: no production implementation was changed
- Status: **COMPLETE**
- Focused Security Review: **FAIL**
- Required next state: **REMEDIATION REQUIRED**

## 1. Completion status

The independent focused review is complete as a FAIL review. Two ordinary
secure-expectation tests reached candidate API/database behavior and exposed
two blocking Medium Findings. Each Finding reproduced on its initial run and
two unchanged focused reruns (`3/3` stable).

The contract's stop condition then applied. The review preserved the minimal
reproductions, classified the Findings, proved audit-owned cleanup and
production-tree invariance, and did not continue into the final aggregate.

## 2. Focused Security Review

**FAIL.**

- Critical: 0
- High: 0
- blocking Medium: 2
- non-blocking new Findings: 0

The verdict follows from independent real-PostgreSQL tests. Candidate
implementer evidence is retained as historical context and is not promoted to
independent PASS evidence.

## 3. Final aggregate

**NOT RUN.**

`make verify` was permitted only after all seven focused boundaries passed
without a Critical, High, or blocking Medium Finding. That prerequisite is
false. Final E2E, Chaos, broad Docker, Security, Eval, coverage, and PASS
sealing were therefore also not run.

## 4. Git baseline and branch

The independently confirmed one-commit history is:

```text
main f547091307c52df8f20fc69bac4b4826cbbc74ad
  -> candidate 10399722e37f3209fa08e5e7edc25f31b429aaad
```

The candidate's exact parent is main, `main..candidate` contains one commit,
and the candidate tree is
`45a4d666eafd6a4e17bddfaef05cafaa67715d59`.

The review branch was created directly from that candidate without force:

```text
audit/phase-5-validation-suites-focused-max
```

Preflight found a clean candidate worktree and index, no untracked files, no
remote, stash, tag, Git lock, replacement/notes ref, hidden candidate ref, or
additional worktree. `git fsck --no-reflogs --unreachable` reported only
pre-existing historical dangling objects with no referencing ref. They were
disclosed and left untouched.

## 5. Independence and production-code invariance

The frozen production boundary contains 159 candidate entries with
`git ls-tree` SHA-256:

```text
7df6b3b54aceb945c3f2bbb9c6a33c93060aa3b4f58237a2f8badfab286d432d
```

It covers API source and migrations, Runner source, Web source, Protocol
source, Dockerfiles, Compose, infrastructure, scripts, and `Makefile`.

The review changed only:

- one independent audit test file;
- one focused ExecPlan;
- this audit report;
- one verification evidence record;
- project status; and
- the active-plan governance pointer.

`git diff --exit-code candidate -- <frozen production paths>` exits `0`. No
production behavior was repaired by this review.

## 6. Seven-boundary decision matrix

| Boundary                                                 | Decision               | Independent evidence                                                                                                                                                                       |
| -------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A. Suite definition immutability and exact Grant binding | **FAIL**               | The same approved Suite Grant creates another Suite attempt when only the idempotency key changes (`VE-P5-SUITES-FR-001`).                                                                 |
| B. Step ordering and injection prevention                | **FAIL**               | A direct persisted-step state injection is accepted and becomes aggregate success (`VE-P5-SUITES-FR-002`). The complete reordered/duplicate/missing-step matrix stopped after the blocker. |
| C. Suite/step state consistency                          | **FAIL**               | Pending/queued steps can be promoted directly to success; lazy synchronization trusts those rows.                                                                                          |
| D. Cancellation and retry fencing                        | **FAIL**               | A second attempt can be created without the required fresh Grant. The complete independent cancellation-race matrix was not run.                                                           |
| E. Per-step and Suite budgets                            | **NOT FULLY VERIFIED** | Candidate control tests for exact output limit and limit-plus-one pass within `10/10`; no complete independent budget matrix was run after the stop condition.                             |
| F. Aggregate Result/Evidence integrity                   | **FAIL**               | A succeeded aggregate Result is created with zero Evidence references.                                                                                                                     |
| G. Cleanup and invariance                                | **PARTIAL PASS**       | Exact review-owned Docker cleanup and production Git invariance pass. Full runtime sandbox/source/canonical invariance is not verified.                                                    |

Because A, B, C, D, and F do not pass, the focused Gate is FAIL.

## 7. Suite definition immutability and Grant binding

The request schema and catalog statically bind the known Suite ID/version, and
the candidate materializes the catalog's two ordered Profiles. Those controls
do not make the approved Suite Grant single-attempt authority.

`VE-P5-SUITES-FR-001` starts the first Suite normally and then repeats the same
create request with the same approved Grant and a fresh idempotency key.
Expected behavior is a typed conflict with unchanged Suite and child-run
counts. Actual behavior is HTTP `201`, with Suite rows and child Validation Run
rows for that Grant both increasing from one to two.

Static review is consistent with the observation:

- Suite Grant issuance budgets child Validation Runs as
  `max_attempts * step_count`;
- Suite create checks only global idempotency-key replay and the active Grant;
  and
- neither the model nor service enforces one root Suite attempt per Grant.

The Web action also generates a new idempotency key for each click while the
approved Grant remains available.

## 8. Step ordering and injection prevention

The catalog and normal create path statically materialize fixed sequences and
fixed Profile references. The database trigger protects definition columns
from later edits.

However, the trigger does not enforce legal step-state transitions or require
the exact child-run identity and Evidence before `succeeded`. The independent
test updates only allowed mutable summary columns, so it is not blocked as a
definition mutation. The complete independent reordered, duplicate, missing,
foreign-child, and foreign-Evidence matrix was stopped after this conclusive
failure and remains not verified.

## 9. Suite/step state consistency

**FAIL — `VE-P5-SUITES-FR-002`.**

Both persisted steps can move directly from their pre-execution state to
`succeeded` with terminal summary fields but without child Evidence. A normal
Suite detail API read performs lazy synchronization, sees all step states as
successful, and finalizes the Suite and aggregate Result as `succeeded`.

Observed independent tuple:

```text
HTTP 200, Suite succeeded, aggregate verdict succeeded, Evidence references 0
```

The secure expectation is rejection at the database transition boundary or
fail-closed revalidation by the Control Plane.

## 10. Cancellation and retry fencing

The candidate's current Suite control file passes its normal cancellation,
timeout, and one bounded retry scenarios within `10/10`. Those controls do not
close `VE-P5-SUITES-FR-001`.

A retry endpoint requires a fresh Grant, but the root create endpoint accepts
the original approved Grant again under a new idempotency key. That creates a
parallel second root attempt and bypasses the governed retry path. The broader
independent cancel-before-dispatch, cancel-during-child, completion/cancel
race, stale replay, and retry Evidence-reuse matrix was not run after the stop
condition.

## 11. Per-step and Suite-level budgets

**NOT FULLY VERIFIED.**

The unchanged candidate Suite tests include exact output-limit success and
limit-plus-one rejection, and the complete candidate Suite control file passes
`10/10` on the review database. Coverage was disabled and no complete
independent matrix for combined bytes, time, artifact count/bytes, replay
charging, or reused Evidence accounting was run.

No budget PASS is inferred from implementer evidence or the limited control
selection.

## 12. Aggregate Result and Evidence integrity

**FAIL — `VE-P5-SUITES-FR-002`.**

Aggregate finalization builds Evidence references only when an optional
persisted `evidence_id` exists. Its success predicate checks step state,
baseline, cleanup summary, and combined output, but does not require one exact,
current-run, ordered Evidence object per successful step.

The independent test therefore obtains a durable successful aggregate with an
empty Evidence-reference list. Persisted step summaries have substituted for
execution proof.

## 13. Cleanup and invariance

**PASS for review-owned cleanup and production Git invariance; otherwise NOT
VERIFIED.**

The unique Compose project
`ve-p5-suites-focused-audit` was removed with its volumes and orphans. Filtered
post-cleanup inventories for that exact project return no container, network,
or volume IDs. No unknown process, container, network, or volume was stopped
or removed.

The frozen production-path diff against the exact candidate is empty, and
main remains unchanged. Full dynamic sandbox/source/canonical Workspace
invariance was not run after the blockers.

## 14. Historical regression status

The unchanged current candidate Suite test file passes `10/10` on real
PostgreSQL and serves only as a focused control. The complete sealed Phase 5
first-slice selections, Phase 4 regressions, and historical independent audit
selections were not rerun.

Existing independent first-slice security tests were not changed, deleted,
weakened, skipped, or marked expected-failing.

## 15. PostgreSQL, Migration, API, and Protocol

- Real PostgreSQL: **USED** on the exact review-owned Compose project.
- Migration upgrade to head: **PASS** through clean test fixture setup,
  including revision `20260730_0008`.
- Full base/head/base/head migration roundtrip: **NOT RUN**.
- API: **USED** through production FastAPI routes and database services.
- Protocol and Runner dynamic suite coverage: **NOT INDEPENDENTLY RUN** after
  the stop condition.
- Static contract/Protocol/Runner/Web review: **COMPLETE as review context**,
  not a dynamic PASS.

## 16. Final `make verify`

**NOT RUN; exit code N/A.**

This is the contractually required response to a stable blocker, not an
environment failure. The candidate's earlier aggregate result remains
implementer evidence only.

## 17. Test, coverage, E2E, Chaos, Docker, Security, and Eval status

Executed:

- independent audit file initial run: `2 failed`, exit `1`;
- each Finding selected twice more: one failure each run, exit `1`;
- unchanged candidate Suite control file: `10 passed`, exit `0`;
- audit-test Ruff format/check: exit `0`;
- one isolated PostgreSQL Compose project startup and exact cleanup.

Coverage was disabled with `--no-cov`.

Not run after the stop condition: complete backend/Runner/Protocol/Web suites,
Web build, browser/E2E/accessibility, Chaos, broad Docker isolation, broad
Security, Eval, and final aggregate.

## 18. First failures and stability reruns

The first independent behavior command ran both audit tests. Both failed on
their secure expectations:

```text
2 failed, exit 1
```

The observed tuples were:

```text
VE-P5-SUITES-FR-001: (201, 1, 2, 1, 2)
VE-P5-SUITES-FR-002: (200, "succeeded", "succeeded", 0)
```

Each test was then selected twice more without changing test or candidate.
Each produced the same assertion and exit `1`. Stable totals are:

```text
VE-P5-SUITES-FR-001: 3 failures / 3 runs
VE-P5-SUITES-FR-002: 3 failures / 3 runs
```

No production fix, assertion weakening, skip, `xfail`, or expected-failure
conversion occurred.

## 19. New Findings

| Finding               | Boundary                                    | Trigger                                                                                        | Expected                                                                                     | Actual                                                                                | Severity        | Stable tests | Exit     | Persistent audit side effect                                                     |
| --------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------- | -----------: | -------- | -------------------------------------------------------------------------------- |
| `VE-P5-SUITES-FR-001` | Suite attempt and retry authority           | Reuse the same approved Suite Grant with a new idempotency key.                                | Typed denial; one Suite attempt and unchanged child-run count; retry requires a fresh Grant. | HTTP `201`; a second Suite and child Validation Run are created under the same Grant. | blocking Medium |        `3/3` | `1` each | No; transaction fixtures rolled back and the exact database project was removed. |
| `VE-P5-SUITES-FR-002` | Step state and aggregate Evidence integrity | Persist successful step summaries without child Evidence, then read the Suite through its API. | Database or Control Plane rejects the transition/finalization.                               | Suite and Result become `succeeded` with zero Evidence references.                    | blocking Medium |        `3/3` | `1` each | No review-owned residue; the reproduction remains only as an audit test.         |

The preserved minimal reproductions are in
`apps/api/tests/test_phase5_validation_suites_focused_review.py`.

## 20. Remaining limitations

These are unverified boundaries, not additional Findings:

- the complete step-order/duplicate/missing/foreign-binding matrix;
- full cancel/timeout/completion race and stale-replay fencing;
- the complete per-step/aggregate time, output, artifact, and replay budget
  matrix;
- successful retry Evidence reuse and exact billing behavior;
- full sandbox/source/canonical Workspace invariance;
- full migration roundtrip;
- complete historical regressions;
- Web/E2E/accessibility, Chaos, broad Docker, Security, Eval, coverage, and
  aggregate verification;
- remote CI, hostile multi-tenant operation, deployment, and customer
  repositories.

## 21. Git FAIL checkpoint

This report belongs to a local audit-only FAIL checkpoint. It is not the
reserved PASS sealing commit. A commit cannot embed its own final object ID
without changing that ID, so the exact checkpoint hash is reported in the
post-commit administrative handoff.

## 22. Worktree, index, and untracked inventory

The candidate started clean. Before checkpoint, every changed/untracked path
is in the review allowlist described in section 5. After checkpoint, the
worktree, index, and untracked inventory must be empty; that result is reported
administratively after the commit.

## 23. External and delivery boundaries

No remote, fetch, pull, push, merge, pull request, tag, deployment, Customer 0,
CreativeDeploy, sibling repository, later Phase 5 slice, or Phase 6 action was
performed. No unknown Docker or host resource was modified.

Main was inspected read-only and was not moved.

## 24. Confirmed, inferred, and not verified

**CONFIRMED**:

- exact main/candidate ancestry and independent branch;
- two stable blocking Medium Findings on real PostgreSQL;
- unchanged candidate Suite controls `10/10`;
- review-owned Docker cleanup;
- production-tree and main invariance; and
- no production edit or delivery action.

**INFERRED from static review, consistent with dynamic evidence**:

- the missing one-Suite-per-Grant constraint/service check enables
  `VE-P5-SUITES-FR-001`;
- the missing legal step-transition and mandatory Evidence validation enables
  `VE-P5-SUITES-FR-002`; and
- the Web can repeat the root create because it generates a fresh idempotency
  key for the still-approved Grant.

**NOT VERIFIED**:

- every remaining item in section 20;
- any broad Security Gate PASS;
- PASS sealing, main integration, or later-phase authorization.

## 25. Decision and next action

The candidate is not approved for PASS sealing, main integration, Customer 0,
a later Phase 5 slice, or Phase 6.

The next eligible milestone is a narrowly scoped production remediation that:

1. makes one approved Suite Grant authorize only one root Suite attempt while
   preserving idempotent replay and fresh-Grant retry; and
2. enforces legal step transitions plus exact ordered current-run Evidence
   before successful aggregate finalization.

That remediation requires a fresh independent focused re-review. The stopped
boundaries and final aggregate remain mandatory before any PASS.

**PHASE 5 SECOND SLICE FOCUSED REVIEW FAIL — REMEDIATION REQUIRED**
