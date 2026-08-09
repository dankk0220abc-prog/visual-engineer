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

echo "Secret scanner dependency failure is fail closed."
