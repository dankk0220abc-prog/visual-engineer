# Phase 4 Verification Evidence

- Date: 2026-07-27 (Asia/Shanghai)
- Branch: `feat/phase-4-isolated-workspace-tools`
- Baseline: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Intended checkpoint: `feat: add isolated workspace and scoped file tools`
- Remote CI: not run; no remote is configured

## Accepted Phase 3 baseline

Before Phase 4 implementation, the specified Phase 3 commit passed local
`make verify`, `make runner-smoke`, and `make runner-chaos-check`. Runtime
inspection confirmed online Runner, internal-only network, no repository or
Docker-socket mount, non-root/read-only/capability restrictions, failed public
egress, and redacted logs. `main` fast-forwarded from `336b46d` to `7590f9d`
without a merge commit. Post-merge contract, Runner/protocol, and live smoke
checks passed.

## Phase 4 current-worktree evidence

- Backend/API/Runner/Protocol suite: 101 passed, 82.29% combined coverage, one
  upstream Starlette/httpx deprecation warning, no skips.
- Frontend unit suite: 39 passed; 72.11% statements, 66.56% branches, 71.89%
  functions, and 74.15% lines.
- Real Playwright E2E: 12 passed in 50.9 seconds in the final aggregate run. Phase 4
  completed the real browser flow at desktop and 390 px, including axe and
  overflow assertions, with the source fingerprint guard enabled.
- Real workspace smoke: prepare, read, replace, create, sensitive/traversal/
  symlink/stale-hash denials, status, diff, three Checkpoints, rollback,
  discard, and full source fingerprint unchanged.
- Real workspace chaos: two prepare Attempts, interrupted atomic write,
  unchanged pre-commit target, two stale leases fenced, retry recovery,
  rollback, discard with no residual workspace, and full source fingerprint
  unchanged.
- Workspace static/adversarial security: 25 focused tests plus the static
  descriptor/isolation checker passed. The broader Runner security target
  passed 42 tests, and the secret scan found no high-confidence secret.
- Eval validator: 58 deterministic cases across four datasets plus 7 scanner
  tests.
- Migration upgrade/downgrade/upgrade, generated contract drift, production
  Web build, and every committed Compose configuration passed.

These are current-worktree observations. The aggregate pre-checkpoint gate
passed. The post-checkpoint gate, final commit hash, and clean-worktree result
are recorded only after they execute.

## Source-isolation method

The smoke, E2E, and chaos harnesses record exact source `HEAD`, a hash of
porcelain status, and a full lstat/content fingerprint including `.git`,
tracked, dirty, untracked, hook, and symlink entries before and after. The
isolated worktree is modified while these source values must remain identical.
Only Runner receives the read-only fixture mount.

## Final verification ledger

| Command                         | Result                                                      |
| ------------------------------- | ----------------------------------------------------------- |
| `make format`                   | exit 0; 92 Python files unchanged; Prettier completed       |
| `make format-check`             | exit 0; Ruff and both Prettier scopes pass                  |
| `make lint`                     | exit 0; Ruff and ESLint pass with zero warnings             |
| `make typecheck`                | exit 0; mypy 70 files and TypeScript pass                   |
| `make test`                     | exit 0; backend 101, frontend 39                            |
| `make build`                    | exit 0; all Next.js routes built                            |
| `make contracts-check`          | exit 0; regenerated OpenAPI/TypeScript have no drift        |
| `make migration-check`          | exit 0; PostgreSQL upgrade/downgrade/upgrade                |
| `make workspace-security-check` | exit 0; 25 tests and static boundary scan                   |
| `make security-check`           | exit 0; secret/static/scanner/42-test Runner gate           |
| `make eval`                     | exit 0; 58 cases and 7 scanner tests                        |
| `make e2e`                      | exit 0; 12 Playwright tests in 50.9s, desktop and 390 px    |
| `make workspace-smoke`          | exit 0; full lifecycle, three Checkpoints, source unchanged |
| `make workspace-chaos-check`    | exit 0; recovery/fencing/disposal, source unchanged         |
| `make verify`                   | exit 0; complete aggregate pre-checkpoint gate              |
| `docker compose config`         | exit 0; base/test/workspace/E2E/Customer 0 variants         |
| `git diff --check`              | exit 0 on the current worktree                              |

No remote CI result is claimed.
