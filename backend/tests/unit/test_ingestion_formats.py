from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest
from openpyxl import Workbook

from geoforge.processing.ingestion import (
    detect_text_format,
    read_dataset,
    safe_preview,
    schema_payload,
)


def test_csv_encoding_and_delimiter_detection(tmp_path: Path) -> None:
    path = tmp_path / "data.csv"
    path.write_bytes("city;value\nKöln;1\n".encode("cp1252"))
    encoding, delimiter = detect_text_format(path)
    assert encoding
    assert delimiter == ";"
    frame, detected, detected_delimiter = read_dataset(path, "csv")
    assert frame["city"][0] == "Köln"
    assert detected == encoding
    assert detected_delimiter == ";"


def test_csv_preserves_mixed_date_formats_for_explicit_pipeline_parsing(tmp_path: Path) -> None:
    path = tmp_path / "mixed-dates.csv"
    path.write_text("date\n2025-02-01\n02/03/2025\n", encoding="utf-8")

    frame, _, _ = read_dataset(path, "csv")

    assert frame.schema["date"] == pl.String
    assert frame["date"].to_list() == ["2025-02-01", "02/03/2025"]


def test_json_jsonl_and_parquet_formats(tmp_path: Path) -> None:
    records = [{"a": 1}, {"a": 2}]
    json_path = tmp_path / "data.json"
    json_path.write_text(json.dumps({"records": records}), encoding="utf-8")
    jsonl_path = tmp_path / "data.jsonl"
    jsonl_path.write_text("\n".join(json.dumps(item) for item in records), encoding="utf-8")
    parquet_path = tmp_path / "data.parquet"
    pl.DataFrame(records).write_parquet(parquet_path)
    assert read_dataset(json_path, "json")[0].height == 2
    assert read_dataset(jsonl_path, "jsonl")[0].height == 2
    assert read_dataset(parquet_path, "parquet")[0].height == 2


def test_xlsx_format_and_empty_workbook_error(tmp_path: Path) -> None:
    path = tmp_path / "data.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["name", "value"])
    sheet.append(["synthetic", 1])
    workbook.save(path)
    assert read_dataset(path, "xlsx")[0].to_dicts() == [{"name": "synthetic", "value": 1}]

    empty = tmp_path / "empty.xlsx"
    empty_book = Workbook()
    empty_book.save(empty)
    with pytest.raises(ValueError, match="empty"):
        read_dataset(empty, "xlsx")


def test_invalid_json_shape_and_unknown_format(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text('"scalar"', encoding="utf-8")
    with pytest.raises(ValueError, match="array"):
        read_dataset(path, "json")
    with pytest.raises(ValueError, match="Unsupported"):
        read_dataset(path, "xml")


def test_schema_and_preview_are_json_safe() -> None:
    frame = pl.DataFrame({"value": [1, 2]})
    assert schema_payload(frame) == {"value": "Int64"}
    assert safe_preview(frame, 1) == [{"value": 1}]
