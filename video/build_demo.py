"""CLI orchestration for the reproducible GeoForge Studio demo video."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from video.models import Timeline, generate_narration_markdown, generate_srt
from video.precheck import Check, required_checks_pass, run_precheck
from video.qa import detect_audio_peak, probe_video, write_qa_report
from video.rendering import (
    build_audio_command,
    build_render_command,
    execute_ffmpeg,
    load_audio_segments,
)
from video.tts import ExternalCredentialMissing, generate_voice_segments

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMELINE_PATH = PROJECT_ROOT / "video/script/timeline.json"
TMP_DIR = PROJECT_ROOT / "video/tmp"
LOG_DIR = PROJECT_ROOT / "video/logs"
DIST_DIR = PROJECT_ROOT / "dist"
CAPTURE_PATH = TMP_DIR / "capture.webm"
SUBTITLE_PATH = TMP_DIR / "subtitles.srt"
NARRATION_PATH = PROJECT_ROOT / "video/script/narration.md"
AUDIO_DIR = TMP_DIR / "audio"
COMBINED_AUDIO_PATH = TMP_DIR / "narration.wav"
FINAL_VIDEO_PATH = DIST_DIR / "solcom_demo.mp4"
PREVIEW_VIDEO_PATH = DIST_DIR / "solcom_demo_preview.mp4"
QA_REPORT_PATH = DIST_DIR / "video_qa.json"
BUILD_REPORT_PATH = DIST_DIR / "build_report.md"

EXIT_SUCCESS = 0
EXIT_PRECHECK = 30
EXIT_RECORDING = 40
EXIT_EXTERNAL_CREDENTIAL = 42
EXIT_RENDER = 50
EXIT_VIDEO_QA = 60


def _safe_remove(path: Path) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(TMP_DIR.resolve()):
        raise ValueError(f"refusing to remove path outside video/tmp: {path}")
    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink(missing_ok=True)


def prepare_recording_workspace(*, resume: bool) -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    if resume and CAPTURE_PATH.is_file():
        return
    targets = [
        CAPTURE_PATH,
        TMP_DIR / "geoforge-video.db",
        TMP_DIR / "geoforge-video.db-shm",
        TMP_DIR / "geoforge-video.db-wal",
        TMP_DIR / "data",
        TMP_DIR / "runs",
        TMP_DIR / "playwright",
        TMP_DIR / "playwright-results",
    ]
    for target in targets:
        if target.exists():
            _safe_remove(target)
    (TMP_DIR / "data").mkdir(parents=True, exist_ok=True)
    (TMP_DIR / "runs").mkdir(parents=True, exist_ok=True)


def print_checks(checks: tuple[Check, ...]) -> None:
    for check in checks:
        print(f"{check.name:<28} {check.status:<28} {check.detail}")


def precheck() -> bool:
    checks = run_precheck(PROJECT_ROOT)
    print_checks(checks)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    (TMP_DIR / "precheck.json").write_text(
        json.dumps(
            [
                {
                    "name": check.name,
                    "status": check.status,
                    "detail": check.detail,
                    "required": check.required,
                }
                for check in checks
            ],
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return required_checks_pass(checks)


def record(*, resume: bool = False) -> None:
    prepare_recording_workspace(resume=resume)
    if resume and CAPTURE_PATH.is_file() and CAPTURE_PATH.stat().st_size > 100_000:
        print(f"RECORDING: cached {CAPTURE_PATH.relative_to(PROJECT_ROOT)}")
        return
    command = [
        str(PROJECT_ROOT / "frontend/node_modules/node/bin/node"),
        str(PROJECT_ROOT / "frontend/node_modules/@playwright/test/cli.js"),
        "test",
        "--config=video.playwright.config.ts",
    ]
    completed = subprocess.run(  # noqa: S603 - executable is repository-local Playwright
        command,
        cwd=PROJECT_ROOT / "frontend",
        env={
            **os.environ,
            "PLAYWRIGHT_BROWSERS_PATH": str(
                PROJECT_ROOT / "frontend/node_modules/.cache/ms-playwright"
            ),
        },
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / "recording.log").write_text(
        completed.stdout + "\n" + completed.stderr, encoding="utf-8"
    )
    if completed.returncode != 0:
        detail = (completed.stdout + "\n" + completed.stderr)[-5_000:]
        raise RuntimeError(f"Playwright recording failed: {detail}")
    if not CAPTURE_PATH.is_file() or CAPTURE_PATH.stat().st_size < 100_000:
        raise RuntimeError("Playwright completed without a valid capture.webm")
    print(f"RECORDING: PASS ({CAPTURE_PATH.relative_to(PROJECT_ROOT)})")


def generate_narration(timeline: Timeline) -> None:
    NARRATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    NARRATION_PATH.write_text(generate_narration_markdown(timeline), encoding="utf-8")
    print(f"NARRATION: PASS ({NARRATION_PATH.relative_to(PROJECT_ROOT)})")


def generate_subtitles(timeline: Timeline) -> None:
    SUBTITLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUBTITLE_PATH.write_text(generate_srt(timeline), encoding="utf-8")
    print(f"SUBTITLES: PASS ({SUBTITLE_PATH.relative_to(PROJECT_ROOT)})")


def generate_voice(timeline: Timeline) -> None:
    generate_voice_segments(timeline, AUDIO_DIR)
    print(f"VOICEOVER: PASS ({AUDIO_DIR.relative_to(PROJECT_ROOT)})")


def render(timeline: Timeline) -> tuple[Path, bool]:
    if not CAPTURE_PATH.is_file():
        raise RuntimeError("recording is missing; run the record phase first")
    if not SUBTITLE_PATH.is_file():
        raise RuntimeError("subtitles are missing; run the subtitles phase first")
    manifest_path = AUDIO_DIR / "manifest.json"
    has_voice = manifest_path.is_file()
    audio: Path | None = None
    if has_voice:
        segments = load_audio_segments(manifest_path, timeline)
        command = build_audio_command(timeline, segments, COMBINED_AUDIO_PATH)
        execute_ffmpeg(command, cwd=PROJECT_ROOT)
        audio = COMBINED_AUDIO_PATH
    output = FINAL_VIDEO_PATH if has_voice else PREVIEW_VIDEO_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    command = build_render_command(
        CAPTURE_PATH,
        SUBTITLE_PATH,
        output,
        duration=timeline.total_duration,
        audio=audio,
    )
    execute_ffmpeg(command, cwd=PROJECT_ROOT)
    print(f"RENDER: PASS ({output.relative_to(PROJECT_ROOT)})")
    return output, has_voice


def video_qa(path: Path, timeline: Timeline, *, has_voice: bool) -> bool:
    result = probe_video(path, expected_duration=timeline.total_duration)
    peak = detect_audio_peak(path)
    result.metadata["audio_peak_db"] = peak
    if has_voice:
        result.checks["audible_voice"] = peak is not None and peak > -45.0
        result.passed = result.passed and result.checks["audible_voice"]
    else:
        result.warnings.append("Preview contains a silent AAC track because TTS is unavailable.")
    write_qa_report(result, QA_REPORT_PATH)
    status = "PASS" if result.passed else "FAIL"
    print(f"VIDEO QA: {status} ({QA_REPORT_PATH.relative_to(PROJECT_ROOT)})")
    return result.passed


def write_build_report(
    *,
    statuses: dict[str, str],
    final_output: Path | None,
    blocker: str | None,
) -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    final_status = "READY_EXCEPT_EXTERNAL_BLOCKER" if blocker else "COMPLETE"
    rows = "\n".join(f"| {name} | {status} |" for name, status in statuses.items())
    output_text = str(final_output.relative_to(PROJECT_ROOT)) if final_output else "not generated"
    BUILD_REPORT_PATH.write_text(
        "\n".join(
            [
                "# GeoForge Studio - Autonomous Build Report",
                "",
                f"Build date: {datetime.now(UTC).isoformat()}",
                f"Final status: **{final_status}**",
                "",
                "| Phase | Status |",
                "|---|---|",
                rows,
                "",
                f"Final output: `{output_text}`",
                "",
                "## External blocker",
                "",
                blocker or "None.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_all(*, skip_tts: bool, resume: bool) -> int:
    timeline = Timeline.load(TIMELINE_PATH)
    statuses: dict[str, str] = {}
    if not precheck():
        statuses["Precheck"] = "FAIL"
        write_build_report(statuses=statuses, final_output=None, blocker=None)
        return EXIT_PRECHECK
    statuses["Precheck"] = "PASS"
    record(resume=resume)
    statuses["Recording"] = "PASS"
    generate_narration(timeline)
    statuses["Narration"] = "PASS"
    blocker: str | None = None
    if skip_tts:
        blocker = "Voice generation was explicitly skipped; no final narrated video was claimed."
        statuses["AI voice"] = "SKIPPED"
    else:
        try:
            generate_voice(timeline)
            statuses["AI voice"] = "PASS"
        except ExternalCredentialMissing:
            blocker = "OPENAI_API_KEY is missing. No TTS request was sent."
            statuses["AI voice"] = "BLOCKED_EXTERNAL_CREDENTIAL"
    generate_subtitles(timeline)
    statuses["Subtitles"] = "PASS"
    output, has_voice = render(timeline)
    statuses["Render"] = "PASS" if has_voice else "PASS_PREVIEW"
    qa_passed = video_qa(output, timeline, has_voice=has_voice)
    statuses["Video QA"] = "PASS" if qa_passed else "FAIL"
    write_build_report(statuses=statuses, final_output=output, blocker=blocker)
    if not qa_passed:
        return EXIT_VIDEO_QA
    return EXIT_EXTERNAL_CREDENTIAL if blocker else EXIT_SUCCESS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("all", "precheck", "record", "narration", "voice", "subtitles", "render", "qa"),
        nargs="?",
        default="all",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-tts", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    timeline = Timeline.load(TIMELINE_PATH)
    if arguments.dry_run:
        checks = run_precheck(PROJECT_ROOT)
        print_checks(checks)
        print(f"TIMELINE: {len(timeline.scenes)} scenes / {timeline.total_duration:.1f} seconds")
        print("DRY RUN: PASS" if required_checks_pass(checks) else "DRY RUN: BLOCKED")
        return EXIT_SUCCESS if required_checks_pass(checks) else EXIT_PRECHECK
    try:
        if arguments.action == "all":
            return run_all(skip_tts=arguments.skip_tts, resume=arguments.resume)
        if arguments.action == "precheck":
            return EXIT_SUCCESS if precheck() else EXIT_PRECHECK
        if arguments.action == "record":
            record(resume=arguments.resume)
        elif arguments.action == "narration":
            generate_narration(timeline)
        elif arguments.action == "voice":
            generate_voice(timeline)
        elif arguments.action == "subtitles":
            generate_subtitles(timeline)
        elif arguments.action == "render":
            render(timeline)
        elif arguments.action == "qa":
            has_voice = (AUDIO_DIR / "manifest.json").is_file()
            target = FINAL_VIDEO_PATH if has_voice else PREVIEW_VIDEO_PATH
            return (
                EXIT_SUCCESS if video_qa(target, timeline, has_voice=has_voice) else EXIT_VIDEO_QA
            )
        return EXIT_SUCCESS
    except ExternalCredentialMissing as error:
        print(f"VOICEOVER: BLOCKED_EXTERNAL_CREDENTIAL - {error}")
        return EXIT_EXTERNAL_CREDENTIAL
    except RuntimeError as error:
        print(f"VIDEO BUILD FAILED: {error}", file=sys.stderr)
        if arguments.action == "record":
            return EXIT_RECORDING
        return EXIT_RENDER


if __name__ == "__main__":
    raise SystemExit(main())
