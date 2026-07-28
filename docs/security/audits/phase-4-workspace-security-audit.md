# Phase 4 Workspace Security Audit

- Audit date: 2026-07-28 (Asia/Shanghai)
- Audited commit: `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Audit branch: `audit/phase-4-workspace-security-max`
- Independence: the auditor is not the Phase 4 implementer
- Status: COMPLETE
- Security Gate: FAIL

## Executive verdict

Phase 4 is not approved for merge or Customer 0. Three Critical and one High
finding block the Gate. One additional Medium and one Low finding require
follow-up before broader use. Production code remained byte-for-byte
unchanged during the audit.

CreativeDeploy access and writes remain prohibited. The audited capability is
limited to the versioned synthetic fixture.

## Scope and severity

The audit covers Repository Handles, Execution Grants, Lease fencing,
mirror/worktree ownership, descriptor-rooted typed tools, atomic writes,
checkpoint/rollback/discard/recovery, resource limits, Docker isolation,
source invariance, logs/events/results, and local supply-chain configuration.

Severity and Gate blocking follow the maximum-depth audit instruction:
Critical or High always block; unresolved Medium findings that affect the
fixture isolation boundary also block.

## Findings

| ID            | Severity | Component                       | Unauthorized side effect | Defensive evidence                       | Required remediation                                 | Gate |
| ------------- | -------- | ------------------------------- | ------------------------ | ---------------------------------------- | ---------------------------------------------------- | ---- |
| VE-P4-AUD-001 | Critical | Git source adapter              | confirmed                | closed synthetic regression observations | neutralize all source-controlled Git execution paths | yes  |
| VE-P4-AUD-002 | Critical | Grant/Lease side-effect fencing | confirmed                | closed in-process authority observation  | add transactional pre-side-effect authority fencing  | yes  |
| VE-P4-AUD-003 | High     | registry/discard recovery       | confirmed                | closed temporary Workspace observation   | fail closed on registry/disk ownership mismatch      | yes  |
| VE-P4-AUD-004 | Critical | fixture source invariance       | confirmed                | exact before/after source manifests      | eliminate all source `.git` metadata writes          | yes  |
| VE-P4-AUD-005 | Medium   | Runner resource isolation       | not demonstrated         | runtime inspection                       | enforce CPU, memory, PID, FD, and output bounds      | no   |
| VE-P4-AUD-006 | Low      | supply-chain reproducibility    | not demonstrated         | local configuration review               | pin immutable image and workflow references          | no   |

For `VE-P4-AUD-004`, the metadata change is confirmed, while attribution to
the exact lifecycle call is **NOT FULLY VERIFIED**. The acceptance condition
is nevertheless disproved and remains Gate-blocking.

## Filesystem and syscall audit

Source review and existing focused tests confirm descriptor-rooted walks,
no-follow/type/link checks, bounded UTF-8 operations, atomic publication,
`fsync`, rollback, and normal exact-registry discard behavior. The remaining
single-writer assumption and absence of portable `openat2`/`renameat2`
pathname-CAS remain explicit limitations. `VE-P4-AUD-003` blocks recovery
paths that cannot prove registry ownership.

## Mirror and source isolation

Runner-owned mirror/worktree volumes are isolated from API, Web, and
PostgreSQL. The source bind is Runner-only and read-only in Linux. Source
content, HEAD, refs, index, config, object content/inodes, status, and counts
remained exact. `VE-P4-AUD-001` and `VE-P4-AUD-004` still block this boundary.

## Authorization and fencing

Plan/Grant separation, canonical policy hashes, Lease/Attempt identifiers,
completion fencing, and request idempotency are implemented. The audit found
that the required authority condition is not transactional with the first
durable Workspace side effect; `VE-P4-AUD-002` blocks the Gate.

## Resource and network isolation

Runtime inspection verified Runner UID 10001, zero effective capabilities,
`no-new-privileges`, read-only rootfs/source, no Docker socket, no published
Runner port, Runner-only private state volumes, and an internal Runner/API
network with no default route. Runner reached API; DB and Web did not resolve
from Runner. No public-network probe was attempted.

`VE-P4-AUD-005` records that explicit CPU, memory, and PID limits are absent.
Output is bounded only after child-process capture in one Git path.

## New audit tests

Four additive tests under `apps/runner/tests/security_audit` use only temporary
synthetic repositories, temporary Workspaces, harmless markers, and
in-process assertions. They reproduce current defensive observations and
perform no external I/O. All four passed; a pass means the finding is
reproducible, not that the product Gate passes.

## Verification

See `docs/evidence/phase-4-security-audit-verification.md`. Every mandatory
command was rerun. The aggregate project gate passes, while the independent
strict source-invariance Gate fails.

## Git result

`main` remains at `7590f9dcecbf06371936ac0265cecb9f7a4438ca`; it was not
checked out, fast-forwarded, or merged. No remote is configured. The audit
evidence commit is created only after final staged review.

## Remaining risks

The audit will retain explicit conclusions for:

- no portable `openat2`/`renameat2` path-resolution CAS;
- the single Runner writer assumption;
- local bearer credentials;
- PostgreSQL polling;
- absent authentication and multi-tenancy;
- absent production deployment; and
- absent real customer repository write evidence.

## Proven capabilities

The independent audit accepts only these bounded facts:

- all mandatory project commands exit zero;
- the production baseline remains byte-for-byte unchanged;
- the inspected Docker mount, identity, capability, and network topology
  matches the declared synthetic-fixture boundary; and
- source content and Git state other than directory metadata remain exact.

## Recommended next milestone

Run a Phase 4 security-repair milestone for the four blocking findings plus
the resource-limit gap, then repeat this audit from a newly frozen production
baseline. Do not proceed to Customer 0, Phase 5, or merge before a fresh PASS.
