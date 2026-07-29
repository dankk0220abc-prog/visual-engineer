# Phase 4 Independent Budget Re-Audit

- Started: 2026-07-29T16:15:25+08:00
- Branch: `audit/phase-4-manifest-budget-reaudit-max`
- Candidate / Round 4 remediation:
  `03f774827afbafd7f0eb991f5abf2c6fee66cd17`
- Candidate parent / single-finding audit:
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Historical Security Gate: **FAIL — PRESERVED**
- Current status:
  `BUDGET RE-AUDIT COMPLETE — FINDING CLOSED — READY FOR FINAL PHASE 4
INTEGRATION GATE`

## Goal

Independently decide only whether Round 4 closes the Blocking Medium finding
that source-less checkout-manifest construction could expand shared Git trees
beyond `mirror_max_tree_entries`.

## Scope

Permitted changes are limited to one additive independent budget test, this
ExecPlan, the matching audit report and verification evidence, and
`docs/status/project-status.md`.

## Non-goals

- No production, API, database, Permit, discard, timeout, Web, Compose, CI,
  Phase 5, LLM, Agents SDK, or delivery change.
- No re-audit of unrelated Phase 4 findings.
- No complete `make verify`, Web E2E, full Chaos, full Docker Gate, Customer 0,
  CreativeDeploy access, remote, push, merge, pull request, or tag.

## Constraints and safety

- Operate only in `/Users/danke/Developer/VisualEngineer`.
- Treat implementer evidence as navigation and rerun every decisive check.
- Preserve historical FAIL evidence and stop on a new Critical or High.
- Never repair production during this independent review.
- Create at most one additive test and one audit-only local checkpoint.

## Current progress

### 2026-07-29

- DONE: reconcile repository, branch, candidate, exact parent, one-commit
  ancestry, refs, remote, stash, tags, and clean worktree/index.
- DONE: create the audit branch directly from the exact candidate.
- DONE: read the required governance, finding, remediation, production, test,
  architecture, threat-model, evidence, and status material.
- DONE: review the Round 4 production diff and directly related tests.
- DONE: run the unchanged permanent shared-tree reproduction; exit `0`,
  `1 passed`.
- DONE: add one distinct three-parent shared-subtree boundary test.
- DONE: run the specified focused verification matrix.
- DONE: write the audit decision, evidence, and status.
- DONE: verify final scope, protected refs, production invariance, and clean
  audit-only checkpoint.

## Decisions

1. Use one shared single-file tree referenced by three parent directories.
   This differs from the repairer's two-parent, three-file case.
2. Require limit `5` to accept exactly five entries and reject a possible
   sixth entry before the third shared blob read.
3. Exercise the actual manager failure path and require no Workspace,
   registry, or ownership record while source and a sibling marker survive.
4. Keep production frozen at the candidate commit.

## Risks

| Risk                                  | Impact          | Mitigation / next action                                        |
| ------------------------------------- | --------------- | --------------------------------------------------------------- |
| A third shared path is not charged    | Blocking Medium | Assert the third content read never occurs at limit five.       |
| Equality is rejected                  | Availability    | Require exactly five expanded entries to succeed at limit five. |
| Failure leaves usable Workspace state | Integrity       | Assert no root, registry, or ownership record.                  |
| Audit scope changes production        | Governance      | Diff production against the exact candidate before commit.      |
| A new Critical or High is found       | Gate blocker    | Preserve facts and stop without repair or scope expansion.      |

## Discoveries

- The candidate shares one mutable expanded-entry counter across recursive
  checkout-manifest paths.
- A leaf charge includes all still-pending materialized ancestor directories
  and fails before blob read or digest calculation.
- Empty Git trees remain omitted because their pending directory is never
  charged without a materialized child.

## Verification

| Check                                 | Status                 |
| ------------------------------------- | ---------------------- |
| Git baseline and audit branch         | VERIFIED               |
| Complete Round 4 diff review          | VERIFIED               |
| Permanent shared-tree reproduction    | VERIFIED — 1 PASS      |
| Independent three-parent boundary     | VERIFIED — 1 PASS      |
| Complete blocking reproduction file   | VERIFIED — 13 PASS     |
| Manifest/object-closure focus         | VERIFIED — 24 PASS     |
| Source invariance                     | VERIFIED — PASS        |
| Workspace security                    | VERIFIED — 63 + STATIC |
| Runner, format, lint, and type checks | VERIFIED — PASS        |
| `git diff --check`                    | VERIFIED — PASS        |
| Complete `make verify` and broad E2E  | NOT RUN — OUT OF SCOPE |

## Rollback

- Keep all audit additions isolated on the dedicated branch.
- Do not reset, clean, stash, prune, force-update, or overwrite refs.
- Tests use only generated temporary repositories.
- If a blocker appears, retain the smallest audit evidence and do not change
  production.

## Completion conditions

1. Every expanded path through a shared tree is independently charged.
2. Equality succeeds and the next entry is rejected before content work.
3. Failure creates no usable or registered Workspace and preserves source,
   sibling, mirror, and existing recovery semantics.
4. The permanent reproduction and every specified focused target pass.
5. Only the one audit test and authorized audit/status documents differ from
   the candidate.
6. One audit-only checkpoint exists and the final worktree/index are clean.

## Outcome and follow-ups

`BUDGET RE-AUDIT COMPLETE — FINDING CLOSED — READY FOR FINAL PHASE 4
INTEGRATION GATE`

This successful narrow result does not authorize or replace the final
integration gate, `main` merge, Customer 0, CreativeDeploy, or Phase 5.

One audit-only checkpoint was created after the five-path allowlist,
production invariance, protected refs, and clean post-commit worktree/index
were verified. Its final hash is recorded in the independent handoff.
