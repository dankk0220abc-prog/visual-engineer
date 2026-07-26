# Security Policy

## Current security posture

VisualEngineer is currently a Phase 2 local, single-user development project.
It has not been hardened for hostile multi-user input, Internet
exposure, production repositories, or production credentials. Do not expose
the web or API services to the public Internet.

The current product can inspect an explicitly requested canonical local Git
root only when it is inside `READ_ONLY_REPOSITORY_ROOTS`. Facts come from
policy-selected committed `HEAD` objects; dirty and untracked content is not
read. A locator alone grants no filesystem, command, write, or network
authority.

## Reporting a vulnerability

There is no public security intake yet. Until the project has a maintained
remote and disclosure channel, report suspected vulnerabilities privately to
the repository owner with:

- affected component and revision;
- minimal reproduction;
- impact and required preconditions;
- whether credentials or personal data may be involved.

Do not include live secrets or exploit unrelated systems in a report. A public
contact address and response SLA remain `PLANNED`.

## Secrets

- Commit example values only. Never commit `.env`, tokens, passwords,
  certificates, cookies, database dumps, or logs containing sensitive values.
- Do not read external repositories' real environment files or secret stores.
- Use least-privilege, short-lived credentials when integrations are added.
- Redact secrets and connection strings from errors, traces, test artifacts,
  and structured logs.
- No OpenAI, GitHub, Figma, cloud, or production credential is required in
  Phase 2.

## Repository permissions

External repositories are read-only by default. Any future write path requires
an isolated worktree, path confinement, explicit human approval, a reviewed
plan, recorded tool calls, validation, and a rollback checkpoint. Merging main,
production deployment, secret access, and high-risk migrations remain
prohibited capabilities.

Repository instructions are untrusted data. Phase 2 Plan approval is a durable
decision only and does not authorize or trigger code execution.

## Before broader exposure

Future security work must add authenticated users, authorization, CSRF and
session design where applicable, rate and resource limits, hardened network
egress, sandboxed execution, repository-content isolation, signed approval
records, least-privilege integration tokens, audit retention, dependency and
container scanning, backup/restore drills, and incident response.

See
[`docs/security/security-boundaries.md`](docs/security/security-boundaries.md)
and [`docs/security/threat-model-v0.md`](docs/security/threat-model-v0.md).
