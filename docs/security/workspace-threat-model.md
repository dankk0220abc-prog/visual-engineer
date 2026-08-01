# Workspace Threat Model

## Scope and assumptions

This model covers the Phase 4 synthetic fixture, immutable Execution Grant,
Runner-owned mirror/worktree, descriptor-safe UTF-8 tools, checkpoints,
rollback, disposal, and the Phase 6 governed local-delivery ref overlay. It
assumes one trusted local operator and a dedicated non-root Runner container.
Repository content and browser input are hostile data. It does not claim
hostile-user, hostile-kernel, or production isolation.

## Assets

- source repository and its `.git` directory;
- exact approved source revision and Snapshot fingerprint;
- immutable Grant policy and separate decision evidence;
- workspace/mirror/registry ownership and the Runner-local ownership HMAC key;
- file contents, hashes, write ledger, checkpoints, and bounded diff;
- Runner credential, Attempt/Lease identity, and audit integrity;
- sibling workspaces and the host outside managed roots.

## Threats and controls

| Threat                                 | Implemented control                                                                                                                                                                                                                       | Residual                                                                                         |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Host path injection                    | Opaque handles registered from Runner-local configuration; no path in user APIs                                                                                                                                                           | Local configuration administrator remains trusted                                                |
| Source mutation                        | Runner-only read-only exact bind, no API/Web/DB mount, no source Git execution, exact no-follow invariance manifest                                                                                                                       | Host administrator can remount; production attestation absent                                    |
| Dirty/untracked or extra-object import | No source working-tree status/read; exact authorized commit/tree/blob closure is parsed from bounded loose/packed objects and materialized into new Runner-owned inodes                                                                   | Narrow ordinary `.git` loose/pack layout only                                                    |
| Replacement metadata changes checkout  | Empty-template mirror, exact detached `HEAD`, no packed/replace refs, dual Git replacement disabling, exact manifest equality, and only bounded fixed-name local-delivery refs whose commit closure and single approved parent revalidate | Legacy or unprovable mirror state requires manual recovery                                       |
| Hook/helper/network execution          | Source is never a Git execution target; managed Runner-only adapter disables extensions and protocols                                                                                                                                     | Container/runtime hardening needs production review                                              |
| Plan approval treated as execution     | Separate pending Grant and local-user decision                                                                                                                                                                                            | No enterprise identity/signature yet                                                             |
| Grant expansion/tamper                 | Server-derived scope, immutable DB trigger, canonical hash, per-operation revalidation                                                                                                                                                    | Local DB administrator is trusted                                                                |
| Traversal or symlink escape            | Bounded POSIX parser, descriptor walk, `O_NOFOLLOW`, type checks                                                                                                                                                                          | No `openat2`; see platform limits                                                                |
| Hard-link alias                        | Writable/read leaves require one link                                                                                                                                                                                                     | Read-only committed Git material can still have normal Git semantics                             |
| Replace race                           | Expected SHA-256 plus opened inode identity recheck before atomic rename                                                                                                                                                                  | No kernel pathname CAS against an unexpected same-UID volume writer                              |
| Partial write/crash                    | Same-directory temp, fsync, atomic link/rename, deterministic retry cleanup/reconciliation                                                                                                                                                | Host/filesystem durability semantics remain trusted                                              |
| FIFO/socket/device blocking            | Nonblocking no-follow open plus `fstat` regular-file requirement                                                                                                                                                                          | Device-node creation is prevented by non-root/capability policy, not exhaustively created in E2E |
| Secret exfiltration                    | Sensitive path and secret-like content denial, bounded/redacted results/events/log checks                                                                                                                                                 | Heuristics do not replace secret classification                                                  |
| Budget exhaustion                      | File/write/list/diff/result/timeout/attempt/TTL plus CPU/memory/PID/FD, streaming output, pack/delta/tree/graph/reference/object/byte/expanded-path/destination/local-ref limits                                                          | Host/fleet quota remains future                                                                  |
| Stale Runner side effect               | Attempt/Lease fencing plus exact short-lived single-use Permit immediately before mutation                                                                                                                                                | Distributed identity/signing remains future work                                                 |
| Rollback over-delete                   | Baseline-only restore and exact created-file ledger/hash                                                                                                                                                                                  | No arbitrary checkpoint restore                                                                  |
| Registry or proof loss/replay          | Authenticated registry, signed ownership manifest, and domain-separated signed pending/completed discard proof; absence enters recovery and state/binding rollback enters quarantine                                                      | Controlled operator recovery is manual                                                           |
| Disposal escape                        | Permit, signatures, exact identities/state/root/inventory/managed boundary, recursive original-inode absence, sibling tests                                                                                                               | No privileged GC after Grant expiry                                                              |
| Leader-first subprocess escape         | Nonblocking pipes plus monotonic complete-process-group deadline, bounded TERM/KILL, absence check, reap, and explicit cleanup failure                                                                                                    | Dedicated local Runner scope; no hostile code executor                                           |
| Unknown or ignored content             | Complete no-follow deletion inventory; quarantine preserves all data                                                                                                                                                                      | No automated quarantine adjudication                                                             |

## Revocation and expiry

The Control Plane rechecks approved status, expiry, Runner/Workspace/Handle,
revision, and policy hash for every claim and lease mutation. Mutating
operations additionally acquire a Permit in a locked transaction and validate
it at the filesystem boundary.

`revoke_requested` commits before it blocks new Permits. Consumed exact
Permits remain visible and bounded; effective `revoked` waits until they are
completed, failed, cancelled, or expired. After effective revocation, new and
old mutation authority both fail. Workspace TTL is 20 minutes and Grant TTL is
30 minutes so an expired Workspace can be explicitly discarded while its
Grant remains active. Once the Grant expires, Phase 4 deliberately offers no
authority-bypassing cleanup path.

## Adversarial evidence

The committed fixture definition creates normal and Unicode text, a fake
`.env`, external/sensitive/nested symlinks, binary and oversized content,
malicious `AGENTS.md`, dirty tracked and untracked source data, source
hooks/filters/fsmonitor/helpers, gitlink, LFS pointer, and collision cases.
Runner tests dynamically add FIFO, UNIX socket, hard link, symlink
replacement, cancellation, interrupted atomic writes, missing/tampered/
replayed discard proof, root/inode drift, ignored/unknown files, sibling
workspaces, loose/packed unreachable objects, alternate/graft/replace
indirection, malformed objects, delta packs, and leader-first descendants.
Round 3 adds packed/loose replacement refs, source metadata non-import,
pre-existing destination refs, direct no-replacement Git execution, semantic
checkout mismatch isolation, and exact normal manifest cases. Real PostgreSQL
tests cover concurrent Permit acquisition, revocation, terminal-state
injection failure, committed-disk retry, and exact Permit lineage. Real
E2E/chaos and the dedicated source harness fingerprint the full source tree
and `.git` before and after.

Round 4 adds exact-limit success and pre-sixth-entry rejection, shared-tree
per-path charging, deep and wide tree rejection, repeated-subtree rejection,
regular/symlink/gitlink entry charging, no Workspace/registry/ownership
creation on rejection, mirror/sibling preservation, and exact source
invariance.

Phase 6 adds a bounded `refs/heads/visual-engineer/<workspace-id>` exception
inside the Runner-owned mirror. Reuse accepts it only when the loose ref is
stable, the target is a commit with exactly the approved source revision as
its sole parent, and the destination object set is exactly the union of the
approved source closure and all accepted local-delivery closures. Arbitrary,
replacement, malformed, over-budget, or tampered refs remain fail-closed.

All secret canaries are synthetic. CreativeDeploy is not mounted or accessed.

## Required pre-Phase-5 review

Before adding target commands or any non-fixture repository, independently
re-audit Linux syscall semantics (`openat2`/`renameat2` or a smaller native
helper), registry/signature design, mirror object ownership, safe garbage
collection, filesystem quotas, container egress enforcement, credential
lifecycle, and hostile concurrency. The original independent audit and later
focused/single-finding reviews remain Security Gate FAIL. Round 4 is a local
budget-remediation candidate only. The only next milestone is a new Phase 4
Independent Budget Re-Audit; the preserved FAIL must continue to block merge,
CreativeDeploy, Customer 0, and Phase 5.
