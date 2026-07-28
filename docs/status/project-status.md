# Project Status

- Phase: Phase 4 — Runner-Owned Isolated Workspace + Scoped Typed File Tools
- Overall status: IMPLEMENTED; INDEPENDENT SECURITY AUDIT COMPLETE; SECURITY
  GATE FAIL; MERGE AND CUSTOMER 0 BLOCKED; REMOTE CI NOT RUN
- Last updated: 2026-07-28
- Branch: `audit/phase-4-workspace-security-max`
- Phase 4 audited commit: `53dc2f5`
- Main: `7590f9d`
- Remote: none

## Product position

VisualEngineer is a governed AI design-engineering and delivery system limited
to Design Implementation, Design-System Migration, and Frontend Quality
Remediation packages.

Phase 2 provides durable Level 0 committed-repository investigation and
deterministic Plan approval. Phase 3 provides a browser-orchestrated outbound
Local Runner with typed repository-free Jobs, PostgreSQL leases, fencing,
cancellation, and recovery. Phase 4 adds Level 1 only for the versioned
synthetic fixture: a separate Execution Grant authorizes closed UTF-8 tools in
a Runner-owned isolated Workspace. Plan approval alone still causes no
execution.

CreativeDeploy remains internal Customer 0 and Design Partner 0, not an
external enterprise customer. Phase 4 does not mount, read, write, test, build,
clean, or otherwise access it.

## Implemented

- Runner-registered opaque Repository Handle with display/revision/dirty
  metadata and no Control Plane host path.
- Immutable Execution Grant and one independent local-user decision, bound to
  an approved exact Plan/Snapshot/revision and server-derived narrow policy.
- RepositoryHandle, Grant/Decision, Workspace/Event/Checkpoint persistence,
  RunnerJob bindings, additive reversible Alembic migration, and generated
  OpenAPI/TypeScript contracts.
- Workspace state machine, typed action APIs, request-ID idempotency, stable
  policy/conflict codes, and per-Lease authority revalidation.
- Runner-only exact fixture read-only bind plus dedicated persistent
  mirror/workspace/registry volumes; API, Web, and PostgreSQL get no mount.
- Fixed-argument no-shell Git boundary for source verification, managed bare
  mirror, detached exact-revision worktree, bounded status/diff, baseline
  restore, and disposal.
- Descriptor-rooted POSIX path parsing and no-follow directory walks;
  sensitive/symlink/hard-link/non-regular/binary/invalid/oversize denial.
- Atomic UTF-8 create/replace with expected absence/hash, inode check, fsync,
  post-write hash, interruption cleanup, and completed-write retry
  reconciliation.
- Eight closed Workspace jobs: prepare, list, read, write, status, diff,
  rollback, and discard.
- Immutable bounded Checkpoints, initial-baseline rollback with created-file
  ledger, and registry-bound exact idempotent discard.
- Repository, Execution Grant, Workspace list/detail, typed tool, write
  preflight, diff/checkpoint, and Timeline Web surfaces.
- Versioned adversarial fixture, real-stack seed/smoke/E2E/chaos harnesses,
  static workspace security checks, and 15-case deterministic workspace Eval
  dataset.

## Current local evidence

- Phase 3 was independently accepted: local verify/smoke/chaos passed, runtime
  isolation was inspected, and main fast-forwarded without a merge commit.
- Backend/API/Runner/Protocol suite: 105 passed with 82.29% combined coverage,
  one upstream Starlette/httpx deprecation warning, and no skips.
- Frontend unit suite: 39 passed with 72.11% statement, 66.56% branch, 71.89%
  function, and 74.15% line coverage.
- Real Playwright suite: 12 passed in the final aggregate gate. Phase 4 passed
  its browser flow at desktop and 390 px with axe and no-overflow checks.
- Workspace smoke completed the real prepare/read/replace/create/deny/status/
  diff/three-Checkpoint/rollback/discard flow and proved the full source plus
  `.git` fingerprint unchanged.
- Workspace chaos stopped Runner during prepare and before atomic commit,
  produced two Attempts for each interrupted Job, fenced two stale leases,
  recovered the complete write, rolled back, discarded with no residual
  Workspace, and preserved the full source fingerprint.
- Workspace security passed 25 focused tests and its static checker; the
  broader Runner security target passed 46 tests and secret scanning found no
  high-confidence secret.
- Contract drift, production Web build, all Compose variants, real PostgreSQL
  upgrade/downgrade/upgrade, and Eval validation (58 cases plus 7 scanner
  tests) passed.

The aggregate `make verify` passed. The independent audit target also passed
four closed synthetic observations, meaning the findings are reproducible.
The production hash remained unchanged.

The independent Security Gate is **FAIL** with three Critical, one High, one
Medium, and one Low finding. Strict source invariance failed on `.git`
directory metadata even though source content and all other captured Git state
remained exact. `main` was not merged. No remote CI result is claimed.

## Current boundaries

- Fixture Workspace writes only; source repository and CreativeDeploy writes
  are forbidden.
- No LLM, OpenAI Agents SDK, prompt-selected tools, or Agent Trace.
- No shell, arbitrary subprocess, target repository install/build/test/lint/
  typecheck/browser command, package lifecycle, or public network.
- No file delete/rename tool, binary write, submodule initialization, or LFS
  fetch.
- No target branch, commit, push, PR, merge, deployment, remote CI evidence,
  authentication, multi-tenancy, or production hardening.

## Known limitations

- Python does not expose portable `openat2`/`renameat2` pathname-CAS semantics.
  Phase 4 uses descriptor walks, no-follow/type/link/inode checks, and makes
  Runner the sole workspace-volume writer; it is not a hostile multi-tenant
  sandbox.
- Git output is bounded before persistence/return, but a child process may
  briefly allocate an over-budget diff before rejection.
- Case-collision fixture coverage is conditional on filesystem support.
- Workspace expiry precedes Grant expiry by ten minutes for typed discard. An
  expired or revoked Grant fences all Jobs, and Phase 4 has no privileged
  garbage collector.
- Local bearer tokens, Docker internal networking, and synthetic fixtures are
  development controls, not production identity or certification.
- The independent audit additionally blocks source-adapter execution surfaces,
  transactional authority fencing, registry/discard mismatch recovery, and
  exact source metadata invariance.

## Technical debt

- Track the upstream Starlette TestClient/httpx deprecation.
- Pin GitHub Actions to immutable commit SHAs before public/high-assurance use.
- Add filesystem quotas, streaming output bounds, authenticated identities,
  retention, backup/restore, and incident response before broader exposure.

## Recommended next milestone

Run a dedicated Phase 4 security-repair milestone for all Gate-blocking
findings and explicit Runner resource limits. Then freeze a new baseline and
repeat the independent audit. Do not merge, access Customer 0, or begin Phase
5 until a fresh Security Gate PASS.
