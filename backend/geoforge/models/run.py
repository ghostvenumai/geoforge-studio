from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from geoforge.models.common import ORMModel


class PipelineCreateRequest(BaseModel):
    yaml_text: str = Field(min_length=1, max_length=1_000_000)


class PipelineValidateRequest(BaseModel):
    yaml_text: str = Field(min_length=1, max_length=1_000_000)


class PipelineValidateResponse(BaseModel):
    valid: bool
    checksum: str
    definition: dict[str, Any]
    warnings: list[str] = []


class PipelineResponse(ORMModel):
    id: str
    name: str
    description: str
    version: int
    yaml_text: str
    definition_json: dict[str, Any]
    checksum: str
    created_at: datetime
    updated_at: datetime


class RunCreateRequest(BaseModel):
    dataset_id: str


class RunResponse(ORMModel):
    id: str
    dataset_id: str
    pipeline_id: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    input_rows: int
    output_rows: int
    quarantine_rows: int
    duplicate_count: int
    quality_before: float | None
    quality_after: float | None
    error_count: int
    warning_count: int
    cancel_requested: bool
    metrics_json: dict[str, Any]
    error_message: str | None
    created_at: datetime


class ArtifactResponse(ORMModel):
    id: str
    run_id: str
    kind: str
    name: str
    checksum: str
    size_bytes: int
    media_type: str
    created_at: datetime


class DuplicateDecisionRequest(BaseModel):
    duplicate_group_id: str
    decision: Literal["accepted", "rejected"]
    canonical_record_id: str | None = None


class DuplicateGroupResponse(BaseModel):
    group_id: str
    review_required: bool
    best_score: float
    records: list[dict[str, Any]]
