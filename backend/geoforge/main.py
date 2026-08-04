from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from geoforge import __version__
from geoforge.api.router import api_router
from geoforge.core.config import get_settings
from geoforge.core.errors import http_exception_handler, validation_exception_handler
from geoforge.core.logging import configure_logging
from geoforge.core.middleware import RequestContextMiddleware
from geoforge.db.base import SessionLocal, init_db
from geoforge.services.pipelines import seed_example_pipelines
from geoforge.services.runs import run_manager


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.ensure_directories()
    init_db()
    run_manager.startup()
    with SessionLocal() as db:
        seed_example_pipelines(db)
    yield
    run_manager.shutdown()


configure_logging()
settings = get_settings()
app = FastAPI(
    title="GeoForge Studio API",
    summary="High-performance address, geo, and data transformation platform",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-Request-ID"],
)
app.add_middleware(RequestContextMiddleware)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.include_router(api_router)
