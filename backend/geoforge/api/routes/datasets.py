from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from geoforge.core.config import Settings, get_settings
from geoforge.db.base import get_db
from geoforge.db.models import Dataset
from geoforge.models.common import ListResponse, MessageResponse
from geoforge.models.dataset import DatasetResponse, DemoDatasetInfo, ProfileResponse
from geoforge.services.datasets import (
    DEMO_DATASETS,
    DemoTheme,
    UploadTooLargeError,
    create_dataset,
    create_demo_dataset,
    delete_dataset_files,
    profile_dataset,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def _get_dataset(dataset_id: str, db: Session) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    db: DbSession, settings: AppSettings, file: Annotated[UploadFile, File(...)]
) -> Dataset:
    try:
        return await create_dataset(file, db, settings)
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/demo", response_model=ListResponse[DemoDatasetInfo])
def list_demo_datasets() -> ListResponse[DemoDatasetInfo]:
    items = [
        DemoDatasetInfo(
            theme=item.theme.value,
            title=item.title,
            description=item.description,
            filename=item.filename,
            recommended_pipeline=item.recommended_pipeline,
        )
        for item in DEMO_DATASETS.values()
    ]
    return ListResponse(items=items, total=len(items))


@router.post("/demo/{theme}", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def load_demo_dataset(theme: DemoTheme, db: DbSession, settings: AppSettings) -> Dataset:
    try:
        return await create_demo_dataset(theme, db, settings)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("", response_model=ListResponse[DatasetResponse])
def list_datasets(db: DbSession) -> ListResponse[DatasetResponse]:
    items = list(db.scalars(select(Dataset).order_by(Dataset.created_at.desc())))
    return ListResponse(
        items=[DatasetResponse.model_validate(item) for item in items], total=len(items)
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: DbSession) -> Dataset:
    return _get_dataset(dataset_id, db)


@router.delete("/{dataset_id}", response_model=MessageResponse)
def delete_dataset(dataset_id: str, db: DbSession, settings: AppSettings) -> MessageResponse:
    dataset = _get_dataset(dataset_id, db)
    if dataset.runs:
        raise HTTPException(status_code=409, detail="Datasets with runs cannot be deleted")
    delete_dataset_files(dataset, settings)
    db.delete(dataset)
    db.commit()
    return MessageResponse(message="Dataset deleted")


@router.post("/{dataset_id}/profile", response_model=ProfileResponse)
def start_profile(dataset_id: str, db: DbSession, settings: AppSettings) -> ProfileResponse:
    dataset = _get_dataset(dataset_id, db)
    try:
        profile = profile_dataset(dataset, db, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProfileResponse(dataset_id=dataset.id, profile=profile)


@router.get("/{dataset_id}/profile", response_model=ProfileResponse)
def get_profile(dataset_id: str, db: DbSession) -> ProfileResponse:
    dataset = _get_dataset(dataset_id, db)
    if dataset.profile_json is None:
        raise HTTPException(status_code=404, detail="Dataset has not been profiled")
    return ProfileResponse(dataset_id=dataset.id, profile=dataset.profile_json)
