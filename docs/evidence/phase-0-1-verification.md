# Phase 0 + 1 Verification Evidence

- Status: VERIFIED FOR FOUNDATION CHECKPOINT
- Evidence date: 2026-07-26
- Remote GitHub Actions: NOT RUN; no remote exists and no remote action was
  authorized.
- Checkpoint: the root commit containing this evidence is the local Foundation
  checkpoint; resolve its hash with `git rev-parse HEAD`.

Every `VERIFIED` result below ran against this worktree and returned the
recorded exit code. Runtime files and long logs remain untracked.

## Execution environment

| Item                | Verified value                                |
| ------------------- | --------------------------------------------- |
| OS / architecture   | macOS 26.5.2 / arm64                          |
| Git                 | 2.50.1                                        |
| Node / pnpm         | 24.18.0 / 11.14.0                             |
| System Python       | 3.9.6; not used as the project runtime        |
| Project Python / uv | uv-managed CPython 3.12.13 / uv 0.11.30       |
| Docker / Compose    | client and daemon 29.6.2 / Compose 5.3.1      |
| Make                | GNU Make 3.81                                 |
| Playwright          | 1.62.0 / Chromium 151.0.7922.34               |
| actionlint          | unavailable; no system installation attempted |
| Git checkpoint      | Identity resolved locally; acceptance pending |

## Closure audit delta

- The previous closure attempt stopped without changes because VisualEngineer
  still lacked repository-level Git identity.
- This task validated the complete, non-placeholder identity already configured
  locally in CreativeDeploy and copied only those two values into
  VisualEngineer's repository-local configuration. Global configuration and
  CreativeDeploy were not modified.
- Independent source inspection confirmed that the SQLAlchemy model, initial
  migration, Pydantic schemas, API, OpenAPI, generated TypeScript, form, client,
  and existing tests use `objective`, `repository_kind`,
  `repository_display_name`, and `repository_locator`. No legacy
  `description`/`request_content` Task field exists.
- Source tracing confirmed that `repository_locator` is passed only through
  validation, SQLAlchemy persistence, API serialization, and UI display; no
  Foundation filesystem, Git, subprocess, clone, or network operation consumes
  it.
- Added semantic OpenAPI assertions, fuller blank/length/NUL/enum coverage,
  frontend NUL validation, UTC assertions, and a two-session barrier test that
  forces the PostgreSQL idempotency uniqueness race.
- Closure regression passes 40 backend tests at 95.91% coverage and 12 frontend
  tests at 82.18% statement coverage.
- Formal product documents now define enterprise frontend governed delivery,
  three bounded V1 packages, VisualEngineer Core versus customer Deployment
  Pack, CreativeDeploy as internal Customer 0/Design Partner 0, and
  evidence-only outcome metrics.

## Closure staged-content audit

- 108 staged files, all expected Foundation source, tests, generated contracts,
  locks, migration, CI, governance, and product/architecture/security/evidence
  documents.
- All staged files are text; no staged symlink, binary, file larger than 1 MiB,
  CreativeDeploy path, dependency directory, database data, log, coverage,
  Playwright artifact, trace, cache, or temporary file exists.
- `.gitignore` and `.dockerignore` cover `.env`, `.env.local`, `.venv`,
  `node_modules`, `.next`, coverage, Playwright reports, `test-results`, traces,
  logs, Python caches, TypeScript build metadata, and local PostgreSQL data.
- Staged searches found no absolute macOS user-home path, credential
  assignment, private key, cloud credential, API key, GitHub token, or Figma
  token. `.env.example` contains only visibly local example values.
- The first `git diff --cached --check` found seven extra blank lines at EOF.
  They were removed, re-staged, and the check then returned 0.
- The complete staged name/status/stat and substantive diff were inspected.
  No unexpected file was retained.

## Closure pre-commit command matrix

| Command                     | Exit | Result                                                                 |
| --------------------------- | ---: | ---------------------------------------------------------------------- |
| `make format`               |    0 | Ruff and Prettier produced no remaining change.                        |
| `make format-check`         |    0 | Python, root, and web formatting passed.                               |
| `make lint`                 |    0 | Ruff and ESLint passed with zero ESLint warnings.                      |
| `make typecheck`            |    0 | Strict mypy checked 24 files; TypeScript strict check passed.          |
| `make test`                 |    0 | 40 backend and 12 frontend tests passed.                               |
| `make build`                |    0 | Next.js production build created `/` and `/tasks/[taskId]`.            |
| `make contracts-check`      |    0 | OpenAPI and TypeScript regenerated byte-identically.                   |
| `make migration-check`      |    0 | PostgreSQL upgrade/downgrade/upgrade reached `20260726_0001`.          |
| `make security-check`       |    0 | No high-confidence credential pattern found.                           |
| `make e2e`                  |    0 | Two real-stack Playwright viewports passed.                            |
| `make verify`               |    0 | Aggregate contract, quality, test, build, Docker, migration, E2E gate. |
| `git diff --cached --check` |    0 | Final staged whitespace gate passed.                                   |

The backend run emitted one non-failing upstream Starlette deprecation warning
for the TestClient transition from `httpx` to `httpx2`. Playwright also noted
that `NO_COLOR` was ignored because `FORCE_COLOR` was set; this did not affect
browser assertions.

## Closure CreativeDeploy safety

Closure started with CreativeDeploy on `main` at
`bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`, with the same four tracked and nine
untracked paths documented by the earlier survey and a diff stat of 60
insertions/21 deletions. The final pre-commit read-only snapshot retained the
same branch, HEAD, and 13 paths, while concurrent external work changed the
diff stat to 70 insertions/21 deletions. Every closure command against
CreativeDeploy was read-only; there is no evidence of a write from this task,
and the external drift is not attributed to it.

## Historical Foundation construction ledger

| Area                | Command                                                     | Exit | Result           | Important evidence                                                                                         |
| ------------------- | ----------------------------------------------------------- | ---: | ---------------- | ---------------------------------------------------------------------------------------------------------- |
| CreativeDeploy      | five before/after `cmp` comparisons                         |    0 | VERIFIED         | Root, `main`, HEAD `bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`, 13-line status, and diff stat identical.    |
| Python runtime      | `uv python install 3.12`                                    |    0 | VERIFIED         | Installed project-managed CPython 3.12.13 without changing system Python.                                  |
| Python lock/install | `uv lock && uv sync --frozen`                               |    0 | VERIFIED         | `uv.lock` resolves and installs 41 development/runtime packages.                                           |
| JS lock/install     | `pnpm install` and final frozen install path                |    0 | VERIFIED         | `pnpm-lock.yaml` is current; only `esbuild`, `sharp`, and `unrs-resolver` builds are explicitly allowed.   |
| Python format       | `uv run ruff format --check apps/api scripts`               |    0 | VERIFIED         | 26 files already formatted.                                                                                |
| Python lint         | `uv run ruff check apps/api scripts`                        |    0 | VERIFIED         | All checks passed.                                                                                         |
| Python types        | `uv run mypy apps/api/src apps/api/tests`                   |    0 | VERIFIED         | Strict mypy: no issues in 23 source files.                                                                 |
| Backend tests       | `./scripts/run-backend-tests.sh`                            |    0 | VERIFIED         | Real PostgreSQL; 27 passed, 0 failed, 0 skipped.                                                           |
| Backend coverage    | pytest-cov within the backend test command                  |    0 | VERIFIED         | 94.03% total coverage; threshold 80%.                                                                      |
| Migration           | `make migration-check`                                      |    0 | VERIFIED         | Empty DB upgrade, downgrade to base, and re-upgrade to `20260726_0001`.                                    |
| Contract generation | `make contracts`                                            |    0 | VERIFIED         | Exported formatted `openapi.json` and generated `schema.d.ts`.                                             |
| Contract drift      | `make contracts-check`                                      |    0 | VERIFIED         | Regeneration plus byte comparison produced no drift.                                                       |
| Frontend format     | `pnpm format:check`                                         |    0 | VERIFIED         | Root and web Prettier checks passed.                                                                       |
| Frontend lint       | `pnpm lint`                                                 |    0 | VERIFIED         | ESLint passed with zero warnings.                                                                          |
| Frontend types      | `pnpm typecheck`                                            |    0 | VERIFIED         | TypeScript strict check passed.                                                                            |
| Frontend tests      | `pnpm test`                                                 |    0 | VERIFIED         | 3 Vitest files / 11 tests passed; none failed or skipped.                                                  |
| Frontend coverage   | Vitest coverage within `pnpm test`                          |    0 | VERIFIED         | Statements 81.6%, branches 68.9%, functions 86.04%, lines 82.91%; statement threshold 70%.                 |
| Frontend build      | `make build`                                                |    0 | VERIFIED         | Next.js 16.2.12 production build compiled `/` and `/tasks/[taskId]`.                                       |
| Compose syntax      | `make docker-config`                                        |    0 | VERIFIED         | Default and test-profile Compose configurations parsed.                                                    |
| Docker build        | `docker compose build`                                      |    0 | VERIFIED         | API and web multi-stage images built successfully.                                                         |
| Runtime start       | `docker compose up -d --wait db api web`                    |    0 | VERIFIED         | PostgreSQL, API, and web reported healthy.                                                                 |
| Liveness            | `curl http://127.0.0.1:8000/health/live`                    |    0 | VERIFIED         | HTTP 200, `{"status":"ok"}`, supplied request ID propagated.                                               |
| Readiness           | `curl http://127.0.0.1:8000/health/ready`                   |    0 | VERIFIED         | HTTP 200, `{"status":"ready"}` against PostgreSQL.                                                         |
| Web                 | `curl http://127.0.0.1:3000/`                               |    0 | VERIFIED         | HTTP 200; title `VisualEngineer · Foundation`.                                                             |
| Runtime CRUD        | create, replay, conflict, get, and list curl flow           |    0 | VERIFIED         | 201 create; 200 same-ID replay with header; 409 conflict; 200 detail/list with persisted Task.             |
| Playwright          | `make e2e`                                                  |    0 | VERIFIED         | 2/2 real-stack tests passed: desktop 1440×1000 and narrow 390×844.                                         |
| Persistence         | detail reload in both Playwright projects                   |    0 | VERIFIED         | Created Task remained visible with `draft` status after browser reload.                                    |
| Accessibility       | axe WCAG 2 A/AA scan in both Playwright projects            |    0 | VERIFIED         | Zero reported violations; no horizontal overflow.                                                          |
| Teardown            | project-scoped Compose cleanup                              |    0 | VERIFIED         | No VisualEngineer containers/listeners remain; external CreativeDeploy PostgreSQL on 5432 was untouched.   |
| Workflow            | PyYAML parse and referenced Make/script checks              |    0 | VERIFIED LOCALLY | Four jobs parsed: backend, frontend, contract, e2e. Remote CI remains NOT RUN.                             |
| Security            | `make security-check`                                       |    0 | VERIFIED         | No high-confidence private-key, OpenAI, GitHub, or AWS credential patterns found.                          |
| Whitespace          | `git diff --check`                                          |    0 | VERIFIED         | No whitespace errors.                                                                                      |
| Aggregate           | `make verify`                                               |    0 | VERIFIED         | Contract, format, lint, types, tests, build, Compose, migration, E2E, security, and diff gates passed.     |
| Git scope           | `git status --short` and full file list inspection          |    0 | VERIFIED         | Only Foundation source/docs/generated locks/migration are present; ignored runtime artifacts are excluded. |
| Git identity        | `git config --get user.name` and `user.email`               |    1 | BLOCKED          | Neither value is configured; no identity was invented.                                                     |
| Git commit          | `git commit -m "feat: establish VisualEngineer foundation"` |    — | NOT RUN          | Prohibited until a legitimate identity exists.                                                             |
| Post-commit status  | `git status --short`                                        |    — | NOT AVAILABLE    | Worktree cannot be clean before the required initial commit.                                               |

## Behavioral evidence

- Liveness is database-independent; readiness executes `SELECT 1`.
- Task input rejects blank, over-limit, invalid enum, and NUL values.
- Valid creation returns 201 with internal idempotency fields excluded.
- Normalized same-body replay returns the same Task with
  `Idempotent-Replay: true`; a different body for the same key returns stable 409.
- Database uniqueness plus `IntegrityError` recovery handles competing
  idempotency inserts without a query-only race.
- Lists are newest-first with bounded limit/offset; missing tasks return stable 404.
- Errors and responses include request IDs without exposing connection details
  or request bodies.
- Both browser viewports create, list, open, and reload a real PostgreSQL-backed
  Task.

## Failures and fixes

| Failure                                              | Root cause                                                                                                                                           | Fix                                                                                                       | Regression                                                                            |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Initial `pnpm install` failed                        | npm registry reset a metadata request                                                                                                                | Retried the locked install without changing versions                                                      | Final installs and Docker frozen install passed.                                      |
| pnpm rejected native build scripts                   | pnpm 11 defaults to strict review of dependency scripts                                                                                              | Added an exact `allowBuilds` map for `esbuild`, `sharp`, and `unrs-resolver`                              | Local and container installs passed.                                                  |
| Initial Python quality checks failed                 | New files needed formatting; dependency annotations and test return types were incomplete                                                            | Formatted and replaced default dependency calls with typed `Annotated` dependencies; corrected types      | Ruff and strict mypy passed.                                                          |
| Initial frontend lint failed                         | React 19 rules caught synchronous effect state changes and render-local component creation; ESLint 10 was incompatible with the current React plugin | Restructured async initialization, moved the error component boundary, and pinned supported ESLint 9.39.5 | Frontend format/lint/typecheck/tests/build passed.                                    |
| Root format failed to load Tailwind plugin           | Root Prettier traversed the web workspace without the plugin at the root                                                                             | Added the same pinned plugin to root dev dependencies                                                     | `make format` and `make format-check` passed.                                         |
| Contract generation failed the later format gate     | Generator output was deterministic but not formatted as part of generation                                                                           | Made contract formatting part of `generate` and drift checking                                            | Generate-then-format-check and byte drift checks passed.                              |
| First E2E Compose start returned `No such container` | Transient Docker daemon container-state race; no code or port conflict found                                                                         | Verified cleanup/ports and retried the exact project-scoped flow                                          | Subsequent starts were healthy.                                                       |
| First Playwright assertions failed                   | A global `draft` locator matched both create confirmation and task card before navigation settled                                                    | Waited for the detail URL and scoped assertions to the detail article                                     | 2/2 viewport tests and aggregate `make verify` passed.                                |
| A later final E2E run found port 5432 occupied       | An external CreativeDeploy PostgreSQL container became active after the initial audit                                                                | Left that external container untouched; parameterized published ports and assigned E2E-only alternatives  | Final `make verify` passed without altering it.                                       |
| CI parse with system Python failed                   | macOS system Python did not include PyYAML                                                                                                           | Used the locked uv environment, which already includes PyYAML                                             | Workflow parsed into all four expected jobs.                                          |
| Initial local checkpoint unavailable                 | Git author name and email were not configured during the construction run                                                                            | No configuration was fabricated or changed                                                                | Resolved in the closure audit through explicitly authorized local identity discovery. |

## Test summary

| Suite           | Passed | Failed | Skipped | Coverage                  |
| --------------- | -----: | -----: | ------: | ------------------------- |
| Backend pytest  |     40 |      0 |       0 | 95.91% total              |
| Frontend Vitest |     12 |      0 |       0 | 82.18% statements         |
| Playwright      |      2 |      0 |       0 | 2 axe scans, 0 violations |

One upstream deprecation warning remains: FastAPI's current `TestClient` path
warns that Starlette will move from `httpx` to `httpx2`. It does not fail the
suite and should be revisited during dependency maintenance.

## Current decision

The independent contract audit, product alignment, staged-content audit, and
complete pre-commit matrix pass. The local root commit is authorized. The
post-commit matrix is intentionally recorded in the acceptance handoff because
it cannot be embedded self-referentially in the same root commit. No remote CI
claim is made.
