# Phase 5 Review revision-freshness single-Finding re-review verification

## Identity and status

- Date: 2026-07-31 +08:00
- Repository: `/Users/danke/Developer/VisualEngineer`
- Main: `50dcc05ce48d042882bcdf199ae1bee662a83af6`
- Previous independent FAIL:
  `cce04d460a40416bc01f6ca2b44ee71948775c88`
- Remediation candidate:
  `efeecda57109ff8c3470f83a2aeb659e7ead31be`
- Candidate subject:
  `fix(review): fence decisions on revision freshness generation`
- Candidate parent: exact previous independent FAIL
- Branch:
  `audit/phase-5-review-revision-freshness-single-finding-rereview`
- Result:
  `PHASE 5 REVIEW REVISION FRESHNESS SINGLE-FINDING RE-REVIEW FAIL — REMEDIATION REQUIRED`
- Final `make verify`: **NOT RUN**
- Sealing: **NOT ELIGIBLE**

## Git preflight ledger

All required commands ran from the exact Developer repository before branch
creation or file modification.

| Command group                              | Exit | Result                                                   |
| ------------------------------------------ | ---: | -------------------------------------------------------- |
| `pwd -P`; `git rev-parse --show-toplevel`  |    0 | exact Developer repository                               |
| branch, HEAD, main                         |    0 | remediation branch, exact candidate, exact recorded main |
| status/diff/cached/untracked               |    0 | worktree, index, and untracked clean                     |
| remote/stash                               |    0 | both empty                                               |
| refs/log                                   |    0 | disclosed local heads; no tag or delivery ref            |
| three `git cat-file -t` probes             |    0 | all declared objects are commits                         |
| three `git show --format=fuller` probes    |    0 | hashes and subjects exact                                |
| main/candidate and FAIL/candidate ancestry |    0 | both ancestor checks pass                                |
| candidate parent                           |    0 | exact direct parent `cce04d...`                          |
| candidate subject                          |    0 | exact expected subject                                   |
| candidate stat/name-status/check           |    0 | 15 scoped files; no whitespace error                     |
| target audit branch existence              |    1 | expected absent                                          |
| branch creation and post-switch checks     |    0 | exact candidate and clean state                          |

No remote, stash, tag, merge, push, pull request, deployment, or unexplained
candidate identity was found.

## Test integrity and hashes

The original independent test and three historical FAIL documents have
identical Git blobs at the FAIL checkpoint and candidate. The test contains no
skip, xfail, or warning filter.

| Test                                       | Git blob                                   | SHA-256                                                            |
| ------------------------------------------ | ------------------------------------------ | ------------------------------------------------------------------ |
| original independent Finding               | `703d6d6d12710bc208c6d75cae5181c826d306bb` | `2b807bc181fcc2a89486bf44c97f5a2c0a1e2e0aeb034a5a07bfdf75e3ccd930` |
| permanent remediation matrix               | `be20ae20fce77a396077e3671c7089518c727e84` | `50b534792eddaa4bcdacb1f4eb03546a1a349687f1b22018f5cb33b708172fc9` |
| independent audit matrix before checkpoint | `cdcccfdf8265d73d41614a74e27a62f2b0ba5b69` | `438acf304880b11e5f57aa198da7c918b1dc96a5bf357d507e063bc46b5c7559` |

The final checkpoint blob/hash is reconciled again after documentation
formatting and commit.

## Read and review coverage

The reviewer read the repository operating contract and ExecPlan standard;
historical focused review/re-review plans, report, and evidence; remediation
plan/evidence; Project Status; Makefile, Python/Node package configuration,
Compose and relevant test/migration scripts; the candidate diff; migrations
0010/0011/0012; Review models/repository/service; trusted Workspace
registration; Validation trusted-manifest lock changes; original/permanent
tests; freshness generation/invalidation functions; Decision/readiness
insert guards; AuditEvent immutability; and focused governance documents.

The candidate introduces no Git, pull-request, tag, deployment, credential,
Provider, LLM, or later-phase authority.

## Migration graph

Static commands:

```text
uv run alembic -c apps/api/alembic.ini heads
uv run alembic -c apps/api/alembic.ini history --verbose
```

Result:

- exit `0`;
- one linear head: `20260730_0012`;
- `0012` directly revises `0011`;
- candidate migration is additive and its downgrade removes only its two
  triggers and four functions.

Dynamic populated and clean roundtrips were **NOT RUN** after the conclusive
single-Finding blocker.

## Minimum Finding matrix

Environment:

- Compose project: `ve-p5-review-freshness-rereview`
- PostgreSQL image/config: repository-declared `test-db`
- bind-probed port: `62941`
- database: real PostgreSQL `visualengineer_test`

Command:

```text
TEST_DATABASE_URL=postgresql+psycopg://visualengineer:visualengineer-test-local@127.0.0.1:62941/visualengineer_test \
uv run pytest \
  apps/api/tests/test_phase5_governed_final_review_focused_rereview.py \
  apps/api/tests/test_phase5_review_revision_freshness_remediation.py \
  --no-cov -vv
```

Result:

- exit `0`;
- `8 passed`;
- every collected case name was printed;
- one pre-existing TestClient deprecation warning.

This confirms the candidate rejects the original stale direct
Decision/readiness chain. It does not close concurrent replay idempotency.

## Independent PostgreSQL matrix

Final command:

```text
TEST_DATABASE_URL=postgresql+psycopg://visualengineer:visualengineer-test-local@127.0.0.1:62941/visualengineer_test \
uv run pytest \
  apps/api/tests/test_phase5_review_revision_freshness_single_finding_rereview.py \
  --no-cov -s -vv
```

Final result:

- exit `1`;
- `10 passed, 1 failed`;
- sole failure:
  `test_audit_concurrent_duplicate_revision_replay_advances_once`;
- one pre-existing TestClient warning.

Passing database facts:

- committed trusted revision:
  generation `1 -> 2`, one invalidation, one invalidation event, historical
  ready row preserved, effective readiness `stale`, old keyed replay `409`;
- forced commit failure:
  tentative generation `2`, then rollback leaves revision unchanged,
  generation `1`, invalidation/event `0/0`;
- out-of-band stale Decision repository writes:
  approve/reject SQLSTATE `55000`, `0` Decision rows, `0` ready rows;
- `changes_requested`:
  API `422`; PostgreSQL SQLSTATE `22001`; `0` Decision rows;
- direct stale ready:
  SQLSTATE `55000`; `0` ready rows;
- approve-first lock order:
  revision transaction waits on advisory `Lock`, approve commits first, later
  revision produces generation `2`, one invalidation/event, and no ready row;
- revision-first lock order:
  approval waits on advisory `Lock`, revision commits generation `2`, approval
  returns `review_generation_mismatch`, and Decision/ready counts are `0/0`;
- invalidation AuditEvent:
  direct update and delete each fail with SQLSTATE `55000`.

## Blocking concurrent replay evidence

Test:

`test_audit_concurrent_duplicate_revision_replay_advances_once`

Trigger:

- two authenticated trusted registration transactions report the same new
  revision for one existing Handle;
- an audit-only synchronization point makes both transactions reach the
  production initial unlocked lookup before either proceeds to the shared
  revision mutex.

Expected ledger:

```text
initial_generation=1
current_generation=2
generation_delta=1
invalidation_rows=1
invalidation_events=1
decision_rows=0
ready_rows=0
```

Actual ledger on every deterministic run:

```text
initial_generation=1
current_generation=3
generation_delta=2
invalidation_rows=1
invalidation_events=1
decision_rows=0
ready_rows=0
both registration outcomes = same changed revision
```

The corrected expanded matrix failed once, two focused invocations then
failed unchanged, and the final complete audit matrix failed at the same
assertion. Each authoritative failure exits `1`.

One invalidation/event prevents duplicate append-only history, but it does not
make the extra generation advance acceptable. The resulting gap violates the
explicit idempotency and exact-generation acceptance condition.

## Static correlation

The trusted writer:

1. performs an unlocked Handle lookup;
2. acquires the advisory revision mutex using that Handle ID;
3. performs `SELECT ... FOR UPDATE` in the same SQLAlchemy Session;
4. compares the ORM Handle revision with the payload; and
5. invokes `bump_review_freshness_repository_handle` when they differ.

The repository locked lookup does not request a forced refresh of an
already-loaded identity. The dynamic concurrency ledger confirms that the
waiting transaction can make its change decision from the pre-wait revision.

This is a narrow root-cause correlation, not a production repair.

## First failures and corrections

1. **AUDIT FORMAT FAILURE:** first Ruff format check exited `1`; only the new
   audit test was mechanically formatted.
2. **INVALID EXPANDED AUDIT ATTEMPT:** first expanded run was
   `5 passed, 6 failed`. Three failures queried invalidation by Package ID as
   though it were the invalidation primary key. Two expected a later
   constraint SQLSTATE even though `changes_requested` exceeds the
   16-character column. These five audit-test assertions were corrected
   without changing a secure expectation or production code.
3. **AUDIT MYPY FAILURE:** one redundant `cast(str, ...)` produced exit `1`;
   only that cast was removed. Ruff format/lint and mypy then passed.
4. **INVALID CLOSEOUT PATH:** one Ruff closeout command misspelled the new
   audit-test path and reported `E902`; it inspected no file and changed
   nothing. The exact-path Ruff format/lint and mypy rerun passed.
5. **PRODUCTION SECURITY FAILURE:** the concurrent identical-revision case
   remained the sole failure after audit corrections and on all unchanged
   deterministic reruns.

## Stopped matrices and Final Gate

Because invalidation replay is non-idempotent:

- focused Review/FR-002/003/004/005 `28/28`: **NOT RUN**
- affected Workspace/Validation `37/37`: **NOT RUN**
- populated and clean migration roundtrips: **NOT RUN**
- contracts, repository-wide format/lint/typecheck/build: **NOT RUN**
- full source-invariance harness: **NOT RUN**
- final `make verify`: **NOT RUN**
- E2E/accessibility/Security/Eval/Chaos: **NOT RUN**
- Final Gate Docker cleanup probe: **NOT ELIGIBLE**
- sealing commit: **NOT ELIGIBLE**

Implementer evidence for those commands was not promoted into this
independent result.

## Audit-owned cleanup

Only the exact project was operated:

```text
COMPOSE_PROJECT_NAME=ve-p5-review-freshness-rereview \
TEST_POSTGRES_PUBLISHED_PORT=62941 \
docker compose --profile test down -v --remove-orphans
```

Results:

- cleanup exit `0`;
- filtered container inventory: empty, exit `0`;
- filtered network inventory: empty, exit `0`;
- filtered volume inventory: empty, exit `0`;
- identical cleanup replay: exit `0`;
- bind probe on `127.0.0.1:62941`: exit `0`.

No unfiltered Docker inventory or cleanup command was used. No unknown
process or port owner was stopped.

## Production and external-action boundaries

- Reviewer production-code modification: none.
- Candidate-to-worktree production-path diff:
  `git diff --exit-code efeecda... -- apps/api/alembic apps/api/src apps/runner/src apps/web/src packages/runner-protocol/src packages/api-contract scripts compose.yaml infra`,
  exit `0`, empty.
- Original independent and permanent remediation test diff from the candidate:
  exit `0`, empty.
- Reviewer file inventory: one audit test, one ExecPlan, one audit report, one
  Evidence file, `PLANS.md`, and Project Status only.
- Source/canonical Workspace mutation by denial paths: none observed.
- Main remains `50dcc05ce48d042882bcdf199ae1bee662a83af6`.
- Remote/push/pull request/merge/tag/deploy: none.
- CreativeDeploy/sibling repositories/Customer 0: not accessed.
- LLM/Agents SDK/Provider/credentials/real customer repository: not used.

The audit test's final pre-checkpoint Git blob is
`cdcccfdf8265d73d41614a74e27a62f2b0ba5b69`; its SHA-256 is
`438acf304880b11e5f57aa198da7c918b1dc96a5bf357d507e063bc46b5c7559`.
The exact audit-only checkpoint hash is reported administratively after
commit.

## Disposition

### Confirmed

- The candidate closes stale direct Decision/readiness insertion and normal
  revision/approve lock ordering.
- Concurrent identical trusted revision replay advances generation twice.
- The replay defect is stable and violates an explicit single-Finding PASS
  condition.
- Audit-owned Docker resources are removed exactly.

### Inferred

- Static ORM identity behavior is the narrow correlation for the observed
  double bump; no production repair was attempted.

### Not verified

- `28/28`, `37/37`, migration roundtrip, full static/build/invariance gates,
  final `make verify`, E2E, accessibility, Security, Eval, Chaos, or sealing.
- Remote CI, main integration, delivery, deployment, CreativeDeploy, Customer
  0, later slice, Phase 6, or production hardening.

**PHASE 5 REVIEW REVISION FRESHNESS SINGLE-FINDING RE-REVIEW FAIL — REMEDIATION REQUIRED**
