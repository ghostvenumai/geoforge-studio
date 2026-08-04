#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

.venv/bin/ruff check backend scripts benchmarks tests
.venv/bin/ruff format --check backend scripts benchmarks tests
.venv/bin/mypy backend/geoforge scripts benchmarks
.venv/bin/pytest backend/tests/unit tests scripts/test_generate_demo_data.py -q
(
  cd frontend
  npm run lint
  npm run typecheck
  npm test
)
echo "Fast quality gate passed."
