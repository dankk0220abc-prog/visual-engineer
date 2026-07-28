# Phase 4 Independent Focused Security Re-Audit Verification

- Date: 2026-07-29
- Closed: 2026-07-29T02:03:49+08:00
- Repository: `/Users/danke/Developer/VisualEngineer`
- Branch: `audit/phase-4-security-focused-reaudit-max`
- Candidate:
  `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`
- Decision:
  **FOCUSED RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED**

## Evidence rules

- `CONFIRMED` means the current reviewer observed the command or inspected the
  current candidate.
- `INFERRED` is used only for a conclusion derived from confirmed evidence and
  is identified as such.
- `NOT VERIFIED` means the check was not run in this focused re-audit.
- Implementer evidence is navigation, not independent approval.
- Exit codes, selected/test counts, first failures, corrections, and stopped
  checks are recorded rather than normalized away.

## Baseline and repository identity

All baseline checks ran before the first audit edit.

| Command / observation                                                 | Exit | CONFIRMED result                                                          |
| --------------------------------------------------------------------- | ---: | ------------------------------------------------------------------------- |
| `pwd` and `git rev-parse --show-toplevel`                             |    0 | Both resolve to `/Users/danke/Developer/VisualEngineer`.                  |
| `git branch --show-current`                                           |    0 | Starting branch was `fix/phase-4-security-remediation-2`.                 |
| `git rev-parse HEAD`                                                  |    0 | `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1`.                               |
| `git status --short` and porcelain-v2 status                          |    0 | Tracked worktree, index, and untracked inventory were empty.              |
| worktree and cached `git diff --check`                                |    0 | No baseline whitespace error.                                             |
| `git remote -v`                                                       |    0 | No configured remote.                                                     |
| `git stash list`                                                      |    0 | No stash.                                                                 |
| `git show-ref --tags`                                                 |    1 | Expected no-match exit; no tags exist.                                    |
| `git cat-file -e <hash>^{commit}` for all disclosed commits           |    0 | Every disclosed hash is a commit object.                                  |
| exact parent and ancestry checks                                      |    0 | The disclosed chain is linear and every transition is exactly one commit. |
| `git rev-list --count b457b61..cb799bc`                               |    0 | `1`.                                                                      |
| focused branch nonexistence check                                     |    1 | Expected no-match exit; the branch did not pre-exist.                     |
| `git switch -c audit/phase-4-security-focused-reaudit-max cb799bc...` |    0 | Audit branch created directly from the exact candidate.                   |

Disclosed protected refs at baseline:

| Ref                    | Hash                                       |
| ---------------------- | ------------------------------------------ |
| `main`                 | `7590f9dcecbf06371936ac0265cecb9f7a4438ca` |
| Phase 4 implementation | `53dc2f5016e9b76e1f39c6306fe116ee4091b302` |
| original audit         | `a560509b2018f86693e38e3646409f9e33841829` |
| first repair           | `e3d653023a55e387f22d0e453a1b9bdaeed6ac3c` |
| independent re-audit   | `b457b614bde6630fb50ff9546c92a4d6925ad38a` |
| Round 2 candidate      | `cb799bcf1407c2c797da46c5a2d0aa0a6b73d3f1` |

`git fsck --full --no-reflogs --unreachable` reported three unreachable
commits: `286300c...`, `b3e3138...`, and `a8a5061...`. Current reflogs identify
them as pre-amend predecessors of disclosed Phase 2, Phase 3, and original
audit commits. They are not refs, stashes, an extra Round 2 commit, or a
second candidate history. No object was deleted or pruned.

The Round 2 diff contains 25 changed files, 4,390 insertions, and 427
deletions. The current reviewer read the full governance set, complete
blocking-reproduction file, all affected threat-model/architecture/runbook/
ADR material, and the production paths governing Git object import, mirror
reuse, ownership/discard, subprocess lifecycle, Permit models/protocol/
repository/service, configuration, and Compose isolation.

## Frozen production boundary

The frozen boundary is:

```text
apps/api/src
apps/runner/src
packages/runner-protocol/src
apps/api/alembic
apps/api/Dockerfile
apps/runner/Dockerfile
compose.yaml
infra
```

It contains 72 tracked files.

| Evidence                         | SHA-256                                                            |
| -------------------------------- | ------------------------------------------------------------------ |
| Initial current-content manifest | `3ca1448901c572da082a75fb002da81b73b347974c753e8ef7b28f5a167787d3` |
| Candidate Git-tree listing       | `be07a14623a65593d5f0c8ddd1a22219b3b7aa3f30f8ee7794206282f312c707` |

Before checkpoint, the same commands are repeated and the production paths
must have no worktree or staged diff from the candidate.

## Audit-only additions

The reviewer added three distinct secure-expectation cases:

1. `test_focused_existing_mirror_packed_replace_cannot_change_checkout`;
2. `test_focused_completed_proof_replay_preserves_symlink_root_replacement`;
3. `test_focused_timeout_kills_child_that_closes_output_after_leader_exit`;
4. `test_focused_five_way_permit_consume_converges_on_one_postgresql_row`.

The first three are in
`apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py`;
the Permit case is in `apps/api/tests/test_workspace_api.py`. No existing test
was removed, weakened, skipped, or marked expected-failing.

## Git object-closure focused run

### Static inspection

`CONFIRMED`:

- the source parser computes a bounded approved commit/ancestor/tree/blob
  closure and validates loose and packed objects;
- destination validation compares the managed mirror's exact object set;
- loose replacement paths, grafts, alternates, unsupported config, and object
  layout drift are rejected;
- existing-mirror validation does not reject a `refs/replace/*` entry encoded
  in `packed-refs`; and
- the fixed Git subprocess environment does not disable replacement-object
  interpretation.

`INFERRED` from those confirmed facts: exact object-ID set equality does not
prevent semantic commit replacement when both the approved commit and its
replacement target already belong to the approved ancestry closure.

### Minimal synthetic reproduction

A temporary reviewer-only probe created two commits, prepared the managed
mirror, added a packed replacement mapping, and requested the second commit.
It observed:

```text
workspace_content='original\n'
expected='approved second revision\n'
replacement_applied=True
```

The same scenario was converted into a repository audit test with two secure
acceptable outcomes: typed rejection, or exact approved content.

### First failure and corrected assertion

The first test version required only an exception. Its first run exited `1`
with `DID NOT RAISE`: the candidate accepted the mirror. This was an
over-narrow audit assertion because a secure implementation could also
sanitize the metadata and produce exact content.

The reviewer corrected only the new audit test to accept either a typed
fail-closed rejection or an exact approved checkout. The corrected test
stably exits `1`:

```text
actual:   'original\n'
expected: 'approved second revision\n'
```

This is a production security failure, not an audit-test error or expected
failure. It is recorded as `VE-P4-FREAUD-001`, Critical.

## Focused Runner and Protocol commands

| Command                                                                                                                          | Exit | Result                                                |
| -------------------------------------------------------------------------------------------------------------------------------- | ---: | ----------------------------------------------------- |
| `/opt/homebrew/bin/uv run pytest apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py -k focused_ --no-cov -q` |    1 | `1 failed, 2 passed`; only packed replacement failed. |
| `/opt/homebrew/bin/uv run pytest apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py --no-cov -q`             |    1 | `1 failed, 9 passed`; only packed replacement failed. |
| `/opt/homebrew/bin/uv run pytest apps/runner/tests/test_workspace_tools.py packages/runner-protocol/tests --no-cov -q`           |    0 | `52 passed in 8.78s`.                                 |

The discard-proof and process-group focused cases therefore pass, including
the two new independent variations. The object-closure scope fails.

## Real-PostgreSQL Permit matrix

The exact disposable service was started with:

```bash
docker compose --profile test up -d --wait test-db
```

It exited `0` and reported healthy. Tests received an explicit repository
test URL for PostgreSQL on `127.0.0.1:55433`; no `.env` file was edited.

| Command scope                                               | Exit | Result                                                  |
| ----------------------------------------------------------- | ---: | ------------------------------------------------------- |
| independent five-session Permit test                        |    0 | `1 passed`; one unrelated Starlette deprecation warning |
| complete `apps/api/tests/test_workspace_api.py --no-cov -q` |    0 | `13 passed, 1 warning in 2.82s`                         |

The independent test uses five separate PostgreSQL sessions synchronized by a
barrier. It confirms:

- one Permit UUID;
- one durable Permit row and one event;
- sequence `1`;
- one non-replay consumer; and
- four exact idempotent replays.

The service was then cleaned with:

```bash
docker compose --profile test stop test-db
docker compose --profile test rm -f test-db
docker compose --profile test ps --all test-db
```

All commands exited `0`; the final listing contains no `test-db` service row.
No broad Docker cleanup was performed. Existing base platform services were
left untouched.

## Source invariance

`make source-invariance-check` exited `0` with JSON status `PASS`:

```text
branch=main
extension_markers=0
source_entries_compared=119
source_git_objects_compared=10
source_status_records=2
```

This confirms no synthetic source mutation. It does not validate the semantic
identity of the resulting worktree and therefore does not offset the Critical
failure.

## Stopped Gate

The stable Critical result triggered the work order's stop rule. The reviewer
did **not** run or infer:

- complete format/lint/type/unit/build/contract/migration Gate;
- aggregate `make verify`;
- complete Docker isolation/resource cleanup Gate;
- Web/browser E2E;
- workspace smoke or chaos;
- security or Eval targets; or
- remote CI.

Only scoped audit-file formatting/lint checks, diff checks, final invariant
hashing, and Git checkpoint validation remain authorized after the failure.

## Failure and correction ledger

| Event                                                         | Classification                                       | Disposition                                                   |
| ------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| `git show-ref --tags` exited `1`                              | Expected no-match                                    | Recorded as confirmation of no tags.                          |
| `git fsck` listed three unreachable commits                   | Explained repository state                           | Reconciled through reflogs; no delete/prune.                  |
| Temporary packed-replacement probe returned wrong content     | Critical production reproduction                     | Converted to additive audit test.                             |
| First exception-only audit assertion reported `DID NOT RAISE` | Over-narrow new audit assertion                      | Corrected to accept either secure rejection or exact content. |
| Corrected packed-replacement test returns wrong content       | Stable Critical production failure                   | Preserved; Security Gate FAIL.                                |
| Focused three-test and complete ten-test files exit `1`       | Expected consequence of open finding, not an `xfail` | Exact failing assertion and passing counts recorded.          |

No production code was changed to repair any failure.

## Final invariant closure

The exact pre-checkpoint changed-path inventory is:

```text
apps/api/tests/test_workspace_api.py
apps/runner/tests/security_audit/test_phase4_blocking_reproductions.py
docs/evidence/phase-4-security-focused-reaudit-verification.md
docs/exec-plans/phase-4-security-focused-reaudit-max.md
docs/security/audits/phase-4-security-focused-reaudit.md
docs/status/project-status.md
```

No production path appears in the inventory.

| Closing check                                             | Exit / result                                                      |
| --------------------------------------------------------- | ------------------------------------------------------------------ |
| scoped `ruff format --check` for the two audit-test files | 0; two files already formatted                                     |
| scoped `ruff check` for the two audit-test files          | 0; all checks passed                                               |
| scoped Prettier check for the four documents              | 0; all matched files use Prettier style                            |
| `git diff --check`                                        | 0                                                                  |
| repeated 72-file current-content digest                   | `3ca1448901c572da082a75fb002da81b73b347974c753e8ef7b28f5a167787d3` |
| repeated candidate Git-tree listing digest                | `be07a14623a65593d5f0c8ddd1a22219b3b7aa3f30f8ee7794206282f312c707` |
| candidate diff under frozen production paths              | 0; empty                                                           |
| protected refs                                            | unchanged                                                          |
| remote / stash / tag inventories                          | empty                                                              |

The six paths are staged only after this review and committed once with:

```text
audit(security): focused re-audit phase 4 blockers
```

The post-checkpoint handoff confirms the final clean worktree/index and
records the commit hash externally because a commit cannot contain its own
hash. No remote, push, merge, pull request, tag, delivery, deployment, or
Phase 5 action is performed.

## Evidence classification summary

| Claim                                                    | Classification                                 |
| -------------------------------------------------------- | ---------------------------------------------- |
| Candidate identity, ancestry, refs, clean baseline       | CONFIRMED                                      |
| Packed replacement changes successful checkout bytes     | CONFIRMED                                      |
| This breaks exact revision/Grant binding                 | INFERRED from confirmed runtime and code facts |
| Discard focused scope passes                             | CONFIRMED                                      |
| Process-group focused scope passes                       | CONFIRMED                                      |
| Permit focused scope passes on real PostgreSQL           | CONFIRMED                                      |
| Source fixture remains invariant                         | CONFIRMED                                      |
| Full aggregate/Docker/E2E/smoke/chaos/security/Eval Gate | NOT VERIFIED                                   |
| Remote CI or production/customer behavior                | NOT VERIFIED                                   |

`FOCUSED RE-AUDIT COMPLETE — SECURITY GATE FAIL — REMEDIATION REQUIRED`
