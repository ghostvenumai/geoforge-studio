from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import psutil
from sqlalchemy.orm import Session

from geoforge import __version__
from geoforge.core.config import Settings, get_settings
from geoforge.core.security import protect_spreadsheet_cell, sha256_file
from geoforge.db.base import SessionLocal
from geoforge.db.models import Artifact, Dataset, Pipeline, Run
from geoforge.models.pipeline import PipelineDefinition, pipeline_to_yaml
from geoforge.processing.engine import (
    RunCancelledError,
    RunTimeoutError,
    execute_pipeline,
    metrics_payload,
)
from geoforge.processing.ingestion import read_dataset, safe_preview
from geoforge.processing.profile import profile_frame


class ResourceMonitor:
    def __init__(self, interval_seconds: float = 0.05) -> None:
        self.interval_seconds = interval_seconds
        self.process = psutil.Process()
        self.peak_memory = self.process.memory_info().rss
        self.cpu_samples: list[float] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._started = False

    def _sample(self) -> None:
        self.process.cpu_percent(None)
        while not self._stop.wait(self.interval_seconds):
            self.peak_memory = max(self.peak_memory, self.process.memory_info().rss)
            self.cpu_samples.append(self.process.cpu_percent(None))

    def start(self) -> None:
        self._started = True
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._started:
            self._thread.join(timeout=1)
        self.peak_memory = max(self.peak_memory, self.process.memory_info().rss)

    @property
    def average_cpu(self) -> float:
        return round(sum(self.cpu_samples) / len(self.cpu_samples), 2) if self.cpu_samples else 0.0


def _atomic_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _safe_csv_frame(frame: pl.DataFrame) -> pl.DataFrame:
    expressions: list[pl.Expr] = []
    for name, dtype in frame.schema.items():
        if dtype.is_nested() or dtype == pl.Object:
            expressions.append(
                pl.col(name)
                .map_elements(
                    lambda value: json.dumps(value, ensure_ascii=False, default=str),
                    return_dtype=pl.String,
                )
                .alias(name)
            )
        elif dtype == pl.String:
            expressions.append(
                pl.col(name)
                .map_elements(protect_spreadsheet_cell, return_dtype=pl.String)
                .alias(name)
            )
    return frame.with_columns(expressions) if expressions else frame


def _write_frame_atomic(frame: pl.DataFrame, path: Path, file_format: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if file_format == "parquet":
        frame.write_parquet(temporary, compression="zstd")
    elif file_format == "csv":
        _safe_csv_frame(frame).write_csv(temporary)
    elif file_format == "jsonl":
        frame.write_ndjson(temporary)
    else:
        raise ValueError(f"Unsupported artifact format: {file_format}")
    os.replace(temporary, path)


def _add_artifact(db: Session, run_id: str, kind: str, path: Path, media_type: str) -> Artifact:
    artifact = Artifact(
        id=uuid.uuid4().hex,
        run_id=run_id,
        kind=kind,
        name=path.name,
        stored_path=str(path),
        checksum=sha256_file(path),
        size_bytes=path.stat().st_size,
        media_type=media_type,
    )
    db.add(artifact)
    return artifact


def _write_artifacts(
    db: Session,
    settings: Settings,
    run: Run,
    dataset: Dataset,
    pipeline: Pipeline,
    output: pl.DataFrame,
    quarantine: pl.DataFrame,
    metrics: dict[str, Any],
    quality_report: dict[str, Any],
) -> list[Artifact]:
    run_dir = settings.artifact_dir / run.id
    run_dir.mkdir(parents=True, exist_ok=False)
    artifacts: list[Artifact] = []
    formats = {
        "result.parquet": ("result_parquet", "parquet", "application/vnd.apache.parquet"),
        "result.csv": ("result_csv", "csv", "text/csv"),
        "result.jsonl": ("result_jsonl", "jsonl", "application/x-ndjson"),
    }
    for filename, (kind, file_format, media_type) in formats.items():
        path = run_dir / filename
        _write_frame_atomic(output, path, file_format)
        artifacts.append(_add_artifact(db, run.id, kind, path, media_type))
    quarantine_path = run_dir / "quarantine.parquet"
    _write_frame_atomic(quarantine, quarantine_path, "parquet")
    artifacts.append(
        _add_artifact(db, run.id, "quarantine", quarantine_path, "application/vnd.apache.parquet")
    )
    quality_path = run_dir / "quality-report.json"
    _atomic_json(quality_path, quality_report)
    artifacts.append(_add_artifact(db, run.id, "quality_report", quality_path, "application/json"))
    performance_path = run_dir / "performance-report.json"
    _atomic_json(performance_path, metrics)
    artifacts.append(
        _add_artifact(db, run.id, "performance_report", performance_path, "application/json")
    )
    pipeline_path = run_dir / "pipeline.yaml"
    pipeline_path.write_text(
        pipeline_to_yaml(PipelineDefinition.model_validate(pipeline.definition_json)),
        encoding="utf-8",
    )
    artifacts.append(_add_artifact(db, run.id, "pipeline_yaml", pipeline_path, "application/yaml"))
    audit_path = run_dir / "audit-log.jsonl"
    audit_entries = [
        {
            "run_id": run.id,
            "event": "step_completed",
            "step_id": step["step_id"],
            "duration_seconds": step["duration_seconds"],
            "input_rows": step["input_rows"],
            "output_rows": step["output_rows"],
            "changed_rows": step["changed_rows"],
            "quarantined_rows": step["quarantined_rows"],
        }
        for step in metrics["steps"]
    ]
    audit_path.write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in audit_entries),
        encoding="utf-8",
    )
    artifacts.append(_add_artifact(db, run.id, "audit_log", audit_path, "application/x-ndjson"))
    manifest = {
        "run_id": run.id,
        "software_version": __version__,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "dataset_id": dataset.id,
        "pipeline_id": pipeline.id,
        "input_checksum": dataset.checksum,
        "pipeline_checksum": pipeline.checksum,
        "input_rows": run.input_rows,
        "output_rows": run.output_rows,
        "quarantine_rows": run.quarantine_rows,
        "errors": run.error_count,
        "warnings": run.warning_count,
        "step_metrics": metrics["steps"],
        "artifacts": [
            {"id": item.id, "kind": item.kind, "name": item.name, "checksum": item.checksum}
            for item in artifacts
        ],
    }
    manifest_path = run_dir / "run-manifest.json"
    _atomic_json(manifest_path, manifest)
    manifest_artifact = _add_artifact(db, run.id, "run_manifest", manifest_path, "application/json")
    artifacts.append(manifest_artifact)
    checksums_path = run_dir / "checksums.sha256"
    checksums_path.write_text(
        "".join(f"{item.checksum}  {item.name}\n" for item in artifacts), encoding="utf-8"
    )
    artifacts.append(_add_artifact(db, run.id, "checksums", checksums_path, "text/plain"))
    return artifacts


def execute_run(run_id: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    db = SessionLocal()
    monitor = ResourceMonitor()
    started_clock = time.perf_counter()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return
        dataset = db.get(Dataset, run.dataset_id)
        pipeline = db.get(Pipeline, run.pipeline_id)
        if dataset is None or pipeline is None:
            raise ValueError("Run references missing dataset or pipeline")
        active_run = run
        run.status = "running"
        run.started_at = datetime.now(UTC)
        db.commit()
        frame, _, _ = read_dataset(Path(dataset.stored_path), dataset.format)
        before_profile = profile_frame(frame)
        run.input_rows = frame.height
        run.quality_before = float(before_profile["quality_score"])
        db.commit()
        monitor.start()

        def cancelled() -> bool:
            db.expire(active_run, ["cancel_requested"])
            return active_run.cancel_requested

        definition = PipelineDefinition.model_validate(pipeline.definition_json)
        result = execute_pipeline(
            frame,
            definition,
            cancel_check=cancelled,
            timeout_seconds=settings.run_timeout_seconds,
        )
        monitor.stop()
        after_profile = profile_frame(result.frame)
        elapsed = time.perf_counter() - started_clock
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        run.output_rows = result.frame.height
        run.quarantine_rows = result.quarantine.height
        run.duplicate_count = result.duplicate_count
        run.quality_after = float(after_profile["quality_score"])
        run.warning_count = len(result.warnings)
        output_estimated = result.frame.estimated_size()
        metrics = {
            "total_runtime_seconds": round(elapsed, 6),
            "rows_per_second": round(frame.height / max(elapsed, 1e-9), 2),
            "peak_memory_bytes": monitor.peak_memory,
            "average_cpu_percent": monitor.average_cpu,
            "input_size_bytes": dataset.size_bytes,
            "output_size_bytes": output_estimated,
            "compression_ratio": round(output_estimated / max(dataset.size_bytes, 1), 4),
            "processed_rows": frame.height,
            "errors": 0,
            "warnings": len(result.warnings),
            "steps": metrics_payload(result.step_metrics),
            "result_preview": safe_preview(result.frame, 25),
            "quarantine_preview": safe_preview(result.quarantine, 25),
        }
        quality_report = {
            "before": before_profile,
            "after": after_profile,
            "absolute_change": round(run.quality_after - run.quality_before, 2),
            "percent_change": round(
                100 * (run.quality_after - run.quality_before) / max(run.quality_before, 1), 2
            ),
            "input_rows": frame.height,
            "output_rows": result.frame.height,
            "quarantine_rows": result.quarantine.height,
            "data_loss_rows": max(0, frame.height - result.frame.height - result.quarantine.height),
            "warnings": result.warnings,
        }
        run.metrics_json = metrics
        db.flush()
        _write_artifacts(
            db,
            settings,
            run,
            dataset,
            pipeline,
            result.frame,
            result.quarantine,
            metrics,
            quality_report,
        )
        db.commit()
    except (RunCancelledError, RunTimeoutError) as exc:
        monitor.stop()
        run = db.get(Run, run_id)
        if run:
            run.status = "cancelled" if isinstance(exc, RunCancelledError) else "timed_out"
            run.finished_at = datetime.now(UTC)
            run.error_message = str(exc)
            run.warning_count += 1
            db.commit()
    except Exception as exc:
        monitor.stop()
        run = db.get(Run, run_id)
        if run:
            run.status = "failed"
            run.finished_at = datetime.now(UTC)
            run.error_count = 1
            run.error_message = f"{type(exc).__name__}: {str(exc)[:800]}"
            db.commit()
    finally:
        db.close()


class RunManager:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.executor: ThreadPoolExecutor | None = None
        self.futures: dict[str, Future[None]] = {}
        self.lock = threading.Lock()
        self.startup()

    def startup(self) -> None:
        with self.lock:
            if self.executor is None:
                self.executor = ThreadPoolExecutor(
                    max_workers=self.settings.run_workers, thread_name_prefix="geoforge-run"
                )

    def submit(self, run_id: str) -> None:
        self.startup()
        with self.lock:
            if self.executor is None:
                raise RuntimeError("Run executor is unavailable")
            self.futures[run_id] = self.executor.submit(execute_run, run_id, self.settings)

    def shutdown(self) -> None:
        with self.lock:
            executor, self.executor = self.executor, None
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)


run_manager = RunManager()
