# CreativeDeploy Read-Only Survey

CreativeDeploy is VisualEngineer Customer 0, Design Partner 0, and the first
real internal usage target for a future Deployment Pack. It is not an external
enterprise customer. This document records a bounded read-only survey, not
adoption, delivery, or outcome evidence.

## Survey status

`VERIFIED READ-ONLY SURVEY`

The Foundation main execution captured and independently compared the required
before/after baselines. This document records only read-only findings; no
CreativeDeploy install, build, test, formatter, generator, application, or Git
write command was run.

## Safety protocol

Before reading project files, save these values to distinct
`/tmp/visualengineer-creativedeploy-before-*` files:

```sh
git -C ~/Developer/CreativeDeploy rev-parse --show-toplevel
git -C ~/Developer/CreativeDeploy rev-parse --verify HEAD
git -C ~/Developer/CreativeDeploy branch --show-current
git -C ~/Developer/CreativeDeploy status --porcelain=v1 -uall
git -C ~/Developer/CreativeDeploy diff --stat
```

After the survey, capture the same values in
`/tmp/visualengineer-creativedeploy-after-*` and compare each pair. Preserve
pre-existing dirty state exactly. Do not read real `.env`, credential,
certificate, token, key, or secret files.

Do not install dependencies or run builds, tests, formatters, generators,
application commands, or Git write/cleanup commands in CreativeDeploy.

## Baseline evidence

| Item                          | Before                                                  | After                                      | Comparison |
| ----------------------------- | ------------------------------------------------------- | ------------------------------------------ | ---------- |
| Repository root               | `~/Developer/CreativeDeploy`                            | `~/Developer/CreativeDeploy`               | IDENTICAL  |
| Branch                        | `main`                                                  | `main`                                     | IDENTICAL  |
| HEAD                          | `bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`              | `bd2fcd23a004ccc99e45bafaef49fe444c1f70fb` | IDENTICAL  |
| `status --porcelain=v1 -uall` | 13 lines: 4 tracked modifications and 9 untracked paths | Same 13 lines                              | IDENTICAL  |
| `diff --stat`                 | 4 files, 59 insertions, 21 deletions                    | Same stat                                  | IDENTICAL  |

Only byte-for-byte equivalent baseline values may support the statement that
the survey produced no repository change. Existing uncommitted changes must be
described without cleaning, resetting, or attributing them to this task.

## Pre-existing worktree state

The exact dirty state existed before the survey and remained unchanged:

- tracked modifications:
  `apps/api/migrations/env.py`,
  `apps/api/src/creativedeploy_api/db/__init__.py`,
  `apps/api/tests/unit/test_database_metadata.py`, and
  `docs/progress/phase-1d-paint-project-vertical-slice-plan.md`;
- nine untracked paths containing a PaintProject ORM/migration candidate, its
  supporting models/tests, and the Phase 1D-1B progress document.

These candidate files are not part of HEAD. They must not be treated as
committed capability, cleaned, reset, or attributed to this survey. The tracked
README and AGENTS baseline still describe PaintProject business persistence as
not implemented at HEAD.

`git diff --check` produced no output during the read-only inspection. This is
an observation of the pre-existing tracked diff, not a validation or approval
of the uncommitted candidate.

## Confirmed by files

### Repository and package boundaries

- CreativeDeploy is a Git repository on `main` at
  `bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`.
- The root `package.json`, `pnpm-workspace.yaml`, and `pnpm-lock.yaml` define
  pnpm `11.14.0`, Node `>=24 <25`, and a workspace containing only `apps/web`.
- `apps/web` is a React `19.2.8` + TypeScript `5.9.3` application built with
  Vite `8.1.5`, Tailwind `4.3.3`, ESLint `9.39.5`, and Vitest `4.1.10`.
- `apps/api/pyproject.toml` defines Python `>=3.13,<3.14`, FastAPI `0.139.2`,
  SQLAlchemy `2.0.51`, psycopg `3.3.4`, Alembic `1.18.5`, uv, Ruff, mypy, and
  pytest.
- `compose.yaml` contains only a locally bound PostgreSQL
  `17.10-alpine3.24` service and a named data volume. There is no API or web
  application Dockerfile, no application Compose service, and no production
  deployment definition.
- No GitHub Actions workflow or other CI definition was present in the surveyed
  file list.

### Implemented committed application surface

- The API ASGI entry is
  `apps/api/src/creativedeploy_api/main.py`, which imports the app factory.
- Committed API routes expose only
  `GET /api/v1/health/live` and `GET /api/v1/health/ready`; readiness performs
  a real asynchronous PostgreSQL `SELECT 1`.
- The web entry is `apps/web/src/main.tsx`; `App.tsx` renders the
  `HealthDashboard`.
- Vite serves on `127.0.0.1:5173` and proxies `/api` to
  `127.0.0.1:8000`.
- The committed UI is a Foundation connectivity dashboard, not the PaintPilot
  product interface.
- Frontend tests use Vitest and React Testing Library. Backend tests use pytest,
  including real-PostgreSQL readiness coverage.
- No Playwright configuration or test exists in the surveyed file list.

### Commands and repository rules

- Root Make targets include `bootstrap`, `db-up`, `db-down`, API/web start,
  backend/frontend lint/type/test/build, migration inspection/checks, and
  aggregate `make check`.
- `AGENTS.md` requires uv for Python, Corepack pnpm for Node, a shared
  SQLAlchemy declarative base, explicit reversible migrations, no automatic
  startup migration, safe readiness errors, and frontend environment-variable
  denial through the Make boundary.
- Approved product/architecture documents live under `docs/product`,
  `docs/architecture`, and `docs/decisions`; active evidence/plans live under
  `docs/progress`.
- Design direction and page wireframes/specifications exist under
  `docs/design`. Golden-case assets and structured reference data live under
  `data/golden-cases/paintpilot-v0.1`.
- No root `PLANS.md` was present; phase plans are stored under `docs/progress`.

### Environment variable names

Only `.env.example` and public configuration references were inspected. The
documented names are `APP_ENV`, `APP_NAME`, `APP_VERSION`, `DATABASE_URL`,
`DATABASE_HEALTH_TIMEOUT_SECONDS`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_DB`, and `POSTGRES_PORT`. Values in `.env.example` are explicitly
local examples.

## Reasoned integration hypotheses

These are integration proposals, not commands run by this survey:

- The safest initial read set is Git metadata plus `AGENTS.md`, README,
  manifests/lockfiles, Makefile, Compose, approved product/architecture/decision
  documents, `docs/design`, application entry points, and tests. Real `.env` and
  binary Golden Case assets should remain outside automatic context by default.
- A future experiment should pin the exact source commit, require the original
  checkout to have a captured status, and create a separate named worktree
  under a task-owned temporary root. It must never write into the user's
  existing checkout or include its pre-existing uncommitted candidate.
- Candidate startup commands are `make db-up`, `make api`, and `make web`;
  candidate verification commands are `make check` plus the documented
  migration inspection checks. They must first be exercised in a disposable
  fixture or isolated worktree and must not be run in this read-only survey.
- The Makefile is the preferred command integration point because it preserves
  the frontend environment denylist and project-specific uv/pnpm invocation.
- `apps/api/migrations/versions`, lockfiles, design specifications, Golden Case
  data, and approved baselines need distinct generated/protected path policy.
  Migration candidates require manual review rather than automatic acceptance.
- Future rollback should record the source commit, worktree branch, pre-change
  diff, migration state, and test artifacts. A Git checkpoint alone is
  insufficient for database effects.

## Questions requiring later validation

- Does `make bootstrap` plus locked installs remain deterministic in a clean
  isolated worktree on the supported Node 24/Python 3.13 toolchain?
- Which exact browser failure/recovery validation is manual versus automated,
  given that no Playwright suite is present?
- Do any quality or migration checks write caches, generated revisions,
  snapshots, or tracked files under their current flags?
- What is the ownership/protection policy for design specs and Golden Case data
  when automated changes begin?
- What exact allowed paths, commands, network access, and approval duration
  should gate a Level 1 isolated-worktree experiment?
- How should the pre-existing PaintProject candidate be excluded from any
  experiment based on committed HEAD?

## Sensitive-data statement

The survey inspected only allowed Git metadata, tracked/untracked path names,
public project files, `.env.example`, and code/configuration references. It did
not read a real `.env`, credential, token, certificate, private key, or secret
store. Example local database values are not production credentials.

## Final survey conclusion

The independently captured before/after repository root, branch, HEAD, full
porcelain status, and diff stat were identical. CreativeDeploy's 4 tracked
modifications and 9 untracked paths pre-existed and remained intact. Therefore,
the read-only survey produced no CreativeDeploy repository change.

## Post-survey final observation

A separate final snapshot near the end of the VisualEngineer task found the
same repository root, `main` branch, HEAD, and 13 porcelain status paths. The
tracked diff had changed after the survey window from 59 insertions / 21
deletions to 60 insertions / 21 deletions, within the same four modified files.
An external CreativeDeploy PostgreSQL container had also become active on port 5432.

Every command issued by this task against CreativeDeploy remained on the
documented read-only allowlist; no install, Compose, build, test, generator, or
write command was executed there. The five-item survey before/after proof
therefore remains valid for the bounded investigation, but the repository's
initial and final whole-task diff are not claimed to be identical because of
the later concurrent activity.

## Foundation closure follow-up

A later Foundation closure audit began with the same `main` branch, HEAD, four
tracked paths, and nine untracked paths; its start diff stat was 60
insertions/21 deletions. The final pre-commit snapshot again retained the same
branch, HEAD, and 13 paths, while concurrent external work moved the diff stat
to 70 insertions/21 deletions.

The closure task used only allowed read-only Git metadata commands against
CreativeDeploy. It did not read real environment or credential files and did
not run project commands. There is no evidence that VisualEngineer closure
wrote the external repository, and the concurrent drift is not attributed to
this task.
