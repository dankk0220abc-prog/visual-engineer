# System Overview

VisualEngineer at the integrated Phase 7 and bilingual-console baseline is a local,
single-user governed planning, fixture-only isolated editing, fixed-Profile
validation, system-owned multi-step Suite, immutable final-review/readiness,
and confirmed recoverable local-delivery foundation. Solid nodes below are
implemented. Dashed nodes are future V1 boundaries.

```mermaid
flowchart TB
    H["Local human operator"]
    W["Next.js console"]
    A["FastAPI /api/v1"]
    D[("PostgreSQL")]
    S["Repository Scanner"]
    R["Exact allowlisted Git repository (read-only)"]
    P["Deterministic Plan Generator"]
    AP["Governed AI Plan Orchestrator"]
    FP["Deterministic fake Provider"]
    AE["System-owned AI Eval"]
    Q["Runner Registry / Queue / Lease Policy"]
    LR["Independent Local Runner"]
    E["Closed Typed Executors"]
    HND["Opaque Fixture Handle"]
    SRC["Exact read-only synthetic source"]
    M["Runner-owned bare mirror"]
    IW["Detached isolated Workspace"]
    VS["Disposable validation sandbox"]
    VE["Bounded ValidationEvidence"]
    RP["Immutable Review Package"]
    RD["Review Decision + Readiness"]
    DM["Immutable delivery manifest + Dispatch history"]
    LC["Deterministic local ref + commit proof"]
    O["OpenAPI and generated TypeScript"]

    H -->|"create Task and Run; revise or decide Plan"| W
    W -->|"typed HTTP"| A
    A -->|"transactional state and audit"| D
    A -->|"Level 0 scan request"| S
    S -->|"fixed Git reads of HEAD objects"| R
    A -->|"Task + Snapshot + package"| P
    A -->|"redacted bounded context + versioned Prompt"| AP
    AP -->|"strict typed request; no network or key"| FP
    FP -->|"strict typed Plan proposal"| AE
    AE -->|"Eval evidence + decision eligibility"| AP
    AP -->|"Prompt, Trace, Eval, request/response"| D
    A -->|"durable jobs, envelopes, attempts"| Q
    Q --> D
    LR -->|"outbound protocol v1"| Q
    LR --> E
    LR --> HND
    HND --> SRC
    LR --> M
    M --> IW
    E --> IW
    IW -->|"exact Checkpoint copy"| VS
    E -->|"fixed Profile only"| VS
    VS --> VE
    VE -->|"typed terminal result"| Q
    VE -->|"trusted ordered manifest"| RP
    H -->|"review and decide"| RD
    RP --> RD
    RD --> DM
    H -->|"confirm exact digest / bounded retry"| DM
    DM --> Q
    E --> LC
    LC -->|"terminal proof"| DM
    A -->|"source contract"| O
    O -->|"typed client input"| W

    subgraph Future["Future - not implemented"]
        B["Controlled browser validation"]
        G["GitHub pull request"]
        C["Target repository commands"]
    end

    IW -. "future separate authority" .-> C
    C -. "future evidence" .-> B
    C -. "future Git delivery approval" .-> G
```

## Implemented responsibilities

### Web

The web application renders Task/Run history, state, permission and snapshot
mode, committed repository intelligence, safety findings, deterministic Plan
versions, typed validation steps, decision controls, and the Audit Timeline.
It also renders Runner Registry, immutable Envelope previews, typed Dispatch,
Job/Attempt state, progress, cancellation, results, and RunnerJobEvent
Timeline. It owns no database, filesystem, Git, Docker, shell, Runner
credential, or target-repository access.

The Run surface also creates and renders one governed AI Plan request. It
shows the structured Plan, context references, Prompt version/digests,
redactions, Provider Trace, system-owned Eval results, freshness, terminal
states, and human approve/reject controls at desktop and narrow widths. It
contains no API-key, model, network, free-form operation, or execution control.

The `/validations` surface lists the fixed Profiles and one immutable Suite,
derives a pending validation-only Grant from an exact eligible Workspace
Checkpoint, preserves a separate human approve/reject decision, creates/
cancels a Validation Run or Suite Run, and renders ordered child timelines and
bounded aggregate Evidence. It has no step editor, command, argv, environment,
package, URL, or free-form tool input.

The `/reviews` surface selects only the latest successful Suite Result, renders
its immutable ordered Evidence Manifest and digests, rechecks freshness,
records one local-user Review Decision, and computes one deterministic
readiness verdict. It displays that Git and deployment authorization are
always false.

The `/deliveries` surface creates and separately decides one exact Delivery
Authorization, renders the immutable manifest and bounded diff before
dispatch, requires explicit digest confirmation, and shows terminal Dispatch
history, cancellation, error reason, safe retry, Runner evidence, and final
local commit proof. It has no ref, message, Git command, identity, credential,
remote, push, PR, tag, or deploy input.

### API

The API validates requests, preserves request IDs, applies stable error codes,
owns Run and Plan state policy, coordinates repository scanning, generates
deterministic plans, serializes final decisions, writes sanitized audit
events, and exports OpenAPI. Routes delegate to typed services and
repositories.

For governed AI planning, the API selects only structured committed-Snapshot
facts and manifest references within fixed byte/count budgets, redacts the
untrusted requirement, binds a versioned Prompt, invokes the deterministic
fake through the model-neutral Provider protocol, validates the closed Plan
schema/digest, runs independent Eval, persists immutable evidence, and
serializes the human handoff decision. It performs no Provider network call
and has no credential input.

The API also owns Runner bootstrap authentication, digest-only credential
verification, derived liveness, revocation, server-side Envelope derivation,
transactional claim, explicit Job/Attempt transitions, lease renewal,
cancellation, typed results/events, and lease recovery. It never executes a
Runner Job.

For delivery lifecycle, the API derives the manifest only from immutable
Authorization/Checkpoint state, serializes keyed dispatch and linear retry,
revalidates the original implementation Grant, and atomically creates each
Dispatch, Runner Job, state transition, and AuditEvent.

### Local Runner

The independent long-running Runner makes outbound calls only. It persists its
credential in a dedicated Docker volume, validates every Envelope, and invokes
one closed typed executor. System Diagnostic and Controlled Wait remain
repository-free. For Phase 4 only, Runner maps an opaque handle to the exact
read-only synthetic fixture, owns a bare mirror/detached worktree/registry, and
executes descriptor-safe UTF-8 file tools plus fixed Git status/diff/restore/
discard. It has no shell, arbitrary command, target command, Docker socket,
inbound port, database/Web network, or public network.

For Phase 5, Runner also owns a separate dedicated validation volume. It
verifies the exact canonical Workspace/Checkpoint, copies bounded fixture input
into a UUID-addressed root, and invokes one fixed Python-standard-library
Profile under Landlock filesystem confinement, seccomp network denial,
resource limits, monotonic timeout/cancel, bounded output, process-group
cleanup, and exact sandbox removal. It never runs a user command or mutates the
canonical Workspace.

The Control Plane, not Runner, owns Suite orchestration. It selects immutable
catalog steps and queues only one existing fixed-Profile child at a time. Each
child retains an independent Job, Attempt, Lease, Permit, result, Evidence, and
sandbox. Runner receives no Suite definition or caller-provided step.

For Phase 6, Runner independently recomputes the delivery manifest from the
current authenticated Workspace immediately before fixed Git plumbing. The
Job, Permit binding, result, and proof carry Dispatch ID, attempt number, and
manifest digest. Retry can reproduce only the same deterministic commit/ref;
it cannot widen authority or access a remote.

### Repository Scanner

The scanner:

1. expands and canonically resolves an absolute local path;
2. verifies allowlist membership, exact Git root, and non-symlink root;
3. uses fixed no-shell Git argument arrays with prompts, hooks, optional locks,
   global/system config, and network protocols disabled;
4. obtains branch, `HEAD`, bounded status paths, and the committed tree;
5. classifies entries before reading;
6. reads only policy-selected committed blobs by object ID;
7. rejects sensitive, binary, oversized, symlink, submodule, and LFS content;
   and
8. returns structured facts and a deterministic fingerprint.

No working-tree file is opened. Dirty/untracked content is not read.

### Deterministic Plan Generator

The generator uses only the Task, immutable Snapshot, selected delivery
package, and versioned product policy. It does not call a model. Plan
validation steps use a closed schema and are displayed rather than executed.
Revision validation is a bounded Foundation string policy; future execution
still requires typed tool schemas and an independent runtime policy layer.

### PostgreSQL

PostgreSQL stores Task, Run, RepositorySnapshot, Plan, ApprovalDecision,
AuditEvent, Runner, PermissionEnvelope, RunnerJob, RunnerJobAttempt,
RunnerJobEvent, RepositoryHandle, ExecutionGrant/Decision, Workspace/Event,
Checkpoint, ValidationRun, ValidationStepRun, ValidationEvidence,
ValidationSuiteRun, ValidationSuiteStepRun, ValidationSuiteResult,
ReviewPackage/Invalidation, ReviewDecision, ReleaseReadinessVerdict,
DeliveryAuthorization/Decision, DeliveryDispatch history, and LocalDelivery
proof.
Alembic owns schema history. Row locks and uniqueness serialize decisions,
claims, workspace actions, validation/Suite dispatch, terminal evidence, and
final review. Database triggers reject Snapshot, PermissionEnvelope, Execution
Grant policy, Checkpoint, validation evidence, Suite authority, terminal
aggregate, governed review mutation, Delivery Dispatch authority/lineage
mutation, and terminal Dispatch rewrites.

### Contract

FastAPI OpenAPI is authoritative. TypeScript types are generated from it.
Contract drift regenerates both artifacts and requires no diff.

## Governed request sequence

```mermaid
sequenceDiagram
    actor User
    participant Web
    participant API
    participant Git as Read-only Git repository
    participant DB as PostgreSQL

    User->>Web: Start read-only investigation
    Web->>API: Create Level 0 Run
    API->>DB: Run created + audit
    Web->>API: Create Snapshot
    API->>DB: Run snapshotting + audit
    API->>Git: Fixed metadata and committed-object reads
    Git-->>API: HEAD tree and selected blobs
    API->>DB: Immutable Snapshot + fingerprint + audit
    Web->>API: Create deterministic Plan
    API->>DB: Draft Plan bound to fingerprint
    User->>Web: Revise and submit exact version
    API->>DB: Supersede old draft; awaiting approval
    User->>Web: Approve or reject
    API->>DB: One final decision + terminal Phase 2 state
    Note over API,Git: No code or command execution follows approval
```

## Customer 0 deployment boundary

The historical Phase 2 Customer 0 override mounts only the exact CreativeDeploy repository into
the API at `/repositories/customer0/creative-deploy` with `read_only: true`.
The Web and database receive no repository mount. The API runs as a non-root
user. The host path is supplied only at invocation and is not committed.
The Phase 3 base platform and Phase 4 fixture Runner do not use this override
and do not mount, scan, read, or modify CreativeDeploy.

## Runner dispatch sequence

```mermaid
sequenceDiagram
    actor User
    participant Web
    participant API
    participant DB as PostgreSQL
    participant Runner

    Runner->>API: Register with bootstrap credential
    API->>DB: Runner identity + token digest
    API-->>Runner: Runner Token returned once
    Runner->>API: Heartbeat and bounded claim poll
    User->>Web: Review fixed Envelope and dispatch typed Job
    Web->>API: Job kind + closed parameters only
    API->>DB: Immutable Envelope + queued Job + event
    Runner->>API: Claim
    API->>DB: SKIP LOCKED claim + fenced Attempt
    Runner->>API: Validate Envelope; start; renew/progress
    User->>Web: Optionally request cancellation
    API->>DB: cancel_requested
    Runner->>API: Typed complete or cancelled acknowledgement
    API->>DB: Terminal state + sanitized evidence
```

## Phase 4 workspace sequence

```mermaid
sequenceDiagram
    actor User
    participant Web
    participant API
    participant DB as PostgreSQL
    participant Runner
    participant Source as Read-only fixture

    Runner->>API: Register opaque Handle + committed revision
    User->>Web: Create pending Grant from approved Plan
    User->>Web: Separately approve exact Grant
    API->>DB: Immutable policy + decision
    User->>Web: Create Workspace
    API->>DB: Bound typed prepare Job
    Runner->>Source: Verify read-only root and exact revision
    Runner->>Runner: Populate bare mirror; detached worktree
    Runner->>API: Fenced ready result + fingerprints
    User->>Web: Typed read/create/replace/status/diff
    API->>DB: Fenced results, events, checkpoints
    User->>Web: Baseline rollback; exact discard
    Runner->>API: Verified clean/discarded evidence
    Note over Source: HEAD, status, contents, and .git remain unchanged
```

The source, mirror, workspace, and registry mounts exist only in Runner. See
[`isolated-workspaces.md`](isolated-workspaces.md) for budgets and platform
limits.

## Phase 5 validation sequence

```mermaid
sequenceDiagram
    actor User
    participant Web
    participant API
    participant DB as PostgreSQL
    participant Runner
    participant Workspace as Canonical fixture Workspace
    participant Sandbox as Disposable validation root

    User->>Web: Select fixed Profile + exact Checkpoint
    Web->>API: Create pending validation-only Grant
    User->>Web: Separately approve exact Grant
    API->>DB: Immutable scope, budgets, and decision
    User->>Web: Create Validation Run
    API->>DB: Bound Run + Job + immutable Envelope
    Runner->>API: Fenced claim and start
    Runner->>Workspace: Verify exact tree and bounded regular input
    Runner->>Sandbox: Copy input; apply Landlock + seccomp + limits
    Runner->>Sandbox: Run fixed system-owned Profile
    Runner->>API: Bounded result + cleanup proof
    API->>DB: Terminal state + immutable evidence
    Note over Workspace: State and bytes remain unchanged
```

## Phase 5 final review sequence

```mermaid
sequenceDiagram
    actor User
    participant Web
    participant API
    participant DB as PostgreSQL

    User->>Web: Select latest successful Suite Result
    Web->>API: Create immutable Review Package
    API->>DB: Lock generation; reconstruct Evidence, policy, Grant, blockers
    DB-->>API: Canonical Manifest/package/blocker digests
    User->>Web: Recheck freshness and inspect exact Evidence
    User->>Web: Approve or reasoned reject
    API->>DB: Bind expected generation + keyed immutable Decision
    User->>Web: Compute Release Readiness
    API->>DB: Recompute full chain; require blocker counts 0/0/0
    API-->>Web: ready, not_ready, or effective stale
    Note over API,DB: Later trusted fact atomically invalidates old generation
    Note over Web,DB: Git and deployment authorization remain false
```

## Deployment posture

Compose is a local development and verification environment, not a production
deployment. Authentication, secrets management, tenant isolation, backups,
high availability, hardened networking, remote CI evidence, and production
operations remain unimplemented.

## Phase 6 governed local-delivery sequence

```mermaid
sequenceDiagram
    actor User
    participant Web
    participant API
    participant DB as PostgreSQL
    participant Runner
    participant Workspace as Runner-owned fixture Workspace

    User->>Web: Select fresh approved ready Review
    Web->>API: Create pending Delivery Authorization
    API->>DB: Bind exact generation, checkpoint, diff, ref, message
    User->>Web: Separately approve local commit
    Web->>API: Fetch manifest and bounded diff preview
    API-->>Web: Exact digest, path closure, zero-remote facts
    User->>Web: Confirm exact digest
    Web->>API: Keyed dispatch or latest terminal retry
    API->>DB: One Dispatch winner + Job + immutable manifest
    Runner->>API: Claim, start, acquire dual-bound Permit
    Runner->>Workspace: Recompute manifest; verify revision/tree/diff/budgets
    Runner->>Workspace: Fixed plumbing creates tree, commit, local ref
    Runner->>API: Dispatch/attempt/manifest-bound local-only proof
    API->>DB: Terminal Dispatch, Job, Permit, Authorization, LocalDelivery
    alt failed or cancelled and still fresh; attempts remain
        User->>Web: Review terminal reason and same manifest
        User->>Web: Confirm exact bounded retry
    end
    Note over Workspace: HEAD and file bytes stay unchanged
    Note over API,Runner: No remote, push, PR, tag, or deploy authority
```
