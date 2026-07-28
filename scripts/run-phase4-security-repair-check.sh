#!/usr/bin/env sh
set -eu

repair_database_url="${TEST_DATABASE_URL:-postgresql+psycopg://visualengineer:visualengineer-test-local@localhost:55433/visualengineer_test}"
repair_started_test_db=false

cleanup() {
  if [ "$repair_started_test_db" = true ]; then
    docker compose --profile test stop test-db >/dev/null 2>&1 || true
    docker compose --profile test rm -f test-db >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

if [ "${PHASE4_REPAIR_MANAGE_TEST_DB:-1}" = "1" ]; then
  if [ -z "$(docker compose --profile test ps --status running -q test-db)" ]; then
    docker compose --profile test up -d --wait test-db
    repair_started_test_db=true
  fi
fi

PYTHONPATH="apps/runner/src:packages/runner-protocol/src" \
  uv run python scripts/check_phase4_findings.py
PYTHONPATH="apps/runner/src:packages/runner-protocol/src" \
  uv run python scripts/check_source_invariance.py
uv run pytest \
  apps/runner/tests/security_audit \
  apps/runner/tests/test_workspace_tools.py \
  packages/runner-protocol/tests \
  --no-cov -q
TEST_DATABASE_URL="$repair_database_url" \
  uv run pytest apps/api/tests/test_workspace_api.py --no-cov -q
