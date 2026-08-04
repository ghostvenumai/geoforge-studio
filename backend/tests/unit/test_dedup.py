from __future__ import annotations

import polars as pl

from geoforge.processing.dedup import (
    DeduplicationConfig,
    create_block_key,
    detect_duplicates,
    weighted_match_score,
)


def config() -> DeduplicationConfig:
    return DeduplicationConfig(
        comparison_columns=["street", "postal_code", "city"],
        blocking_columns=["postal_code"],
        weights={"street": 0.5, "postal_code": 0.3, "city": 0.2},
        minimum_score=80,
        review_threshold=95,
    )


def test_blocking_key_is_normalized() -> None:
    assert create_block_key({"postal_code": " D-10115 "}, config()) == "d10115"


def test_weighted_match_scores_similar_addresses() -> None:
    left = {"street": "Müllerstr. 1", "postal_code": "10115", "city": "Berlin"}
    right = {"street": "Muellerstrasse 1", "postal_code": "10115", "city": "BERLIN"}
    score, columns = weighted_match_score(left, right, config())
    assert score >= 90
    assert "postal_code" in columns


def test_detection_only_compares_inside_blocks_and_selects_canonical() -> None:
    frame = pl.DataFrame(
        [
            {
                "record_id": "a",
                "street": "Teststr. 1",
                "postal_code": "10115",
                "city": "Berlin",
                "email": None,
            },
            {
                "record_id": "b",
                "street": "Teststrasse 1",
                "postal_code": "10115",
                "city": "Berlin",
                "email": "x@example.invalid",
            },
            {
                "record_id": "c",
                "street": "Teststr. 1",
                "postal_code": "20095",
                "city": "Hamburg",
                "email": None,
            },
        ]
    )
    result = detect_duplicates(frame, config())
    assert result.candidate_pairs == 1
    assert result.matched_pairs == 1
    assert result.frame["duplicate_group_id"].null_count() == 1
    assert result.frame.filter(pl.col("record_id") == "a")["canonical_record_id"][0] == "b"


def test_oversized_blocks_are_skipped() -> None:
    frame = pl.DataFrame(
        [{"record_id": str(index), "name": "same", "postal_code": "1"} for index in range(4)]
    )
    settings = DeduplicationConfig(
        comparison_columns=["name"], blocking_columns=["postal_code"], maximum_group_size=3
    )
    result = detect_duplicates(frame, settings)
    assert result.skipped_oversized_blocks == 1
    assert result.candidate_pairs == 0
