#!/usr/bin/env sh
set -eu

PROJECT_NAME=${RUNNER_CHAOS_COMPOSE_PROJECT_NAME:-visualengineer-runner-chaos}
CHAOS_DB_PORT=${CHAOS_DB_PORT:-15435}
CHAOS_API_PORT=${CHAOS_API_PORT:-18002}
RUNNER_BOOTSTRAP_TOKEN=$(uv run python -c 'import secrets; print(secrets.token_urlsafe(48))')
SOURCE_STATUS_BEFORE=$(git status --porcelain=v1 -uall | git hash-object --stdin)
if [ "${CHAOS_SKIP_BUILD:-0}" = "1" ]; then
  BUILD_FLAG=--no-build
else
  BUILD_FLAG=--build
fi

cleanup() {
  RUNNER_BOOTSTRAP_TOKEN="$RUNNER_BOOTSTRAP_TOKEN" \
    docker compose -p "$PROJECT_NAME" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

RUNNER_BOOTSTRAP_TOKEN="$RUNNER_BOOTSTRAP_TOKEN" \
POSTGRES_PUBLISHED_PORT="$CHAOS_DB_PORT" \
API_PUBLISHED_PORT="$CHAOS_API_PORT" \
RUNNER_ONLINE_THRESHOLD_SECONDS=3 \
RUNNER_LEASE_SECONDS=3 \
RUNNER_REAPER_INTERVAL_SECONDS=0.25 \
RUNNER_HEARTBEAT_INTERVAL_SECONDS=0.5 \
RUNNER_POLL_INTERVAL_SECONDS=0.25 \
  docker compose -p "$PROJECT_NAME" up -d "$BUILD_FLAG" --wait db api runner

RUNNER_CHAOS_API_BASE_URL="http://127.0.0.1:$CHAOS_API_PORT" \
RUNNER_CHAOS_PROJECT_NAME="$PROJECT_NAME" \
  uv run python scripts/runner_chaos_check.py

SOURCE_STATUS_AFTER=$(git status --porcelain=v1 -uall | git hash-object --stdin)
test "$SOURCE_STATUS_BEFORE" = "$SOURCE_STATUS_AFTER"
echo "Runner chaos source-tree integrity check passed."
