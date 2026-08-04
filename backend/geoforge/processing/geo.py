from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import polars as pl
from pyproj import CRS, Transformer

EARTH_RADIUS_METERS = 6_371_008.8
GEOHASH_ALPHABET = "0123456789bcdefghjkmnpqrstuvwxyz"


@dataclass(frozen=True)
class CoordinateValidation:
    latitude: float | None
    longitude: float | None
    valid: bool
    swapped: bool
    reason: str | None


def _as_finite_float(value: object) -> float | None:
    try:
        converted = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def validate_coordinates(
    latitude: object, longitude: object, *, auto_swap: bool = True
) -> CoordinateValidation:
    lat = _as_finite_float(latitude)
    lon = _as_finite_float(longitude)
    if lat is None or lon is None:
        return CoordinateValidation(lat, lon, False, False, "missing_or_non_numeric")
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return CoordinateValidation(lat, lon, True, False, None)
    if auto_swap and -90 <= lon <= 90 and -180 <= lat <= 180:
        return CoordinateValidation(lon, lat, True, True, "coordinates_swapped")
    return CoordinateValidation(lat, lon, False, False, "outside_valid_range")


def transform_coordinates(
    x: float, y: float, source_crs: str = "EPSG:4326", target_crs: str = "EPSG:25832"
) -> tuple[float, float]:
    source = CRS.from_user_input(source_crs)
    target = CRS.from_user_input(target_crs)
    transformer = Transformer.from_crs(source, target, always_xy=True)
    transformed_x, transformed_y = transformer.transform(x, y)
    if not (math.isfinite(transformed_x) and math.isfinite(transformed_y)):
        raise ValueError("CRS transformation produced non-finite coordinates")
    return transformed_x, transformed_y


def haversine_distance(
    latitude_1: float, longitude_1: float, latitude_2: float, longitude_2: float
) -> float:
    values = validate_coordinates(latitude_1, longitude_1, auto_swap=False)
    other = validate_coordinates(latitude_2, longitude_2, auto_swap=False)
    if not values.valid or not other.valid:
        raise ValueError("Haversine distance requires valid EPSG:4326 coordinates")
    lat_1, lon_1, lat_2, lon_2 = map(
        math.radians, [latitude_1, longitude_1, latitude_2, longitude_2]
    )
    delta_lat = lat_2 - lat_1
    delta_lon = lon_2 - lon_1
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_1) * math.cos(lat_2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def in_bounding_box(
    latitude: object,
    longitude: object,
    min_latitude: float,
    min_longitude: float,
    max_latitude: float,
    max_longitude: float,
) -> bool:
    result = validate_coordinates(latitude, longitude, auto_swap=False)
    return bool(
        result.valid
        and result.latitude is not None
        and result.longitude is not None
        and min_latitude <= result.latitude <= max_latitude
        and min_longitude <= result.longitude <= max_longitude
    )


def geohash(latitude: float, longitude: float, precision: int = 8) -> str:
    if not 1 <= precision <= 12:
        raise ValueError("Geohash precision must be between 1 and 12")
    validation = validate_coordinates(latitude, longitude, auto_swap=False)
    if not validation.valid:
        raise ValueError("Geohash requires valid coordinates")
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    bits = (16, 8, 4, 2, 1)
    bit = 0
    char_index = 0
    even = True
    result: list[str] = []
    while len(result) < precision:
        interval = lon_interval if even else lat_interval
        value = longitude if even else latitude
        midpoint = sum(interval) / 2
        if value >= midpoint:
            char_index |= bits[bit]
            interval[0] = midpoint
        else:
            interval[1] = midpoint
        even = not even
        if bit < 4:
            bit += 1
        else:
            result.append(GEOHASH_ALPHABET[char_index])
            bit = 0
            char_index = 0
    return "".join(result)


def validate_coordinate_frame(
    frame: pl.DataFrame, latitude_column: str, longitude_column: str, auto_swap: bool = True
) -> pl.DataFrame:
    missing = {latitude_column, longitude_column} - set(frame.columns)
    if missing:
        raise ValueError(f"Coordinate columns not found: {', '.join(sorted(missing))}")
    records: list[dict[str, Any]] = []
    for record in frame.to_dicts():
        validation = validate_coordinates(
            record.get(latitude_column), record.get(longitude_column), auto_swap=auto_swap
        )
        records.append(
            {
                **record,
                "latitude_validated": validation.latitude,
                "longitude_validated": validation.longitude,
                "coordinates_valid": validation.valid,
                "coordinates_swapped": validation.swapped,
                "coordinate_issue": validation.reason,
            }
        )
    return pl.DataFrame(records, infer_schema_length=None)


def spatial_group(latitude: float, longitude: float, cell_size_degrees: float = 0.05) -> str:
    validation = validate_coordinates(latitude, longitude, auto_swap=False)
    if not validation.valid or cell_size_degrees <= 0:
        raise ValueError("Spatial grouping requires valid coordinates and positive cell size")
    lat_cell = math.floor((latitude + 90) / cell_size_degrees)
    lon_cell = math.floor((longitude + 180) / cell_size_degrees)
    return f"grid-{lat_cell}-{lon_cell}"
