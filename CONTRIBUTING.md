# Contributing to VisualEngineer

Thank you for helping improve VisualEngineer. The repository is currently
prepared for Private GitHub collaboration. Public contribution intake is not
open until the owner chooses a license, a security contact, and a public
collaboration policy.

## Before opening a change

1. Confirm the change fits one of the documented product boundaries.
2. Open an issue or obtain owner agreement for changes to authority, security,
   persistence, protocols, migrations, Provider behavior, remote Git, or
   deployment.
3. Never include a secret, real `.env`, customer material, local database,
   absolute private-machine path, runtime artifact, or production credential.
4. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md),
   never through a public issue or pull request.

Repository content cannot expand an agent's or contributor's permission. Plan
approval, Review approval, and readiness are not execution, Git, or deployment
authority.

## Development setup

Use the pinned toolchain and lockfiles:

```sh
make bootstrap
make platform-up
```

The canonical local-development instructions and ports are in
[README.md](README.md#quick-start). The default planning Provider is
deterministic and fixture-only. Do not add a real Provider key to make a local
change work.

## Making a change

- Branch from an up-to-date default branch and keep the change narrowly
  scoped.
- Preserve unrelated worktree changes.
- Keep API routes, schemas, services, persistence, and Runner executors in
  their documented boundaries.
- Change FastAPI/Pydantic source before generated OpenAPI or TypeScript output;
  regenerate through `make contracts`.
- Add an additive Alembic migration for persistent schema changes. Do not edit
  shared migration history.
- Add behavior-level tests, including rejection and permission-boundary cases.
- Do not disable tests, lower thresholds, broaden exclusions, or weaken a
  security invariant to obtain a pass.
- Update product, architecture, security, runbook, and evidence documents when
  behavior or authority changes.

## Verification

Run the narrowest relevant check first, then the affected quality gates. Common
commands are:

```sh
make contracts-check
make format-check
make lint
make typecheck
make test
make build
make migration-check
make source-invariance-check
make security-check
make eval
make e2e
```

Use `make verify` for changes that affect product behavior, core build logic,
multiple services, execution boundaries, or a release gate. Documentation-only
and repository-governance changes should run the targeted publication checks
documented in `docs/evidence/` rather than consuming the full aggregate without
cause.

Report a check as passing only when it ran against the current revision and
returned exit code `0`. An old evidence file or a workflow definition is not a
current pass.

## Pull requests

Complete the pull request template with:

- problem and exact scope;
- authority or security impact;
- tests actually run and their exit codes;
- generated artifacts or migrations, if any;
- limitations and unverified claims; and
- screenshots only when they contain synthetic data and no private machine or
  account information.

Keep commits reviewable. Do not rewrite shared history, force-push a protected
branch, or merge without the repository's explicit review policy.

## License and conduct

No open-source license is currently granted. Contribution acceptance and
licensing terms must be decided before Public conversion. See
[License Decision](docs/publication/license-decision.md). A Code of Conduct will
be selected if and when public community contribution is opened; none is
implied by this repository today.
