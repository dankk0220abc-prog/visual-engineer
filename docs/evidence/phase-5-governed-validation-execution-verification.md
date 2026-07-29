# Phase 5 Governed Validation Execution Verification

- Date: 2026-07-29
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `feat/phase-5-governed-validation-execution`
- Phase 4 / `main` baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Candidate checkpoint: this document's containing local commit
- Completion classification:
  `PHASE 5 FIRST VERTICAL SLICE COMPLETE — READY FOR INDEPENDENT FOCUSED REVIEW`

This record covers the first maximum-safe vertical slice only. It is
implementation evidence for an independent focused read-only review, not a
Phase 5 Security Gate approval.

## Implemented scope

- one immutable system-owned `fixture-python-stdlib-v1:v1` Profile;
- a validation-only Execution Grant with a separate local-user decision and
  exact Run/Plan/revision/Workspace/Checkpoint/Profile/policy binding;
- fixed run, timeout, CPU, memory, PID, file-descriptor, output, artifact,
  operation, and expiry budgets;
- `ValidationRun`, `ValidationStepRun`, and immutable bounded
  `ValidationEvidence` persistence;
- a strict `validation_execute_v1` Runner Job/result with no command, argv,
  cwd, environment, package, URL, or shell field;
- a UUID-addressed disposable validation root separate from the canonical
  Workspace;
- bounded descriptor/no-follow fixture input copy, minimal environment, fixed
  Python standard-library validator, Linux Landlock filesystem confinement,
  seccomp network denial, process/resource limits, bounded streaming output,
  monotonic timeout/cancel, process-group absence proof, and exact sandbox
  cleanup;
- `/validations` Profile/Grant/Run/cancel/evidence browser flow; and
- migration, OpenAPI/TypeScript contract, API, Runner, Web, E2E, Chaos,
  security, and documentation updates.

## Explicit exclusions

No LLM, OpenAI Agents SDK, external Provider, model invocation, API key,
credential, user command, arbitrary subprocess, package lifecycle/install,
network download, CreativeDeploy/Customer 0 repository use, source or
canonical Workspace write, Git delivery, push, pull request, tag, deployment,
or Phase 6 capability was added.

## Focused command ledger

| Gate                                                     | Result                                                            |
| -------------------------------------------------------- | ----------------------------------------------------------------- |
| API and real-PostgreSQL tests                            | PASS — 167 tests; 82.39% coverage                                 |
| Runner/Protocol tests                                    | PASS — 88 tests                                                   |
| Web unit/component tests                                 | PASS — 8 files; 44 tests                                          |
| Playwright desktop + 390 px                              | PASS — 16 tests                                                   |
| Alembic base → head → base → head                        | PASS                                                              |
| Validation sandbox real-container check                  | PASS                                                              |
| Workspace security                                       | PASS — 63 tests plus static isolation                             |
| Runner security                                          | PASS — static boundary, 7 scanner tests, 98 Runner security tests |
| Workspace Chaos and source invariance                    | PASS                                                              |
| Contracts, format, lint, typecheck, build, Compose, Eval | PASS in focused or aggregate attempts                             |
| Final exact-tree `make verify`                           | PASS — exit code 0                                                |

The final aggregate command uses isolated VisualEngineer ports because the
default API port was already held by an unknown host Python listener:

```text
E2E_SKIP_BUILD=1 CHAOS_SKIP_BUILD=1 \
E2E_API_PORT=18100 E2E_WEB_PORT=13100 E2E_DB_PORT=15532 \
WORKSPACE_CHAOS_API_PORT=18103 WORKSPACE_CHAOS_DB_PORT=15536 \
make verify
```

No unknown listener was inspected, killed, or changed.

## Real sandbox evidence

The real Runner-container proof exercised the actual fixed Profile and
confirmed:

- the Profile succeeds on the authorized fixture and returns the expected
  bounded structured result;
- the intentionally failing fixture returns a non-zero typed failure;
- canonical Workspace access from the child is denied by Landlock;
- socket creation/connect paths are denied by seccomp;
- timeout/output bounds and closed exit classification hold;
- child/process-group termination and reap complete; and
- the exact validation root is absent after terminal cleanup.

The same Runner path is used by the browser E2E. The E2E created and sealed an
exact fixture Workspace, separately approved its validation-only Grant,
executed the real Runner Profile, checked structured evidence and reload
persistence at desktop and 390 px, then revoked/discarded the test authority
and Workspace.

## Offline image-build record

Network-disabled image-build attempts were intentionally used to test whether
the existing Dockerfiles could rebuild without resolution. API `apt` and Web
`corepack` resolution stopped under that denial. No package installation or
network download succeeded. Verification then reused already local
dependency-installed images and copied only the current repository source/
compiled application into local test images; E2E and Chaos ran with
`--no-build`.

These failed offline attempts are not represented as production image-build
evidence. The normal repository build gate remained part of the local quality
checks.

## Search-boundary failure record

- Command: `find .. -name AGENTS.md -print`
- Exit code: `0`
- Root cause: the search root used the parent directory.
- Actual impact: output contained a sibling path name only; no sibling file
  content was read and no sibling repository was modified, mounted, run, or
  tested.
- Corrective rule: every subsequent read/search/command was anchored to
  `/Users/danke/Developer/VisualEngineer` or `.` with that exact working
  directory.

No new governance loop or repair branch was created for this retained event.

## Docker metadata diagnostic record

During diagnosis of the occupied default port, one read-only global
`docker ps` inventory printed the name of an existing CreativeDeploy
container. This exposed name/status metadata only. No `inspect`, logs,
filesystem read, mount read, `exec`, start, stop, test, build, or mutation of
that container or repository occurred. No further global Docker inventory was
used; subsequent runtime commands were constrained to exact disposable
VisualEngineer Compose project names.

## CONFIRMED / NOT VERIFIED ledger

### CONFIRMED

- repository root, branch, and Phase 4/main baseline match this record;
- the Phase 5 API accepts only a Profile ID and approved validation Grant;
- Protocol models reject extra fields and expose no arbitrary command input;
- validation authority is separate from Phase 4 implementation authority;
- exact Workspace/Checkpoint/revision/Profile/policy/run budgets are enforced;
- fixed pass/fail execution, Landlock filesystem denial, seccomp network
  denial, output/resource bounds, process cleanup, and sandbox cleanup passed
  focused real-container checks;
- canonical Workspace state is invariant across validation;
- API, Runner, Web, migration, contract, E2E, Chaos, security, and Eval gates
  listed above passed; and
- no remote exists and no push, PR, tag, merge, deployment, Customer 0, LLM,
  Agents SDK, Provider, credential, package install, or Phase 6 action was
  performed.

### NOT VERIFIED

- independent focused review or Phase 5 Security Gate approval;
- remote CI;
- real/customer repository validation;
- browser automation inside a Validation Profile;
- package/lifecycle validation;
- hostile multi-tenant isolation;
- Git delivery, PR, deployment, or production operation; and
- LLM, Agents SDK, Provider, credential, Customer 0, or CreativeDeploy
  behavior.

## Final implementation decision

The repository-defined aggregate `make verify` exited `0`. It composed
contract drift, formatting, lint, Python/TypeScript typecheck, 167 backend/
Runner/Protocol tests, 44 Web tests, production build, Compose rendering,
real-PostgreSQL migration roundtrip, Phase 4 finding preservation and repair
checks, source invariance, 16 real Playwright tests, Workspace Chaos,
Workspace and Runner security, real-container validation sandbox denial,
58 deterministic eval cases, and final `git diff --check`.

The first vertical slice is ready for one local checkpoint and an independent
focused read-only review. It is not approved for a real repository,
CreativeDeploy/Customer 0, arbitrary commands, package lifecycle, LLM or
Provider use, Git delivery, or deployment.
