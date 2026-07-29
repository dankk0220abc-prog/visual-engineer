#!/usr/bin/env sh
set -eu

PROJECT_NAME=visualengineer-e2e
E2E_DB_PORT=${E2E_DB_PORT:-15432}
E2E_API_PORT=${E2E_API_PORT:-18000}
E2E_WEB_PORT=${E2E_WEB_PORT:-13000}
RUNNER_BOOTSTRAP_TOKEN=$(uv run python -c 'import secrets; print(secrets.token_urlsafe(48))')
FIXTURE_DIRECTORY=$(mktemp -d /tmp/visualengineer-e2e-fixture-XXXXXX)
FIXTURE_REPOSITORY="$FIXTURE_DIRECTORY/repository"
WORKSPACE_FIXTURE_REPOSITORY="$PWD/.runtime/workspace-fixture"
if [ "${E2E_SKIP_BUILD:-0}" = "1" ]; then
  BUILD_FLAG=--no-build
else
  BUILD_FLAG=--build
fi
cleanup() {
  E2E_REPOSITORY_PATH="$FIXTURE_REPOSITORY" \
  WORKSPACE_FIXTURE_REPOSITORY_PATH="$WORKSPACE_FIXTURE_REPOSITORY" \
    docker compose -p "$PROJECT_NAME" -f compose.yaml -f infra/compose.workspace.yaml -f infra/compose.e2e.yaml \
      down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$FIXTURE_DIRECTORY"
}
trap cleanup EXIT INT TERM

uv run python scripts/create_adversarial_fixture.py "$FIXTURE_REPOSITORY"
uv run python scripts/create_workspace_fixture.py
FIXTURE_HEAD_BEFORE=$(git -C "$FIXTURE_REPOSITORY" rev-parse HEAD)
FIXTURE_STATUS_BEFORE=$(git -C "$FIXTURE_REPOSITORY" status --porcelain=v1 -uall | git hash-object --stdin)
WORKSPACE_HEAD_BEFORE=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" rev-parse HEAD)
WORKSPACE_STATUS_BEFORE=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" status --porcelain=v1 -uall | git hash-object --stdin)
WORKSPACE_TREE_BEFORE=$(uv run python scripts/tree_fingerprint.py "$WORKSPACE_FIXTURE_REPOSITORY")
E2E_REPOSITORY_PATH="$FIXTURE_REPOSITORY" \
WORKSPACE_FIXTURE_REPOSITORY_PATH="$WORKSPACE_FIXTURE_REPOSITORY" \
POSTGRES_PUBLISHED_PORT="$E2E_DB_PORT" \
API_PUBLISHED_PORT="$E2E_API_PORT" \
WEB_PUBLISHED_PORT="$E2E_WEB_PORT" \
WEB_ORIGIN="http://127.0.0.1:$E2E_WEB_PORT,http://localhost:$E2E_WEB_PORT" \
NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:$E2E_API_PORT" \
RUNNER_BOOTSTRAP_TOKEN="$RUNNER_BOOTSTRAP_TOKEN" \
  docker compose -p "$PROJECT_NAME" -f compose.yaml -f infra/compose.workspace.yaml -f infra/compose.e2e.yaml \
    up -d "$BUILD_FLAG" --wait db api web runner
WORKSPACE_API_BASE_URL="http://127.0.0.1:$E2E_API_PORT" \
WORKSPACE_DATABASE_URL="postgresql+psycopg://visualengineer:visualengineer-local@127.0.0.1:$E2E_DB_PORT/visualengineer" \
  uv run python scripts/seed_workspace_e2e.py
PLAYWRIGHT_BASE_URL="http://127.0.0.1:$E2E_WEB_PORT" \
PLAYWRIGHT_API_BASE_URL="http://127.0.0.1:$E2E_API_PORT" \
PLAYWRIGHT_REPOSITORY_ROOT="$PWD" \
PLAYWRIGHT_COMPOSE_PROJECT_NAME="$PROJECT_NAME" \
PLAYWRIGHT_E2E_REPOSITORY_PATH="$FIXTURE_REPOSITORY" \
PLAYWRIGHT_WORKSPACE_FIXTURE_REPOSITORY_PATH="$WORKSPACE_FIXTURE_REPOSITORY" \
  pnpm --filter @visual-engineer/web exec playwright test
FIXTURE_HEAD_AFTER=$(git -C "$FIXTURE_REPOSITORY" rev-parse HEAD)
FIXTURE_STATUS_AFTER=$(git -C "$FIXTURE_REPOSITORY" status --porcelain=v1 -uall | git hash-object --stdin)
WORKSPACE_HEAD_AFTER=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" rev-parse HEAD)
WORKSPACE_STATUS_AFTER=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" status --porcelain=v1 -uall | git hash-object --stdin)
WORKSPACE_TREE_AFTER=$(uv run python scripts/tree_fingerprint.py "$WORKSPACE_FIXTURE_REPOSITORY")
test "$FIXTURE_HEAD_BEFORE" = "$FIXTURE_HEAD_AFTER"
test "$FIXTURE_STATUS_BEFORE" = "$FIXTURE_STATUS_AFTER"
test "$WORKSPACE_HEAD_BEFORE" = "$WORKSPACE_HEAD_AFTER"
test "$WORKSPACE_STATUS_BEFORE" = "$WORKSPACE_STATUS_AFTER"
test "$WORKSPACE_TREE_BEFORE" = "$WORKSPACE_TREE_AFTER"
test ! -e "$FIXTURE_REPOSITORY/lifecycle-ran"
test ! -e "$FIXTURE_REPOSITORY/dependency-lifecycle-ran"
test ! -e "$FIXTURE_REPOSITORY/dirty-lifecycle-ran"
