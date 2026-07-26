# V1 Boundaries

## Product boundary

VisualEngineer accepts only Design Implementation, Design-System Migration,
and Frontend Quality Remediation work for governed frontend teams. V1 is not a
promise of arbitrary language, repository, backend, infrastructure, or general
software-engineering support.

## Implemented Foundation through Phase 3

- Task create/list/detail with bounded validation and idempotency.
- Level 0 `read_only` Run creation and durable state.
- One immutable committed-`HEAD` Snapshot per successful Run.
- Canonical local-path allowlist and exact Git-root enforcement.
- Fixed no-shell Git metadata/object reads; no credential prompt, hooks,
  network protocol, submodule initialization, or LFS fetch.
- Bounded selected-file facts, sensitive-file denial, and dirty/untracked path
  metadata without working-tree content reads.
- Stable Snapshot fingerprint from normalized committed inputs.
- `deterministic_policy` plan generation with no LLM.
- Typed display-only validation steps and `execution_available = false`.
- Editable plan revision, latest-plan submission, rejection reason,
  idempotency, stale conflict, and one transaction-safe final decision.
- Structured redacted audit events and a responsive review console.
- PostgreSQL migration history, generated contracts, synthetic security
  fixture, deterministic eval cases, and real-stack Playwright flows.
- Runner Protocol v1, registry, high-entropy digest-only credentials,
  heartbeat-derived online/offline state, and revocation.
- Server-derived immutable Permission Envelopes fixed to no repository, no
  shell, and Control-Plane-only network.
- PostgreSQL Jobs, Attempts, event timeline, `SKIP LOCKED` claim, leases,
  fencing, cancellation, retry budget, and lease reaper.
- Independent outbound Local Runner with only typed System Diagnostic and
  Controlled Wait executors.
- Browser Runner Registry, Dispatch, Job detail, progress, cancellation,
  results, offline/expired/requeue evidence, and Timeline.
- Non-root/read-only Runner container on a dedicated internal API-only network,
  plus real Runner E2E and chaos recovery.

## Reserved V1 seams

These remain deliberate future seams, not placeholder capabilities:

- an LLM/Agents SDK planning runtime;
- model invocation and model-specific evaluation;
- isolated worktree lifecycle and scoped file writes;
- typed execution tools and independent runtime policy enforcement;
- checkpoints, artifacts, detailed tool traces, and rollback;
- controlled target-repository install/build/test/lint/browser commands;
- separate final-change approval;
- branch, local commit, remote push, and pull request.

The current AuditEvent timeline is governance evidence, not a complete Agent
trace. Current plan string policy is Foundation validation, not a substitute
for future typed tool schemas and runtime authorization.

## Later versions

- Multiple users and organizations with role-based authorization.
- Concurrent scheduling, quotas, and model/provider routing.
- Rich design and design-system integrations.
- Visual regression baselines and learned bounded repair.
- Production observability, backup/restore, high availability, and disaster
  recovery.
- Broader source-control providers and governed release workflows.

## Explicitly out of scope in Phase 3

- Any LLM API or OpenAI Agents SDK.
- Generic shell or target-repository command execution.
- Reading dirty, untracked, sensitive, or symlink-target file content from the
  working tree.
- Target-repository writes, worktrees, dependency installation, code changes,
  Git state changes, or cleanup.
- Any target-repository mount, scan, read, locator, or file content in Runner;
  any CreativeDeploy access from Phase 3.
- GitHub credentials, clone, push, PR, merge, tag, or deployment.
- Automatic approval or treating plan approval as execution authority.
- Authentication, multi-tenancy, public exposure, or production use.
- Redis, Celery, Temporal, brokers, Kubernetes, or a gateway.
- Fake Agent scores, tool traces, execution states, or outcome metrics.
- Treating CreativeDeploy as external-customer or production-adoption proof.

## Boundary test

If a proposed change requires repository write access, executing a target
command, a credential, an LLM, an isolated worktree, a remote integration, or
an effect caused by plan approval, it is outside Phase 3. Repository read
access by Runner is also outside Phase 3. Each requires a new reviewed
milestone and explicit authority.
