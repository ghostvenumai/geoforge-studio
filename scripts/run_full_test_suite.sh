#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

scripts/run_quality_gate.sh
.venv/bin/pytest backend/tests tests scripts/test_generate_demo_data.py --cov=geoforge --cov-report=term-missing --cov-report=html:artifacts/test-results/backend-htmlcov --cov-report=xml:artifacts/test-results/backend-coverage.xml --cov-fail-under=90
.venv/bin/bandit -r backend/geoforge scripts benchmarks -lll -q -f json -o artifacts/test-results/bandit.json
.venv/bin/pip-audit --requirement requirements.lock --format json --output artifacts/test-results/pip-audit.json
(
  cd frontend
  npm run test:coverage
  npm run test:e2e
)
echo "Full local test suite passed."
