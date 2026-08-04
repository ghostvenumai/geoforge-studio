from __future__ import annotations

import pytest
from scripts.select_codex_model import LUNA, SOL, TERRA, select_model


@pytest.mark.parametrize(
    "task", ["Update documentation", "Format release notes", "Create fixtures"]
)
def test_low_risk_tasks_use_luna(task: str) -> None:
    result = select_model({}, task)
    assert (result.model, result.reasoning_effort) == (LUNA, "low")


def test_regular_work_uses_terra() -> None:
    result = select_model({}, "Implement dataset endpoint")
    assert (result.model, result.reasoning_effort) == (TERRA, "medium")


@pytest.mark.parametrize("task", ["Architecture design", "Dedup blocking", "Performance tuning"])
def test_complex_work_uses_sol_high(task: str) -> None:
    result = select_model({}, task)
    assert (result.model, result.reasoning_effort) == (SOL, "high")


def test_luna_failure_retries_with_terra() -> None:
    result = select_model({"consecutive_failures": 1, "selected_model": LUNA}, "Documentation")
    assert result.model == TERRA


def test_two_matching_failures_get_xhigh() -> None:
    result = select_model({"consecutive_failures": 2, "selected_model": TERRA}, "API repair")
    assert (result.model, result.reasoning_effort) == (SOL, "xhigh")


def test_three_matching_failures_are_blocked() -> None:
    result = select_model({"consecutive_failures": 3}, "API repair")
    assert result.blocked is True


@pytest.mark.parametrize("task", ["Security review", "Release review"])
def test_critical_reviews_use_xhigh(task: str) -> None:
    result = select_model({}, task)
    assert (result.model, result.reasoning_effort, result.review) == (SOL, "xhigh", True)


def test_fifth_success_schedules_review() -> None:
    result = select_model({"successful_regular_iterations": 5}, "Implement endpoint")
    assert result.review is True
    assert result.model == SOL
