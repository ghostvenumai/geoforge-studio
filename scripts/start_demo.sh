#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$PROJECT_ROOT/artifacts/runtime"
BACKEND_PORT="${GEOFORGE_BACKEND_PORT:-8000}"
FRONTEND_PORT=5173
mkdir -p "$RUNTIME_DIR"
cd "$PROJECT_ROOT"

[[ ! -f "$RUNTIME_DIR/backend.pid" ]] || { echo "Die Demo scheint bereits zu laufen. Verwenden Sie zuerst scripts/stop_demo.sh." >&2; exit 30; }
.venv/bin/uvicorn geoforge.main:app --app-dir backend --host 127.0.0.1 --port "$BACKEND_PORT" >"$RUNTIME_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" >"$RUNTIME_DIR/backend.pid"
(
  cd frontend
  export VITE_API_URL="http://127.0.0.1:$BACKEND_PORT/api"
  exec ./node_modules/.bin/vite --host 127.0.0.1 --port "$FRONTEND_PORT"
) >"$RUNTIME_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" >"$RUNTIME_DIR/frontend.pid"

trap 'scripts/stop_demo.sh >/dev/null 2>&1 || true' ERR INT TERM
for _ in {1..60}; do
  if curl --fail --silent "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null && curl --fail --silent "http://127.0.0.1:$FRONTEND_PORT/" >/dev/null; then
    echo "GeoForge Studio ist bereit unter http://127.0.0.1:$FRONTEND_PORT"
    trap - ERR INT TERM
    exit 0
  fi
  sleep 1
done
echo "Die Demo wurde nicht rechtzeitig betriebsbereit. Prüfen Sie artifacts/runtime/*.log" >&2
exit 31
