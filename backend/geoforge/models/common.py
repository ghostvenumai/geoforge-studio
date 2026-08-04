from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    storage: str
    timestamp: datetime


class SystemInfoResponse(BaseModel):
    python_version: str
    platform: str
    cpu_count: int
    memory_total_bytes: int
    memory_available_bytes: int
    process_memory_bytes: int
    uptime_seconds: float
    dependencies: dict[str, str]


class ListResponse[T](BaseModel):
    items: list[T]
    total: int


class MessageResponse(BaseModel):
    message: str


class MetricsResponse(BaseModel):
    metrics: dict[str, Any]
