# VisualEngineer Agent Instructions

This file is the operating contract for Codex and other coding agents in this
repository. Follow the closest `AGENTS.md` if a more specific one is added
later. Explicit user instructions override this file.

## Repository map

- `apps/api/`: FastAPI service, PostgreSQL persistence, Alembic migrations,
  and backend tests.
- `apps/web/`: Next.js App Router console, frontend tests, and Playwright
  configuration.
- `packages/api-contract/`: generated OpenAPI specification and generated
  TypeScript types. Treat generated outputs as derived artifacts.
- `docs/`: product, architecture, security, decisions, execution plans,
  runbooks, status, and verification evidence.
- `evals/datasets/`: deterministic evaluation cases; never record invented
  Agent scores.
- `infra/`: container definitions and infrastructure configuration.
- `scripts/`: small, reviewed project automation.
- `.github/workflows/`: CI definitions only; no deployment workflow belongs in
  the Foundation Sprint.

## Stack and authority

- Web: Node.js, pnpm workspace, Next.js App Router, strict TypeScript,
  Tailwind CSS, ESLint, Prettier, Vitest, React Testing Library, Playwright,
  and axe.
- API: Python 3.12-compatible source layout, uv, FastAPI, Pydantic v2,
  SQLAlchemy 2, Alembic, PostgreSQL, pytest, Ruff, mypy, and coverage.
- FastAPI's exported OpenAPI document is the source of truth for the HTTP
  contract. Do not hand-maintain duplicate core request or response types.
- PostgreSQL migrations are the source of truth for persistent schema history.

## Product scope

- VisualEngineer is a governed AI design-engineering and delivery system for
  enterprise frontend teams, not a general-purpose coding Agent.
- V1 work must fit one of three delivery packages: Design Implementation,
  Design-System Migration, or Frontend Quality Remediation.
- Keep VisualEngineer Core policy/orchestration concerns separate from a
  customer Deployment Pack containing repository profile, customer constraints,
  allowed commands, design-system context, acceptance criteria, test strategy,
  and project playbook.
- CreativeDeploy is Customer 0 and Design Partner 0, not an external enterprise
  customer or evidence of production adoption.
- Never describe planned Agent, approval, worktree, repair, rollback, GitHub, or
  deployment capability as implemented without executable evidence.

## Standard workflow

Before editing, read the relevant product, architecture, security, ADR, and
active ExecPlan documents. Inspect `git status --short` and preserve unrelated
or pre-existing changes.

Use the root commands where they exist:

```sh
make bootstrap
make db-up
make db-down
make migrate
make contracts
make format
make format-check
make lint
make typecheck
make test
make build
make e2e
make verify
make up
make down
make logs
```

Do not report a command as passing unless it ran in the current worktree and
returned exit code 0. Record material verification in
`docs/evidence/phase-0-1-verification.md` or the evidence file for the active
phase.

## Implementation rules

- Keep routes, configuration, persistence models, repositories, schemas, and
  business logic separated where they have distinct responsibilities. Do not
  create empty abstraction layers for appearance.
- Use explicit transactions for database mutations. Store timestamps as
  timezone-aware UTC.
- Validate bounds, blank values, enum values, and NUL characters at system
  boundaries.
- A repository locator is metadata. Receiving a path or URL never authorizes
  reading, executing, or modifying it.
- Never log full request bodies, credentials, tokens, connection strings, or
  other sensitive data. Preserve request IDs and stable public error codes.
- Frontend code must handle loading, empty, failure, and retry states and must
  preserve keyboard focus visibility and accessible names.
- Avoid nondeterministic LLM behavior for logic that code can determine.
- Do not add an Agent runtime, fake tools, fake traces, or unused SDKs to imply
  capabilities that do not exist.

## Contract and generated-file rules

1. Change the FastAPI/Pydantic contract first.
2. Export OpenAPI through the repository script or `make contracts`.
3. Generate TypeScript types from the exported specification.
4. Update consumers and tests.
5. Run the contract drift check and confirm regeneration leaves no diff.

Do not manually patch generated OpenAPI or generated TypeScript types. If
generation produces an unexpected change, fix the source schema or generator.
Only commit generated output after its source and verification are included.

## Migration rules

- Create a migration for every persistent schema change; do not edit an
  already-shared migration to rewrite history.
- Keep migrations small, reviewable, and reversible where safe.
- Do not use SQLite as evidence for PostgreSQL behavior.
- Verify a new migration against an empty PostgreSQL database and, for the
  initial migration, run an upgrade/downgrade/upgrade round trip.
- Local Compose may run a clearly identified migration step. Production must
  use a future dedicated release/migration step, not competing web processes.
- Never run a destructive or production migration without explicit human
  approval and a rollback plan.

## Test and regression rules

- Add behavior-level tests for changed behavior, including error paths and
  permission boundaries.
- Backend integration tests use the dedicated PostgreSQL test database.
- Playwright smoke tests use the real web, API, and PostgreSQL stack; do not
  replace that flow with API mocks.
- Do not delete valid tests, disable checks, lower meaningful thresholds, or
  broaden exclusions to make a change pass.
- After a change, run the narrow test first, then the relevant quality,
  contract, build, migration, and end-to-end regression checks.
- Keep generated reports, traces, screenshots, videos, caches, `.venv`, and
  `node_modules` untracked.

## Documentation and ExecPlans

- Update documentation in the same change when behavior, interfaces, commands,
  security boundaries, or project status changes.
- Long-running or multi-system work requires an ExecPlan under
  `docs/exec-plans/`; maintain progress, decisions, discoveries, failures,
  validation, rollback, and outcomes while work is happening.
- Distinguish `IMPLEMENTED`, `VERIFIED`, `NOT YET VERIFIED`, `PLANNED`, and
  `BLOCKED`. Never convert a plan into a claimed result without evidence.
- If an error pattern repeats, decide whether a precise prevention rule belongs
  here, in a test, or in automation. Prefer an enforceable check over a slogan.

## External repository permissions

- External repositories are read-only by default.
- Do not read real `.env` files, credentials, certificates, tokens, or secret
  stores in an external repository.
- Any future target-repository write requires an isolated worktree, a bounded
  approved plan, explicit human approval, path confinement, an audit trail, and
  a rollback checkpoint.
- Tool levels are defined in
  `docs/architecture/tool-permissions.md`. Do not infer a higher level from a
  task description.
- Never run destructive Git commands against an external repository. Do not
  merge its main branch, deploy it, or publish changes.

## Git and security rules

- Never commit `.env`, secrets, tokens, credentials, database data, logs,
  private machine identifiers, or runtime artifacts.
- Do not modify global Git identity or system configuration. If Git identity is
  missing, stop before commit and report the blocker.
- Do not add a remote, push, create a PR, merge, tag, or deploy unless the user
  explicitly authorizes that external action.
- Keep commits scoped and inspect `git diff --check`, the full diff, and
  `git status --short` before committing.
- Never claim GitHub Actions passed remotely from local workflow validation.
- No Agent may automatically merge the main branch.
