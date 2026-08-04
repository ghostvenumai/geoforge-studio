from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from geoforge.db.base import get_db
from geoforge.db.models import Dataset, Run

router = APIRouter(tags=["overview"])
DbSession = Annotated[Session, Depends(get_db)]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
BENCHMARK_RESULTS = PROJECT_ROOT / "benchmarks" / "benchmark-results.json"


@router.get("/benchmarks")
def benchmark_results() -> dict[str, Any]:
    if not BENCHMARK_RESULTS.is_file():
        return {"measured_at": None, "machine": {}, "results": []}
    payload: Any = json.loads(BENCHMARK_RESULTS.read_text(encoding="utf-8"))
    return (
        payload
        if isinstance(payload, dict)
        else {"measured_at": None, "machine": {}, "results": []}
    )


@router.get("/overview")
def overview(db: DbSession) -> dict[str, Any]:
    datasets = list(db.scalars(select(Dataset).order_by(Dataset.created_at)))
    runs = list(db.scalars(select(Run).order_by(Run.created_at)))
    completed = [run for run in runs if run.status == "completed"]
    latest = completed[-1] if completed else None
    quality_values = [run.quality_after for run in completed if run.quality_after is not None]
    status_counts = Counter(run.status for run in runs)
    step_durations: list[dict[str, Any]] = []
    throughput: list[dict[str, Any]] = []
    for run in completed[-20:]:
        raw_steps = run.metrics_json.get("steps", [])
        steps = raw_steps if isinstance(raw_steps, list) else []
        for raw_step in steps:
            if not isinstance(raw_step, dict):
                continue
            step: dict[str, Any] = raw_step
            step_durations.append(
                {
                    "run_id": run.id,
                    "step": step.get("name", step.get("step_type")),
                    "duration": step.get("duration_seconds", 0),
                }
            )
        throughput.append(
            {
                "run_id": run.id,
                "created_at": run.created_at,
                "rows_per_second": run.metrics_json.get("rows_per_second", 0),
            }
        )
    return {
        "summary": {
            "datasets": len(datasets),
            "processed_datasets": len({run.dataset_id for run in completed}),
            "active_runs": status_counts["queued"] + status_counts["running"],
            "completed_runs": status_counts["completed"],
            "average_quality_score": round(sum(quality_values) / len(quality_values), 2)
            if quality_values
            else 0,
            "duplicates": sum(run.duplicate_count for run in completed),
            "quarantined_rows": sum(run.quarantine_rows for run in completed),
            "latest_throughput": latest.metrics_json.get("rows_per_second", 0) if latest else 0,
            "latest_runtime": latest.metrics_json.get("total_runtime_seconds", 0) if latest else 0,
            "latest_peak_memory": latest.metrics_json.get("peak_memory_bytes", 0) if latest else 0,
            "latest_input_size": latest.metrics_json.get("input_size_bytes", 0) if latest else 0,
            "latest_output_size": latest.metrics_json.get("output_size_bytes", 0) if latest else 0,
        },
        "quality": [
            {"run_id": run.id, "before": run.quality_before, "after": run.quality_after}
            for run in completed[-20:]
        ],
        "step_durations": step_durations,
        "throughput": throughput,
        "dataset_volumes": [
            {"dataset_id": dataset.id, "name": dataset.name, "rows": dataset.row_count}
            for dataset in datasets[-20:]
        ],
        "run_status": dict(status_counts),
    }
