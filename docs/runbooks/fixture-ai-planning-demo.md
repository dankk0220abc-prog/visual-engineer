# Fixture AI Planning Demo

## Purpose

Run the governed AI planning flow against a generated adversarial Git fixture.
The installed Provider is deterministic, synthetic, non-billable, credential-
free, and network-free. This runbook does not authorize a real repository,
Provider, API key, remote Git operation, or deployment.

## Prerequisites

Complete `make bootstrap`, ensure Docker is available, and verify that the
default ports are free or choose project-scoped alternatives. Do not point any
variable in this runbook at a real customer or sibling repository.

## Prepare synthetic inputs

Use an exact task-owned temporary directory:

```sh
test ! -e /tmp/visualengineer-ai-demo
mkdir -p /tmp/visualengineer-ai-demo
uv run python scripts/create_adversarial_fixture.py \
  /tmp/visualengineer-ai-demo/repository
uv run python scripts/create_workspace_fixture.py
uv run python scripts/ensure_runner_bootstrap.py
```

The generated adversarial repository contains only synthetic markers. The
workspace fixture is created under ignored `.runtime/`; the bootstrap token is
created in ignored mode-`0600` `.env.runner.local` and is not printed.

## Start the isolated demo stack

```sh
E2E_REPOSITORY_PATH=/tmp/visualengineer-ai-demo/repository \
WORKSPACE_FIXTURE_REPOSITORY_PATH="$PWD/.runtime/workspace-fixture" \
docker compose --env-file .env.runner.local \
  -p visualengineer-ai-demo \
  -f compose.yaml \
  -f infra/compose.workspace.yaml \
  -f infra/compose.e2e.yaml \
  up -d --build --wait db api web runner
```

Open `http://127.0.0.1:3000` and create a Task with:

- repository kind: `local_path`;
- display name: `Synthetic AI planning fixture`;
- repository locator: `/repositories/e2e/adversarial`; and
- an objective within one documented frontend delivery package.

Start the Run, create the committed-`HEAD` Snapshot, choose a delivery package,
and select the governed AI Plan action. Inspect the Provider capability,
Prompt/context/revision bindings, redactions, typed proposal, Trace, mandatory
Eval results, freshness, and authority boundary.

The operator may switch between English and Simplified Chinese at any time.
Stop before approve/reject unless the human operator intends to record that
decision. Approval still creates only an authority-free Plan handoff with
`execution_available=false`.

## Stop and clean up

Stop only the named demo project:

```sh
E2E_REPOSITORY_PATH=/tmp/visualengineer-ai-demo/repository \
WORKSPACE_FIXTURE_REPOSITORY_PATH="$PWD/.runtime/workspace-fixture" \
docker compose --env-file .env.runner.local \
  -p visualengineer-ai-demo \
  -f compose.yaml \
  -f infra/compose.workspace.yaml \
  -f infra/compose.e2e.yaml \
  down --remove-orphans
```

After confirming the exact path is the generated task-owned fixture, remove
`/tmp/visualengineer-ai-demo` using the host's normal temporary-file cleanup.
Do not delete shared Docker volumes, global caches, or any real repository.
