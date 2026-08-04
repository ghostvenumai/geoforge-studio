from __future__ import annotations

import polars as pl

from scripts.generate_demo_data import generate_frame


def test_generator_is_deterministic() -> None:
    first = generate_frame(100, seed=17, error_rate=0.2, duplicate_rate=0.1)
    second = generate_frame(100, seed=17, error_rate=0.2, duplicate_rate=0.1)
    assert first.equals(second)


def test_generator_contains_required_synthetic_quality_cases() -> None:
    frame = generate_frame(2_000, seed=42, error_rate=0.2, duplicate_rate=0.1)
    assert frame.height == 2_000
    assert set(frame.columns) >= {
        "record_id",
        "street",
        "city",
        "postal_code",
        "latitude",
        "longitude",
        "event_date",
        "quality_note",
    }
    assert frame.filter(pl.col("quality_note").cast(pl.String).str.contains(r"^[=+\-@]")).height > 0
    assert frame["record_id"].n_unique() == frame.height
