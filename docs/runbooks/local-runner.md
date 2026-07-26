# Local Runner Runbook

## Supported local operation

Phase 3 supports one browser-orchestrated, repository-free Local Runner. The
normal operator uses the browser; CLI commands exist only for installation,
startup, diagnostics, verification, and recovery.

Prerequisites are Docker, uv, Node.js, and pnpm as pinned by the repository.
Do not create a real `.env` secret file for the Runner.

## Start

```sh
make bootstrap
make platform-up
```

`platform-up` generates `.env.runner.local` when missing, sets restrictive
permissions, builds and starts PostgreSQL, API, Web, and Runner, waits for
health, and prints browser URLs. It never prints the Bootstrap Token.

Open `http://127.0.0.1:3000/runners`. The Registry should show `online`.

## Browser workflow

1. Review the Runner identity, liveness, protocol/software version, and
   capabilities.
2. Select System Diagnostic or Controlled Wait.
3. Review the non-editable Envelope preview: repository `none`, shell `false`,
   network `control-plane only`, maximum runtime, and no project-code access.
4. Dispatch and observe Job state, Attempt/lease hint, progress, result, and
   Timeline.
5. For a running Controlled Wait, use Cancel. Confirm the intermediate
   `cancel_requested` state before `cancelled`.

The browser never displays a Bootstrap Token, Runner Token, full Lease UUID,
repository locator, or host path.

## Diagnostics

```sh
make runner-status
make runner-smoke
```

`runner-status` waits for an online registry entry. `runner-smoke` starts the
platform if needed, dispatches a real diagnostic through the user API, waits
for success, and validates the restricted Envelope and redacted result.

For local log diagnosis:

```sh
make platform-logs
```

Logs may contain short Runner/Job/Attempt/Lease hints and stable error codes.
They must not contain authorization headers or token values. Stop following
logs with Ctrl-C; that does not stop services.

## Stop

```sh
make platform-down
```

This stops the exact VisualEngineer Compose project and retains named database
and credential volumes. It does not target Customer 0 or another project.

## Strong local verification

```sh
make runner-chaos-check
make verify
```

Chaos uses its own project name, ports, random Bootstrap Token, database, and
credential volume, then removes only those disposable resources. It compares
source-tree status before/after.

## Security restrictions

- Do not add a repository, developer-directory, SSH, or Docker-socket mount to
  Runner.
- Do not attach Runner to the database/Web/default network.
- Do not publish a Runner port or expose the local platform publicly.
- Do not use Runner logs or `docker inspect` to print credential environment or
  volume content.
- Do not describe System Diagnostic as a machine inventory; it intentionally
  excludes hostname, username, IP, environment, paths, files, and packages.
- Do not infer execution authority from a Plan approval.

Credential recovery and revoked/offline behavior are in
[Runner recovery](runner-recovery.md).
