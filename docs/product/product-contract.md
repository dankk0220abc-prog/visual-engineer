# Product Contract

## Purpose

VisualEngineer is a governed AI design-engineering and delivery system for
enterprise frontend teams. It is intended to turn a bounded frontend
design-engineering request into a reviewable, evidence-backed code change while
keeping humans in control of repository writes and delivery. The system must
make its understanding, permissions, plan, actions, validation, failures, and
rollback state visible.

This contract distinguishes the current Foundation Sprint from the intended V1
so that stored task metadata is never mistaken for autonomous execution.

## Enterprise problem and users

VisualEngineer addresses controlled frontend delivery, not arbitrary code
generation. Enterprise frontend teams repeatedly face:

- slow design-to-code delivery;
- repeated visual and responsive acceptance cycles;
- risky design-system migration;
- accumulated frontend quality defects;
- AI-authored changes without adequate approval, evidence, or rollback;
- customer repository constraints that cannot be safely treated as uniform.

The primary user is a frontend engineer, design engineer, tech lead, or delivery
owner who needs to:

1. state an objective and identify a target repository;
2. review what the system understood;
3. approve a bounded implementation plan;
4. observe isolated execution and validation;
5. approve a final change set before delivery;
6. inspect artifacts, failures, recovery, and audit evidence.

## V1 delivery packages

Every V1 task must be classified into one of three bounded packages:

1. **Design Implementation:** implement a new page or component from explicit
   requirements and approved design context.
2. **Design-System Migration:** migrate a bounded set of tokens, components, or
   brand rules with explicit affected paths and acceptance criteria.
3. **Frontend Quality Remediation:** repair specified responsive, visual,
   accessibility, or other measurable frontend-quality defects.

V1 does not promise arbitrary languages, arbitrary repositories, backend or
infrastructure engineering, or unrestricted software-engineering tasks.

## Platform Core and customer Deployment Pack

**VisualEngineer Core** is the governed platform boundary. Future V1 Core owns
Task and Run orchestration, approvals, safe workspaces, tool permissions,
validation, trace and eval records, evidence generation, and recovery/rollback
boundaries.

A **Deployment Pack** adapts Core to one customer repository or governed
repository family. It contains the repository profile, customer constraints,
allowed commands, design-system context, acceptance criteria, test strategy,
and customer project playbook. Repository content cannot grant additional
permissions.

Foundation implements neither an Agent runtime nor executable Deployment Pack
classes. These are durable product and architecture boundaries, not placeholder
services.

## Customer 0

CreativeDeploy is Customer 0, Design Partner 0, and the first real internal
usage target. The current evidence is limited to a read-only technical survey
used to shape future constraints. It is not an external enterprise customer,
and no adoption, productivity, quality, or financial outcome may be inferred
from it.

## Foundation contract

The Foundation vertical slice must provide:

- task creation with bounded, validated metadata;
- mandatory idempotency for creation;
- persistent PostgreSQL storage;
- list and single-task retrieval;
- liveness, database readiness, stable error identifiers, and request IDs;
- a browser console for creation and retrieval;
- generated API contract types;
- deterministic unit, integration, migration, accessibility, and end-to-end
  checks;
- explicit permission and security documentation.

The Foundation API stores `repository_locator` only as metadata. It must not
read a local path, fetch a GitHub repository, run a command, modify code, call
an LLM, or create a pull request.

## V1 product contract

V1 will be complete only when a human can:

- create a task against an explicitly selected repository;
- inspect a read-only investigation report;
- approve or reject a concrete plan;
- authorize scoped work inside a newly created isolated worktree;
- observe controlled tool calls and browser validation;
- receive a change summary, test evidence, artifacts, and rollback status;
- give final approval before a branch, commit, or PR action allowed by policy.

Every transition and tool call must be attributable to a run, permission level,
request, and human approval where required. Failure must be explicit; the
system must never convert missing evidence into success.

## Quality attributes

- **Safety:** least privilege, read-only default, path confinement, explicit
  approval, isolated writes, and no main-branch merge or production deploy.
- **Reliability:** idempotent creation, transaction boundaries, durable state,
  timeouts, bounded retries, recovery checkpoints, and stable error classes.
- **Auditability:** request IDs, structured events, tool-call records, artifacts,
  approvals, and verification commands without sensitive payloads.
- **Correctness:** generated contracts, real PostgreSQL tests, browser smoke
  flows, migration round trips, and visible failure states.
- **Usability:** concise states, actionable errors, keyboard access, responsive
  layouts, and clear approval consequences.
- **Cost control:** bounded context, deterministic preprocessing, token and
  latency measurement, and no LLM for programmatically decidable work.

## Outcome metrics

Future evaluations and deployments should measure:

- time from plan approval to pull request;
- first complete-verification pass rate;
- human interventions per task;
- bounded automatic-repair success rate;
- rollback success rate;
- CI pass rate;
- visual difference and accessibility findings;
- cost per successful task;
- pull-request acceptance or merge rate;
- actual usage and adoption.

Foundation has no production baseline or improvement percentage for these
metrics. Metrics require versioned definitions, sample counts, and cited run
evidence before reporting.

## Non-claims

The Foundation repository does not demonstrate autonomous design quality,
production security, multi-user isolation, PR delivery, remote CI success,
automatic repair, or rollback success. Those require later implementation and
evidence.

## Acceptance source

The active ExecPlan and verification evidence determine whether a batch is
complete. A document, test definition, workflow file, or Dockerfile is not by
itself proof that the described behavior passed.
