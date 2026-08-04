from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import polars as pl

CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f-\x9f]")
WHITESPACE_PATTERN = re.compile(r"\s+")
PUNCTUATION_PATTERN = re.compile(r"\s*[,;|]+\s*")
STREET_PATTERN = re.compile(r"(?:str\b\.?|strasse\b|straße\b)")
HOUSE_NUMBER_PATTERN = re.compile(
    r"^(?P<street>.*?)[,\s]+(?P<number>\d{1,5}(?:\s*[-/]\s*\d{1,5})?\s*[A-Za-z]?)$"
)
COUNTRY_CODES = {
    "de": "DE",
    "deu": "DE",
    "deutschland": "DE",
    "germany": "DE",
    "at": "AT",
    "aut": "AT",
    "österreich": "AT",
    "austria": "AT",
    "ch": "CH",
    "che": "CH",
    "schweiz": "CH",
    "switzerland": "CH",
    "fr": "FR",
    "france": "FR",
    "nl": "NL",
    "netherlands": "NL",
}


@dataclass(frozen=True)
class StreetParts:
    street: str | None
    house_number: str | None


def normalize_unicode(value: object) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", str(value))
    normalized = CONTROL_PATTERN.sub(" ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return normalized or None


def matching_key(value: object, transliterate: bool = True) -> str:
    normalized = normalize_unicode(value) or ""
    normalized = normalized.casefold().replace("ß", "ss")
    if transliterate:
        normalized = normalized.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    return re.sub(r"[^a-z0-9]", "", normalized)


def normalize_street(value: object) -> str | None:
    normalized = normalize_unicode(value)
    if not normalized:
        return None
    normalized = PUNCTUATION_PATTERN.sub(" ", normalized)
    normalized = STREET_PATTERN.sub("straße", normalized.casefold())
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip(" .,")
    words = [word.capitalize() if word != "straße" else "Straße" for word in normalized.split()]
    return " ".join(words) or None


def split_street_and_house_number(value: object) -> StreetParts:
    normalized = normalize_street(value)
    if not normalized:
        return StreetParts(None, None)
    match = HOUSE_NUMBER_PATTERN.fullmatch(normalized)
    if not match:
        return StreetParts(normalized, None)
    number = re.sub(r"\s+", "", match.group("number")).upper()
    return StreetParts(match.group("street").strip(), number)


def normalize_postal_code(value: object, country: str = "DE") -> str | None:
    normalized = normalize_unicode(value)
    if not normalized:
        return None
    normalized = re.sub(r"^(?:D|DE|A|AT|CH)[-\s]", "", normalized, flags=re.IGNORECASE)
    country = normalize_country_code(country) or "DE"
    if country == "NL":
        compact = re.sub(r"\s+", "", normalized).upper()
        return f"{compact[:4]} {compact[4:]}" if len(compact) == 6 else compact
    return re.sub(r"\D", "", normalized)


def validate_postal_code(value: object, country: str = "DE") -> bool:
    normalized = normalize_postal_code(value, country)
    if normalized is None:
        return False
    code = normalize_country_code(country) or "DE"
    patterns = {
        "DE": r"\d{5}",
        "AT": r"\d{4}",
        "CH": r"\d{4}",
        "FR": r"\d{5}",
        "NL": r"\d{4} [A-Z]{2}",
    }
    return re.fullmatch(patterns.get(code, r"[A-Z0-9 -]{3,10}"), normalized) is not None


def normalize_city(value: object) -> str | None:
    normalized = normalize_unicode(value)
    if not normalized:
        return None
    normalized = PUNCTUATION_PATTERN.sub(" ", normalized).strip(" .,")
    return " ".join(part.capitalize() for part in normalized.split())


def normalize_country_code(value: object) -> str | None:
    normalized = normalize_unicode(value)
    if not normalized:
        return None
    key = normalized.casefold().strip(" .")
    return COUNTRY_CODES.get(key, key.upper()[:2] if len(key) >= 2 else None)


def normalize_address_record(
    record: dict[str, Any],
    street_column: str = "street",
    city_column: str = "city",
    postal_code_column: str = "postal_code",
    country_column: str | None = "country",
) -> dict[str, Any]:
    result = dict(record)
    country = normalize_country_code(record.get(country_column)) if country_column else "DE"
    street = record.get(street_column)
    city = record.get(city_column)
    postal = record.get(postal_code_column)
    parts = split_street_and_house_number(street)
    result.update(
        {
            "street_original": street,
            "street_normalized": parts.street,
            "house_number_normalized": parts.house_number,
            "city_original": city,
            "city_normalized": normalize_city(city),
            "postal_code_original": postal,
            "postal_code_normalized": normalize_postal_code(postal, country or "DE"),
            "postal_code_valid": validate_postal_code(postal, country or "DE"),
            "country_normalized": country,
        }
    )
    return result


def normalize_address_frame(
    frame: pl.DataFrame,
    street_column: str = "street",
    city_column: str = "city",
    postal_code_column: str = "postal_code",
    country_column: str | None = "country",
) -> pl.DataFrame:
    required = {street_column, city_column, postal_code_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Address columns not found: {', '.join(missing)}")
    records = [
        normalize_address_record(
            record,
            street_column=street_column,
            city_column=city_column,
            postal_code_column=postal_code_column,
            country_column=country_column if country_column in frame.columns else None,
        )
        for record in frame.to_dicts()
    ]
    return pl.DataFrame(records, infer_schema_length=None)
