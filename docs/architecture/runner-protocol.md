# Runner Protocol v1

## Purpose and boundary

Runner Protocol v1 is the versioned contract between the VisualEngineer
Control Plane and a Local Runner. It supports registration, liveness,
dispatch, fenced attempts, progress, cancellation, typed terminal results, and
Phase 4's closed fixture Workspace jobs plus Phase 5's one fixed fixture
validation Profile. It never carries a host repository path, user command,
arbitrary subprocess, LLM message, or Agent trace.

The canonical Python contract lives in `packages/runner-protocol/`. That package
contains only Pydantic schemas, enums, constants, canonical serialization,
Permission Envelope hashing, typed results, validation, and stable error codes.
It imports neither FastAPI/SQLAlchemy nor either application.

Protocol version is `1`. Runner routes use:

```text
/api/v1/runner-protocol/v1
```

## Identity

`POST /register` uses the local high-entropy Bootstrap Token. The API compares
it in constant time, creates an independent random Runner Token of at least
256 bits, returns that token once, and stores only a SHA-256 digest. SHA-256 is
appropriate here because the input is a uniformly random high-entropy token;
it is not a password-hashing design.

Every other route uses the Runner Token as a Bearer credential. The Runner ID
inside the typed body must equal the identity selected by that token. Invalid
tokens return a stable `401`; an identity mismatch or revoked Runner returns
`403` without exposing credential or lookup details.

## Closed endpoints

| Method and path                          | Purpose                                             |
| ---------------------------------------- | --------------------------------------------------- |
| `POST /register`                         | One-time local registration and credential issuance |
| `POST /heartbeat`                        | Refresh derived liveness without event flooding     |
| `POST /jobs/claim`                       | Atomically claim one compatible queued Job          |
| `POST /jobs/{job_id}/start`              | Move the active fenced Attempt to running           |
| `POST /jobs/{job_id}/renew`              | Extend a lease and observe cancellation             |
| `POST /jobs/{job_id}/side-effect-permit` | Acquire current exact mutation authority            |
| `POST /jobs/{job_id}/events`             | Append one typed, bounded progress event            |
| `POST /jobs/{job_id}/complete`           | Validate and persist one typed result               |
| `POST /jobs/{job_id}/fail`               | Persist one closed failure classification           |
| `POST /jobs/{job_id}/cancelled`          | Acknowledge cancellation                            |

Mutations carry `X-Request-ID`. Runner payloads are strict, reject extra fields,
and are limited to 64 KiB before protocol validation. Results are independently
limited by the immutable Envelope.

## Job assignments

A claim returns either no assignment or:

- Job, Attempt, and Lease UUIDs;
- a positive attempt number;
- one strict Job spec;
- one immutable Permission Envelope;
- the current lease deadline.

Every Attempt mutation repeats `runner_id`, `attempt_id`, and `lease_id`.
Control Plane row locks verify all three, the active Attempt pointer, lease
deadline, Runner status, and legal transition. An expired, superseded, or
mismatched identity returns `409 stale_lease` and cannot change the Job.

Claim is transactional and uses PostgreSQL `FOR UPDATE SKIP LOCKED`. A partial
unique index permits at most one `leased` or `running` Attempt per Job.

## Permission Envelope

The browser never submits an Envelope. The Control Plane derives one from the
closed Job kind. Repository-free Jobs fix:

```text
repository_access = none
shell_access = false
network_policy = control_plane_only
```

It also binds capability, maximum runtime, lease duration, retry count, result
bytes, issue/expiry timestamps, and authorization source. Canonical JSON uses
sorted keys, compact separators, normalized JSON values, and excludes
`policy_hash` from its own digest input. The SHA-256 policy hash is tamper
evidence, not a signature.

The Runner recomputes the hash and validates version, expiry, capability, and
every fixed authority field before it starts. A Deployment Pack cannot expand
these values.

Workspace Jobs instead fix
`repository_access=isolated_workspace`, preserve shell false and
Control-Plane-only transport, and bind one immutable Execution Grant,
Repository Handle, Workspace, source revision, and Grant policy hash. The
Grant itself fixes network `none`, source write false, Git delivery false,
paths, operations, budgets, and expiry. Control Plane revalidates approved
status and all bindings at claim/start/renew/progress/terminal mutation. That
lease-level revalidation is necessary but not sufficient for filesystem
mutation.

## Side-effect Permit

Prepare, text create/replace, rollback, and discard specs produce a canonical
operation description. Immediately before mutation, Runner posts the current
Runner/Attempt/Lease identity plus that description to
`/jobs/{job_id}/side-effect-permit`.

The Control Plane locks and validates all current authority and returns a
strict `SideEffectPermit` bound to:

- Permit, Runner, Job, Attempt, Lease, Grant, Workspace, and Repository Handle
  IDs;
- source revision and policy hash;
- exact operation and normalized relative path where applicable;
- expected-current and proposed-content/operation digests;
- the canonical complete operation digest, covering the consumed state and
  issued/consumed/expiry window; and
- lease, Grant, and short permit deadlines.

The Runner recomputes the canonical digest and rejects any extra field,
mismatch, authorization-window tampering, expiry, cancellation, stale
identity, or unsupported operation before entering a mutating manager method.
The Permit ID is carried through the result and corresponding Workspace
Event/Checkpoint. A Permit is single-use and cannot move to another Attempt.

Grant revocation is explicit: `revoke_requested` blocks new Permit acquisition
while consumed permits are visible as in flight; effective `revoked` waits for
all such permits to be terminal or expired. Effective revocation accepts no
later mutation.

## Typed jobs and results

`system_diagnostic_v1` has no parameters. Its result may include only Runner
software version, protocol version, Python version, OS family, architecture,
capability list, timestamps, and duration. Hostname, username, IP, environment,
paths, files, package inventory, and external network facts are forbidden.

`controlled_wait_v1` accepts only `duration_ms` from 100 through 10,000. Its
result contains requested/elapsed duration and timestamps. The Runner renews
the lease and checks cancellation while waiting.

Both result variants reject unknown fields, secret-like values, absolute paths,
oversized serialization, and kind mismatch.

Phase 4 adds eight strict Workspace specs/results:

| Kind                      | Closed behavior                                             |
| ------------------------- | ----------------------------------------------------------- |
| `workspace_prepare_v1`    | exact local Handle, mirror, detached revision, fingerprints |
| `workspace_list_v1`       | bounded relative directory/depth/entries                    |
| `workspace_read_text_v1`  | bounded allowed regular UTF-8 file + SHA-256                |
| `workspace_write_text_v1` | create-absent or expected-hash replace only                 |
| `workspace_status_v1`     | bounded fixed Git status                                    |
| `workspace_diff_v1`       | allowed-path textual diff + hash + Checkpoint payload       |
| `workspace_rollback_v1`   | initial baseline only                                       |
| `workspace_discard_v1`    | registry-bound exact worktree disposal                      |

Workspace policy/text/diff limits are 512 path bytes, 32 path components,
32-KiB single text/diff, and 64-KiB serialized protocol payload/result.
Unknown fields, control characters, absolute paths, unbounded globs, invalid
UTF-8/binary content, absolute-path-like or secret-like result strings, and
kind mismatches are rejected.

Phase 5 adds `validation_execute_v1`. Its strict spec carries only Validation
Run, Workspace, Checkpoint and fingerprint, exact source revision and Grant
bindings, literal `fixture-python-stdlib-v1:v1`, and bounded timeout/output/
artifact values. There is no field for command, argv, cwd, environment,
package, URL, or user-supplied tool input.

The corresponding result repeats the exact identities and literal Profile,
uses only the fixed safe argv display
`python -I -S <system-owned-fixture-validator>`, and carries a versioned
execution-envelope digest. That digest binds the trusted Job, Validation
Run/step, Runner, Attempt, Lease, Grant, revision, Checkpoint, policy digest,
fixed operation, argv digest, symbolic fixed cwd, fixed environment-allowlist
digest, budgets, and Permit ID/sequence/digest/expiry fence.

The Control Plane reconstructs this envelope from locked persisted records
before it can store a terminal result, complete the Permit, or emit a success
event. It independently recomputes combined UTF-8 stdout/stderr bytes,
truncation consistency, the regular-file-only relative artifact manifest and
its count/individual/total bytes, manifest digest, and complete evidence
digest. Missing or mismatched evidence and any budget overflow return `409`
with no success side effect.

The result never returns a host path or raw environment. The Runner executes
a system-owned argv in a separate disposable validation root; the canonical
Workspace is only the verified source of a bounded copy.

## Idempotency and terminal behavior

An identical repeated start, renewal, completion, failure, or cancellation
acknowledgement returns the durable prior outcome when safe. A conflicting
replay fails. `succeeded`, `cancelled`, and `failed` are terminal. Completion
after `cancel_requested` returns `409 completion_after_cancel`.

## Error classes

Public errors use stable codes and a request ID:

- authentication: `runner_auth_invalid`;
- authorization: `runner_forbidden`;
- fencing/conflict: `stale_lease`, `completion_after_cancel`;
- validation/policy: `validation_error`, `policy_denied`,
  `result_rejected`;
- payload bound: `protocol_payload_too_large`;
- availability: `runner_registration_unavailable`.

Workspace failures additionally use a closed `FailureCode` taxonomy, including
path/sensitive/symlink/hardlink/non-regular/binary/size/budget denials,
expected-absent and `content_conflict`, source/revision/workspace identity,
atomic write, diff, cancellation, ownership/recovery/quarantine, and
Permit-required/invalid/expired errors. Arbitrary exception text never becomes
a public error.

Validation failures add closed codes for Profile denial, Checkpoint mismatch,
sandbox unavailable/denied, fixed-command non-zero result, timeout, output or
artifact overflow, sandbox cleanup failure, and a remaining process group.
Cleanup uncertainty after `cancel_requested` is accepted only as a typed
Validation recovery failure; it atomically fails the Job and Permit and
persists the Validation Run/step as `recovery_required`, never as clean
cancellation.

Messages do not include tokens, authorization headers, host paths, database
details, arbitrary exception text, or customer content.

## Compatibility

Protocol v1 requires exact version compatibility. The security repair is a
coordinated upgrade of the never-merged Phase 4 Workspace portion of v1:
Phase 3 repository-free jobs remain compatible, while a pre-repair Phase 4
Runner is intentionally incompatible with mutating Workspace jobs because it
cannot present a Permit. API and Runner must be deployed from the same repair
revision; strict validation fails closed on either mixed direction. Any
post-merge breaking change requires a new URL and protocol version. OpenAPI is
exported from FastAPI and generated TypeScript is checked for drift.

Agent Trace is a future, separate concept. `RunnerJobEvent`, `WorkspaceEvent`,
and fixed-Profile ValidationEvidence record current typed execution facts only.
Adding a shell, arbitrary target command, Git delivery, or new authority field
requires a separately reviewed protocol version/ADR.

Phase 4 is complete in local `main`. The Phase 5 protocol extension remains an
implementation checkpoint pending independent focused read-only review; it is
not a Phase 5 Security Gate approval.
