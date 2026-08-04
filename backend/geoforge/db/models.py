from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from geoforge.db.base import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    original_filename: Mapped[str] = mapped_column(String(256))
    stored_path: Mapped[str] = mapped_column(Text, unique=True)
    format: Mapped[str] = mapped_column(String(16))
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    schema_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    preview_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    profile_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    encoding: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delimiter: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="ready")
    duplicate_of_dataset_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    runs: Mapped[list[Run]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    yaml_text: Mapped[str] = mapped_column(Text)
    definition_json: Mapped[dict[str, object]] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )

    runs: Mapped[list[Run]] = relationship(back_populates="pipeline")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    pipeline_id: Mapped[str] = mapped_column(ForeignKey("pipelines.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_rows: Mapped[int] = mapped_column(Integer, default=0)
    output_rows: Mapped[int] = mapped_column(Integer, default=0)
    quarantine_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    dataset: Mapped[Dataset] = relationship(back_populates="runs")
    pipeline: Mapped[Pipeline] = relationship(back_populates="runs")
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(256))
    stored_path: Mapped[str] = mapped_column(Text, unique=True)
    checksum: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    run: Mapped[Run] = relationship(back_populates="artifacts")


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    duplicate_group_id: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(String(16))
    canonical_record_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
