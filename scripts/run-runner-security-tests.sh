#!/usr/bin/env sh
set -eu

cleanup() {
  docker compose --profile test stop test-db >/dev/null 2>&1 || true
  docker compose --profile test rm -f test-db >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker compose --profile test up -d --wait test-db
TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+psycopg://visualengineer:visualengineer-test-local@localhost:55433/visualengineer_test}" \
  uv run pytest \
    packages/runner-protocol/tests \
    apps/api/tests/test_runner_api.py \
    apps/api/tests/test_runner_concurrency.py \
    apps/runner/tests \
    --no-cov -q
