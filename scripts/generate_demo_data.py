#!/usr/bin/env python3
"""Generate deterministic, entirely synthetic address and coordinate data."""

from __future__ import annotations

import argparse
import random
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OutputFormat = Literal["csv", "parquet", "jsonl"]
STREETS = [
    "Datenstraße",
    "Pipelineweg",
    "Vektorallee",
    "Qualitätsring",
    "Schemaweg",
    "Koordinatenplatz",
    "Prüfsummenstraße",
    "Spaltenweg",
]
CITIES = ["Nordhafen", "Südwinkel", "Westbogen", "Ostfeld", "Datenheim", "Vektorstetten"]
STREET_VARIANTS = ["{name}", "{name_no_sz}", "{name_short}", "  {name}  "]
DATE_FORMATS = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"]


def _street_variant(street: str, rng: random.Random) -> str:
    short = street.replace("straße", "str.").replace("Straße", "Str.")
    no_sz = street.replace("ß", "ss")
    template = rng.choice(STREET_VARIANTS)
    value = template.format(name=street, name_no_sz=no_sz, name_short=short)
    return unicodedata.normalize("NFD", value) if rng.random() < 0.03 else value


def generate_frame(
    rows: int,
    seed: int = 42,
    error_rate: float = 0.08,
    duplicate_rate: float = 0.06,
) -> pl.DataFrame:
    if rows < 1:
        raise ValueError("rows must be at least 1")
    if not 0 <= error_rate <= 1 or not 0 <= duplicate_rate <= 1:
        raise ValueError("error-rate and duplicate-rate must be between 0 and 1")
    rng = random.Random(seed)  # noqa: S311 - deterministic fixtures, not security
    records: list[dict[str, object]] = []
    start_date = date(2020, 1, 1)
    for index in range(rows):
        duplicate = index > 0 and rng.random() < duplicate_rate
        if duplicate:
            source = dict(records[rng.randrange(max(0, index - 500), index)])
            source["record_id"] = f"syn-{index:09d}"
            source["source_row"] = index
            if rng.random() < 0.5:
                source["street"] = str(source["street"]).replace("straße", "strasse") + " "
                source["city"] = str(source["city"]).upper()
            records.append(source)
            continue
        street = rng.choice(STREETS)
        city = rng.choice(CITIES)
        postal_code = f"{10000 + (index * 7919) % 80000:05d}"
        latitude = 47.3 + rng.random() * 7.6
        longitude = 5.8 + rng.random() * 9.2
        event_date = start_date + timedelta(days=index % 2000)
        house_suffix = chr(65 + index % 4) if index % 7 == 0 else ""
        street_value = f"{_street_variant(street, rng)} {1 + index % 220}{house_suffix}"
        record: dict[str, object] = {
            "record_id": f"syn-{index:09d}",
            "source_row": index,
            "street": street_value,
            "city": f" {city} " if index % 9 == 0 else city,
            "postal_code": postal_code,
            "country": rng.choice(["DE", "deu", "Deutschland", "D"]),
            "latitude": round(latitude, 7),
            "longitude": round(longitude, 7),
            "event_date": event_date.strftime(rng.choice(DATE_FORMATS)),
            "category": f"segment-{index % 12:02d}",
            "quality_note": "synthetic-normal",
        }
        if rng.random() < error_rate:
            error_kind = rng.randrange(7)
            if error_kind == 0:
                record["postal_code"] = rng.choice(["12", "ABCDE", "999999", None])
            elif error_kind == 1:
                record["latitude"] = rng.choice([120.0, -100.0, "not-a-number", None])
            elif error_kind == 2:
                record["latitude"], record["longitude"] = record["longitude"], record["latitude"]
            elif error_kind == 3:
                record["longitude"] = rng.choice([200.0, -220.0, None])
            elif error_kind == 4:
                record["city"] = None
            elif error_kind == 5:
                record["street"] = f"\x00\t{record['street']}  , "
            else:
                record["event_date"] = "31-31-not-a-date"
            record["quality_note"] = "synthetic-error"
        if index % 997 == 0:
            record["quality_note"] = rng.choice(["=1+1", "+SUM(A1:A2)", "@synthetic", "-2+3"])
        records.append(record)
    return pl.DataFrame(records, infer_schema_length=None)


def write_frame(frame: pl.DataFrame, output: Path, output_format: OutputFormat) -> None:
    resolved = output.resolve()
    if not resolved.is_relative_to(PROJECT_ROOT):
        raise ValueError("Demo output must stay inside the GeoForge Studio repository")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "csv":
        frame.write_csv(resolved)
    elif output_format == "parquet":
        frame.write_parquet(resolved, compression="zstd")
    else:
        frame.write_ndjson(resolved)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/samples/geoforge-demo.csv"))
    parser.add_argument("--format", choices=("csv", "parquet", "jsonl"), default="csv")
    parser.add_argument("--error-rate", type=float, default=0.08)
    parser.add_argument("--duplicate-rate", type=float, default=0.06)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    demo = generate_frame(
        arguments.rows, arguments.seed, arguments.error_rate, arguments.duplicate_rate
    )
    write_frame(demo, arguments.output, arguments.format)
    print(
        f"Generated {demo.height} synthetic rows at {arguments.output} "
        f"({arguments.format}, seed={arguments.seed})"
    )
