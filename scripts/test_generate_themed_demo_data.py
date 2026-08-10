from __future__ import annotations

import polars as pl
import pytest

from scripts.generate_themed_demo_data import THEME_BUILDERS, generate_theme_frame

ADDRESS_COLUMNS = {
    "record_id",
    "street",
    "city",
    "postal_code",
    "country",
    "latitude",
    "longitude",
    "quality_note",
}


@pytest.mark.parametrize("theme", sorted(THEME_BUILDERS))
def test_theme_generator_is_deterministic(theme: str) -> None:
    first = generate_theme_frame(theme, 100, seed=17, error_rate=0.2, duplicate_rate=0.1)
    second = generate_theme_frame(theme, 100, seed=17, error_rate=0.2, duplicate_rate=0.1)
    assert first.equals(second)


@pytest.mark.parametrize("theme", sorted(THEME_BUILDERS))
def test_theme_generator_keeps_canonical_address_columns(theme: str) -> None:
    frame = generate_theme_frame(theme, 500, seed=42, error_rate=0.2, duplicate_rate=0.1)
    assert frame.height == 500
    assert set(frame.columns) >= ADDRESS_COLUMNS
    assert frame["record_id"].n_unique() == frame.height


def test_security_theme_contains_defensive_demo_payloads() -> None:
    frame = generate_theme_frame("security", 2_000, seed=42, error_rate=0.3, duplicate_rate=0.05)
    notes = frame["note"].cast(pl.String)
    comments = frame["comment"].cast(pl.String)
    sources = frame["source_file"].cast(pl.String)
    assert notes.str.contains(r"^[=+\-@]").any()
    assert comments.str.contains("<script>").any()
    assert sources.str.contains(r"\.\.").any()


def test_marketing_theme_contains_campaign_fields() -> None:
    frame = generate_theme_frame("marketing", 1_000, seed=42, error_rate=0.2, duplicate_rate=0.1)
    assert {"email", "campaign", "channel", "consent", "lead_score"} <= set(frame.columns)
    assert frame["campaign"].null_count() == 0
