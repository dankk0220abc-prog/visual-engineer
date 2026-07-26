# ADR 0010: Opaque Repository Handles

- Status: Accepted
- Date: 2026-07-27

## Context

The Control Plane must authorize an exact repository without learning or
accepting a Runner host path. A browser-supplied path would cross the execution
boundary and could broaden mounts or escape an allowlist.

## Decision

Only Runner local configuration maps an opaque handle to an exact local
read-only path. Runner registers bounded display/revision/dirty metadata and
closed capabilities for that preconfigured handle. PostgreSQL, API responses,
and Web never contain the source path. User APIs can select an existing
Repository Handle but cannot create one from a path.

## Consequences

- Browser/API compromise cannot choose a host path.
- Runner configuration and mount provisioning remain an explicit local trust
  boundary.
- Moving a repository requires changing Runner-local configuration and
  re-verifying the handle; it is not a Control Plane metadata edit.
- Phase 4 registers only the synthetic fixture and never CreativeDeploy.
