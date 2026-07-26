# Phase 2 Human Rejection Evidence

- Verified: 2026-07-26 (Asia/Shanghai)
- Decision source: local user through the Web Console
- Task: `d71b708b-597e-448d-a41c-90df41c602f0`
- Run: `447510d7-695c-46ec-baad-9a0f750ce965`
- Snapshot: `eddf95d2-fe12-4699-a7c2-36b4331ebe26`
- Snapshot fingerprint:
  `41c0ff6896e97d22b876e7bfe9d31f6f260998a74a2b0ddbcdb3620be1a53797`
- Plan version: `1`
- Verification result: VERIFIED — REJECTED

## Persisted decision

The browser-originated decision is stored once as a `local_user` rejection.
The non-empty reason is:

> CreativeDeploy HEAD has advanced since this Snapshot was created. Regenerate
> the Snapshot and Plan against the current committed HEAD before any execution
> approval.

The persisted Run status is `rejected`, Plan v1 status is `rejected`, and the
ordered Audit Timeline ends with `plan_rejected`. The decision event records
that execution is unavailable.

## Automated verification method

The already-running Customer 0 stack was used without creating replacement
product state. Read-only requests retrieved the specified Run, Plan v1,
Snapshot, and Audit Timeline from the existing API. A read-only PostgreSQL
query retrieved the corresponding ApprovalDecision because Phase 2 exposes
decision creation/replay but no separate decision-read route.

The verification asserted:

1. Run and Plan states are both `rejected`.
2. The Snapshot identity and fingerprint match the recorded Phase 2 evidence.
3. Exactly one ApprovalDecision exists for the Run.
4. Its actor is `local_user`, its decision is `reject`, and its reason is
   non-empty and matches the text above.
5. The last ordered governance event is `plan_rejected`.
6. No event type for execution, tools, writes, Git, or pull requests exists.

No decision mutation endpoint was called during verification.

## Stale-baseline safety result

A read-only Git observation confirmed that the repository's committed `HEAD`
has advanced beyond the Snapshot source revision. The Snapshot and its bound
Plan are therefore stale. The user's rejection is the correct fail-closed
outcome: it prevents an outdated planning baseline from being treated as
current approval.

Plan approval or rejection is only a durable governance decision. It cannot
start execution, grant repository access, authorize writes, or authorize Git
or pull-request operations. This closure did not mount new repository access,
rescan repository content, modify CreativeDeploy, or create a new Task, Run,
Snapshot, or Plan.

## Evidence boundary

This record proves a local browser-originated rejection and its durable,
consistent persistence. It does not prove execution, Agent Runtime behavior,
repository mutation, remote CI, production deployment, or external-customer
outcomes.
