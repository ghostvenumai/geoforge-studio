"""Retry policy primitives shared by loop phases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries_per_state: int = 3
    max_global_iterations: int = 30

    def __post_init__(self) -> None:
        if self.max_retries_per_state < 1:
            raise ValueError("max_retries_per_state must be at least one")
        if self.max_global_iterations < 1:
            raise ValueError("max_global_iterations must be at least one")

    def exhausted(self, state_retries: int, global_iterations: int) -> bool:
        return (
            state_retries >= self.max_retries_per_state
            or global_iterations >= self.max_global_iterations
        )
