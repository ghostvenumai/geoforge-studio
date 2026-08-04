from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from geoforge.db.base import get_db
from geoforge.db.models import Artifact, Dataset, Pipeline, ReviewDecision, Run
from geoforge.models.common import ListResponse, MessageResponse, MetricsResponse
from geoforge.models.run import (
    ArtifactResponse,
    DuplicateDecisionRequest,
    DuplicateGroupResponse,
    RunCreateRequest,
    RunResponse,
)
from geoforge.services.runs import run_manager

router = APIRouter(prefix="/runs", tags=["runs"])
DbSession = Annotated[Session, Depends(get_db)]


def _get_run(run_id: str, db: Session) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("", response_model=ListResponse[RunResponse])
def list_runs(db: DbSession) -> ListResponse[RunResponse]:
    items = list(db.scalars(select(Run).order_by(Run.created_at.desc())))
    return ListResponse(
        items=[RunResponse.model_validate(item) for item in items], total=len(items)
    )


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: str, db: DbSession) -> Run:
    return _get_run(run_id, db)


@router.post("/{run_id}/cancel", response_model=MessageResponse)
def cancel_run(run_id: str, db: DbSession) -> MessageResponse:
    run = _get_run(run_id, db)
    if run.status not in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Only queued or running runs can be cancelled")
    run.cancel_requested = True
    if run.status == "queued":
        run.status = "cancelled"
    db.commit()
    return MessageResponse(message="Cancellation requested")


@router.get("/{run_id}/metrics", response_model=MetricsResponse)
def get_metrics(run_id: str, db: DbSession) -> MetricsResponse:
    return MetricsResponse(metrics=_get_run(run_id, db).metrics_json)


@router.get("/{run_id}/artifacts", response_model=ListResponse[ArtifactResponse])
def get_artifacts(run_id: str, db: DbSession) -> ListResponse[ArtifactResponse]:
    _get_run(run_id, db)
    items = list(db.scalars(select(Artifact).where(Artifact.run_id == run_id)))
    return ListResponse(
        items=[ArtifactResponse.model_validate(item) for item in items], total=len(items)
    )


def _result_frame(run_id: str, db: Session) -> pl.DataFrame:
    artifact = db.scalar(
        select(Artifact).where(Artifact.run_id == run_id, Artifact.kind == "result_parquet")
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Run result is not available")
    return pl.read_parquet(Path(artifact.stored_path))


@router.get("/{run_id}/duplicates", response_model=ListResponse[DuplicateGroupResponse])
def duplicate_groups(run_id: str, db: DbSession) -> ListResponse[DuplicateGroupResponse]:
    _get_run(run_id, db)
    frame = _result_frame(run_id, db)
    if "duplicate_group_id" not in frame.columns:
        return ListResponse(items=[], total=0)
    groups: list[DuplicateGroupResponse] = []
    filtered = frame.filter(pl.col("duplicate_group_id").is_not_null())
    for group in filtered.partition_by("duplicate_group_id", maintain_order=True):
        group_id = str(group["duplicate_group_id"][0])
        scores = [float(score) for score in group["match_score"].drop_nulls().to_list()]
        groups.append(
            DuplicateGroupResponse(
                group_id=group_id,
                review_required=bool(group["review_required"].any()),
                best_score=max(scores, default=100),
                records=group.to_dicts(),
            )
        )
    return ListResponse(items=groups, total=len(groups))


@router.post("/{run_id}/duplicates/decision", response_model=MessageResponse)
def decide_duplicate(
    run_id: str, payload: DuplicateDecisionRequest, db: DbSession
) -> MessageResponse:
    _get_run(run_id, db)
    decision = ReviewDecision(
        id=uuid.uuid4().hex,
        run_id=run_id,
        duplicate_group_id=payload.duplicate_group_id,
        decision=payload.decision,
        canonical_record_id=payload.canonical_record_id,
    )
    db.add(decision)
    db.commit()
    return MessageResponse(message="Review decision recorded")


def create_run_for_pipeline(pipeline_id: str, payload: RunCreateRequest, db: Session) -> Run:
    if db.get(Pipeline, pipeline_id) is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if db.get(Dataset, payload.dataset_id) is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    run = Run(id=uuid.uuid4().hex, dataset_id=payload.dataset_id, pipeline_id=pipeline_id)
    db.add(run)
    db.commit()
    db.refresh(run)
    run_manager.submit(run.id)
    return run


pipeline_run_router = APIRouter(prefix="/pipelines", tags=["runs"])


@pipeline_run_router.post(
    "/{pipeline_id}/run", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED
)
def start_run(pipeline_id: str, payload: RunCreateRequest, db: DbSession) -> Run:
    return create_run_for_pipeline(pipeline_id, payload, db)
