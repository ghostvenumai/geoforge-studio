from __future__ import annotations

import importlib.metadata
import platform
import sys
import time
from datetime import UTC, datetime
from typing import Annotated

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from geoforge import __version__
from geoforge.core.config import Settings, get_settings
from geoforge.db.base import get_db
from geoforge.models.common import HealthResponse, SystemInfoResponse

router = APIRouter(tags=["system"])
STARTED_AT = time.monotonic()


@router.get("/health", response_model=HealthResponse)
def health(
    db: Annotated[Session, Depends(get_db)], settings: Annotated[Settings, Depends(get_settings)]
) -> HealthResponse:
    db.execute(text("SELECT 1"))
    storage = (
        "ready" if settings.data_dir.is_dir() and settings.artifact_dir.is_dir() else "missing"
    )
    return HealthResponse(
        status="healthy" if storage == "ready" else "degraded",
        version=__version__,
        database="ready",
        storage=storage,
        timestamp=datetime.now(UTC),
    )


@router.get("/system/info", response_model=SystemInfoResponse)
def system_info() -> SystemInfoResponse:
    memory = psutil.virtual_memory()
    dependencies = {
        name: importlib.metadata.version(name)
        for name in ("fastapi", "polars", "pyarrow", "duckdb", "pyproj", "sqlalchemy")
    }
    return SystemInfoResponse(
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        cpu_count=psutil.cpu_count(logical=True) or 1,
        memory_total_bytes=memory.total,
        memory_available_bytes=memory.available,
        process_memory_bytes=psutil.Process().memory_info().rss,
        uptime_seconds=time.monotonic() - STARTED_AT,
        dependencies=dependencies,
    )
