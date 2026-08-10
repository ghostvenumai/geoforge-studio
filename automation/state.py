"""Persistent and strictly validated state for the autonomous build loop."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class Phase(StrEnum):
    DISCOVER = "DISCOVER"
    PRECHECK = "PRECHECK"
    PLAN = "PLAN"
    IMPLEMENT = "IMPLEMENT"
    STATIC_CHECK = "STATIC_CHECK"
    UNIT_TEST = "UNIT_TEST"
    INTEGRATION_TEST = "INTEGRATION_TEST"
    SECURITY_CHECK = "SECURITY_CHECK"
    APPLICATION_QA = "APPLICATION_QA"
    DEMO_PRECHECK = "DEMO_PRECHECK"
    DEMO_RUN = "DEMO_RUN"
    RECORD = "RECORD"
    GENERATE_NARRATION = "GENERATE_NARRATION"
    GENERATE_VOICE = "GENERATE_VOICE"
    GENERATE_SUBTITLES = "GENERATE_SUBTITLES"
    RENDER = "RENDER"
    VIDEO_QA = "VIDEO_QA"
    FINAL_VERIFY = "FINAL_VERIFY"
    COMPLETE = "COMPLETE"


PHASE_ORDER = tuple(Phase)


class LoopStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    READY_EXCEPT_EXTERNAL_BLOCKER = "READY_EXCEPT_EXTERNAL_BLOCKER"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def next_phase(phase: Phase) -> Phase:
    index = PHASE_ORDER.index(phase)
    if index == len(PHASE_ORDER) - 1:
        return Phase.COMPLETE
    return PHASE_ORDER[index + 1]


@dataclass(slots=True)
class LoopState:
    build_id: str
    phase: Phase = Phase.DISCOVER
    status: LoopStatus = LoopStatus.RUNNING
    completed_phases: list[str] = field(default_factory=list)
    blocked_phases: list[str] = field(default_factory=list)
    failed_phases: list[str] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)
    global_iterations: int = 0
    max_global_iterations: int = 30
    max_retries_per_state: int = 3
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    last_error: str | None = None
    last_failure_category: str | None = None
    last_successful_action: str | None = None
    resume_state: str | None = None
    blockers: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls, *, max_global_iterations: int = 30, max_retries_per_state: int = 3
    ) -> LoopState:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return cls(
            build_id=f"geoforge-{stamp}",
            max_global_iterations=max_global_iterations,
            max_retries_per_state=max_retries_per_state,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> LoopState:
        data = dict(payload)
        data["phase"] = Phase(data["phase"])
        data["status"] = LoopStatus(data["status"])
        return cls(**data)

    @classmethod
    def load(cls, path: Path) -> LoopState:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("loop state must be a JSON object")
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def transition(self, target: Phase) -> None:
        expected = next_phase(self.phase)
        if target != expected:
            raise ValueError(f"invalid transition {self.phase} -> {target}; expected {expected}")
        self.phase = target
        self.updated_at = utc_now()

    def register_success(self, action: str) -> None:
        phase_name = self.phase.value
        if phase_name not in self.completed_phases:
            self.completed_phases.append(phase_name)
        if phase_name in self.blocked_phases:
            self.blocked_phases.remove(phase_name)
            if not self.blocked_phases:
                self.blockers.clear()
                self.resume_state = None
                self.status = LoopStatus.RUNNING
        self.last_successful_action = action
        self.last_error = None
        self.last_failure_category = None
        self.retry_counts[phase_name] = 0
        self.updated_at = utc_now()

    def register_failure(self, category: str, message: str) -> int:
        phase_name = self.phase.value
        retries = self.retry_counts.get(phase_name, 0) + 1
        self.retry_counts[phase_name] = retries
        self.failed_phases.append(phase_name)
        self.last_failure_category = category
        self.last_error = message[:2_000]
        self.updated_at = utc_now()
        return retries

    def register_external_blocker(self, category: str, message: str) -> None:
        phase_name = self.phase.value
        if phase_name not in self.blocked_phases:
            self.blocked_phases.append(phase_name)
        if message not in self.blockers:
            self.blockers.append(message)
        self.last_failure_category = category
        self.last_error = message
        self.resume_state = phase_name
        self.status = LoopStatus.READY_EXCEPT_EXTERNAL_BLOCKER
        self.updated_at = utc_now()

    def can_attempt(self) -> bool:
        return (
            self.global_iterations < self.max_global_iterations
            and self.retry_counts.get(self.phase.value, 0) < self.max_retries_per_state
        )

    def write_atomic(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
