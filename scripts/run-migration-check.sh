#!/usr/bin/env sh
set -eu

cleanup() {
  docker compose --profile test stop test-db >/dev/null 2>&1 || true
  docker compose --profile test rm -f test-db >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker compose --profile test up -d --wait test-db
export DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://visualengineer:visualengineer-test-local@localhost:55433/visualengineer_test}"
uv run alembic -c apps/api/alembic.ini downgrade base
uv run alembic -c apps/api/alembic.ini upgrade head
uv run alembic -c apps/api/alembic.ini downgrade base
uv run alembic -c apps/api/alembic.ini upgrade head
