from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from geoforge.core.config import Settings, get_settings
from geoforge.core.security import ensure_contained
from geoforge.db.base import get_db
from geoforge.db.models import Artifact

router = APIRouter(prefix="/artifacts", tags=["artifacts"])
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.get("/{artifact_id}/download", response_class=FileResponse)
def download_artifact(artifact_id: str, db: DbSession, settings: AppSettings) -> FileResponse:
    artifact = db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        path = ensure_contained(Path(artifact.stored_path), settings.artifact_dir)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Artifact path is invalid") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact file is missing")
    return FileResponse(path, media_type=artifact.media_type, filename=artifact.name)
