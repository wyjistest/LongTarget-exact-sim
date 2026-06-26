#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RowStats:
    row: str
    chrom: str
    genome_start: int
    genome_end: int
    rule: str
    nt: int
    query_span: int
    ref_span: int
    sum_span: int


def _read_rows(path: Path) -> list[str]:
    rows: list[str] = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        rows.append(line)
    return rows


def _parse_row_stats(row: str) -> RowStats:
    fields = row.split("\t")
    if len(fields) < 14:
        raise SystemExit(f"unsupported row with {len(fields)} fields: {row}")
    try:
        query_start = int(fields[0])
        query_end = int(fields[1])
        ref_start = int(fields[2])
        ref_end = int(fields[3])
        genome_start = int(fields[6])
        genome_end = int(fields[7])
        nt = int(fields[13])
    except ValueError as exc:
        raise SystemExit(f"invalid numeric row: {row}") from exc
    query_span = abs(query_end - query_start) + 1
    ref_span = abs(ref_end - ref_start) + 1
    return RowStats(
        row=row,
        chrom=fields[5],
        genome_start=min(genome_start, genome_end),
        genome_end=max(genome_start, genome_end),
        rule=fields[10],
        nt=nt,
        query_span=query_span,
        ref_span=ref_span,
        sum_span=query_span + ref_span,
    )


def _min_or_zero(values: list[int]) -> int:
    return min(values) if values else 0


def _max_or_zero(values: list[int]) -> int:
    return max(values) if values else 0


def _summarize(prefix: str, rows: list[str]) -> dict[str, str]:
    stats = [_parse_row_stats(row) for row in rows]
    nts = [item.nt for item in stats]
    query_spans = [item.query_span for item in stats]
    ref_spans = [item.ref_span for item in stats]
    sum_spans = [item.sum_span for item in stats]
    return {
        f"{prefix}_min_nt": str(_min_or_zero(nts)),
        f"{prefix}_max_nt": str(_max_or_zero(nts)),
        f"{prefix}_min_query_span": str(_min_or_zero(query_spans)),
        f"{prefix}_max_query_span": str(_max_or_zero(query_spans)),
        f"{prefix}_min_ref_span": str(_min_or_zero(ref_spans)),
        f"{prefix}_max_ref_span": str(_max_or_zero(ref_spans)),
        f"{prefix}_min_sum_span": str(_min_or_zero(sum_spans)),
        f"{prefix}_max_sum_span": str(_max_or_zero(sum_spans)),
    }


def _overlap_bp(lhs: RowStats, rhs: RowStats) -> int:
    if lhs.chrom != rhs.chrom:
        return 0
    start = max(lhs.genome_start, rhs.genome_start)
    end = min(lhs.genome_end, rhs.genome_end)
    if end < start:
        return 0
    return end - start + 1


def _summarize_cross_overlap(
    baseline_only: list[str], candidate_only: list[str]
) -> dict[str, str]:
    baseline_stats = [_parse_row_stats(row) for row in baseline_only]
    candidate_stats = [_parse_row_stats(row) for row in candidate_only]
    pairs = 0
    same_rule_pairs = 0
    max_bp = 0
    for baseline_row in baseline_stats:
        for candidate_row in candidate_stats:
            overlap = _overlap_bp(baseline_row, candidate_row)
            if overlap <= 0:
                continue
            pairs += 1
            max_bp = max(max_bp, overlap)
            if baseline_row.rule == candidate_row.rule:
                same_rule_pairs += 1
    return {
        "cross_overlap_pairs": str(pairs),
        "cross_overlap_max_bp": str(max_bp),
        "cross_overlap_same_rule_pairs": str(same_rule_pairs),
    }


def _distance_bp(lhs: RowStats, rhs: RowStats) -> int | None:
    if lhs.chrom != rhs.chrom:
        return None
    if _overlap_bp(lhs, rhs) > 0:
        return 0
    if lhs.genome_end < rhs.genome_start:
        return rhs.genome_start - lhs.genome_end
    return lhs.genome_start - rhs.genome_end


def _summarize_buckets(
    baseline_only: list[str], candidate_only: list[str]
) -> dict[str, str]:
    baseline_stats = [_parse_row_stats(row) for row in baseline_only]
    candidate_stats = [_parse_row_stats(row) for row in candidate_only]
    baseline_rules = {row.rule for row in baseline_stats}
    candidate_rules = {row.rule for row in candidate_stats}
    distances: list[int] = []
    for baseline_row in baseline_stats:
        for candidate_row in candidate_stats:
            distance = _distance_bp(baseline_row, candidate_row)
            if distance is not None:
                distances.append(distance)
    return {
        "baseline_only_rule_count": str(len(baseline_rules)),
        "candidate_only_rule_count": str(len(candidate_rules)),
        "shared_rule_count": str(len(baseline_rules & candidate_rules)),
        "min_cross_distance_bp": str(_min_or_zero(distances)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare no-prune authority rows with a prune candidate."
    )
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()

    baseline_rows = _read_rows(args.baseline)
    candidate_rows = _read_rows(args.candidate)
    baseline_set = set(baseline_rows)
    candidate_set = set(candidate_rows)
    baseline_only = sorted(baseline_set - candidate_set)
    candidate_only = sorted(candidate_set - baseline_set)

    output: dict[str, str] = {
        "baseline_rows": str(len(baseline_rows)),
        "candidate_rows": str(len(candidate_rows)),
        "baseline_unique_rows": str(len(baseline_set)),
        "candidate_unique_rows": str(len(candidate_set)),
        "baseline_only_rows": str(len(baseline_only)),
        "candidate_only_rows": str(len(candidate_only)),
        "row_set_equal": "1" if not baseline_only and not candidate_only else "0",
    }
    output.update(_summarize("baseline_only", baseline_only))
    output.update(_summarize("candidate_only", candidate_only))
    output.update(_summarize_cross_overlap(baseline_only, candidate_only))
    output.update(_summarize_buckets(baseline_only, candidate_only))

    for key, value in output.items():
        print(f"{key}={value}")
    if baseline_only:
        print(f"first_baseline_only_row={baseline_only[0]}")
    if candidate_only:
        print(f"first_candidate_only_row={candidate_only[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
