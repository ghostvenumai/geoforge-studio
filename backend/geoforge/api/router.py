from fastapi import APIRouter

from geoforge.api.routes import artifacts, datasets, health, overview, pipelines, runs

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(datasets.router)
api_router.include_router(pipelines.router)
api_router.include_router(runs.pipeline_run_router)
api_router.include_router(runs.router)
api_router.include_router(artifacts.router)
api_router.include_router(overview.router)
