#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_PATH="$PROJECT_ROOT/.automation-loop.lock"

cleanup() {
  if [[ -d "$LOCK_PATH" ]]; then
    rmdir "$LOCK_PATH" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

cd "$PROJECT_ROOT"
.venv/bin/python -m automation.run_loop "$@"
