# V1 Boundaries

## Product boundary

VisualEngineer accepts only Design Implementation, Design-System Migration,
and Frontend Quality Remediation work for governed frontend teams. V1 is not a
promise of arbitrary language, repository, backend, infrastructure, or general
software-engineering support.

## Implemented Foundation through Phase 6 Second Vertical Slice

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
- Opaque Runner-registered Repository Handle for one exact read-only synthetic
  fixture without Control Plane host paths.
- Separate immutable and independently approved Execution Grant bound to the
  exact Plan, Snapshot, revision, operations, paths, budgets, and TTL.
- Runner-owned bare mirror, detached fixture Workspace, and registry in
  dedicated volumes unavailable to API, Web, and PostgreSQL.
- Descriptor-rooted bounded UTF-8 list/read/create/replace, fixed status/diff,
  Checkpoints, initial-baseline rollback, and exact idempotent discard.
- Browser surfaces and real-stack smoke/E2E/abrupt-loss recovery with full
  source and `.git` fingerprint comparison.
- Immutable system-owned multi-step Validation Suites with trusted ordered
  aggregate Evidence, bounded retry, cancellation, and zero-artifact policy.
- Immutable Review Packages with exact Evidence Manifests, stale invalidation,
  one local-user Review Decision, and deterministic Release Readiness Verdict.
- Explicit false Git/deployment authorization at package, decision, verdict,
  API, database, and browser boundaries.
- A separate immutable Delivery Authorization and local-user decision bound to
  one exact fresh Review generation, Workspace Checkpoint, tree/diff digest,
  source revision, system-derived branch ref, and fixed commit message.
- One closed `workspace_git_commit_v1` Runner Job with dual implementation
  Grant plus Delivery Authorization, a short-lived Side-effect Permit, fixed
  Git plumbing, durable local-commit proof, and source/remote invariance.
- A canonical immutable manifest and bounded diff preview, exact digest
  confirmation, keyed one-winner dispatch, durable terminal attempt history,
  cancellation, and at most three same-manifest linear attempts.
- Browser-visible attempt/error/recovery state and attributable Runner proof;
  revoked or expired implementation authority fails closed before retry.

## Reserved V1 seams

These remain deliberate future seams, not placeholder capabilities:

- an LLM/Agents SDK planning runtime;
- model invocation and model-specific evaluation;
- non-fixture isolated workspaces;
- controlled target-repository install/build/test/lint/browser commands;
- remote Git authorization, push, and pull request;
- tag, merge, release, and deployment workflows.

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

## Explicitly out of scope in the Phase 6 second slice

- Any LLM API or OpenAI Agents SDK.
- Generic shell or target-repository command execution.
- Reading dirty, untracked, sensitive, or symlink-target file content from the
  working tree.
- Source-repository or CreativeDeploy writes, dependency installation, target
  commands/tests/builds, or arbitrary cleanup.
- Any real customer repository mount in Runner; Phase 4 only mounts the
  versioned synthetic fixture read-only.
- GitHub credentials, clone/fetch, push, PR, merge, tag, or deployment.
- Automatic approval or treating plan approval as execution authority.
- Authentication, multi-tenancy, public exposure, or production use.
- Redis, Celery, Temporal, brokers, Kubernetes, or a gateway.
- Fake Agent scores, tool traces, execution states, or outcome metrics.
- Treating CreativeDeploy as external-customer or production-adoption proof.

## Boundary test

If a proposed change requires a real repository, source write, target command,
credential, LLM, remote integration, remote Git, or an effect caused by Plan
or Review approval alone, it is outside this Phase 6 slice. Each requires a
new reviewed milestone and explicit authority. The fixture's implementation
Grant, validation Grant, Review Decision, and opaque handle cannot be reused
to authorize it.
