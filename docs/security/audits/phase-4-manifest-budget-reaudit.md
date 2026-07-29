# Phase 4 Independent Budget Re-Audit

- Review date: 2026-07-29
- Audit branch: `audit/phase-4-manifest-budget-reaudit-max`
- Candidate / Round 4 remediation:
  `03f774827afbafd7f0eb991f5abf2c6fee66cd17`
- Candidate parent / single-finding audit:
  `2656733aad60d9824db4334b9ef6ba7eb1d677b8`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Decision:
  **BUDGET RE-AUDIT COMPLETE — FINDING CLOSED — READY FOR FINAL PHASE 4
  INTEGRATION GATE**

## Executive decision

Round 4 closes the Blocking Medium finding **Expanded checkout manifest
bypasses configured entry budget**.

**CONFIRMED**: source-less manifest materialization now uses one expanded-entry
counter across the recursive walk. Each materialized leaf is charged together
with every not-yet-charged ancestor directory before blob reading or digest
work. A new directory marker is created for each traversal path, so repeated
references to the same Git tree object are charged again under each distinct
parent.

The unchanged permanent reproduction passes. A distinct independent case uses
one single-file subtree under three parent directories. At limit `5`, an exact
five-entry shared-tree manifest succeeds. The six-entry three-parent manifest
returns typed `mirror_budget_exceeded`; only the first two shared blob paths
are read, proving the third path is rejected before its blob content and
digest. The actual manager path creates no Workspace, registry, or ownership
record and preserves the source, mirror, and a sibling marker.

No production code was changed by the reviewer. No new Critical, High, or
blocking Medium finding was found. This narrow decision closes only the budget
finding. It does not declare the Phase 4 Security Gate PASS and does not
authorize merge, Customer 0, CreativeDeploy, Phase 5, or delivery.

## Authority and scope

This review is limited to:

- expanded source-less manifest entry accounting;
- shared-tree per-path expansion;
- exact-limit and limit-plus-one behavior;
- pre-content rejection;
- failure-path Workspace, registry, ownership, mirror, sibling, source, and
  Permit effects;
- directly related object closure, replacement, Workspace, and source
  invariance regressions.

The review did not re-audit discard proof, process-group timeout, Side-effect
Permit production logic, the complete replacement finding, or the rest of
Phase 4. It did not run aggregate `make verify`, Web E2E, full Chaos, the full
Docker Gate, Customer 0, or any historical full audit.

## Decision matrix

| Required property                    | Result   | Independent basis                                                                 |
| ------------------------------------ | -------- | --------------------------------------------------------------------------------- |
| Original shared-tree reproduction    | **PASS** | Unchanged permanent test passes `1/1`.                                            |
| Exact configured limit               | **PASS** | Independent five-entry manifest returns exactly five entries.                     |
| Limit plus one                       | **PASS** | Six-entry topology returns typed `mirror_budget_exceeded`.                        |
| Shared tree charged per parent path  | **PASS** | One tree referenced by three parents exhausts the same shared counter.            |
| Rejection before content/digest      | **PASS** | Third shared blob read count remains zero; digest occurs only after that read.    |
| No full over-budget list             | **PASS** | The recursive charge precedes leaf construction; checkout returns no manifest.    |
| No usable partial Workspace state    | **PASS** | No canonical Workspace, registry, or ownership record exists after rejection.     |
| Mirror, sibling, and source survival | **PASS** | Mirror directory and sibling marker remain; source HEAD/status are unchanged.     |
| Permit behavior                      | **PASS** | One manager execution receives one Permit; no retry or additional acquisition.    |
| Entry semantics                      | **PASS** | Existing exact regular/symlink/gitlink/mode/size/digest test remains passing.     |
| Object/replacement/source regression | **PASS** | Focused object tests, blocking file, source invariance, and Workspace gates pass. |
| Reviewer production invariance       | **PASS** | Candidate production paths have no worktree or index diff.                        |

## Accounting result

`checkout_manifest` creates one shared mutable count for the entire recursive
walk. For a leaf, `_charge_manifest_leaf`:

1. identifies every pending ancestor directory not yet charged on that path;
2. computes the proposed total including those directories and the leaf;
3. raises typed `mirror_budget_exceeded` when the proposed total is greater
   than `mirror_max_tree_entries`; and
4. only after acceptance updates the count and marks those directories
   charged.

Blob object reading and SHA-256 calculation occur after this charge. Gitlinks
are charged before their inert manifest entry is constructed. Directory
entries are appended only when their recursive child list is non-empty and
their marker has already been charged. This preserves the pre-existing
omission of Git empty trees.

**CONFIRMED**: there is no final `len(manifest)` enforcement over a fully
constructed list. Rejection occurs inside recursion before the over-limit
leaf is read or appended.

## Independent boundary scenario

The additive audit test is
`test_budget_reaudit_three_parent_shared_tree_charges_each_expanded_path`.
It differs from the repairer's two-parent, three-leaf case:

- one shared tree contains one ordinary blob;
- an exact revision materializes two shared directory paths plus one root
  file, producing exactly five entries under limit `5`;
- an over-limit revision references the same shared tree from `first`,
  `second`, and `third`, producing six possible expanded entries;
- a read spy observes the shared blob twice, not three times;
- the direct parser and actual manager both return the typed budget failure;
  and
- the manager failure leaves no Workspace, registry, or ownership record and
  preserves source HEAD/status, the mirror, and a sibling marker.

The test uses only a generated temporary Git repository and no network or
external repository.

## Regression and invariance result

**CONFIRMED** current focused results:

- permanent shared-tree reproduction: `1 passed`;
- independent three-parent boundary: `1 passed`;
- complete blocking reproduction file: `13 passed`;
- manifest/object-closure focus: `24 passed, 34 deselected`;
- source invariance: PASS with 119 entries, 10 Git objects, 2 status records,
  and 0 extension markers;
- Workspace security: `63 passed` plus static isolation;
- Runner/Protocol: `83 passed`;
- final format, lint, and typecheck: PASS.

The complete blocking file retains the original replacement attacks, while the
object/manifest focus retains exact reachable closure, replacement metadata,
semantic mismatch, inert gitlink, malformed-object, and normal manifest
coverage. Their passing result is regression evidence only; this review did
not reopen or re-decide those historical findings.

## New findings

No new Critical, High, or blocking Medium finding was discovered within this
narrow budget re-audit.

## Remaining limitations

- **NOT VERIFIED**: aggregate `make verify`, Web E2E, full Chaos, full Docker
  Gate, Customer 0, remote CI, production deployment, and hostile
  multi-tenant isolation. They were explicitly outside this re-audit.
- Empty Git trees remain intentionally absent from the materialized manifest.
  Their unique objects, entries, references, and depth remain subject to the
  existing object/tree/graph budgets; this review did not change that semantic
  contract.
- A final Phase 4 integration gate remains required before any integration
  decision. That gate is the next milestone, not part of this review.

## Final decision

`BUDGET RE-AUDIT COMPLETE — FINDING CLOSED — READY FOR FINAL PHASE 4
INTEGRATION GATE`

The historical Security Gate FAIL remains preserved until the separate final
integration gate runs and makes its own decision.
