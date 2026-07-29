# Evaluation Strategy v0

## Purpose

Evaluation asks whether VisualEngineer is correct, safe, governed, and
reproducible, not whether it emits plausible text. Phase 4 has no LLM,
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
   before its later separately verified human rejection.
8. **Runner protocol and state:** registration, credentials, Envelope,
   concurrency, leases, fencing, cancellation, retry, liveness, redaction, and
   stable failure classification.
9. **Execution plane:** real outbound Runner success/cancellation and abrupt
   loss/recovery without public-network authority.
10. **Isolated Workspace:** Grant separation, exact revision, source
    isolation, descriptor paths, atomic text writes, budgets, checkpoints,
    rollback, disposal, and interruption recovery.
11. **Validation Suites:** immutable catalog/order, step injection denial,
    serial child fencing, cancellation/timeout/retry races, exact aggregate
    budgets, Evidence reuse/aggregation, cleanup, and invariance.

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

`evals/datasets/runner-protocol-v0.1.jsonl` defines deterministic registration,
heartbeat, claim/concurrency, Envelope, stale lease, cancellation, retry,
offline, secret redaction, unsupported capability, terminal state, and failure
classification cases. Every record declares schema/dataset version, expected
outcome, failure category, and one or more existing test-function mappings.
The validator rejects a missing or stale mapping.

`evals/datasets/workspace-tools-v0.1.jsonl` adds 15 deterministic cases for
Grant approval/revocation/expiry, path/sensitive/symlink/special-file denial,
compare-and-swap conflict, atomic interruption, cancellation, file/byte/diff
budgets, source isolation, Checkpoint/diff, rollback, disposal, stale Lease,
and stable failure classification. Every case maps to executable tests; no
model score or inferred outcome is stored.

`evals/datasets/validation-suites-v0.1.jsonl` maps deterministic cases for
catalog/step injection, serial success, create replay/conflict, revoked Grant,
partial failure and fresh-Grant retry, successful-Evidence reuse without
recharge, cancellation and completion race, Suite timeout cleanup, child
timeout/recovery fail-fast, and exact/+1 combined output. The dataset stores
expected behavior only and every case maps to a current executable test.

## Failure taxonomy

| Class                       | Examples                                                                    |
| --------------------------- | --------------------------------------------------------------------------- |
| `contract`                  | schema, generated type, request ID, or stable-error mismatch                |
| `database`                  | migration, transaction, uniqueness, immutability, or lock failure           |
| `path_boundary`             | traversal, allowlist, root, symlink, or locator acceptance error            |
| `secret_boundary`           | sensitive path/value reaches result, DB, API, audit, or log                 |
| `snapshot_integrity`        | worktree content affects facts/fingerprint or Snapshot mutates              |
| `execution_boundary`        | script, dependency, hook, import, or target command runs                    |
| `network_boundary`          | submodule, LFS, remote Git, credential, or other egress occurs              |
| `resource_boundary`         | count, byte, binary, symlink metadata, or deadline is unbounded             |
| `policy`                    | repository text raises permission or invalid Plan reaches approval          |
| `approval_integrity`        | stale/duplicate/racing decision produces invalid state                      |
| `frontend`                  | missing state, accessibility, keyboard, responsive, or persistence behavior |
| `environment`               | required PostgreSQL, Docker, browser, or tool is unavailable                |
| `authentication`            | Bootstrap or Runner identity accepted incorrectly                           |
| `concurrency`               | multiple claim winners or active Attempts                                   |
| `lease_fencing`             | stale, mismatched, expired, or superseded Lease mutates state               |
| `state_transition`          | illegal or terminal Runner Job transition                                   |
| `permission_boundary`       | Envelope/capability authority is expanded                                   |
| `retry_exhausted`           | retry budget is ignored or misclassified                                    |
| `control_plane_unavailable` | transient API failure is retried incorrectly                                |
| `workspace_identity`        | Workspace, Handle, Runner, revision, registry, or root identity mismatches  |
| `content_conflict`          | expected absence/hash/inode changed before atomic commit                    |
| `cleanup_boundary`          | rollback/discard affects unknown, source, or sibling data                   |

Failures stay visible in the active ExecPlan with root cause, fix, and
regression. Checks must not be deleted, skipped, weakened, or reclassified as
success.

## Ground-truth fixture

The fixtures contain no real secret. Synthetic markers make forbidden reads or
execution observable. Phase 4 adds normal/Unicode text, fake sensitive files,
external/sensitive/nested symlinks, binary/oversized content, malicious
instructions, dirty/untracked source data, a hook, gitlink, LFS pointer, and
collision cases; tests add FIFO, socket, hard link, and replacement races.
Before/after exact `HEAD`, status hash, and full lstat/content fingerprint
including `.git` prove the source did not change.

## Release gate

Phase 4 passes only when:

- all deterministic dataset records validate;
- backend and frontend behavior tests pass at their configured coverage gates;
- real PostgreSQL migration and approval concurrency pass;
- scanner security and fingerprint regressions pass;
- Playwright approve/reject flows pass with real services, both viewports,
  axe, persistence, and no overflow;
- target `HEAD`/status and lifecycle markers are unchanged;
- the historical Customer 0 rejection remains separate and Phase 4 never
  accesses CreativeDeploy;
- concurrent claim and stale fencing pass on real PostgreSQL;
- real Runner Playwright diagnostic/cancellation passes at both viewports;
- chaos proves offline, expiry, requeue, new Attempt, stale denial, recovery,
  success, and source integrity;
- real browser flows independently approve a Grant, prepare/read/write/diff/
  checkpoint/rollback/discard a fixture Workspace at desktop and 390 px with
  axe, persistence, and no overflow;
- workspace chaos proves interruption before atomic commit, old-or-complete
  contents, safe retry, stale fencing, no residual worktree, and unchanged
  source/`.git`;
- Compose inspection proves the Runner network, mounts, user, capabilities,
  root filesystem, and no published port; and
- current verification evidence records exact commands and limitations.

Remote GitHub Actions are not considered passed unless actually run.

The Phase 5 second-slice implementation candidate additionally requires the
fixed Suite browser flow, real PostgreSQL Suite state/race/budget matrix,
Runner Docker isolation for both fixed Profiles, aggregate Evidence and
canonical/source invariance, project-filtered zero residue, and a final
`make verify`. Passing implementer checks does not declare the independent
focused Security Gate.

## Future model evaluation

Only after an LLM is deliberately introduced should evaluation add held-out
repositories, instruction-following and unsupported-claim measures, token/
latency/cost, blinded expert review, design fidelity, bounded repair, rollback,
and approval-to-PR metrics. Results must include evaluator and dataset version,
configuration, sample count, uncertainty, taxonomy, and evidence.
