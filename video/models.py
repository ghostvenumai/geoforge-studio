"""Validated timeline model and deterministic narration/subtitle generation."""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Scene:
    id: str
    order: int
    action: str
    route: str
    planned_duration: float
    narration: str
    overlay: str
    pause_before: float = 0.0
    pause_after: float = 0.0

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Scene:
        required = {"id", "order", "action", "route", "planned_duration", "narration", "overlay"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"scene is missing fields: {', '.join(sorted(missing))}")
        scene = cls(
            id=str(payload["id"]),
            order=int(payload["order"]),
            action=str(payload["action"]),
            route=str(payload["route"]),
            planned_duration=float(payload["planned_duration"]),
            narration=str(payload["narration"]),
            overlay=str(payload["overlay"]),
            pause_before=float(payload.get("pause_before", 0.0)),
            pause_after=float(payload.get("pause_after", 0.0)),
        )
        if not scene.id or not scene.action or not scene.narration or not scene.overlay:
            raise ValueError("scene text fields must not be empty")
        if scene.order < 1 or scene.planned_duration <= 0:
            raise ValueError("scene order and duration must be positive")
        if scene.pause_before < 0 or scene.pause_after < 0:
            raise ValueError("scene pauses must not be negative")
        return scene


@dataclass(frozen=True, slots=True)
class Timeline:
    title: str
    language: str
    width: int
    height: int
    fps: int
    scenes: tuple[Scene, ...]

    @classmethod
    def load(cls, path: Path) -> Timeline:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("timeline must be a JSON object")
        raw_scenes = payload.get("scenes")
        if not isinstance(raw_scenes, list) or not raw_scenes:
            raise ValueError("timeline scenes must be a non-empty list")
        scenes = tuple(
            Scene.from_dict(item) if isinstance(item, dict) else _invalid_scene()
            for item in raw_scenes
        )
        timeline = cls(
            title=str(payload.get("title", "")),
            language=str(payload.get("language", "")),
            width=int(payload.get("width", 0)),
            height=int(payload.get("height", 0)),
            fps=int(payload.get("fps", 0)),
            scenes=tuple(sorted(scenes, key=lambda scene: scene.order)),
        )
        timeline.validate()
        return timeline

    @property
    def total_duration(self) -> float:
        return sum(
            scene.pause_before + scene.planned_duration + scene.pause_after for scene in self.scenes
        )

    def validate(self) -> None:
        if not self.title or self.language not in {"de", "en"}:
            raise ValueError("timeline title and supported language are required")
        if (self.width, self.height, self.fps) != (1920, 1080, 30):
            raise ValueError("final timeline must be 1920x1080 at 30 FPS")
        ids = [scene.id for scene in self.scenes]
        orders = [scene.order for scene in self.scenes]
        if len(ids) != len(set(ids)):
            raise ValueError("scene ids must be unique")
        if orders != list(range(1, len(self.scenes) + 1)):
            raise ValueError("scene order must be contiguous and start at one")
        if not 120 <= self.total_duration <= 180:
            raise ValueError("timeline duration must be between two and three minutes")

    def timings(self) -> tuple[tuple[Scene, float, float], ...]:
        cursor = 0.0
        output: list[tuple[Scene, float, float]] = []
        for scene in self.scenes:
            cursor += scene.pause_before
            start = cursor
            end = start + scene.planned_duration
            output.append((scene, start, end))
            cursor = end + scene.pause_after
        return tuple(output)


def _invalid_scene() -> Scene:
    raise ValueError("each timeline scene must be a JSON object")


def format_srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1_000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d},{milliseconds:03d}"


def wrap_subtitle(text: str, width: int = 48) -> str:
    lines = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
    if len(lines) <= 2:
        return "\n".join(lines)
    midpoint = len(text) // 2
    split = text.rfind(" ", 0, midpoint)
    if split < 1:
        split = text.find(" ", midpoint)
    if split < 1:
        return text
    return f"{text[:split].strip()}\n{text[split:].strip()}"


def generate_srt(timeline: Timeline) -> str:
    blocks: list[str] = []
    for index, (scene, start, end) in enumerate(timeline.timings(), start=1):
        subtitle_start = start + min(0.4, scene.planned_duration / 10)
        subtitle_end = max(subtitle_start + 1.0, end - 0.3)
        blocks.append(
            f"{index}\n{format_srt_timestamp(subtitle_start)} --> "
            f"{format_srt_timestamp(subtitle_end)}\n{wrap_subtitle(scene.narration)}"
        )
    return "\n\n".join(blocks) + "\n"


def generate_narration_markdown(timeline: Timeline) -> str:
    lines = [f"# {timeline.title} - Sprechertext", "", f"Sprache: `{timeline.language}`", ""]
    for scene in timeline.scenes:
        lines.extend(
            [
                f"## {scene.order:02d} · {scene.overlay}",
                "",
                scene.narration,
                "",
                f"Geplante Szenendauer: {scene.planned_duration:.1f} Sekunden.",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
