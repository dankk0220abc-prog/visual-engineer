#!/usr/bin/env sh
set -eu

PATTERN='(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)'

if ! command -v rg >/dev/null 2>&1; then
  echo "secret scanner dependency missing: rg" >&2
  exit 2
fi

scan_root=${1:-.}

set +e
matches=$(
  if ! cd "$scan_root" 2>/dev/null; then
    exit 2
  fi
  rg --files-with-matches --hidden \
    --glob '!.git/**' \
    --glob '!node_modules/**' \
    --glob '!.venv/**' \
    --glob '!playwright-report/**' \
    --glob '!test-results/**' \
    --glob '!coverage/**' \
    --glob '!htmlcov/**' \
    "$PATTERN" . 2>/dev/null
)
scan_status=$?
set -e

case "$scan_status" in
  0)
    printf '%s\n' "$matches" | while IFS= read -r matched_path; do
      [ -n "$matched_path" ] || continue
      echo "HIGH-CONFIDENCE SECRET PATTERN FOUND: $matched_path" >&2
    done
    exit 1
    ;;
  1)
    echo "No high-confidence secret patterns found."
    ;;
  *)
    echo "secret scanner failed safely" >&2
    exit 2
    ;;
esac
