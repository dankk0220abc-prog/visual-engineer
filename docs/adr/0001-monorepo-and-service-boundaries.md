# ADR 0001: Lightweight Monorepo and Service Boundaries

- Status: Accepted for Foundation

## Context

The first vertical slice needs a browser console, an HTTP API, PostgreSQL,
generated contract artifacts, shared commands, tests, and documentation.
Splitting these into independent repositories would add versioning and delivery
coordination before the product boundary is stable. A heavy monorepo
orchestrator would add configuration without a demonstrated need.

## Decision

Use one lightweight repository with pnpm workspaces and root Make targets:

- `apps/web` owns the Next.js browser application;
- `apps/api` owns FastAPI behavior and database access;
- `packages/api-contract` contains generated API artifacts;
- PostgreSQL is the only application database;
- docs, evals, infrastructure, and scripts remain explicit top-level concerns;
- no Turborepo, Nx, queue, gateway, or microservice split is introduced.

Within the API, separate routes, typed configuration, persistence models,
schemas, repository access, and real business logic, while avoiding empty
layers.

## Consequences

Local and CI changes can be reviewed atomically and contract drift can be
checked in one worktree. Python and Node tooling still require separate package
managers and caches. Make commands must fail fast and keep local/CI behavior
aligned. If scale later requires independent deployment, boundaries are clear
enough to extract with an ADR.

## Alternatives considered

- Separate web and API repositories: rejected because cross-repository contract
  coordination is premature.
- Turborepo or Nx: rejected because two applications and one generated package
  do not justify another orchestration layer.
- Single full-stack runtime: rejected because Python Agent/backend concerns and
  Next.js UI concerns have distinct ecosystems and deployment boundaries.
- Microservices and a message broker: rejected because there is no current
  asynchronous workload that needs them.
