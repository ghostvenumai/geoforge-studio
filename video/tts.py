"""Scene-based, cacheable TTS with an explicit external-credential boundary."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from video.models import Scene, Timeline


class ExternalCredentialMissing(RuntimeError):
    """Raised before network access when the configured provider has no credential."""


class TTSProvider(Protocol):
    def synthesize(self, scene: Scene, output: Path) -> None: ...


@dataclass(frozen=True, slots=True)
class TTSConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini-tts"
    voice: str = "coral"
    response_format: str = "wav"
    language: str = "de"
    endpoint: str = "https://api.openai.com/v1/audio/speech"
    instructions: str = (
        "Sprich professionell, ruhig, souverän und technisch präzise. "
        "Verwende natürliches Hochdeutsch und eine gut verständliche Geschwindigkeit."
    )

    @classmethod
    def from_environment(cls) -> TTSConfig:
        return cls(
            provider=os.getenv("VIDEO_TTS_PROVIDER", "openai"),
            model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            voice=os.getenv("OPENAI_TTS_VOICE", "coral"),
            language=os.getenv("VIDEO_LANGUAGE", "de"),
        )


class OpenAITTSProvider:
    def __init__(self, config: TTSConfig, api_key: str | None = None) -> None:
        self.config = config
        self._api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")

    def synthesize(self, scene: Scene, output: Path) -> None:
        if not self._api_key:
            raise ExternalCredentialMissing("OPENAI_API_KEY is missing; no TTS request was sent")
        endpoint = urllib.parse.urlparse(self.config.endpoint)
        if endpoint.scheme != "https" or not endpoint.hostname:
            raise ValueError("TTS endpoint must use HTTPS")
        body = json.dumps(
            {
                "model": self.config.model,
                "voice": self.config.voice,
                "input": scene.narration,
                "instructions": self.config.instructions,
                "response_format": self.config.response_format,
            }
        ).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310 - HTTPS scheme validated above
            self.config.endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
                audio = response.read()
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"OpenAI TTS failed with HTTP {error.code}") from error
        except urllib.error.URLError as error:
            raise RuntimeError("OpenAI TTS network request failed") from error
        if len(audio) < 44:
            raise RuntimeError("OpenAI TTS returned an invalid or empty audio response")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(audio)


def scene_hash(scene: Scene, config: TTSConfig) -> str:
    payload = json.dumps(
        {"scene": asdict(scene), "config": asdict(config)},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def generate_voice_segments(
    timeline: Timeline,
    output_dir: Path,
    *,
    config: TTSConfig | None = None,
    provider: TTSProvider | None = None,
) -> dict[str, object]:
    selected_config = config or TTSConfig.from_environment()
    if selected_config.language != timeline.language:
        raise ValueError("TTS language must match timeline language")
    selected_provider = provider or OpenAITTSProvider(selected_config)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    existing: dict[str, object] = {}
    if manifest_path.exists():
        loaded: object = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            existing = loaded
    existing_segments = existing.get("segments", {})
    cached = existing_segments if isinstance(existing_segments, dict) else {}
    segments: dict[str, dict[str, object]] = {}
    for scene in timeline.scenes:
        digest = scene_hash(scene, selected_config)
        output = output_dir / f"{scene.order:03d}_{scene.id}.wav"
        cached_scene = cached.get(scene.id)
        cache_matches = (
            isinstance(cached_scene, dict)
            and cached_scene.get("sha256") == digest
            and output.is_file()
            and output.stat().st_size >= 44
        )
        if not cache_matches:
            selected_provider.synthesize(scene, output)
        segments[scene.id] = {
            "path": str(output),
            "sha256": digest,
            "duration_seconds": scene.planned_duration,
        }
    manifest: dict[str, object] = {
        "provider": selected_config.provider,
        "model": selected_config.model,
        "voice": selected_config.voice,
        "language": selected_config.language,
        "segments": segments,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest
