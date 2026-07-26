#!/usr/bin/env sh
set -eu

PATTERN='(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)'

if rg -n --hidden \
  --glob '!.git/**' \
  --glob '!node_modules/**' \
  --glob '!.venv/**' \
  --glob '!playwright-report/**' \
  --glob '!test-results/**' \
  --glob '!coverage/**' \
  --glob '!htmlcov/**' \
  "$PATTERN" .; then
  echo "Potential secret material found." >&2
  exit 1
fi

echo "No high-confidence secret patterns found."
