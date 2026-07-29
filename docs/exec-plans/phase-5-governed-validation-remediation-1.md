# Phase 5 Targeted Security Remediation 1

- Started: 2026-07-29
- Branch: `fix/phase-5-governed-validation-remediation-1`
- Base focused-review checkpoint:
  `cd980582e9d950cb0176eae46ffaedd528ce0afe`
- Reviewed Phase 5 implementation:
  `1b6481156337c9f615240bf10dcca3f1e6833400`
- Main baseline:
  `928a89d2055d172bbd7c6670b42f668d103dcb03`
- Candidate status:
  `PHASE 5 TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`
- Remote CI: `NOT VERIFIED`

## Goal

Close the four confirmed Phase 5 remediation scopes in one maximum-safe local
candidate without expanding execution authority:

- `VE-P5-FSR-001` — leader-first timeout/process-group cleanup;
- `VE-P5-FSR-002` — cancellation must preserve typed cleanup/recovery failure;
- `P5-AUD-005` — Control Plane result identity and full execution-envelope
  binding; and
- `P5-AUD-006` — Control Plane output/artifact budget revalidation before
  terminal persistence.

The unchanged historical focused review remains FAIL. This implementation run
cannot close an independent Finding or declare a Security Gate PASS.

## Scope and invariants

Allowed changes are the Runner/API/Protocol/database code directly required by
the four scopes, permanent regressions, generated OpenAPI/TypeScript contract,
the Web contract fixture, the minimal mypy treatment for immutable audit
modules, and directly related architecture/threat/status/evidence documents.

The candidate does not add an LLM, Agents SDK, Provider, external credential,
user command, shell, package installation, source write, Git delivery,
CreativeDeploy, Customer 0, deployment, later Phase 5 slice, or Phase 6
capability.

The independent audit test files are unchanged. Main, implementation and audit
references remain fixed. No remote, push, merge, pull request or tag is
allowed.

## Four-scope matrix

| Scope           | Exact root cause                                                                                           | Candidate repair                                                                                                                                                                                                    | Permanent evidence                                                                                          |
| --------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `VE-P5-FSR-001` | Termination escalation stopped tracking after the leader exited, while a descendant retained the pipes.    | Track the process-group identity independently; enforce monotonic deadline and bounded group TERM/grace/KILL; prove group absence; reap the leader; close selector and streams.                                     | Leader-first TERM-ignoring descendant regression plus unchanged `P5-AUD-002`.                               |
| `VE-P5-FSR-002` | Cancellation swallowed typed `WorkspaceExecutionError` and acknowledged clean cancellation.                | Runner reports the typed failure with its consumed Permit. API permits only closed Validation recovery codes after `cancel_requested` and atomically persists Job/Permit failure plus Run/step `recovery_required`. | Fake lifecycle regression and real-PostgreSQL cancellation/failure/replay/zero-success-side-effect test.    |
| `P5-AUD-005`    | Completion validated outer Lease/Permit only and trusted the Runner's inner Result identity.               | Reconstruct and compare a versioned canonical envelope from locked persisted Job/Run/step/Attempt/Lease/Grant/Profile/revision/Checkpoint/policy/operation/argv/cwd/env/Permit records before terminal writes.      | Unchanged five-case audit plus permanent identity, fence, revoked Grant, rejection replay and legal replay. |
| `P5-AUD-006`    | Completion trusted Runner output/artifact totals and completed the Permit before independent revalidation. | Recompute combined UTF-8 output bytes, truncation consistency, artifact paths/type/count/single/total bytes, manifest digest and evidence digest before Result/Permit/Event success.                                | Unchanged two-case audit plus exact-limit, +1, combined, manifest, protocol metadata and replay tests.      |

## Trusted execution envelope

The result schema is versioned and includes only bounded evidence. The
canonical envelope digest binds:

- Runner, Runner Job, Validation Run, Validation step;
- Attempt, Lease and active Job pointer;
- exact Execution Grant ID/policy hash/status/expiry;
- Profile ID/version and source revision;
- Checkpoint ID/fingerprint and Validation policy digest;
- fixed `validate` operation, fixed argv digest, symbolic fixed cwd and fixed
  environment-allowlist digest;
- timeout/output/artifact budgets;
- Permit ID, sequence, operation digest, expiry and a separate fencing token.

The Runner computes the candidate digest from its exact assignment and Permit.
The Control Plane never accepts that as self-authenticating: it reconstructs
the same values from locked database records and the system-owned Profile.
Mismatch or missing evidence returns `409` before any success transition.

## Budget and evidence revalidation

The Control Plane:

1. recomputes `len(stdout.encode("utf-8")) +
len(stderr.encode("utf-8"))`;
2. rejects a value above the trusted limit;
3. requires any truncated result to retain exactly the trusted byte limit;
4. validates every artifact as a unique relative regular-file entry;
5. recomputes count, each size and total size using non-negative bounded
   integers;
6. recomputes the canonical manifest digest; and
7. recomputes the complete evidence digest after removing only its own digest
   field.

The only current Profile has an artifact budget of zero, so zero is its exact
legal boundary and every artifact is denied. Non-zero artifact transfer or
content retrieval remains future, separately authorized work.

## Transaction and rejection behavior

The active Job, Attempt, Grant, Validation Run/step and Permit are selected
with row locks in the completion transaction. Validation occurs before Permit
completion, terminal Result storage, success events or Evidence synchronization.

A rejected completion leaves:

- no succeeded Result;
- Permit not completed;
- no `job_succeeded` or `side_effect_permit_completed`;
- no terminal success Evidence;
- no duplicate run-budget charge; and
- canonical Workspace/source unchanged.

An identical rejected replay repeats the rejection without new terminal
writes. An identical legal terminal replay returns the stored result and
creates at most one Evidence/event/Permit transition.

## Migration and compatibility

Alembic revision
`20260729_0007_bind_validation_result_evidence` adds nullable additive columns
for the schema/step/revision/policy, fixed execution digests, Permit fence,
artifact manifest, execution envelope and evidence digest. New records always
populate them; nullable storage permits upgrade of any pre-remediation local
evidence without inventing historical digests.

OpenAPI and generated TypeScript are regenerated. The two independent audit
files remain runtime-tested but are excluded from mypy discovery because their
identical top-level module names collide under the repository's existing
non-package test layout.

## Verification plan

Completed focused gates:

- unchanged Runner audit plus Runner remediation regressions: `8 passed`;
- pure Protocol: `5 passed`;
- unchanged API focused audit: `8 passed`;
- permanent Control Plane remediation: `31 passed`;
- combined focused Validation selection: `40 passed`;
- complete API: `118 passed`;
- complete Runner/Protocol: `96 passed`;
- real PostgreSQL empty-database migration roundtrip: exit `0`;
- contracts, format, lint, Python/TypeScript typecheck, Web tests/build;
- Validation sandbox, source invariance, Phase 4 security regressions,
  Workspace security, E2E, Chaos, Security and Eval gates.

The final `make verify` returns exit `0`. Exact remediation, E2E and Chaos
resource inventories are zero. Git/reference and allowed-file checks remain
the last pre-commit action before the one authorized local commit.

## First failures preserved

- Original Runner audit: `2 failed, 4 passed`; each finding stable `3/3`.
- Original API third boundary: `1 passed, 7 failed`; `P5-AUD-005` and
  `P5-AUD-006` stable `3/3`, with HTTP `200`/succeeded and durable success
  side effects.
- First permanent Runner fixture used a one-second Lease below the Protocol
  minimum; corrected to two seconds.
- First valid API completion after the protocol repair lacked required
  evidence and correctly returned `409`; the fixture now constructs the real
  canonical binding.
- First populated-database migration downgrade reached 0006 then failed
  because historical downgrade constraints cannot accept extant Validation
  Permits. The disposable database was recreated empty and the full
  base/head/base/head roundtrip passed.
- First typecheck exposed identical independent-audit module names; the two
  immutable runtime-tested audit files are now excluded from mypy discovery.
- First contract check found expected OpenAPI drift; regenerated contracts
  pass.
- First format/lint/typecheck sequence found two Python format items, sorted
  exports and the Web evidence fixture missing new fields; each focused rerun
  passes.

## Exit criteria

Success requires:

- every focused and related gate passing;
- final `make verify` exit `0`;
- exact disposable resource inventories at zero;
- unchanged main/implementation/audit references;
- clean `git diff --check`;
- only the authorized single local commit; and
- no remote/push/merge/PR/tag or forbidden-project access.

The eligible final status is only:

`PHASE 5 TARGETED REMEDIATION COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`
