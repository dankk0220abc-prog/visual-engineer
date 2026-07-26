# Phase 3 Browser-Orchestrated Local Runner Foundation ExecPlan

- Status: COMPLETE
- Started: 2026-07-26 (Asia/Shanghai)
- Working branch: `feat/phase-3-browser-orchestrated-local-runner`
- Base branch: `main`
- Base commit: `336b46d`
- Intended checkpoint message:
  `feat: add browser-orchestrated local runner foundation`
- Remote CI: NOT RUN; no remote is configured

## Goal

Deliver a real browser-orchestrated Control Plane and independent outbound
Local Runner that can execute only two closed, repository-free job kinds:
`system_diagnostic_v1` and `controlled_wait_v1`.

The observable outcome is a local user opening the Web Console, seeing a
registered Runner, dispatching a typed job whose immutable Permission Envelope
grants no repository, shell, worktree, Git, or public-network authority,
observing lease-backed progress, cancelling a controlled wait, and retaining
durable sanitized evidence across refresh and recovery.

## Scope

- Versioned shared Runner Protocol schemas and canonical policy hashing.
- PostgreSQL Runner, PermissionEnvelope, RunnerJob, RunnerJobAttempt, and
  RunnerJobEvent entities plus a reversible Alembic migration.
- Bootstrap registration, per-Runner credential issuance/digest storage,
  heartbeat, registry, revocation, dispatch, claim, start, renewal,
  cancellation, completion, failure, events, lease recovery, and fencing.
- An independent long-running Python Runner with outbound polling only,
  persistent credentials, typed executors, cancellation, backoff, and redacted
  evidence.
- Browser Runner registry, dispatch, job detail, cancellation, timeline,
  offline/conflict/error/empty/loading/retry states, keyboard/focus semantics,
  desktop and narrow layouts.
- Compose network isolation, non-root/read-only Runner container, local secret
  bootstrap automation, Make targets, CI, tests, deterministic Eval, runbooks,
  architecture/security documents, ADRs, and verification evidence.
- One Phase 3 checkpoint after complete local verification.

## Non-goals

- OpenAI Agents SDK, LLM calls, embeddings, vector stores, or model scores.
- Any target repository mount, locator, scan, read, write, or command.
- CreativeDeploy access of any kind in Phase 3.
- Isolated worktrees, file tools, generic shell, subprocess-backed tools,
  dependency installation, target build/test/browser execution, or Docker
  socket access.
- Git branch/commit/push/PR capabilities exposed by the product.
- External network destinations, GitHub integration, authentication,
  multi-tenancy, production deployment, Redis, Celery, Temporal, Kafka,
  Kubernetes, Electron, Tauri, or native clients.
- Automatic repair, rollback execution, main merge, remote push, or deploy.

## Constraints and safety

1. Web, API, and PostgreSQL never receive customer repository write access.
2. The Phase 2 API read-only mount remains historical and is not part of the
   Phase 3 platform configuration.
3. The Runner has no repository mount, Docker socket, SSH material, inbound
   port, database network, Web network, shell tool, or public egress.
4. Deployment Pack data can only narrow a future envelope; it cannot expand
   capability.
5. Plan approval remains unrelated to Runner dispatch or execution authority.
6. Bootstrap and Runner tokens never enter Git, logs, AuditEvent,
   RunnerJobEvent metadata, screenshots, or API read responses.
7. Only high-entropy random tokens use SHA-256 digests; no user-password
   hashing is introduced.
8. Every Runner mutation carries a request ID. Attempt mutations additionally
   bind runner ID, attempt ID, and lease ID.
9. Stale, expired, superseded, revoked, or mismatched leases fail closed with a
   stable error and cannot change a Job.
10. Cancellation prevents a later success result.
11. Customer 0 stays stopped with its database volume preserved. Phase 3
    automation must not select or stop other projects' containers.
12. No destructive Git command, remote, push, merge of Phase 3, global
    configuration, sudo, or package-manager system installation is allowed.

Stop implementation if the required network boundary cannot be expressed,
claim uniqueness or stale fencing cannot be proven, a token leaks, a mandatory
test cannot pass without weakening policy, a migration threatens retained
data, or the worktree cannot be made clean without deleting unknown content.

## Trust boundary

The Control Plane consists of Web, API, and PostgreSQL. It owns user intent,
policy derivation, durable state, identity, scheduling, leases, cancellation,
audit, and evidence indexes. It does not execute customer code.

The Execution Plane is one or more independent outbound Local Runners. A
Runner authenticates to the Control Plane, validates every received immutable
Envelope, and invokes only an in-process typed executor. It has no authority
from Task text, repository content, Plan approval, or client-supplied policy.

Browser input, Runner requests, persisted JSON, and protocol payloads are
untrusted at each boundary. The local operator controls the machine, but this
phase is not hardened for public or hostile multi-user exposure.

## Runner Protocol

- Protocol version is integer `1`; HTTP prefix is
  `/api/v1/runner-protocol/v1`.
- `packages/runner-protocol/` contains only Pydantic schemas, enums, protocol
  constants, canonical JSON serialization, policy hashing, typed results, and
  stable error codes.
- API and Runner depend on that package. The Runner must not import API
  internals, SQLAlchemy, FastAPI routes, or database code.
- Canonical serialization uses sorted keys, UTF-8, compact separators, UTC
  timestamps, and excludes the stored `policy_hash` from its own hash input.
- Register uses the Bootstrap Token. Every other Runner route uses a
  per-Runner Bearer Token.
- Claims return one complete Envelope and lease identity. Start, renew,
  complete, fail, and cancel acknowledgement are idempotent for an identical
  request against the active attempt.
- Oversized, extra-field, secret-like, path-like, hostname/username, arbitrary
  metadata, unsupported capability, expired policy, or policy-hash mismatch
  inputs fail with stable public errors.

## Data model

### Runner

UUID identity, display name, protocol/software versions, normalized typed
capabilities, high-entropy token digest, registered/online/offline/revoked
status, last seen, registered/revoked timestamps, optimistic version, and
created/updated timestamps. Online/offline presentation is derived from
`last_seen_at` plus the configured threshold; client status text is not
authoritative.

### PermissionEnvelope

Immutable UUID row bound one-to-one to a Job with envelope version,
authorization source, allowed capabilities, fixed
`repository_access = none`, fixed `shell_access = false`, fixed
`network_policy = control_plane_only`, bounded runtime/lease/attempt/result
budgets, issued/expiry timestamps, canonical policy hash, and creation time.
It contains no locator, path, arbitrary command, or mutable policy JSON.

### RunnerJob

UUID identity, closed kind/state, immutable Envelope link,
`requested_by = local_user`, strictly typed normalized parameters, optional
active attempt ID, attempt/max-attempt counts, typed sanitized result, stable
error code/message, optimistic version, and timestamps.

### RunnerJobAttempt

UUID identity, Job and Runner links, positive attempt number, high-entropy
lease UUID used as a fencing token, closed state, lease deadline, heartbeat,
start/completion/error fields, and creation time. A partial unique PostgreSQL
index permits at most one active leased/running Attempt for a Job.

### RunnerJobEvent

UUID identity, Runner/Job/Attempt links as applicable, closed event type,
monotonic per-Job sequence, request ID, bounded typed sanitized metadata, and
creation time. Heartbeat polling updates `Runner.last_seen_at`; it does not
append an event for every heartbeat.

## Job state machine

Allowed Job transitions:

```text
queued -> leased
leased -> running
leased -> cancel_requested
running -> cancel_requested
running -> succeeded
running -> failed
cancel_requested -> cancelled
leased|running -> queued       only through lease-expiry recovery
leased|running -> failed       only when retry budget is exhausted
```

Terminal `succeeded`, `cancelled`, and `failed` Jobs are immutable. Queued Jobs
cannot succeed directly. A success after `cancel_requested` is denied. The
service owns one explicit transition table; routes do not assign state.

Attempt transitions are `leased -> running -> succeeded|cancelled|failed`, with
`leased|running -> lease_expired` only in the reaper.

## Credential strategy

`make platform-up` invokes a reviewed local script that creates
`.env.runner.local` with a cryptographically random Bootstrap Token when
missing, sets restrictive file permissions, and never prints its value. The
file is ignored; `.env.example` contains placeholders only.

Registration compares the supplied Bootstrap Token in constant time against
the configured high-entropy value. The Control Plane creates an independent
at-least-256-bit Runner Token, returns it once, and persists only its SHA-256
digest. The Runner stores the token in a dedicated Docker volume with the
restrictive permissions available to its non-root user. Subsequent requests
use `Authorization: Bearer`; public errors do not reveal whether a Runner ID
exists.

mTLS, workload identity, enterprise secret managers, and automated rotation
are documented future production upgrades, not implemented claims.

## Permission Envelope

The Control Plane derives an Envelope solely from the closed Job kind. The
browser submits only typed Job parameters, never an Envelope.

- `system_diagnostic_v1` allows `system_diagnostic_v1`.
- `controlled_wait_v1` allows `controlled_wait_v1` with a bounded duration.
- Both fix repository access to none, shell to false, and network to
  Control Plane only.
- Runtime, lease, attempts, result bytes, issue time, and expiry are
  Control-Plane values.

The Runner recomputes the policy hash and validates version, expiry,
capability, repository, shell, network, and all budgets before start. A denied
Envelope produces a typed policy denial; it never falls back to broader work.

## Lease, claim, and fencing

Claim uses an explicit PostgreSQL transaction and
`SELECT ... FOR UPDATE SKIP LOCKED`. The transaction selects one queued Job,
creates its next Attempt and random lease UUID, updates the Job atomically, and
appends the claimed event. Concurrent claims therefore have one winner.

Every Attempt mutation locks and verifies the active Job/Attempt, authenticated
Runner, attempt ID, lease ID, lease deadline, Runner revocation, and allowable
state before applying an idempotent transition. An expired or superseded lease
returns `409 stale_lease` and cannot overwrite the active result.

## Cancellation

The browser requests cancellation through the user API. A queued Job becomes
cancelled immediately; leased/running becomes `cancel_requested`.
Renew/heartbeat responses expose that request to the active Runner. The
controlled-wait executor checks it at short bounded intervals and posts
`cancelled`. The Control Plane rejects completion after cancellation.

The UI distinguishes requested cancellation from completed cancellation.

## Lease expiry and lost-runner recovery

A FastAPI lifespan loop runs the reaper on a configurable interval. A
PostgreSQL advisory transaction lock ensures one active reaper across local API
replicas.

For each expired active Attempt, the reaper marks it `lease_expired` and
appends an event. An uncancelled Job with remaining attempts returns to
`queued`; exhausted retries become `failed`. A `cancel_requested` Job becomes
`cancelled` and never requeues. The future production seam is a separate
Control Plane worker; no broker is added now.

## Runner execution

The long-running Runner loads typed settings and durable credentials, performs
one-time registration if needed, heartbeats, polls with bounded waits, validates
the Envelope, starts the Attempt, runs the selected in-process executor,
renews/checks cancellation, and reports one typed terminal result.

Diagnostics use Python standard-library APIs only and return software/protocol/
Python version, OS family, architecture, normalized capability list, timestamps,
and duration. They exclude hostname, username, IP, environment, paths, package
inventory, files, and external network facts.

Controlled wait uses monotonic time plus bounded async waits. Neither executor
uses a shell, subprocess, repository, filesystem content, or external network.
Transient API failures use capped exponential backoff with jitter and graceful
shutdown.

## Docker network

- `runner-control` is an internal network containing only API and Runner.
- API also joins the normal Control Plane network for PostgreSQL and Web.
- Runner joins only `runner-control`, publishes no port, and cannot resolve or
  connect directly to PostgreSQL or Web.
- Runner is non-root, drops all capabilities, enables no-new-privileges, uses a
  read-only root filesystem and tmpfs `/tmp`, and mounts only its dedicated
  credential volume.
- No customer repository, developer directory, Docker socket, SSH material, or
  host credential path is mounted.

Compose rendering and runtime inspection must prove these claims. The internal
network is the local V1 egress boundary; production-grade network policy
remains future work.

## Current progress

- [x] 2026-07-26: Verified exact Phase 2 branch/commit baseline, clean
      worktree, no remote, repository-local Git identity, Customer 0 services,
      and expected ports.
- [x] 2026-07-26: Queried the specified existing Run, Plan, Snapshot, decision,
      and Audit Timeline; verified the browser-originated rejection and
      absence of execution/write events.
- [x] 2026-07-26: Recorded the decision in four evidence/status documents,
      passed focused formatting/security/link/diff checks, and created commit
      `336b46d` with the required message.
- [x] 2026-07-26: Stopped only the Customer 0 Web/API/database containers and
      preserved its PostgreSQL volume.
- [x] 2026-07-26: Verified `main` at the Foundation history, fast-forwarded
      Phase 2 with no merge commit, and passed the existing full `make verify`.
- [x] 2026-07-26: Created the dedicated Phase 3 branch and this ExecPlan before
      runtime implementation.
- [x] 2026-07-26: Inspected API, Web, migration, contract, Docker, test, and
      CI seams.
- [x] 2026-07-26: Implemented and focused-tested protocol, schema, state machine, credentials,
      transaction-safe scheduling, leases, fencing, cancellation, and reaper.
- [x] 2026-07-26: Implemented and focused-tested the independent Runner and
      typed executors.
- [x] 2026-07-26: Implemented and focused-tested Web registry, dispatch, job
      detail, timeline, and
      cancellation.
- [x] 2026-07-26: Implemented Compose isolation, local automation, CI, Eval,
      required docs, ADRs, and in-progress evidence.
- [x] 2026-07-26: Passed real-stack Playwright 10/10 and isolated Runner chaos
      recovery after repairing recorded test issues.
- [x] 2026-07-26: Passed all focused real-stack, smoke, chaos, security,
      migration, Docker configuration, runtime-boundary, and browser gates
      without weakening policy.
- [x] 2026-07-26: Passed the complete pre-commit `make verify` aggregate gate.
- [x] Audit and stage the exact Phase 3 diff, create the one checkpoint, rerun
      post-commit verification, and leave the Phase 3 platform running.

## Decisions

1. Use PostgreSQL as the bounded V1 queue because durable relational state,
   row locks, `SKIP LOCKED`, and low local throughput fit the milestone.
   Upgrade to a broker only when measured throughput, fan-out, scheduling, or
   operational isolation warrants its cost.
2. Use outbound polling rather than inbound Runner HTTP. This keeps the Runner
   behind the Control Plane boundary and removes an exposed Runner port.
3. Use random bearer credentials with digests for local V1. Do not imply that
   this is production workload identity.
4. Keep protocol definitions in an independent pure package to prevent API
   internals from becoming an accidental Runner trust dependency.
5. Derive Envelopes server-side by Job kind and persist them immutably. The
   browser and Deployment Pack cannot submit expanded authority.
6. Keep RunnerJobEvent distinct from Agent Trace. No Agent Trace is introduced
   because no LLM or repository tool exists.
7. Use polling in the Web Console. WebSockets are unnecessary for this local
   foundation.

## Risks

| Risk                                | Likelihood | Impact   | Mitigation / next action                                                 |
| ----------------------------------- | ---------- | -------- | ------------------------------------------------------------------------ |
| Duplicate concurrent claim          | Medium     | Critical | Row lock, partial unique index, independent-transaction regression       |
| Stale Runner overwrites result      | Medium     | Critical | Three-part fencing identity and expiry checks on every mutation          |
| Token appears in logs/artifacts     | Medium     | Critical | Redaction, no body logging, dynamic-token scans across DB/log/API/tests  |
| Cancellation races completion       | Medium     | High     | Locked transition table; deny success after cancel; concurrency tests    |
| Reaper races renewal                | Medium     | High     | Advisory lock plus row locks and deadline recheck                        |
| Docker egress broader than claimed  | Medium     | High     | Internal isolated network and runtime network/mount inspection           |
| Protocol drift                      | Medium     | High     | Shared package, generated OpenAPI, drift gate, API/Runner contract tests |
| Event/heartbeat growth              | Medium     | Medium   | last-seen updates without per-heartbeat event append                     |
| Local bearer token theft            | Low        | High     | ignored restrictive files/volume; document local-only limitation         |
| Phase 2 mount accidentally retained | Low        | Critical | base platform has no repository override; config and mount assertions    |

## Discoveries

- Customer 0 was already running and contained the exact expected durable
  browser rejection; no recovery or state creation was necessary.
- Phase 2 has no standalone decision-read route, so closure used API reads for
  Run/Plan/Snapshot/Audit plus a read-only PostgreSQL query for the decision.
- The existing full post-merge verification passes: 55 backend tests, 21
  frontend tests, six real-stack Playwright flows, migration round trip,
  security, Eval, Docker configuration, and contract drift.
- The repository currently uses one root Python project and pnpm workspace;
  the pure protocol and Runner are integrated through source paths without
  importing API internals.
- The focused real PostgreSQL run now collects 76 backend/Runner/protocol tests
  and covers the Phase 3 concurrency, credential, state, and policy boundaries.
- Real Playwright starts a true Runner container on the internal control
  network and passes diagnostic/cancellation at desktop and 390 px.
- Graceful SIGTERM intentionally allows the active typed Job to complete.
  Abrupt process-loss recovery therefore requires a zero-timeout container
  stop in the chaos harness.
- The protocol had strict field/result bounds but no request-wide bound.
  A 64 KiB Runner-protocol middleware gate and adversarial regression were
  added before final verification.

## Failures and fixes

- The first Phase 2 closure format check found one Prettier-only Markdown
  wrapping difference. The repository formatter corrected it; the unchanged
  full format gate then passed.
- The first static Runner security scan treated safe `platform.system()` as a
  prohibited `system()` call. The marker was narrowed to real
  `os.system`/subprocess primitives while AST import denial remains.
- The first Playwright run passed 8/10. Both failures were the same strict
  selector matching an event label and its metadata; the product state was
  correct. The exact event selector was fixed and the full run passed 10/10.
- The first chaos run used graceful `docker compose stop`; Runner completed the
  wait, so the Job succeeded instead of expiring. Chaos now uses
  `stop --timeout 0`, then passed offline, expiry, requeue, old completion
  fencing, recovery, and success.
- One direct pytest invocation omitted the required test PostgreSQL and failed
  at fixture setup. It was rerun through `make test-api`, which started the
  dedicated database and passed 76/76 with 83.92% coverage.
- The first final static group found two Ruff import-order findings and two
  strict mypy `Any` return findings. Imports were sorted and typed response
  casts were added; the full group then passed unchanged thresholds.
- One read-only migration inspection used an obsolete candidate filename. It
  was immediately rerun against the actual revision filename and performed no
  repository mutation.
- The first staged large-file loop reused zsh's special `path` variable, so
  `git` was unavailable inside that loop. The invalid result was discarded and
  the loop was rerun with a safe variable name; no staged file exceeds 1 MiB.

## Test strategy

Backend tests use real PostgreSQL for registration, digests, online/offline,
revocation, dispatch, canonical policy hash, concurrent claim, start/renew,
cancellation, lease expiry/requeue/exhaustion, fencing, idempotency, result
validation, event ordering, migration round trip, and OpenAPI semantics.

Runner unit/contract tests cover registration, credential persistence/restart,
redaction, heartbeat/claim, Envelope rejection, typed diagnostics/wait,
cancellation, transient failure, backoff, stale lease, unsupported capability,
and shutdown without invoking a shell.

Vitest covers registry states, dispatch preview, Job states, cancellation,
lease expiry/retry, typed result, timeline, revoked/offline behavior, and narrow
layout. Playwright uses real Web/API/PostgreSQL/Runner for success and
cancellation at desktop and 390 px with axe and overflow assertions.

Chaos stops only the Phase 3 Runner after it leases a controlled wait, proves
offline/expiry/requeue/new attempt/stale-fence denial/recovery/success, and
leaves the source tree clean.

## Eval

`evals/datasets/runner-protocol-v0.1.jsonl` is deterministic and versioned. It
covers registration, heartbeat, claim, concurrency, Envelope, stale lease,
cancel, retry, offline, secret/path redaction, unsupported capability,
terminal immutability, and stable failure categories. `make eval` validates
schema, version, expected outcome, failure category, parseability, unique IDs,
and explicit test mappings. It records no model score because no model exists.

## Verification ledger

| Gate                                              | Status   | Exit / result                                  |
| ------------------------------------------------- | -------- | ---------------------------------------------- |
| Phase 2 focused format/security/link/diff closure | VERIFIED | exit 0                                         |
| Post-merge existing `make verify`                 | VERIFIED | exit 0                                         |
| `make format`                                     | VERIFIED | exit 0                                         |
| `make format-check`                               | VERIFIED | exit 0                                         |
| `make lint`                                       | VERIFIED | exit 0                                         |
| `make typecheck`                                  | VERIFIED | exit 0                                         |
| `make test`                                       | VERIFIED | 76 backend/Runner/protocol + 32 frontend       |
| `make build`                                      | VERIFIED | Next.js production build                       |
| `make contracts-check`                            | VERIFIED | repeatable OpenAPI/TypeScript generation       |
| `make migration-check`                            | VERIFIED | PostgreSQL upgrade/downgrade/upgrade           |
| `make security-check`                             | VERIFIED | secret/scanner/protocol/Runner gates           |
| `make eval`                                       | VERIFIED | 43 deterministic cases                         |
| `make e2e`                                        | VERIFIED | 10/10 real-stack desktop + 390 px              |
| `make runner-smoke`                               | VERIFIED | online Runner and diagnostic success           |
| `make runner-chaos-check`                         | VERIFIED | offline/expiry/requeue/fence/recovery/success  |
| `make verify` pre-commit                          | VERIFIED | exit 0                                         |
| `make verify` post-commit                         | VERIFIED | exit 0                                         |
| `docker compose config`                           | VERIFIED | base, test, E2E, and Customer 0 render         |
| concurrent claim / stale fencing                  | VERIFIED | real PostgreSQL + chaos old complete 409       |
| offline / expiry / requeue / recovery             | VERIFIED | isolated real-container chaos                  |
| token and absolute-path absence                   | VERIFIED | DB/API/log/schema/static tests and source scan |
| runtime Docker network and mounts                 | VERIFIED | UID 10001, API-only network, one 0600 volume   |
| browser success and cancellation                  | VERIFIED | real Runner, both viewports, axe               |
| final clean status / no remote                    | VERIFIED | clean branch; no configured remote             |

## Deviations

No product-scope or trust-boundary deviation. Test mechanics changed from a
graceful stop to a zero-timeout stop because graceful shutdown is not process
loss; this is recorded above and does not change Runner production behavior.

## Rollback

- Stop only the exact Phase 3 Compose project with `make platform-down`; do not
  remove the Customer 0 volume or any other project's container/volume.
- Before checkpoint, reverse only inspected Phase 3 paths with targeted
  patches. Never use reset-hard, clean, stash, or broad deletion.
- The Alembic downgrade removes only Phase 3 tables, triggers, indexes, and
  constraints after verification against a disposable database.
- Revoke a local Runner through the Control Plane if a Runner credential is
  suspected. Delete/replace ignored local bootstrap state only after the exact
  target is identified and recovery is documented.
- No remote, push, PR, deployment, or Phase 3 merge exists to roll back.

## Completion conditions

1. All five entities, constraints, immutable Envelope, explicit transitions,
   claim uniqueness, leases, retries, and fencing are implemented and verified
   on real PostgreSQL.
2. Bootstrap/Runner credentials are generated, stored, compared, redacted, and
   persisted exactly within the declared local boundary.
3. A real Runner performs only typed diagnostic/wait jobs, validates Envelope
   authority, renews leases, observes cancellation, and recovers from API loss.
4. Docker config and runtime inspection prove the Runner has only the API
   network plus its own credential volume and no repository/database/Web/
   Docker-socket/SSH/public-network access.
5. The browser completes real diagnostic success and controlled-wait
   cancellation flows at desktop and 390 px with axe and no overflow.
6. Chaos proves offline detection, expiry, requeue, a new Attempt, stale-fence
   denial, recovery, and final success without touching another project.
7. Required unit, integration, migration, contract, security, Eval, build,
   Docker, E2E, smoke, chaos, and aggregate commands return exit 0.
8. Documents and ADRs distinguish implemented, verified, Phase 4, local-token
   limits, PostgreSQL queue limits, and every explicit non-goal.
9. The staged diff contains no secret, local token, absolute personal path,
   customer code, environment file, runtime artifact, report, cache, large
   generated file, or unrelated change.
10. One Phase 3 commit exists on the Phase 3 branch; `main` remains at the
    Phase 2 closure; no remote or push exists; the worktree is clean; and the
    Phase 3 platform remains running for browser inspection.

## Outcome and follow-ups

COMPLETE locally. The repository-free Runner foundation, browser flows,
failure recovery, security boundary, and all mandatory gates are verified.
`main` remains at the Phase 2 closure, the current branch contains one Phase 3
checkpoint, no remote/push/merge occurred, and the platform remains running.
The exact final commit hash is recorded in the post-commit handoff because a
commit cannot self-embed its own object ID. Phase 4 should be one separately
reviewed isolated-worktree readiness milestone; it is not implemented here.
