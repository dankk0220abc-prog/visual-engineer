# Phase 2 Governed Read-Only Repository Intelligence ExecPlan

- Status: COMPLETE
- Started: 2026-07-26 (Asia/Shanghai)
- Working repository: `~/Developer/VisualEngineer`
- Foundation branch: `main`
- Foundation commit: `d136418158d9f5ffc4f2f8ba993ca48e837ed59b`
- Working branch: `feat/phase-2-readonly-repository-intelligence`
- Intended checkpoint message:
  `feat: add governed read-only repository intelligence`

## Goal

Deliver a real, durable, reviewable Phase 2 loop in which a local user creates
a Level 0 Run for an existing Task, snapshots only an allowlisted repository's
committed `HEAD`, reviews structured repository intelligence and a
deterministic plan, revises and submits that plan, and records one human
approve or reject decision without executing or modifying target code.

The batch also proves the boundary against an adversarial synthetic repository
and runs the complete read-only flow against the internal CreativeDeploy
Customer 0 repository, stopping its plan at `awaiting_plan_approval`.

## Current progress

- [x] 2026-07-26: Verified the supplied Foundation gate on `main`: exact
      commit, clean worktree, no remote, complete repository-local Git identity.
- [x] 2026-07-26: Confirmed the Phase 2 branch did not already exist and
      created `feat/phase-2-readonly-repository-intelligence`.
- [x] 2026-07-26: Read repository governance, product, architecture, security,
      ADR, evaluation, and Foundation ExecPlan documents.
- [x] 2026-07-26: Created this ExecPlan before cross-cutting implementation.
- [x] 2026-07-26: Inspected the complete backend, frontend, migration, contract, Docker,
      test, and CI implementation seams.
- [x] 2026-07-26: Implemented Run, RepositorySnapshot, Plan,
      ApprovalDecision, and AuditEvent.
- [x] 2026-07-26: Implemented the bounded committed-HEAD Repository Scanner and deterministic
      plan generator.
- [x] 2026-07-26: Implemented transactional Run/plan/revision/submit/decision/cancel APIs.
- [x] 2026-07-26: Regenerated OpenAPI and TypeScript contracts.
- [x] 2026-07-26: Extended the task console and added the Run review page.
- [x] 2026-07-26: Added adversarial fixture generation, 29 structured
      deterministic eval cases across two datasets, backend,
      frontend, migration, concurrency, and real-stack browser tests.
- [x] 2026-07-26: Added the optional API-only read-only Customer 0 Compose
      override and runbook.
- [x] 2026-07-26: Updated product, architecture, security, ADR, status,
      Customer 0, and runbook documentation.
- [x] 2026-07-26: Executed the CreativeDeploy read-only
      Task/Run/Snapshot/Plan flow and stopped at human approval.
- [x] 2026-07-26: Ran every mandatory local verification command and recorded
      exact results in the Phase 2 evidence.
- [x] 2026-07-26: Audited and staged the complete 75-file scope, created the
      local checkpoint, and passed post-commit `make verify`; final branch,
      remote, and worktree state are recorded in the handoff.

## Scope

- PostgreSQL schema and Alembic history for the five Phase 2 entities.
- Explicit Run and Plan state-transition policy with optimistic concurrency
  and transaction-safe final decisions.
- Typed, bounded Level 0 local-repository configuration.
- A read-only Git object scanner using fixed argument arrays, no shell, no
  hooks, no credentials, no network, and committed blob object IDs.
- Stable repository fingerprints and structured, content-minimizing facts.
- Deterministic plan creation and bounded human-editable revisions.
- Versioned `/api/v1` Run, Snapshot, Plan, decision, audit, and cancel APIs.
- Generated OpenAPI and TypeScript contract artifacts.
- Existing-console extensions for Run history, repository intelligence, plan
  review, explicit non-execution messaging, and audit timeline.
- Synthetic adversarial repository fixture and deterministic failure taxonomy.
- PostgreSQL, Vitest, Playwright, migration, contract, security, Docker, and
  Customer 0 verification.
- Documentation and one local Git checkpoint.

## Non-goals

- OpenAI Agents SDK, an LLM, embeddings, vector search, or model scoring.
- Generic shell, target-repository script execution, dependency installation,
  build, test, lint, formatter, generator, or dynamic import.
- Target-repository writes, checkout/switch/add/commit/reset/clean/stash,
  worktrees, rollback execution, branch publication, PR, merge, or deployment.
- Network repository access, GitHub/Figma credentials, authentication,
  multi-tenancy, queues, workers, or production exposure.
- Treating plan approval as execution authority.
- Treating CreativeDeploy as an external enterprise customer or claiming
  productivity, adoption, production-quality, or production-deployment data.

## Constraints and safety

- CreativeDeploy is strictly read-only. Its dirty and untracked content must
  not be read, run, imported, installed, formatted, cleaned, or modified.
- Repository facts come from the current committed `HEAD`; working-tree status
  is path metadata only.
- A repository path must resolve inside a configured exact allowlisted root.
  Traversal, a symlink repository root, a non-Git directory, a network locator,
  or an out-of-root path fails closed with a stable non-disclosing code.
- In-repository symlinks are recorded but never followed. Submodules are
  recorded but never initialized. LFS pointers are recognized but never
  fetched.
- Sensitive paths are never read. Secret findings contain only a relative
  path, rule class, blocked flag, and non-secret summary.
- Repository text is `untrusted_repository_content`; it cannot alter policy or
  permissions.
- Git reads use fixed arrays with `shell=False`, bounded timeout, disabled
  prompts/optional locks/hooks/aliases, and no credential or network access.
- Plan revision cannot raise permission, introduce execution, arbitrary shell,
  secret access, automatic merge/deploy, authentication/payment work, or
  high-risk database migration.
- Only the user may approve or reject the real CreativeDeploy plan.
- Stop if the committed-HEAD boundary, read-only mount, secret containment,
  approval concurrency, mandatory verification, or final clean checkpoint
  cannot be proven.

## Data model

### Run

UUID identity, Task foreign key, explicit status, `read_only` permission,
`git_head` snapshot mode, optimistic version, stable trace ID, current plan
version, redacted failure fields, and UTC timestamps. The Phase 2 transition
table is:

```text
created -> snapshotting -> snapshot_ready -> plan_ready
        -> awaiting_plan_approval -> approved | rejected
```

Active states may fail. Reasonable pre-approval states may cancel. `approved`
means only that the bound plan received a human decision.

### RepositorySnapshot

One successful immutable snapshot per Run. It stores the commit, branch,
bounded dirty-path metadata, scanner and policy versions, deterministic
fingerprint, bounded manifest and file counts, extracted stack/scripts/tests/
design-system/instruction/safety facts, and UTC creation time. It stores no
absolute home path, source corpus, untracked or dirty file content, or secret.

### Plan

Versioned immutable plan content bound to a snapshot fingerprint. Source is
always `deterministic_policy`. Status is `draft`, `awaiting_approval`,
`approved`, `rejected`, or `superseded`. Validation steps use a closed typed
schema and are display-only. A revision supersedes the prior editable draft.

### ApprovalDecision

One final local-user decision per Plan, with request ID and optional comment;
rejection requires a reason. Only the latest awaiting version is decidable.
Identical replay is idempotent; a conflicting decision or stale version is a
stable conflict. Database uniqueness and row locking serialize races.

### AuditEvent

Append-only, structured, redacted governance events for Run creation,
snapshot start/completion/failure, plan create/revise/submit/decision,
cancel, and policy denial. It is not represented as a complete Agent trace.

## API

- `POST /api/v1/tasks/{task_id}/runs`
- `GET /api/v1/tasks/{task_id}/runs`
- `GET /api/v1/runs/{run_id}`
- `POST /api/v1/runs/{run_id}/snapshot`
- `GET /api/v1/runs/{run_id}/snapshot`
- `POST /api/v1/runs/{run_id}/plans`
- `GET /api/v1/runs/{run_id}/plans`
- `GET /api/v1/runs/{run_id}/plans/{version}`
- `POST /api/v1/runs/{run_id}/plans/{version}/revisions`
- `POST /api/v1/runs/{run_id}/plans/{version}/submit`
- `POST /api/v1/runs/{run_id}/plans/{version}/decisions`
- `GET /api/v1/runs/{run_id}/audit-events`
- `POST /api/v1/runs/{run_id}/cancel`

Request IDs and stable errors remain mandatory. Mutations use typed services
and explicit transactions; routes do not own the state machine.

## Repository scanner design

1. Validate and canonicalize the local repository root without disclosing it.
2. Verify it is a non-symlink directory inside an exact allowlisted root.
3. Use a hardened Git environment and fixed read-only commands to identify
   root, branch, `HEAD`, status, and the committed tree.
4. Classify every tree entry before selection. Never open a working-tree file.
5. Select a bounded set of non-sensitive text candidates by explicit policy.
6. Read selected committed blobs by object ID, reject binary/oversized data,
   and extract only structured facts.
7. Canonically sort and hash stable inputs to create the fingerprint.
8. Persist the immutable sanitized snapshot and audit event transactionally.

## Deterministic plan generator

The generator uses only the Task, immutable Snapshot, selected delivery
package, and versioned Phase 2 policy. It produces the documented plan fields,
`source = deterministic_policy`, and `execution_available = false`. It never
claims Agent reasoning or executes a validation step.

## Adversarial scenarios

The synthetic fixture will cover injected README/AGENTS instructions, fake
environment/key files, an escaping symlink, large and binary files,
`node_modules`, a malicious lifecycle script, a submodule entry, dirty tracked
and untracked content, traversal, out-of-allowlist input, timeout/budget
failure, a network locator, and repeat scans.

Assertions will prove no secret payload reaches database/log/API/snapshot,
dirty and untracked content is not read, symlinks are not followed, scripts
are parsed but not run, submodules are not initialized, fingerprints are
stable, snapshots are immutable, and the target repository's status and
committed-file hashes are unchanged.

## CreativeDeploy Customer 0 process

After fixture and mandatory safety tests pass:

1. Capture branch, `HEAD`, full status, and diff stat with read-only Git.
2. mount only CreativeDeploy into the API at
   `/repositories/customer0/creative-deploy:ro`;
3. configure that path as the sole repository allowlist root;
4. create the specified Task and Level 0 Run;
5. create the committed-HEAD Snapshot;
6. create Frontend Quality Remediation Plan v1;
7. submit it to `awaiting_plan_approval`;
8. do not approve or reject;
9. capture IDs, fingerprint, page address, audit state, and a second read-only
   CreativeDeploy baseline.

Concurrent external changes will be reported, never reset, cleaned, or
attributed to this batch without evidence.

## Decisions

| Decision                                             | Rationale                                                                                                                   |
| ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Keep scanner and planning synchronous in Phase 2     | Bounded local scans have a hard timeout and no queue is authorized; durable state still exposes progress and failure.       |
| Read committed blobs by object ID                    | It decouples repository facts from dirty working-tree content and avoids untrusted path interpolation.                      |
| Store summaries and hashes, not selected source text | Product needs repository intelligence, while persistence of a source corpus would enlarge secret and prompt-injection risk. |
| Make approval terminal in Phase 2                    | Approval records intent only; there is no execution state or tool capability in this batch.                                 |
| Use PostgreSQL constraints plus row locks            | In-memory or UI-only checks cannot serialize concurrent final decisions.                                                    |

## Risks

| Risk                                                         | Likelihood / impact                   | Mitigation and next action                                                                                                |
| ------------------------------------------------------------ | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Existing Foundation seams are too small for the new workflow | Medium / medium                       | Inspect before choosing boundaries; add only behavior-backed modules.                                                     |
| Git object parsing mishandles unusual paths                  | Medium / high                         | Use NUL-delimited machine formats where possible, object IDs for reads, synthetic path tests, and bounded decode policy.  |
| A selected manifest contains a secret-like value             | Medium / high                         | Deny sensitive filenames, extract only allowlisted keys, redact findings, and scan persisted/API/log representations.     |
| Plan decision race creates two outcomes                      | Medium / high                         | Row lock the Run/latest Plan and enforce one-decision uniqueness; force a real PostgreSQL race.                           |
| Docker bind mount is writable or visible to another service  | Low / critical                        | Dedicated override, read-only API-only mount, config/runtime mount inspection, non-root user; no real-target write probe. |
| CreativeDeploy changes concurrently                          | High / low for this task if read-only | Preserve exact before/after observations and do not clean or reset.                                                       |
| Mandatory matrix exceeds local resources                     | Medium / medium                       | Run narrow checks first, diagnose exact failures, and keep services project-scoped.                                       |

## Discoveries

- 2026-07-26: The supplied baseline is exact and the new branch was safe to
  create.
- 2026-07-26: The repository already has ignored local dependency, coverage,
  build, and Playwright artifacts; they are not Foundation tracked content and
  must remain outside the checkpoint.
- 2026-07-26: Foundation currently persists only Task and represents all Run
  behavior as future documentation, so Phase 2 requires one additive migration
  and a real replacement of those future-only claims.
- 2026-07-26: Existing contract generation, PostgreSQL test, Docker E2E, and
  non-root image seams can be extended rather than replaced.
- 2026-07-26: A 14-test narrow regression against real PostgreSQL and synthetic
  Git repositories passed at 82.15% backend coverage. It exercises the scanner,
  immutable Snapshot trigger, plan revisions, stale conflicts, approval
  idempotency, and a concurrent approve/reject race.
- 2026-07-26: The scanner's first security audit found symlink target metadata
  was read before applying the normal blob byte budget. The read is now denied
  before `cat-file` when size is unknown or over budget, and a dedicated
  oversized-symlink regression passes.
- 2026-07-26: CreativeDeploy Customer 0 completed through Plan submission.
  The API runtime user is `app`; the exact repository mount reports
  `.RW=false`; Web has no target mount; PostgreSQL has only its data volume.
  Before/after branch, `HEAD`, 13-path status hash, and diff-stat hash were
  identical. Run `447510d7-695c-46ec-baad-9a0f750ce965` and deterministic Plan
  v1 remain at their human approval states.

## Failures and root causes

- 2026-07-26: The first backend static check failed with 27 Ruff findings
  (unused imports, long deterministic policy strings, and two missing exception
  chains) plus six mypy route return findings. Root cause: the initial slice
  had not yet been normalized to the repository's strict line and `NoReturn`
  conventions. Imports and string layout were corrected, exception chaining
  was made explicit, and the HTTP error raiser was typed `NoReturn`. Regression:
  Ruff and strict mypy both pass.
- 2026-07-26: The first full backend regression failed because a retained
  Foundation test truncated only `tasks` after Phase 2 foreign keys existed.
  Root cause: cleanup assumed Task was the only table. The fixture now
  truncates all mapped tables in dependency-safe PostgreSQL form. Regression:
  55 backend tests pass on real PostgreSQL.
- 2026-07-26: The initial eval validator assumed only the new Phase 2 JSONL
  shape and rejected the retained Foundation dataset. The validator now
  explicitly accepts and validates both versioned shapes while still rejecting
  duplicate IDs and invented result/score fields. Regression: 29 cases across
  two datasets validate.
- 2026-07-26: Initial frontend checks found a TypeScript cancellation-request
  narrowing error and an ESLint state-update-in-effect violation. Request
  lifetime handling and deferred refresh logic were corrected without
  weakening checks. Frontend typecheck/lint and 21 tests pass.
- 2026-07-26: The first expanded Playwright run passed desktop flows but axe
  reported `scrollable-region-focusable` for two narrow-screen Audit metadata
  blocks. The `<pre>` regions now have an accessible label and keyboard
  `tabIndex`. Regression: all six desktop/narrow approve/reject flows pass.
- 2026-07-26: The pre-stage security audit found that denied sensitive paths
  still retained Git object ID and size in the manifest. Although no value had
  been read, these content-derived fields were unnecessary. Sensitive-name and
  detected-secret entries now remove object ID and size before fingerprint or
  persistence. A dynamic synthetic-token regression proves the value is absent
  from scanner result, API, database, audit, and governance log surfaces.

## Verification ledger

Individual and aggregate Phase 2 pre-commit commands below are current.

| Command or gate                               | Status                  | Exit | Result                                                   |
| --------------------------------------------- | ----------------------- | ---- | -------------------------------------------------------- |
| `make format`                                 | VERIFIED                | 0    | Ruff and Prettier completed                              |
| `make format-check`                           | VERIFIED                | 0    | Python and workspace formatting passed                   |
| `make lint`                                   | VERIFIED                | 0    | Ruff and ESLint passed                                   |
| `make typecheck`                              | VERIFIED                | 0    | mypy 38 files and TypeScript strict passed               |
| `make test`                                   | VERIFIED                | 0    | 55 backend / 21 frontend; 84.91% backend coverage        |
| `make build`                                  | VERIFIED                | 0    | Next.js production build with four routes                |
| `make contracts-check`                        | VERIFIED                | 0    | OpenAPI and generated TypeScript have no drift           |
| `make migration-check`                        | VERIFIED                | 0    | PostgreSQL upgrade/downgrade/upgrade                     |
| `make security-check`                         | VERIFIED (intermediate) | 0    | secret scan + 7 scanner cases                            |
| `make eval`                                   | VERIFIED (intermediate) | 0    | 29 dataset cases + 7 scanner cases                       |
| `make e2e`                                    | VERIFIED (intermediate) | 0    | 6 real-stack desktop/narrow flows                        |
| `make verify`                                 | VERIFIED (pre-commit)   | 0    | Full aggregate matrix passed                             |
| `docker compose config`                       | VERIFIED                | 0    | Base and all override configurations rendered            |
| `git diff --check`                            | VERIFIED                | 0    | No whitespace errors                                     |
| adversarial end-to-end flow                   | VERIFIED                | 0    | read-only mount; HEAD/status unchanged; lifecycle absent |
| approval decision concurrency                 | VERIFIED                | 0    | one winner, one conflict, one row                        |
| repeated fingerprint                          | VERIFIED                | 0    | same HEAD/scanner stable across dirty-byte changes       |
| CreativeDeploy read-only mount and workflow   | VERIFIED                | 0    | Plan v1 awaiting user approval                           |
| CreativeDeploy before/after safety comparison | VERIFIED                | 0    | branch/HEAD/status/diff-stat hashes identical            |

Intermediate evidence:

- `uv run ruff check apps/api scripts`: exit 0.
- `uv run mypy apps/api/src apps/api/tests`: exit 0.
- Targeted PostgreSQL/Git suite: exit 0, 14 passed, 82.15% coverage, one
  pre-existing Starlette `httpx` deprecation warning.

## Rollback

- Stop only VisualEngineer project-scoped services with the exact Compose
  project/override command used by this batch.
- Before the checkpoint, reverse only files introduced by this branch after
  inspecting scope; never use destructive Git reset/clean or overwrite
  unrelated changes.
- The Alembic downgrade removes only Phase 2 tables and enum types after
  explicit verification against a disposable local database.
- CreativeDeploy has no rollback action because it must receive no write. Any
  suspected write is a stop condition and incident to investigate.
- No remote, push, merge, tag, or deployment exists to undo.

## Completion conditions

1. All five entities, invariants, migration round trip, and API contracts are
   implemented and verified on PostgreSQL.
2. Scanner security assertions pass against the adversarial fixture, including
   deterministic fingerprinting and unchanged repository evidence.
3. Plan revisions, stale conflicts, rejection reason, idempotent replay, and
   approve/reject concurrency behave deterministically.
4. The responsive web workflow and real-stack desktop/narrow/axe flows pass.
5. Contract, format, lint, type, build, security, eval, Docker, migration,
   E2E, and aggregate verification gates all return exit code 0.
6. CreativeDeploy remains read-only and its actual Plan is durably
   `awaiting_plan_approval` for the user.
7. Documentation matches only proven Phase 2 behavior and preserves every
   explicit limitation.
8. The staged diff contains no CreativeDeploy file, personal absolute path,
   secret, environment file, runtime data, cache, report, trace, or dependency.
9. The local checkpoint exists on the Phase 2 branch, the post-commit
   `make verify` passes, there is no remote, and the worktree is clean.

## Outcome and follow-ups

COMPLETE. Implementation, documentation, Customer 0, pre-commit verification,
staged-content audit, local checkpoint, and post-commit `make verify` are
complete. The final clean branch/remote inspection is reported in the handoff
because recording the containing commit hash inside itself would be
self-referential.

The only proposed next milestone is a separately approved Level 1
isolated-worktree design and typed runtime-policy prototype; it is not part of
Phase 2 and was not implemented here.
