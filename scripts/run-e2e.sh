#!/usr/bin/env sh
set -eu

PROJECT_NAME=visualengineer-e2e
E2E_DB_PORT=${E2E_DB_PORT:-15432}
E2E_API_PORT=${E2E_API_PORT:-18000}
E2E_WEB_PORT=${E2E_WEB_PORT:-13000}
cleanup() {
  docker compose -p "$PROJECT_NAME" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

POSTGRES_PUBLISHED_PORT="$E2E_DB_PORT" \
API_PUBLISHED_PORT="$E2E_API_PORT" \
WEB_PUBLISHED_PORT="$E2E_WEB_PORT" \
WEB_ORIGIN="http://127.0.0.1:$E2E_WEB_PORT,http://localhost:$E2E_WEB_PORT" \
NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:$E2E_API_PORT" \
  docker compose -p "$PROJECT_NAME" up -d --build --wait db api web
PLAYWRIGHT_BASE_URL="http://127.0.0.1:$E2E_WEB_PORT" \
  pnpm --filter @visual-engineer/web exec playwright test
