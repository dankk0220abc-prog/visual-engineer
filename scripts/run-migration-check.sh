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
test_db_port=${TEST_POSTGRES_PUBLISHED_PORT:-55433}
export DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://visualengineer:visualengineer-test-local@127.0.0.1:$test_db_port/visualengineer_test}"
uv run alembic -c apps/api/alembic.ini downgrade base
uv run alembic -c apps/api/alembic.ini upgrade head
uv run alembic -c apps/api/alembic.ini downgrade base
uv run alembic -c apps/api/alembic.ini upgrade head
