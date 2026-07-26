# CreativeDeploy Phase 2 Read-Only Evidence

- Observed: 2026-07-26, Asia/Shanghai
- Customer status: internal Customer 0 / Design Partner 0
- Task ID: `d71b708b-597e-448d-a41c-90df41c602f0`
- Run ID: `447510d7-695c-46ec-baad-9a0f750ce965`
- Plan version: `1`
- Snapshot fingerprint:
  `41c0ff6896e97d22b876e7bfe9d31f6f260998a74a2b0ddbcdb3620be1a53797`
- Local page:
  `http://127.0.0.1:13001/runs/447510d7-695c-46ec-baad-9a0f750ce965`

## Before and after comparison

| Observation          | Before                                                             | After  |
| -------------------- | ------------------------------------------------------------------ | ------ |
| Branch               | `main`                                                             | `main` |
| HEAD                 | `bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`                         | same   |
| Porcelain path count | 13                                                                 | 13     |
| Status SHA-256       | `0307d1daaa9ac29e09567e63513b5b77263a1e2ffafec3054fdfcd299210dca7` | same   |
| Tracked diff stat    | 4 files, 84 insertions, 21 deletions                               | same   |
| Diff-stat SHA-256    | `adb5a57b58493814020a44c711589144f33b6336eadbd6bc3d35c8f95132d076` | same   |

No external concurrent change was observed during the run. No reset, clean,
stash, checkout, install, command execution, or write was performed.

## Mount and process evidence

- API runtime user: `app`.
- API target mount:
  `/repositories/customer0/creative-deploy`, `.RW=false`.
- API allowlist:
  `/repositories/customer0/creative-deploy`.
- Web: no target mount.
- PostgreSQL: only its own data volume; no target mount.
- No Docker socket, privileged mode, or broad developer-directory mount.

The real repository was not write-probed. The runtime mount inspection plus
identical full status/HEAD hashes provide the read-only evidence.

## Durable product evidence

The Snapshot bound revision
`bd2fcd23a004ccc99e45bafaef49fe444c1f70fb`, recorded a dirty working tree with
13 bounded path records, and used committed blobs for structured facts. It
selected 16 of 86 entries and produced the fingerprint above.

Plan v1:

- status `awaiting_approval`;
- source `deterministic_policy`;
- delivery package `frontend_quality_remediation`;
- required future level `level_2_controlled_validation`;
- `execution_available = false`; and
- Snapshot fingerprint equal to the persisted Snapshot.

Run status is `awaiting_plan_approval`. Its five AuditEvents, in order, are
`run_created`, `snapshot_started`, `snapshot_completed`, `plan_created`, and
`plan_submitted`. There is no decision or execution event. The user must
personally approve or reject.

## Evidence boundary

This case proves local governed read-only investigation and durable plan
submission only. It provides no LLM, Agent Runtime, code-write, worktree,
validation execution, PR, remote CI, production, external-customer, adoption,
time-saving, or outcome evidence.
