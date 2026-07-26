# ADR 0003: External Repositories Read-Only by Default

- Status: Accepted

## Context

VisualEngineer is intended to work on real repositories whose content,
credentials, local changes, and Git history may be valuable or hostile.
Treating a task locator as implicit permission would create unacceptable risks:
prompt injection, secret access, path escape, command execution, data loss, and
unreviewed delivery.

## Decision

An external repository is read-only by default. Its locator is metadata, not a
capability. Level 0 investigation may inspect explicitly allowed non-secret
files and Git metadata without running commands that can write.

Future writes require a separate isolated worktree, an exact plan, explicit
human approval, path and command allowlists, a permission ceiling, an audit
trail, verification, a checkpoint, and rollback. Branch/commit and PR creation
are separate elevated levels. Automatic main-branch merge, production deploy,
secret access, and high-risk migrations have no permitted level.

## Consequences

The system must ask for approval and may stop rather than complete a tempting
action. Repository investigation needs before/after baseline evidence. A future
tool runtime must enforce capabilities server-side; UI intent alone is
insufficient. Safety adds workflow steps but makes real-repository adoption
possible.

## Alternatives considered

- Trust any repository selected by the user: rejected because selection does
  not define files, commands, credentials, or delivery authority.
- Write directly in the user's checkout: rejected because it can mix or erase
  existing work and weakens rollback.
- One broad approval for all actions: rejected because read, write, execute,
  Git, PR, merge, and deploy have materially different risks.
- Container-only isolation: rejected as a complete control because mounts,
  tokens, networks, and the Docker socket can still grant excessive authority.
