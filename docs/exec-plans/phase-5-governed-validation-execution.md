# Phase 5 — Governed Validation Execution

- Started: 2026-07-29
- Branch: `feat/phase-5-governed-validation-execution`
- Main baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Status:
  `PHASE 5 FIRST VERTICAL SLICE COMPLETE — READY FOR INDEPENDENT FOCUSED REVIEW`
- Remote CI: NOT VERIFIED

## Goal

Add the first maximum-safe Browser-first validation slice for the trusted
repository-owned synthetic fixture. A local user chooses a system-owned,
versioned Validation Profile that is already allowed by a separately approved
Execution Grant. The Control Plane binds the request to an exact Run, Plan,
revision, Workspace Checkpoint, Runner, Attempt, Lease, policy digest, and
budgets. The independent Runner validates a disposable per-run copy with a
fixed command and returns bounded structured evidence.

The successful implementation outcome is:

`PHASE 5 FIRST VERTICAL SLICE COMPLETE — READY FOR INDEPENDENT FOCUSED REVIEW`

This implementation checkpoint is not a Phase 5 Security Gate PASS and does
not authorize a real repository, Customer 0, Git delivery, or deployment.

## Verified baseline

Preflight confirmed the exact repository root
`/Users/danke/Developer/VisualEngineer`, clean `main`, and both `HEAD` and
`main` at `928a89d2055d172bbd7c6670b42f668d103dcb03`. Remotes, stashes,
additional worktrees, and Git locks were absent. The implementation branch was
created without force from that exact commit.

Phase 4 is complete and integrated locally. Historical Phase 4 audit and
re-audit FAIL records remain correct for the revisions they inspected; their
later repairs, independent closures, and final aggregate PASS remain preserved.

## Product boundary

Phase 5 is formally named **Governed Validation Execution**. This batch adds:

- a system-owned immutable Validation Profile catalog;
- an independently approved validation-scoped Execution Grant;
- an exact Workspace Checkpoint binding;
- closed Validation Run, step, result, and evidence records;
- a typed Runner Job with no user command, argument, cwd, or environment;
- a disposable per-run validation sandbox;
- fixed Python-standard-library fixture validation;
- monotonic process-group timeout, cancel, output budgets, and cleanup;
- Browser create/list/detail/cancel and bounded evidence surfaces; and
- PostgreSQL, migration, API, Protocol, Runner, Web, E2E, security, and Eval
  verification.

## Non-goals and stop conditions

This batch must not add or access:

- an LLM, OpenAI Agents SDK, external model provider, model invocation, or
  Agent reasoning;
- API keys, external credentials, or a real user HOME;
- user-supplied command, argv, cwd, environment, shell fragment, or plugin;
- shell execution, package lifecycle scripts, package installation, or
  network download;
- a non-fixture repository, CreativeDeploy, or Customer 0;
- source or canonical Workspace mutation by validation;
- Git branch/commit delivery, push, pull request, tag, deployment, or Phase 6.

Stop with `PHASE_5_REQUIRES_EXPLICIT_USER_APPROVAL` if any excluded model,
provider, credential, customer, or delivery capability becomes necessary.
Stop with
`PHASE 5 IMPLEMENTATION STOPPED — EXECUTION BOUNDARY NOT PROVEN`
if arbitrary command inputs, filesystem isolation, network denial, complete
process cleanup, or sandbox cleanup cannot be proven in the real Runner
container.

## Vertical slice

### Validation Profile catalog

The first catalog entry is `fixture-python-stdlib-v1`, version `1`. Its actual
command is owned by Runner code. API and Web accept only the Profile ID. The
Profile uses the existing Python runtime with `-I` and `-S`; it runs no package
script and imports no third-party validation dependency. It checks the fixed
fixture contract and intentionally produces exit `1` if the exact checkpoint
does not satisfy that contract, allowing both success and failure evidence.

No Node Profile will be added unless a second system-owned command is justified
without dependencies or lifecycle execution.

### Data model

The Phase 5 migration will add:

- validation fields to immutable Execution Grants, including exact Workspace
  and Checkpoint, allowed Profile versions, run count, timeout, resource,
  output, artifact, and validity budgets;
- `validation_runs`, bound to Run/Plan/revision/Workspace/Checkpoint/Grant,
  Runner Job, Runner/Attempt/Lease, Profile, policy digest, idempotency, and
  timestamps;
- `validation_step_runs`, one closed fixed step per current Profile; and
- `validation_evidence`, one immutable bounded result/evidence record.

Validation Run state is closed to `requested`, `queued`, `claimed`, `running`,
`cancel_requested`, `succeeded`, `failed`, `timed_out`, `cancelled`, and
`recovery_required`. Database constraints and triggers protect immutable
authority and terminal evidence.

### API and Protocol

User API will provide Profile catalog, eligible Checkpoints, validation-scoped
Grant creation through the existing Grant boundary, Validation Run
create/list/detail/cancel, and bounded evidence reads. Creation accepts a
Profile ID and approved validation Grant only; no command-bearing field exists.

Runner Protocol v1 will gain one discriminated `validation_execute_v1` Job and
result. The Job carries only fixed Profile identity, exact Checkpoint and
revision bindings, policy digest, and budgets. The permission envelope remains
no-shell and Control-Plane-only; the validation subprocess receives a stricter
no-network syscall boundary.

### Runner sandbox and command boundary

Runner creates a UUID-addressed validation root separate from the canonical
Workspace. It verifies the exact current Workspace tree against the authorized
Checkpoint, copies only bounded no-follow fixture inputs, creates private
scratch/output directories, and launches one fixed system-owned Python
validator with a minimal environment and fresh process group.

The child applies Linux Landlock filesystem rules and a seccomp network syscall
denylist before reading fixture data. It can read the validation copy and use
only the per-run scratch/output directories; canonical Workspace, mirror,
registry, credential, source, and real HOME paths remain outside its filesystem
rules. Unsupported or failed kernel enforcement is a typed fail-closed error.

Parent execution uses a monotonic deadline, cooperative cancellation,
TERM/bounded grace/KILL, complete process-group absence verification, bounded
stdout/stderr streaming, redaction, and exact validation-root cleanup. Cleanup
failure maps to `recovery_required` and is never reported as success.

## Permission and state-machine decisions

- Plan approval remains non-executing.
- A Phase 4 implementation Grant cannot dispatch validation.
- A separate pending validation Grant is derived from an approved Plan plus
  exact existing Workspace Checkpoint and independently decided by the local
  user.
- Validation authority fixes Profile/version, Workspace/Checkpoint/revision,
  maximum run count, timeout, CPU/memory/PID/FD, output and artifact budgets,
  operation, and expiry.
- Validation does not grant source write, canonical Workspace write, shell,
  external network, Git delivery, PR, or deployment.
- Runner Job Attempt/Lease fencing owns claim/start/cancel/terminal mutation.
- Duplicate completion and idempotency replays cannot create a second evidence
  row or consume the run budget twice.

## Failure classification

Stable categories include Profile/policy denial, stale baseline, stale
Attempt/Lease, revoked/expired Grant, cancellation, non-zero profile result,
timeout, output/artifact overflow, network/filesystem sandbox failure,
orphan-process cleanup failure, sandbox cleanup failure, malformed result, and
internal failure. Only an exact completed fixed-profile result can succeed.

## Web flow

Eligible Workspace detail presents fixed Profile metadata and limitations,
validation Grant state, and exact Checkpoint. After separate Grant approval the
user can create a Validation Run, inspect queued/running/terminal state,
duration, exit code, bounded stdout/stderr, truncation/redaction, resource and
artifact summary, cleanup evidence, and cancel an active run. No free-form
command control exists. Desktop and 390 px plus accessibility are mandatory.

## Logging, evidence, and audit

Persistent evidence is limited to Profile ID/version, safe fixed-argv display,
Runner/Attempt/Lease identifiers, revision/Checkpoint, timing, exit code,
timeout/cancel flags, bounded redacted output, truncation/redaction counts,
resource-limit classification, artifact summary, cleanup result, and
Audit/Runner/Workspace event identity. Raw environment and credentials are
forbidden.

## Test plan

Focused tests cover catalog closure, request schemas, database constraints,
migration roundtrip, idempotency, Grant/Profile/Checkpoint policy, Protocol
closure, fixed command enforcement, filesystem/network denial, cancel,
timeout, output/artifact limits, stale/revoked/replay behavior, sandbox and
process cleanup, source/canonical Workspace invariance, API/Web behavior,
desktop/390 px, and axe.

Required final gates are format, lint, Python/TypeScript typecheck, unit tests,
real PostgreSQL integration, migration roundtrip, contract generation/check,
Runner integration, Web tests/build, E2E, security negatives, Docker isolation,
source invariance, no residual resources, `git diff --check`, and one final
`make verify`.

## Progress

- done — exact Phase 4/main preflight and branch creation
- done — repository-defined Make, fixture, Runner, Workspace, Protocol, and
  Docker boundary inspection
- done — governance correction and ExecPlan
- done — model, migration, API, Protocol, Runner, and Web implementation
- done — focused tests, real PostgreSQL migration roundtrip, real Runner
  sandbox proof, full browser E2E, Chaos, security, and source invariance
- done — final aggregate verification and evidence reconciliation
- done — final diff review and one local checkpoint

## Decisions and discoveries

- The Runner runtime intentionally installs no development dependencies, so
  pytest is not currently available inside the execution container. Adding
  package installation or lifecycle execution is outside scope. The first
  Profile therefore uses the existing Python standard library.
- The Runner container can reach only the internal Control Plane, but that is
  still network access. A validation child cannot inherit that namespace
  unrestricted and be called no-network. Kernel-enforced child network denial
  is therefore mandatory.
- Phase 4 descriptor and process-group controls are reused; validation does
  not weaken or replace them.
- The repository build images normally resolve OS/package-manager metadata.
  Offline image-build attempts were deliberately run with networking disabled;
  API `apt` and Web `corepack` resolution stopped without a successful package
  install or download. Verification therefore reused local dependency-installed
  images while copying only the current repository source/build output, then
  ran E2E and Chaos with `--no-build`.
- The default E2E API port was already held by an unknown host Python listener.
  No process was inspected, killed, or changed. Isolated alternate API/Web/
  PostgreSQL ports were used instead.
- A read-only global Docker inventory used during that diagnosis printed the
  name of an existing sibling-project container. No inspect, logs, filesystem,
  mount, start, stop, exec, test, or mutation followed; later diagnostics were
  constrained to exact VisualEngineer Compose project names.

## Focused verification completed

- API and real-PostgreSQL tests: 167 passed; coverage 82.39%.
- Runner/Protocol tests: 88 passed.
- Web component tests: 8 files and 44 tests passed.
- Full real Playwright flow: 16 passed at desktop and 390 px, including
  separate validation Grant approval, real Runner execution, persistence, and
  teardown.
- Real PostgreSQL Alembic base-to-head, downgrade-to-base, and
  upgrade-to-head roundtrip passed.
- Validation sandbox proof passed real-container Landlock filesystem denial,
  seccomp network denial, fixed-Profile pass/fail, bounded exit, process
  cleanup, and sandbox cleanup.
- Workspace security passed 63 tests plus static isolation; Runner security
  passed its static checks, 7 scanner tests, and 98 Runner security tests.
- Workspace Chaos, source invariance, contracts, format, lint, Python/
  TypeScript typecheck, production build, Compose rendering, and Eval passed in
  focused or aggregate attempts.

The repository-defined aggregate `make verify` also exited `0`, composing
contracts, formatting, lint, typecheck, tests, build, Compose rendering,
migration, Phase 4 preservation, source invariance, E2E, Chaos, security,
validation sandbox, Eval, and `git diff --check`. This is implementation
evidence for independent focused review, not an independent review decision.

## Risks

- Landlock or seccomp may be unavailable in the actual Docker kernel. The
  implementation must fail closed and the real Docker gate must prove support.
- Copying untrusted filesystem entries can recreate link or device hazards.
  Copy is bounded, descriptor-rooted, no-follow, regular-file-only, and limited
  to Profile-owned inputs.
- Cancellation can race terminal completion. Existing locked Attempt/Lease
  transitions and idempotent terminal evidence must remain authoritative.
- A cleanup error can hide residual state. Cleanup proof is explicit and
  failure becomes `recovery_required`.

## Rollback

Stop only exact repository-owned Compose projects and preserve unknown state.
Before a checkpoint, revert only Phase 5 files through reviewed patches; never
reset, clean, or rewrite Phase 4 history. The migration downgrade removes only
Phase 5 tables, triggers, constraints, indexes, and new nullable/defaulted
columns. Validation sandboxes are UUID-bound under their dedicated Runner
volume and never authorize deletion of canonical Workspace state.

## Completion conditions

All scope, migration, contract, API, Protocol, Runner, Web, security,
invariance, Docker, cleanup, and aggregate gates must pass. `main` must remain
at the sealed Phase 4 hash; no remote, push, PR, merge, tag, Customer 0, or
CreativeDeploy access may occur. Exactly one local implementation checkpoint
is permitted, followed by a clean worktree.

## Independent focused review

The next milestone after an implementation PASS is an independent focused
read-only review of:

- arbitrary-command prevention;
- sandbox versus canonical Workspace isolation;
- network and credential isolation;
- Lease/fencing/cancel/timeout behavior;
- output/artifact budgets; and
- cleanup/recovery.

It does not reopen the completed whole-Phase-4 audit.
