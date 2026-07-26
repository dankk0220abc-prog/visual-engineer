#!/usr/bin/env sh
set -eu

OPENAPI=packages/api-contract/openapi.json
SCHEMA=packages/api-contract/src/schema.d.ts
if [ ! -f "$OPENAPI" ] || [ ! -f "$SCHEMA" ]; then
  echo "Generated contract files are missing. Run make contracts." >&2
  exit 1
fi

TMP_DIR=$(mktemp -d /tmp/visualengineer-contract-XXXXXX)
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

cp "$OPENAPI" "$TMP_DIR/openapi.json"
cp "$SCHEMA" "$TMP_DIR/schema.d.ts"
pnpm --filter @visual-engineer/api-contract generate
cmp "$TMP_DIR/openapi.json" "$OPENAPI"
cmp "$TMP_DIR/schema.d.ts" "$SCHEMA"
