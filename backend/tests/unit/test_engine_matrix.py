from __future__ import annotations

import time

import polars as pl
import pytest

from geoforge.models.pipeline import PipelineDefinition, PipelineStep, StepType, pipeline_from_yaml
from geoforge.processing.engine import (
    RunCancelledError,
    RunTimeoutError,
    apply_step,
    execute_pipeline,
    metrics_payload,
)


def step(step_type: StepType, config: dict[str, object]) -> PipelineStep:
    return PipelineStep(id="step", type=step_type, name="Test step", config=config)


def test_column_selection_rename_cast_and_missing_strategies() -> None:
    frame = pl.DataFrame({"a": ["1", None, "3"], "b": [" x ", "y", None], "extra": [1, 2, 3]})
    selected, _, _, _ = apply_step(frame, step(StepType.SELECT_COLUMNS, {"columns": ["a", "b"]}))
    assert selected.columns == ["a", "b"]
    renamed, _, _, _ = apply_step(
        selected, step(StepType.RENAME_COLUMNS, {"mapping": {"a": "value"}})
    )
    casted, _, _, _ = apply_step(
        renamed,
        step(StepType.CAST_TYPES, {"mapping": {"value": "integer"}, "strict": False}),
    )
    assert casted["value"].dtype == pl.Int64
    filled, _, _, _ = apply_step(
        casted,
        step(StepType.HANDLE_MISSING, {"columns": ["value"], "strategy": "fill", "value": 0}),
    )
    assert filled["value"].to_list() == [1, 0, 3]
    forward, _, _, _ = apply_step(
        casted,
        step(StepType.HANDLE_MISSING, {"columns": ["value"], "strategy": "forward_fill"}),
    )
    assert forward["value"].to_list() == [1, 1, 3]
    backward, _, _, _ = apply_step(
        casted,
        step(StepType.HANDLE_MISSING, {"columns": ["value"], "strategy": "backward_fill"}),
    )
    assert backward["value"].to_list() == [1, 3, 3]
    dropped, _, _, _ = apply_step(
        casted,
        step(StepType.HANDLE_MISSING, {"columns": ["value"], "strategy": "drop"}),
    )
    assert dropped.height == 2


def test_text_replace_and_date_steps() -> None:
    frame = pl.DataFrame(
        {"text": ["  Mu\x00ller  ", " old "], "date": ["2024-01-02", "03.02.2024"]}
    )
    normalized, _, _, _ = apply_step(frame, step(StepType.NORMALIZE_UNICODE, {"columns": ["text"]}))
    trimmed, _, _, _ = apply_step(normalized, step(StepType.TRIM_WHITESPACE, {"columns": ["text"]}))
    assert trimmed["text"][0] == "Mu ller"
    replaced, _, _, _ = apply_step(
        trimmed,
        step(
            StepType.REPLACE_VALUES,
            {"columns": ["text"], "mapping": {"old": "new"}},
        ),
    )
    assert "new" in replaced["text"].to_list()
    parsed, _, _, _ = apply_step(
        replaced,
        step(
            StepType.PARSE_DATES,
            {"columns": ["date"], "formats": ["%Y-%m-%d", "%d.%m.%Y"]},
        ),
    )
    assert parsed["date"].dtype == pl.Date


def test_validation_crs_distance_and_dedup_steps() -> None:
    frame = pl.DataFrame(
        {
            "record_id": ["a", "b"],
            "street": ["Teststr. 1", "Teststrasse 1"],
            "city": ["Berlin", "BERLIN"],
            "postal_code": ["10115", "10115"],
            "latitude": [52.52, 13.405],
            "longitude": [13.405, 52.52],
        }
    )
    postal, _, _, _ = apply_step(
        frame,
        step(
            StepType.VALIDATE_POSTAL_CODE,
            {"column": "postal_code", "country": "DE", "output_column": "postal_code_valid"},
        ),
    )
    coordinates, _, _, _ = apply_step(
        postal,
        step(
            StepType.VALIDATE_COORDINATES,
            {"latitude_column": "latitude", "longitude_column": "longitude", "auto_swap": True},
        ),
    )
    assert coordinates["coordinates_swapped"].to_list() == [False, False]
    transformed, _, _, _ = apply_step(
        coordinates,
        step(
            StepType.TRANSFORM_CRS,
            {
                "x_column": "longitude_validated",
                "y_column": "latitude_validated",
                "source_crs": "EPSG:4326",
                "target_crs": "EPSG:25832",
                "output_x_column": "easting",
                "output_y_column": "northing",
            },
        ),
    )
    assert transformed["easting"].null_count() == 0
    distance, _, _, _ = apply_step(
        transformed,
        step(
            StepType.CALCULATE_DISTANCE,
            {
                "latitude_column": "latitude_validated",
                "longitude_column": "longitude_validated",
                "reference_latitude": 52.52,
                "reference_longitude": 13.405,
                "output_column": "distance",
            },
        ),
    )
    assert distance["distance"][0] == 0
    duplicates, _, warnings, count = apply_step(
        distance,
        step(
            StepType.DETECT_DUPLICATES,
            {
                "comparison_columns": ["street", "postal_code", "city"],
                "blocking_columns": ["postal_code"],
                "minimum_score": 70,
                "review_threshold": 95,
                "maximum_group_size": 500,
                "mode": "weighted",
                "record_id_column": "record_id",
                "canonical_strategy": "first",
            },
        ),
    )
    assert not warnings
    assert count == 2
    assert duplicates["duplicate_group_id"].null_count() == 0


@pytest.mark.parametrize(
    ("operator", "value", "expected"),
    [
        ("eq", 2, [2]),
        ("ne", 2, [1, 3]),
        ("gt", 1, [2, 3]),
        ("gte", 2, [2, 3]),
        ("lt", 3, [1, 2]),
        ("lte", 2, [1, 2]),
        ("in", [1, 3], [1, 3]),
    ],
)
def test_filter_operators(operator: str, value: object, expected: list[int]) -> None:
    output, _, _, _ = apply_step(
        pl.DataFrame({"value": [1, 2, 3]}),
        step(StepType.FILTER_ROWS, {"column": "value", "operator": operator, "value": value}),
    )
    assert output["value"].to_list() == expected


def test_filter_string_and_null_operators() -> None:
    frame = pl.DataFrame({"value": ["alpha", "beta", None]})
    contains, _, _, _ = apply_step(
        frame,
        step(StepType.FILTER_ROWS, {"column": "value", "operator": "contains", "value": "ph"}),
    )
    assert contains.height == 1
    nulls, _, _, _ = apply_step(
        frame, step(StepType.FILTER_ROWS, {"column": "value", "operator": "is_null"})
    )
    assert nulls.height == 1


@pytest.mark.parametrize(
    ("operation", "columns", "expected"),
    [
        ("concat", ["a", "b"], "Hello World"),
        ("coalesce", ["missing", "a"], "Hello"),
        ("lower", ["a"], "hello"),
        ("upper", ["a"], "HELLO"),
        ("length", ["a"], 5),
    ],
)
def test_calculated_column_operations(operation: str, columns: list[str], expected: object) -> None:
    frame = pl.DataFrame({"a": ["Hello"], "b": ["World"], "missing": [None]})
    output, _, _, _ = apply_step(
        frame,
        step(
            StepType.ADD_CALCULATED_COLUMN,
            {
                "output_column": "result",
                "operation": operation,
                "columns": columns,
                "separator": " ",
            },
        ),
    )
    assert output["result"][0] == expected


def test_all_quarantine_conditions() -> None:
    frame = pl.DataFrame(
        {
            "postal_code_valid": [True, False],
            "coordinates_valid": [False, True],
            "required": ["value", None],
        }
    )
    for condition in ("invalid_postal_code", "invalid_coordinates", "any_validation_error"):
        output, quarantine, _, _ = apply_step(
            frame,
            step(
                StepType.QUARANTINE_INVALID,
                {"condition": condition, "required_columns": []},
            ),
        )
        expected_quarantine = 2 if condition == "any_validation_error" else 1
        assert output.height == 2 - expected_quarantine
        assert quarantine is not None and quarantine.height == expected_quarantine
    _, required, _, _ = apply_step(
        frame,
        step(
            StepType.QUARANTINE_INVALID,
            {"condition": "missing_required", "required_columns": ["required"]},
        ),
    )
    assert required is not None and required.height == 1


def test_passthrough_disabled_cancellation_timeout_and_metrics() -> None:
    frame = pl.DataFrame({"value": [1]})
    passthrough, _, _, _ = apply_step(frame, step(StepType.LOAD_DATASET, {}))
    assert passthrough.equals(frame)
    definition = PipelineDefinition(
        name="Disabled",
        steps=[
            PipelineStep(
                id="disabled",
                type=StepType.FILTER_ROWS,
                name="Disabled",
                enabled=False,
                config={"column": "value", "operator": "eq", "value": 0},
            )
        ],
    )
    assert execute_pipeline(frame, definition).frame.equals(frame)
    active = pipeline_from_yaml(
        """name: Active
steps:
  - id: export
    type: export_dataset
    name: Export
    config: {format: csv, filename: result}
"""
    )
    with pytest.raises(RunCancelledError):
        execute_pipeline(frame, active, cancel_check=lambda: True)
    with pytest.raises(RunTimeoutError):
        execute_pipeline(frame, active, timeout_seconds=-1)
    measured = execute_pipeline(frame, active)
    assert metrics_payload(measured.step_metrics)[0]["step_type"] == "export_dataset"
    assert time.perf_counter() > 0


def test_missing_columns_and_invalid_quarantine_are_isolated() -> None:
    frame = pl.DataFrame({"value": [1]})
    with pytest.raises(ValueError, match="Columns not found"):
        apply_step(frame, step(StepType.SELECT_COLUMNS, {"columns": ["missing"]}))
    with pytest.raises(ValueError, match="postal_code_valid"):
        apply_step(
            frame,
            step(
                StepType.QUARANTINE_INVALID,
                {"condition": "invalid_postal_code", "required_columns": []},
            ),
        )
