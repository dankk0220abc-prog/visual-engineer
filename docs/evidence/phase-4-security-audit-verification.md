# Phase 4 Maximum-Depth Security Audit Evidence

- Started: 2026-07-28T12:58:43+08:00
- Audit branch: `audit/phase-4-workspace-security-max`
- Phase 4 commit: `53dc2f5016e9b76e1f39c6306fe116ee4091b302`
- Main baseline: `7590f9dcecbf06371936ac0265cecb9f7a4438ca`
- Remote CI: not run; no remote is configured
- Status: COMPLETE — SECURITY GATE FAIL

## Trusted baseline

The pre-write checks observed:

- exact repository root and expected feature branch;
- exact Phase 4 and Phase 3 commits;
- clean tracked and untracked worktree;
- no Git remote;
- repository-local author name and email present; and
- four healthy base Compose services.

The production baseline contains 69 tracked files. The SHA-256 content
manifest digest is
`d4e48b0ae34ccb686bb0f484d8a51c25a5c01cc39999dfd30ba7e610862aeb26`.
The Git-tree manifest digest is
`92cdff10f1abd70d75364e7c3857237417629d984006aa123b12395bd039b357`.
The generated manifests are kept outside the repository in a unique
`/tmp/visualengineer-phase4-audit-baseline-*` directory and will be compared
after all tests.

## Commands and results

| Command / probe                           | Exit | Result                                      |
| ----------------------------------------- | ---: | ------------------------------------------- |
| `pwd` and `git rev-parse --show-toplevel` |    0 | exact instructed repository                 |
| branch/HEAD/main/status/remote/log        |    0 | exact expected commits; clean; no remote    |
| repository-local Git identity             |    0 | both values present                         |
| `docker compose ps`                       |    0 | API, DB, Runner, Web healthy/running        |
| `docker compose config`                   |    0 | base topology rendered                      |
| production file/hash/tree freeze          |    0 | 69 files; digests recorded above            |
| create audit branch                       |    0 | exact Phase 4 starting commit               |
| `make workspace-security-audit`           |    0 | 4 closed synthetic observations passed      |
| `make format-check`                       |    0 | final pass after formatting audit docs      |
| `make lint`                               |    0 | Ruff and ESLint pass                        |
| `make typecheck`                          |    0 | mypy 71 files and TypeScript pass           |
| `make test`                               |    0 | backend 105; frontend 39                    |
| `make build`                              |    0 | production Web build                        |
| `make contracts-check`                    |    0 | generated contracts unchanged               |
| `make migration-check`                    |    0 | PostgreSQL upgrade/downgrade/upgrade        |
| `make workspace-security-check`           |    0 | 25 focused tests plus static check          |
| `make security-check`                     |    0 | secret/static checks; 7 plus 46 tests       |
| `make eval`                               |    0 | 58 deterministic cases plus 7 scanner tests |
| `make e2e`                                |    0 | 12 browser tests                            |
| `make workspace-smoke`                    |    0 | real-stack synthetic-fixture flow           |
| `make workspace-chaos-check`              |    0 | bounded crash/retry flow                    |
| `make verify`                             |    0 | aggregate mandatory gate                    |
| `git diff --check`                        |    0 | no whitespace errors                        |
| final production SHA-256 comparison       |    0 | exact 69-file match                         |

## Review ledger

| Area                  | Status   | Evidence                                   |
| --------------------- | -------- | ------------------------------------------ |
| Repository Handle     | REVIEWED | opaque handle source/API/runtime trace     |
| Execution Grant       | FAIL     | `VE-P4-AUD-002`                            |
| Lease and fencing     | FAIL     | `VE-P4-AUD-002`                            |
| Mirror and worktree   | FAIL     | `VE-P4-AUD-001`, `VE-P4-AUD-004`           |
| Descriptor-safe paths | REVIEWED | source trace plus focused tests            |
| Atomic write          | REVIEWED | focused and chaos tests                    |
| Rollback and discard  | FAIL     | `VE-P4-AUD-003`                            |
| Resource isolation    | GAP      | `VE-P4-AUD-005`                            |
| Docker and network    | PASS     | live container inspection and reachability |
| Static/supply chain   | GAP      | local checks pass; `VE-P4-AUD-006` remains |

## Independent test ledger

The audit target ran four closed synthetic observations:

- `VE-P4-AUD-001`: two observations;
- `VE-P4-AUD-002`: one observation; and
- `VE-P4-AUD-003`: one observation.

Result: `4 passed`. The observations confirm current unsafe behavior and are
not evidence of a product Security Gate pass.

## Mandatory verification ledger

Every command mandated by the audit instruction ran. Individual commands and
the aggregate `make verify` exited zero. The project test totals include the
four audit observations.

## Failures and corrected methodology

The following failures or invalid first methods are retained:

1. The first source snapshot method followed fixture symlinks and treated a
   Gitlink as a regular file. It was discarded and replaced with a
   type-aware, no-follow manifest.
2. Two initial Docker inspection commands were incomplete: one omitted the
   required fixture environment, and one encountered an expected non-root
   permission denial. The corrected probes used the rendered fixture
   environment and kernel/container inspection.
3. The first `make format-check` failed only on the three new audit Markdown
   files. Prettier was run on exactly those files; the repeated command and
   aggregate `make verify` passed.
4. Strict source invariance failed and was not corrected or waived.

## Source invariance

**FAIL.** The corrected before/after proof compared:

- full no-follow tree content/type fingerprint;
- HEAD, branch, refs, local config, index, and binary porcelain status;
- tracked and untracked content;
- every `.git` regular-file hash;
- Git object inode/link/size inventory; and
- file/directory counts and complete lstat metadata.

All items matched except the mtimes of the root `.git` directory and the
nested submodule Git metadata directory. Modes, owners, sizes, inodes, file
content, refs, index, status, and counts remained exact. The metadata change
is confirmed. Attribution to the exact lifecycle call is **NOT FULLY
VERIFIED** and is not treated as a pass.

## Docker runtime

**PASS for declared topology; resource gap recorded.** Live inspection
verified:

- Runner UID 10001, zero effective capabilities, `no-new-privileges`, and a
  read-only rootfs;
- a Runner-only read-only fixture mount and Runner-only writable private
  volumes;
- no source/private mounts on API, Web, or PostgreSQL;
- no Docker socket and no published Runner port;
- an internal Runner/API network with no Runner default route;
- API reachable from Runner; DB and Web unresolved from Runner; and
- write probes against the source and rootfs rejected read-only.

No public DNS or HTTP probe was attempted. Explicit CPU, memory, and PID limits
were absent and are recorded as `VE-P4-AUD-005`.

## Final Gate

**FAIL.**

- Critical: 3
- High: 1
- Medium: 1
- Low: 1
- Production hash: unchanged
- Strict source invariance: failed
- `main`: unchanged and not merged
- Next milestone: Phase 4 security repair, then a fresh independent audit

## Preserved result and later repair branch

This file is the immutable narrative of the independent audit run. Its FAIL
result, command ledger, findings, and source-invariance failure are not
superseded by later local implementation.

A subsequent isolated repair branch records new evidence in
`docs/evidence/phase-4-security-repair-verification.md`. That evidence may show
the candidate blocks the original reproductions, but it is not an independent
Security Gate PASS. Phase 4 is still outside `main`, CreativeDeploy was not in
scope, and the only next milestone is **Phase 4 Independent Security
Re-Audit**.
