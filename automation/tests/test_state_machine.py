from __future__ import annotations

from pathlib import Path

import pytest

from automation.diagnostics import CommandResult, FailureCategory, classify_failure, redact
from automation.retry import RetryPolicy
from automation.state import LoopState, LoopStatus, Phase, next_phase


def test_state_machine_allows_only_next_transition() -> None:
    state = LoopState.create()
    state.transition(Phase.PRECHECK)
    assert state.phase == Phase.PRECHECK
    with pytest.raises(ValueError, match="invalid transition"):
        state.transition(Phase.UNIT_TEST)


def test_next_phase_reaches_complete() -> None:
    assert next_phase(Phase.DISCOVER) == Phase.PRECHECK
    assert next_phase(Phase.FINAL_VERIFY) == Phase.COMPLETE
    assert next_phase(Phase.COMPLETE) == Phase.COMPLETE


def test_retry_and_global_limits() -> None:
    policy = RetryPolicy(max_retries_per_state=3, max_global_iterations=30)
    assert not policy.exhausted(2, 29)
    assert policy.exhausted(3, 2)
    assert policy.exhausted(0, 30)
    with pytest.raises(ValueError):
        RetryPolicy(max_retries_per_state=0)


def test_state_persists_atomically_and_can_resume(tmp_path: Path) -> None:
    path = tmp_path / "state/loop_state.json"
    state = LoopState.create()
    state.register_success("repository discovery")
    state.transition(Phase.PRECHECK)
    state.register_external_blocker(
        FailureCategory.EXTERNAL_CREDENTIAL_MISSING.value,
        "OPENAI_API_KEY missing",
    )
    state.write_atomic(path)
    loaded = LoopState.load(path)
    assert loaded.phase == Phase.PRECHECK
    assert loaded.status == LoopStatus.READY_EXCEPT_EXTERNAL_BLOCKER
    assert loaded.resume_state == Phase.PRECHECK.value
    assert list(path.parent.glob("*.tmp")) == []


def test_retry_counter_is_scoped_to_phase() -> None:
    state = LoopState.create(max_retries_per_state=2)
    assert state.register_failure("TEST_FAILURE", "one") == 1
    assert state.can_attempt()
    assert state.register_failure("TEST_FAILURE", "two") == 2
    assert not state.can_attempt()


def test_successful_resumed_phase_clears_external_blocker() -> None:
    state = LoopState.create()
    state.phase = Phase.GENERATE_VOICE
    state.register_external_blocker(
        FailureCategory.EXTERNAL_CREDENTIAL_MISSING.value,
        "OPENAI_API_KEY missing",
    )

    state.register_success("OpenAI scene voice generation")

    assert state.status == LoopStatus.RUNNING
    assert state.blocked_phases == []
    assert state.blockers == []
    assert state.resume_state is None


def test_failure_classification_and_secret_redaction() -> None:
    missing_key = CommandResult(("voice",), 42, "OPENAI_API_KEY missing", "", 0.1)
    assert classify_failure(missing_key) == FailureCategory.EXTERNAL_CREDENTIAL_MISSING
    timeout = CommandResult(("test",), 124, "", "", 3.0, timed_out=True)
    assert classify_failure(timeout) == FailureCategory.TIMEOUT
    assert "sk-secretvalue123" not in redact("token sk-secretvalue123")
