# Phase 5 Review revision-freshness final independent re-review verification

- Date: 2026-07-31 (Asia/Shanghai)
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch:
  `audit/phase-5-review-revision-freshness-final-rereview`
- Candidate:
  `7450d4665d682db808692347860a602809bfa080`
- Main:
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Finding: `VE-P5-REVIEW-RR-001`
- Decision: **PASS**
- Final aggregate: **PASS**, exit `0`
- Reviewer production changes: **none**
- Remote CI: **NOT VERIFIED**

## Disposition

Concurrent identical trusted revision registration now reloads committed
PostgreSQL state after the existing transaction-level revision-authority lock.
Both callers return the same revision and final generation, and the one real
authority transition advances generation exactly once.

Final label:

`PHASE 5 THIRD SLICE FINAL GATE PASS — SEALED AND AWAITING EXPLICIT USER AUTHORIZATION FOR LOCAL FAST-FORWARD MAIN`

## Evidence boundary

This independent review decides only `VE-P5-REVIEW-RR-001`. It does not reopen
the design or disposition of `FR-002`, `FR-003`, `FR-004`, or `FR-005`.
Their existing tests run only as the required non-regression matrix.

Implementer evidence was used for navigation, not promoted into the verdict.
The decision below relies on current Git inspection, byte-identity checks,
source review, real PostgreSQL transactions, current-worktree gates, one
complete aggregate, and exact Docker cleanup.

## Git preflight

| Check                     | Confirmed result                                                |
| ------------------------- | --------------------------------------------------------------- |
| repository root           | exact `/Users/danke/Developer/VisualEngineer`                   |
| initial HEAD              | exact candidate `7450d466...`                                   |
| candidate subject         | `fix(review): serialize identical revision generation advances` |
| local main                | exact `50dcc05c...`                                             |
| object types              | candidate and main are commits                                  |
| clean state               | worktree, index, and untracked empty                            |
| ancestry                  | main is candidate ancestor and exact merge-base                 |
| candidate range           | seven commits, no merge commit                                  |
| remote/stash/tag          | empty                                                           |
| in-progress Git operation | none                                                            |
| target audit branch       | absent before creation                                          |
| branch creation           | direct from exact candidate, no force                           |

No reset, overwrite, stash, rebase, cherry-pick, merge, remote contact, or
delivery action occurred.

## Candidate and independent-test integrity

The remediation-3 production change is one locked query:

```text
SELECT RepositoryHandle ... FOR UPDATE
execution option: populate_existing=True
```

The trusted registration order remains:

1. resolve the existing Handle ID;
2. acquire `lock_review_revision_authority(handle_id)`;
3. lock and reload the Handle from PostgreSQL;
4. compare the committed revision/status with the request;
5. update and bump only for a real authority transition; and
6. commit revision, generation, invalidation, and AuditEvent together.

The independent file
`apps/api/tests/test_phase5_review_revision_freshness_single_finding_rereview.py`
has:

```text
SHA-256 438acf304880b11e5f57aa198da7c918b1dc96a5bf357d507e063bc46b5c7559
Git blob cdcccfdf8265d73d41614a74e27a62f2b0ba5b69
```

Those values match the preserved independent FAIL checkpoint
`a1dd0a9b68c73a45e4aa8b8754e51c385f3bad95`. The file, historical FAIL
Evidence, ExecPlan, and audit report were not edited, skipped, xfailed, or
weakened.

## Real PostgreSQL environment

- Compose project:
  `ve-p5-review-freshness-final-rereview`
- Image: repository-pinned PostgreSQL 17 test service
- Published loopback port: `62947`
- Database: `visualengineer_test`
- Pre-start filtered project resources: zero
- Port preflight: successful bind probe

No SQLite or persistence mock is acceptance evidence.

## Concurrent identical revision

The permanent remediation-3 test uses two independent SQLAlchemy Engines and
Sessions. A deterministic barrier aligns both initial reads, the first
transaction is held after acquiring the production lock, and
`pg_stat_activity` must observe the other backend waiting before release.

Current ledger:

```text
initial_generation=1
input_revisions=[bbbb...bbbb, bbbb...bbbb]
registration_outcomes=[
  [bbbb...bbbb, bbbb...bbbb, 2],
  [bbbb...bbbb, bbbb...bbbb, 2]
]
final_generation=2
invalidation_rows=1
invalidation_events=1
decision_rows=1
ready_rows=1
effective_ready=stale
wait_event_type=Lock
wait_event=advisory
```

Both requests therefore return the same requested/stored revision and the same
final generation. PostgreSQL generation is exact `1 -> 2`, not `3`. The
historical Decision and ready row remain immutable history; effective
readiness becomes stale exactly once.

The byte-unchanged independent reproduction separately records:

```text
initial_generation=1
current_generation=2
generation_delta=1
current_revision=eeee...eeee
registration_outcomes=[eeee...eeee, eeee...eeee]
invalidation_rows=1
invalidation_events=1
decision_rows=0
ready_rows=0
```

## Sequential and different-revision controls

- Sequential same-revision registration advances generation once and leaves it
  at `2`, with one invalidation and one invalidation AuditEvent.
- Two concurrent different revisions are both retained as real transitions:

```text
initial_generation=1
input_revisions=[bbbb...bbbb, cccc...cccc]
registration_outcomes=[
  [bbbb...bbbb, bbbb...bbbb, 2],
  [cccc...cccc, cccc...cccc, 3]
]
final_generation=3
invalidation_rows=1
invalidation_events=1
wait_event_type=Lock
wait_event=advisory
```

The repair does not incorrectly fold two real authority changes into one.

## Lock order and transaction atomicity

The byte-unchanged independent matrix confirms:

- approve-first: revision waits on PostgreSQL `Lock/advisory`; approval
  commits, revision then advances generation to `2`, creates one
  invalidation/event, and creates no ready row;
- revision-first: approval waits on PostgreSQL `Lock/advisory`, then returns
  `review_generation_mismatch`; generation is `2` and Decision/ready counts
  remain `0/0`;
- forced pre-commit failure: tentative generation `2` plus tentative
  invalidation/event are visible only inside the transaction; rollback leaves
  revision `aaaa...aaaa`, generation `1`, invalidation `0`, and AuditEvent
  `0`.

The post-lock comparison therefore uses committed database state, and
revision, generation, invalidation, and AuditEvent retain one transaction
boundary.

## Database fencing

| Boundary                               | Current result                           |
| -------------------------------------- | ---------------------------------------- |
| stale direct `approve` insert          | SQLSTATE `55000`, zero Decision/ready    |
| stale direct `reject` insert           | SQLSTATE `55000`, zero Decision/ready    |
| unsupported direct `changes_requested` | API `422`, PostgreSQL closed domain      |
| stale direct `ready` insert            | SQLSTATE `55000`, zero ready             |
| old-generation exact keyed replay      | HTTP `409`, `review_generation_mismatch` |
| AuditEvent `UPDATE`                    | SQLSTATE `55000`                         |
| AuditEvent `DELETE`                    | SQLSTATE `55000`                         |

Denied paths do not create a new Decision, readiness, invalidation event,
generation advance, or delivery authority.

## Focused test ledger

| Selection                                     | Exit |      Result |
| --------------------------------------------- | ---: | ----------: |
| remediation-3 identical/different concurrency |  `0` |  `2 passed` |
| unchanged independent single-Finding file     |  `0` | `11 passed` |
| original Finding plus remediation matrix      |  `0` |  `8 passed` |
| focused Review / `FR-002` through `FR-005`    |  `0` | `28 passed` |
| affected Workspace/Validation                 |  `0` | `37 passed` |
| clean migration pytest                        |  `0` |  `1 passed` |

The only test warning is the pre-existing Starlette TestClient/httpx
deprecation warning.

## Migration verification

Static Alembic inspection reports one head:
`20260730_0012`.

The populated task database contained:

```text
runners=1
repository_handles=1
audit_events=2
```

Populated `0012 -> 0011 -> 0012` exits `0`, and all three counts remain
`1 / 1 / 2`.

After recreating only the exact task-owned tmpfs test database:

- clean `base -> head -> base -> head`: exit `0`;
- final revision: `20260730_0012`;
- application tables: `30`;
- Validation step rows: `0`; and
- clean migration pytest: `1 passed`, exit `0`.

No migration or schema file changed during this review.

## Contracts, static gates, build, and invariance

| Command                        | Result                                              |
| ------------------------------ | --------------------------------------------------- |
| `make contracts-check`         | exit `0`, no generated drift                        |
| `make format-check`            | exit `0`, Ruff 143 files and Prettier pass          |
| `make lint`                    | exit `0`, Ruff and ESLint pass                      |
| `make typecheck`               | exit `0`, mypy 109 source files and TypeScript pass |
| `make build`                   | exit `0`, Next.js production build pass             |
| `make source-invariance-check` | exit `0`, status `PASS`                             |
| `git diff --check`             | exit `0`                                            |

Source invariance reports:

```text
source_entries_compared=119
source_git_objects_compared=10
source_status_records=2
extension_markers=0
```

## Complete aggregate

Exactly one complete aggregate was run with unique project names and
bind-probed official port overrides:

```text
make verify
exit=0
```

Material totals:

- Python/API/Runner/Protocol: `293 passed`, coverage `83.49%`;
- Web unit/component: `50 passed`;
- Playwright real stack: `16 passed`;
- Phase 4 security audit: `22 passed`;
- Workspace repair selection: `86 passed` plus Workspace API `14 passed`;
- Workspace Security: `64 passed`;
- Runner Security: `111 passed`;
- Review Security: `20 passed`;
- Eval: `74` deterministic cases plus scanner `7 passed`;
- Migration, Docker config, source invariance, Workspace Chaos, Validation
  Security, static security checks, and final `git diff --check`: pass.

Workspace Chaos reports atomic pre/post-rename recovery, stale-Lease fencing,
revocation concurrency, zero post-revocation side effects, exact discard, and
source/`.git` invariance.

## First failure preserved

One pre-aggregate migration-order attempt failed with exit `1`:

- the populated database from the `37/37` Validation matrix was incorrectly
  passed to the clean full-history roundtrip;
- downgrade `0008 -> 0007` correctly rejected those newer Validation rows
  while restoring the historical `step_id = 'fixture-contract'` constraint;
- a migration pytest immediately following the same non-clean state failed for
  the same reason.

This was an invalid clean-gate setup, not a candidate or Finding failure.
The populated target roundtrip had already passed. Only the exact audit-owned
tmpfs database was recreated; the unchanged clean roundtrip and migration
pytest then passed. No production, migration, or test file was modified.

## Docker cleanup

Exact projects:

- `ve-p5-review-freshness-final-rereview`
- `ve-p5-review-freshness-final-rereview-e2e`
- `ve-p5-review-freshness-final-rereview-chaos`

For each project:

```text
containers=0
networks=0
volumes=0
```

`down -v --remove-orphans` and an identical cleanup replay exit `0`. Ports
`62947`, `25447`, `28447`, `23447`, `25448`, and `28448` all pass a final bind
probe. No unfiltered Docker cleanup ran and no unknown process was stopped.

## Production and external-action boundaries

- Candidate-to-worktree production-path diff: empty.
- Reviewer production-code modification: none.
- Independent test hash after all verification: unchanged.
- Main remains
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`.
- No remote, fetch, push, pull request, merge, tag, deployment, delivery,
  CreativeDeploy, sibling repository, Customer 0, Provider, credential, or
  real-customer action occurred.
- The local sealing commit uses subject:
  `chore: seal phase 5 governed final review`.
- The resulting sealing hash and post-commit clean state are reported in the
  final handoff because a commit cannot contain its own object ID.

## Verification classification

### Confirmed

- Same-revision concurrency is exact `1 -> 2`, with equal revision/generation
  responses and one invalidation/AuditEvent.
- Different revisions remain exact `1 -> 3`.
- The second transaction really waits on PostgreSQL advisory locking and
  reloads committed state afterward.
- Sequential replay, both Review lock orders, forced rollback, direct database
  fencing, keyed replay fencing, and append-only AuditEvent behavior pass.
- Every required focused, migration, contract, static, build, invariance,
  aggregate, and cleanup gate passes.
- Reviewer production changes are zero.

### Not verified or authorized

- Remote CI, local main integration, push, pull request, tag, deployment,
  delivery, another slice, or Phase 6.

**VE-P5-REVIEW-RR-001 PASS**

**PHASE 5 THIRD SLICE FINAL GATE PASS — SEALED AND AWAITING EXPLICIT USER AUTHORIZATION FOR LOCAL FAST-FORWARD MAIN**
