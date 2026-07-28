# Phase 4 Independent Security Re-Audit

- Re-audit date: 2026-07-28 (Asia/Shanghai)
- Repair commit:
  `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c`
- Re-audit branch: `audit/phase-4-security-reaudit-max`
- Independence: the auditor did not implement the Phase 4 security repair
- Status: COMPLETE
- Security Gate: **FAIL**
- Required next state: **REMEDIATION REQUIRED**

## Executive verdict

The repair candidate is not approved for merge, Customer 0, Phase 5, or
production use. Independent tests stably reproduce three production defects:

1. the source-less Git adapter imports an unreachable, unapproved loose object
   into the Runner mirror;
2. discard reports idempotent success when both the mutable registry and
   original Workspace root are absent even though no trusted signed
   pending-discard proof exists; and
3. the Git subprocess output collector can miss its timeout after the process
   leader exits while another process keeps the pipes open, leaving the process
   group able to continue past the deadline.

These results leave `VE-P4-AUD-001` and `VE-P4-AUD-003` open and make the
resource-boundary regression under `VE-P4-AUD-005` a blocking Medium. The
Security Gate therefore fails without relying on any unexecuted aggregate
gate.

No production implementation was changed during this re-audit.

## Trusted Git baseline

The independently confirmed ancestry is:

`main 7590f9d` → `Phase 4 53dc2f5` → `audit a560509` → `repair e3d6530`

The repair is exactly one commit after the original audit. Its subject is
`fix(security): close phase 4 workspace audit findings`. The independently
observed repair diff contains 68 files, 7,501 insertions, and 571 deletions and
passes `git diff --check`.

The initial repair worktree and index were clean. No remote, stash, submodule,
additional worktree, replace ref, hidden special ref, or untracked/local patch
was found. The re-audit branch was created directly from the full repair hash.

## Independence and invariance boundary

The frozen production boundary is:

- `apps/api/src`
- `apps/runner/src`
- `packages/runner-protocol/src`
- `compose.yaml`
- `infra`
- `apps/api/alembic`
- `apps/api/Dockerfile`
- `apps/runner/Dockerfile`

At the repair commit it contains 71 tracked files. Its initial independent
SHA-256 worktree content-manifest digest is
`3d86a5d2d423a73a3819d06e45289a6e1050d09b96595577f16c4aee94fc3147`;
its Git-tree listing digest is
`eacd9a8f554c63832c67b17ea43a23657ce9fee25e23cf606d23870a2ebe89a8`.

The only re-audit changes are an additive independent test and re-audit
documentation. Final pre- and post-checkpoint comparisons are recorded in
`docs/evidence/phase-4-security-reaudit-verification.md`.

CreativeDeploy was outside scope and was not accessed, mounted, scanned,
built, tested, modified, or cleaned.

## Original six-Finding re-audit matrix

| Finding         | Severity | Original attack and reproduction                                                                                                                      | Repair control and code area                                                                                                                                                                                              | Independent review and dynamic evidence                                                                                                                                                                                                                                                                                                                                                           | Source/disk effects                                                                                                                                                                                                   | Remaining risk and conclusion                                                                                                                                                                                                               | Gate                                    |
| --------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `VE-P4-AUD-001` | Critical | Source-controlled Git extension behavior executed during source inspection/mirror preparation; the original audit captured harmless external markers. | Source-less ordinary-layout reader and bounded object copy in `apps/runner/src/visual_engineer_runner/git_ops.py`. Contract requires only the approved revision's committed reachable closure in new Runner-owned inodes. | Original repaired helper regressions pass, but the new `test_reaudit_unreachable_uncommitted_object_is_not_imported_into_mirror` fails consistently. Static review shows `_copy_source_objects` enumerates every regular loose/pack object entry without selecting the approved revision's reachable closure.                                                                                     | The unapproved file is absent from the Workspace, but its unreachable loose object is present in the Runner mirror. The generated source fixture remains audit-owned and temporary.                                   | Unapproved or sensitive object content already present in the source object database can be retained in Runner storage despite not belonging to the authorized revision. **FAIL; UNRESOLVED.**                                              | Blocking                                |
| `VE-P4-AUD-002` | Critical | Revocation could occur after lifecycle start but before the durable file mutation, allowing the mutation before completion was rejected.              | PostgreSQL Side-effect Permit model, locking/consume paths, Runner boundary validation, immutable bindings, and requested/effective revocation semantics.                                                                 | Static review found the expected binding fields and boundary validation. Eight real PostgreSQL Workspace API tests pass, including focused two-session acquire/revoke coverage. A new, separately authored full concurrent consume/crash/cancellation matrix was not completed after the Gate had already failed.                                                                                 | The focused tests report no unauthorized disk mutation; broader independent side-effect proof was not completed.                                                                                                      | Repair controls have supporting focused evidence, but the complete independent closure requirement is not established. **NOT VERIFIED; remains unclosed for this Gate.**                                                                    | Blocking by missing independent closure |
| `VE-P4-AUD-003` | High     | With registry ownership evidence missing, discard could infer ownership and remove unknown ignored content.                                           | Authenticated registry, separate signed ownership manifest, recovery/quarantine states, inventory validation, and discard flow in `workspace_manager.py` and ownership support.                                           | The new `test_reaudit_registry_loss_and_absent_root_requires_signed_recovery_proof` fails consistently. Static review shows `_discard_without_registry` returns idempotent success solely because the expected root path is absent; it does not require a trusted signed pending-discard record.                                                                                                  | The audit preserves the moved synthetic Workspace root; no source, mirror, sibling, or external path is deleted. The defect is a false successful discard/state transition rather than deletion in this reproduction. | Loss or unexplained relocation of local state can be misreported as authenticated completion, suppressing required recovery/quarantine handling. **FAIL; UNRESOLVED.**                                                                      | Blocking                                |
| `VE-P4-AUD-004` | Critical | The original lifecycle changed source `.git` directory metadata even though content and Git state remained stable.                                    | Elimination of source Git execution plus a strict no-follow lifecycle manifest in `scripts/check_source_invariance.py`.                                                                                                   | An independent current run of `make source-invariance-check` exits 0 with 119 source entries, 10 source Git objects, two status records, and zero extension markers compared.                                                                                                                                                                                                                     | Exact source/source-`.git` manifest comparison passes for the dedicated synthetic lifecycle. The object-closure failure above imports an object but does not mutate the source fixture.                               | The dedicated Finding contract is independently satisfied within its synthetic supported layout. **PASS.** This does not override `VE-P4-AUD-001`.                                                                                          | Non-blocking                            |
| `VE-P4-AUD-005` | Medium   | Explicit CPU/memory/PID limits were absent and one child-output path was bounded only after capture.                                                  | Compose CPU, memory, PID, FD controls; streaming combined-output limit; timeout/process-group termination; mirror object/byte bounds.                                                                                     | Live limits are present and effective. The new `test_reaudit_timeout_kills_process_group_after_leader_exits` fails consistently: the collector does not raise at the deadline after the leader exits while a descendant keeps the pipes open. Static review identifies a blocking read after a synthetic read event and an early return from group termination when the leader is already reaped. | The audit child writes only a temporary marker after the missed deadline and then exits; test cleanup is bounded. No production repository is touched.                                                                | A bounded Git operation can exceed its declared deadline and permit descendant execution beyond it. Within the V1 Runner resource boundary this is a **blocking Medium FAIL**. Host/fleet quotas remain a separate non-blocking limitation. | Blocking                                |
| `VE-P4-AUD-006` | Low      | Mutable Compose image tags and GitHub Action major references weakened reproducibility.                                                               | Digest-pinned external images and full-SHA GitHub Actions references plus a local checker.                                                                                                                                | Independent configuration search finds the Postgres digest and full Action SHAs; `make docker-config` renders every declared profile successfully; the static Finding checker reports all six repair controls present while preserving the independent FAIL.                                                                                                                                      | Configuration-only checks cause no source or Workspace side effect.                                                                                                                                                   | Local immutable-reference contract is **PASS**. Remote CI execution and upstream artifact provenance are **NOT VERIFIED** and are not inferred.                                                                                             | Non-blocking                            |

## New defect records

The re-audit uses three local defect records. They refine original Findings;
they do not replace or renumber the preserved audit history.

| Re-audit record   | Maps to         | Severity        | Test                                                                        | Trigger condition                                                                               | Expected / actual                                                                                               | Exit |
| ----------------- | --------------- | --------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ---: |
| `VE-P4-REAUD-001` | `VE-P4-AUD-001` | Critical        | `test_reaudit_unreachable_uncommitted_object_is_not_imported_into_mirror`   | An object exists in the source object database but is not reachable from the approved revision. | Expected: object absent from mirror. Actual: object copied into mirror.                                         |    1 |
| `VE-P4-REAUD-002` | `VE-P4-AUD-003` | High            | `test_reaudit_registry_loss_and_absent_root_requires_signed_recovery_proof` | Registry and expected root are absent without trusted signed pending-discard completion proof.  | Expected: `WORKSPACE_RECOVERY_REQUIRED` or quarantine. Actual: discard reports success.                         |    1 |
| `VE-P4-REAUD-003` | `VE-P4-AUD-005` | Blocking Medium | `test_reaudit_timeout_kills_process_group_after_leader_exits`               | Process leader exits while a descendant keeps captured pipes open beyond the timeout.           | Expected: timeout error and terminated group. Actual: no timeout error; descendant continues past the deadline. |    1 |

The complete reproducible assertions are kept only in the independent audit
test file. The evidence document records execution results without expanding
the attack procedure.

## NameError correction ledger

The first focused run selected three new tests. The first two reached
production assertions and failed. The third stopped in audit test code with
`NameError: GitOperationError is not defined`.

- Classification: audit-test defect, not a production Finding.
- Root cause: the existing import named `GitOperations` but omitted
  `GitOperationError`, which the new expectation referenced.
- Allowed correction: add only `GitOperationError` to that audit test import.
- Production change: none.
- Focused rerun: no `NameError`; the test reaches production behavior and
  fails because the expected timeout exception is not raised.
- Stable full-file rerun: four preserved repair regressions pass and all three
  new re-audit assertions fail (`3 failed, 4 passed`, exit 1).

## Source, authorization, ownership, and resource conclusions

- **Source invariance: PASS** for the independently executed strict synthetic
  lifecycle. This is narrower than the mirror-content authorization failure in
  `VE-P4-AUD-001`.
- **Side-effect authorization: NOT VERIFIED** as a complete independent
  closure. Focused real PostgreSQL tests pass, but the required separately
  authored full concurrency/adversarial matrix was stopped after the Gate
  failed.
- **Ownership/discard: FAIL.** Absence of local paths is not trusted evidence
  of completed discard.
- **Resource isolation: FAIL.** Container limits are active, but subprocess
  timeout/process-group enforcement is not complete.
- **Supply-chain configuration: PASS locally; remote CI NOT VERIFIED.**

## PostgreSQL, API, Protocol, contracts, and Docker

Real PostgreSQL migration downgrade/upgrade/re-upgrade succeeds. The focused
Workspace API file passes eight tests against the real test database,
including database constraints/triggers and two-session Permit/revocation
coverage. The live API health endpoint returns 200. Protocol and descriptor
boundary tests pass 35 cases. Generated OpenAPI/TypeScript contracts show no
drift.

The live Runner uses UID/GID 10001, read-only rootfs, zero effective
capabilities, `no-new-privileges`, one CPU, 512 MiB memory, PID limit 128, and
FD limit 256. Its fixture bind is read-only, private state volumes are
Runner-only, no Docker socket or published Runner port exists, DB/Web DNS is
unresolved, and the Runner has no default route. API, Web, and DB do not carry
source, Workspace, mirror, registry, or credential mounts. The ownership key
is in the credential volume with mode 0600, UID/GID 10001, and size 32 bytes.

These passing components do not offset the three blocking defects.

## Checks intentionally stopped after Gate failure

The complete Web build/browser E2E, smoke, runner/workspace chaos, full
security/Eval suites, `workspace-security-repair-check`, full project tests,
and final aggregate `make verify` were not continued in this re-audit. The
reason is not convenience or an attempt to manufacture a partial PASS:
independently stable Critical, High, and blocking Medium production failures
already make PASS impossible, while those downstream commands would not close
the reproduced defects.

Their repair-implementer results remain untrusted historical claims. This
report makes no current PASS claim for the stopped checks.

## Remaining limitations ledger

- Narrow ordinary Git layout: acceptable only when unsupported layouts fail
  closed; it does not excuse importing unreachable objects.
- Consumed-Permit execution window and complete crash/concurrency behavior:
  **NOT VERIFIED** in this re-audit.
- Manual recovery/quarantine adjudication: non-blocking within local V1 only
  if entry into those states fails closed; the reproduced discard fallback
  currently violates that prerequisite.
- Host administrator trust and no host/fleet quota: accepted local V1 trust
  boundary / non-blocking follow-up. The process-group timeout defect is a
  separate blocking Medium.
- No portable `openat2`/`renameat2`, sole Runner writer, and
  `case_collision_supported=false`: accepted only for the declared local,
  synthetic, non-hostile V1 boundary; broader safety is not claimed.
- Real customer repository behavior, hostile code, hostile multi-tenancy,
  public deployment, and remote CI: **NOT VERIFIED** and outside this audit.

## Final decision

- Confirmed open Critical: 1
- Additional Critical not independently closed: 1
- Confirmed open High: 1
- Confirmed blocking Medium: 1
- Local Low closure: 1
- Security Gate: **FAIL**
- Merge/push/PR: **NO**
- Main modification: **NO**
- CreativeDeploy access: **NO**

The minimum next milestone is a narrowly scoped production remediation for
reachable-object closure, authenticated pending-discard recovery, and robust
process-group timeout enforcement, followed by a fresh independent focused
re-audit. The Side-effect Permit Finding must also receive complete
independent closure evidence before any PASS decision.

**RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED**
