from __future__ import annotations

import polars as pl

from geoforge.models.pipeline import pipeline_from_yaml
from geoforge.processing.engine import execute_pipeline


def test_pipeline_engine_normalizes_and_quarantines() -> None:
    definition = pipeline_from_yaml(
        """
name: Unit pipeline
steps:
  - id: address
    type: normalize_address
    name: Address
    config:
      street_column: street
      city_column: city
      postal_code_column: postal_code
      country_column: null
  - id: quarantine
    type: quarantine_invalid_rows
    name: Quarantine
    config: {condition: invalid_postal_code, required_columns: []}
"""
    )
    frame = pl.DataFrame(
        {
            "street": ["Teststr. 1", "Other Str. 2"],
            "city": ["berlin", "hamburg"],
            "postal_code": ["10115", "bad"],
        }
    )
    result = execute_pipeline(frame, definition)
    assert result.frame.height == 1
    assert result.quarantine.height == 1
    assert result.frame["street_normalized"][0] == "Teststraße"
    assert result.step_metrics[-1].quarantined_rows == 1


def test_calculated_column_uses_fixed_operator() -> None:
    definition = pipeline_from_yaml(
        """
name: Calculated
steps:
  - id: calculated
    type: add_calculated_column
    name: Full address
    config:
      output_column: full_address
      operation: concat
      columns: [street, city]
      separator: ', '
"""
    )
    result = execute_pipeline(pl.DataFrame({"street": ["A"], "city": ["B"]}), definition)
    assert result.frame["full_address"][0] == "A, B"
