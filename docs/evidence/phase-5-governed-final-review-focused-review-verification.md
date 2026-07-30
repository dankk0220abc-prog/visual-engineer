# Phase 5 governed final review focused-review verification

## Identity and status

- Date: 2026-07-30 +08:00
- Repository: `/Users/danke/Developer/VisualEngineer`
- Main: `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Candidate: `c2054469c8d10441bcab8ade89c52de1f9aa893f`
- Candidate parent: `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Candidate range count: `1`
- Branch: `audit/phase-5-governed-final-review-focused-max`
- Result: `FOCUSED REVIEW FAIL — REMEDIATION REQUIRED`
- Aggregate: `NOT RUN`

## Git preflight ledger

All requested preflight commands were run from the exact repository root.

| Command group                                  | Exit | Result                                                            |
| ---------------------------------------------- | ---: | ----------------------------------------------------------------- |
| `pwd`; `git rev-parse --show-toplevel`         |    0 | exact Developer repository                                        |
| branch, HEAD, main                             |    0 | feature candidate and declared hashes exact                       |
| porcelain-v2, tracked/cached stat, untracked   |    0 | clean                                                             |
| remote, stash, worktree, tag, heads            |    0 | no remote/stash/tag; one expected worktree; disclosed local heads |
| graph/log and object-type checks               |    0 | both declared objects are commits; history present                |
| ancestor, range count, candidate parent        |    0 | ancestor true; count `1`; parent equals main                      |
| `git diff --check main..candidate`             |    0 | clean                                                             |
| Git lock inventory                             |    0 | empty                                                             |
| audit branch existence                         |    1 | expected absent before creation                                   |
| audit branch creation and post-switch identity |    0 | exact candidate; clean                                            |

The candidate deletes no file. Historical Phase 5 FAIL/remediation/sealing
records remain present. The candidate test diff contains no skip, xfail, or
existing test deletion.

## Read and review coverage

The review completely read the repository agent contract, planning standard,
README, security policy, Makefile, project status, Third Slice ExecPlan and
evidence, ADR 0018, changed architecture/state/security/product documents,
Runner threat model, Validation Suite runbook, migration, Review models,
repository, schemas, service, API, trusted Suite manifest extension, Web
workflow, candidate backend/Web/E2E tests, Eval mapping, and the complete
candidate file range.

No Third Slice-specific threat-model or review runbook file exists in the
candidate range. This is recorded as a limitation, not a separate security
Finding.

## Candidate baseline

An exact isolated Compose project and bind-probed port ran:

`make review-security-check`

- Exit: `0`
- Result: `7 passed`
- Meaning: candidate-owned focused scenarios pass; this is implementer
  coverage, not an independent Gate decision.

## Independent audit matrix

Primary final command:

`pytest apps/api/tests/test_phase5_governed_final_review_focused_audit.py --no-cov -q`

The command used a unique task-owned PostgreSQL Compose project, a free
loopback port, and a local test connection supplied only through the process
environment.

- Exit: `1`
- Result: `4 failed, 2 passed`
- Warning: one unrelated TestClient deprecation warning.

| Test                                                                            | Exit disposition | Finding/control                      |
| ------------------------------------------------------------------------------- | ---------------- | ------------------------------------ |
| `test_p5_review_aud_001_later_failed_validation_revokes_existing_ready`         | FAIL             | `VE-P5-REVIEW-FR-001`                |
| `test_p5_review_aud_002_database_rejects_forged_digest_ready_chain`             | FAIL             | `VE-P5-REVIEW-FR-002`                |
| `test_p5_review_aud_003_review_audit_events_reject_update_and_delete`           | FAIL             | `VE-P5-REVIEW-FR-003`                |
| `test_p5_review_aud_004_concurrent_approve_reject_has_one_winner_and_one_event` | PASS             | concurrency and exact payload replay |
| `test_p5_review_aud_005_review_api_rejects_git_pr_delivery_injection`           | PASS             | approval/delivery separation         |
| `test_p5_review_aud_006_decision_requires_generation_and_keyed_idempotency`     | FAIL             | `VE-P5-REVIEW-FR-004`                |

`VE-P5-REVIEW-FR-001` was rerun unchanged after the corrected fixture and
failed again at the exact freshness assertion. `FR-002` and `FR-003` repeated
unchanged across focused runs. `FR-004` also failed independently because the
Package response has no freshness generation.

## First failures and audit-only corrections

1. **INVALID_ATTEMPT:** the first `FR-001` construction requested a second
   root Suite Grant after success. Existing Suite lineage policy correctly
   returned `409` before the intended freshness assertion. The audit test was
   changed to the allowed separately approved fixed-Profile Validation path.
2. **INVALID_ATTEMPT:** the next `FR-001` run used a helper that assumes every
   completed Runner Job succeeds. Production correctly returned `failed`;
   the helper assertion stopped before freshness. The audit test was changed
   to call the same completion API directly and assert the negative terminal
   state.
3. **AUDIT-ONLY FORMAT FAILURE:** initial Ruff format-check requested layout
   changes in the new audit file. Only that test file was formatted. Final
   Ruff format-check and lint pass.
4. **AUDIT-ONLY DOCUMENT FORMAT FAILURE:** initial Prettier check requested
   layout changes in the three new review documents. Only those new documents
   were formatted. Final Prettier check passes, including the updated project
   status.

Neither invalid attempt is a production Finding. The corrected test preserves
the same intended security assertion and reaches it reliably.

## Static confirmations

- Review Package and verdict digest columns have format checks, but the
  database guards do not recompute their canonical values.
- Package digest construction includes a random Package UUID and has no
  freshness-generation field.
- Decision request/model/table have no expected generation, independent
  Decision idempotency key, or request hash.
- Readiness service chooses `ready` from fresh plus approve and has no trusted
  Critical/High/blocking-Medium inputs.
- Third Slice immutability triggers cover the four review tables, not
  `audit_events`.

## Stopped gates

Because blocking Medium incorrect-readiness, digest-forgery, and
audit-forgery Findings are confirmed:

- final `make verify`: **NOT RUN**
- project-label-only Docker cleanup probe after aggregate: **NOT RUN**
- migration roundtrip: **NOT RUN in this independent review**
- real browser E2E/accessibility: **NOT RUN in this independent review**
- broad Security/Eval/Chaos: **NOT RUN in this independent review**
- PASS sealing: **NOT ELIGIBLE**

Candidate implementation evidence for those gates remains historical only.

## Production invariance and cleanup

Before audit documents, `git diff --name-only` from the candidate contained
only the new untracked audit test. Production source diff was empty.

Seven exact audit-owned Compose projects were inspected by project label after
their cleanup traps:

- containers: `0`
- networks: `0`
- volumes: `0`

No unknown process or port owner was stopped. No CreativeDeploy or sibling
repository was accessed. No remote, push, pull request, merge, tag, Customer
0, later slice, or Phase 6 action occurred.

## Checkpoint boundary

The FAIL checkpoint may contain only:

- `apps/api/tests/test_phase5_governed_final_review_focused_audit.py`
- `docs/exec-plans/phase-5-governed-final-review-focused-review.md`
- `docs/security/audits/phase-5-governed-final-review-focused-review.md`
- `docs/evidence/phase-5-governed-final-review-focused-review-verification.md`
- `docs/status/project-status.md`

The exact checkpoint hash and final clean state are recorded administratively
after commit.

**PHASE 5 THIRD SLICE FOCUSED REVIEW FAIL — REMEDIATION REQUIRED**
