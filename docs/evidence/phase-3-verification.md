# Phase 3 Verification Evidence

- Phase: Browser-Orchestrated Local Runner Foundation
- Date: 2026-07-26
- Branch: `feat/phase-3-browser-orchestrated-local-runner`
- Remote CI: NOT RUN; no remote is configured
- Status: COMPLETE LOCALLY; remote CI not run

## Scope

This evidence covers the repository-free Runner Protocol, PostgreSQL state and
lease semantics, Local Runner, browser console, Docker boundary, deterministic
Eval, and source integrity. It does not claim LLM, repository access, shell,
worktree, Git/PR, public network, production deployment, or remote CI.

CreativeDeploy was not mounted, scanned, read, or modified during Phase 3.
Its Phase 2 rejection evidence remains historical and separate.

## Verified during implementation

- Real PostgreSQL backend/Runner/protocol suite: 76 passed; total API source
  coverage 83.92%.
- Frontend Vitest: 32 passed; 82.89% statements, 74.60% branches, 85.00%
  functions, and 84.36% lines.
- Playwright real-stack Web/API/PostgreSQL/Runner: 10 passed across desktop and
  390 px. Both Phase 3 diagnostic and cancellation flows include axe WCAG 2
  A/AA and horizontal-overflow checks.
- Chaos: actual immediate Runner stop, derived offline state, lease expiry,
  requeue, old completion rejected with `409 stale_lease`, restored Runner,
  second Attempt success, and unchanged source status.
- Eval validator: 43 deterministic cases across three versioned datasets,
  including explicit Runner test mappings and no model scores.
- Migration round trip upgraded an empty PostgreSQL database through revision
  `20260726_0003`, downgraded to base, and upgraded to head again.
- Docker Compose rendered successfully for base, test, E2E, and Customer 0
  configurations.
- Runtime inspection proved Runner UID/GID 10001, a read-only root filesystem,
  all capabilities dropped, `no-new-privileges`, no published port, and only
  the dedicated credential volume at mode 0600.
- Runtime network probes returned API readiness 200 while Runner access to
  PostgreSQL DNS, Web DNS, and a public HTTPS destination failed. The
  bootstrap token was absent from combined API/Runner/Web/PostgreSQL logs.

## Failures repaired

1. The first browser run passed 8/10; the two failures were the same strict
   selector resolving both a Timeline label and its metadata. The product state
   was correct. The selector was made exact and the full run passed 10/10.
2. The first chaos injection used graceful `docker compose stop`. Runner
   correctly completed its in-process Job before shutdown, so no lease expired.
   The test now uses an immediate zero-timeout stop to simulate process loss;
   the complete recovery chain passed.
3. A static security marker initially matched safe `platform.system()`. The
   rule was narrowed to actual shell/subprocess primitives and retained AST
   import enforcement.
4. One direct pytest command was invoked without the required test PostgreSQL
   service. The official `make test-api` entrypoint started the database and
   passed all 76 tests.
5. The first final static gate found two import-order findings and two strict
   `Any` return findings in test helpers. Imports were sorted, response values
   were explicitly cast, and the unchanged format/lint/typecheck/contract
   group passed.
6. One manual migration inspection used an obsolete candidate filename. It
   performed no write; the command was rerun against
   `20260726_0003_add_local_runner_foundation.py`.
7. The first staged large-file loop used zsh's special `path` variable and
   therefore lost command lookup inside the loop. Its output was discarded;
   the audit was rerun with `staged_file` and confirmed no staged file exceeds
   1 MiB.

No test was deleted, skipped, or weakened, and no threshold was lowered.

## Final command ledger

| Command                     | Status                                               |
| --------------------------- | ---------------------------------------------------- |
| `make format`               | VERIFIED: exit 0                                     |
| `make format-check`         | VERIFIED: exit 0                                     |
| `make lint`                 | VERIFIED: exit 0                                     |
| `make typecheck`            | VERIFIED: exit 0                                     |
| `make test`                 | VERIFIED: 76 backend/Runner/protocol + 32 frontend   |
| `make build`                | VERIFIED: Next.js production build                   |
| `make contracts-check`      | VERIFIED: repeatable generation, no drift            |
| `make migration-check`      | VERIFIED: upgrade/downgrade/upgrade                  |
| `make security-check`       | VERIFIED: secret, scanner, protocol, Runner boundary |
| `make eval`                 | VERIFIED: 43 deterministic cases                     |
| `make e2e`                  | VERIFIED: 10/10 real-stack desktop + 390 px          |
| `make runner-smoke`         | VERIFIED: online Runner and diagnostic success       |
| `make runner-chaos-check`   | VERIFIED: offline/expiry/requeue/fence/recovery      |
| `make verify` before commit | VERIFIED: exit 0                                     |
| `make verify` after commit  | VERIFIED: exit 0                                     |
| `docker compose config`     | VERIFIED: base, test, E2E, Customer 0                |
| `git diff --check`          | VERIFIED before commit and after commit              |

## Required final Git state

The final handoff records the Phase 3 commit hash because a commit cannot
self-embed its final object ID. Post-commit inspection verified a clean
worktree, no remote or push, `main` at `336b46d`, Phase 3 unmerged on its
dedicated branch, the preserved Customer 0 database volume, and the local
platform running at `http://127.0.0.1:3000`.
