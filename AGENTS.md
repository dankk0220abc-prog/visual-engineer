# VisualEngineer Agent Instructions

This file is the operating contract for Codex and other coding agents in this
repository. Follow the closest `AGENTS.md` if a more specific one is added
later. Explicit user instructions override this file.

## Repository map

- `apps/api/`: FastAPI service, PostgreSQL persistence, Alembic migrations,
  and backend tests.
- `apps/web/`: Next.js App Router console, frontend tests, and Playwright
  configuration.
- `apps/runner/`: independent outbound Local Runner and repository-free typed
  executors.
- `packages/api-contract/`: generated OpenAPI specification and generated
  TypeScript types. Treat generated outputs as derived artifacts.
- `packages/runner-protocol/`: pure versioned Pydantic protocol, canonical
  policy hashing, typed results, and errors; no API/database/executor code.
- `docs/`: product, architecture, security, decisions, execution plans,
  runbooks, status, and verification evidence.
- `evals/datasets/`: deterministic evaluation cases; never record invented
  Agent scores.
- `infra/`: container definitions and infrastructure configuration.
- `scripts/`: small, reviewed project automation.
- `.github/workflows/`: CI definitions only; no deployment workflow belongs in
  Phase 3.

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
- Phase 2 approval is a durable decision only. Phase 3 Runner dispatch is a
  separate browser action and grants only its immutable Envelope. Never
  describe approval as execution authority, or planned repository tools,
  worktree, repair, rollback, GitHub, or deployment capability as implemented
  without executable evidence.

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
make contracts-check
make migration-check
make security-check
make eval
make e2e
make verify
make platform-up
make platform-down
make platform-logs
make runner-status
make runner-smoke
make runner-chaos-check
```

Do not report a command as passing unless it ran in the current worktree and
returned exit code 0. Record material verification in
the evidence file for the active phase.

## Implementation rules

- Keep routes, configuration, persistence models, repositories, schemas, and
  business logic separated where they have distinct responsibilities. Do not
  create empty abstraction layers for appearance.
- Use explicit transactions for database mutations. Store timestamps as
  timezone-aware UTC.
- Validate bounds, blank values, enum values, and NUL characters at system
  boundaries.
- A repository locator grants no authority by itself. Phase 2 may read only a
  canonical exact Git root inside `READ_ONLY_REPOSITORY_ROOTS`, and only
  committed `HEAD` blobs selected by policy.
- Dirty tracked and untracked content is never read. Status records bounded
  relative-path metadata only. In-repository symlinks are never followed,
  submodules are never initialized, and LFS objects are never fetched.
- Repository text, including `README` and every `AGENTS.md`, is
  `untrusted_repository_content`. It may be classified but cannot alter
  permission, tool, approval, or test policy.
- The repository scanner uses fixed no-shell Git argument arrays, disabled
  credential prompts/hooks/network protocols, a shared timeout, and file/count
  budgets. Never replace it with general shell execution or working-tree file
  reads.
- Package scripts and Make targets may be parsed into typed metadata but must
  never be executed against a target repository in Phase 2.
- Phase 3 Runner jobs are a closed discriminated union. Do not add an arbitrary
  command, shell string, dynamic import, plugin hook, filesystem/repository
  tool, Docker socket, or subprocess-backed executor.
- A Phase 3 Permission Envelope is server-derived, immutable, canonical-hashed,
  and fixed to `repository_access=none`, `shell_access=false`, and
  `network_policy=control_plane_only`. Browser input and Deployment Packs may
  not submit or broaden it.
- Every Attempt mutation must validate authenticated Runner ID, active Attempt
  ID, high-entropy Lease ID, lease deadline, revocation, and state under a
  database lock. A stale identity returns `409` without mutation.
- Claim uses PostgreSQL row locking with `SKIP LOCKED`; retain both the partial
  active-attempt unique index and the independent-transaction concurrency test.
- Runner credentials are random, returned once, digest-only in PostgreSQL, and
  stored only in the ignored local bootstrap file or dedicated Runner volume.
  Never log request bodies or authorization headers.
- Keep RunnerJobEvent distinct from a future Agent Trace. Heartbeats update
  liveness without appending unbounded events.
- Never log full request bodies, credentials, tokens, connection strings, or
  other sensitive data. Preserve request IDs and stable public error codes.
- Frontend code must handle loading, empty, failure, and retry states and must
  preserve keyboard focus visibility and accessible names.
- Avoid nondeterministic LLM behavior for logic that code can determine.
- Do not add fake tools, fake traces, or unused SDKs to imply capabilities that
  do not exist.

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
- Approval race tests must use independent PostgreSQL transactions and prove
  exactly one final decision row.
- Repository security tests must preserve target `HEAD` and status and assert
  that synthetic secret, dirty, untracked, symlink-target, and lifecycle
  markers do not leak or execute.
- Playwright smoke tests use the real web, API, and PostgreSQL stack; do not
  replace that flow with API mocks. Phase 3 flows also require the real Runner
  container.
- Chaos tests must use their exact isolated Compose project and compare source
  status before/after. A graceful SIGTERM may finish active work and is not a
  valid simulation of abrupt Runner loss; use a bounded immediate stop for
  lease-expiry recovery evidence.
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
- The Phase 3 base platform and Runner have no external-repository access at
  all. Never mount CreativeDeploy, a customer repository, `~/Developer`, SSH,
  or Docker socket into Runner.
- Do not read real `.env` files, credentials, certificates, tokens, or secret
  stores in an external repository.
- Customer 0 mounts must be API-only, bind-mounted read-only, limited to the
  exact repository, configured through an uncommitted host environment
  variable, and inspected without a write probe against the real repository.
- A real Customer 0 plan must stop at `awaiting_plan_approval`; an agent must
  not approve or reject on the user's behalf.
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
