# GitHub Publication Readiness ExecPlan

## Goal

Prepare the exact integrated VisualEngineer baseline for an explicitly
authorized first Private GitHub publication without creating a repository,
configuring a remote, pushing, opening a pull request, tagging, deploying, or
configuring a real Provider.

## Scope

- Read-only current-tree and complete-history publication risk review.
- Canonical English and Chinese README entry points.
- Architecture, Quick Start, deterministic fixture demo, security,
  contribution, License decision, and publication governance documents.
- GitHub Actions, Dependabot, and Issue/PR templates.
- Local static verification and one scoped local checkpoint commit.

Product behavior, dependencies, lockfiles, migrations, real Provider access,
API keys, remote Git, deployment, and historical evidence are outside the
mutation scope.

## Non-goals

- Choosing or adding a formal License.
- Deleting or rewriting historical evidence or Git history.
- Claiming remote GitHub Actions results.
- Changing product behavior, dependencies, lockfiles, tests, migration state,
  or runtime/build authorization.
- Creating a GitHub repository, remote, PR, tag, release, Pages site, package,
  container publication, or deployment.

## Constraints and safety

- Stop on repository root, branch, base SHA, cleanliness, remote, or scope
  mismatch; do not reset, clean, stash, or overwrite.
- Never print a suspected secret value. Report only type, path/commit metadata,
  and a redacted fingerprint if a candidate exists.
- Preserve historical evidence and internal material on the Private path;
  classify it for later Public curation.
- Do not create a real `.env`, Provider key, GitHub credential, or remote.
- Review the complete diff and run `git diff --check` before the only local
  checkpoint commit.

## Current progress

- [x] Verify repository root, branch, expected baseline, cleanliness, remote,
      stash, tags, history count, publication-file inventory, and Git identity.
- [x] Create `chore/github-publication-readiness` from the exact clean default
      branch baseline.
- [x] Scan current tracked content and complete Git history for high-confidence
      secrets without printing candidate values.
- [x] Inventory PII/local paths, internal/customer references, runtime
      artifacts, symlinks, executable modes, binaries, and large objects.
- [x] Classify Private-compatible material and Public conversion blockers.
- [x] Complete publication documents, workflows, templates, and checks.
- [x] Run targeted verification and record every material exit code.
- [x] Review the complete diff, create the local checkpoint commit, and verify
      final branch/HEAD/default-branch/worktree state.

## Decisions

- The first publication target is Private. Historical audit evidence and
  internal Customer 0 material remain preserved and are classified, not
  silently deleted.
- Public conversion remains blocked by License choice, local-path/history
  curation, customer/internal-content review, security contact, and a fresh
  post-curation history scan.
- No Code of Conduct is added while public contribution intake is closed.
- CI uses no repository Secret, grants only `contents: read`, pins every action
  to an immutable commit SHA, and uses deterministic fixtures.
- Product tests and thresholds are not changed to make unrun GitHub Actions
  appear successful.

## Risks

| Risk                                          | Likelihood / impact | Mitigation / next action                                                                             |
| --------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------- |
| Internal evidence becomes public accidentally | Medium / High       | First publication is Private; Public checklist blocks conversion until curated.                      |
| Secret scanner false negative                 | Low / High          | Use existing scanner plus reachable-history scan; require fresh external-quality scan before Public. |
| Workflow looks valid but fails remotely       | Medium / Medium     | Parse and statically inspect locally; label remote CI `NOT VERIFIED` until actual runs exist.        |
| License recommendation is mistaken for grant  | Medium / High       | Do not add `LICENSE`; mark Apache-2.0 as recommendation only.                                        |
| Publication docs overstate product capability | Medium / High       | Cross-check code, ADRs, current evidence, and explicit limitations.                                  |

## Discoveries

- Baseline matched exactly: clean local `main`, no remote/stash/tag, 56
  commits, and configured Git identity.
- Reachable history contains no high-confidence secret marker under the local
  scanners, but it contains local absolute paths and extensive internal
  Customer 0/audit context.
- The tracked tree has no runtime artifact, binary, LFS requirement, symlink,
  submodule, database, or object larger than 0.5 MB.
- Existing README/current-status prose lagged the already integrated Phase 7,
  localization, and Web-build final gate.
- Existing CI already used immutable action SHAs and minimal `contents: read`,
  but did not separate fast and heavy publication-facing gates or declare
  lockfile paths for every cache.

## Verification

- Worktree and complete-history high-confidence secret scan.
- PII/local-path/internal-content counts and author-metadata classification.
- Tracked artifact, large-object, binary, symlink, executable, ignore-rule,
  and LFS review.
- README/document link and command-target checks.
- Markdown formatting, JSON parse, YAML parse, workflow action/permission/cache
  review, and `actionlint` only if installed.
- `.env.example` secret/policy review, source invariance, and `git diff --check`.
- No full `make verify`, because product and core build logic are unchanged.

Exact completed commands and exit codes are maintained in
[`docs/evidence/github-publication-readiness-verification.md`](../evidence/github-publication-readiness-verification.md).
Unfinished final checks are `NOT YET VERIFIED` until that file records exit
code `0`.

## Rollback

All changes are isolated on one local branch. No remote state exists. If the
candidate is rejected, leave the branch for inspection or remove it only after
explicit owner direction; do not reset or rewrite the default branch.

## Completion conditions

- Private/Public verdicts and blockers are explicit and evidence-backed.
- Canonical English/Chinese entry points, architecture, demo, security,
  contribution, License decision, templates, CI, and publication checklists
  exist and agree on product boundaries.
- Required local scans and static checks return exit `0`, except `actionlint`
  may be `NOT AVAILABLE` exactly as authorized.
- Complete diff contains no secret, PII, real customer data, runtime artifact,
  Provider configuration, remote change, or false completion claim.
- One scoped local commit exists; default branch and remote remain unchanged;
  branch worktree is clean.

## Outcome and follow-ups

`COMPLETE`. Publication-only checks pass and the scoped local checkpoint is the
sole branch delta. The Private verdict is ready for explicit repository
creation authorization; Public remains blocked. The checkpoint hash and final
branch/default-branch/worktree state are reported in the final handoff because
a commit cannot contain its own hash.
