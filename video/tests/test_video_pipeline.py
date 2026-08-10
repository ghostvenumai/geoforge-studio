from __future__ import annotations

import json
from pathlib import Path

import pytest

from video.models import Scene, Timeline, generate_narration_markdown, generate_srt
from video.precheck import run_precheck
from video.qa import analyze_probe
from video.rendering import build_audio_command, build_render_command
from video.tts import (
    ExternalCredentialMissing,
    OpenAITTSProvider,
    TTSConfig,
    generate_voice_segments,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def synthesize(self, scene: Scene, output: Path) -> None:
        self.calls += 1
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"RIFF" + b"\x00" * 64)


def test_real_timeline_is_valid_and_in_target_duration() -> None:
    timeline = Timeline.load(PROJECT_ROOT / "video/script/timeline.json")
    assert timeline.language == "de"
    assert (timeline.width, timeline.height, timeline.fps) == (1920, 1080, 30)
    assert 135 <= timeline.total_duration <= 165
    assert len(timeline.scenes) == 11


def test_recording_uses_compatible_project_local_node_runtime() -> None:
    checks = {check.name: check for check in run_precheck(PROJECT_ROOT)}
    assert checks["recording-node"].status == "PASS"
    assert checks["recording-node"].detail.startswith("v22.")
    assert checks["playwright-video-codec"].status == "PASS"


def test_timeline_rejects_duplicate_ids(tmp_path: Path) -> None:
    scene = {
        "id": "same",
        "order": 1,
        "action": "show",
        "route": "/",
        "planned_duration": 60,
        "narration": "Text",
        "overlay": "OVERLAY",
    }
    second = {**scene, "order": 2, "planned_duration": 61}
    path = tmp_path / "timeline.json"
    path.write_text(
        json.dumps(
            {
                "title": "Demo",
                "language": "de",
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "scenes": [scene, second],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unique"):
        Timeline.load(path)


def test_narration_and_subtitles_share_timeline() -> None:
    timeline = Timeline.load(PROJECT_ROOT / "video/script/timeline.json")
    narration = generate_narration_markdown(timeline)
    subtitles = generate_srt(timeline)
    assert timeline.scenes[0].narration in narration
    assert "00:00:00,400 --> 00:00:05,700" in subtitles
    assert subtitles.count(" --> ") == len(timeline.scenes)
    starts = [start for _, start, _ in timeline.timings()]
    ends = [end for _, _, end in timeline.timings()]
    assert all(
        current_end <= next_start for current_end, next_start in zip(ends, starts[1:], strict=False)
    )


def test_openai_provider_stops_before_network_without_key(tmp_path: Path) -> None:
    timeline = Timeline.load(PROJECT_ROOT / "video/script/timeline.json")
    provider = OpenAITTSProvider(TTSConfig(), api_key="")
    with pytest.raises(ExternalCredentialMissing, match="no TTS request"):
        provider.synthesize(timeline.scenes[0], tmp_path / "audio.wav")


def test_scene_audio_generation_is_cached(tmp_path: Path) -> None:
    timeline = Timeline.load(PROJECT_ROOT / "video/script/timeline.json")
    fake = FakeProvider()
    config = TTSConfig()
    first = generate_voice_segments(timeline, tmp_path / "audio", config=config, provider=fake)
    assert fake.calls == len(timeline.scenes)
    second = generate_voice_segments(timeline, tmp_path / "audio", config=config, provider=fake)
    assert fake.calls == len(timeline.scenes)
    assert first == second


def test_ffmpeg_commands_are_bounded_and_do_not_use_shell(tmp_path: Path) -> None:
    timeline = Timeline.load(PROJECT_ROOT / "video/script/timeline.json")
    segments = tuple(tmp_path / f"{index}.wav" for index in range(len(timeline.scenes)))
    audio_command = build_audio_command(timeline, segments, tmp_path / "combined.wav")
    assert audio_command[0] == "ffmpeg"
    assert "concat=n=11:v=0:a=1" in audio_command[audio_command.index("-filter_complex") + 1]
    render_command = build_render_command(
        tmp_path / "capture.webm",
        tmp_path / "subtitles.srt",
        tmp_path / "video.mp4",
        duration=timeline.total_duration,
        audio=None,
    )
    assert "libx264" in render_command
    assert "1920:1080" in render_command[render_command.index("-vf") + 1]
    assert "anullsrc=r=48000:cl=stereo" in render_command


def test_video_qa_accepts_expected_probe_payload() -> None:
    payload = {
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "30/1",
            },
            {"codec_type": "audio"},
        ],
        "format": {"duration": "147.0"},
    }
    result = analyze_probe(payload, expected_duration=147.0, file_size=2_000_000)
    assert result.passed
    assert all(result.checks.values())
