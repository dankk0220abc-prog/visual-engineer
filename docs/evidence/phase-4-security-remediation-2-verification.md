# Phase 4 Security Remediation Round 2 Verification

- Date: 2026-07-28
- Branch: `fix/phase-4-security-remediation-2`
- Base / preserved independent re-audit:
  `b457b614bde6630fb50ff9546c92a4d6925ad38a`
- Historical Security Gate: **FAIL — PRESERVED**
- Evidence status:
  `REMEDIATION ROUND 2 COMPLETE — READY FOR INDEPENDENT FOCUSED RE-AUDIT`
- Remote CI: NOT VERIFIED

This is implementer evidence, not an independent audit or approval. It does
not change the original audit or independent re-audit conclusions. A command
is recorded as passing only after it exits zero in this exact worktree.

## Baseline

The pre-branch investigation confirmed:

| Ref                                 | Exact commit                               |
| ----------------------------------- | ------------------------------------------ |
| `main`                              | `7590f9dcecbf06371936ac0265cecb9f7a4438ca` |
| Phase 4                             | `53dc2f5016e9b76e1f39c6306fe116ee4091b302` |
| original audit                      | `a560509b2018f86693e38e3646409f9e33841829` |
| first repair                        | `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c` |
| independent re-audit / Round 2 base | `b457b614bde6630fb50ff9546c92a4d6925ad38a` |

Git showed one linear ancestry chain, a clean tracked/index/untracked
inventory, one worktree, no remote, no stash, no tag, and no pre-existing
Round 2 branch. The re-audit commit's sole parent was the first repair and its
diff contained only audit tests and audit/status documents. Base Compose
rendering contained no CreativeDeploy mount.

## Preserved pre-repair reproduction

Command:

```text
/opt/homebrew/bin/uv run pytest \
  apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py \
  --no-cov -vv
```

Exit: `1`. Result: `3 failed, 4 passed`.

The three failing secure assertions were preserved without edits:

1. an unreachable loose source object entered the mirror;
2. missing registry and expected root returned discard success without signed
   recovery proof; and
3. a child process survived the timeout after its leader exited.

## VE-P4-AUD-001 / VE-P4-REAUD-001

The Round 2 source adapter computes the exact commit/ancestor/tree/blob graph
from the authorized revision without invoking Git on the source. It parses
ordinary loose objects and pack-index-v2/pack-v2-or-v3 data with bounded
normal, OFS-delta, and REF-delta reconstruction. It treats gitlinks as
validated inert superproject metadata without opening/importing their target
commit or enabling submodule recursion. It rejects tag roots, alternates, HTTP
alternates, grafts, replacements, malformed refs, malformed object headers,
type/hash/length inconsistencies, delta cycles or depth overflow,
tree/graph/reference/object/byte overflow, and pack/index identity or checksum
drift.

Only authorized objects are recompressed as mode-0600 Runner-owned loose
objects with new inodes. Existing destination config, indirection locations,
packs, and loose objects must already be exact; valid but unauthorized
destination objects fail closed. Source and selected pack/loose descriptors
are revalidated after materialization.

Current focused evidence:

- complete Runner Workspace file: exit `0`, `47 passed`;
- preserved re-audit file: exit `0`, `7 passed`;
- source invariance: exit `0`, `119` source entries, `10` canonical Git object
  comparisons, `2` source-status records, zero extension markers;
- packed-delta fixture proves the mirror object-ID set equals the exact
  authorized closure and excludes the commit/tree/blob reachable only through
  another source ref;
- object-count, aggregate byte, single-object/decompression, tree, graph,
  reference, delta, pack, destination identity, and output bounds fail closed.
- source-object, pack-directory, and destination-object scans are streaming;
  every supported pack sidecar consumes the pack-entry bound and must belong
  to a real paired pack/index.

## VE-P4-AUD-003 / VE-P4-REAUD-002

Before deletion, Runner persists a domain-separated HMAC-signed pending proof
binding Workspace, Runner, Grant, Handle, revision, policy, creation nonce,
root device/inode, Job/operation, Permit sequence and identity, Attempt,
Lease, job/operation/proposed/current digests, authorization timestamps, and a
proof nonce. The registry then durably records the exact pending operation.

After exact worktree deletion, Runner durably transitions the proof to
`completed` before it records terminal registry state. Recovery accepts only
the exact crash window represented by these states. Missing proof becomes
`workspace_recovery_required`; invalid signature, mismatched state/binding, a
rolled-back pending proof, or replay under another operation becomes
`workspace_quarantined`; expiry becomes
`side_effect_permit_expired`. Every replay rechecks the expected path and
recursively searches the managed workspace volume for the original
device/inode without following symlinks.

Current focused evidence:

- unsigned registry/root absence fails the preserved re-audit assertion;
- exact pending proof plus absent root reconciles once and becomes completed;
- completed exact replay is idempotent;
- recreated/replaced root and nested renamed original inode are preserved and
  rejected;
- tamper, binding mismatch, cross-operation replay, terminal-to-pending
  rollback, and expiry fail closed;
- source, mirror after authorized disposal, and sibling fingerprints remain
  unchanged on rejected/replayed paths.

## VE-P4-AUD-005 / VE-P4-REAUD-003

Git output pipes are nonblocking and a monotonic deadline remains active until
the leader has a return code, both pipes reach EOF, and the process group is
absent. Leader exit is not completion. Timeout or combined-output overflow
signals the complete group with `SIGTERM`, waits a bounded grace period,
escalates to `SIGKILL`, verifies group absence, reaps the leader, and closes
both pipes. An inability to terminate or reap returns a stable
`workspace_state_invalid` failure rather than the requested timeout/overflow
result.

Current focused evidence covers inherited pipes, closed pipes, leader-first
exit, three descendants, TERM resistance and KILL escalation, deadline-before
normal completion, normal bounded output, combined-output overflow, repeated
cleanup, no residual marker/PID group, and explicit termination failure.

## VE-P4-AUD-002 real PostgreSQL closure

No new production defect was reproduced, so production Permit behavior was
not changed. Permanent integration coverage uses real PostgreSQL sessions,
row locks, constraints, triggers, and actual Runner-owned Git workspaces.

Current complete Workspace API file: exit `0`, `12 passed`.

The matrix verifies:

- two concurrent database sessions acquire one Permit row and one acquired
  event; one response is the exact idempotent replay;
- Runner, Job, Attempt, Lease, Grant, Workspace, Handle, revision, policy,
  operation, path, precondition, proposed digest, canonical job/operation
  digest, budgets, and issued/consumed/expiry window bindings;
- stale Runner/Attempt/Lease, wrong digest, inactive Grant, expired Permit,
  mismatched/tampered/replayed Permit, cancellation, and last-moment budget
  change reject before a new disk side effect;
- `revoke_requested` serializes with acquisition, blocks later acquisition,
  and effective revocation waits for consumed Permit terminal/cancelled state;
- crash before mutation leaves no Permit/disk mutation; a consumed Permit can
  exist before disk mutation; disk mutation can commit while database
  Workspace accounting remains unchanged;
- a PostgreSQL trigger-injected completion crash rolls back the whole
  completion transaction while the disk commit remains;
- Manager restart/retry returns the same result without replacing the target
  inode or charging bytes twice;
- the final result, checkpoint, Workspace events, and Runner events share one
  Permit ID; terminal completion replay is idempotent.

## Data, API, Protocol, and migration disposition

The PostgreSQL closure matrix did not reproduce a Side-effect Permit
production defect. Round 2 therefore makes no production Permit, API route,
database model, migration, generated OpenAPI/TypeScript contract, or pure
Runner Protocol change. `make contracts-check` reports no generated drift.

The only production configuration additions are explicit Git-object graph,
tree, reference, delta, pack, object-count, object-byte, single-object, and
process-group termination-grace limits. The Compose Runner service passes
those bounded values to the already private Runner process.

The real PostgreSQL migration gate downgraded to base, upgraded through
`20260728_0005`, downgraded, and re-upgraded successfully. The Permit matrix
also exercised real row locks, independent transactions, constraints, and a
trigger-injected completion rollback.

## Live Docker and runtime isolation

The actual disposable project was
`visualengineer-round2-smoke`, using host ports `15437`, `18004`, and `13004`
and only the Round-2 synthetic workspace fixture.

`docker inspect` and in-container runtime probes confirmed:

- Runner user and process identity: UID/GID/groups `10001`;
- command: `python -m visual_engineer_runner.main`;
- read-only root filesystem and read-only
  `/repositories/fixture` bind (`statvfs` and Docker mount state agree);
- `CapDrop=ALL`, effective capability mask zero, and
  `NoNewPrivs=1`;
- actual limits: `cpu.max=100000 100000`, memory
  `536870912`, `pids.max=128`, and `RLIMIT_NOFILE=256/256`;
- private volume roots are mode `0700`, owned by `10001:10001`;
- the ownership key is the 32-byte regular file
  `/var/lib/visual-engineer-runner/ownership.key`, mode `0600`, owner
  `10001:10001`;
- Runner has no published port, Docker socket, SSH directory, default route,
  or attachment to the default application network;
- Runner resolves `api` only on `runner-control`; `db` and `web` do not
  resolve there;
- API joins the default and runner-control networks; Web and DB join only the
  default network;
- API and Web have no mounts, so they do not receive Runner credentials,
  mirrors, workspaces, registry, or source; and
- Runner mounts only its four private named-volume locations plus the
  read-only synthetic source. No Docker socket is present.

The exact project was removed with Compose `down -v --remove-orphans`.
Label-filtered post-cleanup inspection reported:

```text
containers=0
volumes=0
networks=0
```

## Smoke and chaos evidence

- `make workspace-smoke`: exit `0`; the workspace was prepared, two typed
  writes produced three checkpoints, rollback returned clean, discard and
  repeat discard were idempotent, the four expected policy-denial classes
  were observed, and `source_unchanged=true`.
- `make runner-smoke`: exit `0`; diagnostic Job `44b8664b` succeeded with
  repository access `none`, shell access false, control-plane-only network
  policy, and a redacted result.
- `make runner-chaos-check`: exit `0`; offline handling, lease expiry,
  requeue, stale fencing, recovery, final success, and source-tree integrity
  passed.
- `make workspace-chaos-check`: exit `0`; precommit/postrename atomicity,
  revoke concurrency, zero revoke-effective side effects, three stale leases,
  write recovery, no budget replay, no discard residue, and unchanged source
  repository plus `.git` fingerprint passed.
- The exact `visualengineer-runner-chaos` and
  `visualengineer-workspace-chaos` projects each ended with zero labeled
  containers, volumes, and networks.

## First-failure ledger

| Classification                           | First result                                                                                                          | Root cause                                                                                                                                                                | Correction and rerun                                                                                                                                                                                        |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| expected production baseline             | re-audit file exit 1; 3 failed, 4 passed                                                                              | the three independently reproduced production defects                                                                                                                     | repaired production paths; unchanged file now exits 0 with 7 passed                                                                                                                                         |
| invalid migration filename               | `wc -l` exit 1                                                                                                        | historical description was not the real migration filename                                                                                                                | discovered and read `20260728_0005_close_phase4_security_findings.py`                                                                                                                                       |
| static implementation defect             | Ruff exit 1; five `B904` findings                                                                                     | fail-closed packed-ref raises lacked explicit cause inside an exception handler                                                                                           | added `from None`; Ruff and mypy reruns exit 0                                                                                                                                                              |
| source command environment               | direct source script exit 1 with `ModuleNotFoundError`                                                                | omitted the Make target's required package `PYTHONPATH`                                                                                                                   | declared `make source-invariance-check` exits 0                                                                                                                                                             |
| source success-fixture/comparison defect | first closure-aware harness runs rejected its gitlink and then recompressed destination bytes                         | the first implementation chose rejection although the fixture's established policy treats gitlink as inert; zlib bytes need not be identical for one canonical Git object | intermediate focused runs separated the fixture; the E2E failure below forced final inert handling, restored gitlink source-invariance coverage, and retained canonical-byte plus distinct-inode comparison |
| proof test helper                        | expanded Runner file exit 1; 44 passed, 1 failed                                                                      | replay branch did not retain the original signed pending proof                                                                                                            | retain/restore exact proof; later full reruns pass                                                                                                                                                          |
| terminal replay test baseline            | Runner file exit 1; 46 passed, 1 failed                                                                               | mirror snapshot was captured before legitimate discard metadata cleanup                                                                                                   | moved baseline after first authorized discard; focused 1 passed and aggregate 47 passed                                                                                                                     |
| full test budget classification          | first `make test` exit 2; backend 142 passed, 1 failed                                                                | a configured single-object overflow returned generic `repository_unavailable`                                                                                             | classify actual size overflow as `mirror_budget_exceeded`; focused test and complete `make test` rerun pass                                                                                                 |
| full E2E gitlink policy                  | first `make e2e` exit 2; Playwright 10 passed, 4 failed; both Phase 4 prepare flows reported `repository_unavailable` | Round 2 rejected the versioned fixture's inert gitlink                                                                                                                    | validate the entry without importing its target or recursing; restore source harness coverage and rerun E2E                                                                                                 |
| Docker inspect template                  | first combined inspection exit 1 after API/Web/DB facts; Runner lacked optional `Config.ExposedPorts` map             | the Go template dereferenced an intentionally absent optional map                                                                                                         | rerun Runner inspection without that field; exit 0, empty port bindings and all remaining runtime facts confirmed                                                                                           |
| aggregate documentation format           | first post-documentation `make verify` exit 2 after contracts; `format-check` named both new Round 2 Markdown files   | the latest evidence additions had not yet been normalized by repository Prettier                                                                                          | `make format` exit 0 changed only those documents; focused format and complete aggregate reruns required                                                                                                    |
| final diff pack-budget review            | additive budget case exit 1: six orphan pack sidecars under a one-pack limit did not raise                            | whole-directory listing preceded limits and orphan supported sidecars were neither counted nor paired                                                                     | stream source/pack/destination scans, bound all pack entries, require sidecar-to-pack pairing; focused 1, complete Runner/Protocol 52, source invariance, and final aggregate reruns pass                   |

## Verification ledger

| Command                                                        | Exit / result                                                     |
| -------------------------------------------------------------- | ----------------------------------------------------------------- |
| targeted Ruff format/check and mypy                            | `0`; no findings                                                  |
| `pytest apps/runner/tests/test_workspace_tools.py --no-cov -q` | `0`; 47 passed                                                    |
| preserved re-audit file                                        | `0`; 7 passed                                                     |
| real PostgreSQL `test_workspace_api.py`                        | `0`; 12 passed, one dependency deprecation warning                |
| `make source-invariance-check`                                 | `0`; PASS with counts above                                       |
| `make workspace-security-check`                                | `0`; 52 passed plus static checker                                |
| `make phase4-findings-check`                                   | `0`; 7 passed; `FAIL_PRESERVED`                                   |
| `make workspace-security-repair-check`                         | `0`; 59 Runner/Protocol plus 12 PostgreSQL tests                  |
| `make contracts-check`                                         | `0`; regenerated contract had no drift                            |
| `make format` / `make format-check`                            | `0`; 98 Python files and all Web sources clean                    |
| `make lint` / `make typecheck`                                 | `0`; Ruff, ESLint, mypy 73 files, TypeScript pass                 |
| `make test`                                                    | `0`; backend 143 and Web 41 passed                                |
| backend coverage                                               | `81.79%` total; one dependency deprecation warning                |
| Web coverage                                                   | 72.35 statements / 67.12 branches / 71.89 functions / 74.22 lines |
| `make build`                                                   | `0`; production Next build generated 10 routes                    |
| `make docker-config`                                           | `0`; all 5 declared Compose renderings valid                      |
| `make migration-check`                                         | `0`; base/upgrade/downgrade/re-upgrade passed                     |
| `make security-check`                                          | `0`; secret/static gates, 7 scanner, 76 security tests            |
| `make eval`                                                    | `0`; 58 deterministic cases / 4 datasets plus 7 scanner tests     |
| final `make e2e`                                               | `0`; Playwright 14 passed in 1.1 minutes                          |
| `make workspace-smoke` / `make runner-smoke`                   | `0`; exact isolated Compose project                               |
| both chaos targets                                             | `0`; checks passed and exact resources removed                    |
| live Docker isolation probes                                   | `0`; all facts listed above                                       |
| final `make verify`                                            | `0`; post-review correction rerun passed every declared subtarget |

## Final aggregate and checkpoint handoff

The first post-documentation `make verify` exited `2` after
`contracts-check` succeeded because `format-check` identified only the two
new Round 2 Markdown files. `make format` exited `0`; a focused
`make format-check` exited `0`; the complete `make verify` rerun then exited
`0`.

That successful aggregate reran contracts, formatting, lint, type checking,
143 backend tests, 41 Web tests, the production Web build, five Compose
renderings, PostgreSQL base/upgrade/downgrade/re-upgrade, seven preserved
re-audit tests, source invariance, the 59+12 repair matrix, 14 browser E2E
tests, Workspace Chaos, 52 Workspace security tests, 76 Runner/API security
tests, 58 deterministic Eval cases across four datasets, seven scanner tests,
and final `git diff --check`.

The later complete diff review added one in-scope pack-directory budget
regression. Its first run failed as intended; its focused, complete
Runner/Protocol, source-invariance, and final complete aggregate reruns all
pass.

The one authorized local checkpoint contains this finalized evidence and uses
`fix(security): close phase 4 re-audit blockers`. A Git commit cannot embed
its own final hash; the exact hash and clean post-commit worktree/index are
reported in the external handoff.

## Invariance and scope

The source harness compares the complete no-follow synthetic source tree and
`.git` metadata/content before and after. Selected source object and
destination inodes differ while their decompressed canonical Git bytes match.
The packed test compares exact authorized and destination object-ID sets.

No source write, target command, shell, build/test executor, LLM, Agents SDK,
Git delivery, remote, push, merge, pull request, tag, Phase 5 work, or
CreativeDeploy access is authorized or claimed.

No new out-of-scope Critical or High finding was reproduced. This is a local
implementer observation, not an independent closure decision.

## Limitations and decision boundary

The current threat model remains a dedicated local single-Writer Runner, not a
hostile same-UID multi-writer, hostile multi-tenant, remote-CI, or production
sandbox claim. Python still lacks portable `openat2`/`renameat2`
path-resolution/CAS guarantees. No privileged garbage collector or automated
quarantine adjudication exists. PostgreSQL and Docker evidence is local.

Only a new independent focused re-audit may decide the Security Gate.
