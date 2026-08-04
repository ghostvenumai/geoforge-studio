#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
.venv/bin/pytest backend/tests/integration/test_api_workflow.py -q
echo "API demo smoke test passed."
