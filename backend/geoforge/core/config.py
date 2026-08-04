from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GEOFORGE_", env_file=PROJECT_ROOT / ".env", extra="ignore"
    )

    environment: str = Field("development", alias="GEOFORGE_ENV")
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'geoforge.db'}"
    data_dir: Path = PROJECT_ROOT / "data"
    artifact_dir: Path = PROJECT_ROOT / "artifacts" / "runs"
    max_upload_mb: int = Field(100, ge=1, le=2048)
    profile_sample_rows: int = Field(100_000, ge=100, le=1_000_000)
    preview_rows: int = Field(100, ge=1, le=1000)
    run_workers: int = Field(2, ge=1, le=8)
    run_timeout_seconds: int = Field(900, ge=10, le=86_400)
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    def ensure_directories(self) -> None:
        for directory in (self.data_dir, self.upload_dir, self.processed_dir, self.artifact_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
