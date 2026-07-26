# Local Development Runbook

## Purpose

Run the local Foundation and Phase 2 web/API/PostgreSQL stack on one machine.
This is not a public or production deployment runbook. The base Compose file
does not mount a target repository; use a reviewed override explicitly.

## Start

```sh
cd ~/Developer/VisualEngineer
cp .env.example .env
make bootstrap
make up
```

`make up` builds the non-root API and web images, waits for PostgreSQL, applies
the local Alembic migration before the API starts, and waits for all health
checks. In a future production environment, migrations must run as one
dedicated release step rather than inside competing application processes.

Open:

- `http://localhost:3000` for the console;
- `http://localhost:8000/docs` for local API documentation;
- `http://localhost:8000/health/live` for process liveness;
- `http://localhost:8000/health/ready` for database readiness.

## Verify

```sh
make verify
```

This starts and removes project-scoped test/E2E services. It does not remove
unrelated containers or volumes. Reports, traces, screenshots, coverage, local
dependencies, and `.env` files are ignored by Git.

The aggregate gate includes format, lint, typecheck, backend and frontend
tests, contract drift, build, Compose configuration, migration round trip,
desktop/narrow real-stack Playwright, adversarial repository security, eval
dataset validation, and `git diff --check`.

Narrow Phase 2 gates are:

```sh
make security-check
make eval
make migration-check
make e2e
```

For the internal CreativeDeploy Customer 0 case, first complete all synthetic
gates and follow
[`customer0-readonly-investigation.md`](customer0-readonly-investigation.md).
Do not add the Customer 0 host path to `.env` or any committed file.

## Diagnose

```sh
docker compose ps
make logs
```

If ports 3000, 8000, 5432, or 55433 are occupied, do not kill the owning
process. Set `WEB_PUBLISHED_PORT`, `API_PUBLISHED_PORT`,
`POSTGRES_PUBLISHED_PORT`, or `TEST_POSTGRES_PUBLISHED_PORT` to free local
ports. Also update `NEXT_PUBLIC_API_BASE_URL` and `WEB_ORIGIN` when web/API
published ports change, then rebuild.

## Stop

```sh
make down
```

This stops and removes this project's containers and network but preserves the
development PostgreSQL volume. Use a separate explicitly reviewed command if
local database deletion is ever intended.
