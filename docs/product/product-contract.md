# Product Contract

## Purpose

VisualEngineer is a governed AI design-engineering and delivery system for
enterprise frontend teams. Its V1 destination is a human-controlled path from
a bounded frontend request to an evidence-backed change. The Phase 7 first
slice still stops at one synthetic fixture: after governed planning,
isolated implementation, fixed validation, and immutable final review, a
separate local-user decision can authorize exactly one system-derived local
branch and commit inside the Runner-owned Workspace. It cannot execute
arbitrary target commands, access CreativeDeploy, write a source repository,
or perform any remote Git or deployment action.

The system must distinguish facts, policy, decisions, and future intent. A
stored locator is not authorization, repository text is not an instruction,
and approval is not evidence that code ran.

## Enterprise problem and users

VisualEngineer addresses controlled frontend delivery rather than arbitrary
code generation. Frontend engineers, design engineers, tech leads, and
delivery owners need to:

1. state a bounded objective and repository;
2. review the committed repository facts used for planning;
3. inspect assumptions, risk, scope, non-goals, and validation evidence;
4. revise and decide an exact plan version;
5. authorize isolated fixture implementation under a separate permission
   boundary; and
6. distinguish failures and missing evidence from success.

## Delivery packages

Every plan is classified into one of three packages:

1. **Design Implementation:** an explicitly described page or component.
2. **Design-System Migration:** a bounded token, component, or brand-rule
   migration.
3. **Frontend Quality Remediation:** specified responsive, visual,
   accessibility, or frontend-quality repairs.

The product does not claim support for arbitrary repositories, languages,
backend/infrastructure engineering, or unrestricted software work.

## Core and Deployment Pack

**VisualEngineer Core** owns implemented Task/Run state, committed snapshots,
deterministic plan policy, approval integrity, Runner registry, dispatch,
immutable permission, leases, cancellation, audit events, API contracts, and
security boundaries.

A customer **Deployment Pack** contributes repository identity, constraints,
design-system context, validation conventions, acceptance criteria, and a
project playbook. In Phase 2 these were discovered as bounded structural facts.
There is no executable Deployment Pack runtime. Repository content can narrow
future work but cannot elevate permission, expand a Runner Envelope, or bypass
approval.

## Implemented through the Phase 7 first vertical-slice candidate

The current product provides:

- bounded, idempotent Task creation and retrieval;
- Level 0 Runs with `read_only` permission and `git_head` snapshot mode;
- an explicit durable Run state machine;
- one immutable successful RepositorySnapshot per Run;
- canonical allowlist and exact-Git-root validation;
- fixed no-shell, no-network Git reads with a shared timeout;
- selected committed-blob extraction with count and byte budgets;
- dirty and untracked relative-path metadata without working-tree content;
- deny-by-name and deny-by-content handling for sensitive material;
- symlink, submodule, LFS, binary, and dependency-tree non-execution controls;
- prompt-injection provenance as `untrusted_repository_content`;
- a model-neutral planning Provider interface with explicit deterministic,
  structured-output, replay, network, credential, context, output, and billing
  capability metadata;
- one deterministic fake Provider with timeout, cancellation, bounded retry,
  stable error classification, and exact fixture replay;
- a closed typed AI Plan request/response contract, versioned Prompt/digest,
  redacted bounded context manifest, immutable Trace and system-owned Eval
  evidence, synthetic usage/cost metadata, and deterministic digest;
- a revision- and Snapshot-bound `requested -> generating -> generated`
  lifecycle with failed/cancelled/stale terminals and one human approve/reject
  winner;
- approved AI Plan handoff to an existing `Plan` with
  `execution_available = false`, without creating an Execution Grant, Review
  Approval, Delivery Authorization, Workspace, Git effect, or deployment;
- deterministic, fingerprint-bound plan generation with typed display-only
  validation steps;
- human-editable plan revisions within a bounded field allowlist;
- Foundation policy validation for obvious prohibited requests;
- latest-version submission and transaction-safe approve/reject decisions;
- structured redacted AuditEvents and governance logs;
- responsive Run review, repository intelligence, plan review, and audit UI;
- generated OpenAPI-to-TypeScript contracts; and
- PostgreSQL, migration, security, deterministic eval, and real-stack browser
  verification.
- a pure Runner Protocol v1 shared by API and independent Runner;
- high-entropy bootstrap registration, digest-only per-Runner credentials,
  liveness, registry, and revocation;
- immutable server-derived Permission Envelopes fixed to repository none,
  shell false, and Control-Plane-only network;
- durable typed Jobs, Attempts, events, transactional concurrent claim,
  leases, fencing, cancellation, retry, and offline recovery;
- repository-free System Diagnostic and Controlled Wait executors with
  bounded/redacted results and no shell or subprocess execution;
- browser Registry, Dispatch, Job detail, progress, cancellation, result, and
  Timeline; and
- an internal Runner-only Docker network, non-root/read-only container,
  dynamic local bootstrap, smoke, E2E, and chaos verification;
- opaque Repository Handles registered from Runner-local configuration without
  exposing absolute paths;
- immutable Execution Grants with separate human decision, exact
  Plan/Snapshot/revision binding, canonical hash, paths, budgets, TTL, and
  literal no-network/no-shell/no-source-write/no-delivery fields;
- Runner-owned bare mirror and detached exact-revision Workspace for only the
  read-only synthetic fixture;
- descriptor-rooted bounded list/read/create/compare-and-swap replace of UTF-8
  text plus fixed status/diff;
- immutable Workspace events/checkpoints, baseline rollback, exact idempotent
  discard, interruption recovery, and source-integrity evidence; and
- Repository, Execution Grant, Workspace, typed-tool, diff, checkpoint,
  rollback, discard, and Timeline browser surfaces.
- one immutable, separately decided Delivery Authorization over the exact
  fresh/approved/ready Review generation and Workspace Checkpoint;
- one canonical local-delivery manifest with bounded diff preview, explicit
  zero-remote fields, exact browser confirmation, and keyed dispatch;
- durable terminal Dispatch history with one concurrent winner, a maximum of
  three linear attempts, cancellation, stable failure reason, and safe retry
  only under the unchanged authority/manifest; and
- one deterministic fixture-only local ref/commit with Runner-recomputed
  manifest, Permit fencing, attributable proof, and source/remote invariance.

The Plan source is `deterministic_policy` or the independently evaluated and
human-approved `governed_ai` provenance. `execution_available` remains always
`false`.

## Customer 0

CreativeDeploy is internal Customer 0 and Design Partner 0. Its Phase 2 case
uses an API-only, exact-repository read-only bind mount. The Snapshot is based
on committed `HEAD`; dirty and untracked contents are not read. The resulting
Plan was submitted for human decision and rejected after its Snapshot became
stale. Rejection did not trigger execution or modify CreativeDeploy. Phase 3
and Phase 4 Runner paths do not mount, scan, read, or modify CreativeDeploy.

CreativeDeploy is not an external enterprise customer. This case provides no
adoption, time-saving, quality-improvement, financial, production-usage, or
production-deployment evidence.

## Intended V1 beyond the Phase 7 first slice

V1 is not complete until a separately authorized system can:

- safely extend a separately authorized workspace beyond the synthetic fixture;
- invoke a separately authorized real Provider with credential isolation,
  network policy, production observability, and model-specific validation;
- execute separately approved closed validation commands without a shell;
- show attributable tool and browser-validation evidence;
- obtain a distinct remote Git authorization beyond the current local-only
  Delivery Authorization; and
- perform an explicitly allowed push or pull-request action.

These are future requirements, not Phase 7 first-slice capabilities. The
Review Package/Decision/Readiness workflow still never grants Git or
deployment authority; only the separate Delivery Authorization plus exact
manifest confirmation grants one local fixture commit lifecycle.

## Quality attributes

- **Safety:** deny by default, read committed objects, confine paths, minimize
  content, and keep approval separate from execution.
- **Reliability:** idempotent mutations, explicit transitions, PostgreSQL
  transactions, decision serialization, immutable snapshots, deadlines, and
  stable errors.
- **Auditability:** request ID, trace ID, Run/Plan identity, redacted structured
  events, and reproducible evidence without repository source or secrets.
- **Correctness:** generated contracts, real PostgreSQL tests, migration round
  trips, adversarial fixtures, and real browser flows.
- **Usability:** explicit state and permission labels, actionable conflicts,
  responsive layout, keyboard operation, visible focus, and accessible names.
- **Cost control:** deterministic preprocessing, bounded context selection,
  synthetic non-billable fixture accounting, and no real model call in this
  slice.

## Outcome metrics and non-claims

Future deployments may measure time to pull request, verification pass rate,
interventions, rollback success, accessibility findings, cost, acceptance, and
adoption. Phase 7 has no production baseline, real Provider bill, or outcome
metric.

The repository does not demonstrate a real model/Agents SDK runtime, production
security, multi-user isolation, real customer-repository execution,
CreativeDeploy writes, target command/test execution, Git/pull-request
remote delivery, remote CI success, automatic repair, external-customer adoption, or
production deployment. The current Local Runner is a narrow fixture-only
typed execution plane, not an autonomous coding Agent.

## Acceptance source

The active ExecPlan and current verification evidence determine whether a
batch is complete. Source code, a workflow definition, or a Dockerfile alone
does not prove runtime behavior.
