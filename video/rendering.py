"""Maintainable FFmpeg command construction for audio and final video."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from video.models import Timeline


def load_audio_segments(manifest_path: Path, timeline: Timeline) -> tuple[Path, ...]:
    payload: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("audio manifest must be a JSON object")
    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, dict):
        raise ValueError("audio manifest has no segments")
    output: list[Path] = []
    for scene in timeline.scenes:
        entry: Any = raw_segments.get(scene.id)
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError(f"audio segment missing for {scene.id}")
        path = Path(entry["path"])
        if not path.is_file() or path.stat().st_size < 44:
            raise ValueError(f"audio segment is invalid for {scene.id}")
        output.append(path)
    return tuple(output)


def build_audio_command(
    timeline: Timeline,
    segments: tuple[Path, ...],
    output: Path,
    *,
    ffmpeg: str = "ffmpeg",
) -> tuple[str, ...]:
    if len(segments) != len(timeline.scenes):
        raise ValueError("one audio segment is required per scene")
    command: list[str] = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y"]
    for segment in segments:
        command.extend(["-i", str(segment)])
    filters: list[str] = []
    labels: list[str] = []
    for index, scene in enumerate(timeline.scenes):
        label = f"a{index}"
        filters.append(
            f"[{index}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"apad,atrim=duration={scene.planned_duration:.3f}[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[aout]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )
    return tuple(command)


def _subtitle_filter(path: Path) -> str:
    escaped = str(path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    style = (
        "FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101826,BorderStyle=1,Outline=2,Shadow=0,"
        "Alignment=2,MarginV=42"
    )
    return f"subtitles='{escaped}':force_style='{style}'"


def build_render_command(
    capture: Path,
    subtitles: Path,
    output: Path,
    *,
    duration: float,
    audio: Path | None,
    ffmpeg: str = "ffmpeg",
) -> tuple[str, ...]:
    command: list[str] = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(capture),
    ]
    if audio is None:
        command.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
    else:
        command.extend(["-i", str(audio)])
    video_filter = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=#0f172a,"
        f"fps=30,{_subtitle_filter(subtitles)}"
    )
    command.extend(
        [
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return tuple(command)


def execute_ffmpeg(command: tuple[str, ...], *, cwd: Path, timeout: int = 900) -> None:
    completed = subprocess.run(  # noqa: S603 - command is built by typed functions above
        list(command), cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout)[-4_000:]
        raise RuntimeError(f"FFmpeg failed with exit code {completed.returncode}: {detail}")
