# Phase 4 Independent Focused Security Re-Audit

- Review date: 2026-07-29
- Audit branch: `audit/phase-4-security-focused-reaudit-max`
- Candidate:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`
- Candidate parent / preserved re-audit:
  `b457b614bde6630fb50ff9546c92a4d6925ad38a`
- Decision:
  **FOCUSED RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED**

## Executive decision

Round 2 does not close the Phase 4 Security Gate. The focused review
independently passes the authenticated-discard, process-group, and
real-PostgreSQL Permit blocker scopes, but reproduces a new Critical path
within the exact-object-closure scope.

An existing managed mirror may store a Git replacement ref in
`packed-refs`. Mirror validation rejects loose `refs/replace` metadata but
does not reject the packed equivalent, and later Git subprocesses do not
disable replacement-object interpretation. The mirror can therefore contain
only the exact authorized object-ID closure and report the authorized
revision at `HEAD`, while checkout materializes the tree of a different
reachable commit. This breaks the exact authorized revision boundary.

The Critical result is stable in an additive independent audit test.
Accordingly, the final full Gate, aggregate `make verify`, full live Docker
isolation Gate, E2E, smoke, chaos, security, and Eval runs were intentionally
not executed. A passing local sub-gate cannot override this failure.

## Authority and scope

This review is limited to the four blocker scopes named by the work order:

1. `VE-P4-AUD-001` / `VE-P4-REAUD-001`: exact authorized Git object closure;
2. `VE-P4-AUD-003` / `VE-P4-REAUD-002`: authenticated discard proof;
3. `VE-P4-AUD-005` / `VE-P4-REAUD-003`: complete process-group deadline; and
4. `VE-P4-AUD-002`: real-PostgreSQL Side-effect Permit closure.

The review used only synthetic repositories, repository-owned tests, and the
disposable `test-db` service. It made no production implementation change.
It did not access a customer repository, use a remote, push, merge, open a
pull request, create a tag, run a target-repository command, deploy, or begin
Phase 5.

Round 2 implementation evidence was used only to locate claims and candidate
tests. Every decision below comes from current static inspection or a current
independent run.

## Finding matrix

| ID                                  | Severity        | Focused result | Decision basis                                                                                                                                             |
| ----------------------------------- | --------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `VE-P4-AUD-001` / `VE-P4-REAUD-001` | Critical        | **FAIL**       | New `VE-P4-FREAUD-001`: packed replacement metadata changes checkout semantics while the authorized object set and `HEAD` remain exact.                    |
| `VE-P4-AUD-003` / `VE-P4-REAUD-002` | High            | **PASS**       | Preserved and independent replay/root-replacement cases fail closed and preserve the replacement root, sibling, mirror, and source evidence.               |
| `VE-P4-AUD-005` / `VE-P4-REAUD-003` | Blocking Medium | **PASS**       | Preserved leader-first cases and an independent child-closes-output case prove deadline enforcement, group termination, and no delayed side effect.        |
| `VE-P4-AUD-002`                     | Critical        | **PASS**       | Thirteen real-PostgreSQL Workspace API tests pass, including an independent five-session simultaneous Permit consume case with one durable Permit lineage. |

Critical findings: **1**. High findings: **0**. Blocking Medium findings:
**0**. The Security Gate is therefore **FAIL**.

## `VE-P4-FREAUD-001`: packed replacement ref changes authorized checkout

- Severity: **Critical**
- Status: **OPEN / BLOCKING**
- Maps to: `VE-P4-AUD-001` / `VE-P4-REAUD-001`
- Affected boundary: existing Runner-owned mirror validation followed by
  fixed Git checkout/worktree operations

### Security invariant

Preparing an exact approved revision must materialize exactly that revision's
tree. No source or pre-existing mirror metadata may reinterpret an authorized
object ID, even if every object in the destination belongs to the approved
commit/ancestor/tree/blob closure.

### Independent reproduction

The additive audit test creates two synthetic commits, prepares the managed
mirror, and then records a replacement mapping from the approved second commit
to its first-commit ancestor in the mirror's `packed-refs`. It accepts either:

- a typed fail-closed rejection before workspace materialization; or
- successful materialization of the approved second revision's exact content.

The candidate instead returns success and materializes `original\n`, while
the approved revision contains `approved second revision\n`. The reported
authorized revision remains the second commit. The failure is deterministic
on the corrected assertion and is the sole failure in the ten-test blocking
reproduction file.

### Root cause

The source adapter rejects loose replacement metadata and validates the exact
object closure. Existing-mirror validation likewise checks managed config,
object formats, packs, loose objects, and loose replacement paths. It does not
reject replacement refs encoded in `packed-refs`. The Runner's Git subprocess
environment also does not set replacement interpretation off.

Because both commits already belong to the authorized ancestry closure, exact
destination object-ID equality does not detect the semantic indirection.

### Impact

A stale or tampered managed mirror can make a valid approved revision produce
unapproved workspace bytes without changing its requested commit ID. This
breaks Grant/revision binding, snapshot integrity, checkpoint provenance, and
the premise that downstream mutations operate on the approved baseline.

### Required remediation boundary

Production remediation is intentionally outside this audit. A repair must
make replacement metadata impossible at every accepted ref representation and
must ensure Runner-owned Git operations cannot interpret replacement objects.
The fix needs a fresh independent focused re-audit; this report does not
prescribe or approve a particular implementation.

## Focused PASS dispositions

### Authenticated discard proof

The original Round 2 re-audit cases pass. The independent completed-proof
replay test replaces the expected workspace root with a symlink after
legitimate completion and removes the mutable registry. Exact replay returns
`WORKSPACE_RECOVERY_REQUIRED`; the symlink, sibling target, mirror, and source
remain unchanged. No new High discard defect was reproduced.

### Complete process-group deadline

The original leader-first cases pass. The independent case starts a child
that closes inherited output, lets the process leader exit, and would create a
delayed marker if it survived. The operation returns a typed timeout, the
process group becomes absent, and the marker is never created. No new
blocking process-lifetime defect was reproduced.

### Side-effect Permit closure

The complete Workspace API file passes against the real repository-owned
PostgreSQL service. The independent case begins five consumers in five
independent database sessions behind one barrier. All converge on one Permit
UUID, one durable Permit row and event, sequence `1`, one non-replay consumer,
and four idempotent replays. No new Critical Permit defect was reproduced.

These PASS dispositions are limited to their named focused scopes. They are
not a release, merge, or Phase 5 approval.

## Source and production invariance

The dedicated source-invariance target exits zero with:

- `extension_markers=0`;
- `source_entries_compared=119`;
- `source_git_objects_compared=10`; and
- `source_status_records=2`.

The frozen production boundary contains 72 tracked files. Its pre-audit
current-content SHA-256 manifest digest is
`3ca1448901c572da082a75fb002da81b73b347974c753e8ef7b28f5a167787d3`;
the candidate Git-tree listing digest is
`be07a14623a65593d5f0c8ddd1a22219b3b7aa3f30f8ee7794206282f312c707`.
Both are rechecked before the local checkpoint. Only additive audit tests and
the authorized audit/status documents may differ from the candidate.

Source invariance proves that the synthetic source did not change during the
run. It does not prove that the resulting worktree corresponds to the
authorized revision, so it cannot close `VE-P4-FREAUD-001`.

## Stopped checks and verification limits

Because a stable Critical finding makes PASS impossible, the following are
**NOT VERIFIED** by this focused re-audit:

- final full format, lint, type, unit, build, contract, and migration Gate;
- aggregate `make verify`;
- full live Docker isolation and cleanup Gate;
- Web/browser E2E, workspace smoke, workspace chaos, security, and Eval;
- remote CI; and
- real customer-repository behavior.

The exact disposable `test-db` used by the focused Permit run was stopped and
removed. Pre-existing base platform services were not treated as audit
evidence and were not altered.

## Residual boundaries

This fixture-only local design still assumes a trusted single local operator,
a sole Runner writer, trusted host/kernel/filesystem/runtime, and no hostile
multi-tenant isolation. Portable Python still lacks the stronger
`openat2`/`renameat2` primitives discussed in the threat models. Production
identity, public-network policy, fleet quotas, privileged garbage collection,
quarantine adjudication, backup/restore, and incident response remain outside
Phase 4.

## Final disposition

`FOCUSED RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED`

Do not merge Phase 4, access Customer 0, begin Phase 5, push, open a pull
request, tag, deliver, or deploy. The only safe next milestone is a narrowly
scoped production remediation followed by a new independent focused
read-only security re-audit.
