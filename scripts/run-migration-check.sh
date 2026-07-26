#!/usr/bin/env sh
set -eu

cleanup() {
  if [ "${STARTED_TEST_DB:-0}" = "1" ]; then
    docker compose --profile test stop test-db >/dev/null 2>&1 || true
    docker compose --profile test rm -f test-db >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

if [ -z "${TEST_DATABASE_URL:-}" ]; then
  docker compose --profile test up -d --wait test-db
  STARTED_TEST_DB=1
fi
export DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://visualengineer:visualengineer-test-local@localhost:55433/visualengineer_test}"
uv run alembic -c apps/api/alembic.ini downgrade base
uv run alembic -c apps/api/alembic.ini upgrade head
uv run alembic -c apps/api/alembic.ini downgrade base
uv run alembic -c apps/api/alembic.ini upgrade head
