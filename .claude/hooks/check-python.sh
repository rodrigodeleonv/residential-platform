#!/bin/bash
# PostToolUse hook: run ruff + pyright on Python files edited under apps/api.
# Exit 2 feeds the errors back to Claude so it fixes them immediately.
f=$(jq -r '.tool_input.file_path // empty')
[ -n "$f" ] || exit 0
case "$f" in
  *.py) ;;
  *) exit 0 ;;
esac
case "$f" in
  */apps/api/*) ;;
  *) exit 0 ;;
esac
cd "${CLAUDE_PROJECT_DIR:-.}/apps/api" || exit 0

out=$(uv run ruff check "$f" 2>&1) || { printf 'ruff check failed:\n%s\n' "$out" >&2; exit 2; }
out=$(uv run pyright "$f" 2>&1) || { printf 'pyright failed:\n%s\n' "$out" >&2; exit 2; }
exit 0
