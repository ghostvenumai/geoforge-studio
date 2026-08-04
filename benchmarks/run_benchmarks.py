#!/usr/bin/env python3
"""Run reproducible CSV/Parquet ingestion and pipeline benchmarks."""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
import psutil
from scripts.generate_demo_data import generate_frame

from geoforge.models.pipeline import pipeline_from_yaml
from geoforge.processing.engine import execute_pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = PROJECT_ROOT / "benchmarks" / "benchmark-results.json"
REPORT_PATH = PROJECT_ROOT / "BENCHMARK_REPORT.md"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "benchmarks"
PIPELINE = pipeline_from_yaml(
    """
name: Benchmark pipeline
steps:
  - id: address
    type: normalize_address
    name: Normalize address
    config:
      street_column: street
      city_column: city
      postal_code_column: postal_code
      country_column: country
  - id: coordinates
    type: validate_coordinates
    name: Validate coordinates
    config: {latitude_column: latitude, longitude_column: longitude, auto_swap: true}
  - id: duplicates
    type: detect_duplicates
    name: Detect duplicates
    config:
      comparison_columns: [street_normalized, postal_code_normalized, city_normalized]
      blocking_columns: [postal_code_normalized]
      weights: {street_normalized: 0.5, postal_code_normalized: 0.3, city_normalized: 0.2}
      minimum_score: 82
      review_threshold: 94
      maximum_group_size: 500
      mode: weighted
      record_id_column: record_id
      canonical_strategy: most_complete
"""
)


def _measure(operation: Any) -> tuple[Any, float, int]:
    process = psutil.Process()
    before_memory = process.memory_info().rss
    started = time.perf_counter()
    result = operation()
    elapsed = time.perf_counter() - started
    after_memory = process.memory_info().rss
    return result, elapsed, max(before_memory, after_memory)


def run_case(rows: int, seed: int) -> dict[str, Any]:
    frame, generation_seconds, generation_memory = _measure(
        lambda: generate_frame(rows, seed=seed, error_rate=0.08, duplicate_rate=0.06)
    )
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = ARTIFACT_DIR / f"benchmark-{rows}.csv"
    parquet_path = ARTIFACT_DIR / f"benchmark-{rows}.parquet"
    _, csv_write, _ = _measure(lambda: frame.write_csv(csv_path))
    _, parquet_write, _ = _measure(lambda: frame.write_parquet(parquet_path, compression="zstd"))
    csv_frame, csv_read, csv_memory = _measure(
        lambda: pl.read_csv(csv_path, infer_schema_length=10_000)
    )
    parquet_frame, parquet_read, parquet_memory = _measure(lambda: pl.read_parquet(parquet_path))
    execution, pipeline_seconds, pipeline_memory = _measure(
        lambda: execute_pipeline(parquet_frame, PIPELINE, timeout_seconds=3600)
    )
    assert csv_frame.height == parquet_frame.height == rows
    return {
        "rows": rows,
        "seed": seed,
        "generation_seconds": round(generation_seconds, 6),
        "pipeline_seconds": round(pipeline_seconds, 6),
        "pipeline_rows_per_second": round(rows / max(pipeline_seconds, 1e-9), 2),
        "pipeline_peak_observed_rss_bytes": pipeline_memory,
        "output_rows": execution.frame.height,
        "quarantine_rows": execution.quarantine.height,
        "duplicate_records": execution.duplicate_count,
        "formats": {
            "csv": {
                "size_bytes": csv_path.stat().st_size,
                "write_seconds": round(csv_write, 6),
                "read_seconds": round(csv_read, 6),
                "read_rows_per_second": round(rows / max(csv_read, 1e-9), 2),
                "peak_observed_rss_bytes": csv_memory,
            },
            "parquet": {
                "size_bytes": parquet_path.stat().st_size,
                "write_seconds": round(parquet_write, 6),
                "read_seconds": round(parquet_read, 6),
                "read_rows_per_second": round(rows / max(parquet_read, 1e-9), 2),
                "peak_observed_rss_bytes": parquet_memory,
            },
        },
        "generation_peak_observed_rss_bytes": generation_memory,
    }


def write_report(payload: dict[str, Any]) -> None:
    rows = [
        "# GeoForge Studio Benchmark Report",
        "",
        f"Measured at `{payload['measured_at']}` on `{payload['machine']['platform']}`.",
        "Times are wall-clock measurements from a single local run; RSS is process memory sampled at operation boundaries.",  # noqa: E501 - generated Markdown table/prose
        "",
        "| Rows | Pipeline s | Pipeline rows/s | CSV read s | Parquet read s | CSV size | Parquet size |",  # noqa: E501 - generated Markdown table/prose
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in payload["results"]:
        rows.append(
            f"| {result['rows']:,} | {result['pipeline_seconds']:.3f} | "
            f"{result['pipeline_rows_per_second']:,.0f} | {result['formats']['csv']['read_seconds']:.3f} | "  # noqa: E501 - generated Markdown table/prose
            f"{result['formats']['parquet']['read_seconds']:.3f} | {result['formats']['csv']['size_bytes']:,} | "  # noqa: E501 - generated Markdown table/prose
            f"{result['formats']['parquet']['size_bytes']:,} |"
        )
    rows.extend(
        [
            "",
            "## Method",
            "",
            "Synthetic rows are generated with a fixed seed, written to CSV and Zstandard Parquet, read with Polars, then processed through address normalization, coordinate validation, and blocked weighted deduplication. The one-million-row case is opt-in via `--include-million`.",  # noqa: E501 - generated Markdown table/prose
        ]
    )
    REPORT_PATH.write_text("\n".join(rows) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, nargs="+", default=[10_000, 100_000])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-million", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    sizes = list(dict.fromkeys(arguments.rows + ([1_000_000] if arguments.include_million else [])))
    results = [run_case(size, arguments.seed) for size in sizes]
    payload = {
        "measured_at": datetime.now(UTC).isoformat(),
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": psutil.cpu_count(logical=True),
            "memory_total_bytes": psutil.virtual_memory().total,
        },
        "results": results,
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_report(payload)
    print(json.dumps(payload, indent=2))
