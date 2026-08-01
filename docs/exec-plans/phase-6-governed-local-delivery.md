# Phase 6 First Vertical Slice — Governed Local Git Delivery

## Goal

Turn one fresh, approved, `ready` Phase 5 Review Package into one separately
approved, fixture-only local Git delivery in the existing Runner-owned
Workspace: a system-derived branch and one local commit with durable,
digest-bound evidence. No remote, push, pull request, tag, merge, deployment,
source-repository write, or new credential is permitted.

## Scope

- Add immutable PostgreSQL delivery authorization, decision, and result state
  plus one reversible additive migration.
- Add one closed Runner Protocol job for an exact Workspace/Checkpoint commit.
- Require both the original Workspace authority and a distinct approved
  delivery authorization, with a current Side-effect Permit immediately before
  Git mutation.
- Add API, generated contract, browser workflow, state-machine documentation,
  and focused unit/PostgreSQL/Runner/Web/real-stack security regressions.
- Update Phase 6 evidence, Project Status, product, architecture, and ADR
  records in the local checkpoint.

## Non-goals

- LLMs, Agents SDK, Providers, model calls, API keys, or external credentials.
- CreativeDeploy, Customer 0, real customer repositories, or non-fixture
  Workspace expansion.
- User-supplied branch names, commit messages, commands, argv, cwd,
  environment, author identity, hooks, signing, or arbitrary Git.
- Remote configuration, fetch, push, pull request, merge, tag, deployment, or
  source-repository mutation.
- Authentication, multi-tenancy, or production release operations.

## Constraints and safety

- Baseline is clean local `main`
  `962b72ec92329de929ca5f9381b5324a68a18dde`; implementation branch is
  `feat/phase-6-governed-local-delivery`.
- Delivery is allowed only for the exact fresh Review Package generation,
  approving Review Decision, effective `ready` verdict, Workspace, immutable
  Checkpoint, tree/diff digest, revision, and repository handle.
- The server derives the branch/ref and commit message. Runner uses only the
  hardened Git adapter with hooks, signing, credentials, network, filters,
  helpers, and repository configuration disabled.
- A current PostgreSQL-backed Side-effect Permit must bind the exact Runner,
  Job, Attempt, Lease, Workspace, original Execution Grant, Delivery
  Authorization, operation digest, Checkpoint, and deadline.
- Any stale Review, changed Workspace, non-ready verdict, identity mismatch,
  existing ref, unexpected Git state, or ambiguous migration head fails closed
  before mutation.
- Stop before any remote/delivery expansion, real repository, credential,
  LLM, destructive migration, or permission increase beyond this exact local
  fixture operation.

## Current progress

- 2026-07-31 CST — **done**: real repository, exact root, clean state, branch,
  HEAD/main, refs, no remote/stash, Git identity, and sole migration head
  `20260730_0012` verified.
- 2026-07-31 CST — **done**: product, architecture, ADR, Project Status,
  roadmap seams, and latest Phase 5 ExecPlans inspected.
- 2026-07-31 CST — **done**: Phase 6 Inception selected the only clearly
  authorized V1 seam: fixture-only governed local branch/commit.
- 2026-07-31 CST — **done**: implementation branch created from the exact
  baseline.
- 2026-07-31 CST — **done**: additive data model/migration, dual-authority
  protocol, API, Runner Git plumbing, local-delivery state, Web console, and
  generated contract implemented.
- 2026-07-31 CST — **done**: focused Protocol/API/PostgreSQL/Runner/Web,
  migration, source-invariance, real-stack, security, build, and quality
  verification completed; first failures retained.
- 2026-07-31 CST — **blocked**: final single-run aggregate remains open on the
  pre-existing Workspace Chaos recovery timing instability. One exact isolated
  run passed; four final-source attempts failed without a policy change.
- 2026-07-31 CST — **done**: Evidence, Project Status, product, architecture,
  security, and ADR records reconciled.
- 2026-07-31 CST — **in progress**: final diff/scope review and local
  checkpoint.

## Decisions

1. Model Git authority separately from Phase 5 Review approval and the Phase 4
   Execution Grant; neither existing approval is silently broadened.
2. Permit only one system-derived ref in a private
   `refs/heads/visual-engineer/<workspace-id-hex>` namespace and one commit
   whose parent is the exact source revision.
3. Store only bounded metadata and digests in PostgreSQL/API. Source content,
   raw patch payloads, local paths, credentials, and environment are excluded.
4. Preserve the original source and canonical Workspace bytes; the operation
   changes only Runner-owned Git metadata and records a local commit.
5. Keep this first slice local-only. Remote delivery is a later authorization
   and security review.

## Risks

- Shared-mirror ref collision or cross-Workspace confusion: use an exact
  Workspace-derived ref, require absence before creation, and bind result
  verification to Workspace and parent revision.
- Approval becoming stale between dispatch and Git mutation: revalidate at
  dispatch, Permit acquisition, and result acceptance; mutation requires the
  latest short-lived Permit.
- Hooks, signing, attributes, or repository config influencing commit:
  construct a tree with fixed Git plumbing and fixed identity instead of
  invoking user-facing `git commit`.
- Partial Git mutation before completion: create the commit object first and
  use one old-OID-guarded ref update as the sole visible transition; retry
  accepts only the exact expected commit/ref binding.

## Discoveries

- The repository does not name a standalone Phase 6 milestone. Its Reserved V1
  seams identify LLM, real-repository command, and Git delivery directions.
  The user stop boundaries exclude the first two and every remote action,
  leaving governed fixture-only local branch/commit as the sole safe direction.
- The Phase 4 hardened adapter already centralizes fixed-environment Git
  plumbing on Runner-owned workspaces, and Phase 4 Side-effect Permits provide
  the required last-authority pattern.
- A delivery Job must reuse the Workspace's original implementation Grant for
  path and diff budgets. The Phase 5 validation Grant proves the review chain
  but cannot be repurposed as write authority; the distinct Delivery
  Authorization supplies only the exact local-commit authority.
- Real-stack verification first exposed an empty reviewed diff, then incorrect
  reuse of the validation Grant, and finally missing Web terminal polling.
  These failures are retained in the Evidence record.
- The first complete browser matrix exposed a Phase 4/Phase 6 mirror reuse
  conflict: the governed delivery ref was valid, but the legacy validator
  required every loose ref to remain empty, so later Workspaces failed
  `workspace_state_invalid`. The repaired invariant admits only bounded
  fixed-namespace refs with stable bytes, exact single-parent source lineage,
  and an exact source-plus-delivery object-closure union.
- Final Diff review found that the first union implementation retained only
  the last governed ref closure. The fixed implementation accumulates every
  validated ref closure and a two-ref sibling-prepare regression passes.
- The post-review aggregate is not stable at the pre-existing Workspace Chaos
  recovery gate. Its failures are `envelope_expired`, `retry_exhausted`, and a
  failed recovered prepare; one identical isolated run passed. No lease,
  attempt, TTL, timeout, or authority was widened.

## Verification

The final source passes contracts, format, lint, mypy over 115 source files,
TypeScript, 300 Python/API/Runner/Protocol tests, 53 Web tests, production
build, Docker config, migration base/head/base/head, historical security
preservation, source invariance, Workspace repair, 16 desktop+narrow E2E
tests, Workspace and Validation sandbox security, real PostgreSQL
Runner/Review security, 74 eval cases, and `git diff --check`.

The post-review `E2E_SKIP_BUILD=1 make verify` attempts reached Workspace
Chaos only after their preceding gates passed, then exited `2`. One exact
isolated Chaos run passed; four attempts failed during recovery. Exact
commands, counts, coverage, first failures, invariance proofs, and Docker
cleanup are recorded in
`docs/evidence/phase-6-governed-local-delivery-verification.md`.

## Rollback

Before the checkpoint, revert only this branch's reviewed patch. The additive
migration downgrade removes only Phase 6 tables/columns/checks. Test cleanup
may stop and remove only exact task-owned Compose projects. Never reset, clean,
stash, delete unrelated Docker state, or modify a source repository. A created
local delivery ref is retained as governed evidence unless an explicitly
designed, separately authorized cleanup flow exists.

## Completion conditions

- One fresh ready Review can receive exactly one immutable, separately decided
  Delivery Authorization and one bound local commit result.
- Denial, stale state, injection, replay, cancellation, and authority mismatch
  produce no ref/commit result, no success event, and no remote effect.
- Protocol, API, database, Runner, Web, migration, contract, quality, build,
  source-invariance, real-stack, and cleanup gates required by the change pass.
- Main remains at the exact baseline; no remote, push, PR, tag, merge, deploy,
  Customer 0, CreativeDeploy, LLM, Provider, or credential action occurs.
- The final diff is reviewed, `git diff --check` passes, one local checkpoint
  exists, and the worktree is clean.

## Outcome and follow-ups

**IMPLEMENTED; FOCUSED VERIFICATION PASSES; AGGREGATE GATE OPEN.** The next
safe milestone after the local checkpoint is an independent focused security
review of local Git authority, Permit fencing, fixed Git plumbing,
managed-ref/object-closure integrity, replay, source invariance, and
zero-remote behavior, followed by one stable aggregate run. Remote delivery
remains separately unauthorized.
