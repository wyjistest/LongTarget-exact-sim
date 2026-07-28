#!/usr/bin/env python3
"""Tiny diagnostic scalar model for the frozen modified-SSW score frontier."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreInfo:
    score: int
    position: int


def _score(a: str, b: str, match: int, mismatch_penalty: int) -> int:
    return match if a.upper() == b.upper() and a.upper() in "ACGT" else -mismatch_penalty


def column_maxima(
    query: str,
    reference: str,
    *,
    match: int = 5,
    mismatch_penalty: int = 4,
    gap_open: int = 16,
    gap_extend: int = 4,
) -> list[int]:
    """Return local affine-gap maxima per reference column.

    This intentionally small model is diagnostic. The SSE2 implementation, including
    its striped lazy-F order and saturation/recompute behavior, remains the oracle.
    """

    if not query or not reference:
        return []
    previous = [0] * (len(query) + 1)
    e_gap = [0] * (len(query) + 1)
    maxima: list[int] = []
    for ref_base in reference:
        current = [0] * (len(query) + 1)
        f_gap = 0
        column_max = 0
        for row, query_base in enumerate(query, start=1):
            e_gap[row] = max(previous[row] - gap_open, e_gap[row] - gap_extend, 0)
            f_gap = max(current[row - 1] - gap_open, f_gap - gap_extend, 0)
            diagonal = previous[row - 1] + _score(
                query_base, ref_base, match, mismatch_penalty
            )
            current[row] = max(0, diagonal, e_gap[row], f_gap)
            column_max = max(column_max, current[row])
        maxima.append(column_max)
        previous = current
    return maxima


def select_scoreinfos(columns: list[int], threshold: int) -> list[ScoreInfo]:
    """Mirror Aligner::preAlign's strict threshold and <5-position grouping."""

    above = [ScoreInfo(score, position) for position, score in enumerate(columns) if score > threshold]
    selected: list[ScoreInfo] = []
    cursor = 0
    while cursor < len(above):
        end = cursor + 1
        while end < len(above) and 0 < above[end].position - above[end - 1].position < 5:
            end += 1
        group = above[cursor:end]
        maximum = max(item.score for item in group)
        selected.append(next(item for item in group if item.score == maximum))
        cursor = end
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("reference")
    parser.add_argument("--threshold", type=int, default=0)
    args = parser.parse_args()
    columns = column_maxima(args.query, args.reference)
    print(
        json.dumps(
            {
                "column_maxima": columns,
                "scoreinfos": [item.__dict__ for item in select_scoreinfos(columns, args.threshold)],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
