# Runner Protocol v1

## Purpose and boundary

Runner Protocol v1 is the versioned contract between the VisualEngineer
Control Plane and a repository-free Local Runner. It supports only registration,
liveness, dispatch, fenced attempts, progress, cancellation, and typed terminal
results. It does not carry repository locators, file content, shell commands,
Git operations, arbitrary tools, LLM messages, or Agent traces.

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

| Method and path                 | Purpose                                             |
| ------------------------------- | --------------------------------------------------- |
| `POST /register`                | One-time local registration and credential issuance |
| `POST /heartbeat`               | Refresh derived liveness without event flooding     |
| `POST /jobs/claim`              | Atomically claim one compatible queued Job          |
| `POST /jobs/{job_id}/start`     | Move the active fenced Attempt to running           |
| `POST /jobs/{job_id}/renew`     | Extend a lease and observe cancellation             |
| `POST /jobs/{job_id}/events`    | Append one typed, bounded progress event            |
| `POST /jobs/{job_id}/complete`  | Validate and persist one typed result               |
| `POST /jobs/{job_id}/fail`      | Persist one closed failure classification           |
| `POST /jobs/{job_id}/cancelled` | Acknowledge cancellation                            |

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
closed Job kind and fixes:

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

Messages do not include tokens, authorization headers, host paths, database
details, arbitrary exception text, or customer content.

## Compatibility

Protocol v1 requires exact version compatibility. Backward-compatible v1
schema changes must remain additive only where strict clients can safely
ignore nothing; otherwise a new URL and protocol version are required.
OpenAPI is exported from FastAPI and generated TypeScript is checked for drift.

Agent Trace is a future, separate concept. `RunnerJobEvent` records current
typed execution facts only.
