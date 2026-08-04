from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from geoforge.processing.geo import (
    geohash,
    haversine_distance,
    transform_coordinates,
    validate_coordinates,
)


def test_valid_and_swapped_coordinates() -> None:
    assert validate_coordinates(52.52, 13.405).valid
    swapped = validate_coordinates(120.0, 52.0)
    assert swapped.valid and swapped.swapped
    assert (swapped.latitude, swapped.longitude) == (52.0, 120.0)


@given(
    st.floats(allow_nan=False, allow_infinity=False),
    st.floats(allow_nan=False, allow_infinity=False),
)
def test_coordinate_validity_matches_world_bounds(latitude: float, longitude: float) -> None:
    result = validate_coordinates(latitude, longitude, auto_swap=False)
    assert result.valid == (-90 <= latitude <= 90 and -180 <= longitude <= 180)


def test_epsg_roundtrip_is_accurate() -> None:
    easting, northing = transform_coordinates(13.405, 52.52)
    longitude, latitude = transform_coordinates(easting, northing, "EPSG:25832", "EPSG:4326")
    assert longitude == pytest.approx(13.405, abs=1e-6)
    assert latitude == pytest.approx(52.52, abs=1e-6)


def test_haversine_identity_and_known_distance() -> None:
    assert haversine_distance(52.52, 13.405, 52.52, 13.405) == 0
    berlin_hamburg = haversine_distance(52.52, 13.405, 53.5511, 9.9937)
    assert berlin_hamburg == pytest.approx(255_000, rel=0.03)
    assert math.isfinite(berlin_hamburg)


def test_geohash_is_deterministic() -> None:
    assert geohash(52.52, 13.405, 7) == geohash(52.52, 13.405, 7)
    assert len(geohash(52.52, 13.405, 7)) == 7
