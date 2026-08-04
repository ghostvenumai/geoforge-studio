from __future__ import annotations

import hashlib
import itertools
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal

import polars as pl
from rapidfuzz.fuzz import ratio

from geoforge.processing.address import matching_key

MatchMode = Literal["exact", "normalized", "fuzzy", "weighted"]


@dataclass(frozen=True)
class DeduplicationConfig:
    comparison_columns: list[str]
    blocking_columns: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    minimum_score: float = 85.0
    review_threshold: float = 93.0
    maximum_group_size: int = 500
    mode: MatchMode = "weighted"
    record_id_column: str = "record_id"
    canonical_strategy: Literal["first", "most_complete"] = "most_complete"

    def __post_init__(self) -> None:
        if not self.comparison_columns:
            raise ValueError("At least one comparison column is required")
        if not 0 <= self.minimum_score <= 100:
            raise ValueError("minimum_score must be between 0 and 100")
        if not self.minimum_score <= self.review_threshold <= 100:
            raise ValueError("review_threshold must be >= minimum_score and <= 100")
        if not 2 <= self.maximum_group_size <= 10_000:
            raise ValueError("maximum_group_size must be between 2 and 10000")


@dataclass(frozen=True)
class DeduplicationResult:
    frame: pl.DataFrame
    candidate_pairs: int
    matched_pairs: int
    skipped_oversized_blocks: int


def create_block_key(record: dict[str, Any], config: DeduplicationConfig) -> str:
    columns = config.blocking_columns
    if columns:
        return "|".join(matching_key(record.get(column)) for column in columns)
    primary = matching_key(record.get(config.comparison_columns[0]))
    return primary[:3] if len(primary) >= 3 else primary


def weighted_match_score(
    left: dict[str, Any], right: dict[str, Any], config: DeduplicationConfig
) -> tuple[float, list[str]]:
    scores: list[tuple[str, float, float]] = []
    default_weight = 1.0
    for column in config.comparison_columns:
        left_value = matching_key(left.get(column))
        right_value = matching_key(right.get(column))
        if not left_value and not right_value:
            score = 100.0
        elif config.mode == "exact":
            score = 100.0 if str(left.get(column)) == str(right.get(column)) else 0.0
        elif config.mode == "normalized":
            score = 100.0 if left_value == right_value else 0.0
        else:
            score = float(ratio(left_value, right_value))
        scores.append((column, score, config.weights.get(column, default_weight)))
    total_weight = sum(weight for _, _, weight in scores)
    if total_weight <= 0:
        raise ValueError("Comparison weights must have a positive sum")
    weighted = sum(score * weight for _, score, weight in scores) / total_weight
    matched = [column for column, score, _ in scores if score >= config.minimum_score]
    return round(weighted, 2), matched


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def _canonical_index(indexes: list[int], records: list[dict[str, Any]], strategy: str) -> int:
    if strategy == "first":
        return min(indexes)
    return max(
        indexes, key=lambda index: sum(value not in (None, "") for value in records[index].values())
    )


def detect_duplicates(frame: pl.DataFrame, config: DeduplicationConfig) -> DeduplicationResult:
    missing = set(config.comparison_columns + config.blocking_columns) - set(frame.columns)
    if missing:
        raise ValueError(f"Deduplication columns not found: {', '.join(sorted(missing))}")
    records = frame.to_dicts()
    blocks: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        key = create_block_key(record, config)
        if key:
            blocks[key].append(index)
    union_find = _UnionFind(len(records))
    pair_details: dict[tuple[int, int], tuple[float, list[str]]] = {}
    candidates = 0
    skipped = 0
    for indexes in blocks.values():
        if len(indexes) > config.maximum_group_size:
            skipped += 1
            continue
        for left_index, right_index in itertools.combinations(indexes, 2):
            candidates += 1
            score, columns = weighted_match_score(records[left_index], records[right_index], config)
            if score >= config.minimum_score:
                union_find.union(left_index, right_index)
                pair_details[(left_index, right_index)] = (score, columns)
    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        groups[union_find.find(index)].append(index)
    duplicate_groups = [indexes for indexes in groups.values() if len(indexes) > 1]
    output = [dict(record) for record in records]
    for indexes in duplicate_groups:
        canonical = _canonical_index(indexes, records, config.canonical_strategy)
        record_ids = [str(records[index].get(config.record_id_column, index)) for index in indexes]
        digest = hashlib.sha256("|".join(sorted(record_ids)).encode()).hexdigest()[:12]
        group_id = f"dup-{digest}"
        blocking_label = ", ".join(config.blocking_columns) or "prefix"
        for index in indexes:
            record_id = str(records[index].get(config.record_id_column, index))
            canonical_id = str(records[canonical].get(config.record_id_column, canonical))
            related = [
                detail
                for pair, detail in pair_details.items()
                if index in pair and pair[0] in indexes and pair[1] in indexes
            ]
            best_score, matched_columns = max(related, default=(100.0, config.comparison_columns))
            output[index].update(
                {
                    "duplicate_group_id": group_id,
                    "record_id": record_id,
                    "canonical_record_id": canonical_id,
                    "match_score": best_score,
                    "match_reason": f"blocked match on {blocking_label}",
                    "review_required": best_score < config.review_threshold,
                    "matched_columns": matched_columns,
                }
            )
    for index, record in enumerate(output):
        if "duplicate_group_id" not in record:
            record.update(
                {
                    "duplicate_group_id": None,
                    "record_id": str(records[index].get(config.record_id_column, index)),
                    "canonical_record_id": None,
                    "match_score": None,
                    "match_reason": None,
                    "review_required": False,
                    "matched_columns": [],
                }
            )
    return DeduplicationResult(
        frame=pl.DataFrame(output, infer_schema_length=None),
        candidate_pairs=candidates,
        matched_pairs=len(pair_details),
        skipped_oversized_blocks=skipped,
    )
