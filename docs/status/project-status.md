# Project Status

- Phase: Phase 4 — Workspace Security Repair Candidate
- Overall status: REPAIR COMPLETE — READY FOR INDEPENDENT RE-AUDIT;
  INDEPENDENT SECURITY GATE REMAINS FAIL; NOT IN MAIN
- Last updated: 2026-07-28
- Repair branch: `fix/phase-4-security-remediation`
- Repair base / audit commit:
  `a560509b2018f86693e38e3646409f9e33841829`
- Phase 4 implementation:
  `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Remote: none
- Remote CI: not run

## Governance status

The independent maximum-depth audit completed with **Security Gate: FAIL**:
three Critical, one High, one Medium, and one Low finding. That report, its
severity assignments, and its failing source-invariance evidence are
preserved. This repair implementer cannot change the independent Gate.

The isolated repair branch addresses all six findings and prepares evidence
for another reviewer. A local passing result means only
`REPAIR COMPLETE — READY FOR INDEPENDENT RE-AUDIT`; it does not mean approved,
merged, Customer 0 ready, or production ready.

## Repair-candidate implementation

- `VE-P4-AUD-001`: source registration and mirror preparation invoke no Git
  process against source. A no-follow adapter validates direct HEAD/refs/
  ordinary objects and copies a bounded committed snapshot into new
  Runner-owned mirror inodes with no alternates. Bounds are enforced against
  opened source descriptors and the aggregate destination mirror.
- `VE-P4-AUD-002`: PostgreSQL-backed Side-effect Permits bind the current
  Runner, Job, Attempt, Lease, Grant, Workspace, operation and canonical
  digest, including the immutable authorization time window, immediately
  before prepare, create/replace, rollback, or discard.
  `revoke_requested` blocks new permits; effective `revoked` waits for
  in-flight permits to become terminal or expire.
- `VE-P4-AUD-003`: registry payloads and separate ownership manifests are
  domain-separated HMAC authenticated with a Runner-local mode-`0600` key.
  Missing proof enters `recovery_required`; inconsistent proof or unknown
  content enters `quarantined`; neither deletes.
- `VE-P4-AUD-004`: a strict no-follow harness compares source content,
  lstat/type metadata, branch, HEAD, refs, config, hooks, index, object
  inventory/inodes, and tracked/untracked hashes across the full lifecycle.
- `VE-P4-AUD-005`: Runner CPU, memory, PID, FD, Git streaming-output, timeout,
  and mirror object/byte bounds fail closed.
- `VE-P4-AUD-006`: in-scope external Compose images use immutable digests and
  GitHub Actions use full commit SHAs.

The API, database migration, pure Runner Protocol, generated OpenAPI/
TypeScript contract, browser surfaces, E2E/chaos harnesses, Make targets, CI
definition, threat models, architecture, ADRs, and runbooks are updated with
the same semantics.

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

## Verification status

The complete local command matrix, real-stack E2E/chaos, Docker runtime
inspection, strict source invariance, migrations, security/Eval checks, and
pre-checkpoint aggregate `make verify` produced passing evidence. Exact
commands, counts, coverage, warnings, failures and corrections are recorded in
`docs/evidence/phase-4-security-repair-verification.md`.

The immutable repair hash and required post-checkpoint reruns are authoritative
only in the final handoff because committed documentation cannot record its own
hash without changing it. Remote GitHub Actions are not run and must not be
inferred from the local CI definition.

## Remaining limitations

- A different reviewer has not performed the Phase 4 Independent Security
  Re-Audit.
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

**Phase 4 Independent Security Re-Audit**

Do not merge `main`, access CreativeDeploy/Customer 0, or begin Phase 5 before
that independent decision.
