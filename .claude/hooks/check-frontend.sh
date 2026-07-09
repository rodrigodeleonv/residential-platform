#!/bin/bash
# PostToolUse hook: run lint + typecheck on frontend files edited under apps/web.
# No-op until apps/web is scaffolded with package.json scripts named "lint"/"typecheck".
f=$(jq -r '.tool_input.file_path // empty')
[ -n "$f" ] || exit 0
case "$f" in
  *.ts|*.tsx|*.js|*.jsx) ;;
  *) exit 0 ;;
esac
case "$f" in
  */apps/web/*) ;;
  *) exit 0 ;;
esac
web="${CLAUDE_PROJECT_DIR:-.}/apps/web"
[ -f "$web/package.json" ] || exit 0
cd "$web" || exit 0

if jq -e '.scripts.lint' package.json >/dev/null 2>&1; then
  out=$(npm run --silent lint 2>&1) || { printf 'lint failed:\n%s\n' "$out" >&2; exit 2; }
fi
if jq -e '.scripts.typecheck' package.json >/dev/null 2>&1; then
  out=$(npm run --silent typecheck 2>&1) || { printf 'typecheck failed:\n%s\n' "$out" >&2; exit 2; }
fi
exit 0
