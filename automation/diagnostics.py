"""Safe command execution, structured logs, and failure classification."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class FailureCategory(StrEnum):
    APPLICATION_ERROR = "APPLICATION_ERROR"
    TEST_FAILURE = "TEST_FAILURE"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    DISPLAY_UNAVAILABLE = "DISPLAY_UNAVAILABLE"
    RECORDING_FAILURE = "RECORDING_FAILURE"
    TTS_FAILURE = "TTS_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    RENDER_FAILURE = "RENDER_FAILURE"
    VIDEO_QA_FAILURE = "VIDEO_QA_FAILURE"
    EXTERNAL_CREDENTIAL_MISSING = "EXTERNAL_CREDENTIAL_MISSING"
    SECURITY_BLOCK = "SECURITY_BLOCK"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0 and not self.timed_out


_ENV_SECRET_PATTERN = re.compile(r"(?i)(OPENAI_API_KEY\s*[=:]\s*)\S+")
_TOKEN_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b")


def redact(text: str) -> str:
    clean = _ENV_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}[REDACTED]", text)
    return _TOKEN_PATTERN.sub("[REDACTED]", clean)


def classify_failure(result: CommandResult) -> FailureCategory:
    combined = f"{result.stdout}\n{result.stderr}".lower()
    if result.timed_out:
        return FailureCategory.TIMEOUT
    if result.returncode == 42 or ("openai_api_key" in combined and "missing" in combined):
        return FailureCategory.EXTERNAL_CREDENTIAL_MISSING
    if "no such file or directory" in combined or "command not found" in combined:
        return FailureCategory.DEPENDENCY_MISSING
    if "could not resolve" in combined or "network is unreachable" in combined:
        return FailureCategory.NETWORK_FAILURE
    if "bandit" in combined or "security" in combined:
        return FailureCategory.SECURITY_BLOCK
    if "ffmpeg" in combined or "render" in combined:
        return FailureCategory.RENDER_FAILURE
    if "video qa" in combined or "ffprobe" in combined:
        return FailureCategory.VIDEO_QA_FAILURE
    if "pytest" in combined or "test" in combined or "assert" in combined:
        return FailureCategory.TEST_FAILURE
    return FailureCategory.APPLICATION_ERROR


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    log_path: Path,
    environment: dict[str, str] | None = None,
) -> CommandResult:
    started = datetime.now(UTC)
    process_environment = os.environ.copy()
    if environment:
        process_environment.update(environment)
    try:
        completed = subprocess.run(  # noqa: S603 - commands come from the fixed gate registry
            list(command),
            cwd=cwd,
            env=process_environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        timed_out = False
        returncode = completed.returncode
        stdout = redact(completed.stdout)
        stderr = redact(completed.stderr)
    except subprocess.TimeoutExpired as error:
        timed_out = True
        returncode = 124
        stdout = redact(str(error.stdout or ""))
        stderr = redact(str(error.stderr or ""))
    duration = (datetime.now(UTC) - started).total_seconds()
    result = CommandResult(tuple(command), returncode, stdout, stderr, duration, timed_out)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "command": list(command),
        "returncode": returncode,
        "duration_seconds": duration,
        "timed_out": timed_out,
        "stdout": stdout[-20_000:],
        "stderr": stderr[-20_000:],
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return result
