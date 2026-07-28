# Phase 4 Independent Single-Finding Security Re-Audit

- Review date: 2026-07-29
- Audit branch: `audit/phase-4-replacement-single-finding-max`
- Candidate / Round 3 repair:
  `6cce662bf4cf34961c7d3f0d16741952cd2c1fd2`
- Candidate parent / focused re-audit:
  `8985fa0356e636602d1414a3ade9d9a7888c624a`
- Main baseline:
  `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Decision:
  **SINGLE-FINDING RE-AUDIT COMPLETE — VE-P4-FREAUD-001 FAIL —
  REMEDIATION REQUIRED**

## Executive decision

Round 3 closes the original packed-replacement checkout reproduction and
passes a distinct independent late-injection replacement scenario. Mirror
metadata validation, dual replacement disabling, exact authorized object
closure, semantic content/mode/link comparison, mismatch quarantine, and
source invariance all pass their current focused checks.

`VE-P4-FREAUD-001` nevertheless cannot be independently closed. The new
source-less checkout manifest recursively expands every path through a shared
Git tree object without charging the expanded entries to
`mirror_max_tree_entries`. The pre-existing closure walk charges each unique
tree object only once. A compact shared-subtree DAG can therefore make
`prepare_mirror` return an over-budget manifest before the descriptor-rooted
Workspace scanner applies its separate limit.

The minimal independent case configures a five-entry limit. Its unique source
trees contain five entries, but two root names share one three-file subtree,
so the prepared manifest has eight path entries and is accepted. The stable
secure-expectation test fails `8 <= 5`.

This is a Blocking Medium availability and stability defect inside the
Workspace semantic-proof acceptance boundary required by this re-audit. It
does not reproduce unauthorized registered Workspace bytes: a complete
manager-path probe later rejects the eight-entry checkout with typed
`mirror_budget_exceeded`, quarantines it, and creates no registry. However,
the unbounded expected-manifest expansion occurs earlier in `prepare_mirror`,
before that scanner and before Git's subprocess timeout applies. With repeated
shared subtrees, expanded entries grow exponentially while unique objects and
references remain small, so the Runner can exhaust its 512 MiB container or
Permit window and leave an incomplete managed mirror requiring recovery.

The PASS standard explicitly requires capacity and stability limits and no new
blocking Medium. The single finding therefore remains open. No production
repair was attempted.

## Authority and scope

This review is limited to `VE-P4-FREAUD-001`:

- source and destination replacement metadata;
- the minimal managed mirror/ref namespace;
- command and environment replacement disabling;
- exact Workspace-to-authorized-revision semantics;
- semantic-proof quarantine, capacity, and stability;
- exact object closure and source invariance; and
- directly related Runner/Protocol regression gates.

The already independently passing discard, process-group timeout, and
Side-effect Permit findings were not re-audited. The review used only
repository-owned code and generated synthetic repositories. It did not access
CreativeDeploy or Customer 0, modify production, run aggregate
`make verify`, run Web E2E/Chaos/full Docker gates, use a remote, push, merge,
open a pull request, create a tag, deploy, or begin Phase 5.

Round 3 evidence was used only to locate claims. Every decision below comes
from current static inspection or a current independent command.

## Decision matrix

| Required scope                                  | Result             | Independent basis                                                                                                                 |
| ----------------------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| Original packed replacement reproduction        | **PASS**           | Unchanged original test passes `1/1`; polluted pre-existing mirror is rejected before the second Workspace is created.            |
| Distinct independent adversarial replacement    | **PASS**           | Packed replacement inserted after final mirror validation cannot alter actual checkout bytes; the next prepare rejects pollution. |
| New mirror and destination metadata/ref hygiene | **PASS**           | Empty-template normal case and six-case destination/source metadata matrix pass; raw top-level/ref validation is fail closed.     |
| Command/environment replacement disabling       | **PASS**           | Every production Git call reaches one fixed `shell=False` boundary with both defenses; hostile host Git variables do not win.     |
| Workspace semantic equality and quarantine      | **PARTIAL / FAIL** | Content/mode/symlink/gitlink equality and mismatch quarantine pass, but expected-manifest expanded path count is not bounded.     |
| Exact source object closure                     | **PASS**           | Nineteen-case object/ref/manifest focus and 58-case Workspace/Protocol target pass.                                               |
| Source invariance                               | **PASS**           | Strict target reports `119` entries, `10` Git objects, `2` status records, and `0` extension markers.                             |
| New Critical/High/blocking Medium               | **FAIL**           | One new Blocking Medium manifest-capacity defect is stable.                                                                       |
| Production-code invariance                      | **PASS**           | Audit diff contains no production path; frozen 72-file boundary is unchanged from the candidate.                                  |

## Original replacement reproduction

The unchanged
`test_focused_existing_mirror_packed_replace_cannot_change_checkout` now
passes. It prepares the approved second revision, adds a packed
`refs/replace/<approved>` mapping to the authorized ancestor, and requests a
second Workspace. Round 3 rejects the polluted mirror with a typed
Workspace error before the second Workspace path exists. The source revision
and approved source bytes remain unchanged.

This closes the exact exploit observed by the prior focused re-audit.

## Independent late-injection replacement scenario

The new
`test_single_finding_late_packed_replace_is_ignored_then_rejected` differs
from both the original finding and the repairer's tests:

1. it lets the actual production `prepare_mirror` finish its final validation;
2. it then injects packed replacement metadata before the actual production
   worktree checkout;
3. it sets hostile host `GIT_DIR`, `GIT_OBJECT_DIRECTORY`,
   `GIT_NO_REPLACE_OBJECTS=0`, and `GIT_REPLACE_REF_BASE` values;
4. it executes the complete `WorkspaceManager` prepare path; and
5. it requires exact approved bytes and registry creation for that in-flight
   checkout, followed by typed rejection of the still-polluted mirror on the
   next prepare.

The test passes `1/1` alone and remains the passing case beside the new
capacity failure after formatting. This confirms defense in depth across the
validation-to-checkout interval without assuming hostile same-UID concurrent
writers.

## Mirror metadata result

**CONFIRMED**:

- new mirrors use `git init --bare --template=` under the fixed environment;
- accepted top-level names are exactly `HEAD`, `config`, `objects`, `refs`,
  and optional Runner-generated `worktrees`;
- `HEAD` is a stable, single-link, mode-`0600` detached file containing only
  the exact authorized object ID;
- config is an exact stable managed payload with no include or replacement
  control;
- raw refs must be exactly empty `refs/heads` and `refs/tags`;
- top-level `packed-refs`, `hooks`, `logs`, `info`, `shallow`, loose refs,
  `refs/replace`, object alternates, and HTTP alternates are rejected;
- source packed replacement metadata is never copied; and
- destination objects remain the exact authorized reachable closure.

The Round 3 six-case replacement/manifest selection passes `6/6`; the broader
object/ref/manifest selection passes `19/19`.

## Replacement disabling result

Every production `subprocess.Popen` is in
`apps/runner/src/visual_engineer_runner/git_ops.py`. All fifteen `_run` call
sites use the same construction:

- argv begins with `git --no-replace-objects`;
- the replacement environment contains `GIT_NO_REPLACE_OBJECTS=1`;
- system/global configuration and host Git authority variables are not
  inherited;
- repository config cannot replace the exact managed config;
- `shell=False`;
- only Runner-owned mirror or Workspace paths reach Git; and
- source access remains the source-less parser, never a Git worktree,
  Git directory, object database, alternate, or fetch source.

The direct repair regression and the independent actual-prepare late
replacement test both pass.

## Workspace semantic-proof result

The semantic fields themselves are implemented and pass focused tests:

- source parser path bytes;
- directory, regular, symlink, and inert gitlink types;
- Git mode and executable bit;
- regular-file and symlink-target size;
- SHA-256 content/target digest;
- source-less expectation;
- descriptor-rooted `O_NOFOLLOW` traversal;
- single-link regular files;
- stable inode/mode/size/mtime and directory inventories;
- special-file rejection;
- inert non-recursive gitlinks;
- semantic mismatch rejection before ownership/registry creation; and
- atomic same-root quarantine preserving unexpected bytes.

The complete manager-path budget probe also confirms that the later actual
Workspace scanner rejects the over-budget checkout, removes its canonical
address, creates exactly one quarantine, and creates no registry.

The proof still fails its required capacity property. In
`SourceObjectClosure._walk_tree`, a cached tree returns before its entries are
charged again. `SourceObjectClosure._walk_checkout_manifest` then recursively
expands the same tree once per path but has no expanded-entry counter. The
actual scanner's counter is too late to bound construction of the expected
manifest.

For a binary shared-tree chain of depth `n` with one final blob, unique parsed
tree entries grow as `2n + 1`, while expanded manifest entries grow as
`3 * 2^n - 2`. At depth `20`, only `41` unique tree entries can expand to
`3,145,726` manifest entries, already above the default one-million limit and
large enough to threaten the declared 512 MiB Runner boundary.

## Source and object-closure invariance

Current independent evidence passes:

- strict source invariance:
  `extension_markers=0`, `source_entries_compared=119`,
  `source_git_objects_compared=10`, `source_status_records=2`;
- Round 3 replacement/manifest cases: `6 passed`;
- object/ref/manifest focus: `19 passed`;
- Workspace/Protocol target: `58 passed` plus the static isolation check; and
- original plus independent late replacement scenarios.

The complete blocking file is `1 failed, 11 passed`; only the new secure
manifest-budget assertion fails. The full Runner/Protocol target is
`1 failed, 76 passed` for the same single reason.

## New blocking issue

### Expanded checkout manifest bypasses its configured entry budget

- Scope: `VE-P4-FREAUD-001` Workspace semantic-proof capacity
- Severity: **Blocking Medium**
- Status: **OPEN / BLOCKING**
- Confidentiality impact: none reproduced
- Integrity impact: no unauthorized registered Workspace reproduced
- Availability impact: compact hostile Git DAG can amplify CPU/memory before
  the enforcement point, crash/restart the bounded Runner, and leave a
  canonical incomplete mirror requiring manual recovery

Required remediation is intentionally not prescribed or implemented here.
Any repair must charge every expanded manifest path against a strict budget
during source-less construction, preserve raw-path/type/mode/digest
semantics, avoid materializing an over-budget Workspace, retain Permit
freshness, and receive another independent focused review.

## Remaining non-blocking limitations

- Same-UID hostile concurrent Workspace mutation, hostile host/kernel/
  filesystem/runtime, and hostile multi-tenant isolation remain outside the
  declared sole-Runner-writer model.
- Portable Python still lacks `openat2`/`renameat2` pathname CAS.
- Legacy mirrors that do not match the Round 3 identity require manual
  recovery.
- Quarantine adjudication, privileged garbage collection, filesystem quotas,
  fleet admission, production identity/credentials, backup/restore, incident
  response, remote CI, and production deployment remain future work.
- Local focused tests do not prove remote CI, customer-repository behavior, or
  production safety.

## Final disposition

`SINGLE-FINDING RE-AUDIT COMPLETE — VE-P4-FREAUD-001 FAIL — REMEDIATION REQUIRED`

Do not merge Phase 4, access Customer 0, begin Phase 5, push, open a pull
request, tag, deliver, or deploy. The only safe next milestone is a narrow
manifest-capacity remediation followed by another independent
single-finding re-audit.
