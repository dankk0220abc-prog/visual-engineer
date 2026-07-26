# V1 Boundaries

## Product boundary

VisualEngineer serves enterprise frontend teams through governed delivery. V1
accepts only:

- **Design Implementation:** new pages, components, and explicit design
  requirements;
- **Design-System Migration:** bounded token, component, and brand-rule
  migrations;
- **Frontend Quality Remediation:** specified responsive, visual,
  accessibility, and frontend-quality repairs.

V1 is not a claim of support for arbitrary languages, arbitrary repositories,
backend/infrastructure work, or unrestricted software-engineering requests.

## Foundation Sprint: must implement now

- Task metadata persisted in PostgreSQL.
- `POST /api/v1/tasks` with `Idempotency-Key`.
- Idempotent replay for an equivalent normalized body and conflict for a
  different body under the same key.
- Task list and task detail reads.
- Process liveness and database readiness.
- Stable public error shape and request-ID propagation.
- Responsive browser console with health, create, list, detail, loading, empty,
  error, retry, form validation, keyboard focus, and accessible names.
- FastAPI OpenAPI export and generated TypeScript types.
- PostgreSQL migration history and deterministic checks.
- Local Compose, quality commands, tests, and CI definition.
- Safety, architecture, evaluation, evidence, status, and operating documents.

## V1: reserve deliberate seams

Reserve contracts and boundaries, but do not create empty tables or fake
services, for:

- a `Run` associated with a Task;
- read-only repository investigation;
- explicit plan and final approvals;
- isolated worktree lifecycle;
- policy-checked tool calls;
- checkpoints, artifacts, traces, and evaluation results;
- controlled browser validation and bounded repair loops;
- branch/commit/PR operations after permission elevation.

Reservation means stable identifiers, version fields, state-machine and
permission documentation, API/service boundaries, and migration-friendly
schema ownership. It does not mean placeholder runtime classes or no-op tools.

V1 must keep governed platform behavior in VisualEngineer Core and
repository/customer-specific facts in a Deployment Pack. A Deployment Pack may
describe repository layout, constraints, allowed commands, design-system
context, acceptance criteria, test strategy, and a project playbook; it cannot
raise tool permission or bypass approval.

## Later versions

- Multiple users and organizations with role-based authorization.
- Concurrent project scheduling and quota management.
- Multiple model/provider routing.
- Rich Figma and design-system integrations.
- Visual regression baselines and learned repair strategies.
- Production observability, backup/restore, high availability, and disaster
  recovery.
- Broader source-control and deployment providers.
- Governed production release workflows.

## Explicitly out of scope now

- Any real LLM or OpenAI Agents SDK call.
- Generic shell execution.
- Automatic filesystem access based on `repository_locator`.
- Target-repository writes, including CreativeDeploy.
- An isolated target worktree or generated code modification.
- GitHub token use, repository creation, remote push, PR creation, merge, tag,
  or deployment.
- Redis, Celery, Temporal, a message broker, Kubernetes, or a gateway.
- Authentication, public exposure, and production use.
- Fake traces, Agent scores, approval events, or execution states.
- Using SQLite as evidence for PostgreSQL behavior.
- Treating CreativeDeploy as an external enterprise customer or adoption proof.

## Boundary test

If a proposed Foundation change can act on a target repository, requires a
credential, implies a human approval occurred, or reports an execution state
beyond Task `draft`, it is outside this batch and must stop for a new reviewed
plan.
