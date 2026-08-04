#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_DIR="$PROJECT_ROOT/.codex-loop.lock"
RUNTIME_DIR="$PROJECT_ROOT/artifacts/codex-loop"
mkdir -p "$RUNTIME_DIR"
cd "$PROJECT_ROOT"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Another Codex loop is active." >&2
  exit 40
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT INT TERM
scripts/preflight.sh

TASK="$(.venv/bin/python -c 'import json; print(json.load(open("LOOP_STATE.json", encoding="utf-8"))["current_task"])')"
ROUTING_FILE="$RUNTIME_DIR/routing.json"
ROUTING_LOG="$RUNTIME_DIR/model-routing.jsonl"
.venv/bin/python scripts/select_codex_model.py --state LOOP_STATE.json --task "$TASK" --output "$ROUTING_FILE" --log "$ROUTING_LOG" >/dev/null

MODEL="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["model"])' "$ROUTING_FILE")"
EFFORT="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["reasoning_effort"])' "$ROUTING_FILE")"
BLOCKED="$(.venv/bin/python -c 'import json,sys; print(str(json.load(open(sys.argv[1], encoding="utf-8"))["blocked"]).lower())' "$ROUTING_FILE")"
[[ "$BLOCKED" != "true" ]] || { echo "Task is blocked after three identical failure signatures." >&2; exit 41; }

ITERATION="$(.venv/bin/python -c 'import json; print(json.load(open("LOOP_STATE.json", encoding="utf-8"))["iteration"])')"
OUTPUT_LOG="$RUNTIME_DIR/iteration-$ITERATION.jsonl"
set +e
timeout --signal=TERM 3600 codex exec \
  --cd "$PROJECT_ROOT" \
  --sandbox workspace-write \
  --ask-for-approval never \
  --model "$MODEL" \
  -c sandbox_workspace_write.network_access=false \
  -c "model_reasoning_effort=\"$EFFORT\"" \
  --json \
  "$(cat prompts/iteration.md)" >"$OUTPUT_LOG" 2>&1
EXIT_CODE=$?
set -e

.venv/bin/python scripts/update_loop_state.py --state LOOP_STATE.json --routing "$ROUTING_FILE" --log "$OUTPUT_LOG" --exit-code "$EXIT_CODE"
exit "$EXIT_CODE"
