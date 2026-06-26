#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedRow:
    row: str
    rule: str
    chrom: str
    strand: str


def _read_rows(path: Path) -> list[str]:
    rows: list[str] = []
    for line in path.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("QueryStart\t"):
            continue
        rows.append(line)
    return rows


def _parse_row(row: str) -> ParsedRow:
    fields = row.split("\t")
    if len(fields) < 12:
        raise SystemExit(f"unsupported row with {len(fields)} fields: {row}")
    return ParsedRow(row=row, chrom=fields[5], strand=fields[10], rule=fields[11])


def _frontier_bucket(row: ParsedRow, key: str) -> str:
    if key == "rule":
        return row.rule
    if key == "chrom_rule":
        return f"{row.chrom}\t{row.rule}"
    if key == "chrom_strand_rule":
        return f"{row.chrom}\t{row.strand}\t{row.rule}"
    raise SystemExit(f"unsupported frontier key: {key}")


def _bucket_rows(rows: list[str], key: str) -> dict[str, set[str]]:
    buckets: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        parsed = _parse_row(row)
        buckets[_frontier_bucket(parsed, key)].add(row)
    return dict(buckets)


def _first_or_empty(values: set[str]) -> str:
    return sorted(values)[0] if values else ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check whether a prune candidate preserves kept rows inside "
            "task-local frontier buckets."
        )
    )
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--baseline-only", type=Path)
    parser.add_argument("--candidate-only", type=Path)
    parser.add_argument(
        "--frontier-key",
        default="chrom_strand_rule",
        choices=("rule", "chrom_rule", "chrom_strand_rule"),
    )
    args = parser.parse_args()

    full_mode = args.baseline is not None or args.candidate is not None
    diff_only_mode = args.baseline_only is not None or args.candidate_only is not None
    if full_mode == diff_only_mode:
        raise SystemExit(
            "provide either --baseline/--candidate or "
            "--baseline-only/--candidate-only"
        )
    if full_mode and (args.baseline is None or args.candidate is None):
        raise SystemExit("--baseline and --candidate must be provided together")
    if diff_only_mode and (
        args.baseline_only is None or args.candidate_only is None
    ):
        raise SystemExit(
            "--baseline-only and --candidate-only must be provided together"
        )

    if full_mode:
        baseline_rows = _read_rows(args.baseline)
        candidate_rows = _read_rows(args.candidate)
        baseline_set = set(baseline_rows)
        candidate_set = set(candidate_rows)
        baseline_only = baseline_set - candidate_set
        candidate_only = candidate_set - baseline_set
        input_mode = "full"
        baseline_buckets = _bucket_rows(baseline_rows, args.frontier_key)
        candidate_buckets = _bucket_rows(candidate_rows, args.frontier_key)
        baseline_row_count = len(baseline_rows)
        candidate_row_count = len(candidate_rows)
        baseline_unique_count = len(baseline_set)
        candidate_unique_count = len(candidate_set)
    else:
        baseline_only = set(_read_rows(args.baseline_only))
        candidate_only = set(_read_rows(args.candidate_only))
        baseline_rows = sorted(baseline_only)
        candidate_rows = sorted(candidate_only)
        input_mode = "diff_only"
        baseline_buckets = _bucket_rows(baseline_rows, args.frontier_key)
        candidate_buckets = _bucket_rows(candidate_rows, args.frontier_key)
        baseline_row_count = len(baseline_rows)
        candidate_row_count = len(candidate_rows)
        baseline_unique_count = len(baseline_only)
        candidate_unique_count = len(candidate_only)
    all_bucket_keys = set(baseline_buckets) | set(candidate_buckets)
    changed_buckets: set[str] = set()
    shared_changed_buckets: set[str] = set()
    baseline_only_buckets: set[str] = set()
    candidate_only_buckets: set[str] = set()
    for bucket in all_bucket_keys:
        baseline_bucket_rows = baseline_buckets.get(bucket, set())
        candidate_bucket_rows = candidate_buckets.get(bucket, set())
        if baseline_bucket_rows == candidate_bucket_rows:
            continue
        changed_buckets.add(bucket)
        if baseline_bucket_rows and candidate_bucket_rows:
            shared_changed_buckets.add(bucket)
        elif baseline_bucket_rows:
            baseline_only_buckets.add(bucket)
        else:
            candidate_only_buckets.add(bucket)

    row_set_equal = not baseline_only and not candidate_only
    frontier_safe = row_set_equal and not changed_buckets

    output = {
        "input_mode": input_mode,
        "baseline_rows": str(baseline_row_count),
        "candidate_rows": str(candidate_row_count),
        "baseline_unique_rows": str(baseline_unique_count),
        "candidate_unique_rows": str(candidate_unique_count),
        "baseline_only_rows": str(len(baseline_only)),
        "candidate_only_rows": str(len(candidate_only)),
        "row_set_equal": "1" if row_set_equal else "0",
        "frontier_key": args.frontier_key,
        "frontier_safety": "safe" if frontier_safe else "unsafe",
        "frontier_changed_buckets": str(len(changed_buckets)),
        "frontier_shared_changed_buckets": str(len(shared_changed_buckets)),
        "frontier_baseline_only_buckets": str(len(baseline_only_buckets)),
        "frontier_candidate_only_buckets": str(len(candidate_only_buckets)),
        "first_frontier_changed_bucket": _first_or_empty(changed_buckets),
    }
    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
