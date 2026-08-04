from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

import polars as pl

from geoforge.models.pipeline import (
    CalculatedColumnConfig,
    CalculateDistanceConfig,
    CastTypesConfig,
    ColumnListConfig,
    DetectDuplicatesConfig,
    FilterRowsConfig,
    MissingValuesConfig,
    NormalizeAddressConfig,
    ParseDatesConfig,
    PipelineDefinition,
    PipelineStep,
    QuarantineConfig,
    RenameColumnsConfig,
    ReplaceValuesConfig,
    SelectColumnsConfig,
    StepType,
    TransformCrsConfig,
    ValidateCoordinatesConfig,
    ValidatePostalCodeConfig,
)
from geoforge.processing.address import (
    normalize_address_frame,
    normalize_unicode,
    validate_postal_code,
)
from geoforge.processing.dedup import DeduplicationConfig, detect_duplicates
from geoforge.processing.geo import (
    haversine_distance,
    transform_coordinates,
    validate_coordinate_frame,
)


class RunCancelledError(RuntimeError):
    pass


class RunTimeoutError(TimeoutError):
    pass


@dataclass
class StepMetric:
    step_id: str
    step_type: str
    name: str
    duration_seconds: float
    input_rows: int
    output_rows: int
    changed_rows: int
    quarantined_rows: int
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class PipelineExecutionResult:
    frame: pl.DataFrame
    quarantine: pl.DataFrame
    step_metrics: list[StepMetric]
    warnings: list[str]
    duplicate_count: int


def _require_columns(frame: pl.DataFrame, columns: list[str]) -> None:
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"Columns not found: {', '.join(sorted(missing))}")


def _changed_rows(before: pl.DataFrame, after: pl.DataFrame) -> int:
    if before.columns == after.columns and before.height == after.height:
        return int((before.hash_rows() != after.hash_rows()).sum())
    return max(before.height, after.height)


def _cast_types(frame: pl.DataFrame, config: CastTypesConfig) -> pl.DataFrame:
    type_map: dict[str, Any] = {
        "string": pl.String,
        "integer": pl.Int64,
        "float": pl.Float64,
        "boolean": pl.Boolean,
        "date": pl.Date,
        "datetime": pl.Datetime,
    }
    _require_columns(frame, list(config.mapping))
    return frame.with_columns(
        [
            pl.col(column).cast(type_map[dtype], strict=config.strict)
            for column, dtype in config.mapping.items()
        ]
    )


def _parse_dates(frame: pl.DataFrame, config: ParseDatesConfig) -> pl.DataFrame:
    _require_columns(frame, config.columns)
    expressions: list[pl.Expr] = []
    for column in config.columns:
        parsed = [
            pl.col(column).cast(pl.String).str.strptime(pl.Date, fmt, strict=False)
            for fmt in config.formats
        ]
        expressions.append(pl.coalesce(parsed).alias(column))
    return frame.with_columns(expressions)


def _handle_missing(frame: pl.DataFrame, config: MissingValuesConfig) -> pl.DataFrame:
    columns = config.columns or frame.columns
    _require_columns(frame, columns)
    if config.strategy == "drop":
        return frame.drop_nulls(subset=columns)
    if config.strategy == "forward_fill":
        return frame.with_columns([pl.col(column).forward_fill() for column in columns])
    if config.strategy == "backward_fill":
        return frame.with_columns([pl.col(column).backward_fill() for column in columns])
    return frame.with_columns([pl.col(column).fill_null(config.value) for column in columns])


def _transform_crs(frame: pl.DataFrame, config: TransformCrsConfig) -> pl.DataFrame:
    _require_columns(frame, [config.x_column, config.y_column])
    output_x: list[float | None] = []
    output_y: list[float | None] = []
    for x_value, y_value in zip(
        frame[config.x_column].to_list(), frame[config.y_column].to_list(), strict=True
    ):
        if x_value is None or y_value is None:
            output_x.append(None)
            output_y.append(None)
            continue
        try:
            x_result, y_result = transform_coordinates(
                float(x_value), float(y_value), config.source_crs, config.target_crs
            )
        except (TypeError, ValueError):
            output_x.append(None)
            output_y.append(None)
        else:
            output_x.append(x_result)
            output_y.append(y_result)
    return frame.with_columns(
        pl.Series(config.output_x_column, output_x, dtype=pl.Float64),
        pl.Series(config.output_y_column, output_y, dtype=pl.Float64),
    )


def _calculate_distance(frame: pl.DataFrame, config: CalculateDistanceConfig) -> pl.DataFrame:
    _require_columns(frame, [config.latitude_column, config.longitude_column])
    distances: list[float | None] = []
    for latitude, longitude in zip(
        frame[config.latitude_column].to_list(),
        frame[config.longitude_column].to_list(),
        strict=True,
    ):
        try:
            distances.append(
                haversine_distance(
                    float(latitude),
                    float(longitude),
                    config.reference_latitude,
                    config.reference_longitude,
                )
            )
        except (TypeError, ValueError):
            distances.append(None)
    return frame.with_columns(pl.Series(config.output_column, distances, dtype=pl.Float64))


def _filter_rows(frame: pl.DataFrame, config: FilterRowsConfig) -> pl.DataFrame:
    _require_columns(frame, [config.column])
    column = pl.col(config.column)
    if config.operator == "is_null":
        expression = column.is_null()
    elif config.operator == "contains":
        expression = column.cast(pl.String).str.contains(str(config.value), literal=True)
    elif config.operator == "in":
        values = config.value if isinstance(config.value, list) else [config.value]
        expression = column.is_in(values)
    elif config.operator == "eq":
        expression = column == config.value
    elif config.operator == "ne":
        expression = column != config.value
    elif config.operator == "gt":
        expression = column > config.value
    elif config.operator == "gte":
        expression = column >= config.value
    elif config.operator == "lt":
        expression = column < config.value
    else:
        expression = column <= config.value
    return frame.filter(expression)


def _calculated_column(frame: pl.DataFrame, config: CalculatedColumnConfig) -> pl.DataFrame:
    _require_columns(frame, config.columns)
    if config.operation == "concat":
        expression = pl.concat_str(config.columns, separator=config.separator, ignore_nulls=True)
    elif config.operation == "coalesce":
        expression = pl.coalesce(config.columns)
    elif config.operation == "lower":
        expression = pl.col(config.columns[0]).cast(pl.String).str.to_lowercase()
    elif config.operation == "upper":
        expression = pl.col(config.columns[0]).cast(pl.String).str.to_uppercase()
    else:
        expression = pl.col(config.columns[0]).cast(pl.String).str.len_chars()
    return frame.with_columns(expression.alias(config.output_column))


def _quarantine_mask(frame: pl.DataFrame, config: QuarantineConfig) -> pl.Expr:
    if config.condition == "invalid_postal_code":
        if "postal_code_valid" not in frame.columns:
            raise ValueError("postal_code_valid is required before postal quarantine")
        return ~pl.col("postal_code_valid").fill_null(False)
    if config.condition == "invalid_coordinates":
        if "coordinates_valid" not in frame.columns:
            raise ValueError("coordinates_valid is required before coordinate quarantine")
        return ~pl.col("coordinates_valid").fill_null(False)
    if config.condition == "missing_required":
        _require_columns(frame, config.required_columns)
        mask = pl.lit(False)
        for column in config.required_columns:
            mask = (
                mask
                | pl.col(column).is_null()
                | (pl.col(column).cast(pl.String).str.len_chars() == 0)
            )
        return mask
    available = [
        column for column in ("postal_code_valid", "coordinates_valid") if column in frame.columns
    ]
    if not available:
        raise ValueError("No validation result columns exist for quarantine")
    mask = pl.lit(False)
    for column in available:
        mask = mask | ~pl.col(column).fill_null(False)
    return mask


def apply_step(
    frame: pl.DataFrame, step: PipelineStep
) -> tuple[pl.DataFrame, pl.DataFrame | None, list[str], int]:
    warnings: list[str] = []
    duplicate_count = 0
    if step.type in {StepType.LOAD_DATASET, StepType.EXPORT_DATASET}:
        return frame, None, warnings, duplicate_count
    if step.type == StepType.SELECT_COLUMNS:
        select_config = SelectColumnsConfig.model_validate(step.config)
        _require_columns(frame, select_config.columns)
        return frame.select(select_config.columns), None, warnings, duplicate_count
    if step.type == StepType.RENAME_COLUMNS:
        rename_config = RenameColumnsConfig.model_validate(step.config)
        _require_columns(frame, list(rename_config.mapping))
        return frame.rename(rename_config.mapping), None, warnings, duplicate_count
    if step.type == StepType.CAST_TYPES:
        return _cast_types(frame, CastTypesConfig.model_validate(step.config)), None, warnings, 0
    if step.type in {StepType.NORMALIZE_UNICODE, StepType.TRIM_WHITESPACE}:
        columns_config = ColumnListConfig.model_validate(step.config)
        _require_columns(frame, columns_config.columns)
        expressions = []
        for column in columns_config.columns:
            expression = pl.col(column).cast(pl.String)
            if step.type == StepType.NORMALIZE_UNICODE:
                expression = expression.map_elements(normalize_unicode, return_dtype=pl.String)
            else:
                expression = expression.str.strip_chars().str.replace_all(r"\s+", " ")
            expressions.append(expression.alias(column))
        return frame.with_columns(expressions), None, warnings, 0
    if step.type == StepType.REPLACE_VALUES:
        replace_config = ReplaceValuesConfig.model_validate(step.config)
        _require_columns(frame, replace_config.columns)
        return (
            frame.with_columns(
                [
                    pl.col(column).replace(replace_config.mapping).alias(column)
                    for column in replace_config.columns
                ]
            ),
            None,
            warnings,
            0,
        )
    if step.type == StepType.PARSE_DATES:
        return _parse_dates(frame, ParseDatesConfig.model_validate(step.config)), None, warnings, 0
    if step.type == StepType.HANDLE_MISSING:
        return (
            _handle_missing(frame, MissingValuesConfig.model_validate(step.config)),
            None,
            warnings,
            0,
        )
    if step.type == StepType.NORMALIZE_ADDRESS:
        address_config = NormalizeAddressConfig.model_validate(step.config)
        return (
            normalize_address_frame(
                frame,
                address_config.street_column,
                address_config.city_column,
                address_config.postal_code_column,
                address_config.country_column,
            ),
            None,
            warnings,
            0,
        )
    if step.type == StepType.VALIDATE_POSTAL_CODE:
        postal_config = ValidatePostalCodeConfig.model_validate(step.config)
        _require_columns(frame, [postal_config.column])
        expression = pl.col(postal_config.column).map_elements(
            lambda value: validate_postal_code(value, postal_config.country),
            return_dtype=pl.Boolean,
        )
        return frame.with_columns(expression.alias(postal_config.output_column)), None, warnings, 0
    if step.type == StepType.VALIDATE_COORDINATES:
        coordinate_config = ValidateCoordinatesConfig.model_validate(step.config)
        return (
            validate_coordinate_frame(
                frame,
                coordinate_config.latitude_column,
                coordinate_config.longitude_column,
                coordinate_config.auto_swap,
            ),
            None,
            warnings,
            0,
        )
    if step.type == StepType.TRANSFORM_CRS:
        return (
            _transform_crs(frame, TransformCrsConfig.model_validate(step.config)),
            None,
            warnings,
            0,
        )
    if step.type == StepType.CALCULATE_DISTANCE:
        return (
            _calculate_distance(frame, CalculateDistanceConfig.model_validate(step.config)),
            None,
            warnings,
            0,
        )
    if step.type == StepType.DETECT_DUPLICATES:
        dedup_config = DetectDuplicatesConfig.model_validate(step.config)
        result = detect_duplicates(frame, DeduplicationConfig(**dedup_config.model_dump()))
        if result.skipped_oversized_blocks:
            warnings.append(f"Skipped {result.skipped_oversized_blocks} oversized duplicate blocks")
        return (
            result.frame,
            None,
            warnings,
            int(result.frame["duplicate_group_id"].is_not_null().sum()),
        )
    if step.type == StepType.QUARANTINE_INVALID:
        quarantine_config = QuarantineConfig.model_validate(step.config)
        mask = _quarantine_mask(frame, quarantine_config)
        quarantined = frame.filter(mask).with_columns(
            pl.lit(quarantine_config.condition).alias("quarantine_reason")
        )
        return frame.filter(~mask), quarantined, warnings, 0
    if step.type == StepType.FILTER_ROWS:
        return _filter_rows(frame, FilterRowsConfig.model_validate(step.config)), None, warnings, 0
    if step.type == StepType.ADD_CALCULATED_COLUMN:
        return (
            _calculated_column(frame, CalculatedColumnConfig.model_validate(step.config)),
            None,
            warnings,
            0,
        )
    raise ValueError(f"Unsupported pipeline step: {step.type}")


def execute_pipeline(
    frame: pl.DataFrame,
    definition: PipelineDefinition,
    *,
    cancel_check: Callable[[], bool] | None = None,
    timeout_seconds: float = 900,
) -> PipelineExecutionResult:
    started = time.perf_counter()
    current = frame
    quarantine_frames: list[pl.DataFrame] = []
    metrics: list[StepMetric] = []
    warnings: list[str] = []
    duplicate_count = 0
    for step in definition.ordered_steps():
        if not step.enabled:
            continue
        if cancel_check and cancel_check():
            raise RunCancelledError("Run cancellation requested")
        if time.perf_counter() - started > timeout_seconds:
            raise RunTimeoutError(f"Run exceeded {timeout_seconds:g} seconds")
        step_started = time.perf_counter()
        before = current
        try:
            current, quarantined, step_warnings, step_duplicates = apply_step(current, step)
        except Exception as exc:
            metrics.append(
                StepMetric(
                    step_id=step.id,
                    step_type=step.type,
                    name=step.name,
                    duration_seconds=time.perf_counter() - step_started,
                    input_rows=before.height,
                    output_rows=before.height,
                    changed_rows=0,
                    quarantined_rows=0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            raise
        if quarantined is not None and quarantined.height:
            quarantine_frames.append(quarantined)
        duplicate_count = max(duplicate_count, int(step_duplicates))
        warnings.extend(step_warnings)
        metrics.append(
            StepMetric(
                step_id=step.id,
                step_type=step.type,
                name=step.name,
                duration_seconds=time.perf_counter() - step_started,
                input_rows=before.height,
                output_rows=current.height,
                changed_rows=_changed_rows(before, current),
                quarantined_rows=quarantined.height if quarantined is not None else 0,
                warnings=step_warnings,
            )
        )
    quarantine = (
        pl.concat(quarantine_frames, how="diagonal_relaxed")
        if quarantine_frames
        else pl.DataFrame(schema={**current.schema, "quarantine_reason": pl.String})
    )
    return PipelineExecutionResult(current, quarantine, metrics, warnings, duplicate_count)


def metrics_payload(metrics: list[StepMetric]) -> list[dict[str, Any]]:
    return [
        {**asdict(metric), "duration_seconds": round(metric.duration_seconds, 6)}
        for metric in metrics
    ]
