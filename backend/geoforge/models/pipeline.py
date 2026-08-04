from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from geoforge.core.security import sha256_text


class StepType(StrEnum):
    LOAD_DATASET = "load_dataset"
    SELECT_COLUMNS = "select_columns"
    RENAME_COLUMNS = "rename_columns"
    CAST_TYPES = "cast_types"
    NORMALIZE_UNICODE = "normalize_unicode"
    TRIM_WHITESPACE = "trim_whitespace"
    REPLACE_VALUES = "replace_values"
    PARSE_DATES = "parse_dates"
    HANDLE_MISSING = "handle_missing_values"
    NORMALIZE_ADDRESS = "normalize_address"
    VALIDATE_POSTAL_CODE = "validate_postal_code"
    VALIDATE_COORDINATES = "validate_coordinates"
    TRANSFORM_CRS = "transform_crs"
    CALCULATE_DISTANCE = "calculate_distance"
    DETECT_DUPLICATES = "detect_duplicates"
    QUARANTINE_INVALID = "quarantine_invalid_rows"
    FILTER_ROWS = "filter_rows"
    ADD_CALCULATED_COLUMN = "add_calculated_column"
    EXPORT_DATASET = "export_dataset"


class StrictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoadDatasetConfig(StrictConfig):
    dataset_id: str | None = None


class SelectColumnsConfig(StrictConfig):
    columns: list[str] = Field(min_length=1)


class RenameColumnsConfig(StrictConfig):
    mapping: dict[str, str] = Field(min_length=1)


class CastTypesConfig(StrictConfig):
    mapping: dict[str, Literal["string", "integer", "float", "boolean", "date", "datetime"]]
    strict: bool = False


class ColumnListConfig(StrictConfig):
    columns: list[str] = Field(min_length=1)


class ReplaceValuesConfig(StrictConfig):
    columns: list[str] = Field(min_length=1)
    mapping: dict[str, str | int | float | bool | None]


class ParseDatesConfig(StrictConfig):
    columns: list[str] = Field(min_length=1)
    formats: list[str] = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"]


class MissingValuesConfig(StrictConfig):
    columns: list[str] = Field(default_factory=list)
    strategy: Literal["fill", "drop", "forward_fill", "backward_fill"]
    value: str | int | float | bool | None = None


class NormalizeAddressConfig(StrictConfig):
    street_column: str = "street"
    city_column: str = "city"
    postal_code_column: str = "postal_code"
    country_column: str | None = "country"


class ValidatePostalCodeConfig(StrictConfig):
    column: str = "postal_code"
    country: str = "DE"
    output_column: str = "postal_code_valid"


class ValidateCoordinatesConfig(StrictConfig):
    latitude_column: str = "latitude"
    longitude_column: str = "longitude"
    auto_swap: bool = True


class TransformCrsConfig(StrictConfig):
    x_column: str = "longitude"
    y_column: str = "latitude"
    source_crs: str = "EPSG:4326"
    target_crs: str = "EPSG:25832"
    output_x_column: str = "easting"
    output_y_column: str = "northing"


class CalculateDistanceConfig(StrictConfig):
    latitude_column: str = "latitude"
    longitude_column: str = "longitude"
    reference_latitude: float = Field(ge=-90, le=90)
    reference_longitude: float = Field(ge=-180, le=180)
    output_column: str = "distance_meters"


class DetectDuplicatesConfig(StrictConfig):
    comparison_columns: list[str] = Field(min_length=1)
    blocking_columns: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)
    minimum_score: float = Field(85, ge=0, le=100)
    review_threshold: float = Field(93, ge=0, le=100)
    maximum_group_size: int = Field(500, ge=2, le=10_000)
    mode: Literal["exact", "normalized", "fuzzy", "weighted"] = "weighted"
    record_id_column: str = "record_id"
    canonical_strategy: Literal["first", "most_complete"] = "most_complete"

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        if self.review_threshold < self.minimum_score:
            raise ValueError("review_threshold must be greater than or equal to minimum_score")
        if self.weights and sum(self.weights.values()) <= 0:
            raise ValueError("weights must have a positive sum")
        return self


class QuarantineConfig(StrictConfig):
    condition: Literal[
        "invalid_postal_code", "invalid_coordinates", "missing_required", "any_validation_error"
    ]
    required_columns: list[str] = Field(default_factory=list)


class FilterRowsConfig(StrictConfig):
    column: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "contains", "in", "is_null"]
    value: Any = None


class CalculatedColumnConfig(StrictConfig):
    output_column: str
    operation: Literal["concat", "coalesce", "lower", "upper", "length"]
    columns: list[str] = Field(min_length=1)
    separator: str = " "


class ExportConfig(StrictConfig):
    format: Literal["csv", "jsonl", "parquet"] = "parquet"
    filename: str = "result"


CONFIG_BY_TYPE: dict[StepType, type[StrictConfig]] = {
    StepType.LOAD_DATASET: LoadDatasetConfig,
    StepType.SELECT_COLUMNS: SelectColumnsConfig,
    StepType.RENAME_COLUMNS: RenameColumnsConfig,
    StepType.CAST_TYPES: CastTypesConfig,
    StepType.NORMALIZE_UNICODE: ColumnListConfig,
    StepType.TRIM_WHITESPACE: ColumnListConfig,
    StepType.REPLACE_VALUES: ReplaceValuesConfig,
    StepType.PARSE_DATES: ParseDatesConfig,
    StepType.HANDLE_MISSING: MissingValuesConfig,
    StepType.NORMALIZE_ADDRESS: NormalizeAddressConfig,
    StepType.VALIDATE_POSTAL_CODE: ValidatePostalCodeConfig,
    StepType.VALIDATE_COORDINATES: ValidateCoordinatesConfig,
    StepType.TRANSFORM_CRS: TransformCrsConfig,
    StepType.CALCULATE_DISTANCE: CalculateDistanceConfig,
    StepType.DETECT_DUPLICATES: DetectDuplicatesConfig,
    StepType.QUARANTINE_INVALID: QuarantineConfig,
    StepType.FILTER_ROWS: FilterRowsConfig,
    StepType.ADD_CALCULATED_COLUMN: CalculatedColumnConfig,
    StepType.EXPORT_DATASET: ExportConfig,
}


class PipelineStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    type: StepType
    name: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, float] | None = None

    @model_validator(mode="after")
    def validate_step_config(self) -> Self:
        validated = CONFIG_BY_TYPE[self.type].model_validate(self.config)
        self.config = validated.model_dump(mode="json")
        return self


class PipelineEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str


class PipelineDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    version: int = Field(default=1, ge=1)
    steps: list[PipelineStep] = Field(min_length=1, max_length=100)
    edges: list[PipelineEdge] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Pipeline step IDs must be unique")
        known = set(ids)
        if any(edge.source not in known or edge.target not in known for edge in self.edges):
            raise ValueError("Pipeline edges must reference existing step IDs")
        if _contains_cycle(known, self.edges):
            raise ValueError("Pipeline graph must be acyclic")
        return self

    @property
    def checksum(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return sha256_text(canonical)

    def ordered_steps(self) -> list[PipelineStep]:
        if not self.edges:
            return self.steps
        by_id = {step.id: step for step in self.steps}
        incoming = {step_id: 0 for step_id in by_id}
        outgoing: dict[str, list[str]] = {step_id: [] for step_id in by_id}
        for edge in self.edges:
            incoming[edge.target] += 1
            outgoing[edge.source].append(edge.target)
        queue = [step.id for step in self.steps if incoming[step.id] == 0]
        result: list[PipelineStep] = []
        while queue:
            step_id = queue.pop(0)
            result.append(by_id[step_id])
            for target in outgoing[step_id]:
                incoming[target] -= 1
                if incoming[target] == 0:
                    queue.append(target)
        return result


def _contains_cycle(nodes: set[str], edges: list[PipelineEdge]) -> bool:
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    for edge in edges:
        adjacency[edge.source].append(edge.target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in adjacency[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in nodes)


def pipeline_from_yaml(yaml_text: str) -> PipelineDefinition:
    if len(yaml_text.encode("utf-8")) > 1_000_000:
        raise ValueError("Pipeline YAML exceeds the 1 MB limit")
    if re.search(r"(^|\s)[&*][A-Za-z0-9_-]+", yaml_text):
        raise ValueError("YAML anchors and aliases are not allowed")
    try:
        payload = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid pipeline YAML: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Pipeline YAML must contain a mapping")
    return PipelineDefinition.model_validate(payload)


def pipeline_to_yaml(definition: PipelineDefinition) -> str:
    return yaml.safe_dump(
        definition.model_dump(mode="json", exclude_none=True),
        sort_keys=False,
        allow_unicode=True,
    )


PipelineDefinitionField = Annotated[PipelineDefinition, Field(description="Validated pipeline DSL")]
