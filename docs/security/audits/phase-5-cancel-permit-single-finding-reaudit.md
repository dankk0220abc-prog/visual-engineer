# Phase 5 Cancel-Permit Independent Single-Finding Re-Audit

- Review date: 2026-07-30 (Asia/Shanghai)
- Remediation candidate:
  `c9e5268f1287f49ac0ba5c5d26045395b8e72dc0`
- Independent FAIL checkpoint:
  `4ce5a1a8e63ec530517f17ae82fc3aeb7747c4de`
- Main baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Review branch: `audit/phase-5-cancel-permit-single-finding-max`
- Independence: no production implementation was changed
- Status: **COMPLETE**
- Single-Finding decision: **PASS**
- mypy governance decision: **PASS**
- Final Aggregate: **FAIL — ENVIRONMENTAL PORT COLLISION**
- Overall Gate: **FAIL**

## 1. Completion status

The authorized single-finding and mypy-governance review is complete.
`VE-P5-FREAUD-001` is independently closed on the remediation candidate, and
strict mypy independently discovers every named Phase 5 focused-review,
re-audit, remediation, and current audit test.

The overall first-slice sealing Gate is nevertheless **FAIL** because the one
authorized final `make verify` stopped in E2E setup with exit `2`: TCP
`127.0.0.1:18000` was already in use before the audit-owned API container
could bind. The task permits a second full aggregate only after an audit-test
or documentation-format failure. This was neither, so no second aggregate was
started and the reserved PASS sealing subject was not used.

No new production security Finding was discovered. The remaining blocker is
verification-environment availability, not evidence supporting another
production remediation.

## 2. Single-Finding decision

**PASS.**

Real-PostgreSQL production-path checks prove that successful active Validation
cancellation atomically reaches the required durable terminal state:

- Job: `cancelled`, no Result;
- Attempt: `cancelled`;
- Validation Run: `cancelled`;
- Validation step: `cancelled`;
- exact Side-effect Permit: `cancelled`, `terminal_at` set;
- Validation Evidence: absent;
- `job_succeeded`: absent;
- `side_effect_permit_completed`: absent; and
- canonical Workspace fingerprint: unchanged.

The original permanent independent reproduction passes unchanged. The new
independent case additionally proves that the now-terminal Attempt/Lease can
neither reopen nor complete the Permit.

## 3. mypy governance decision

**PASS.**

Configured verbose mypy discovery names all eight target files:

- API and Runner historical focused-review tests;
- API and Runner focused re-audit tests;
- API and Runner remediation tests;
- the cancel-Permit remediation test; and
- this review's independent test.

The modules are distinct despite the two historical shared basenames.
`strict = true` and `explicit_package_bases = true` remain enabled. No
targeted exclusion, shared `ignore_errors`, new blanket `# type: ignore`,
disabled error code, or relaxed untyped policy exists. Configured mypy reports:

```text
Success: no issues found in 91 source files
```

The candidate checked 90 files; the increase to 91 is exactly the additive
audit test.

## 4. Final Aggregate

**FAIL, exit `2`.**

The single authorized `make verify` passed:

- contract regeneration drift;
- repository format;
- Ruff and ESLint;
- mypy and TypeScript;
- Python/API/Runner/Protocol tests and coverage;
- Web tests and coverage;
- Next.js production build;
- all Compose rendering;
- empty-PostgreSQL migration roundtrip;
- permanent Phase 4 Finding controls and security-audit tests;
- source invariance; and
- the Phase 4 workspace security repair target.

It then failed before Playwright execution when the E2E API container could
not bind fixed host port `18000`. E2E behavior, Workspace Chaos, Workspace
Security, Validation Security, the later broad Security target, Eval, and the
aggregate's final `git diff --check` were not reached by that command.

The port owner was not inspected or stopped. The exact audit-owned E2E Compose
project cleaned itself to zero containers, networks, and volumes.

## 5. Git baseline and branch

Independently confirmed:

```text
main
928a89d2055d172bbd7c6670b42f668d103dcb03

independent FAIL checkpoint
4ce5a1a8e63ec530517f17ae82fc3aeb7747c4de

remediation candidate
c9e5268f1287f49ac0ba5c5d26045395b8e72dc0
```

The candidate parent is exactly `4ce5a1a...`, and the range contains exactly
one commit with subject:

`fix(validation): finalize permit on cancelled validation`

The audit branch was created without force directly from the candidate:

`audit/phase-5-cancel-permit-single-finding-max`

Preflight found a clean worktree/index/untracked inventory, one worktree, and
no remote, stash, tag, Git lock, or undisclosed candidate commit.

## 6. Production-code invariance

The frozen production/gate boundary contains 163 tracked entries and has
candidate `git ls-tree` digest:

`beae532e006bcf280a9b05a76e4286eaa344c1cffe3622a7a837c9cc00c018b5`

It covers API source/migrations, Runner source, Protocol source, Web source and
E2E, generated contracts, Dockerfiles, Compose, infrastructure, scripts,
`Makefile`, and `pyproject.toml`.

The review changes only one independent API test and audit/governance
documents. The production/gate diff from the exact candidate is empty.

## 7. Cancellation and Permit result

**PASS.**

The original Finding test passes once independently, the new independent case
passes, and the normal-cancel matrix passes `3/3`.

The direct post-acknowledgement transaction proves all five durable lifecycle
records terminate together. The Permit terminal timestamp is present, the
Permit cannot be used for late completion, no successful Result or Evidence
exists, no success/completion event exists, and the canonical Workspace is
unchanged.

## 8. Cleanup-failure non-regression

**PASS.**

The real-PostgreSQL cleanup matrix passes `2/2`:

- `validation_cleanup_failed`; and
- `validation_process_remained`.

Both retain failed Job/Attempt/Permit and `recovery_required` Validation
Run/step. Neither is misclassified as clean cancellation; no Result, Evidence,
success event, duplicate terminal event, or Workspace mutation appears.

## 9. Stale, replay, mismatch, and idempotency result

**PASS.**

The dedicated matrix passes `4/4`. It proves:

- stale Attempt and Lease fail closed;
- cross-Runner identity and mismatched persisted Validation Run cannot close
  either the target or an unrelated Permit;
- exact cancellation replay is idempotent;
- a stale terminal Lease replay is rejected;
- late completion is rejected;
- Permit timestamp and Validation Run version remain unchanged; and
- replay adds no event, Result, Evidence, or successful side effect.

## 10. Test counts and exit codes

| Selection                               | Exit | Result                 |
| --------------------------------------- | ---: | ---------------------- |
| original `VE-P5-FREAUD-001` test        |    0 | `1 passed`             |
| independent terminal Attempt/Lease test |    0 | `1 passed`             |
| normal-cancel PostgreSQL matrix         |    0 | `3 passed`             |
| cleanup-failure PostgreSQL matrix       |    0 | `2 passed`             |
| stale/replay/idempotency matrix         |    0 | `4 passed`             |
| Phase 5 Control Plane focused selection |    0 | `49 passed`            |
| focused Runner/Protocol selection       |    0 | `21 passed`            |
| relevant Runner/Workspace API selection |    0 | `23 passed`            |
| configured mypy                         |    0 | `91 source files`      |
| aggregate Python/API/Runner/Protocol    |    0 | `227 passed`, `82.95%` |
| aggregate Web unit tests                |    0 | `44 passed`            |
| final `make verify`                     |    2 | E2E port bind failure  |

Every focused behavior run used current candidate code. API matrices used a
real PostgreSQL service, not SQLite or mocks.

## 11. Final `make verify`

**FAIL, exit `2`; run count: exactly one.**

The failure is retained verbatim in the verification evidence. A second full
aggregate was not run. The branch is therefore not eligible for the reserved
commit:

`chore: seal phase 5 governed validation first slice`

## 12. Source and canonical Workspace invariance

`make source-invariance-check` passes before the aggregate and again inside
the aggregate:

```text
status = PASS
source entries = 119
Git objects = 10
status records = 2
extension markers = 0
```

Every independent PostgreSQL cancel, failure, mismatch, and replay case checks
the canonical Workspace fingerprint directly. No mismatch was observed.

## 13. New findings

- Critical: 0
- High: 0
- blocking Medium: 0
- non-blocking production security Findings: 0
- aggregate environment blockers: 1

The fixed-port collision is not classified as a production security Finding.

## 14. Remaining limitations

Because the final aggregate stopped during E2E setup:

- Playwright E2E/accessibility is not verified by this review;
- Workspace Chaos is not verified by this review;
- the later Workspace Security, Validation Security, broad Security, and Eval
  aggregate targets are not verified by this review; and
- remote CI, deployment, customer behavior, hostile multi-tenant execution,
  later Phase 5 slices, and Phase 6 remain unverified or out of scope.

Historical passing results are not promoted into this review's final
aggregate ledger.

## 15. Git checkpoint

This report belongs to a local FAIL audit checkpoint, not the Phase 5 PASS
sealing commit. A commit cannot embed its own object ID without changing that
ID; the exact checkpoint is reported in the post-commit administrative
handoff.

## 16. Worktree, index, and untracked inventory

Before the checkpoint, all changes are confined to:

- one independent audit test;
- the re-audit ExecPlan;
- this report;
- verification evidence; and
- project status.

After the local FAIL checkpoint, the worktree, index, and untracked inventory
must be empty.

## 17. CreativeDeploy, remote, and delivery status

- CreativeDeploy content access: none
- sibling/customer repository access: none
- remote: none
- push: none
- merge / main movement: none
- pull request: none
- tag: none
- Customer 0: not run
- later Phase 5 slice / Phase 6: not started

Four long-running current-repository platform services predated this review
and were left untouched. Every exact audit-owned PostgreSQL and E2E Compose
project has zero container/network/volume residue.

## 18. CONFIRMED / INFERRED / NOT VERIFIED ledger

### CONFIRMED

- Exact Git baseline, parent, one-commit candidate range, branch, and main.
- Historical Finding test integrity.
- `VE-P5-FREAUD-001` independently closes on real PostgreSQL.
- Cleanup failure does not regress.
- Stale/replay/mismatch paths fail closed and remain idempotent.
- Strict mypy discovers all eight target files and checks 91 sources.
- Format, lint, typecheck, empty-database migration, production-tree
  invariance, source/canonical Workspace invariance, and focused cleanup pass.
- The one final aggregate passes all recorded stages before E2E setup and
  fails with exit `2` on fixed port `18000`.
- No production code was changed.
- The audit-owned E2E project cleaned to zero resource residue.
- Main, remote, push, merge, pull request, and tag state are unchanged.

### INFERRED

- The four current-repository platform services were pre-existing: Docker
  reports 8–31 hours uptime, while this review ran for minutes.
- The fixed port was occupied by external local state rather than candidate
  behavior; the owner was deliberately not inspected.

### NOT VERIFIED

- A complete exit-0 final aggregate.
- Playwright E2E/accessibility and every aggregate target after E2E.
- Remote CI, deployment, production, customer, or hostile multi-tenant use.
- Any scope outside this first governed-validation vertical slice.

## 19. Recommended next action

Do not modify production code or merge main. The user should first make fixed
E2E port `18000` available, or explicitly authorize a fresh aggregate with
isolated alternate ports. Then a new independent continuation may run one
complete aggregate. Only an exit-0 result may create the reserved Phase 5
sealing commit and authorize a recommendation for user-controlled main
integration.

**PHASE 5 SINGLE-FINDING RE-AUDIT FAIL — REMEDIATION REQUIRED**
