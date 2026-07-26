# Product Contract

## Purpose

VisualEngineer is a governed AI design-engineering and delivery system for
enterprise frontend teams. Its V1 destination is a human-controlled path from
a bounded frontend request to an evidence-backed change. The current Phase 3
product stops much earlier: it can complete the governed Phase 2 planning flow
and separately orchestrate a repository-free Local Runner for a typed
diagnostic or controlled wait. It cannot execute a plan or access project
code.

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
5. eventually authorize isolated implementation under a separate permission
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

## Implemented through Phase 3

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
  dynamic local bootstrap, smoke, E2E, and chaos verification.

The plan source is always `deterministic_policy`, and
`execution_available` is always `false`.

## Customer 0

CreativeDeploy is internal Customer 0 and Design Partner 0. Its Phase 2 case
uses an API-only, exact-repository read-only bind mount. The Snapshot is based
on committed `HEAD`; dirty and untracked contents are not read. The resulting
Plan was submitted for human decision and rejected after its Snapshot became
stale. Rejection did not trigger execution or modify CreativeDeploy. Phase 3
does not mount, scan, read, or modify CreativeDeploy.

CreativeDeploy is not an external enterprise customer. This case provides no
adoption, time-saving, quality-improvement, financial, production-usage, or
production-deployment evidence.

## Intended V1 beyond Phase 3

V1 is not complete until a separately authorized system can:

- create a new isolated worktree for an approved plan;
- enforce typed write and validation tools at runtime;
- preserve checkpoints and recover from bounded failures;
- show attributable tool and browser-validation evidence;
- obtain a distinct final delivery approval; and
- perform an explicitly allowed branch, commit, or pull-request action.

These are future requirements, not Phase 3 capabilities.

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
- **Cost control:** deterministic preprocessing, bounded file selection, and no
  LLM for programmatically decidable work.

## Outcome metrics and non-claims

Future deployments may measure time to pull request, verification pass rate,
interventions, rollback success, accessibility findings, cost, acceptance, and
adoption. Phase 3 has no production baseline or outcome metric.

The repository does not demonstrate an LLM/Agents SDK runtime, production
security, multi-user isolation, repository reading/writing by Runner, isolated
worktrees, target command execution, pull-request delivery, remote CI success,
automatic repair, rollback, external-customer adoption, or production
deployment. The current Local Runner is a narrow typed execution-plane
foundation, not an autonomous coding Agent.

## Acceptance source

The active ExecPlan and current verification evidence determine whether a
batch is complete. Source code, a workflow definition, or a Dockerfile alone
does not prove runtime behavior.
