#!/usr/bin/env sh
set -eu

PROJECT_NAME=${E2E_COMPOSE_PROJECT_NAME:-visualengineer-e2e}
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

CHECK_PHASE=postcondition
CHECK_STATUS=0

report_check() {
  e2e_report_status=$1
  e2e_report_name=$2
  e2e_report_expected=$3
  e2e_report_actual=$4
  e2e_report_resource=$5
  e2e_report_exit=$6
  [ -n "$e2e_report_expected" ] || e2e_report_expected='<empty>'
  [ -n "$e2e_report_actual" ] || e2e_report_actual='<empty>'
  printf 'E2E_CHECK phase="%s" status="%s" check="%s" expected="%s" actual="%s" resource="%s" raw_exit=%s\n' \
    "$CHECK_PHASE" "$e2e_report_status" "$e2e_report_name" "$e2e_report_expected" \
    "$e2e_report_actual" "$e2e_report_resource" "$e2e_report_exit"
  if [ "$e2e_report_status" = FAIL ]; then
    CHECK_STATUS=1
  fi
}

check_values_equal() {
  e2e_check_name=$1
  e2e_check_expected=$2
  e2e_check_actual=$3
  e2e_check_resource=$4
  if [ "$e2e_check_expected" = "$e2e_check_actual" ]; then
    report_check PASS "$e2e_check_name" "$e2e_check_expected" "$e2e_check_actual" "$e2e_check_resource" 0
  else
    report_check FAIL "$e2e_check_name" "$e2e_check_expected" "$e2e_check_actual" "$e2e_check_resource" 1 >&2
  fi
}

check_command_equal() {
  e2e_check_name=$1
  e2e_check_expected=$2
  e2e_check_resource=$3
  shift 3
  if e2e_check_actual=$("$@" 2>&1); then
    check_values_equal "$e2e_check_name" "$e2e_check_expected" "$e2e_check_actual" "$e2e_check_resource"
  else
    e2e_check_exit=$?
    report_check FAIL "$e2e_check_name" "$e2e_check_expected" "$e2e_check_actual" "$e2e_check_resource" "$e2e_check_exit" >&2
  fi
}

check_path_absent() {
  e2e_check_name=$1
  e2e_check_path=$2
  if [ ! -e "$e2e_check_path" ] && [ ! -L "$e2e_check_path" ]; then
    report_check PASS "$e2e_check_name" absent absent "$e2e_check_path" 0
  else
    report_check FAIL "$e2e_check_name" absent present "$e2e_check_path" 1 >&2
  fi
}

git_status_hash() {
  e2e_git_repository=$1
  if e2e_git_status=$(git -C "$e2e_git_repository" status --porcelain=v1 -uall); then
    printf '%s' "$e2e_git_status" | git hash-object --stdin
  else
    e2e_git_status_exit=$?
    return "$e2e_git_status_exit"
  fi
}

write_workspace_payload_manifest() {
  e2e_manifest_output=$1
  uv run python scripts/workspace_payload_manifest.py write \
    "$WORKSPACE_FIXTURE_REPOSITORY" "$e2e_manifest_output"
}

workspace_payload_manifest_digest() {
  e2e_manifest_path=$1
  uv run python scripts/workspace_payload_manifest.py digest "$e2e_manifest_path"
}

check_workspace_payload_manifest() {
  e2e_expected_manifest=$1
  e2e_actual_manifest=$2
  e2e_workspace_root=$3
  e2e_expected_digest=$4

  if write_workspace_payload_manifest "$e2e_actual_manifest"; then
    if e2e_actual_digest=$(workspace_payload_manifest_digest "$e2e_actual_manifest"); then
      if [ "$e2e_expected_digest" = "$e2e_actual_digest" ]; then
        report_check PASS workspace-tree "$e2e_expected_digest" "$e2e_actual_digest" \
          "$e2e_workspace_root" 0
      else
        report_check FAIL workspace-tree "$e2e_expected_digest" "$e2e_actual_digest" \
          "$e2e_workspace_root" 1 >&2
        if uv run python scripts/workspace_payload_manifest.py compare \
          "$e2e_expected_manifest" "$e2e_actual_manifest" \
          --check-name workspace-tree --workspace-root "$e2e_workspace_root" >&2; then
          printf 'E2E_WORKSPACE_MANIFEST_DIAGNOSTIC status="FAIL" reason="digest-mismatch-without-entry-diff"\n' >&2
        else
          e2e_manifest_compare_exit=$?
          if [ "$e2e_manifest_compare_exit" -ne 1 ]; then
            printf 'E2E_WORKSPACE_MANIFEST_DIAGNOSTIC status="FAIL" reason="compare-error" raw_exit=%s\n' \
              "$e2e_manifest_compare_exit" >&2
          fi
        fi
      fi
    else
      e2e_manifest_digest_exit=$?
      report_check FAIL workspace-tree "$e2e_expected_digest" manifest-digest-error \
        "$e2e_workspace_root" "$e2e_manifest_digest_exit" >&2
    fi
  else
    e2e_manifest_write_exit=$?
    report_check FAIL workspace-tree "$e2e_expected_digest" manifest-write-error \
      "$e2e_workspace_root" "$e2e_manifest_write_exit" >&2
  fi
  return 0
}

compose_down() {
  E2E_REPOSITORY_PATH="$FIXTURE_REPOSITORY" \
  WORKSPACE_FIXTURE_REPOSITORY_PATH="$WORKSPACE_FIXTURE_REPOSITORY" \
    docker compose -p "$PROJECT_NAME" -f compose.yaml -f infra/compose.workspace.yaml -f infra/compose.e2e.yaml \
      down -v --remove-orphans
}

remove_fixture_directory() {
  rm -rf -- "$FIXTURE_DIRECTORY"
}

project_container_ids() {
  docker ps -aq --filter "label=com.docker.compose.project=$PROJECT_NAME"
}

project_network_ids() {
  docker network ls -q --filter "label=com.docker.compose.project=$PROJECT_NAME"
}

project_volume_ids() {
  docker volume ls -q --filter "label=com.docker.compose.project=$PROJECT_NAME"
}

run_cleanup_command() {
  e2e_cleanup_name=$1
  e2e_cleanup_resource=$2
  shift 2
  if e2e_cleanup_output=$("$@" 2>&1); then
    e2e_cleanup_exit=0
    e2e_cleanup_status=PASS
  else
    e2e_cleanup_exit=$?
    e2e_cleanup_status=WARN
  fi
  printf 'E2E_CLEANUP status="%s" check="%s" expected="0" actual="%s" resource="%s" raw_exit=%s\n' \
    "$e2e_cleanup_status" "$e2e_cleanup_name" "$e2e_cleanup_exit" \
    "$e2e_cleanup_resource" "$e2e_cleanup_exit"
  if [ "$e2e_cleanup_exit" -ne 0 ] && [ -n "$e2e_cleanup_output" ]; then
    printf 'E2E_CLEANUP_DIAGNOSTIC check="%s" output="%s"\n' \
      "$e2e_cleanup_name" "$e2e_cleanup_output" >&2
  fi
}

cleanup() {
  run_cleanup_command compose-down "$PROJECT_NAME" compose_down
  run_cleanup_command fixture-directory-removal "$FIXTURE_DIRECTORY" remove_fixture_directory

  CHECK_PHASE=cleanup-verification
  CHECK_STATUS=0
  check_command_equal residual-containers '' "$PROJECT_NAME" project_container_ids
  check_command_equal residual-networks '' "$PROJECT_NAME" project_network_ids
  check_command_equal residual-volumes '' "$PROJECT_NAME" project_volume_ids
  check_path_absent residual-fixture-directory "$FIXTURE_DIRECTORY"
  return "$CHECK_STATUS"
}

on_exit() {
  e2e_original_exit=$?
  trap - EXIT INT TERM
  set +e
  cleanup
  e2e_cleanup_verification_exit=$?
  if [ "$e2e_original_exit" -ne 0 ]; then
    e2e_final_exit=$e2e_original_exit
  else
    e2e_final_exit=$e2e_cleanup_verification_exit
  fi
  printf 'E2E_RESULT primary_exit=%s cleanup_verification_exit=%s final_exit=%s\n' \
    "$e2e_original_exit" "$e2e_cleanup_verification_exit" "$e2e_final_exit"
  exit "$e2e_final_exit"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

uv run python scripts/create_adversarial_fixture.py "$FIXTURE_REPOSITORY"
uv run python scripts/create_workspace_fixture.py
FIXTURE_HEAD_BEFORE=$(git -C "$FIXTURE_REPOSITORY" rev-parse HEAD)
FIXTURE_STATUS_BEFORE=$(git_status_hash "$FIXTURE_REPOSITORY")
WORKSPACE_HEAD_BEFORE=$(git -C "$WORKSPACE_FIXTURE_REPOSITORY" rev-parse HEAD)
WORKSPACE_STATUS_BEFORE=$(git_status_hash "$WORKSPACE_FIXTURE_REPOSITORY")
WORKSPACE_MANIFEST_BEFORE="$FIXTURE_DIRECTORY/workspace-payload-before.json"
WORKSPACE_MANIFEST_AFTER="$FIXTURE_DIRECTORY/workspace-payload-after.json"
write_workspace_payload_manifest "$WORKSPACE_MANIFEST_BEFORE"
WORKSPACE_TREE_BEFORE=$(workspace_payload_manifest_digest "$WORKSPACE_MANIFEST_BEFORE")
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
if PLAYWRIGHT_BASE_URL="http://127.0.0.1:$E2E_WEB_PORT" \
  PLAYWRIGHT_API_BASE_URL="http://127.0.0.1:$E2E_API_PORT" \
  PLAYWRIGHT_REPOSITORY_ROOT="$PWD" \
  PLAYWRIGHT_COMPOSE_PROJECT_NAME="$PROJECT_NAME" \
  PLAYWRIGHT_E2E_REPOSITORY_PATH="$FIXTURE_REPOSITORY" \
  PLAYWRIGHT_WORKSPACE_FIXTURE_REPOSITORY_PATH="$WORKSPACE_FIXTURE_REPOSITORY" \
    pnpm --filter @visual-engineer/web exec playwright test "$@"; then
  PLAYWRIGHT_EXIT=0
else
  PLAYWRIGHT_EXIT=$?
fi

if [ "$PLAYWRIGHT_EXIT" -eq 0 ]; then
  e2e_playwright_status=PASS
else
  e2e_playwright_status=FAIL
fi
printf 'E2E_SUITE status="%s" check="playwright" expected="0" actual="%s" resource="apps/web/e2e" raw_exit=%s\n' \
  "$e2e_playwright_status" "$PLAYWRIGHT_EXIT" "$PLAYWRIGHT_EXIT"

CHECK_PHASE=postcondition
CHECK_STATUS=0
check_command_equal fixture-head "$FIXTURE_HEAD_BEFORE" "$FIXTURE_REPOSITORY" \
  git -C "$FIXTURE_REPOSITORY" rev-parse HEAD
check_command_equal fixture-status "$FIXTURE_STATUS_BEFORE" "$FIXTURE_REPOSITORY" \
  git_status_hash "$FIXTURE_REPOSITORY"
check_command_equal workspace-head "$WORKSPACE_HEAD_BEFORE" "$WORKSPACE_FIXTURE_REPOSITORY" \
  git -C "$WORKSPACE_FIXTURE_REPOSITORY" rev-parse HEAD
check_command_equal workspace-status "$WORKSPACE_STATUS_BEFORE" "$WORKSPACE_FIXTURE_REPOSITORY" \
  git_status_hash "$WORKSPACE_FIXTURE_REPOSITORY"
check_workspace_payload_manifest "$WORKSPACE_MANIFEST_BEFORE" "$WORKSPACE_MANIFEST_AFTER" \
  "$WORKSPACE_FIXTURE_REPOSITORY" "$WORKSPACE_TREE_BEFORE"
check_path_absent committed-lifecycle-marker "$FIXTURE_REPOSITORY/lifecycle-ran"
check_path_absent dependency-lifecycle-marker "$FIXTURE_REPOSITORY/dependency-lifecycle-ran"
check_path_absent dirty-lifecycle-marker "$FIXTURE_REPOSITORY/dirty-lifecycle-ran"
if [ "${E2E_INJECT_POSTCONDITION_FAILURE:-0}" = 1 ]; then
  check_values_equal injected-postcondition disabled enabled "$FIXTURE_REPOSITORY"
fi
POSTCONDITION_EXIT=$CHECK_STATUS

if [ "$PLAYWRIGHT_EXIT" -ne 0 ]; then
  E2E_PRIMARY_EXIT=$PLAYWRIGHT_EXIT
else
  E2E_PRIMARY_EXIT=$POSTCONDITION_EXIT
fi
printf 'E2E_PRE_CLEANUP_RESULT playwright_exit=%s postcondition_exit=%s primary_exit=%s\n' \
  "$PLAYWRIGHT_EXIT" "$POSTCONDITION_EXIT" "$E2E_PRIMARY_EXIT"
exit "$E2E_PRIMARY_EXIT"
