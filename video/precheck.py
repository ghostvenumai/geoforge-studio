"""Read-only preflight checks for deterministic recording and rendering."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from video.models import Timeline


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    status: str
    detail: str
    required: bool = True


def run_precheck(project_root: Path) -> tuple[Check, ...]:
    timeline_path = project_root / "video/script/timeline.json"
    checks: list[Check] = []
    for binary in ("ffmpeg", "ffprobe", "google-chrome"):
        location = shutil.which(binary)
        checks.append(Check(binary, "PASS" if location else "BLOCKED", location or "not found"))
    checks.extend(
        [
            Check(
                "python-venv",
                "PASS" if (project_root / ".venv/bin/python").is_file() else "BLOCKED",
                ".venv/bin/python",
            ),
            Check(
                "frontend-dependencies",
                "PASS"
                if (project_root / "frontend/node_modules/.bin/playwright").is_file()
                else "BLOCKED",
                "frontend/node_modules",
            ),
            _recording_node_check(project_root),
            Check(
                "playwright-video-codec",
                "PASS"
                if (
                    project_root
                    / "frontend/node_modules/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux"
                ).is_file()
                else "BLOCKED",
                "frontend/node_modules/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux",
            ),
            Check(
                "marketing-demo-data",
                "PASS"
                if (project_root / "data/samples/geoforge-demo-marketing.csv").is_file()
                else "BLOCKED",
                "data/samples/geoforge-demo-marketing.csv",
            ),
        ]
    )
    try:
        timeline = Timeline.load(timeline_path)
        checks.append(
            Check(
                "timeline",
                "PASS",
                f"{len(timeline.scenes)} scenes, {timeline.total_duration:.1f} seconds",
            )
        )
    except (OSError, ValueError) as error:
        checks.append(Check("timeline", "BLOCKED", str(error)))
    checks.append(
        Check(
            "openai-tts-credential",
            "PASS" if os.getenv("OPENAI_API_KEY") else "BLOCKED_EXTERNAL_CREDENTIAL",
            "configured" if os.getenv("OPENAI_API_KEY") else "OPENAI_API_KEY missing",
            required=False,
        )
    )
    return tuple(checks)


def _recording_node_check(project_root: Path) -> Check:
    executable = project_root / "frontend/node_modules/node/bin/node"
    if not executable.is_file():
        return Check("recording-node", "BLOCKED", "project-local Node.js is missing")
    completed = subprocess.run(  # noqa: S603 - fixed project-local executable
        [str(executable), "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    version = completed.stdout.strip()
    try:
        major = int(version.removeprefix("v").partition(".")[0])
    except ValueError:
        major = 0
    return Check(
        "recording-node",
        "PASS" if completed.returncode == 0 and major >= 20 else "BLOCKED",
        version or completed.stderr.strip() or "unknown version",
    )


def required_checks_pass(checks: tuple[Check, ...]) -> bool:
    return all(check.status == "PASS" for check in checks if check.required)
