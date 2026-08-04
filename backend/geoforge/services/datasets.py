from __future__ import annotations

import hashlib
import os
import uuid
from contextlib import suppress
from pathlib import Path

import polars as pl
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from geoforge.core.config import Settings
from geoforge.core.security import sanitize_filename, validate_extension
from geoforge.db.models import Dataset
from geoforge.processing.ingestion import read_dataset, safe_preview, schema_payload
from geoforge.processing.profile import ProfileOptions, profile_frame

UPLOAD_CHUNK_SIZE = 1024 * 1024


class UploadTooLargeError(ValueError):
    pass


async def create_dataset(upload: UploadFile, db: Session, settings: Settings) -> Dataset:
    safe_name = sanitize_filename(upload.filename or "upload")
    file_format = validate_extension(safe_name)
    dataset_id = uuid.uuid4().hex
    target_dir = settings.upload_dir / dataset_id
    target_dir.mkdir(parents=True, exist_ok=False)
    target = target_dir / f"original.{file_format}"
    partial = target_dir / ".uploading"
    maximum_bytes = settings.max_upload_mb * 1024 * 1024
    total = 0
    digest = hashlib.sha256()
    try:
        with partial.open("xb") as handle:
            while chunk := await upload.read(UPLOAD_CHUNK_SIZE):
                total += len(chunk)
                if total > maximum_bytes:
                    raise UploadTooLargeError(
                        f"Upload exceeds the configured {settings.max_upload_mb} MB limit"
                    )
                digest.update(chunk)
                handle.write(chunk)
        os.replace(partial, target)
        frame, encoding, delimiter = read_dataset(target, file_format)
    except Exception:
        partial.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        target_dir.rmdir()
        raise
    checksum = digest.hexdigest()
    existing = db.scalar(select(Dataset).where(Dataset.checksum == checksum))
    dataset = Dataset(
        id=dataset_id,
        name=Path(safe_name).stem[:128],
        original_filename=safe_name,
        stored_path=str(target),
        format=file_format,
        checksum=checksum,
        size_bytes=total,
        row_count=frame.height,
        column_count=frame.width,
        schema_json=schema_payload(frame),
        preview_json=safe_preview(frame, settings.preview_rows),
        encoding=encoding,
        delimiter=delimiter,
        status="duplicate" if existing else "ready",
        duplicate_of_dataset_id=existing.id if existing else None,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def load_dataset_frame(dataset: Dataset) -> pl.DataFrame:
    frame, _, _ = read_dataset(Path(dataset.stored_path), dataset.format)
    return frame


def profile_dataset(dataset: Dataset, db: Session, settings: Settings) -> dict[str, object]:
    frame, _, _ = read_dataset(Path(dataset.stored_path), dataset.format)
    profile = profile_frame(frame, ProfileOptions(sample_rows=settings.profile_sample_rows))
    warnings: list[str] = []
    if dataset.duplicate_of_dataset_id:
        warnings.append(f"File checksum matches dataset {dataset.duplicate_of_dataset_id}")
    profile["warnings"] = warnings
    dataset.profile_json = profile
    dataset.status = "profiled"
    db.commit()
    return profile


def delete_dataset_files(dataset: Dataset, settings: Settings) -> None:
    target = Path(dataset.stored_path).resolve()
    root = settings.upload_dir.resolve()
    if not target.is_relative_to(root):
        raise ValueError("Dataset storage path is outside the upload root")
    target.unlink(missing_ok=True)
    with suppress(OSError):
        target.parent.rmdir()
