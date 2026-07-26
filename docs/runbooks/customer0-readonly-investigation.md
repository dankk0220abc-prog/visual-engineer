# Customer 0 Read-Only Investigation Runbook

## Purpose

Run the Phase 2 Level 0 workflow against internal Customer 0 CreativeDeploy.
This procedure never approves/rejects the Plan and never writes, installs,
imports, builds, tests, formats, cleans, or changes Git in CreativeDeploy.

## Preconditions

- Work from the VisualEngineer repository.
- Complete the synthetic scanner, PostgreSQL, migration, and E2E gates first.
- Confirm Docker is available.
- Do not store the host repository path in `.env` or another committed file.
- If the read-only mount or committed-HEAD boundary cannot be verified, stop.

## Record the target baseline

Run only these read-only observations:

```sh
git -C "$HOME/Developer/CreativeDeploy" branch --show-current
git -C "$HOME/Developer/CreativeDeploy" rev-parse HEAD
git -C "$HOME/Developer/CreativeDeploy" status --porcelain=v1 -uall
git -C "$HOME/Developer/CreativeDeploy" diff --stat
```

Preserve the output privately during execution. Evidence committed to
VisualEngineer may include branch, `HEAD`, counts, and a sanitized stat, but no
secret, source content, or unnecessary personal absolute path.

## Start and create the governed case

```sh
CUSTOMER0_REPOSITORY_PATH="$HOME/Developer/CreativeDeploy" \
  make customer0-readonly-case
```

The command:

1. builds/starts project `visualengineer-customer0`;
2. mounts the exact host repository only into the API at
   `/repositories/customer0/creative-deploy` with `read_only: true`;
3. sets that exact container path as the only repository allowlist root;
4. creates or idempotently reuses the Customer 0 Task and Run;
5. creates the committed-HEAD Snapshot;
6. creates Frontend Quality Remediation deterministic Plan v1;
7. submits the Plan; and
8. asserts Run `awaiting_plan_approval` and Plan `awaiting_approval`.

The output contains Task ID, Run ID, Snapshot fingerprint, Plan version,
statuses, and the local Run page. It makes no decision.

## Inspect the runtime mount

Resolve the API container and inspect its mounts without attempting to write:

```sh
docker inspect visualengineer-customer0-api-1 \
  --format '{{range .Mounts}}{{println .Destination .RW}}{{end}}'
```

The repository destination must appear with `false` for `.RW`. Inspect the
effective Compose configuration if anything differs:

```sh
CUSTOMER0_REPOSITORY_PATH="$HOME/Developer/CreativeDeploy" \
  docker compose -p visualengineer-customer0 \
  -f compose.yaml -f infra/compose.customer0.yaml config
```

Do not use a write-denial probe against the real repository.

## Record the target after-state

Repeat the four baseline Git commands exactly. Compare branch, `HEAD`, full
porcelain status, and diff stat. If concurrent external work changed them:

- do not clean, reset, stash, or overwrite it;
- do not attribute it to VisualEngineer without evidence;
- report the observed difference; and
- rely on the API-only read-only mount plus fixed scanner operations as the
  access proof.

## Human review

Open the emitted `/runs/{run_id}` page. Confirm Level 0, Committed HEAD,
Snapshot fingerprint, dirty warning, sensitive/skipped paths, safety findings,
deterministic Plan source, non-goals, stop conditions, typed validation steps,
and the two non-execution warnings.

The user—not Codex—then chooses:

- **Approve**, optionally with a note; or
- **Reject**, with a required reason.

The decision is a durable record only. It does not execute code.

## Stop services

After the user has captured any desired evidence:

```sh
CUSTOMER0_REPOSITORY_PATH="$HOME/Developer/CreativeDeploy" \
  make customer0-down
```

This removes only the Customer 0 Compose project containers/network. The named
database volume is preserved unless an explicitly reviewed deletion is
requested.
