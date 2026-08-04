from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import polars as pl

from geoforge.processing.address import validate_postal_code
from geoforge.processing.geo import validate_coordinates


@dataclass(frozen=True)
class ProfileOptions:
    sample_rows: int = 100_000
    top_values: int = 8


def _json_value(value: object) -> Any:
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _invalid_count(series: pl.Series, name: str, frame: pl.DataFrame) -> int:
    normalized = name.casefold()
    values = series.to_list()
    if "postal" in normalized or normalized in {"plz", "zip"}:
        return sum(value is not None and not validate_postal_code(value) for value in values)
    if normalized in {"latitude", "lat"}:
        longitude_name = next(
            (
                candidate
                for candidate in frame.columns
                if candidate.casefold() in {"longitude", "lon", "lng"}
            ),
            None,
        )
        if longitude_name:
            return sum(
                not validate_coordinates(lat, lon, auto_swap=False).valid
                for lat, lon in zip(values, frame[longitude_name].to_list(), strict=True)
                if lat is not None or lon is not None
            )
    return 0


def _recommendation(null_ratio: float, unique_ratio: float, invalid_count: int, dtype: str) -> str:
    if invalid_count:
        return "Validate and quarantine invalid values"
    if null_ratio > 0.2:
        return "Define a missing-value strategy"
    if dtype == "String" and unique_ratio < 0.1:
        return "Consider categorical encoding or value normalization"
    if dtype == "String":
        return "Trim whitespace and normalize Unicode"
    return "No transformation required"


def profile_frame(frame: pl.DataFrame, options: ProfileOptions | None = None) -> dict[str, Any]:
    options = options or ProfileOptions()
    total_rows = frame.height
    sampled = frame.head(options.sample_rows) if total_rows > options.sample_rows else frame
    columns: list[dict[str, Any]] = []
    total_nulls = 0
    total_invalid = 0
    for name in sampled.columns:
        series = sampled[name]
        non_null = series.drop_nulls()
        null_count = series.null_count()
        unique_count = series.n_unique()
        null_ratio = null_count / max(sampled.height, 1)
        unique_ratio = unique_count / max(sampled.height, 1)
        invalid_count = _invalid_count(series, name, sampled)
        total_nulls += null_count
        total_invalid += invalid_count
        stats: dict[str, Any] = {}
        if series.dtype.is_numeric() and len(non_null):
            numeric = non_null.cast(pl.Float64)
            stats = {
                "min": _json_value(numeric.min()),
                "max": _json_value(numeric.max()),
                "mean": _json_value(numeric.mean()),
                "median": _json_value(numeric.median()),
                "quantiles": {
                    "q25": _json_value(numeric.quantile(0.25)),
                    "q75": _json_value(numeric.quantile(0.75)),
                },
            }
            q25, q75 = numeric.quantile(0.25), numeric.quantile(0.75)
            if q25 is not None and q75 is not None:
                spread = q75 - q25
                stats["outlier_count"] = numeric.filter(
                    (numeric < q25 - 1.5 * spread) | (numeric > q75 + 1.5 * spread)
                ).len()
        elif len(non_null) and (
            series.dtype == pl.String or series.dtype == pl.Boolean or series.dtype.is_temporal()
        ):
            stats = {"min": _json_value(non_null.min()), "max": _json_value(non_null.max())}
        value_counts = series.drop_nulls().value_counts(sort=True).head(options.top_values)
        top_values = [
            {"value": _json_value(row[name]), "count": row["count"]}
            for row in value_counts.to_dicts()
        ]
        columns.append(
            {
                "name": name,
                "dtype": str(series.dtype),
                "null_count": null_count,
                "null_ratio": round(null_ratio, 6),
                "unique_count": unique_count,
                "unique_ratio": round(unique_ratio, 6),
                "cardinality": unique_count,
                "invalid_count": invalid_count,
                "sample_values": [_json_value(value) for value in non_null.head(5).to_list()],
                "top_values": top_values,
                "statistics": stats,
                "recommendation": _recommendation(
                    null_ratio, unique_ratio, invalid_count, str(series.dtype)
                ),
            }
        )
    exact_duplicates = int(sampled.is_duplicated().sum()) if sampled.height else 0
    cells = max(sampled.height * max(sampled.width, 1), 1)
    completeness = 1 - total_nulls / cells
    validity = 1 - min(total_invalid / cells, 1)
    uniqueness = 1 - exact_duplicates / max(sampled.height, 1)
    quality_score = round(
        max(0.0, 100 * (0.45 * completeness + 0.35 * validity + 0.2 * uniqueness)), 2
    )
    return {
        "row_count": total_rows,
        "sampled_rows": sampled.height,
        "column_count": frame.width,
        "memory_bytes": frame.estimated_size(),
        "exact_duplicate_count": exact_duplicates,
        "total_null_count": total_nulls,
        "total_invalid_count": total_invalid,
        "quality_score": quality_score,
        "sampled": sampled.height < total_rows,
        "columns": columns,
    }
