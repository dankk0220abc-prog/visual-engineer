# Phase 5 governed multi-step Validation Suites verification

- Date: 2026-07-30 +08:00
- Repository: `/Users/danke/Developer/VisualEngineer`
- Baseline/main: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Branch: `feat/phase-5-governed-validation-suites`
- Candidate status: `IMPLEMENTED_PENDING_INDEPENDENT_FOCUSED_REVIEW`
- Security decision: not made by this implementer

## Scope and governance

Preflight ran the required `pwd`, repository/top-level, branch, HEAD/main,
porcelain status, tracked/cached diff, untracked, remote, stash, worktree, tag,
heads, graph, and baseline-show commands. Every command exited `0`.

**CONFIRMED** at start:

- exact repository, `main`, HEAD, and main matched the declared baseline;
- worktree/index/untracked were clean;
- no remote, stash, tag, Git lock, other worktree, or concurrent modification
  existed;
- the sealed first Phase 5 slice and Git history agreed; and
- no approved milestone conflicted with this second slice.

The branch was created directly from that baseline. Searches and fixture
operations stayed anchored to this repository. No CreativeDeploy, Customer 0,
sibling repository, remote, push, merge, pull request, tag, deployment, LLM,
Provider, credential, arbitrary command, package install, or Phase 6 action is
part of this candidate.

## Implemented closure

The source-owned `fixture-integrity-suite-v1:v1` definition has two ordered
fixed steps:

1. `fixture-contract` → `fixture-python-stdlib-v1:v1`, 10 seconds, 8192 output
   bytes, zero artifacts.
2. `fixture-manifest` → `fixture-python-manifest-v1:v1`, 10 seconds, 4096
   output bytes, zero artifacts.

The Suite is fail-fast with a 30-second total timeout, 10,000-byte combined
retained-output cap, two attempts, a canonical policy digest, and no
caller-defined steps. Create accepts only the Suite ID/version and exact
approved Suite Grant. Strict schemas reject command, argv, cwd, environment,
shell, Profile definition, ordering, duplicate-step, or step-list input.

Migration `20260730_0008` adds Suite-scoped Grant references,
`validation_suite_runs`, `validation_suite_step_runs`, and
`validation_suite_results`, with foreign keys, unique/index/idempotency/
ordering constraints, closed checks, immutable-authority/terminal/transition
triggers, and downgrade.

The Control Plane dispatches one existing fixed-Profile Validation Run at a
time. Each started step has an independent Runner Job, Attempt, Lease, Permit,
result, Evidence, sandbox, and cleanup proof. Cancellation wins before lazy
child synchronization can dispatch the next step. Suite timeout cancels an
active child before terminal `timed_out`. A fresh-Grant retry reuses successful
immutable Evidence with zero redispatch/output recharge and creates fresh
execution identities for incomplete steps.

## Focused verification ledger

| Command / scope                                    | Exit | Result                                                                                                                                              |
| -------------------------------------------------- | ---: | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make format`                                      |    0 | Ruff and Prettier formatted the candidate                                                                                                           |
| `make contracts && make contracts-check`           |    0 | OpenAPI and generated TypeScript have no drift                                                                                                      |
| `make format-check && make lint && make typecheck` |    0 | Ruff/Prettier/ESLint; mypy 94 modules; TypeScript pass                                                                                              |
| focused Suite PostgreSQL test file                 |    0 | 10 passed; injection, serial order, replay/conflict, revocation, partial retry, cancel races, Suite/step timeout, cleanup recovery, exact/+1 output |
| complete `uv run pytest` before final additions    |    0 | 236 passed, 83.18% aggregate Python coverage                                                                                                        |
| focused Runner/Protocol                            |    0 | 12 passed after descriptor-based manifest repair                                                                                                    |
| `pnpm test`                                        |    0 | 47 passed; statements 71.87%, branches 68.66%, functions 71.34%, lines 73.61%                                                                       |
| `make build`                                       |    0 | Next.js production build; `/validations` emitted                                                                                                    |
| real PostgreSQL migration roundtrip                |    0 | base → head → base → head, ending at `20260730_0008`                                                                                                |
| `make eval` before two final mapped cases          |    0 | 65 cases and repository scanner 7 passed; final dataset count is checked by aggregate                                                               |
| `make phase4-findings-check`                       |    0 | six repair controls present; historical independent FAIL preserved; security audit 22 passed                                                        |
| `make workspace-security-check`                    |    0 | 64 passed and static descriptor/isolation checks passed                                                                                             |
| `make security-check`                              |    0 | secrets/static checks, scanner 7 passed, broad security selection 111 passed                                                                        |
| `make source-invariance-check`                     |    0 | PASS: 119 source entries, 10 Git objects, 2 status records, 0 extension markers                                                                     |
| focused desktop + 390 px E2E                       |    0 | 16 passed, including first-slice compatibility, two Suite steps, aggregate Evidence, persistence, axe, and horizontal containment                   |
| Workspace Chaos                                    |    0 | atomic pre/post-rename recovery, three stale leases fenced, concurrent revocation, zero effective side effects, source/.git unchanged               |
| `make validation-security-check` after repair      |    0 | Landlock filesystem denial, seccomp network denial, both fixed Profiles pass/fail, bounded exit codes, executor cleanup                             |
| `git diff --check`                                 |    0 | no whitespace errors                                                                                                                                |

The focused E2E project was `ve-p5-suites-e2e-final` on ports
`25554/28054/23054`. The focused Chaos project was
`ve-p5-suites-chaos-final` on ports `25555/28055`. Label/project-filtered
post-cleanup container/network/volume queries returned zero entries for both.
The first E2E residue query omitted required Compose interpolation variables
and exited `1`; the corrected, exact project-filtered query exited `0` and was
empty.

The generated trusted Workspace fixture remained at:

- HEAD `e3c7f3c918ba0454a5b7d0a3a05063eb61f66692`;
- status digest `4757265c3a51c7198f0a36a6ed8e6766b1ae134e`; and
- no-follow tree fingerprint
  `6cbac795cc667541b5bb20111ba747b7201bab6b6fdb46cb32bd7c4f6e583b68`.

E2E and Chaos independently compared before/after fixture HEAD, status, and
tree fingerprints and exited `0`. Suite aggregate success also required its
persisted `source_invariant` and `canonical_workspace_invariant` flags to be
true.

## First failures, causes, and reruns

Failures are preserved rather than promoted to passing evidence:

1. A mixed narrow pytest invocation passed its ten behavior tests but exited
   `1` because the repository-wide coverage plugin was applied to a deliberately
   partial import set. Rerun with `--no-cov`: pass.
2. Initial Ruff/mypy checks found import ordering, an unused import, and missing
   annotations. The code was corrected; reruns passed.
3. A Web import landed after executable code and produced a syntax error.
   Import placement was corrected; TypeScript passed.
4. First Suite PostgreSQL run failed two of four tests because the new
   migration retained the first-slice Profile check. The additive migration
   now extends the check without editing history; rerun passed.
5. The next Suite run rejected the second fixed Profile because aggregate
   authority incorrectly required its output cap to equal the Grant ceiling.
   Control Plane validation now requires the exact child/Profile cap and proves
   it is within the Grant ceiling; rerun passed.
6. The first full backend attempt found `test_task_concurrency` had a private
   explicit TRUNCATE list missing the three new Suite tables. The list was
   extended; the focused rerun passed, then complete backend passed 236.
7. Suite total-timeout regression first returned `500`: the trigger allowed
   `cancel_requested → cancelled/recovery_required` but not the required
   cleanup-first `cancel_requested → timed_out`. The closed transition was
   added to the new migration; Suite tests passed.
8. Web behavior tests passed 44/44 but the larger Suite UI reduced aggregate
   coverage below thresholds. Suite approve/start/cancel/retry/aggregate/error
   tests were added without changing thresholds; 47/47 and all four coverage
   thresholds passed.
9. The first standalone Docker check failed the new manifest Profile with
   `EACCES` after Landlock. It had attempted to reopen an absolute input path.
   The worker now retains a no-follow directory descriptor opened before
   confinement and enumerates the manifest through that descriptor after
   confinement; 12 focused tests and the Docker check passed.
10. The first revoked-Grant assertion expected an incorrect HTTP category.
    The implementation correctly returned typed `409 validation_grant_inactive`;
    the expectation was corrected and Suite tests passed 9/9.
11. Architecture review found two pre-gate race windows: dispatch marked a
    step queued before creating its idempotent child, and cancellation first
    synchronized a completed child, which could dispatch the next step.
    Dispatch now creates/replays the deterministic child before binding queued
    state; cancellation locks/fences the Suite before child synchronization.
    The new cancellation/completion race and full Suite matrix pass 10/10.

## Final aggregate and checkpoint

The final aggregate used:

```text
COMPOSE_PROJECT_NAME=ve-p5-suites-verify-core
TEST_POSTGRES_PUBLISHED_PORT=55560
E2E_COMPOSE_PROJECT_NAME=ve-p5-suites-verify-e2e
E2E_DB_PORT=25561 E2E_API_PORT=28061 E2E_WEB_PORT=23061
WORKSPACE_CHAOS_COMPOSE_PROJECT_NAME=ve-p5-suites-verify-chaos
WORKSPACE_CHAOS_DB_PORT=25562 WORKSPACE_CHAOS_API_PORT=28062
VALIDATION_RUNNER_IMAGE=ve-p5-suites-verify-e2e-runner:latest
make verify
```

It exited `0`. Final aggregate results:

- contract drift, format, lint, mypy 94 modules, TypeScript: pass;
- Python/API/Runner/Protocol: `239/239`, 83.35% aggregate coverage;
- Web: `47/47`; statements 71.87%, branches 68.66%, functions 71.34%,
  lines 73.61%;
- production Web build and Docker config: pass;
- PostgreSQL base/head/base/head through `20260730_0008`: pass;
- historical Phase 4 controls: six present, historical FAIL preserved,
  security audit `22/22`;
- source invariance: 119 entries, 10 Git objects, 2 status records, zero
  extension markers;
- workspace repair selections: `86/86` Runner/Protocol plus `14/14` API;
- desktop/390 px Playwright and axe: `16/16`;
- Workspace Chaos and unchanged source/`.git`: pass;
- Workspace Security: `64/64` plus static check;
- both fixed Profiles' Docker isolation/pass/fail/cleanup probe: pass;
- broad Security: scanner `7/7`, Runner/API/Protocol `111/111`, static secrets
  and boundaries pass;
- Eval: 67 deterministic cases across five datasets plus scanner `7/7`; and
- final `git diff --check`: pass.

Exact project-filtered post-gate container/network/volume inventories for the
core, E2E, and Chaos projects are empty after explicit cleanup. The only
post-aggregate edits are this result reconciliation and living status/ExecPlan
labels; no product, migration, API, Protocol, Runner, Web, test, Eval, contract,
script, or configuration content changed after `make verify`. Formatting and
`git diff --check` are rerun on that documentation-only reconciliation.

The one local checkpoint is created after this evidence record is frozen; its
exact hash and final clean worktree/index/untracked state are reported in the
final handoff. Independent focused review and remote CI are `NOT RUN`.
Security Gate PASS is `NOT DECLARED`.

The required independent focused review is limited to Suite definition
immutability, step injection prevention, Suite/step consistency,
cancellation/retry races, Suite-level budgets, result/Evidence aggregation,
cleanup, and source/canonical-Workspace invariance. It must not reopen sealed
Phase 4 or first-slice boundaries without new evidence.
