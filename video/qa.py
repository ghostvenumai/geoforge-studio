"""Technical validation for rendered 1080p MP4 artifacts."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class VideoQAResult:
    passed: bool
    checks: dict[str, bool]
    metadata: dict[str, object]
    warnings: list[str] = field(default_factory=list)


def _frame_rate(value: str) -> float:
    numerator, separator, denominator = value.partition("/")
    if not separator:
        return float(value)
    return float(numerator) / float(denominator)


def analyze_probe(
    payload: dict[str, Any],
    *,
    expected_duration: float,
    file_size: int,
) -> VideoQAResult:
    streams = payload.get("streams", [])
    if not isinstance(streams, list):
        streams = []
    video_stream = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "video"
        ),
        None,
    )
    audio_stream = next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == "audio"
        ),
        None,
    )
    format_payload = payload.get("format", {})
    duration = float(format_payload.get("duration", 0)) if isinstance(format_payload, dict) else 0.0
    fps = 0.0
    if isinstance(video_stream, dict):
        try:
            fps = _frame_rate(str(video_stream.get("avg_frame_rate", "0")))
        except (ValueError, ZeroDivisionError):
            fps = 0.0
    checks = {
        "file_size": file_size > 500_000,
        "video_stream": video_stream is not None,
        "audio_stream": audio_stream is not None,
        "width": isinstance(video_stream, dict) and video_stream.get("width") == 1920,
        "height": isinstance(video_stream, dict) and video_stream.get("height") == 1080,
        "fps": abs(fps - 30.0) <= 0.1,
        "duration": abs(duration - expected_duration) <= 3.0,
        "nonzero_duration": duration > 0,
    }
    return VideoQAResult(
        passed=all(checks.values()),
        checks=checks,
        metadata={"duration": duration, "fps": fps, "file_size": file_size},
    )


def probe_video(path: Path, *, expected_duration: float, ffprobe: str = "ffprobe") -> VideoQAResult:
    if not path.is_file():
        return VideoQAResult(False, {"file_exists": False}, {"path": str(path)})
    completed = subprocess.run(  # noqa: S603 - ffprobe binary is preflight-validated
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        return VideoQAResult(
            False,
            {"file_exists": True, "decodable": False},
            {"ffprobe_error": completed.stderr[-2_000:]},
        )
    payload: object = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("ffprobe output must be a JSON object")
    return analyze_probe(
        payload, expected_duration=expected_duration, file_size=path.stat().st_size
    )


def detect_audio_peak(path: Path, *, ffmpeg: str = "ffmpeg") -> float | None:
    completed = subprocess.run(  # noqa: S603 - ffmpeg binary is preflight-validated
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    match = re.search(r"max_volume:\s*(-?(?:inf|\d+(?:\.\d+)?)) dB", completed.stderr)
    if not match or match.group(1) == "-inf":
        return None
    return float(match.group(1))


def write_qa_report(result: VideoQAResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "passed": result.passed,
                "checks": result.checks,
                "metadata": result.metadata,
                "warnings": result.warnings,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
