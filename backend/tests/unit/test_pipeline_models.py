from __future__ import annotations

import pytest
from pydantic import ValidationError

from geoforge.models.pipeline import PipelineDefinition, pipeline_from_yaml, pipeline_to_yaml

VALID_PIPELINE = """
name: Cleanup
version: 1
steps:
  - id: load
    type: load_dataset
    name: Load
    config: {}
  - id: trim
    type: trim_whitespace
    name: Trim
    config:
      columns: [street]
edges:
  - id: e1
    source: load
    target: trim
"""


def test_yaml_pipeline_is_safe_and_deterministic() -> None:
    pipeline = pipeline_from_yaml(VALID_PIPELINE)
    assert [step.id for step in pipeline.ordered_steps()] == ["load", "trim"]
    assert pipeline_from_yaml(pipeline_to_yaml(pipeline)).checksum == pipeline.checksum


def test_python_yaml_tag_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid pipeline YAML"):
        pipeline_from_yaml("!!python/object/apply:os.system ['whoami']")


def test_yaml_aliases_are_rejected() -> None:
    with pytest.raises(ValueError, match="anchors"):
        pipeline_from_yaml("name: test\nsteps: &steps []\ncopy: *steps")


def test_unknown_step_config_is_rejected() -> None:
    payload = pipeline_from_yaml(VALID_PIPELINE).model_dump()
    payload["steps"][1]["config"]["command"] = "rm"
    with pytest.raises(ValidationError):
        PipelineDefinition.model_validate(payload)


def test_cycles_are_rejected() -> None:
    payload = pipeline_from_yaml(VALID_PIPELINE).model_dump()
    payload["edges"].append({"id": "e2", "source": "trim", "target": "load"})
    with pytest.raises(ValidationError, match="acyclic"):
        PipelineDefinition.model_validate(payload)
