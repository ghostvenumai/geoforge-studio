"""Phase-to-command mapping for the bounded master loop."""

from __future__ import annotations

from dataclasses import dataclass

from automation.state import Phase


@dataclass(frozen=True, slots=True)
class Gate:
    name: str
    commands: tuple[tuple[str, ...], ...]
    timeout_seconds: int


def gate_for(phase: Phase) -> Gate:
    gates = {
        Phase.DISCOVER: Gate(
            "Repository discovery", ((".venv/bin/python", "main.py", "doctor"),), 60
        ),
        Phase.PRECHECK: Gate("Repository precheck", (("scripts/preflight.sh",),), 120),
        Phase.PLAN: Gate("Validated execution plan", (), 1),
        Phase.IMPLEMENT: Gate(
            "Themed deterministic demo data",
            ((".venv/bin/pytest", "scripts/test_generate_themed_demo_data.py", "-q"),),
            120,
        ),
        Phase.STATIC_CHECK: Gate(
            "Static checks",
            (
                (
                    ".venv/bin/ruff",
                    "check",
                    "backend",
                    "scripts",
                    "benchmarks",
                    "tests",
                    "automation",
                    "video",
                ),
                (
                    ".venv/bin/ruff",
                    "format",
                    "--check",
                    "backend",
                    "scripts",
                    "benchmarks",
                    "tests",
                    "automation",
                    "video",
                ),
                (
                    ".venv/bin/mypy",
                    "backend/geoforge",
                    "scripts",
                    "benchmarks",
                    "automation",
                    "video",
                ),
            ),
            240,
        ),
        Phase.UNIT_TEST: Gate(
            "Unit tests",
            (
                (
                    ".venv/bin/pytest",
                    "backend/tests/unit",
                    "tests",
                    "automation/tests",
                    "video/tests",
                    "scripts/test_generate_demo_data.py",
                    "scripts/test_generate_themed_demo_data.py",
                    "-q",
                ),
            ),
            240,
        ),
        Phase.INTEGRATION_TEST: Gate(
            "API integration tests",
            ((".venv/bin/pytest", "backend/tests/integration", "-q"),),
            300,
        ),
        Phase.SECURITY_CHECK: Gate(
            "Security checks",
            (
                (
                    ".venv/bin/bandit",
                    "-r",
                    "backend/geoforge",
                    "scripts",
                    "automation",
                    "video",
                    "-lll",
                    "-q",
                ),
            ),
            180,
        ),
        Phase.APPLICATION_QA: Gate(
            "Frontend quality and build",
            (
                ("npm", "run", "lint"),
                ("npm", "run", "typecheck"),
                ("npm", "test"),
                ("npm", "run", "build"),
            ),
            300,
        ),
        Phase.DEMO_PRECHECK: Gate(
            "Demo/video precheck",
            ((".venv/bin/python", "-m", "video.build_demo", "precheck"),),
            120,
        ),
        Phase.DEMO_RUN: Gate(
            "Application demo smoke test", (("scripts/run_demo_smoke_test.sh",),), 300
        ),
        Phase.RECORD: Gate(
            "Deterministic Playwright recording",
            ((".venv/bin/python", "-m", "video.build_demo", "record", "--resume"),),
            420,
        ),
        Phase.GENERATE_NARRATION: Gate(
            "Narration generation",
            ((".venv/bin/python", "-m", "video.build_demo", "narration"),),
            60,
        ),
        Phase.GENERATE_VOICE: Gate(
            "OpenAI scene voice generation",
            ((".venv/bin/python", "-m", "video.build_demo", "voice"),),
            1_200,
        ),
        Phase.GENERATE_SUBTITLES: Gate(
            "Subtitle generation",
            ((".venv/bin/python", "-m", "video.build_demo", "subtitles"),),
            60,
        ),
        Phase.RENDER: Gate(
            "FFmpeg render", ((".venv/bin/python", "-m", "video.build_demo", "render"),), 1_200
        ),
        Phase.VIDEO_QA: Gate(
            "FFprobe video QA", ((".venv/bin/python", "-m", "video.build_demo", "qa"),), 180
        ),
        Phase.FINAL_VERIFY: Gate("Final artifact verification", (), 1),
        Phase.COMPLETE: Gate("Complete", (), 1),
    }
    return gates[phase]


def command_cwd(phase: Phase) -> str:
    return "frontend" if phase == Phase.APPLICATION_QA else "."
