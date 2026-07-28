# Workspace Lifecycle Runbook

## Purpose

Operate the Phase 4 synthetic fixture path without terminal knowledge in the
normal case. This runbook does not authorize CreativeDeploy, a source write,
shell, target command, Git delivery, or production use.

## Start and inspect

Run `make platform-up` from the VisualEngineer repository. It creates or
validates the versioned synthetic fixture, starts PostgreSQL, API, Web, and the
non-root Runner, registers the opaque handle, and seeds an approved synthetic
Plan. The fixture source is mounted read-only only into Runner.

Open:

- `http://127.0.0.1:3000/repositories`
- `http://127.0.0.1:3000/execution-grants`
- `http://127.0.0.1:3000/workspaces`

The repository page must show `Phase 4 Adversarial Fixture` and never a host
path.

## Grant

1. Create a Grant from the eligible fixture context.
2. Verify it is `pending`.
3. Review exact revision, `sandbox/**`, denied paths, 8-file/128-KiB/32-KiB
   limits, 20-minute Workspace TTL, network `none`, and false shell/source
   write/Git delivery fields.
4. Approve as the local test user. Plan approval alone does not authorize this
   step.

Reject requires a reason. Revocation first shows `revoke_requested` while an
already consumed, exact short-lived Permit finishes or expires; it then shows
effective `revoked`. The request blocks new Permits immediately, and effective
revocation accepts no later mutation. A rejected, revoke-requested, revoked,
or expired Grant cannot begin a new mutating operation.

## Prepare and operate

Create one Workspace. Wait for `ready`, then open its detail page. The typed
console supports only:

- list a bounded directory;
- read bounded UTF-8 text;
- create a text file when absent;
- replace text using the displayed SHA-256;
- status;
- bounded textual diff;
- rollback to the initial baseline; and
- discard.

There is no shell input. A write preview shows path, operation, expected hash,
new byte count, and remaining budget. The Control Plane derives an exact
Side-effect Permit immediately before create/replace. `.env`, traversal,
symlink, binary, oversize, stale-hash, stale Lease/Attempt/Permit, and revoked
Grant attempts must fail with stable policy/conflict codes.

## Seal, rollback, and discard

Diff seals the current evidence and creates a checkpoint. Rollback restores
the initial tracked tree and removes only files recorded as created by this
Workspace. Confirm clean status and matching initial/current tree hashes.

Discard is allowed from sealed, rolled-back, failed, or expired Workspace
states. It requires a current discard Permit, authenticated registry, valid
signed ownership manifest, exact root identity, complete safe inventory, and a
durable signed pending-to-completed discard proof bound to the same
operation/Permit/Attempt/Lease. It removes only that managed worktree.
Idempotent retry revalidates the completed proof and proves both the expected
root and original inode remain absent.

If proof is missing, the page shows `recovery_required`; if proof conflicts or
unknown content exists, it shows `quarantined`. Destructive controls are
disabled and no deletion occurs. Follow the Workspace recovery runbook; never
repair state by editing rows or local files. The Workspace TTL is 20 minutes
while the Grant TTL is 30 minutes; use that cleanup window. Do not bypass an
expired or revoked Grant.

## Stop

`make platform-down` stops the Phase 4 local services without authorizing or
touching another project. Runner mirror/workspace/registry volumes are local
test state; do not manually delete their host paths.

CreativeDeploy is prohibited for this lifecycle. Phase 4 is not in `main`;
the original audit and independent re-audit remain Security Gate FAIL and the
only next milestone is Phase 4 Independent Focused Security Re-Audit.
