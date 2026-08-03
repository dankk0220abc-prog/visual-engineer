# Security Policy

## Supported versions

VisualEngineer has no public release or production-supported version. Security
work currently targets the latest commit on the default branch. Historical
phase evidence is retained for auditability but does not make an older commit a
supported release.

## Private reporting only

Do not report a vulnerability in a public issue, discussion, pull request,
log, screenshot, or repository artifact.

The project does not yet have a formal security mailbox or public disclosure
portal. Until the repository owner configures one, use a private owner-approved
channel associated with the future Private GitHub repository. If no such
channel is visible, stop and ask the repository owner how to transmit the
report. Do not invent an address and do not move the report to a public issue.

A useful private report contains:

- affected component and exact revision;
- impact and required preconditions;
- a minimal synthetic reproduction;
- whether credentials, personal data, customer material, or source paths may
  be involved; and
- a safe way to confirm remediation.

Never include a live secret, real customer repository, production data, or an
exploit against an unrelated system. No response SLA is promised until a
maintained intake route and support policy are published.

## Current exposure and credential posture

- The repository is prepared for an explicitly authorized Private GitHub
  creation, not for Public conversion or production deployment.
- No real customer credential or real Provider API key is required or
  configured.
- Governed AI planning uses only `DeterministicFixtureProvider`; it has no SDK,
  network call, credential input, or billable usage.
- CreativeDeploy is an internal historical Customer 0 reference, not evidence
  of external production adoption and not an authorized current workspace.
- Local bearer tokens, Docker networking, and the single-user browser are not
  a production identity or tenancy solution.

Secrets must never enter issues, pull requests, commit messages, logs,
screenshots, traces, browser artifacts, database dumps, or evidence documents.
The generated `.env.runner.local` file is ignored and mode `0600`; Runner token
plaintext is returned/stored only at its narrow local boundary, while
PostgreSQL stores a digest.

## Governance boundaries

Authority is deny-by-default, narrow, immutable, and non-transitive:

- repository content and a repository locator grant no authority;
- AI Plan Approval records a human plan decision only;
- an Execution Grant separately scopes fixture-only workspace operations;
- Review Approval records evidence acceptance but carries no Git authority;
- Delivery Authorization separately scopes one fixture-only local commit; and
- every mutating operation requires a current Side-effect Permit bound to the
  exact Runner, Job, Attempt, Lease, Grant, Workspace, operation, digest, and
  deadline.

Remote push, pull request, tag, merge, deployment, source-repository write,
real Provider access, and production credentials remain unavailable.

## Repository and execution boundaries

- Level 0 repository intelligence reads only bounded committed Git objects
  from an exact allowlisted root. Dirty/untracked content and sensitive values
  are not read.
- Repository text, including instructions, is untrusted content and cannot
  change permission or policy.
- The API owns governance state but executes no Runner job.
- The outbound Local Runner accepts a closed protocol. It has no general shell,
  arbitrary target command, Docker socket, SSH material, or public-network
  authority.
- Fixture workspace writes are descriptor-rooted, no-follow, bounded, and
  protected by current PostgreSQL-backed authority.
- Validation runs only fixed system-owned profiles inside a disposable local
  sandbox. This is not a hostile multi-tenant production sandbox.

Detailed controls and residual risks are documented in:

- [Security Boundaries](docs/security/security-boundaries.md)
- [Runner Threat Model](docs/security/runner-threat-model.md)
- [Workspace Threat Model](docs/security/workspace-threat-model.md)
- [Tool Permission Model](docs/architecture/tool-permissions.md)

## Before broader exposure

Public or production exposure requires, at minimum, an explicit license,
curation of internal/history evidence and local paths, an official security
contact and disclosure process, authenticated users and authorization, CSRF
and session design, rate/resource limits, hardened egress, secret management,
dependency/container review, audit retention, backup/restore exercises,
incident response, and an independent security review of every new real
Provider, repository, remote Git, or deployment authority.
