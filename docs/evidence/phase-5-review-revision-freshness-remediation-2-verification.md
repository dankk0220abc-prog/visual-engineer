# Phase 5 final review revision freshness remediation 2 verification

## Disposition

This is implementer evidence for the single blocking Medium Finding
`VE-P5-REVIEW-RR-001`. It preserves the independent focused re-review FAIL and
does not announce Gate PASS, sealing, main integration, Git delivery, a later
slice, Customer 0, or Phase 6.

Successful handoff label:

`PHASE 5 REVIEW REVISION FRESHNESS REMEDIATION COMPLETE — READY FOR INDEPENDENT SINGLE-FINDING RE-REVIEW`

## Exact baseline and intake

- Repository and top level:
  `/Users/danke/Developer/VisualEngineer`
- Local main:
  `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Previous remediation candidate:
  `3eddb9623550227a30013df6dbc6dc7a17d5315c`
- Independent re-review FAIL checkpoint and remediation base:
  `cce04d460a40416bc01f6ca2b44ee71948775c88`
- Intake re-review branch:
  `audit/phase-5-governed-final-review-reaudit-max`
- Remediation branch:
  `fix/phase-5-review-revision-freshness-remediation-2`
- Ancestry:
  `3eddb962...` is the exact parent of `cce04d...`; the ancestor probe passed.
- Audit checkpoint scope: only the permanent independent test and
  audit/governance evidence; no production code.
- Intake worktree/index/untracked: clean.
- Remote/stash/tag/Git lock: none.
- Worktrees: one exact repository worktree.
- The remediation branch did not exist and was created without overwrite.
- Original independent test: byte-identical to the FAIL checkpoint; no
  deletion, loosened assertion, skip, or xfail.

All commands in this remediation used the exact repository as working
directory. No CreativeDeploy or sibling repository path was accessed. No
reset, stash, force, remote, push, pull request, merge, tag, Customer 0, LLM,
production credential, or delivery action occurred.

## Original Finding extracted from source

Permanent test:

`test_p5_review_rereview_001_repository_revision_change_rejects_database_ready_chain`

Trigger order:

1. create a successful trusted Suite and immutable Review Package;
2. preserve the Package freshness generation, Workspace revision/tree, and
   Evidence digests;
3. mutate the Repository Handle revision in PostgreSQL and commit;
4. confirm the API reports `stale` /
   `source_revision_changed`, while the independent reproduction deliberately
   observes no accepted freshness-generation transition or invalidation row;
5. attempt a direct canonical old-generation `approve` Decision insert;
6. if accepted, attempt a direct canonical old-generation `ready` insert; and
7. assert zero accepted write, approved Decision, ready row, readiness-success
   event, delivery authority, or Workspace/Evidence mutation.

Expected final database tuple:

```text
(decision_accepted, readiness_accepted, approved_decisions, ready_rows, readiness_events)
(False, False, 0, 0, 0)
```

Preserved pre-repair actual on two unchanged real-PostgreSQL runs:

```text
(True, True, 1, 1, 0)
1 failed
exit 1
```

The repeated identical result established a stable failure before production
repair.

## Root cause

Migration `20260730_0010` directly compared the trusted Repository Handle
revision/status before Decision and readiness inserts. Migration
`20260730_0011` replaced those insert guards while adding broader canonical
generation and digest controls, but omitted the direct revision-authority
comparison. The authenticated Runner registration writer also persisted a
Handle revision/status transition without advancing Review freshness.
Finally, the Review service returned a matching idempotency replay before
validating current generation and freshness.

The API read path could therefore derive `stale`, but that derived response did
not close the database write boundary.

## Repair

- Additive Alembic revision `20260730_0012` installs:
  - `lock_review_revision_authority(uuid)`, a transaction-level advisory mutex
    shared by trusted revision changes and Review writes;
  - `bump_review_freshness_repository_handle(uuid, text)`, which selects each
    affected immutable Package scope once and calls the existing
    `bump_review_freshness_scope` transaction function; and
  - before-insert Decision and readiness guards that lock and compare the
    trusted Handle revision/status with the frozen Package.
- The authenticated Runner repository registration service is the sole
  production writer of `RepositoryHandle.current_revision`. On a real
  revision or available-status transition it acquires the shared mutex and
  Handle lock, flushes the authority change, advances all affected scopes, and
  commits revision, generation, invalidation, and invalidation AuditEvent
  together.
- Exact unchanged registration does not advance generation.
- An arbitrary direct Handle table mutation is not treated as an accepted
  trusted registration event; the independent database insert guards still
  fail closed against that drift.
- Decision and readiness services acquire the same mutex and trusted Handle
  lock before Package/scope validation.
- Decision generation/freshness validation now precedes idempotency replay, so
  an old-generation exact key cannot return its historical Decision.
- The pure post-commit response reconstructs trusted Suite evidence without
  reacquiring write locks. Write validation retains its locks; this avoids a
  lock-order deadlock without weakening the write boundary.

No persistent API field or HTTP schema changed. The Third Slice terminal
Decision domain remains exactly `approve` / `reject`; `changes_requested`
continues to return `422`.

## Permanent regression coverage

New test module:

`apps/api/tests/test_phase5_review_revision_freshness_remediation.py`

Coverage:

- trusted revision registration advances generation exactly `+1`;
- old Package becomes durably stale;
- old effective ready is invalidated;
- one Package invalidation and one immutable invalidation AuditEvent;
- repeated identical registration adds no generation or event;
- unchanged revision adds no false generation;
- old-generation exact-key replay returns `409`;
- direct old-revision approve and reject both fail in PostgreSQL;
- direct old-revision `ready` fails in PostgreSQL;
- concurrent revision change/approve is serialized into a real order, with at
  most one historical Decision and no stale ready row;
- a new generation requires a distinct new Package and Decision;
- the old Decision remains history and cannot affect the new generation;
- checkpoint/tree/policy/Grant/blocker freshness remains covered by the
  unchanged focused matrix;
- Workspace source/tree and Evidence digests remain unchanged; and
- delivery Grants and Review authorization fields remain false.

## Focused PostgreSQL results

Task-owned PostgreSQL:

- Compose project:
  `ve-p5-review-revision-remediation-2`
- Published test port: `62881`
- Unknown port owners stopped: none.
- Canonical Compose services modified: none.

Original Finding plus new regression module after repair:

```text
8 passed
exit 0
```

Focused Review API plus original, prior-remediation, focused-audit,
focused-re-review, and new revision-freshness modules:

```text
28 passed
exit 0
```

This matrix includes the unchanged `FR-002`, `FR-003`, `FR-004`, and `FR-005`
non-regressions, the original `VE-P5-REVIEW-RR-001`, Decision/readiness
database enforcement, concurrency, idempotency, blocker summary, canonical
digest, and append-only AuditEvent cases.

Affected Workspace and Validation Suite modules:

```text
37 passed
exit 0
```

Clean migration pytest:

```text
1 passed
exit 0
```

The only warning is the pre-existing Starlette TestClient/httpx deprecation
warning.

## Migration and contracts

- Additive revision:
  `20260730_0012_fence_review_revision_freshness`
- Historical migration modified: no.
- Populated database `0012 -> 0011 -> 0012`: exit `0`.
- Clean database `base -> head -> base -> head`: exit `0`, executed twice by
  `scripts/run-migration-check.sh`.
- Clean migration pytest: `1/1`.
- `make contracts-check`: exit `0`, no OpenAPI/generated TypeScript drift.
- Downgrade removes only the two new insert guards and the two new helper
  functions.
- Existing rows remain immutable history; no backfill or destructive rewrite
  is required.

## Static, build, and invariance

- Ruff format for all Python sources: pass.
- Ruff and ESLint lint: pass.
- strict mypy: `107` source files, no issues.
- TypeScript typecheck: pass.
- Web production build: pass, including `/reviews`.
- Source invariance:
  - source entries compared: `119`;
  - source Git objects compared: `10`;
  - source status records: `2`;
  - extension markers: `0`;
  - status: `PASS`.
- Final Prettier/format check: pass.
- Final `git diff --check`: pass.

No full `make verify`, full E2E, Chaos, Security, Eval, browser/accessibility
expansion, or final aggregate was run, as required by the remediation scope.

## Rejection and no-side-effect evidence

For stale revision/generation, direct database, replay, and concurrent denial
paths, the permanent tests confirm:

- new approved Decision: `0`;
- effective `approved_ready`: `0`;
- readiness-success event: `0`;
- delivery Grant or Git/deployment authority: `0`;
- duplicate invalidation AuditEvent: `0`;
- duplicate Package invalidation: `0`;
- Workspace/source mutation: `0`;
- Evidence mutation: `0`; and
- Git/PR/merge/tag/deployment action: `0`.

When real ordering permits approval before the trusted revision transaction,
that Decision remains immutable historical evidence; the same transaction that
accepts the later revision advances generation, invalidates the Package, and
prevents any effective ready result. When revision wins first, approval fails
closed.

## First failures and invalid attempts

1. **PRESERVED SECURITY REPRODUCTION:** two pre-repair runs each exited `1`
   with the same stale database-ready tuple
   `(True, True, 1, 1, 0)`.
2. **CONCURRENCY LOCK ORDER:** the first expanded focused run was
   `26 passed, 2 failed` with PostgreSQL deadlocks in existing concurrent
   approve/reject cases; a narrow run retained one deadlock. A shared advisory
   revision mutex established one authority order, and the pure response path
   stopped reacquiring write locks. The narrow matrix then passed `3/3` and
   the full focused matrix passed `28/28`.
3. **INVALID POPULATED FULL-DOWNGRADE ATTEMPT:** after proving populated
   `0012 -> 0011 -> 0012`, one attempt to continue through historical
   `0011 -> 0010` encountered an old invalidation-reason constraint. It did
   not test the new migration. No historical migration was changed; the exact
   task database was recreated and the clean full migration check passed.
4. **INVALID TEST ORDER:** one combined affected-test invocation ran the
   migration pytest after multi-step Validation rows and reported
   `37 passed, 1 failed` in the historical `0008` downgrade constraint. The
   task database was recreated; migration pytest passed `1/1` on clean state,
   then the same affected business tests passed `37/37`.
5. **DOCUMENT FORMAT:** the first format check passed Ruff but identified the
   unfinished new ExecPlan in Prettier. After the evidence/governance updates,
   the final complete format check passed.
6. **INVALID READ-ONLY PROBE:** one migration-current probe used the wrong
   test password and an unscoped read-only Compose status command. It exited
   `1` and changed no container or database. Exact task labels and the
   repository-declared test credential were then used for all authoritative
   checks.

## Closeout

Only the exact task-owned PostgreSQL Compose project is removed at closeout.
Its post-cleanup container/network/volume inventory is zero and port `62881`
is free. The pre-existing canonical Compose project was not stopped,
recreated, migrated, or written.

Local main remains
`50dcc05ce48d042882bcdf199ae1bee662a83af6`. The independent test and
historical FAIL/evidence are unchanged. The one local checkpoint uses subject:

`fix(review): fence decisions on revision freshness generation`

## Verification ledger

### Confirmed

- The trusted revision transition advances freshness generation monotonically
  and commits invalidation/AuditEvent in the same transaction.
- Direct database Decision/readiness inserts cannot bypass frozen revision and
  current-generation fencing.
- Exact keyed replay is generation-scoped.
- Old Decisions/readiness remain history but have no current effect.
- The unchanged independent reproduction and all authorized focused
  regressions pass.
- Review approval/readiness still grants no Git or deployment authority.

### Inferred

- None used for the completion disposition.

### Not verified / not claimed

- Independent single-Finding re-review or Gate PASS
- sealing, main integration, push, pull request, merge, tag, or deployment
- full aggregate, full E2E, Chaos, Security, Eval, or browser expansion
- remote CI
- hostile multi-tenant PostgreSQL role isolation or production hardening
- Customer 0, later slice, Phase 6, LLM, or production credentials

The next authorized step is an independent single-Finding re-review of the
exact local remediation checkpoint. No broader authorization is implied.
