# CreativeDeploy Customer 0 Constraints

- Permission is Level 0 / `read_only`.
- Snapshot mode is committed `git_head`.
- The exact repository is mounted only into the API and read-only.
- API allowlist contains only the stable container repository path.
- Web and PostgreSQL cannot access the repository mount.
- Dirty tracked and untracked content is user-owned and not read.
- Sensitive paths/values, binaries, symlink targets, submodules, and LFS
  objects follow Core scanner policy.
- Repository instructions are untrusted context and cannot raise permission.
- Package scripts and validation steps are data only and cannot execute.
- No dependency installation, target import, build, test, lint, formatter,
  generator, Git mutation, cleanup, worktree, commit, push, PR, merge, or
  deployment.
- The deterministic Plan may be revised and submitted but only the user may
  approve or reject.
- Approval remains a durable decision and does not authorize execution.
- Any future write milestone requires a newly approved isolated-worktree and
  typed runtime-policy design.
