#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$PROJECT_ROOT/artifacts/runtime"

for service in frontend backend; do
  pid_file="$RUNTIME_DIR/$service.pid"
  if [[ -f "$pid_file" ]]; then
    pid="$(tr -cd '0-9' <"$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
    fi
    .venv/bin/python -c 'from pathlib import Path; import sys; Path(sys.argv[1]).unlink(missing_ok=True)' "$pid_file"
  fi
done
echo "GeoForge-Studio-Demo wurde beendet."
