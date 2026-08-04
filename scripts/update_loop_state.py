#!/usr/bin/env python3
"""Atomically update loop routing, usage, and iteration outcome."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _usage(value: Any) -> tuple[int, int]:
    input_tokens = 0
    output_tokens = 0
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"input_tokens", "inputTokens"} and isinstance(item, int):
                input_tokens = max(input_tokens, item)
            elif key in {"output_tokens", "outputTokens"} and isinstance(item, int):
                output_tokens = max(output_tokens, item)
            else:
                child_input, child_output = _usage(item)
                input_tokens = max(input_tokens, child_input)
                output_tokens = max(output_tokens, child_output)
    elif isinstance(value, list):
        for item in value:
            child_input, child_output = _usage(item)
            input_tokens = max(input_tokens, child_input)
            output_tokens = max(output_tokens, child_output)
    return input_tokens, output_tokens


def parse_usage(log_path: Path) -> tuple[int, int]:
    total_input = 0
    total_output = 0
    if not log_path.exists():
        return 0, 0
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        input_tokens, output_tokens = _usage(payload)
        total_input = max(total_input, input_tokens)
        total_output = max(total_output, output_tokens)
    return total_input, total_output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--routing", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    arguments = parser.parse_args()
    state = json.loads(arguments.state.read_text(encoding="utf-8"))
    routing = json.loads(arguments.routing.read_text(encoding="utf-8"))
    model = routing["model"]
    input_tokens, output_tokens = parse_usage(arguments.log)
    usage = state.setdefault("model_usage", {}).setdefault(
        model, {"iterations": 0, "input_tokens": 0, "output_tokens": 0}
    )
    usage["iterations"] += 1
    usage["input_tokens"] += input_tokens
    usage["output_tokens"] += output_tokens
    state["selected_model"] = model
    state["reasoning_effort"] = routing["reasoning_effort"]
    state["routing_reason"] = routing["reason"]
    state["last_iteration_was_review"] = routing.get("review", False)
    state["iteration"] += 1
    if arguments.exit_code == 0:
        state["consecutive_failures"] = 0
        if not routing.get("review", False):
            state["successful_regular_iterations"] += 1
    else:
        state["consecutive_failures"] += 1
        state.setdefault("failed_checks", []).append(
            f"iteration_{state['iteration']}_exit_{arguments.exit_code}"
        )
    state["updated_at"] = datetime.now(UTC).isoformat()
    temporary = arguments.state.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, arguments.state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
