# Phase 5 governed final review independent focused re-review

## Decision

- Candidate: `3eddb9623550227a30013df6dbc6dc7a17d5315c`
- Candidate parent / original FAIL:
  `5371495b1dd27db2ff3bbca4ddc12eaee47e7982`
- Main: `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Review branch: `audit/phase-5-governed-final-review-reaudit-max`
- Focused Re-Review: **FAIL**
- Final Aggregate: **NOT RUN**
- Critical / High / blocking Medium: **0 / 0 / 1**
- Production changes by reviewer: **none**

The remediation candidate is not eligible for PASS sealing or main
integration. The unchanged original focused matrix passes, but a distinct
real-PostgreSQL secure expectation confirms that one trusted revision fact can
be stale without advancing the Package generation. The database then accepts
an approved Decision and durable `ready` row for the old generation.

## Five-Finding matrix

| Finding               | Result                              | Independent disposition                                                                                                                                 |
| --------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VE-P5-REVIEW-FR-001` | **FAIL**                            | `VE-P5-REVIEW-RR-001`: revision authority is stale at the read boundary but remains current at the database generation boundary.                        |
| `VE-P5-REVIEW-FR-002` | **PASS in executed original scope** | The unchanged direct forged-digest reproduction is rejected. Expanded mismatch work stopped after the new blocker.                                      |
| `VE-P5-REVIEW-FR-003` | **PASS in executed original scope** | Direct Review AuditEvent update and delete are rejected. Extended event matrix stopped after the new blocker.                                           |
| `VE-P5-REVIEW-FR-004` | **PASS in executed original scope** | Expected-generation/keyed replay and one-winner concurrency tests pass. Additional race expansion stopped after the new blocker.                        |
| `VE-P5-REVIEW-FR-005` | **FAIL downstream**                 | Frozen zero-blocker fields are present, but approved-readiness correctness still fails because PostgreSQL accepts `ready` for the stale old generation. |

## Finding

### VE-P5-REVIEW-RR-001

- Severity: blocking Medium
- Trigger: change the trusted repository revision authority after creating a
  fresh Package, then exercise the database Decision/readiness boundary for
  that old generation.
- Expected: generation advances or the first stale approved insert fails
  closed; approved Decision, ready row, and success event counts remain zero.
- Actual: the API reports the Package stale, but generation and durable
  invalidation remain unchanged; PostgreSQL accepts one approved Decision and
  one `ready` row. No readiness-success AuditEvent or Git-delivery authority is
  created.
- Finding: revision freshness is not consistently enforced across the read
  and database canonicalization boundaries.
- Test:
  `test_p5_review_rereview_001_repository_revision_change_rejects_database_ready_chain`
- Stability: failed on the first run and one unchanged rerun at the same final
  secure assertion.
- Production-hash status: unchanged from candidate.

## Passing focused controls

- Original independent focused file: `6/6`.
- Original later-failed Validation invalidates old ready.
- Original forged Package/Decision/readiness digest chain is rejected.
- Direct Review AuditEvent update/delete is rejected.
- Concurrent approve/reject produces one terminal winner and one Decision
  event.
- Exact Decision key/payload replay and mismatched generation/key conflict
  controls pass.
- Git, pull-request, tag, deployment, and delivery-authority request injection
  remains rejected.
- The new failing test confirms Workspace and Evidence remain unchanged, no
  readiness-success event is appended, and every Grant retains false
  Git-delivery authority.

## Stop decision

The blocker rule applies. The remaining expanded freshness, Evidence,
AuditEvent, Decision, blocker-summary, Web/API, migration, browser, source
invariance, and aggregate matrices are not continued because they cannot
produce an eligible PASS while this stale database approval boundary remains
open.

`make verify`, the post-aggregate unique-project cleanup probe, and PASS
sealing are not run. Historical implementer aggregate results are not promoted
into this independent decision.

No API, migration, model, repository, service, Web, generated contract,
Runner, or other production file changed. Main is unchanged. No remote, push,
pull request, merge, tag, Customer 0, CreativeDeploy, later slice, or Phase 6
action occurred.

## Required next action

Implement a narrow remediation for `VE-P5-REVIEW-RR-001`, preserving this FAIL
checkpoint and its test assertion, then start another fresh independent
focused re-review from the remediation candidate.

**PHASE 5 THIRD SLICE FOCUSED RE-REVIEW FAIL — REMEDIATION REQUIRED**
