# Governed Validation Suite runbook

## Scope

This runbook covers only the trusted synthetic fixture and the source-owned
`fixture-integrity-suite-v1:v1` definition. It does not authorize a real
repository, arbitrary command, network, package installation, artifact
content, Git delivery, or deployment.

## Normal browser workflow

1. Open `/validations` and inspect the fixed Suite version, ordered Profiles,
   per-step limits, total limits, failure policy, and attempt budget.
2. Select an eligible sealed fixture Workspace Checkpoint.
3. Create the Suite-scoped pending Execution Grant and make the explicit local
   approve/reject decision. Confirm it shows the immutable definition digest,
   attempt `1`, and one allowed Suite Run.
4. Create the Suite Run. The Control Plane dispatches one fixed child at a
   time; inspect the ordered timeline and bounded Evidence.
5. Treat `succeeded` as a local fixture result only. `failed`, `timed_out`,
   `cancelled`, and `recovery_required` remain non-success.

## Cancel and retry

Cancel requests fence the Suite immediately, cancel any active child, and
prevent later dispatch. Total timeout follows the same cleanup-first path.
Retry is offered only for a terminal non-success and only once. Create and
approve a fresh Suite-scoped Grant explicitly bound to that source Suite Run.
Confirm the displayed root, source, and next attempt before retrying.
Successful steps are shown as reused and consume zero retry output, while
failed/skipped steps receive fresh child execution identities. Never use a
root Grant or a retry Grant from another Suite lineage.

## Recovery

Do not force a `recovery_required` Suite to success and do not mutate its
terminal database rows. Preserve the Suite/step timeline, child Validation
Run, Attempt, Lease, Permit, bounded Evidence, Audit references, and exact
filtered Compose logs. Confirm no active child, process group, sandbox, or
project-scoped Docker resource remains. Escalate for focused diagnosis; never
expand authority or use an external repository as a recovery shortcut.

If the API reports `validation_suite_grant_already_consumed`,
`validation_suite_retry_lineage_required`, or
`validation_suite_retry_binding_mismatch`, do not alter database lineage or
retry with another idempotency key. Inspect the immutable Grant root/source/
attempt fields and request new authority only for the latest terminal
non-success source.

## Verification

Use the repository Make targets. PostgreSQL, E2E, and Chaos runs must use a
unique Compose project and bound ports. Inspect only project/label-filtered
Docker resources. The final implementation gate is `make verify`; its success
does not replace the required independent focused security review.
