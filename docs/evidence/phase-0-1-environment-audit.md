# Phase 0 + 1 Environment Audit

- Audit scope: read-only local development prerequisites
- Platform: macOS 26.5.2, arm64
- Evidence status: audit observations and project-level runtime compatibility
  have been verified.
- Changes made to the system: none by this documentation work

No username, hostname, token, secret, or unnecessary personal path is recorded.

| Tool or resource         | Audit command                      | Actual observation                    | Result                   | Handling                                                                                              |
| ------------------------ | ---------------------------------- | ------------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------- |
| macOS                    | `sw_vers -productVersion`          | `26.5.2`                              | AVAILABLE                | Record only; no system update.                                                                        |
| CPU architecture         | `uname -m`                         | `arm64`                               | AVAILABLE                | Use arm64-compatible local images and tools.                                                          |
| Git                      | `git --version`                    | `2.50.1`                              | AVAILABLE                | Local repository operations are possible.                                                             |
| Xcode Command Line Tools | `xcode-select -p`                  | `/Library/Developer/CommandLineTools` | AVAILABLE                | Existing CLT only; no installation.                                                                   |
| Clang                    | `clang --version`                  | Apple clang `21`                      | AVAILABLE                | Existing compiler only.                                                                               |
| Node.js                  | `node --version`                   | `24.18.0`                             | VERIFIED                 | Pinned and used for install, tests, build, and Playwright.                                            |
| Corepack                 | `corepack --version`               | `0.35.0`                              | AVAILABLE                | May run project-local pnpm without `sudo`.                                                            |
| pnpm                     | `pnpm --version`                   | `11.14.0`                             | VERIFIED                 | Exact package manager pinned; locked local and container installs passed.                             |
| System Python            | `python3 --version`                | `3.9.6`                               | INSUFFICIENT FOR PROJECT | Do not upgrade globally; use uv-managed Python 3.12 for the project.                                  |
| uv                       | `uv --version`                     | `0.11.30`                             | VERIFIED                 | Installed project-managed CPython 3.12.13 and synchronized `uv.lock`.                                 |
| Docker                   | `docker --version`                 | `29.6.2`                              | VERIFIED                 | Docker Desktop daemon 29.6.2/aarch64; image build and runtime passed.                                 |
| Docker Compose           | `docker compose version`           | `5.3.1`                               | VERIFIED                 | Config, build, healthy startup, E2E project, and teardown passed.                                     |
| Make                     | `make --version`                   | GNU Make `3.81`                       | AVAILABLE                | Makefile must remain compatible with this version.                                                    |
| actionlint               | `actionlint -version`              | command not found                     | OPTIONAL TOOL MISSING    | Do not install system-wide; use YAML parsing and local-equivalent command checks.                     |
| Port 3000                | `lsof -nP -iTCP:3000 -sTCP:LISTEN` | no listener                           | AVAILABLE                | Default web port was free at audit time; recheck before start.                                        |
| Port 8000                | `lsof -nP -iTCP:8000 -sTCP:LISTEN` | no listener                           | AVAILABLE                | Default API port was free at audit time; recheck before start.                                        |
| Port 5432                | `lsof -nP -iTCP:5432 -sTCP:LISTEN` | no listener                           | AVAILABLE                | Default PostgreSQL port was free at audit time; recheck before start.                                 |
| Git author name          | `git config --get user.name`       | not configured                        | BLOCKED FOR COMMIT       | Do not invent or change global identity. User must configure an identity if a checkpoint is required. |
| Git author email         | `git config --get user.email`      | not configured                        | BLOCKED FOR COMMIT       | Stop before commit; do not add a fabricated local identity.                                           |

The table records the original environment-audit start state.

## Conclusions

- The machine has the required package managers, container daemon, compiler,
  and ports for the Foundation work.
- System Python 3.9.6 is not the project runtime. The repository must use a
  uv-managed Python 3.12 environment without modifying the system interpreter.
- Missing `actionlint` is not permission to install it globally and is not by
  itself a runtime blocker.
- At original audit time, a legitimate local Git commit was blocked because
  author identity was absent. No Agent fabricated identity or claimed a
  checkpoint.
- Project compatibility is evidenced by locked installs, Docker build/start,
  tests, migrations, and browser flows in the verification ledger.

## Foundation closure update

The later Foundation closure task was explicitly authorized to discover
repository-level identity from CreativeDeploy when VisualEngineer remained
unset. Both source fields were complete, non-placeholder, and syntactically
reasonable, so they were copied only into VisualEngineer's local Git
configuration. Global Git configuration and CreativeDeploy configuration were
not modified. The original observations above remain historical evidence and
are superseded only for the current VisualEngineer repository-local identity
state.
