from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from geoforge.db.models import Pipeline
from geoforge.models.pipeline import PipelineDefinition, pipeline_from_yaml, pipeline_to_yaml

EXAMPLE_PIPELINES = [
    """name: German Address Cleanup
description: Normalize German address fields and quarantine invalid postal codes.
version: 1
steps:
  - id: load
    type: load_dataset
    name: Load dataset
    config: {}
  - id: address
    type: normalize_address
    name: Normalize address
    config:
      street_column: street
      city_column: city
      postal_code_column: postal_code
      country_column: country
  - id: quarantine
    type: quarantine_invalid_rows
    name: Quarantine invalid postal codes
    config:
      condition: invalid_postal_code
      required_columns: []
  - id: export
    type: export_dataset
    name: Export result
    config:
      format: parquet
      filename: german-address-cleanup
edges:
  - {id: e1, source: load, target: address}
  - {id: e2, source: address, target: quarantine}
  - {id: e3, source: quarantine, target: export}
""",
    """name: Coordinate Validation and Transformation
description: Validate WGS84 coordinates, repair swaps, and transform to ETRS89 / UTM 32N.
version: 1
steps:
  - id: load
    type: load_dataset
    name: Load dataset
    config: {}
  - id: validate
    type: validate_coordinates
    name: Validate coordinates
    config:
      latitude_column: latitude
      longitude_column: longitude
      auto_swap: true
  - id: transform
    type: transform_crs
    name: Transform to EPSG 25832
    config:
      x_column: longitude_validated
      y_column: latitude_validated
      source_crs: EPSG:4326
      target_crs: EPSG:25832
      output_x_column: easting
      output_y_column: northing
  - id: quarantine
    type: quarantine_invalid_rows
    name: Quarantine invalid coordinates
    config:
      condition: invalid_coordinates
      required_columns: []
  - id: export
    type: export_dataset
    name: Export result
    config: {format: parquet, filename: coordinate-validation}
""",
    """name: Full Data Quality and Deduplication
description: >-
  Normalize addresses, validate coordinates, detect blocked fuzzy duplicates,
  and quarantine invalid rows.
version: 1
steps:
  - id: load
    type: load_dataset
    name: Load dataset
    config: {}
  - id: address
    type: normalize_address
    name: Normalize address
    config:
      street_column: street
      city_column: city
      postal_code_column: postal_code
      country_column: country
  - id: coordinates
    type: validate_coordinates
    name: Validate coordinates
    config: {latitude_column: latitude, longitude_column: longitude, auto_swap: true}
  - id: duplicates
    type: detect_duplicates
    name: Detect duplicates
    config:
      comparison_columns: [street_normalized, postal_code_normalized, city_normalized]
      blocking_columns: [postal_code_normalized]
      weights: {street_normalized: 0.5, postal_code_normalized: 0.3, city_normalized: 0.2}
      minimum_score: 82
      review_threshold: 94
      maximum_group_size: 500
      mode: weighted
      record_id_column: record_id
      canonical_strategy: most_complete
  - id: quarantine
    type: quarantine_invalid_rows
    name: Quarantine invalid values
    config: {condition: any_validation_error, required_columns: []}
  - id: export
    type: export_dataset
    name: Export result
    config: {format: parquet, filename: full-quality}
""",
]


def create_pipeline(
    db: Session, definition: PipelineDefinition, yaml_text: str | None = None
) -> Pipeline:
    pipeline = Pipeline(
        id=uuid.uuid4().hex,
        name=definition.name,
        description=definition.description,
        version=definition.version,
        yaml_text=yaml_text or pipeline_to_yaml(definition),
        definition_json=definition.model_dump(mode="json"),
        checksum=definition.checksum,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


def seed_example_pipelines(db: Session) -> None:
    existing_names = set(db.scalars(select(Pipeline.name)))
    for yaml_text in EXAMPLE_PIPELINES:
        definition = pipeline_from_yaml(yaml_text)
        if definition.name not in existing_names:
            create_pipeline(db, definition, yaml_text)
