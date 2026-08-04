from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from geoforge.db.base import get_db
from geoforge.db.models import Pipeline
from geoforge.models.common import ListResponse
from geoforge.models.pipeline import pipeline_from_yaml
from geoforge.models.run import (
    PipelineCreateRequest,
    PipelineResponse,
    PipelineValidateRequest,
    PipelineValidateResponse,
)
from geoforge.services.pipelines import create_pipeline

router = APIRouter(prefix="/pipelines", tags=["pipelines"])
DbSession = Annotated[Session, Depends(get_db)]


def _get_pipeline(pipeline_id: str, db: Session) -> Pipeline:
    pipeline = db.get(Pipeline, pipeline_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.post("/validate", response_model=PipelineValidateResponse)
def validate_pipeline(payload: PipelineValidateRequest) -> PipelineValidateResponse:
    try:
        definition = pipeline_from_yaml(payload.yaml_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    warnings = [] if definition.edges else ["No graph edges supplied; steps execute in list order"]
    return PipelineValidateResponse(
        valid=True,
        checksum=definition.checksum,
        definition=definition.model_dump(mode="json"),
        warnings=warnings,
    )


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def add_pipeline(payload: PipelineCreateRequest, db: DbSession) -> Pipeline:
    try:
        definition = pipeline_from_yaml(payload.yaml_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return create_pipeline(db, definition, payload.yaml_text)


@router.get("", response_model=ListResponse[PipelineResponse])
def list_pipelines(db: DbSession) -> ListResponse[PipelineResponse]:
    items = list(db.scalars(select(Pipeline).order_by(Pipeline.updated_at.desc())))
    return ListResponse(
        items=[PipelineResponse.model_validate(item) for item in items], total=len(items)
    )


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(pipeline_id: str, db: DbSession) -> Pipeline:
    return _get_pipeline(pipeline_id, db)
