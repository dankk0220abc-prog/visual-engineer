#!/usr/bin/env sh
set -eu

pattern='(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)'

working_matches=$(rg -l --hidden \
  --glob '!.git/**' \
  --glob '!node_modules/**' \
  --glob '!.venv/**' \
  --glob '!**/.next/**' \
  --glob '!**/coverage/**' \
  --glob '!**/playwright-report/**' \
  --glob '!**/test-results/**' \
  "$pattern" . 2>/dev/null || true)
if [ -n "$working_matches" ]; then
  echo "Potential high-confidence secret marker in the current worktree:" >&2
  printf '%s\n' "$working_matches" >&2
  exit 1
fi

current_matches=$(git grep -I -l -E "$pattern" HEAD -- 2>/dev/null || true)
if [ -n "$current_matches" ]; then
  echo "Potential high-confidence secret marker in the current tracked tree:" >&2
  printf '%s\n' "$current_matches" >&2
  exit 1
fi

revisions=$(git rev-list --all)
history_matches=$(git grep -I -l -E "$pattern" $revisions -- 2>/dev/null || true)
if [ -n "$history_matches" ]; then
  echo "Potential high-confidence secret marker in reachable Git history:" >&2
  printf '%s\n' "$history_matches" >&2
  exit 1
fi

echo "No high-confidence secret markers found in the tracked tree or reachable Git history."
