# Local Delivery Lifecycle Runbook

## Scope

This runbook operates only the Phase 6 synthetic fixture through the local
`/deliveries` console. It never authorizes a source write, remote, push, PR,
tag, deploy, arbitrary Git command, real repository, or Customer 0 action.

## Dispatch

1. Confirm the Review Package remains fresh, approved, and effectively ready.
2. Create and separately approve the Delivery Authorization.
3. Select **Review delivery preview**.
4. Inspect the exact branch/message, changed-path closure, bounded diff, byte
   count, manifest digest, and every false remote/source-write flag.
5. Confirm the checkbox for that exact digest, then dispatch once. The browser
   creates a unique idempotency key; repeated submission of the same request
   replays the same Dispatch.
6. Follow the attempt's Runner evidence link. Success must show commit proof,
   terminal Attempt status, and explicit source/remote invariance.

## Failure or cancellation

- `failed` and `cancelled` are durable terminal attempt facts. Record the
  stable error code shown in the history; do not delete or edit the record.
- Select **Review safe retry**. If preview says it is blocked, stop. Do not
  bypass stale Review, expired/revoked Grant, invalid lineage, manifest drift,
  existing LocalDelivery, or exhausted budget.
- Reinspect and reconfirm the exact manifest. Retry must name the latest
  terminal Dispatch and produces a new Job/Attempt while retaining the same
  Authorization, ref, message, timestamp, and manifest.
- Maximum attempt number is three. There is no operator cleanup, ref rewrite,
  branch deletion, or budget reset in this slice.

## Fail-closed conditions

Stop and preserve the visible status/error when any of these appear:

- `delivery_execution_authority_inactive`
- `delivery_authorization_expired` or `delivery_authorization_stale`
- `delivery_confirmation_mismatch` or `delivery_manifest_invalid`
- `delivery_retry_lineage_invalid`
- `delivery_dispatch_budget_exhausted`
- `local_delivery_already_succeeded`
- Runner `workspace_state_invalid`, Permit expiry, or recovery/quarantine state

An independent reviewer should inspect the Authorization, all Dispatches,
Runner Job/Attempt/Permit evidence, AuditEvents, LocalDelivery proof, and
source-invariance evidence together. Do not infer remote delivery or approve a
later phase from local success.
