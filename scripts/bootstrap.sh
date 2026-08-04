#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

python3 main.py bootstrap
(
  cd frontend
  npm ci
)

if [[ -x /usr/bin/ffmpeg ]]; then
  mkdir -p frontend/node_modules/.cache/ms-playwright/ffmpeg-1011
  cp -a /usr/bin/ffmpeg frontend/node_modules/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux
fi

.venv/bin/python -m pip freeze --exclude-editable > requirements.lock
echo "Bootstrap complete. Subsequent development loops run without network access."
