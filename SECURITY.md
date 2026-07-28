# Security Policy

## Current security posture

VisualEngineer is currently a Phase 4 local, single-user development project.
The original audit and independent re-audit both remain **Security Gate:
FAIL**. This Round 2 branch is a remediation candidate only; local green
checks cannot replace a new independent decision. Phase 4 is not in `main`
and must undergo a separate Phase 4 Independent Focused Security Re-Audit.

The system has not been hardened for hostile multi-user input, Internet
exposure, production repositories, or production credentials. Do not expose
the web or API services to the public Internet.

The current product can inspect an explicitly requested canonical local Git
root only when it is inside `READ_ONLY_REPOSITORY_ROOTS`. Facts come from
policy-selected committed `HEAD` objects; dirty and untracked content is not
read. A locator alone grants no filesystem, command, write, or network
authority.

The Phase 3 base platform remains repository-free. The Phase 4 fixture profile
gives only the independent Runner one exact synthetic Git source bind,
read-only, plus dedicated managed credential/mirror/workspace/registry
volumes. API, Web, and PostgreSQL get none. The hardened snapshot adapter does
not execute Git against the source; it validates bounded
loose/pack/index/delta input, computes the exact authorized commit/tree/blob
closure, and materializes only that closure into new Runner-owned
loose-object inodes. Runner has no shell, arbitrary command, Docker socket,
inbound port, database/Web network, or public network, and has explicit CPU,
memory, PID, FD, subprocess-output, process-group deadline, and mirror
object/byte/graph bounds.

Execution requires an immutable server-derived Grant, a separate local-user
decision, a fenced typed Job, and—for every mutating operation—a short-lived,
single-use Side-effect Permit acquired from current PostgreSQL authority. The
Grant is bound to the approved Plan/Snapshot/revision, `sandbox/**`,
sensitive-path denials, strict budgets, network `none`, and false
shell/source-write/Git-delivery fields. `revoke_requested` blocks new permits;
`revoked` becomes effective only when every consumed permit is terminal or
expired.

File access is descriptor-rooted and no-follow; status/diff/rollback/discard
use fixed operations. Workspace registry, ownership, and pending/completed
discard evidence are domain-separated HMAC authenticated with a mode-`0600`
Runner-local key. Missing proof enters `recovery_required`; inconsistent,
expired, replayed, or root/inode-conflicting proof enters a typed failure;
unknown content enters `quarantined`. None of those paths deletes. This is
fixture-only and is not a hostile multi-tenant or production sandbox.

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
  Phase 4.
- `.env.runner.local` is ignored local bootstrap state. The Bootstrap Token
  must never be printed or stored in PostgreSQL. Per-Runner Tokens are returned
  once, persisted only in the dedicated Runner volume, and stored in the
  database only as high-entropy SHA-256 digests.
- The Workspace ownership HMAC key is generated inside the Runner credential
  volume with mode `0600`. Its value and signed local paths must never enter
  PostgreSQL, API/Web responses, logs, test evidence, or Git.
- The local bearer-token scheme is not a production identity solution.

## Repository permissions

External repositories are read-only by default. Phase 4 permits writes only in
the Runner-owned isolated copy of the synthetic fixture. It does not authorize
CreativeDeploy or source-repository writes. Any future real repository path
requires a new maximum-depth security audit and approval. Merging a target
main branch, production deployment, secret access, target commands, and
high-risk migrations remain prohibited capabilities.

Repository instructions are untrusted data. Phase 2 Plan approval is a durable
decision only and does not authorize or trigger a Runner Job. Browser dispatch
cannot submit or expand a Permission Envelope.

## Before broader exposure

Future security work must add authenticated users, authorization, CSRF and
session design where applicable, rate and resource limits, hardened network
egress, sandboxed execution, repository-content isolation, signed approval
records, least-privilege integration tokens, audit retention, dependency and
container scanning, backup/restore drills, and incident response.

See
[`docs/security/security-boundaries.md`](docs/security/security-boundaries.md)
and [`docs/security/threat-model-v0.md`](docs/security/threat-model-v0.md).
The Phase 3 execution boundary is detailed in
[`docs/security/runner-threat-model.md`](docs/security/runner-threat-model.md).
The Phase 4 filesystem and workspace boundary is detailed in
[`docs/security/workspace-threat-model.md`](docs/security/workspace-threat-model.md).
