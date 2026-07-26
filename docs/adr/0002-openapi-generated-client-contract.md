# ADR 0002: OpenAPI-Generated Client Contract

- Status: Accepted for Foundation

## Context

Manually duplicating Pydantic API schemas in TypeScript creates drift,
especially around enum values, optionality, bounds, and error responses. The
Foundation needs a reproducible contract that can be reviewed and checked in
CI without introducing a large client generator.

## Decision

FastAPI's OpenAPI export is the authoritative HTTP schema. A deterministic
project command exports it to `packages/api-contract/openapi.json`, then uses
`openapi-typescript` or an equivalent lightweight generator for TypeScript
types consumed by the web API client.

Contract verification regenerates both artifacts and fails when Git reports a
diff. Core API types are not hand-maintained in parallel.

## Consequences

Backend schema changes visibly propagate to frontend types, and CI can detect
stale artifacts. Generated output becomes reviewable repository content but
must never be hand-edited. Semantic runtime behavior such as headers,
idempotent replay, and stable errors still needs explicit tests and client
logic; type generation does not prove behavior.

## Alternatives considered

- Handwritten TypeScript interfaces: rejected because drift is likely.
- TypeScript-first schemas shared with Python: rejected because FastAPI/Pydantic
  already defines runtime validation and would need another translation layer.
- A full generated client SDK: deferred until endpoint count and operational
  needs justify the additional generated surface.
- Runtime-only OpenAPI fetch: rejected because builds and reviews should be
  deterministic and not depend on a running API.
