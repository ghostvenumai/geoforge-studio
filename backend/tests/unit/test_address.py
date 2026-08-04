from __future__ import annotations

import polars as pl
from hypothesis import given
from hypothesis import strategies as st

from geoforge.processing.address import (
    matching_key,
    normalize_address_frame,
    normalize_street,
    normalize_unicode,
    split_street_and_house_number,
    validate_postal_code,
)


def test_german_street_variants_are_standardized() -> None:
    assert normalize_street("  müller str.  ") == "Müller Straße"
    assert normalize_street("MÜLLER STRASSE") == "Müller Straße"


def test_house_number_suffix_is_split() -> None:
    parts = split_street_and_house_number("Hauptstrasse 12 b")
    assert parts.street == "Hauptstraße"
    assert parts.house_number == "12B"


def test_postal_validation_by_country() -> None:
    assert validate_postal_code("D-10115", "DE")
    assert validate_postal_code("1010", "AT")
    assert not validate_postal_code("123", "DE")


def test_original_address_values_are_preserved() -> None:
    frame = pl.DataFrame(
        {"street": [" Teststr. 1"], "city": [" berlin "], "postal_code": ["10115"]}
    )
    output = normalize_address_frame(frame, country_column=None)
    assert output["street_original"][0] == " Teststr. 1"
    assert output["street_normalized"][0] == "Teststraße"
    assert output["city_normalized"][0] == "Berlin"


@given(st.text())
def test_unicode_normalization_never_emits_controls(value: str) -> None:
    result = normalize_unicode(value)
    if result is not None:
        assert "\x00" not in result
        assert result == result.strip()


def test_matching_key_handles_umlaut_transliteration() -> None:
    assert matching_key("Müllerstraße") == matching_key("Mueller Strasse")
