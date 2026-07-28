# Phase 4 Maximum-Depth Independent Workspace Security Audit

- Started: 2026-07-28T12:58:43+08:00
- Branch: `audit/phase-4-workspace-security-max`
- Audited commit: `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main baseline: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Auditor role: independent; not the Phase 4 implementer
- Status: COMPLETE — SECURITY GATE FAIL

## Goal

Independently determine whether Phase 4's synthetic-fixture-only isolated
Workspace boundary is safe enough to merge to `main` and proceed to the next
security phase. The audit covers opaque Repository Handles, immutable
Execution Grants, Lease fencing, Runner-owned mirrors and worktrees,
descriptor-rooted typed file tools, checkpoints, rollback, discard, recovery,
Docker isolation, resource limits, and source-repository invariance.

## Scope

Permitted changes are limited to this ExecPlan, the audit report and evidence,
new independent security regression tests and audit-only fixtures/scripts, the
Eval mapping, the project audit status, the `workspace-security-audit` test
entry point, and necessary audit commits.

The production baseline is frozen across:

- `apps/api/src`
- `apps/runner/src`
- `packages/runner-protocol/src`
- `compose.yaml`
- `infra`
- `apps/api/alembic`
- the API and Runner Dockerfiles

The pre-audit manifest contains 69 tracked files. Its SHA-256 manifest digest
is `d4e48b0ae34ccb686bb0f484d8a51c25a5c01cc39999dfd30ba7e610862aeb26`;
the corresponding Git-tree manifest digest is
`92cdff10f1abd70d75364e7c3857237417629d984006aa123b12395bd039b357`.

## Non-goals

- No production API, Runner, protocol, migration, Web product, permission
  policy, or Docker production-boundary change.
- No CreativeDeploy or other customer repository access.
- No shell or target-repository command capability.
- No system package installation, remote, push, pull request, tag, or
  deployment.
- No claim of hostile multi-tenant or production isolation.

## Constraints and safety

- A production defect is documented and reproduced, not fixed in this audit.
- Critical, High, fixture-boundary Medium, source mutation, production-hash
  drift, mandatory verification failure, or an unprovable Docker/Grant/Lease
  boundary blocks the merge.
- Never use reset-hard, clean, stash, sudo, Homebrew, apt, broad deletion, or
  global/system Git configuration.
- Race tests are bounded. Synthetic fixtures only.
- Stop dangerous tests immediately if a source, sibling Workspace, or host
  boundary changes.
- A PASS requires every mandated command, audit test, source-invariance check,
  Docker runtime probe, secret scan, and staged review to pass.

## Threat hypotheses

| ID            | Hypothesis                                                        | Required observation                                                  | Status            |
| ------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------- | ----------------- |
| H-PATH-01     | Rename/symlink races can redirect a descriptor-rooted operation   | No effect outside the Workspace and a closed failure                  | REVIEWED          |
| H-PATH-02     | Hard links or special files can bypass regular-file policy        | All write/read mutation paths reject unsafe inode types/link counts   | REVIEWED          |
| H-ATOMIC-01   | Temp-file collision or interruption can publish partial data      | Old or complete content only; deterministic recovery                  | REVIEWED          |
| H-AUTH-01     | Revoked/expired Grant can race a write                            | Zero file, checkpoint, event-success, and budget side effects         | BLOCKER CONFIRMED |
| H-LEASE-01    | Stale Attempt/Lease can commit after replacement                  | Zero durable side effects and `stale_lease`                           | BLOCKER CONFIRMED |
| H-GIT-01      | Mirror/worktree setup can modify or share mutable source state    | Exact source invariance, no alternates, no shared object inode        | BLOCKER CONFIRMED |
| H-GIT-02      | Git hooks/helpers/filters/LFS/submodules/network can execute      | Marker remains absent and requests fail closed                        | BLOCKER CONFIRMED |
| H-RECOVERY-01 | Crash windows can produce false success or unsafe cleanup         | Honest state, deterministic retry, sibling/source survival            | BLOCKER CONFIRMED |
| H-RESOURCE-01 | Output, event, file, process, or storage growth can escape bounds | Bounded failure and recoverable state                                 | GAP CONFIRMED     |
| H-DOCKER-01   | Runtime mounts/network/identity exceed declared authority         | Runner-only read-only source and private state; API-only reachability | TOPOLOGY VERIFIED |

## Current progress

### 2026-07-28

- DONE: validated the exact Phase 4 branch and commit, Phase 3 `main`, clean
  worktree, absent remotes, repository-local Git identity, Compose services,
  ports, networks, mounts, and volumes.
- DONE: froze the 69-file production baseline before repository writes under a
  unique `/tmp/visualengineer-phase4-audit-baseline-*` directory.
- DONE: created this audit branch directly from the Phase 4 commit without
  modifying the feature branch or `main`.
- DONE: read the repository operating contract, Phase 4 ExecPlan and evidence,
  security boundary, Workspace and Runner threat models, isolated Workspace
  architecture, and permission model.
- DONE: completed production code and configuration review.
- DONE: added four closed synthetic regression observations and the
  `workspace-security-audit` target; all four observations pass.
- DONE: verified Docker identity, capabilities, read-only source/rootfs,
  mounts, networks, reachability, and sibling-service isolation.
- DONE: ran every mandatory local command, including aggregate `make verify`.
- DONE: repeated the 69-file production hash comparison; it is exact.
- DONE: completed severity classification and Gate decision.
- FAIL: strict source invariance detected source `.git` directory metadata
  drift. Content and all other captured state remained exact.
- NOT DONE BY POLICY: no fast-forward or merge to `main`.

## Decisions

1. **Audit the specified repository, not the desktop attachment workspace.**
   The trusted repository exists at the instructed path and is a distinct
   directory.
2. **Freeze a slightly wider production set.** API/Runner Dockerfiles and all
   tracked `infra` and Alembic files are included so an audit-only change
   cannot hide a runtime-boundary or migration edit.
3. **Treat existing Phase 4 evidence only as a claim to reproduce.** No prior
   pass is carried into the independent Gate.
4. **Keep test failures as evidence.** Failed commands and corrected test
   methodology will remain in this plan and the evidence ledger.

## Risks

| Risk                                               | Likelihood / impact | Mitigation / next action                                                 |
| -------------------------------------------------- | ------------------- | ------------------------------------------------------------------------ |
| Audit test accidentally mutates the fixture source | low / critical      | fingerprint before/after and stop on first mismatch                      |
| Race harness becomes unbounded                     | medium / medium     | explicit iteration and subprocess time bounds                            |
| Local macOS semantics hide Linux behavior          | high / high         | run acceptance probes inside the Linux Runner profile                    |
| Audit-only test reaches production/customer data   | low / critical      | use only the committed adversarial fixture and isolated Compose projects |
| Existing services mask image/config drift          | medium / high       | inspect container runtime and rebuild through mandated checks            |

## Discoveries

- Base Compose currently runs four healthy services. Only API, Web, and
  PostgreSQL publish loopback ports; Runner publishes none.
- Base Runner currently mounts only its credential volume. The Phase 4 source,
  mirror, Workspace, and registry boundaries live in an override and require
  separate runtime verification.
- Existing design documents explicitly rely on Runner being the only
  Workspace-volume writer because Python lacks portable `openat2` and
  `renameat2` pathname-CAS interfaces.
- Existing design states that Git diff output is limited after child-process
  capture, not by a streaming OS quota.
- `VE-P4-AUD-001` confirms an unauthorized Git adapter side effect and blocks
  the Gate.
- `VE-P4-AUD-002` confirms an unauthorized post-revocation Workspace side
  effect and blocks the Gate.
- `VE-P4-AUD-003` confirms unsafe unknown-content removal in registry recovery
  and blocks the Gate.
- `VE-P4-AUD-004` confirms source `.git` metadata drift. Attribution to the
  exact lifecycle call is not fully isolated, but the required invariance
  condition is disproved.
- `VE-P4-AUD-005` records absent explicit Runner CPU, memory, and PID limits.
- `VE-P4-AUD-006` records non-immutable supply-chain references.

## Findings

| ID            | Severity | Component                       | Unauthorized side effect | Gate blocking | Fix required |
| ------------- | -------- | ------------------------------- | ------------------------ | ------------- | ------------ |
| VE-P4-AUD-001 | Critical | Git source adapter              | confirmed                | yes           | yes          |
| VE-P4-AUD-002 | Critical | Grant/Lease side-effect fencing | confirmed                | yes           | yes          |
| VE-P4-AUD-003 | High     | registry/discard recovery       | confirmed                | yes           | yes          |
| VE-P4-AUD-004 | Critical | fixture source invariance       | confirmed                | yes           | yes          |
| VE-P4-AUD-005 | Medium   | Runner resource isolation       | not demonstrated         | no            | yes          |
| VE-P4-AUD-006 | Low      | supply-chain reproducibility    | not demonstrated         | no            | yes          |

## Verification

| Command / evidence               | Status   | Result                                                             |
| -------------------------------- | -------- | ------------------------------------------------------------------ |
| trusted baseline commands        | VERIFIED | expected commits; clean; no remote; identity present               |
| production manifest freeze       | VERIFIED | 69 files; frozen digests recorded above                            |
| production source review         | COMPLETE | six findings classified                                            |
| `make workspace-security-audit`  | PASS     | 4 passed                                                           |
| `make format-check`              | PASS     | initial audit-doc format failure corrected; final pass             |
| `make lint`                      | PASS     | Ruff and ESLint pass                                               |
| `make typecheck`                 | PASS     | mypy 71 files and TypeScript pass                                  |
| `make test`                      | PASS     | backend 105; frontend 39                                           |
| `make build`                     | PASS     | production Web build                                               |
| `make contracts-check`           | PASS     | no generated-contract drift                                        |
| `make migration-check`           | PASS     | upgrade/downgrade/upgrade                                          |
| `make workspace-security-check`  | PASS     | 25 tests plus static check                                         |
| `make security-check`            | PASS     | secret/static checks; 7 scanner and 46 Runner security tests       |
| `make eval`                      | PASS     | 58 deterministic cases and 7 scanner tests                         |
| `make e2e`                       | PASS     | 12 browser tests                                                   |
| `make workspace-smoke`           | PASS     | real-stack fixture flow                                            |
| `make workspace-chaos-check`     | PASS     | bounded crash/retry flow                                           |
| `make verify`                    | PASS     | aggregate command exited zero                                      |
| Docker runtime probes            | PASS     | declared topology verified; resource-limit gap separately recorded |
| source invariance                | FAIL     | source `.git` directory metadata changed                           |
| final production hash comparison | PASS     | exact 69-file match                                                |

## Rollback

Audit documents and tests are additive. If the Gate fails, preserve them on
the audit branch as evidence, leave `main` unchanged, stop only exact
audit-owned Compose projects, and leave a clean worktree. Never clean or reset
the Phase 4 branch or fixture source.

## Completion conditions

1. Every required source and runtime boundary is independently reviewed.
2. Reproducible audit tests cover the feasible path, authorization, Git,
   recovery, resource, and output hypotheses and record platform limitations.
3. Production hashes and fixture source fingerprints remain unchanged.
4. Every mandatory command exits zero for PASS; any failure remains blocking.
5. Audit report and evidence contain severity, reproduction, exact results,
   residual assumptions, and one next milestone.
6. A reviewed audit commit exists. Only PASS permits an `--ff-only` update of
   `main`; FAIL leaves `main` untouched and the audit branch checked out.

## Outcome and follow-ups

The audit is complete. Security Gate is **FAIL**.

There are three Critical, one High, one Medium, and one Low findings. The
production hash is unchanged, but the Critical/High findings and failed strict
source-invariance requirement prohibit merge. `main` remains unchanged.

The next milestone is a dedicated Phase 4 security-repair batch covering Git
source-adapter hardening, transactional authority fencing, conservative
registry recovery, exact source invariance, and explicit Runner resource
bounds, followed by a fresh independent audit.
