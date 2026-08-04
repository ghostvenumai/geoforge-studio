from __future__ import annotations

import polars as pl

from geoforge.processing.profile import ProfileOptions, profile_frame


def test_profile_reports_quality_statistics_and_sampling() -> None:
    frame = pl.DataFrame(
        {
            "postal_code": ["10115", "bad", None, "10115"],
            "value": [1, 2, 100, 1],
            "city": ["Berlin", "Berlin", None, "Berlin"],
        }
    )
    profile = profile_frame(frame, ProfileOptions(sample_rows=3))
    assert profile["row_count"] == 4
    assert profile["sampled_rows"] == 3
    assert profile["sampled"] is True
    assert 0 <= profile["quality_score"] <= 100
    postal = next(column for column in profile["columns"] if column["name"] == "postal_code")
    assert postal["invalid_count"] == 1
    assert postal["recommendation"] == "Validate and quarantine invalid values"


def test_profile_detects_exact_duplicates() -> None:
    frame = pl.DataFrame({"a": [1, 1], "b": ["x", "x"]})
    assert profile_frame(frame)["exact_duplicate_count"] == 2
