#!/usr/bin/env sh
set -eu

PROJECT_NAME=visualengineer-workspace-chaos
CHAOS_DB_PORT=${WORKSPACE_CHAOS_DB_PORT:-15436}
CHAOS_API_PORT=${WORKSPACE_CHAOS_API_PORT:-18003}
WORKSPACE_FIXTURE_REPOSITORY=${WORKSPACE_FIXTURE_REPOSITORY_PATH:-"$PWD/.runtime/workspace-fixture"}
RUNNER_BOOTSTRAP_TOKEN=$(uv run python -c 'import secrets; print(secrets.token_urlsafe(48))')
if [ "${CHAOS_SKIP_BUILD:-0}" = "1" ]; then
  BUILD_FLAG=--no-build
else
  BUILD_FLAG=--build
fi

cleanup() {
  WORKSPACE_FIXTURE_REPOSITORY_PATH="$WORKSPACE_FIXTURE_REPOSITORY" \
    docker compose -p "$PROJECT_NAME" -f compose.yaml -f infra/compose.workspace.yaml \
      down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

uv run python scripts/create_workspace_fixture.py
SOURCE_HEAD_BEFORE=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" rev-parse HEAD)
SOURCE_STATUS_BEFORE=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" status --porcelain=v1 -uall | git hash-object --stdin)
SOURCE_TREE_BEFORE=$(uv run python scripts/tree_fingerprint.py "$WORKSPACE_FIXTURE_REPOSITORY")

export WORKSPACE_FIXTURE_REPOSITORY_PATH="$WORKSPACE_FIXTURE_REPOSITORY"
export POSTGRES_PUBLISHED_PORT="$CHAOS_DB_PORT"
export API_PUBLISHED_PORT="$CHAOS_API_PORT"
export RUNNER_BOOTSTRAP_TOKEN
export RUNNER_ONLINE_THRESHOLD_SECONDS=3
export RUNNER_LEASE_SECONDS=6
export RUNNER_REAPER_INTERVAL_SECONDS=0.25
export RUNNER_HEARTBEAT_INTERVAL_SECONDS=0.5
export RUNNER_POLL_INTERVAL_SECONDS=0.1
export RUNNER_WORKSPACE_PREPARE_DELAY_MS=4000
export RUNNER_WORKSPACE_WRITE_COMMIT_DELAY_MS=2000
export RUNNER_WORKSPACE_WRITE_POST_COMMIT_DELAY_MS=1500

docker compose -p "$PROJECT_NAME" -f compose.yaml -f infra/compose.workspace.yaml \
  up -d "$BUILD_FLAG" --wait db api runner

WORKSPACE_API_BASE_URL="http://127.0.0.1:$CHAOS_API_PORT" \
WORKSPACE_DATABASE_URL="postgresql+psycopg://visualengineer:visualengineer-local@127.0.0.1:$CHAOS_DB_PORT/visualengineer" \
  uv run python scripts/seed_workspace_e2e.py

WORKSPACE_CHAOS_API_BASE_URL="http://127.0.0.1:$CHAOS_API_PORT" \
WORKSPACE_CHAOS_PROJECT_NAME="$PROJECT_NAME" \
  uv run python scripts/workspace_chaos_check.py

SOURCE_HEAD_AFTER=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" rev-parse HEAD)
SOURCE_STATUS_AFTER=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" status --porcelain=v1 -uall | git hash-object --stdin)
SOURCE_TREE_AFTER=$(uv run python scripts/tree_fingerprint.py "$WORKSPACE_FIXTURE_REPOSITORY")
test "$SOURCE_HEAD_BEFORE" = "$SOURCE_HEAD_AFTER"
test "$SOURCE_STATUS_BEFORE" = "$SOURCE_STATUS_AFTER"
test "$SOURCE_TREE_BEFORE" = "$SOURCE_TREE_AFTER"
echo "Workspace chaos source repository and .git fingerprint remained unchanged."
