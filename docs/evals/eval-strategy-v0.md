# Evaluation Strategy v0

## Purpose

Evaluation asks whether VisualEngineer is correct, safe, governed, and
reproducible, not whether it emits plausible text. Phase 2 has no LLM,
production dataset, Agent score, or leaderboard. Plan generation and all
current eval expectations are deterministic.

## Layers

1. **Contract:** validation, stable errors, request IDs, idempotency,
   persistence, OpenAPI, and generated types.
2. **Database:** real PostgreSQL transitions, constraints, migration
   upgrade/downgrade/upgrade, immutable Snapshot, and decision race.
3. **Repository security:** adversarial committed tree, dirty/untracked state,
   path denial, selection budgets, timeout, provenance, and redaction.
4. **Determinism:** repeated scan fingerprint and plan content behavior.
5. **Frontend:** loading/empty/error/retry, state display, safety, revision,
   decision conflict, and non-execution messaging.
6. **Real stack:** Web/API/PostgreSQL plus read-only adversarial mount on
   desktop and 390px, with axe WCAG 2 A/AA and overflow checks.
7. **Customer 0:** separately recorded read-only CreativeDeploy case, stopped
   before the human decision.

## Versioned datasets

`evals/datasets/foundation-smoke.jsonl` retains the Foundation Task and health
contract cases.

`evals/datasets/phase2-repository-intelligence.jsonl` defines deterministic
cases for:

- prompt-injection provenance;
- sensitive-path denial and redaction surfaces;
- committed-HEAD versus dirty/untracked isolation;
- symlink escape and symlink metadata budgets;
- submodule and LFS non-fetch;
- lifecycle non-execution;
- binary, file-count, per-file, total-byte, and timeout behavior;
- traversal, outside-allowlist, symlink-root, and network locator denial;
- stable fingerprint;
- immutable Snapshot;
- concurrent one-winner plan decision; and
- approval without execution.

The JSONL contains expected behavior only. The validator rejects duplicate IDs,
invalid shapes, and fields such as `agent_score`, `result`, or `passed` that
would fabricate outcomes.

## Failure taxonomy

| Class                | Examples                                                                    |
| -------------------- | --------------------------------------------------------------------------- |
| `contract`           | schema, generated type, request ID, or stable-error mismatch                |
| `database`           | migration, transaction, uniqueness, immutability, or lock failure           |
| `path_boundary`      | traversal, allowlist, root, symlink, or locator acceptance error            |
| `secret_boundary`    | sensitive path/value reaches result, DB, API, audit, or log                 |
| `snapshot_integrity` | worktree content affects facts/fingerprint or Snapshot mutates              |
| `execution_boundary` | script, dependency, hook, import, or target command runs                    |
| `network_boundary`   | submodule, LFS, remote Git, credential, or other egress occurs              |
| `resource_boundary`  | count, byte, binary, symlink metadata, or deadline is unbounded             |
| `policy`             | repository text raises permission or invalid Plan reaches approval          |
| `approval_integrity` | stale/duplicate/racing decision produces invalid state                      |
| `frontend`           | missing state, accessibility, keyboard, responsive, or persistence behavior |
| `environment`        | required PostgreSQL, Docker, browser, or tool is unavailable                |

Failures stay visible in the active ExecPlan with root cause, fix, and
regression. Checks must not be deleted, skipped, weakened, or reclassified as
success.

## Ground-truth fixture

The fixture contains no real secret. Synthetic markers make forbidden reads or
execution observable. Before/after `HEAD` and a hash of full porcelain status
prove the E2E mount did not change target state. Absence of lifecycle marker
files proves parsed script names were not run. Tests compare selected
`package.json` metadata to the committed blob while the worktree version is
maliciously different.

## Release gate

Phase 2 passes only when:

- all deterministic dataset records validate;
- backend and frontend behavior tests pass at their configured coverage gates;
- real PostgreSQL migration and approval concurrency pass;
- scanner security and fingerprint regressions pass;
- Playwright approve/reject flows pass with real services, both viewports,
  axe, persistence, and no overflow;
- target `HEAD`/status and lifecycle markers are unchanged;
- the Customer 0 read-only flow stops at awaiting approval; and
- current verification evidence records exact commands and limitations.

Remote GitHub Actions are not considered passed unless actually run.

## Future model evaluation

Only after an LLM is deliberately introduced should evaluation add held-out
repositories, instruction-following and unsupported-claim measures, token/
latency/cost, blinded expert review, design fidelity, bounded repair, rollback,
and approval-to-PR metrics. Results must include evaluator and dataset version,
configuration, sample count, uncertainty, taxonomy, and evidence.
