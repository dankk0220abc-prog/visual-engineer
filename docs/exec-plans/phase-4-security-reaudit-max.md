# Phase 4 Independent Security Re-Audit

- Started: 2026-07-28 (Asia/Shanghai)
- Branch: `audit/phase-4-security-reaudit-max`
- Repair commit:
  `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c`
- Repair base / original independent audit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4 implementation:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Auditor role: independent; not the security-repair implementer
- Status: COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED

## Goal

Independently determine whether the Phase 4 security-repair commit closes all
six preserved findings and satisfies the fixture-only Security Gate. The
decision must come from current Git, code, PostgreSQL, Docker, filesystem,
protocol, browser, chaos, security, Eval, and aggregate verification evidence,
not from the repair summary or its reported test totals.

## Scope

Permitted changes are limited to:

- this independent ExecPlan;
- an independent re-audit report and verification evidence;
- additive independent security tests and synthetic fixtures;
- audit-test documentation and Make wiring when strictly needed; and
- the project status after the independent Gate decision.

Production implementation, migrations, contracts, runtime configuration, and
existing assertions are read-only during the re-audit.

The frozen production boundary is:

- `apps/api/src`
- `apps/runner/src`
- `packages/runner-protocol/src`
- `compose.yaml`
- `infra`
- `apps/api/alembic`
- `apps/api/Dockerfile`
- `apps/runner/Dockerfile`

At the repair commit this boundary contains 71 tracked files. The current
worktree SHA-256 content-manifest digest is
`3d86a5d2d423a73a3819d06e45289a6e1050d09b96595577f16c4aee94fc3147`;
the Git-tree listing digest is
`eacd9a8f554c63832c67b17ea43a23657ce9fee25e23cf606d23870a2ebe89a8`.

## Non-goals

- No production-code repair.
- No CreativeDeploy or customer-repository access, mount, scan, build, test,
  read, write, or cleanup.
- No shell or arbitrary target-repository command capability.
- No LLM, Agents SDK, Git delivery, remote, push, pull request, merge, tag,
  deployment, or Phase 5 work.
- No claim of hostile multi-tenant, hostile-code, production, or remote-CI
  safety.

## Constraints and safety

- Any Critical, High, blocking Medium, strict source-invariance failure,
  production-hash drift, or mandatory verification failure makes the Security
  Gate fail.
- A discovered production defect is preserved as a minimal reproduction and
  remediation requirement; it is not fixed during this audit.
- Tests use only generated synthetic repositories and exact audit-owned
  PostgreSQL/Compose resources.
- No existing test is deleted, skipped, weakened, or converted to a mock in
  place of required PostgreSQL, Docker, disk, or browser evidence.
- No dangerous Git cleanup, reset, stash, branch overwrite, or global/system
  configuration is permitted.
- `main`, the Phase 4 branch, the original audit branch, and the repair branch
  must remain unchanged.

## Progress

### 2026-07-28

- DONE: read the complete external re-audit instruction.
- DONE: confirmed the real repository root is
  `~/Developer/VisualEngineer`, distinct from the desktop attachment
  workspace.
- DONE: confirmed a clean repair worktree and index, absent remote, absent
  stash/submodules/additional worktrees/local patches, and no target re-audit
  branch.
- DONE: confirmed all four candidate commits exist and form the exact ancestry
  `main -> Phase 4 -> original audit -> repair`.
- DONE: confirmed the repair is exactly one commit after the original audit,
  with 68 changed files, 7,501 insertions, 571 deletions, and a clean
  `git diff --check`.
- DONE: created this independent branch directly from the full repair hash.
- DONE: froze the 71-file production boundary and confirmed no initial diff
  from the repair commit.
- DONE: read `AGENTS.md`, `PLANS.md`, `README.md`, `SECURITY.md`, project
  status, the preserved audit plan/report/evidence, the repair plan/evidence,
  the preserved blocking reproductions, ADR 0014-0016, data/state/protocol/
  permission/Workspace documents, the Workspace recovery/lifecycle and Runner
  runbooks, and the Runner/Workspace threat models.
- DONE: inventory the complete 68-file repair diff and perform focused static
  review of all six Finding controls, with line-level review of the three
  defect paths.
- DONE: add three independent adversarial tests without weakening the four
  preserved repair regressions.
- DONE: preserve the first third-test `NameError`, correct only its missing
  audit-test import, and rerun the single test, all three new tests, the four
  preserved tests, and the complete seven-test file.
- DONE: independently reproduce a Critical Git object-closure defect, a High
  discard recovery defect, and a blocking Medium process-group timeout defect.
- DONE: run strict source invariance, real PostgreSQL migration and focused API
  tests, contracts, Runner/Protocol checks, Compose rendering, immutable
  reference review, API health, and live Docker isolation probes.
- DONE: create the formal re-audit report, verification evidence, and project
  status update.
- STOPPED BY GATE: full Web/browser/E2E, smoke, chaos, security/Eval,
  repair-aggregate, and final `make verify`. They cannot close the stable
  Critical, High, and blocking Medium failures and are recorded as
  `NOT VERIFIED`, not PASS.
- DONE PRE-CHECKPOINT: final audit-file formatting/lint/typecheck/diff checks
  and production digest comparison. The scoped commit hash and final clean
  worktree/index confirmation are reported in the handoff because this plan
  cannot record the hash of the commit that contains it.

## Decisions

1. **Treat repair evidence as untrusted claims.** It is useful for locating
   intended controls and historical failures but supplies no independent
   closure.
2. **Preserve the original FAIL.** The original report and tests remain
   permanent history; re-audit evidence is separate and additive.
3. **Use a wider production freeze.** The boundary includes all API/Runner
   sources, protocol sources, migrations, Compose/infra, and API/Runner
   Dockerfiles so audit-only work cannot conceal implementation drift.
4. **Fail closed on environment or scope mismatch.** A dirty or unexpected
   state stops the audit rather than being cleaned or repaired.

## Risks

| Risk                                                | Likelihood / impact | Mitigation                                                                     |
| --------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------ |
| A synthetic Git fixture mutates source unexpectedly | medium / critical   | exact no-follow before/after manifests and immediate stop                      |
| A concurrency probe becomes unbounded               | medium / high       | independent transactions, deterministic barriers, and explicit timeouts        |
| Audit edits cross into production                   | low / critical      | frozen path manifest plus final path/diff/hash comparison                      |
| Docker evidence reuses stale state                  | medium / high       | render exact configuration, inspect live IDs, and use exact isolated resources |
| Passing tests miss a production attack path         | medium / critical   | trace every test to the production path and add distinct adversarial cases     |

## Discoveries

- The first batch form of `git merge-base` failed with exit 128 because zsh
  did not split a quoted pair variable into two arguments. The explicit
  two-argument rerun exited zero for all ancestry checks. The failed command
  changed no repository state.
- The repair diff statistics exactly match the candidate report, but this is
  only a Git-baseline confirmation and not a security conclusion.
- The repair expands the frozen production boundary from the original audit's
  69 files to 71 through the security migration and ownership implementation.
- The source-less object copy traverses all regular loose and packed object
  entries rather than selecting only the approved revision's reachable
  closure. The independent synthetic assertion fails consistently.
- The registry-missing discard fallback uses expected-root absence as
  sufficient evidence of completion. It does not require trusted signed
  pending-discard proof and fails the independent recovery assertion.
- The bounded-output collector can perform a blocking read after the process
  leader exits, bypassing its deadline while a descendant keeps the pipes
  open. Group termination also returns early after leader exit. The corrected
  independent test fails consistently.
- The first execution of that third test did not reach production because
  `GitOperationError` was omitted from the audit-test import. This is retained
  as a test defect, corrected only in the audit test, and not counted as a
  production Finding.

## Re-Audit matrix

| Finding         | Severity | Independent static review                                                       | Independent dynamic reproduction                     | New adversarial test                    | Side effects                                 | Remaining risk                       | Gate status                          |
| --------------- | -------- | ------------------------------------------------------------------------------- | ---------------------------------------------------- | --------------------------------------- | -------------------------------------------- | ------------------------------------ | ------------------------------------ |
| `VE-P4-AUD-001` | Critical | source Git execution removed, but object copy lacks reachable-closure selection | unreachable unapproved object appears in mirror      | stable FAIL                             | source fixture only; Workspace file absent   | unapproved object retention          | **FAIL / OPEN / BLOCKING**           |
| `VE-P4-AUD-002` | Critical | Permit binding/DB controls reviewed                                             | 8 focused real PostgreSQL tests pass                 | complete new concurrency matrix stopped | focused cases report zero unauthorized write | full independent closure absent      | **NOT VERIFIED / OPEN / BLOCKING**   |
| `VE-P4-AUD-003` | High     | signed normal ownership path exists; registry/root-absent fallback is fail-open | discard reports success without signed pending proof | stable FAIL                             | safely preserved synthetic root; no deletion | recovery can be suppressed           | **FAIL / OPEN / BLOCKING**           |
| `VE-P4-AUD-004` | Critical | strict no-follow harness reviewed                                               | independent 119-entry/10-object lifecycle exact      | repair harness independently executed   | zero observed source drift or marker         | narrower than mirror authorization   | **PASS / CLOSED FOR THIS FINDING**   |
| `VE-P4-AUD-005` | Medium   | live limits present; collector/group termination path flawed                    | deadline missed after leader exit                    | stable FAIL                             | bounded temporary marker/process only        | descendant execution beyond deadline | **FAIL / BLOCKING MEDIUM**           |
| `VE-P4-AUD-006` | Low      | image/Action references immutable                                               | all Compose profiles render                          | independent reference search            | configuration only                           | remote CI not run                    | **PASS LOCAL / REMOTE NOT VERIFIED** |

## Verification ledger

No command is a current re-audit PASS until it runs on this branch and exits
zero. Repair-implementer results are not copied into this ledger.

| Command or evidence                       | Exit | Current result                                                           |
| ----------------------------------------- | ---: | ------------------------------------------------------------------------ |
| Git baseline investigation                |    0 | exact commits, clean state, no remote or hidden local state              |
| first batched `git merge-base` invocation |  128 | invalid zsh argument grouping; no repository change                      |
| explicit ancestry rerun                   |    0 | exact four-commit ancestor chain                                         |
| repair diff count/stat/check              |    0 | one commit; 68 files; 7,501 insertions; 571 deletions; clean             |
| production baseline freeze                |    0 | 71 files; digest recorded; no diff from repair commit                    |
| first three-test re-audit run             |    1 | two production failures; third audit-test `NameError`                    |
| corrected third test                      |    1 | no `NameError`; production timeout expectation fails                     |
| corrected three-test rerun                |    1 | 3 stable production failures; 4 deselected                               |
| preserved original repair regressions     |    0 | 4 passed; 3 deselected                                                   |
| final complete audit file                 |    1 | 3 failed, 4 passed; exact defect set                                     |
| `make source-invariance-check`            |    0 | 119 source entries; 10 objects; 0 markers; PASS                          |
| `make workspace-security-check`           |    0 | 35 tests and static check pass                                           |
| real PostgreSQL Workspace API tests       |    0 | 8 passed; one upstream warning                                           |
| `make migration-check`                    |    0 | downgrade/upgrade/re-upgrade pass                                        |
| `make contracts-check`                    |    0 | no generated contract drift                                              |
| `make docker-config`                      |    0 | all declared profiles render                                             |
| live Docker/API isolation probes          |    0 | declared UID/rootfs/capability/resource/volume/network controls observed |
| downstream aggregate gates                |  N/A | NOT VERIFIED; stopped after stable blockers                              |

## Rollback

The branch contains audit-only additions. If the Gate fails, preserve the
reproduction, report, evidence, and branch; do not remove or patch the
production defect. Stop only exact audit-owned services or disposable
resources using repository-supported commands. Never reset, clean, delete
unknown directories, or alter another branch to manufacture a clean result.

## Completion conditions

The PASS conditions are intentionally not met:

1. `VE-P4-AUD-001` and `VE-P4-AUD-003` fail independent secure assertions.
2. `VE-P4-AUD-005` fails timeout/process-group enforcement and is blocking.
3. `VE-P4-AUD-002` lacks complete independent closure evidence.
4. Aggregate gates stopped after the Gate became irreversibly FAIL.

The FAIL handoff completes when the final production manifest exactly matches
the repair commit, the diff contains only audit test/documentation paths, one
reviewed local audit checkpoint exists, the worktree/index are clean, and
main/repair/original-audit/Phase-4 refs, remote/push/merge, and CreativeDeploy
constraints remain unchanged.

## Outcome and follow-ups

The Security Gate is **FAIL**. The minimum next remediation is:

1. limit mirror import to the approved revision's validated reachable object
   closure;
2. require a trusted signed pending-discard completion record before treating
   absent local state as an idempotent success;
3. enforce the deadline against the entire process group even after the leader
   exits; and
4. obtain complete independent Side-effect Permit closure evidence.

Do not merge, push, open a pull request, access Customer 0/CreativeDeploy, begin
Phase 5, or claim production/hostile-sandbox safety.

**RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED**
