# Phase 5 Validation Suites Targeted Remediation 1 Verification

- Date: 2026-07-30 +0800
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `fix/phase-5-validation-suites-remediation-1`
- Main baseline: `f547091307c52df8f20fc69bac4b4826cbbc74ad`
- Implementation candidate: `10399722e37f3209fa08e5e7edc25f31b429aaad`
- Focused-review FAIL checkpoint:
  `d325fa197e1fdad2c522fdf76f11b738682a86ca`
- Audit test SHA-256 before remediation:
  `47d9623ce5aab2e0de18e14fc473970f828c312f2d27ad167574be72c0bb350d`
- Credential handling: all local test credentials and generated Runner tokens
  are redacted from this record.
- Evidence status:
  `PHASE 5 SUITES TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`

This is implementer remediation evidence for only `VE-P5-SUITES-FR-001` and
`VE-P5-SUITES-FR-002`. It is not an independent review, Security Gate PASS,
sealing decision, main-integration authorization, Customer 0 authorization,
or later-phase authorization.

## Exact preflight

| Check                                | Result                                                                                     |
| ------------------------------------ | ------------------------------------------------------------------------------------------ |
| repository root                      | exact Developer repository                                                                 |
| starting branch / HEAD               | `audit/phase-5-validation-suites-focused-max` / `d325fa197e1fdad2c522fdf76f11b738682a86ca` |
| exact parent                         | `10399722e37f3209fa08e5e7edc25f31b429aaad`                                                 |
| merge-base with main                 | exact main `f547091307c52df8f20fc69bac4b4826cbbc74ad`                                      |
| implementation parent                | exact main                                                                                 |
| audit delta                          | review plan/report/evidence/status and preserved audit test only                           |
| initial worktree/index/untracked     | clean / clean / none                                                                       |
| remote/stash/tag/lock/extra worktree | none / none / none / none / none                                                           |
| remediation branch                   | created directly from focused-review checkpoint                                            |
| historical migration `0008`          | unchanged                                                                                  |

No remote, push, merge, pull request, tag, main movement, or external
repository access occurred.

## Preserved pre-fix Findings

The unchanged focused-review file ran against real PostgreSQL in the exact
project `ve-p5-suites-remediation-1`, with its test database published on a
unique loopback port.

| Finding               | Test                                         | First result                         | Stable focused reruns                         | Exit     |
| --------------------- | -------------------------------------------- | ------------------------------------ | --------------------------------------------- | -------- |
| `VE-P5-SUITES-FR-001` | same Grant, new idempotency key              | `(201, 1, 2, 1, 2)`                  | `3/3` failed with the same secure expectation | `1` each |
| `VE-P5-SUITES-FR-002` | injected successful summaries, zero Evidence | `(200, "succeeded", "succeeded", 0)` | `3/3` failed with the same secure expectation | `1` each |

The combined first run was `2 failed`, exit `1`. The original failure
observations remain preserved in the historical focused-review report and
test. The audit test was not edited.

## Repair boundary

### `VE-P5-SUITES-FR-001`

- Execution Grant policy and hash now bind the immutable Suite-definition
  digest, root/source Suite Run IDs, exact attempt number, and one allowed
  Suite Run.
- A root Grant has attempt `1` and no source/root reference. A retry Grant
  names the immediate terminal non-success source; the server derives the
  common root and next attempt.
- PostgreSQL enforces one Suite Run per Grant, one Run per root/attempt, exact
  root/retry checks, and one active root or retry authority for the same
  baseline/source.
- Grant and baseline authority are locked and rechecked. Exact idempotency
  replay converges; a different key, concurrent consumer, expired/revoked
  Grant, stale baseline, or mismatched lineage fails closed.
- Suite child budget is the two catalog steps for the one authorized attempt,
  not the product of all possible Suite attempts.

### `VE-P5-SUITES-FR-002`

- Successful aggregation re-queries the exact source-owned catalog definition
  and locked Suite step, Validation Run, Job/spec/result, Attempt, Lease,
  lineage Grant/policy hash, completed Permit, and immutable Evidence.
- Evidence identity, output, redaction/truncation, cleanup, zero artifacts,
  execution-envelope fields, Permit sequence/digest, and evidence digest are
  matched and recomputed before success.
- Aggregate references are server-built in catalog order and include exact
  Run/Job/Runner/Attempt/Lease/Grant/Evidence IDs plus the Evidence digest and
  reuse marker.
- PostgreSQL rejects illegal transitions, step-definition injection,
  missing/foreign/mismatched successful step proof, incomplete Suite success,
  and missing/duplicate/reordered/stale aggregate references. SQL comparisons
  use null-safe `IS DISTINCT FROM` semantics.
- `ValidationSuiteResult` stores explicit Suite/root/Run/Grant/definition/
  revision/Checkpoint/policy/attempt/budget and ordered Runner/Profile/
  Evidence bindings.

## First implementation and verification failures preserved

| Stage                                 | First failure                                                                                                      | Narrow correction                                                                                                                | Current result                 |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Ruff                                  | unused `ValidationRun` import                                                                                      | removed unused import                                                                                                            | pass                           |
| migration upgrade 1                   | old Suite trigger blocked lineage backfill                                                                         | replace triggers around additive backfill                                                                                        | pass                           |
| migration upgrade 2                   | Grant immutability trigger blocked policy backfill                                                                 | replace immutable trigger around backfill                                                                                        | pass                           |
| migration upgrade 3                   | reserved SQL alias                                                                                                 | renamed alias                                                                                                                    | pass                           |
| migration upgrade 4                   | reserved SQL `references` alias                                                                                    | renamed alias                                                                                                                    | pass                           |
| migration upgrade 5                   | SQLAlchemy parsed a PL/pgSQL colon literal as a bind                                                               | used SQL concatenation                                                                                                           | pass                           |
| evolved local `0009` downgrade        | newly added optional index absent in the already-migrated disposable database                                      | null-safe `IF EXISTS` downgrade for newly evolved objects                                                                        | pass                           |
| first full migration-check invocation | populated test data made historical `0006` reject a downgrade to the pre-Validation Permit operation set; exit `2` | classified as an invalid environment attempt; removed only the exact disposable project and used a fresh empty migration project | fresh base/head/base/head pass |
| post-hardening retry control          | aggregate trigger compared reused Evidence to the retry Grant rather than the original child Grant                 | derive reference Grant from the bound child Validation Run                                                                       | `12/12` pass                   |
| first Web typecheck                   | generated contract made lineage/result bindings required in fixtures                                               | updated typed fixtures only                                                                                                      | pass                           |
| first Web test                        | retry fixture still described root authority                                                                       | bind fixture to failed source/root/attempt `2`                                                                                   | `47/47` pass                   |
| first concurrency harness             | the fixture Session retained a transaction while worker Sessions waited                                            | close the fixture transaction before starting workers                                                                            | bounded two-session pass       |

The interrupted first concurrency harness was a test-fixture transaction
ownership issue, not a production PASS. The permanent test uses independent
PostgreSQL Sessions after explicitly closing fixture setup.

## Focused PostgreSQL matrix

| Boundary                                        | Current result                                                                                                                                                                                                        |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| unchanged focused-review tests                  | `2/2` pass                                                                                                                                                                                                            |
| original Suite controls                         | `10/10` pass; retry control also asserts exact-key replay and different-key denial                                                                                                                                    |
| permanent remediation tests                     | same-key concurrent replay, different-key single consumption, revoked/expired/stale authority, foreign/mismatched Run/Job/Attempt/Lease/Evidence proof, definition injection, and malformed aggregate references pass |
| combined focused selection                      | `19/19` pass including the final retry-replay assertions                                                                                                                                                              |
| Protocol and focused Runner executor            | `12/12` pass                                                                                                                                                                                                          |
| exact/plus-one aggregate output                 | existing parameterized control pass                                                                                                                                                                                   |
| Suite timeout/cancel/fail-fast/cleanup recovery | existing controls pass                                                                                                                                                                                                |

Each rejected authority or proof mutation asserts unchanged counts across
Suite Run, Suite step, child Validation Run, Runner Job, Attempt, Permit,
Suite Result, Evidence, and audit event tables. The canonical Workspace
fingerprint remains unchanged across each denial.

## Migration and contracts

| Command                                             | Result                                             |
| --------------------------------------------------- | -------------------------------------------------- |
| `alembic downgrade 0008`                            | exit `0`                                           |
| `alembic upgrade 0009`                              | exit `0`                                           |
| repeated downgrade/upgrade on disposable PostgreSQL | exit `0`                                           |
| fresh `make migration-check`                        | exit `0`; base → head → base → head                |
| `make contracts`                                    | exit `0`; generated OpenAPI and TypeScript updated |
| `make contracts-check`                              | exit `0`; no drift                                 |
| strict Ruff and mypy after schema/service/tests     | exit `0`; 96 source files                          |

The final base/head/base/head migration check remains recorded by the
repository gate. No historical migration was edited.

## Web and generated contract

| Command          | Result                                      |
| ---------------- | ------------------------------------------- |
| `pnpm typecheck` | exit `0` after typed fixture update         |
| `pnpm test`      | exit `0`; `47/47`                           |
| `pnpm build`     | exit `0`; production Next.js build complete |

## Related complete verification

| Boundary                            | Result                                                                                                                                |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| full backend/API                    | `147/147`, exit `0`                                                                                                                   |
| Runner security selection           | `111/111`, exit `0`                                                                                                                   |
| Phase 4 security-repair selection   | `86/86` plus Workspace API `14/14`, exit `0`                                                                                          |
| Workspace/Protocol static and tests | `64/64`; descriptor/static isolation pass                                                                                             |
| security audit regression           | `22/22`; historical independent FAIL remains preserved                                                                                |
| source invariance                   | 119 entries, 10 Git objects, 2 status records, 0 extension markers; pass                                                              |
| validation sandbox                  | Landlock, seccomp, fixed Profile pass/fail, bounded exit codes; pass                                                                  |
| Eval                                | 67 deterministic cases plus repository scanner `7/7`; pass                                                                            |
| format/lint/typecheck               | Ruff/Prettier/ESLint and strict mypy 96 files; pass                                                                                   |
| browser E2E                         | desktop + narrow `16/16`; source and canonical Workspace HEAD/status/tree unchanged                                                   |
| Workspace Chaos                     | atomic recovery and revoke concurrency pass; 3 stale leases fenced; no effective post-revoke side effect; source and `.git` unchanged |
| Docker cleanup                      | all exact remediation/final/E2E/Chaos project filters report 0 containers, 0 networks, 0 volumes                                      |
| focused audit hash                  | unchanged `47d9623ce5aab2e0de18e14fc473970f828c312f2d27ad167574be72c0bb350d`                                                          |

## Final aggregate

The first final aggregate used isolated projects and ports:

```text
COMPOSE_PROJECT_NAME=ve-p5-suites-remediation-1-final
TEST_POSTGRES_PUBLISHED_PORT=35650
E2E_COMPOSE_PROJECT_NAME=ve-p5-suites-remediation-1-final-e2e
E2E_DB_PORT=35651 E2E_API_PORT=38651 E2E_WEB_PORT=39651
WORKSPACE_CHAOS_COMPOSE_PROJECT_NAME=ve-p5-suites-remediation-1-final-chaos
WORKSPACE_CHAOS_DB_PORT=35652 WORKSPACE_CHAOS_API_PORT=38652
make verify
```

It passed contracts, format, lint, typecheck, Python `248/248` at `83.27%`
coverage, Web `47/47`, build, configuration, migration, Phase 4 audit, source
invariance, and repair checks. The E2E image build then failed with exit `2`
while fetching an anonymous `ghcr.io` token: the registry connection ended in
`EOF`. This was an external image-registry failure, not a product-test failure.
The failed E2E/Chaos project filters had zero residue.

The single allowed full rerun reused the exact local E2E and Chaos images
built from the completed source and already exercised by the pre-final real
browser/Chaos checks:

```text
COMPOSE_PROJECT_NAME=ve-p5-suites-remediation-1-final-rerun
TEST_POSTGRES_PUBLISHED_PORT=35653
E2E_COMPOSE_PROJECT_NAME=ve-p5-suites-remediation-1-e2e
E2E_DB_PORT=35640 E2E_API_PORT=38640 E2E_WEB_PORT=39640 E2E_SKIP_BUILD=1
WORKSPACE_CHAOS_COMPOSE_PROJECT_NAME=ve-p5-suites-remediation-1-chaos
WORKSPACE_CHAOS_DB_PORT=35641 WORKSPACE_CHAOS_API_PORT=38641 CHAOS_SKIP_BUILD=1
make verify
```

The rerun exited `0` with:

- Python/API/Runner/Protocol `248/248`, `83.27%` coverage;
- Web `47/47`, strict typecheck, lint, format, and production build;
- migration base → head → base → head and generated-contract drift checks;
- Phase 4 security audit `22/22` with its historical FAIL preserved;
- Phase 4 repair `86/86` plus Workspace API `14/14`;
- real browser E2E desktop/narrow `16/16`;
- Workspace Chaos atomic pre/post rename recovery, revoke concurrency, three
  stale leases fenced, zero effective post-revoke side effects, and unchanged
  source repository/`.git`;
- Workspace/Protocol `64/64`, Runner security `111/111`, repository scanner
  `7/7`, Eval 67, validation sandbox, source invariance, secret/static security,
  and final `git diff --check`.

## Final reconciliation

- The focused audit file hash remains
  `47d9623ce5aab2e0de18e14fc473970f828c312f2d27ad167574be72c0bb350d`.
- `main`, implementation candidate, and focused-review refs remain unchanged.
- All exact task-owned Compose project filters report zero containers,
  networks, and volumes after cleanup.
- Credential values and generated Runner tokens remain redacted.
- One local checkpoint uses
  `fix(validation): enforce suite grant lineage and trusted aggregation`;
  its final hash is recorded in the handoff after commit creation.

This is local implementer verification only. It does not change the historical
focused-review FAIL or declare Security Gate PASS, sealing, main integration,
Customer 0, or a later phase.
