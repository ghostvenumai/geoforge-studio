"""Bounded state-machine runner for application, demo, and video quality gates."""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import suppress
from pathlib import Path

from automation.diagnostics import FailureCategory, classify_failure, run_command
from automation.gates import command_cwd, gate_for
from automation.reports import terminal_summary, write_build_report
from automation.retry import RetryPolicy
from automation.state import LoopState, LoopStatus, Phase, next_phase

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = PROJECT_ROOT / "automation/state/loop_state.json"
LOG_PATH = PROJECT_ROOT / "automation/logs/master-loop.jsonl"
REPORT_PATH = PROJECT_ROOT / "dist/build_report.md"
LOCK_PATH = PROJECT_ROOT / ".automation-loop.lock"
EXTERNAL_EXIT = 42


def acquire_lock() -> None:
    try:
        LOCK_PATH.mkdir()
    except FileExistsError as error:
        raise RuntimeError("another GeoForge master loop is already running") from error


def release_lock() -> None:
    with suppress(FileNotFoundError):
        LOCK_PATH.rmdir()


def rotate_log() -> None:
    if LOG_PATH.is_file() and LOG_PATH.stat().st_size > 2_000_000:
        rotated = LOG_PATH.with_suffix(".jsonl.1")
        rotated.unlink(missing_ok=True)
        LOG_PATH.replace(rotated)


def final_artifacts_valid(state: LoopState) -> tuple[bool, str]:
    required = [
        PROJECT_ROOT / "video/tmp/capture.webm",
        PROJECT_ROOT / "video/tmp/subtitles.srt",
        PROJECT_ROOT / "video/script/narration.md",
        PROJECT_ROOT / "dist/video_qa.json",
    ]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required if not path.is_file()]
    if missing:
        return False, f"missing final artifacts: {', '.join(missing)}"
    if state.blockers:
        preview = PROJECT_ROOT / "dist/solcom_demo_preview.mp4"
        return (
            preview.is_file(),
            "preview video is missing" if not preview.is_file() else "preview verified",
        )
    final = PROJECT_ROOT / "dist/solcom_demo.mp4"
    return (
        final.is_file(),
        "final narrated video is missing" if not final.is_file() else "final video verified",
    )


def dry_run(policy: RetryPolicy) -> int:
    from video.precheck import required_checks_pass, run_precheck

    checks = run_precheck(PROJECT_ROOT)
    print("MASTER LOOP DRY RUN")
    for check in checks:
        print(f"{check.name:<28} {check.status:<28} {check.detail}")
    print(f"max retries/state: {policy.max_retries_per_state}")
    print(f"max global iterations: {policy.max_global_iterations}")
    print("planned phases:")
    for phase in Phase:
        gate = gate_for(phase)
        print(f"- {phase.value}: {gate.name}")
    return 0 if required_checks_pass(checks) else 30


def load_or_create_state(arguments: argparse.Namespace, policy: RetryPolicy) -> LoopState:
    if arguments.resume and STATE_PATH.is_file():
        state = LoopState.load(STATE_PATH)
        if state.resume_state:
            state.phase = Phase(state.resume_state)
            state.status = LoopStatus.RUNNING
            state.last_error = None
            state.last_failure_category = None
            state.retry_counts[state.phase.value] = 0
        return state
    return LoopState.create(
        max_global_iterations=policy.max_global_iterations,
        max_retries_per_state=policy.max_retries_per_state,
    )


def execute_phase(state: LoopState) -> tuple[bool, FailureCategory | None, str]:
    gate = gate_for(state.phase)
    if state.phase == Phase.FINAL_VERIFY:
        passed, detail = final_artifacts_valid(state)
        return passed, None if passed else FailureCategory.APPLICATION_ERROR, detail
    for command in gate.commands:
        cwd = (PROJECT_ROOT / command_cwd(state.phase)).resolve()
        result = run_command(
            command,
            cwd=cwd,
            timeout=gate.timeout_seconds,
            log_path=LOG_PATH,
        )
        if not result.succeeded:
            detail = (result.stderr or result.stdout or f"exit code {result.returncode}")[-2_000:]
            return False, classify_failure(result), detail
    return True, None, gate.name


def run(arguments: argparse.Namespace) -> int:
    policy = RetryPolicy(arguments.max_retries, arguments.max_iterations)
    if arguments.dry_run:
        return dry_run(policy)
    rotate_log()
    acquire_lock()
    try:
        state = load_or_create_state(arguments, policy)
        while state.phase != Phase.COMPLETE:
            if not state.can_attempt():
                state.status = LoopStatus.FAILED
                state.last_error = "retry or global iteration limit reached"
                break
            state.global_iterations += 1
            state.write_atomic(STATE_PATH)
            passed, category, detail = execute_phase(state)
            if passed:
                state.register_success(gate_for(state.phase).name)
                state.transition(next_phase(state.phase))
                state.write_atomic(STATE_PATH)
                continue
            assert category is not None
            if category == FailureCategory.EXTERNAL_CREDENTIAL_MISSING:
                state.register_external_blocker(category.value, detail)
                state.transition(next_phase(state.phase))
                state.write_atomic(STATE_PATH)
                continue
            retries = state.register_failure(category.value, detail)
            state.write_atomic(STATE_PATH)
            if retries >= state.max_retries_per_state:
                state.status = LoopStatus.FAILED
                break
        if state.phase == Phase.COMPLETE and state.status == LoopStatus.RUNNING:
            state.status = LoopStatus.COMPLETE
        state.write_atomic(STATE_PATH)
        write_build_report(state, REPORT_PATH)
        print(terminal_summary(state))
        if state.status == LoopStatus.COMPLETE:
            return 0
        if state.status == LoopStatus.READY_EXCEPT_EXTERNAL_BLOCKER:
            return EXTERNAL_EXIT
        return 20
    finally:
        release_lock()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-retries", type=int, default=int(os.getenv("LOOP_MAX_RETRIES", "3")))
    parser.add_argument(
        "--max-iterations", type=int, default=int(os.getenv("LOOP_MAX_ITERATIONS", "30"))
    )
    return parser.parse_args()


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args()))
    except (RuntimeError, ValueError) as error:
        print(f"MASTER LOOP ERROR: {error}", file=sys.stderr)
        raise SystemExit(20) from error
