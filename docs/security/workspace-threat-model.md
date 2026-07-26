# Workspace Threat Model

## Scope and assumptions

This model covers the Phase 4 synthetic fixture, immutable Execution Grant,
Runner-owned mirror/worktree, descriptor-safe UTF-8 tools, checkpoints,
rollback, and disposal. It assumes one trusted local operator and a dedicated
non-root Runner container. Repository content and browser input are hostile
data. It does not claim hostile-user, hostile-kernel, or production isolation.

## Assets

- source repository and its `.git` directory;
- exact approved source revision and Snapshot fingerprint;
- immutable Grant policy and separate decision evidence;
- workspace/mirror/registry ownership;
- file contents, hashes, write ledger, checkpoints, and bounded diff;
- Runner credential, Attempt/Lease identity, and audit integrity;
- sibling workspaces and the host outside managed roots.

## Threats and controls

| Threat                             | Implemented control                                                                         | Residual                                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Host path injection                | Opaque handles registered from Runner-local configuration; no path in user APIs             | Local configuration administrator remains trusted                                                |
| Source mutation                    | Runner-only read-only exact bind, no API/Web/DB mount, source fingerprint before/after      | Host administrator can remount; production attestation absent                                    |
| Dirty/untracked import             | Mirror fetches committed objects and exact detached revision                                | Git implementation is trusted                                                                    |
| Hook/helper/network execution      | Fixed Git arrays, sanitized environment, hooks/helpers/protocols disabled, internal network | Container/runtime hardening needs production review                                              |
| Plan approval treated as execution | Separate pending Grant and local-user decision                                              | No enterprise identity/signature yet                                                             |
| Grant expansion/tamper             | Server-derived scope, immutable DB trigger, canonical hash, per-operation revalidation      | Local DB administrator is trusted                                                                |
| Traversal or symlink escape        | Bounded POSIX parser, descriptor walk, `O_NOFOLLOW`, type checks                            | No `openat2`; see platform limits                                                                |
| Hard-link alias                    | Writable/read leaves require one link                                                       | Read-only committed Git material can still have normal Git semantics                             |
| Replace race                       | Expected SHA-256 plus opened inode identity recheck before atomic rename                    | No kernel pathname CAS against an unexpected same-UID volume writer                              |
| Partial write/crash                | Same-directory temp, fsync, atomic link/rename, deterministic retry cleanup/reconciliation  | Host/filesystem durability semantics remain trusted                                              |
| FIFO/socket/device blocking        | Nonblocking no-follow open plus `fstat` regular-file requirement                            | Device-node creation is prevented by non-root/capability policy, not exhaustively created in E2E |
| Secret exfiltration                | Sensitive path and secret-like content denial, bounded/redacted results/events/log checks   | Heuristics do not replace secret classification                                                  |
| Budget exhaustion                  | File, cumulative bytes, single file, list, diff, result, timeout, attempt, and TTL limits   | Git child output is bounded after capture                                                        |
| Stale Runner result                | Attempt/Lease fencing and authority checks at claim/start/renew/complete                    | Distributed identity/signing remains future work                                                 |
| Rollback over-delete               | Baseline-only restore and exact created-file ledger/hash                                    | No arbitrary checkpoint restore                                                                  |
| Disposal escape                    | Workspace UUID lookup, registry/root identity, managed worktree removal, sibling tests      | No privileged GC after Grant expiry                                                              |

## Revocation and expiry

The Control Plane rechecks approved status, expiry, Runner/Workspace/Handle,
revision, and policy hash for every claim and lease mutation. Revoked or
expired Grants cannot run any Job. Workspace TTL is 20 minutes and Grant TTL is
30 minutes so an expired Workspace can be explicitly discarded while its
Grant remains active. Once the Grant expires, Phase 4 deliberately offers no
authority-bypassing cleanup path.

## Adversarial evidence

The committed fixture definition creates normal and Unicode text, a fake
`.env`, external/sensitive/nested symlinks, binary and oversized content,
malicious `AGENTS.md`, dirty tracked and untracked source data, a source hook,
gitlink, LFS pointer, and collision cases. Runner tests dynamically add FIFO,
UNIX socket, hard link, symlink replacement, cancellation, and interrupted
atomic writes. Real smoke/chaos fingerprint the full source tree and `.git`
before and after.

All secret canaries are synthetic. CreativeDeploy is not mounted or accessed.

## Required pre-Phase-5 review

Before adding target commands or any non-fixture repository, perform a
maximum-depth review of Linux syscall semantics (`openat2`/`renameat2` or a
smaller native helper), registry tamper resistance, mirror object ownership,
safe garbage collection, filesystem quotas, Git output streaming, container
egress enforcement, credential lifecycle, and hostile concurrency. Failure of
that audit must block Phase 5.
