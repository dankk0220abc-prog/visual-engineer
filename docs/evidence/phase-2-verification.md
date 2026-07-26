# Phase 2 Verification Evidence

- Date: 2026-07-26 (Asia/Shanghai)
- Branch: `feat/phase-2-readonly-repository-intelligence`
- Foundation commit: `d136418158d9f5ffc4f2f8ba993ca48e837ed59b`
- Checkpoint status: COMPLETE
- Remote CI: not run

## Baseline

The batch began on clean `main` at the exact Foundation commit above, with no
remote and a complete repository-local Git identity. The Phase 2 branch was
created without deleting or resetting any branch.

## Proven architecture

- Five Phase 2 entities are present in SQLAlchemy and one additive Alembic
  migration.
- PostgreSQL enforces fixed read-only/snapshot/plan source/execution fields,
  one Snapshot per Run, Run-scoped Plan version, one decision per Plan,
  reasoned rejection, and Snapshot update/delete denial.
- Services own explicit transitions, committed scanning, deterministic
  planning, revision validation, idempotency, stale conflicts, row locking,
  audit metadata allowlisting, and stable errors.
- The Run console exposes repository facts, safety findings, deterministic
  Plan content, revision/submission/decision controls, non-execution warnings,
  and a durable audit timeline.

## Security and adversarial evidence

The fixture includes synthetic prompt injection, fake `.env` and key paths, an
outside symlink, an oversized symlink blob, large and binary candidates, an
LFS pointer, dependency tree, lifecycle scripts, a gitlink, dirty tracked and
untracked content, traversal/outside/root-symlink/network inputs, and resource
deadline/budget cases.

Current tests prove:

- selected facts come from committed object IDs, not dirty bytes;
- untracked and outside-symlink markers do not enter result/API/DB/audit/log;
- sensitive values are not read or persisted;
- scripts are names only and no lifecycle marker is created;
- symlink targets are not followed and oversized target metadata is not read;
- submodules are not initialized and LFS content is not fetched;
- count, selected-file, per-file, total-byte, dirty-path, and timeout policy is
  bounded;
- same `HEAD` and scanner policy produce the same fingerprint despite dirty
  byte changes;
- Snapshot update and delete are rejected by PostgreSQL;
- approve/reject concurrency produces exactly one final row; and
- E2E preserves synthetic target `HEAD` and full status.

## Customer 0 evidence

CreativeDeploy was mounted only into the non-root API process at
`/repositories/customer0/creative-deploy`, and Docker reported `.RW=false`.
Web had no target mount; PostgreSQL had only its own data volume. No write
probe was used against the real repository.

Before and after observations were identical:

- branch `main`;
- `HEAD` `bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`;
- 13 porcelain status paths;
- status SHA-256
  `0307d1daaa9ac29e09567e63513b5b77263a1e2ffafec3054fdfcd299210dca7`;
- tracked diff stat of four files, 84 insertions, and 21 deletions; and
- diff-stat SHA-256
  `adb5a57b58493814020a44c711589144f33b6336eadbd6bc3d35c8f95132d076`.

Durable IDs:

- Task `d71b708b-597e-448d-a41c-90df41c602f0`;
- Run `447510d7-695c-46ec-baad-9a0f750ce965`;
- Snapshot fingerprint
  `41c0ff6896e97d22b876e7bfe9d31f6f260998a74a2b0ddbcdb3620be1a53797`;
- Plan v1, source `deterministic_policy`, status `awaiting_approval`;
- Run status `awaiting_plan_approval`; and
- local page
  `http://127.0.0.1:13001/runs/447510d7-695c-46ec-baad-9a0f750ce965`.

Audit ends with `plan_submitted`. No decision API was called.

## Verification matrix

| Command                     | Exit | Result                                     |
| --------------------------- | ---: | ------------------------------------------ |
| `make format`               |    0 | Ruff/Prettier completed                    |
| `make format-check`         |    0 | Python and workspace formatting pass       |
| `make lint`                 |    0 | Ruff and ESLint, zero findings             |
| `make typecheck`            |    0 | mypy 38 files + TypeScript strict          |
| `make test`                 |    0 | 55 backend + 21 frontend                   |
| `make build`                |    0 | Next.js production build; four routes      |
| `make contracts-check`      |    0 | OpenAPI and generated TypeScript no drift  |
| `make migration-check`      |    0 | PostgreSQL upgrade/downgrade/upgrade       |
| `make security-check`       |    0 | secret scan + 7 scanner tests              |
| `make eval`                 |    0 | 29 deterministic records + 7 scanner tests |
| `make e2e`                  |    0 | 6 real-stack Playwright flows              |
| `make verify` before commit |    0 | full aggregate matrix passed               |
| `make verify` after commit  |    0 | full aggregate matrix passed               |
| `docker compose config`     |    0 | base configuration rendered                |
| `make docker-config`        |    0 | base/test/E2E/Customer 0 configurations    |
| `git diff --check`          |    0 | no whitespace errors                       |

Coverage from the current intermediate full test:

- backend: 84.91% total;
- frontend: 87.38% statements, 73.87% branches, 90.65% functions, and 88.29%
  lines.

Playwright passes desktop and 390px approve/reject flows with real
Web/API/PostgreSQL, refresh persistence, axe WCAG 2 A/AA, and no horizontal
overflow.

## Failures retained

1. Initial Ruff/mypy failures exposed import, formatting, exception-chain, and
   route `NoReturn` issues; all were corrected and strict checks pass.
2. A Foundation cleanup fixture assumed Task was the only table; it now
   truncates all mapped PostgreSQL tables.
3. The first eval validator accepted only Phase 2 JSONL; it now validates both
   versioned dataset shapes without allowing invented results.
4. Frontend type/effect checks exposed cancellation narrowing and effect-state
   update issues; request lifetime and deferred refresh were corrected.
5. Narrow axe found non-focusable scrollable audit metadata; labelled,
   focusable `<pre>` regions fixed the keyboard boundary and all six E2E flows
   pass.
6. Security review found unbounded symlink metadata read before normal file
   budget; the scanner now checks size before `cat-file`, with regression.
7. Pre-stage review found sensitive-path manifest entries retained unnecessary
   Git object ID and size. Both sensitive-name and detected-secret branches now
   remove them; a dynamic fake-token regression covers result/API/DB/audit/log.

No test was deleted, skipped, threshold-lowered, or weakened.

## Evidence boundary

This evidence proves local Phase 2 read-only investigation and durable
deterministic plan decisions only. It proves no LLM, Agents SDK, code writing,
target command execution, worktree, PR, remote CI, external-customer adoption,
production outcome, or production deployment. Approval does not authorize
execution.
