# Project Status

- Phase: Phase 4 — Security Remediation Round 2
- Overall status:
  `REMEDIATION ROUND 2 COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`
- Governance qualifier: HISTORICAL SECURITY GATE FAIL PRESERVED; NOT IN MAIN
- Last updated: 2026-07-28
- Round 2 branch: `fix/phase-4-security-remediation-2`
- Round 2 base / independent re-audit:
  `b457b614bde6630fb50ff9546c92a4d6925ad38a`
- Re-audit branch: `audit/phase-4-security-reaudit-max`
- Re-audited repair commit:
  `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c`
- Repair branch: `fix/phase-4-security-remediation`
- Repair base / audit commit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4 implementation:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Remote: none
- Remote CI: not run

## Governance status

The independent re-audit of the isolated security-repair commit completed with
**Security Gate: FAIL**. Three production defects are independently stable:

- `VE-P4-AUD-001` remains open because the source-less adapter copies an
  unreachable, unapproved source object into the Runner mirror.
- `VE-P4-AUD-003` remains open because registry/root absence without trusted
  signed pending-discard completion proof is reported as successful discard.
- `VE-P4-AUD-005` is a blocking Medium because a descendant that retains the
  output pipes can continue past the Git operation timeout after the process
  leader exits.

The first two defects are Critical and High; either alone requires FAIL. The
third is independently Gate-blocking within the declared local Runner
resource boundary. `VE-P4-AUD-002` is not independently closed because the
complete new concurrency/adversarial matrix was stopped after the Gate had
already failed. `VE-P4-AUD-004` and local `VE-P4-AUD-006` checks pass.

The original audit FAIL and the repair implementer's evidence remain preserved
history. Neither is rewritten as the current result.

## Round 2 remediation candidate

Round 2 locally implements the three production corrections required by the
independent re-audit:

- exact authorized commit/ancestor/tree/blob closure parsing and
  Runner-owned loose-object materialization, including bounded loose and
  packed OFS/REF delta input, without Git execution against the source;
- domain-separated signed pending/completed discard proof with exact
  registry, ownership, root device/inode, operation, Permit, Attempt, Lease,
  digest, and time-window binding; and
- monotonic complete-process-group monitoring after leader exit, with
  nonblocking pipes, bounded TERM/KILL escalation, reaping, and explicit
  termination failure.

The unchanged re-audit file now passes `7/7` locally. Additive Runner,
Protocol, source-invariance, and real-PostgreSQL Permit regressions also pass
their focused Round 2 runs. Every named non-aggregate local target, including
Docker, E2E `14/14`, both smoke targets, both chaos targets, security, and
Eval, has exited zero. Live Runner isolation was inspected in a uniquely
named disposable Compose project and its exact resources were removed.
The corrected complete post-documentation `make verify` rerun exited zero.
Final diff review then closed one further in-scope pack-directory enumeration
budget gap; focused, complete Runner/Protocol, and source-invariance reruns
pass, and the final post-correction aggregate rerun exited zero. Remote CI is
not run.

`VE-P4-AUD-002` received the previously missing real-PostgreSQL concurrency,
revocation, binding, crash-ordering, retry, lineage, and budget matrix. No new
production Permit defect was reproduced, so Round 2 does not change Permit
production code.

These are implementer-candidate facts only. The historical Security Gate
remains FAIL until a new independent focused re-audit makes a new decision.

## Preserved re-audit disposition

- `VE-P4-AUD-001`: **FAIL / UNRESOLVED.** Source registration and mirror
  preparation no longer invoke Git against the source, but object copying is
  not restricted to the authorized revision's reachable object closure.
- `VE-P4-AUD-002`: PostgreSQL-backed Side-effect Permits bind the current
  Runner, Job, Attempt, Lease, Grant, Workspace, operation and canonical
  digest, including the immutable authorization time window, immediately
  before prepare, create/replace, rollback, or discard.
  `revoke_requested` blocks new permits; effective `revoked` waits for
  in-flight permits to become terminal or expire. Focused real PostgreSQL
  evidence passes; complete independent closure is **NOT VERIFIED**.
- `VE-P4-AUD-003`: **FAIL / UNRESOLVED.** Registry payloads and ownership
  manifests are authenticated in normal paths, but absence of both registry
  and expected root can still return idempotent success without trusted signed
  pending-discard evidence.
- `VE-P4-AUD-004`: **PASS** for the independently executed strict synthetic
  source-invariance harness.
- `VE-P4-AUD-005`: **FAIL / BLOCKING MEDIUM.** Live Runner CPU, memory, PID,
  FD, rootfs, capability and network controls pass, but timeout/process-group
  enforcement does not.
- `VE-P4-AUD-006`: in-scope external Compose images use immutable digests and
  GitHub Actions use full commit SHAs. Local configuration is **PASS**; remote
  CI is **NOT VERIFIED**.

The API, database migration, pure Runner Protocol, generated OpenAPI/
TypeScript contract, browser surfaces, E2E/chaos harnesses, Make targets, CI
definition, threat models, architecture, ADRs, and runbooks remain part of the
historical first-repair candidate. This section records the independent
re-audit result at `b457b61`; it is intentionally not rewritten by Round 2.

## Product boundary

Implemented Phase 4 remains fixture-only Level 1:

- independently decided exact Execution Grant;
- opaque synthetic Repository Handle;
- closed prepare/list/read/create/replace/status/diff/rollback/discard jobs;
- descriptor-rooted bounded UTF-8 operations;
- immutable Checkpoints and initial-baseline rollback;
- Runner-only private mirror/workspace/registry/credential volumes; and
- outbound API-only Runner control transport.

Explicitly absent: LLM, OpenAI Agents SDK, Agent Trace, shell, arbitrary
subprocess, target repository command/build/test, delete/rename/binary tool,
source write, Git delivery, branch/commit/push/PR, remote CI evidence,
authentication, multi-tenancy, public hosting, and production deployment.

CreativeDeploy is not authorized for this repair and was not mounted,
accessed, read, written, built, tested, or cleaned.

## Preserved re-audit verification status

The current re-audit evidence includes stable minimal filesystem/process
reproductions, a strict independent source-invariance run, real PostgreSQL
migration and eight-test Workspace API execution, 35 focused
Runner/Protocol tests, contract drift checks, Compose rendering, live Docker
isolation inspection, and final production-boundary hash comparisons.

The three-test first run also exposed a missing audit-test exception import.
That test-only `NameError` is preserved, classified separately, corrected only
in the audit test, and rerun. The corrected complete test file produces
`3 failed, 4 passed`: the failures are the three intended secure assertions
against current production behavior.

Full Web/browser/E2E/smoke/chaos/security/Eval and aggregate `make verify` were
not continued because the Critical, High, and blocking Medium reproductions
already make Security Gate PASS impossible. They are **NOT VERIFIED** in the
current re-audit and are not inferred from repair evidence.

Exact commands, exit codes, counts, first failures, root causes, corrections,
runtime facts, and stopped-check rationale are in
`docs/evidence/phase-4-security-reaudit-verification.md`.

Round 2 commands, counts, production/source invariance, PostgreSQL ordering,
Docker evidence, and final Git state are recorded separately in
`docs/evidence/phase-4-security-remediation-2-verification.md`.

## Remaining limitations

- Round 2 corrections still require a fresh independent focused re-audit;
  local implementation evidence cannot approve them.
- The Permit matrix is locally exercised but still requires independent
  closure as part of that re-audit.
- Python does not expose portable `openat2`/`renameat2` pathname-CAS; the
  implementation retains descriptor-rooted no-follow checks and a sole
  Runner-Writer assumption.
- Local bearer credentials, HMAC ownership, Docker networking, PostgreSQL
  polling, and synthetic fixtures are development controls, not hostile
  multi-tenant or production identity/isolation.
- No privileged garbage collector or automatic quarantine adjudication exists.
- Filesystem quotas, fleet admission, production credential lifecycle,
  backup/restore, incident response, and public deployment remain future work.

## Recommended next milestone

**Phase 4 Independent Focused Security Re-Audit**. Round 2 implementer
evidence cannot make that independent decision.

Do not merge `main`, access CreativeDeploy/Customer 0, push, create a pull
request, or begin Phase 5 before a fresh independent PASS.

`REMEDIATION ROUND 2 COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`
