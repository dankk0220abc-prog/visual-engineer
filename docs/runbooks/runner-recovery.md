# Runner Recovery Runbook

## Determine the condition

Open `/runners` or run:

```sh
make runner-status
```

Interpret Registry states:

- `registered`: registration exists but no recent heartbeat has established
  online state;
- `online`: `last_seen_at` is within the configured threshold;
- `offline`: the threshold elapsed; this is derived by the Control Plane;
- `revoked`: the credential is permanently denied.

Review the active Job and Timeline. Do not infer success from a missing Runner.
An expired Attempt is explicitly `lease_expired`; the Job is either requeued
within its retry budget or failed with `retry_exhausted`.

## Temporary Control Plane failure

Leave the Runner running. It uses bounded exponential backoff with jitter and
retains its credential. After API recovery, heartbeat and claim polling resume.
Do not rotate or expose a token merely because the API was temporarily
unavailable.

## Runner process or container loss

1. Do not manually change Job or Attempt rows.
2. Wait for the Registry to show `offline`.
3. Wait for the lease reaper to record `lease_expired`.
4. Confirm whether the Job is `queued` or `failed`.
5. Restore the existing Runner:

   ```sh
   docker compose start runner
   make runner-status
   ```

6. Confirm a requeued Job receives a new Attempt number and a different lease
   hint. The old Lease must receive `409 stale_lease`.

`make runner-chaos-check` proves this sequence against an isolated disposable
project.

## Invalid local credential

On `401`, Runner clears its unusable local credential and attempts bootstrap
registration using the configured local Bootstrap Token. This handles a
database reset with a retained Runner volume without exposing the old token.

If registration remains unavailable, verify that the API and Runner received
the same ignored `.env.runner.local` configuration by rerunning:

```sh
make platform-up
```

Do not print or copy the token while diagnosing. Do not put it in a command
argument, issue, chat, screenshot, or committed file.

## Revoked Runner

A revoked token receives `403` and does not silently self-register. This is
intentional. Review why it was revoked before establishing a new identity.
Automatic token rotation and un-revoke are not implemented.

For local development, preserve evidence and stop the platform. Any targeted
credential-volume replacement is a destructive operator action and is outside
the automatic runbook; identify the exact Compose project and obtain explicit
authorization first.

## Cancellation during loss

If a Job is already `cancel_requested` when its Lease expires, the reaper
transitions it to `cancelled`; it does not requeue. A late success from the
lost Runner is fenced.

## Reaper diagnosis

The local API lifespan loop uses a PostgreSQL advisory lock so only one
instance performs a reaper pass. Inspect stable structured events, API
readiness, and database availability. Do not add a message broker as a local
repair. A dedicated Control Plane worker becomes appropriate only when
measured operations need independent availability or scaling.

## Escalate

Stop and preserve evidence if:

- two active Attempts exist;
- an old Lease mutation succeeds;
- a cancelled Job succeeds;
- a token appears in a log/read API;
- Runner has a repository, database, Web, Docker-socket, SSH, or public-network
  path;
- migration or recovery would require editing retained rows.
