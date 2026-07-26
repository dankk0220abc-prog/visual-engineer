# Threat Model v0

## Scope and assumptions

This model covers the local Foundation web/API/PostgreSQL slice and the future
boundary toward autonomous repository work. The current assumption is one
trusted local operator, but browser/API input and all repository content are
untrusted. Controls described as Foundation controls require verification
evidence before they are considered effective.

| Threat                          | Current risk                                                                         | Foundation Sprint control                                                                            | Later required control                                                                                                   |
| ------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Prompt injection                | Future repository text may impersonate instructions and request broader access.      | No LLM or Agent runtime; locator is inert; external survey is human-bounded Level 0.                 | Treat repository text as data; instruction provenance, policy engine, context separation, adversarial evals.             |
| Malicious repository content    | Files can contain traps, huge inputs, generated malware, or dependency hooks.        | No generic repository ingestion or execution; external install/build/test prohibited in survey.      | Sandboxed parser/executor, file and size limits, binary policy, dependency-script controls, malware scanning.            |
| Path traversal / symlink escape | A locator or archive path could escape an intended workspace.                        | API never dereferences locators; length and NUL validation.                                          | Canonical-path confinement, `openat`-style safe access, symlink policy, mount isolation, archive traversal tests.        |
| Shell injection                 | User or repository strings could become commands.                                    | No shell tool; values stay typed metadata; project automation uses fixed commands.                   | Structured process APIs, strict command/argument allowlists, no shell interpolation, time/resource limits.               |
| Secret leakage                  | Config, repository files, logs, errors, or artifacts may expose credentials.         | No credential need; real env/secret reads prohibited; response and logging policy redacts internals. | Secret scanning, classified artifacts, redaction tests, vault-backed short-lived credentials, incident rotation.         |
| Dependency scripts              | Package installation may run arbitrary lifecycle code.                               | CreativeDeploy install is prohibited; Foundation dependency use is only in the owned repository.     | Lockfile review, trusted registries, lifecycle-script policy, isolated network-limited build, SBOM and provenance.       |
| Destructive Git command         | Reset/clean/rebase/force push can erase user work or history.                        | External repository is read-only; destructive commands prohibited; preserve dirty state.             | Command policy, immutable checkpoint, isolated worktree, protected branches, recoverability tests.                       |
| Unauthorized write              | A tool may edit outside approved scope or before approval.                           | No target write tool; repository locator grants no authority.                                        | Capability tokens bound to run/path/plan, kernel/container isolation, write audit, fail-closed approval checks.          |
| SSRF                            | A future repository URL or artifact fetch could reach local/cloud metadata services. | API does not fetch locators; no integration egress.                                                  | URL parsing, scheme/host allowlists, DNS/IP revalidation, private/link-local denylist, egress proxy.                     |
| Sensitive logging               | Request bodies, connection strings, tokens, or stack traces could enter logs.        | Structured request metadata only; stable public errors; no full sensitive payloads.                  | Central redaction, field classification, access/retention controls, leak canaries and tests.                             |
| Docker privilege                | Privileged containers, Docker socket, or root workloads could escape isolation.      | Local Compose only; require non-root runtime and no socket/privileged mode.                          | Rootless hardened sandbox, seccomp/AppArmor, read-only filesystem, dropped capabilities, isolation tests.                |
| GitHub token overreach          | Broad tokens could push, merge, or access unrelated repositories.                    | No token, remote, push, or PR action.                                                                | Fine-grained short-lived token, repository/base allowlist, no merge scope, approval and audit.                           |
| Approval bypass                 | Race, replay, stale state, or UI confusion could execute an unapproved plan.         | No execution or approval engine; future state machine is documented only.                            | Signed attributable approvals bound to plan hash/version, expiry, optimistic locking, server-side gates, negative tests. |
| Rollback failure                | Partial external effects may make rollback incomplete or destructive.                | No target changes; no rollback claim.                                                                | Pre-change checkpoints, compensating actions, effect journal, idempotent rollback, failure escalation and drills.        |

## Abuse and reliability cases

- Duplicate requests are expected and must not duplicate tasks.
- Conflicting reuse of an idempotency key must fail with a stable 409 error.
- Pagination and field limits constrain memory/database abuse but are not a
  substitute for future rate limits.
- Database unavailability must make readiness fail without making liveness fail
  or exposing connection details.
- Cancellation and retries must be version checked when Run orchestration is
  introduced.

## Validation plan

Foundation verification should include input-bound tests, NUL rejection,
idempotency races/conflicts, stable errors, request-ID behavior, dependency and
secret scans, Compose configuration inspection, and a real PostgreSQL/browser
smoke flow. Future Agent phases require dedicated adversarial repositories,
prompt-injection cases, path-escape tests, command-policy tests, approval-bypass
tests, and rollback drills.

## Residual risk

Even with all Foundation checks passing, authentication, hostile multi-user
isolation, sandboxed code execution, integration credentials, production
hardening, and incident response remain absent. The system must stay local and
must not act on target repositories.
