# Phase 5 Validation Suites Independent Focused Re-Audit and Sealing

- Started: 2026-07-30 +0800
- Repository: `/Users/danke/Developer/VisualEngineer`
- Main baseline: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Original focused-review FAIL checkpoint:
  `d325fa197e1fdad2c522fdf76f11b738682a86ca`
- Remediation candidate:
  `b6d53ba0275933e18919ceb2d90152e5ae8efcac`
- Branch: `audit/phase-5-validation-suites-reaudit-max`
- Status: `COMPLETE — INDEPENDENT FOCUSED RE-AUDIT PASS`

## Goal

Independently decide only:

1. `VE-P5-SUITES-FR-001` — one approved Suite Grant authorizes exactly one
   root/retry lineage attempt, with exact idempotent replay and fresh,
   lineage-bound retry authority.
2. `VE-P5-SUITES-FR-002` — Suite success requires a trusted child execution
   chain and complete, current, correctly ordered Evidence.

If both Findings and the previously stopped budget/race/cleanup boundaries
pass, run one final `make verify`, prove production-code invariance, and create
the authorized local sealing commit. A Critical, High, or blocking Medium
Finding stops the aggregate and produces an audit-only FAIL checkpoint without
repairing production code.

## Scope

Allowed writes are limited to independent audit tests, this ExecPlan, the
focused re-audit report, verification evidence, project status, and necessary
audit-governance documentation. Production code, migration, generated
contracts, Runner, Protocol, Web, Compose, infrastructure, and scripts are
read-only relative to the remediation candidate.

This review does not reopen Phase 4, the sealed Phase 5 first slice, the entire
Suite architecture, Customer 0, a later Phase 5 slice, or Phase 6.

## Non-goals

- Re-audit Phase 4 or the sealed Phase 5 first slice.
- Re-design the Suite architecture or add a Suite/Profile/command editor.
- Repair production code, migrations, generated contracts, Runner, Protocol,
  Web, Compose, infrastructure, or scripts.
- Exercise artifact transport, remote CI, production deployment, Customer 0,
  hostile multi-user operation, a later Phase 5 slice, or Phase 6.
- Move `main`, merge, push, create a pull request, or create a tag.

## Safety and independence

- All audit operations are anchored at the exact Developer repository.
- Docker operations use only the exact project
  `ve-p5-suites-reaudit-max` or an explicitly named final aggregate project
  and exact `com.docker.compose.project` label filters.
- No production repair is permitted.
- The historical FAIL report and original focused-review tests remain
  unchanged.
- No remote, push, pull request, tag, merge, main movement, or external
  repository access is permitted.
- Unknown ports, processes, containers, networks, and volumes are never
  stopped or removed.

## Decisions

1. Use a real PostgreSQL service under the exact focused project
   `ve-p5-suites-reaudit-max` and a preflighted published port. SQLite and
   mock persistence are insufficient for row locks, concurrency, constraints,
   and triggers.
2. Add four independent cases rather than copy the remediator's regressions:
   a retry/late-completion race, a foreign retry Grant, a coherent foreign
   ordered Evidence chain, and a legal two-step digest/replay/terminal fence.
3. Preserve every first failure. Audit-only formatting defects may be fixed
   mechanically; production behavior is never repaired in this review.
4. Reuse completed-source local images for the aggregate only after comparing
   the API and Runner image source-tree digests with the candidate and
   identifying the Web bundle's build-time API binding.
5. Keep historical FAIL artifacts byte-for-byte unchanged. This record closes
   only `VE-P5-SUITES-FR-001`, `VE-P5-SUITES-FR-002`, and the explicitly
   enumerated stopped boundaries.

## Risks

| Risk                                                  | Impact                     | Mitigation / result                                                                  |
| ----------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------ |
| row-lock or idempotency race is hidden by one session | false FR-001 PASS          | independent concurrent SQLAlchemy sessions; PASS                                     |
| coherent but foreign Evidence bypasses shallow checks | false FR-002 PASS          | full foreign two-step chain with correct ordering; denied with zero side effects     |
| old child completion contaminates a retry lineage     | cross-lineage success      | retry and completion released concurrently; old completion denied                    |
| local image differs from candidate                    | invalid aggregate evidence | API/Runner tree hashes match; Web exercised by 16 browser cases                      |
| build-time Web API URL differs from runtime port      | environmental E2E failure  | first mismatch preserved; bundle binding inspected and official port override used   |
| cleanup removes unrelated resources                   | destructive audit          | exact project labels and preflighted ports only; final filtered inventories are zero |

## Ordered work

1. Confirm the exact Git baseline, one-commit ancestry, refs, clean state, and
   unchanged historical audit tests.
2. Read the historical focused review, remediation evidence, full remediation
   diff, permanent regressions, Suite/Grant/Run/Evidence implementation,
   Migration 0009, state machine, API, Protocol, Runner, and bounded
   race/budget/cleanup tests.
3. Run the two unchanged original focused reproductions on real PostgreSQL.
4. Add independent cases that differ from the remediator's tests, including a
   Grant/retry race and a foreign or reordered Evidence rejection.
5. Run the Grant/lineage and trusted-aggregation matrices, then only the
   necessary combined-output, cancellation, late-completion, cleanup, and
   source/canonical-invariance boundaries.
6. Run focused API/Protocol/Runner checks and migration/contract checks.
7. If every focused boundary passes, run one final `make verify`, using only
   verified local images when the repository's supported skip-build controls
   are needed for an external registry failure.
8. Prove exact task-owned Docker cleanup, production-code invariance, main
   invariance, and allowed-file scope; complete the evidence/report/status and
   create the sealing commit.

## Progress

- done — exact root, branch, HEAD, main, status, diff, untracked, remote,
  stash, worktree, tag, ref, graph, object, ancestry, one-commit, subject,
  whitespace, lock, and target-branch preflight
- done — original focused-review test is unchanged and contains no
  skip/xfail marker
- done — independent branch created directly from the exact remediation
  candidate without overwriting a ref
- done — historical review/evidence/ExecPlan and remediation
  ExecPlan/evidence read completely
- done — complete one-commit remediation diff, Migration 0009, service,
  repository, models, state machine, API, Protocol, Runner, and bounded test
  review
- done — unchanged original focused reproductions pass `2/2` on real
  PostgreSQL
- done — four new independent cases pass `4/4`
- done — combined Suite/Grant/Evidence/budget/race/cleanup matrix passes
  `23/23`
- done — focused Protocol/Runner selection passes `6/6`
- done — fresh Migration 0009 base/head/base/head, contracts, and standalone
  source invariance pass
- done — final complete aggregate exits `0`; Python `252/252` at `83.33%`,
  Web `47/47`, Playwright `16/16`, Runner Security `111/111`, Eval 67, Chaos,
  migration, contracts, build, Docker, security, and invariance pass
- done — first audit-artifact formatting failure and first reused-Web-image
  port-binding failure are preserved; neither changed production code
- done — focused/final/E2E/Chaos container, network, volume, listener, and
  temporary image-alias cleanup verified
- done — production-code diff from the remediation candidate is empty and
  `main` remains unchanged
- done — report, evidence, status, and sealing-only scope prepared

## Discoveries

- The remediation candidate is exactly one commit after the original FAIL
  checkpoint and has the declared parent and subject.
- The original focused-review test hash is identical at the FAIL checkpoint,
  candidate, and working tree.
- Service row locks and PostgreSQL uniqueness/transition/Evidence triggers
  form complementary enforcement; neither layer alone is treated as proof.
- The candidate API image tree digest is
  `e62976f11b8478d748af44963674924c098dff1de86cd605b0ef293df42527c8`
  across 64 non-bytecode files. The Runner/Protocol digest is
  `3407dc104bc58644868d74626cfe357fa07d6a637a68eeb034cc4b0de54db152`
  across 22 files. Both match the candidate worktree.
- The reused Web bundle contains the build-time URL
  `http://127.0.0.1:38640`. A first aggregate E2E attempt used a different API
  port and produced browser failures/timeouts; no product assertion
  established a production failure.

## Verification

Exact commands, exit codes, first failures, reruns, counts, hashes, project
identities, cleanup, and final Git state are recorded in
`docs/evidence/phase-5-validation-suites-focused-reaudit-verification.md`.
The final decision is recorded in
`docs/security/audits/phase-5-validation-suites-focused-reaudit.md`.

| Gate                               | Exit | Result                           |
| ---------------------------------- | ---: | -------------------------------- |
| unchanged original focused tests   |    0 | `2 passed`                       |
| new independent focused tests      |    0 | `4 passed`                       |
| combined focused PostgreSQL matrix |    0 | `23 passed`                      |
| focused Protocol/Runner            |    0 | `6 passed`                       |
| fresh migration roundtrip          |    0 | base/head/base/head              |
| contracts drift                    |    0 | no diff                          |
| standalone source invariance       |    0 | PASS                             |
| final complete `make verify`       |    0 | complete aggregate PASS          |
| exact Docker cleanup probes        |    0 | zero containers/networks/volumes |
| production-code comparison         |    0 | empty diff                       |

## First failures and deviations

1. The first new-test static check failed import ordering and `zip()` strictness
   in the audit test only. Ruff fixed that file mechanically; the focused
   behavior run then passed.
2. The first aggregate invocation stopped at Prettier because this new
   ExecPlan was not formatted. No test, Docker, or product gate ran. The
   audit-only document was formatted and the full affected chain was rerun.
3. The next aggregate invocation reached E2E but the reused Web image was
   compiled for API port `38640` while the audit mapped `38741`. One browser
   case failed and two timed out; the task-owned process was interrupted and
   its trap cleaned the project. Bundle inspection confirmed the mismatch. A
   fresh preflight found the supported port free, and the final complete rerun
   used only official environment inputs and exited `0`.

No failed attempt was erased or reclassified as a product PASS.

## Rollback and cleanup

- Focused PostgreSQL:
  `TEST_POSTGRES_PUBLISHED_PORT=35730 docker compose -p ve-p5-suites-reaudit-max --profile test down -v --remove-orphans`
- Final PostgreSQL:
  `TEST_POSTGRES_PUBLISHED_PORT=35743 docker compose -p ve-p5-suites-reaudit-final-rerun --profile test down -v --remove-orphans`
- E2E and Chaos use their repository cleanup traps with exact project names.
- Exact post-cleanup label filters prove zero task-owned containers, networks,
  and volumes for all five focused/final project identities.
- Five temporary audit image aliases were removed; the original remediation
  tags retain the underlying images.
- Reversing the sealing record, if later authorized, should use a new revert
  commit. `main` was never moved by this task.

## Completion conditions

- [x] FR-001 PASS.
- [x] FR-002 PASS.
- [x] Required budget/race/cleanup boundaries PASS.
- [x] Critical 0, High 0, blocking Medium 0.
- [x] Final complete aggregate exit `0`.
- [x] Migration/contracts/E2E/Chaos/Docker/Security/Eval PASS.
- [x] Source and canonical Workspace invariance PASS.
- [x] Production-code diff from candidate empty.
- [x] Exact task-owned runtime inventories empty.
- [x] `main` unchanged and no remote/push/merge/PR/tag action.
- [x] Only independent tests and governance/evidence documents are eligible
      for the sealing commit.

## Outcome and follow-ups

`VE-P5-SUITES-FR-001` and `VE-P5-SUITES-FR-002` are independently closed for
the exact remediation candidate. The second slice is eligible for the local
sealing subject `chore: seal phase 5 governed validation suites`.

This is not authorization to move `main`, push, open a pull request, tag,
deploy, run Customer 0, start another Phase 5 slice, or start Phase 6. The next
eligible action is an explicitly user-authorized local main integration.
