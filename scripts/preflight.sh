#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

required=(AGENTS.md LOOP_GOAL.md LOOP_STATE.json TASKS.md pyproject.toml frontend/package-lock.json)
for file in "${required[@]}"; do
  [[ -f "$file" ]] || { echo "Missing required file: $file" >&2; exit 20; }
done
[[ -x .venv/bin/python ]] || { echo "Missing .venv; run scripts/bootstrap.sh" >&2; exit 21; }
[[ -d frontend/node_modules ]] || { echo "Missing frontend/node_modules; run scripts/bootstrap.sh" >&2; exit 22; }
command -v codex >/dev/null || { echo "Codex CLI unavailable" >&2; exit 23; }

global_help="$(codex --help)"
help_text="$(codex exec --help)"
[[ "$global_help" == *"--ask-for-approval"* ]] || { echo "Codex CLI does not document --ask-for-approval" >&2; exit 24; }
for argument in --cd --sandbox --model --config; do
  [[ "$help_text" == *"$argument"* ]] || { echo "Codex CLI does not document $argument" >&2; exit 24; }
done
echo "Preflight passed."
