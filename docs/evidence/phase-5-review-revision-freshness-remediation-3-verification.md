# Phase 5 Review revision-freshness final narrow remediation 3 verification

## Disposition

This is production-implementer evidence for the single blocking Finding
`VE-P5-REVIEW-RR-001`. It does not announce Security Gate PASS, sealing, main
integration, Git delivery, a later slice, Customer 0, or Phase 6.

Successful handoff label:

`PHASE 5 REVIEW REVISION FRESHNESS REMEDIATION 3 COMPLETE — READY FOR INDEPENDENT SINGLE-FINDING RE-REVIEW`

## Git preflight

All required commands ran before file modification from
`/Users/danke/Developer/VisualEngineer`.

| Fact                                    | Result                                                            |
| --------------------------------------- | ----------------------------------------------------------------- |
| `pwd -P`; Git top level                 | exact authorized Developer repository; exit `0`                   |
| Intake branch                           | `audit/phase-5-review-revision-freshness-single-finding-rereview` |
| Intake HEAD                             | `a1dd0a9b68c73a45e4aa8b8754e51c385f3bad95`                        |
| Local main                              | `50dcc05ce48d042882bcdf199ae1bee662a83af6`                        |
| Previous candidate                      | `efeecda57109ff8c3470f83a2aeb659e7ead31be`                        |
| Worktree/index/untracked                | clean                                                             |
| Remote/stash/tag                        | empty                                                             |
| Candidate ancestry                      | candidate is an ancestor of the FAIL checkpoint; exit `0`         |
| Candidate-to-checkpoint diff            | one independent test and five audit/governance files only         |
| Candidate-to-checkpoint production diff | none                                                              |
| Required object types/subjects          | all three objects are commits and subjects match                  |
| Target remediation branch probe         | absent as required                                                |

No unexplained merge, delivery ref, historical-test deletion, production-code
change in the audit checkpoint, or baseline mismatch was found. The branch
`fix/phase-5-review-revision-freshness-remediation-3` was created directly
from `a1dd0a9...`; branch creation and post-switch checks exited `0`.

## Candidate and test identity

- Main:
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Remediation-2 candidate:
  `efeecda57109ff8c3470f83a2aeb659e7ead31be`
- Independent FAIL checkpoint / remediation-3 base:
  `a1dd0a9b68c73a45e4aa8b8754e51c385f3bad95`
- FAIL subject:
  `audit(review): record revision freshness re-review failure`
- Independent test SHA-256 before and after production repair:
  `438acf304880b11e5f57aa198da7c918b1dc96a5bf357d507e063bc46b5c7559`

The independent test, its FAIL Evidence, its ExecPlan, and its audit report
were not edited, skipped, xfailed, or weakened.

## Original failure reproduction

Task-owned PostgreSQL:

- Compose project: `ve-p5-review-freshness-remediation-3`
- bind-probed loopback port: `62943`
- database: `visualengineer_test`
- task container health: healthy before testing

Command, with the repository-declared local test URL supplied through
`TEST_DATABASE_URL`:

```text
uv run pytest \
  apps/api/tests/test_phase5_review_revision_freshness_single_finding_rereview.py::test_audit_concurrent_duplicate_revision_replay_advances_once \
  --no-cov -s -vv
```

First unchanged result:

- exit `1`;
- one collected test, one failed;
- input revision identity for both requests:
  `eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee`;
- both registration responses returned that same revision;
- initial generation: `1`;
- persisted generation: `3`;
- generation delta: `2`, expected `1`;
- invalidation rows: `1`;
- invalidation AuditEvents: `1`;
- Decision rows: `0`;
- ready rows: `0`.

This preserved the original production failure before any production edit.

## Confirmed root cause

The trusted registration service performed:

1. an unlocked opaque-Handle query, loading the Handle into the SQLAlchemy
   Session identity map;
2. the existing transaction-level PostgreSQL advisory revision-authority
   lock;
3. a `SELECT ... FOR UPDATE` for the same Handle in the same Session; and
4. the revision comparison and generation decision.

The locked query issued SQL but did not request `populate_existing`. A waiting
transaction could therefore retain the pre-wait ORM attribute values even
after PostgreSQL serialized it behind the first transaction. The stable real
PostgreSQL generation `1 -> 3` reproduction confirms that this stale
comparison reached the generation-bump function twice.

## Production repair

One production file changed:

`apps/api/src/visual_engineer_api/repositories/workspace.py`

The existing locked opaque-Handle query now uses:

```text
SELECT RepositoryHandle ... FOR UPDATE
execution option: populate_existing=True
```

No unlocked query was reinterpreted as authoritative. After the advisory lock,
the locked query now overwrites the identity-map instance with the committed
PostgreSQL row before the service compares `current_revision` and `status`.

No migration, model, service transaction boundary, API schema, generated
contract, Review Decision state, permission, cache, process mutex, or
invalidation function changed.

## Lock-before-read and lock-after-reload behavior

The retained order is:

1. initial lookup only to resolve the existing Handle ID;
2. `lock_review_revision_authority(handle_id)`;
3. locked PostgreSQL Handle lookup with forced refresh;
4. compare refreshed canonical revision/status with the request;
5. for a real change, update Handle and call the existing freshness bump;
6. commit revision, generation, invalidation, and AuditEvent together.

Review Decision/readiness continues to acquire the same advisory authority
lock before the Handle row lock. Both existing approve-first and
revision-first tests observed the waiting transaction in PostgreSQL as
`wait_event_type=Lock`, `wait_event=advisory` and passed.

## Concurrent identical revision evidence

The unchanged independent test after repair:

```text
initial_generation=1
current_generation=2
generation_delta=1
current_revision=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
registration_outcomes=[same revision, same revision]
invalidation_rows=1
invalidation_events=1
decision_rows=0
ready_rows=0
exit=0
```

An additive permanent remediation-3 regression holds the first transaction
after its advisory/row locks, observes the second transaction waiting in
`pg_stat_activity`, and then releases the holder. It proves:

- both inputs are the same `bbbb...bbbb` canonical revision;
- both calls return that same revision;
- both calls observe the same final generation `2`;
- persisted generation is exactly `1 -> 2`;
- invalidation/AuditEvent counts are `1/1`;
- the one historical Decision and ready row remain immutable history;
- effective readiness changes from `ready` to `stale`;
- no duplicate ready row or blocker summary is produced; and
- the observed wait is PostgreSQL `Lock/advisory`, not sleep-only
  synchronization.

The additive regression file passes `2/2`. Its second case submits two
different canonical revisions behind the same observed advisory wait. The
persisted generation is exactly `1 -> 3`, proving two real changes are not
collapsed into one replay; invalidation/AuditEvent remain `1/1` for the one
already-invalidated historical Package.

## Generation, invalidation, and AuditEvent evidence

- Sequential identical replay: generation advances once and remains at `2`.
- Concurrent identical replay: generation advances once and remains at `2`.
- Concurrent different revisions: two real transitions advance generation to
  `3`.
- Identical replay creates no generation gap.
- The historical Package has one durable
  `source_revision_changed` invalidation.
- The Package has one immutable `review_package_invalidated` AuditEvent.
- Direct AuditEvent update and delete attempts fail with SQLSTATE `55000`.
- Historical blocker summary digest remains unchanged.

## Decision/readiness and idempotency fencing

The full independent matrix confirms:

- direct stale `approve` insert: SQLSTATE `55000`, zero new Decision/ready;
- direct stale `reject` insert: SQLSTATE `55000`, zero new Decision/ready;
- direct stale `ready` insert: SQLSTATE `55000`, zero ready;
- `changes_requested`: API `422`, PostgreSQL closed storage boundary;
- old-generation exact keyed replay: HTTP `409`,
  `review_generation_mismatch`;
- historical ready row remains stored but is effectively `stale`;
- approve-first: one historical Decision may commit, then the later revision
  advances generation once, invalidates once, and creates no ready row; and
- revision-first: the waiting approval fails
  `review_generation_mismatch`, with zero Decision/ready rows.

## Transaction rollback evidence

The independent forced pre-commit failure observes tentative generation `2`,
one tentative invalidation, and one tentative invalidation event in the
transaction. After rollback:

```text
revision=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
generation=1
invalidation_rows=0
invalidation_events=0
transaction_outcome=rolled_back
```

Revision, generation, invalidation, and AuditEvent therefore retain one
atomic transaction boundary.

## Focused PostgreSQL results

| Matrix                                                     | Exit |      Result |
| ---------------------------------------------------------- | ---: | ----------: |
| additive remediation-3 concurrency regressions             |  `0` |  `2 passed` |
| unchanged original Finding plus remediation-2 regressions  |  `0` |  `8 passed` |
| independent single-Finding file                            |  `0` | `11 passed` |
| focused Review / `FR-002` / `FR-003` / `FR-004` / `FR-005` |  `0` | `28 passed` |
| affected Workspace/Validation                              |  `0` | `37 passed` |
| clean migration pytest                                     |  `0` |  `1 passed` |

The only warning is the pre-existing Starlette TestClient/httpx deprecation
warning.

## Migration evidence

Production migrations are byte-unchanged.

- static/current head: one legal head, `20260730_0012`;
- populated database before roundtrip:
  `runner=1`, `repository_handle=1`, `audit_event=2`;
- populated `0012 -> 0011`: exit `0`;
- populated `0011 -> 0012`: exit `0`;
- the same populated rows remain afterward;
- exact task database was then recreated to remove synthetic test state;
- clean `base -> head -> base -> head`: exit `0`;
- clean current revision: `20260730_0012`;
- clean migration pytest: `1 passed`, exit `0`.

No new Migration was necessary because the defect was an ORM post-lock reload
gap and the existing PostgreSQL lock/function/trigger model was sufficient.

## Contracts, format, lint, typecheck, and build

| Command                | Exit | Result                                       |
| ---------------------- | ---: | -------------------------------------------- |
| `make contracts-check` |  `0` | regenerated OpenAPI/types have no drift      |
| `make format-check`    |  `0` | Ruff `143` files; Prettier all matched       |
| `make lint`            |  `0` | Ruff and ESLint pass                         |
| `make typecheck`       |  `0` | mypy `109` source files; TypeScript pass     |
| `make build`           |  `0` | Next.js production build and all routes pass |
| `git diff --check`     |  `0` | final governance-formatted diff passes       |

## Source invariance

`make source-invariance-check` exits `0`:

```text
status=PASS
source_entries_compared=119
source_git_objects_compared=10
source_status_records=2
extension_markers=0
```

No canonical Workspace or external source repository was used or modified.

## First failures and invalid attempts

1. **PRESERVED PRODUCTION FAILURE:** the unchanged concurrent duplicate test
   exits `1` before repair with generation `1 -> 3`.
2. **TEST-ONLY LOCK PROBE FAILURE:** the first additive `2`-case run exits `1`
   with `2 failed` because PostgreSQL truncates `application_name` to 63 bytes
   and the test queried an overlong exact prefix. Only the test application
   prefix was shortened. Production logic and secure assertions were
   unchanged; the rerun passes `2/2` and observes `Lock/advisory`.
3. **OUTPUT CAPTURE RERUN:** the first `37`-case command printed all 37 progress
   dots but its final summary was not retained by the command transport. The
   exact unchanged command was rerun and authoritatively records
   `37 passed`, exit `0`.

## Docker cleanup

Only Compose project `ve-p5-review-freshness-remediation-3` was operated.

- `down -v --remove-orphans`: exit `0`;
- filtered task container inventory: empty;
- filtered task network inventory: empty;
- filtered task volume inventory: empty;
- identical cleanup replay: exit `0`;
- loopback port `62943` bind probe: free;
- unknown processes stopped: none;
- unfiltered Docker inventory or cleanup: never used.

The removed test container/network and synthetic database are intentionally
ephemeral and reproducible from migrations/tests; no task volume existed.

## Git and production boundary

The final pre-commit inventory is six files:

- one production file:
  `apps/api/src/visual_engineer_api/repositories/workspace.py`;
- one additive regression:
  `apps/api/tests/test_phase5_review_revision_freshness_remediation_3.py`;
- this ExecPlan and Evidence;
- `PLANS.md`; and
- `docs/status/project-status.md`.

Production-boundary inventory reports only the one Workspace repository file.
Migration diff is empty. The independent test and historical FAIL
plan/evidence/report are byte-identical to `a1dd0a9...`. Secret scan,
historical-file invariance, full diff inspection, `make format-check`, and
`git diff --check` exit `0`.

One local checkpoint uses subject:

`fix(review): serialize identical revision generation advances`

Its exact hash and post-commit clean-state reconciliation are reported in the
final handoff because a commit cannot embed its own resulting hash.

No remote, push, pull request, merge, tag, deploy, reset, force, stash, full
`make verify`, final aggregate, E2E, Chaos, broad Security/Eval, sealing, main
move, CreativeDeploy, sibling repository, Customer 0, LLM, Provider, API key,
or real credential action occurred.

## Verification classification

### Confirmed

- The pre-repair concurrent same-revision failure is generation `1 -> 3`.
- The post-lock forced reload changes the unchanged test to exact `1 -> 2`.
- Both identical callers return the same revision and observe final generation
  `2`.
- PostgreSQL advisory locking, atomic rollback, direct Decision/readiness
  fencing, generation-scoped replay, invalidation uniqueness, AuditEvent
  immutability, and both Review lock orders pass.
- Different concurrent revisions remain two distinct generation transitions.
- All authorized focused, migration, contract, static, build, and source
  invariance checks pass.
- Exact task Docker resources are removed and the task port is free.

### Inferred

- No unrelated Docker project was affected because every Docker command was
  constrained to the exact Compose project/label; global inventories were
  intentionally prohibited and not read.

### Not verified / not claimed

- independent single-Finding re-review of the new checkpoint;
- Security Gate PASS, sealing, main integration, push, pull request, merge,
  tag, deployment, or remote CI;
- full `make verify`, final aggregate, E2E/accessibility, full Chaos, broad
  Security/Eval, or production hardening;
- CreativeDeploy, Customer 0, sibling repositories, later slice, Phase 6,
  LLM, Provider, or real-customer behavior.

The exact next step is a fresh independent single-Finding re-review of
`VE-P5-REVIEW-RR-001` at the local remediation-3 checkpoint.
