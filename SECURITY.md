# Security Policy

## Current security posture

VisualEngineer is currently a local, single-user development project through
the second Phase 5 implementation slice.
The original audit, independent re-audit, focused re-audit, and
single-finding re-audit remain **Security Gate: FAIL** for the revisions they
inspected. Those historical decisions are preserved. Four focused remediation
rounds and their independent closure checkpoints now culminate in a complete
local Phase 4 Final Integration Gate PASS. That local result does not claim
remote CI, customer, hostile multi-tenant, or production validation. Phase 4
was explicitly integrated into local `main` at
`928a89d2055d172bbd7c6670b42f668d103dcb03`; the independently sealed first
Phase 5 slice is integrated in local `main` at
`f547091307c52df8f20fc69bac4b4826cbbc74ad`. The second slice is limited to a
system-owned Suite of fixed-Profile validations of the trusted synthetic
fixture. Its implementation evidence does not declare Security Gate PASS and
requires an independent focused review.

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
loose-object inodes. A mirror starts from an explicitly empty Git template,
has an exact detached `HEAD` and empty loose/packed ref namespace, and rejects
unprovable pre-existing metadata. Every Runner-owned Git process disables
replacement objects in both its command and fixed environment. After
checkout, a descriptor-rooted no-follow Workspace manifest must exactly match
the source-less parser's authorized path/type/mode/size/content-digest
manifest before ownership or registry evidence is created. The source-less
walk charges every actually expanded path, including every path through a
shared tree, before an over-limit entry or its blob digest is created. Runner
has no shell, arbitrary command, Docker socket,
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

A Suite request can select only a source-owned Suite ID/version. It cannot
provide steps, Profile definitions, command, argv, cwd, environment, shell, or
artifact content. The Control Plane dispatches one pre-existing fixed-Profile
Validation Run at a time, revalidates every child result, enforces the combined
timeout/output/attempt budgets, and writes one immutable aggregate result.
Cancel and total timeout cancel any active child before terminalizing and
never dispatch a pending child. Retry requires a fresh approved Suite Grant;
successful child Evidence is referenced without redispatch or output recharge.

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
  Phase 4 or the Phase 5 fixture validation slice.
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
