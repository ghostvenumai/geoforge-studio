#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

scripts/preflight.sh
scripts/run_full_test_suite.sh
(
  cd frontend
  npm run build
)
scripts/run_demo_smoke_test.sh
.venv/bin/python -m benchmarks.run_benchmarks --rows 10000 100000
COMPOSE=""
if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
elif docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
fi
if command -v docker >/dev/null && docker info >/dev/null 2>&1 && [[ -n "$COMPOSE" ]]; then
  GEOFORGE_BACKEND_PORT=18081 GEOFORGE_FRONTEND_PORT=15174 $COMPOSE build
  GEOFORGE_BACKEND_PORT=18081 GEOFORGE_FRONTEND_PORT=15174 $COMPOSE up -d --wait
  curl --fail --silent http://127.0.0.1:18081/api/health >/dev/null
  GEOFORGE_BACKEND_PORT=18081 GEOFORGE_FRONTEND_PORT=15174 $COMPOSE down
else
  echo "Docker Compose unavailable; Docker smoke test skipped and must be recorded in FINAL_REPORT.md."
fi
echo "Release gate passed."
