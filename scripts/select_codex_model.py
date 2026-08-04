#!/usr/bin/env python3
"""Deterministically route one bounded Codex iteration to a model tier."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LUNA = "gpt-5.6-luna"
TERRA = "gpt-5.6-terra"
SOL = "gpt-5.6-sol"
SIMPLE_TERMS = {"documentation", "format", "fixture", "copy", "changelog"}
COMPLEX_TERMS = {
    "architecture",
    "pipeline",
    "dedup",
    "security",
    "performance",
    "integration",
    "react flow",
    "ui architecture",
}


@dataclass(frozen=True)
class Decision:
    model: str
    reasoning_effort: str
    reason: str
    blocked: bool = False
    review: bool = False


def _contains(task: str, terms: set[str]) -> bool:
    normalized = task.casefold()
    return any(term in normalized for term in terms)


def select_model(state: dict[str, Any], task: str) -> Decision:
    """Apply safety/review, failure escalation, complexity, then default routing."""
    failures = int(state.get("consecutive_failures", 0))
    previous = str(state.get("selected_model", ""))
    successful = int(state.get("successful_regular_iterations", 0))
    task_lower = task.casefold()

    if failures >= 3:
        return Decision(SOL, "xhigh", "Three identical failure signatures; mark task BLOCKED", True)
    if "release review" in task_lower or "security review" in task_lower:
        return Decision(
            SOL, "xhigh", "Security or release review requires maximum scrutiny", review=True
        )
    if failures >= 2:
        return Decision(SOL, "xhigh", "Same task failed at least twice; one xhigh investigation")
    if failures == 1 and previous == LUNA:
        return Decision(TERRA, "medium", "Retry failed low-risk Luna task with Terra")
    if int(state.get("terra_failures_for_task", 0)) >= 2:
        return Decision(SOL, "high", "Two Terra attempts failed; escalate to Sol high")
    if int(state.get("sol_failures_for_task", 0)) >= 1:
        return Decision(
            SOL, "xhigh", "Release-critical or repeated Sol failure; one xhigh investigation"
        )
    if successful > 0 and successful % 5 == 0 and not state.get("last_iteration_was_review", False):
        return Decision(
            SOL, "high", "Scheduled independent architecture and quality review", review=True
        )
    if _contains(task, COMPLEX_TERMS):
        return Decision(
            SOL, "high", "Complex architecture, data, security, performance, or UI task"
        )
    if _contains(task, SIMPLE_TERMS):
        return Decision(LUNA, "low", "Clearly bounded low-risk documentation or fixture task")
    return Decision(TERRA, "medium", "Regular implementation, test, or repair task")


def route(state_path: Path, task: str, output_path: Path | None, log_path: Path | None) -> Decision:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    decision = select_model(state, task)
    payload = {
        **asdict(decision),
        "task": task,
        "iteration": state.get("iteration", 0),
        "selected_at": datetime.now(UTC).isoformat(),
    }
    serialized = json.dumps(payload, sort_keys=True)
    if output_path:
        output_path.write_text(serialized + "\n", encoding="utf-8")
    if log_path:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
    return decision


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path("LOOP_STATE.json"))
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--log", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    chosen = route(arguments.state, arguments.task, arguments.output, arguments.log)
    print(json.dumps(asdict(chosen), sort_keys=True))
