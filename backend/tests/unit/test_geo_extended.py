from __future__ import annotations

import polars as pl
import pytest

from geoforge.processing.geo import (
    geohash,
    in_bounding_box,
    spatial_group,
    validate_coordinate_frame,
    validate_coordinates,
)


def test_non_numeric_missing_and_outside_coordinates() -> None:
    assert validate_coordinates(None, 1).reason == "missing_or_non_numeric"
    assert validate_coordinates("nan", 1).reason == "missing_or_non_numeric"
    assert validate_coordinates(100, 200).reason == "outside_valid_range"


def test_bbox_and_spatial_group() -> None:
    assert in_bounding_box(52.5, 13.4, 47, 5, 55, 16)
    assert not in_bounding_box(None, 13.4, 47, 5, 55, 16)
    assert spatial_group(52.5, 13.4, 0.1).startswith("grid-")
    with pytest.raises(ValueError):
        spatial_group(52.5, 13.4, 0)


def test_geohash_validation() -> None:
    with pytest.raises(ValueError, match="precision"):
        geohash(52.5, 13.4, 0)
    with pytest.raises(ValueError, match="valid"):
        geohash(100, 13.4)


def test_coordinate_frame_handles_missing_and_swap() -> None:
    frame = pl.DataFrame({"lat": [52.5, 120.0, None], "lon": [13.4, 52.0, 10.0]})
    result = validate_coordinate_frame(frame, "lat", "lon")
    assert result["coordinates_valid"].to_list() == [True, True, False]
    assert result["coordinates_swapped"].to_list() == [False, True, False]
    with pytest.raises(ValueError, match="not found"):
        validate_coordinate_frame(frame, "missing", "lon")
