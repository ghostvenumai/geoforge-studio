from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from geoforge.models.common import ORMModel


class DatasetResponse(ORMModel):
    id: str
    name: str
    original_filename: str
    format: str
    checksum: str
    size_bytes: int
    row_count: int
    column_count: int
    schema_data: dict[str, Any] = Field(
        validation_alias="schema_json", serialization_alias="schema"
    )
    preview_json: list[dict[str, Any]]
    encoding: str | None
    delimiter: str | None
    status: str
    duplicate_of_dataset_id: str | None = None
    created_at: datetime


class ProfileResponse(BaseModel):
    dataset_id: str
    profile: dict[str, Any]


class DemoDatasetInfo(BaseModel):
    theme: str
    title: str
    description: str
    filename: str
    recommended_pipeline: str
