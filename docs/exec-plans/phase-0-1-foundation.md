# Phase 0 + 1 Foundation Sprint ExecPlan

- Status: VERIFIED FOR FOUNDATION CHECKPOINT
- Working repository: `~/Developer/VisualEngineer`
- Default branch: `main`
- Checkpoint: the root commit containing this plan, with message
  `feat: establish VisualEngineer foundation`

## Goal

Deliver the smallest safe, reviewable vertical slice in which a local user can
create and retrieve a validated Task through a responsive browser, with the
same data durably stored in PostgreSQL, while establishing explicit contracts
for future human-approved Agent execution.

## Scope

- Read-only Mac prerequisite audit.
- Read-only CreativeDeploy technical survey with before/after baseline.
- Lightweight web/API/contract monorepo.
- Task API, idempotency, PostgreSQL schema, and initial migration.
- Browser creation, list, detail, health, failure, and accessibility states.
- OpenAPI-derived frontend types.
- Unit, integration, migration, coverage, and real-stack Playwright smoke tests.
- Local Docker Compose and non-deploying GitHub Actions definitions.
- Root governance plus product, architecture, security, ADR, eval, evidence, and
  status documentation.
- One local commit only after every mandatory gate succeeds.

## Non-goals

- LLM calls, Agent runtime, generic tool executor, fake traces or eval scores.
- Repository access derived from a task locator.
- Target-repository write, isolated worktree execution, GitHub PR, merge,
  deployment, or production migration.
- Authentication, public exposure, Redis, queues, orchestration platforms,
  Kubernetes, or microservice gateways.
- Modification, build, install, test, formatting, generation, or cleanup in
  CreativeDeploy.

## Constraints and stop conditions

- Do not use `sudo`, Homebrew, global upgrades, or global Git configuration.
- Do not read real environment, token, certificate, key, or credential files.
- Preserve any existing worktree changes and Git history.
- Stop the relevant action if CreativeDeploy baseline changes, a mandatory
  check cannot be safely repaired, a real secret is at risk, a target write is
  required, or remote/publish authority is needed.
- Git identity must be complete and non-placeholder. If VisualEngineer lacks
  either value, the closure task may copy the already-configured
  repository-level CreativeDeploy identity only after validating both fields,
  and may write only VisualEngineer's local Git configuration.

## Current progress

- [x] 2026-07-26: Recorded supplied read-only environment observations and
      missing Git identity.
- [x] 2026-07-26: Established product, architecture, permissions, security,
      ADR, eval, operating, and evidence document scaffolds.
- [x] 2026-07-26: Captured CreativeDeploy before baseline.
- [x] 2026-07-26: Completed allowed CreativeDeploy file survey without running
      project commands or reading real secret configuration.
- [x] 2026-07-26: Captured and independently compared CreativeDeploy after
      baseline; root, branch, HEAD, 13-line status, and diff stat are identical.
- [x] 2026-07-26: Implemented and inspected root manifests and workspace
      commands.
- [x] 2026-07-26: Implemented Task migration, API behavior, idempotency, and
      PostgreSQL integration.
- [x] 2026-07-26: Implemented the responsive web console and generated contract
      client.
- [x] 2026-07-26: Implemented and ran unit, integration, migration, and
      Playwright tests.
- [x] 2026-07-26: Implemented and locally validated Compose and the CI
      definition.
- [x] 2026-07-26: Installed/synced locked dependencies without global
      modification.
- [x] 2026-07-26: Ran every locally executable mandatory verification and
      recorded results.
- [x] 2026-07-26: Scanned for secrets and inspected final diff/file scope.
- [x] 2026-07-26: Previous closure attempt stopped without changes because
      VisualEngineer still lacked repository-level Git identity.
- [x] 2026-07-26: Validated CreativeDeploy's complete non-placeholder local
      identity and copied it only into VisualEngineer's local Git configuration.
- [x] 2026-07-26: Independently traced the Task contract through SQLAlchemy,
      Alembic, Pydantic, routes, OpenAPI, generated TypeScript, web, and tests.
- [x] 2026-07-26: Confirmed the required `objective` and repository metadata
      fields already exist and that locator values never authorize access.
- [x] 2026-07-26: Added OpenAPI semantic assertions, broader boundary tests,
      frontend NUL coverage, and a forced real-PostgreSQL idempotency race test.
- [x] 2026-07-26: Aligned formal product documents to enterprise frontend
      governed delivery, three V1 packages, Core/Deployment Pack, Customer 0,
      and evidence-based outcome metrics.
- [x] Complete staged-content and sensitive-information audit.
- [x] Run the complete pre-commit command matrix.
- [x] Include this plan in the local Foundation root checkpoint after every
      pre-commit gate passes.
- [ ] Run the complete post-commit command matrix; record it in the final
      acceptance handoff because the result cannot be embedded in this same
      root commit.
- [ ] Confirm final worktree is clean after checkpoint in the acceptance
      handoff.

## Decisions

| Decision                                   | Rationale                                                                        |
| ------------------------------------------ | -------------------------------------------------------------------------------- |
| Lightweight monorepo, no Nx/Turborepo      | Two applications and one generated contract do not justify more orchestration.   |
| FastAPI OpenAPI is authoritative           | Prevents Python/TypeScript contract duplication.                                 |
| PostgreSQL only for persistence evidence   | SQLite would not verify production-relevant constraints or concurrency.          |
| Only Task in the initial migration         | Avoids pretending the future Agent lifecycle exists.                             |
| External repositories read-only by default | A locator or repository instruction cannot grant authority.                      |
| Compose is local development only          | Build/start evidence is not production deployment.                               |
| No checkpoint with missing identity        | Author identity must not be fabricated or changed globally.                      |
| Reuse validated repository-local identity  | Avoids guessing while keeping global and source-repository configuration intact. |

See ADRs 0001-0003 for durable reasoning.

## Risks

| Risk                                                      | Impact                              | Mitigation / next action                                                                                      |
| --------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Node 24 may not be supported by selected Next.js packages | Install/build failure               | Pin a compatible Node version actually available or uv/tool-managed without global upgrade; record deviation. |
| System Python is 3.9.6                                    | API install/type syntax failure     | Use uv-managed Python 3.12 and record exact interpreter.                                                      |
| Docker daemon or images unavailable                       | PostgreSQL/E2E blocked              | Run config first, inspect exact daemon/network error, avoid global changes.                                   |
| Concurrent idempotency race                               | Duplicate tasks or incorrect replay | Unique database constraint plus transactional conflict handling and integration test.                         |
| Generated contract drift                                  | Runtime/client mismatch             | Deterministic regeneration and clean-diff gate.                                                               |
| CreativeDeploy pre-existing changes                       | Incorrect safety claim              | Capture exact before/after baselines and preserve existing state.                                             |
| Git identity absent                                       | No valid checkpoint                 | Copy only a complete validated CreativeDeploy local identity when explicitly authorized; otherwise stop.      |
| Docs outrun implementation                                | False capability claims             | Status vocabulary and evidence file; update only from inspected code/results.                                 |

## Discoveries

- 2026-07-26: The VisualEngineer Git repository exists on `main` with no
  checkpoint at the start of the documentation work.
- 2026-07-26: Required local tools are present except `actionlint`; system
  Python is below the project target and Git author identity is absent.
- 2026-07-26: CreativeDeploy is on `main` at
  `bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`. Its 4 tracked modifications and
  9 untracked paths pre-existed the survey and remained identical.
- 2026-07-26: Committed CreativeDeploy supports a React/Vite health dashboard,
  FastAPI liveness/readiness, and local PostgreSQL. PaintProject candidate
  models/migration are uncommitted and are not treated as HEAD capability.
- 2026-07-26: uv safely installed project-managed CPython 3.12.13; the system
  Python remained unchanged.
- 2026-07-26: pnpm 11 requires explicit dependency build review. Only
  `esbuild`, `sharp`, and `unrs-resolver` are allowed to run native install
  scripts.
- 2026-07-26: Contract output must be formatted as part of generation, not as a
  later unrelated format step, or drift and format gates disagree.
- 2026-07-26: The real PostgreSQL backend suite passed 27 tests at 94.03%
  coverage; the frontend passed 11 tests at 81.6% statement coverage.
- 2026-07-26: Both real-stack Playwright viewports passed creation, detail,
  reload persistence, axe, and overflow checks.
- 2026-07-26: The first E2E Compose start encountered a transient missing
  container; a later test failed because a global locator was ambiguous.
  Project-scoped cleanup, retry, and article-scoped assertions resolved both
  without weakening behavior checks.
- 2026-07-26: The original construction run's `make verify` passed; at that
  time Git author identity remained its sole completion blocker.
- 2026-07-26: An external CreativeDeploy PostgreSQL container began using 5432
  after the initial audit. It was left untouched; published ports were
  parameterized and E2E now uses 15432/18000/13000.
- 2026-07-26: A final CreativeDeploy snapshot retained the same root, `main`,
  HEAD, and 13 status paths but its diff grew from 59 to 60 insertions after the
  verified survey window. All task commands against it were read-only, so the
  survey conclusion is preserved while the later concurrent drift is recorded.
- 2026-07-26: Closure audit found the complete non-placeholder CreativeDeploy
  repository-level identity and copied it only to VisualEngineer's local
  configuration; no global configuration changed.
- 2026-07-26: The required Task contract was already implemented consistently.
  The previous summary's `description`/`request_content` wording was inaccurate,
  not the current code.
- 2026-07-26: Existing code handled the PostgreSQL unique-key race, but no test
  forced the collision. A two-session barrier test now exercises the recovery
  against real PostgreSQL.
- 2026-07-26: During closure, CreativeDeploy retained `main`, the same HEAD, and
  the same 13 status paths while concurrent external work changed its diff stat
  from 60/21 to 70/21. All closure commands against it were read-only.

## Verification

The command ledger is
[`../evidence/phase-0-1-verification.md`](../evidence/phase-0-1-verification.md).
The closure audit independently covers CreativeDeploy safety, locked project
state, quality, 40 PostgreSQL-backed tests, 12 frontend tests, contract drift,
migration round trip, image build, runtime CRUD, two browser
persistence/accessibility flows, security scan, staged diff, and `make verify`.
Remote CI has not run.

## Rollback

- Stop only this project's Compose services with `make down` or the exact
  project-scoped Compose command; never delete unrelated containers or volumes.
- Before a commit exists, revert only explicitly identified Foundation files
  after preserving unrelated user work. Do not use `git reset --hard`,
  `git clean`, or broad destructive paths.
- Database test data may be removed only through the project-scoped test
  database/volume process after confirming the exact target.
- CreativeDeploy has no rollback path in this plan because it must receive no
  writes. Any observed difference is a stop condition requiring investigation.

## Completion conditions

All of the following must be true:

1. Environment and CreativeDeploy evidence is complete and the external
   before/after baseline is identical.
2. The API, web, database, migration, generated contract, Compose, and CI files
   exist and match documented boundaries.
3. Required backend, frontend, migration, contract, Docker, accessibility, and
   real-stack Playwright checks have exit code 0.
4. `make verify`, secret scan, `git diff --check`, and final diff review pass.
5. No credential, runtime artifact, database data, or external-repository change
   is included.
6. A legitimate Git identity exists without Agent fabrication.
7. The local commit is created and post-commit `git status --short` is empty.

## Outcome and follow-ups

Foundation implementation, positioning alignment, staged audit, and the full
pre-commit matrix pass. The root commit containing this plan is the Foundation
checkpoint. Post-commit reproducibility and clean-status evidence are recorded
in the final acceptance handoff.
