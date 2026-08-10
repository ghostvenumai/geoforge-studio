#!/usr/bin/env python3
"""Generate deterministic, entirely synthetic themed demo datasets.

Complements ``generate_demo_data.py`` with domain-specific fixtures that show
different sides of GeoForge Studio:

- ``security``  - hostile-looking but harmless payloads (spreadsheet formulas,
  control characters, traversal strings, oversized values) that demonstrate
  sanitization, quarantine and CSV formula-injection escaping.
- ``marketing`` - CRM/lead records with campaigns, channels, consent flags and
  messy e-mail addresses for deduplication and quality demos.
- ``ecommerce`` - order records with locale-formatted amounts, currency
  variants and delivery addresses.
- ``logistics`` - shipment records with delivery coordinates, weights and
  carrier data for geo validation and distance workflows.

All themes keep the canonical address/geo columns (``street``, ``city``,
``postal_code``, ``country``, ``latitude``, ``longitude``, ``record_id``) so
the seeded example pipelines run on them without reconfiguration.
"""

from __future__ import annotations

import argparse
import random
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import polars as pl

from scripts.generate_demo_data import CITIES, DATE_FORMATS, STREETS, _street_variant

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OutputFormat = Literal["csv", "parquet", "jsonl"]

FIRST_NAMES = ["Alex", "Kim", "Robin", "Sascha", "Toni", "Chris", "Nika", "Luca"]
LAST_NAMES = ["Beispiel", "Muster", "Testmann", "Datenberg", "Synthetik", "Demoholz"]
COMPANIES = [
    "Beispiel GmbH",
    "Muster AG",
    "Synthetika KG",
    "Datenwerk e.K.",
    "Demo Solutions GmbH",
    "Testfabrik UG",
]
CHANNELS = ["email", "social", "search", "event", "referral", "newsletter"]
CAMPAIGNS = [f"kampagne-{year}-q{quarter}" for year in (2024, 2025) for quarter in (1, 2, 3, 4)]
CONSENT_VALUES = ["yes", "no", "1", "0", "true", "false", "JA", "nein", None]
CARRIERS = ["SynthExpress", "DemoLogistik", "Musterfracht", "Beispielkurier"]
ORDER_STATUS = ["neu", "bezahlt", "versendet", "storniert", "retourniert"]
CURRENCIES = ["EUR", "eur", "€", "Euro"]

# Classic, harmless demo payloads that must never execute anywhere: they show
# formula escaping on export, control-character cleanup and path containment.
FORMULA_PAYLOADS = ["=1+1", "+SUM(A1:A2)", "@synthetic", "-2+3", '=HYPERLINK("x")']
TRAVERSAL_PAYLOADS = ["../../etc/passwd", "..\\..\\windows\\system32", "%2e%2e%2fdemo"]
MARKUP_PAYLOADS = ["<script>alert('synthetic')</script>", "<img src=x onerror=demo>", "{{7*7}}"]


def _email(rng: random.Random, index: int, messy: bool) -> str | None:
    first = rng.choice(FIRST_NAMES).lower()
    last = rng.choice(LAST_NAMES).lower()
    clean = f"{first}.{last}{index % 97}@example.invalid"
    if not messy:
        return clean
    return rng.choice(
        [
            clean.upper(),
            f" {clean} ",
            clean.replace("@", "(at)"),
            f"{first}.{last}@",
            "keine-angabe",
            None,
        ]
    )


def _address_block(index: int, rng: random.Random) -> dict[str, object]:
    street = rng.choice(STREETS)
    return {
        "street": f"{_street_variant(street, rng)} {1 + index % 220}",
        "city": f" {rng.choice(CITIES)} " if index % 9 == 0 else rng.choice(CITIES),
        "postal_code": f"{10000 + (index * 7919) % 80000:05d}",
        "country": rng.choice(["DE", "deu", "Deutschland", "D"]),
        "latitude": round(47.3 + rng.random() * 7.6, 7),
        "longitude": round(5.8 + rng.random() * 9.2, 7),
    }


def _inject_geo_errors(record: dict[str, object], rng: random.Random) -> None:
    error_kind = rng.randrange(5)
    if error_kind == 0:
        record["postal_code"] = rng.choice(["12", "ABCDE", "999999", None])
    elif error_kind == 1:
        record["latitude"] = rng.choice([120.0, -100.0, "not-a-number", None])
    elif error_kind == 2:
        record["latitude"], record["longitude"] = record["longitude"], record["latitude"]
    elif error_kind == 3:
        record["longitude"] = rng.choice([200.0, -220.0, None])
    else:
        record["city"] = None


def _marketing_row(index: int, rng: random.Random, error: bool) -> dict[str, object]:
    signup = date(2024, 1, 1) + timedelta(days=index % 600)
    record: dict[str, object] = {
        **_address_block(index, rng),
        "full_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        "email": _email(rng, index, messy=error),
        "company": rng.choice(COMPANIES),
        "campaign": rng.choice(CAMPAIGNS),
        "channel": rng.choice(CHANNELS),
        "utm_source": rng.choice(["synth_ads", "synth_mail", "synth_social", None]),
        "consent": rng.choice(CONSENT_VALUES),
        "lead_score": rng.randint(0, 100) if not error else rng.choice([-5, 250, None, "hoch"]),
        "signup_date": signup.strftime(rng.choice(DATE_FORMATS)),
    }
    if error:
        _inject_geo_errors(record, rng)
    return record


def _security_row(index: int, rng: random.Random, error: bool) -> dict[str, object]:
    record: dict[str, object] = {
        **_address_block(index, rng),
        "note": "synthetic-clean",
        "source_file": f"import-{index % 40:02d}.csv",
        "comment": "unauffaellig",
    }
    if error:
        payload_kind = rng.randrange(5)
        if payload_kind == 0:
            record["note"] = rng.choice(FORMULA_PAYLOADS)
        elif payload_kind == 1:
            record["comment"] = rng.choice(MARKUP_PAYLOADS)
        elif payload_kind == 2:
            record["source_file"] = rng.choice(TRAVERSAL_PAYLOADS)
        elif payload_kind == 3:
            record["street"] = f"\x00\t{record['street']}\x1b[0m  , "
        else:
            record["comment"] = "A" * 4096
        _inject_geo_errors(record, rng)
    return record


def _ecommerce_row(index: int, rng: random.Random, error: bool) -> dict[str, object]:
    order_date = date(2024, 6, 1) + timedelta(days=index % 400)
    amount: object = round(rng.uniform(5, 900), 2)
    if error:
        amount = rng.choice(["1.234,56", "-12.50", "n/a", None, "99,90 EUR"])
    record: dict[str, object] = {
        **_address_block(index, rng),
        "order_number": f"ORD-{2024000 + index}",
        "customer": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
        "amount": amount,
        "currency": rng.choice(CURRENCIES),
        "status": rng.choice(ORDER_STATUS),
        "items": rng.randint(1, 12),
        "order_date": order_date.strftime(rng.choice(DATE_FORMATS)),
    }
    if error:
        _inject_geo_errors(record, rng)
    return record


def _logistics_row(index: int, rng: random.Random, error: bool) -> dict[str, object]:
    dispatch = date(2025, 1, 1) + timedelta(days=index % 300)
    weight: object = round(rng.uniform(0.1, 800.0), 2)
    if error:
        weight = rng.choice([-4.0, 100000.0, "schwer", None])
    record: dict[str, object] = {
        **_address_block(index, rng),
        "shipment_number": f"SHP-{500000 + index}",
        "carrier": rng.choice(CARRIERS),
        "weight_kg": weight,
        "status": rng.choice(["angekuendigt", "unterwegs", "zugestellt", "verloren"]),
        "dispatch_date": dispatch.strftime(rng.choice(DATE_FORMATS)),
    }
    if error:
        _inject_geo_errors(record, rng)
    return record


THEME_BUILDERS: dict[str, Callable[[int, random.Random, bool], dict[str, object]]] = {
    "security": _security_row,
    "marketing": _marketing_row,
    "ecommerce": _ecommerce_row,
    "logistics": _logistics_row,
}


def generate_theme_frame(
    theme: str,
    rows: int,
    seed: int = 42,
    error_rate: float = 0.12,
    duplicate_rate: float = 0.08,
) -> pl.DataFrame:
    if theme not in THEME_BUILDERS:
        raise ValueError(f"unknown theme: {theme}")
    if rows < 1:
        raise ValueError("rows must be at least 1")
    if not 0 <= error_rate <= 1 or not 0 <= duplicate_rate <= 1:
        raise ValueError("error-rate and duplicate-rate must be between 0 and 1")
    build_row = THEME_BUILDERS[theme]
    rng = random.Random(seed)  # noqa: S311 - deterministic fixtures, not security
    records: list[dict[str, object]] = []
    for index in range(rows):
        if index > 0 and rng.random() < duplicate_rate:
            source = dict(records[rng.randrange(max(0, index - 500), index)])
            source["record_id"] = f"{theme[:3]}-{index:09d}"
            source["source_row"] = index
            if rng.random() < 0.5:
                source["street"] = str(source["street"]).replace("straße", "strasse") + " "
                source["city"] = str(source["city"]).upper()
            records.append(source)
            continue
        error = rng.random() < error_rate
        record: dict[str, object] = {
            "record_id": f"{theme[:3]}-{index:09d}",
            "source_row": index,
            **build_row(index, rng, error),
            "quality_note": "synthetic-error" if error else "synthetic-normal",
        }
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
    parser.add_argument("--theme", choices=(*THEME_BUILDERS, "all"), default="all")
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=Path("data/samples"))
    parser.add_argument("--format", choices=("csv", "parquet", "jsonl"), default="csv")
    parser.add_argument("--error-rate", type=float, default=0.12)
    parser.add_argument("--duplicate-rate", type=float, default=0.08)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    themes = list(THEME_BUILDERS) if arguments.theme == "all" else [arguments.theme]
    for theme_name in themes:
        frame = generate_theme_frame(
            theme_name,
            arguments.rows,
            arguments.seed,
            arguments.error_rate,
            arguments.duplicate_rate,
        )
        suffix = "csv" if arguments.format == "csv" else arguments.format
        target = arguments.output_dir / f"geoforge-demo-{theme_name}.{suffix}"
        write_frame(frame, target, arguments.format)
        print(
            f"Generated {frame.height} synthetic {theme_name} rows at {target} "
            f"({arguments.format}, seed={arguments.seed})"
        )
