#!/usr/bin/env sh
set -eu

set +e
output=$(PATH=/visualengineer-no-tools /bin/sh ./scripts/check-secrets.sh 2>&1)
status=$?
set -e

if [ "$status" -eq 0 ]; then
  echo "secret scanner unexpectedly passed without rg" >&2
  exit 1
fi
if [ "$output" != "secret scanner dependency missing: rg" ]; then
  echo "secret scanner missing-rg result was not the fixed safe error" >&2
  exit 1
fi
case "$output" in
  *"No high-confidence secret patterns found."*)
    echo "secret scanner emitted a clean result without rg" >&2
    exit 1
    ;;
esac

set +e
invalid_root_output=$(./scripts/check-secrets.sh "/visualengineer-missing-scan-root" 2>&1)
invalid_root_status=$?
set -e
if [ "$invalid_root_status" -eq 0 ]; then
  echo "secret scanner unexpectedly passed an inaccessible root" >&2
  exit 1
fi
if [ "$invalid_root_output" != "secret scanner failed safely" ]; then
  echo "secret scanner inaccessible-root result was not fixed and safe" >&2
  exit 1
fi

scanner_fixture_dir=$(mktemp -d)
trap 'rm -rf "$scanner_fixture_dir"' EXIT HUP INT TERM

printf '%s\n' 'ordinary fixture text' >"$scanner_fixture_dir/clean.txt"
clean_output=$(./scripts/check-secrets.sh "$scanner_fixture_dir" 2>&1)
if [ "$clean_output" != "No high-confidence secret patterns found." ]; then
  echo "secret scanner clean result was not fixed" >&2
  exit 1
fi

synthetic_secret="sk-$(printf '%024d' 0)"
printf 'synthetic credential fixture: %s\n' "$synthetic_secret" \
  >"$scanner_fixture_dir/synthetic-secret.txt"
set +e
positive_output=$(./scripts/check-secrets.sh "$scanner_fixture_dir" 2>&1)
positive_status=$?
set -e
if [ "$positive_status" -eq 0 ]; then
  echo "secret scanner unexpectedly passed a synthetic match" >&2
  exit 1
fi
case "$positive_output" in
  *"$synthetic_secret"*|*"synthetic credential fixture:"*|*"sk-"*)
    echo "secret scanner disclosed synthetic secret material" >&2
    exit 1
    ;;
esac
case "$positive_output" in
  *"HIGH-CONFIDENCE SECRET PATTERN FOUND:"*"synthetic-secret.txt"*) ;;
  *)
    echo "secret scanner did not emit the fixed finding and path" >&2
    exit 1
    ;;
esac

echo "Secret scanner dependency failure is fail closed."
