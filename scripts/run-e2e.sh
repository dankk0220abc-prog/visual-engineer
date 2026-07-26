#!/usr/bin/env sh
set -eu

PROJECT_NAME=visualengineer-e2e
E2E_DB_PORT=${E2E_DB_PORT:-15432}
E2E_API_PORT=${E2E_API_PORT:-18000}
E2E_WEB_PORT=${E2E_WEB_PORT:-13000}
FIXTURE_DIRECTORY=$(mktemp -d /tmp/visualengineer-e2e-fixture-XXXXXX)
FIXTURE_REPOSITORY="$FIXTURE_DIRECTORY/repository"
cleanup() {
  E2E_REPOSITORY_PATH="$FIXTURE_REPOSITORY" \
    docker compose -p "$PROJECT_NAME" -f compose.yaml -f infra/compose.e2e.yaml \
      down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$FIXTURE_DIRECTORY"
}
trap cleanup EXIT INT TERM

uv run python scripts/create_adversarial_fixture.py "$FIXTURE_REPOSITORY"
FIXTURE_HEAD_BEFORE=$(git -C "$FIXTURE_REPOSITORY" rev-parse HEAD)
FIXTURE_STATUS_BEFORE=$(git -C "$FIXTURE_REPOSITORY" status --porcelain=v1 -uall | git hash-object --stdin)
E2E_REPOSITORY_PATH="$FIXTURE_REPOSITORY" \
POSTGRES_PUBLISHED_PORT="$E2E_DB_PORT" \
API_PUBLISHED_PORT="$E2E_API_PORT" \
WEB_PUBLISHED_PORT="$E2E_WEB_PORT" \
WEB_ORIGIN="http://127.0.0.1:$E2E_WEB_PORT,http://localhost:$E2E_WEB_PORT" \
NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:$E2E_API_PORT" \
  docker compose -p "$PROJECT_NAME" -f compose.yaml -f infra/compose.e2e.yaml \
    up -d --build --wait db api web
PLAYWRIGHT_BASE_URL="http://127.0.0.1:$E2E_WEB_PORT" \
  pnpm --filter @visual-engineer/web exec playwright test
FIXTURE_HEAD_AFTER=$(git -C "$FIXTURE_REPOSITORY" rev-parse HEAD)
FIXTURE_STATUS_AFTER=$(git -C "$FIXTURE_REPOSITORY" status --porcelain=v1 -uall | git hash-object --stdin)
test "$FIXTURE_HEAD_BEFORE" = "$FIXTURE_HEAD_AFTER"
test "$FIXTURE_STATUS_BEFORE" = "$FIXTURE_STATUS_AFTER"
test ! -e "$FIXTURE_REPOSITORY/lifecycle-ran"
test ! -e "$FIXTURE_REPOSITORY/dependency-lifecycle-ran"
test ! -e "$FIXTURE_REPOSITORY/dirty-lifecycle-ran"
