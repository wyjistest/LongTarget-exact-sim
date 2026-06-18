#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


PREFIX = "benchmark.fasim_gasal2_traceback_rejection_taxonomy_"

BUCKET_NOTES = {
    "retained_emitted": "kept through emit/final output",
    "filtered_score": "below score/minScore threshold",
    "filtered_identity": "post-CIGAR identity threshold",
    "filtered_stability": "post-CIGAR stability threshold",
    "filtered_nt": "post-CIGAR nt threshold",
    "invalid_span_bound": "invalid or insufficient span bound",
    "duplicate_descriptor": "duplicate traceback descriptor",
    "duplicate_row": "duplicate emitted row",
    "final_sort_dedup_removed": "removed by final sort/dedup",
    "final_nonoverlap_dominated": "dominated by final non-overlap policy",
    "top5_frontier_dominated": "dominated by top5 frontier",
    "post_cigar_only": "requires CIGAR/traceback before classification",
    "unknown": "unclassified diagnostic bucket",
}

BUCKET_ORDER = [
    "retained_emitted",
    "filtered_score",
    "filtered_identity",
    "filtered_stability",
    "filtered_nt",
    "invalid_span_bound",
    "duplicate_descriptor",
    "duplicate_row",
    "final_sort_dedup_removed",
    "final_nonoverlap_dominated",
    "top5_frontier_dominated",
    "post_cigar_only",
    "unknown",
]

REQUIRED_COLUMNS = {
    "decision_bucket",
    "pre_traceback_decidable",
    "post_traceback_only",
    "top5_only_safe_candidate",
    "full_output_safe_candidate",
    "emitted_row",
    "final_row",
}


@dataclass
class BucketSummary:
    attempts: int = 0
    pre_traceback_decidable: int = 0
    post_traceback_only: int = 0
    top5_only_safe_candidate: int = 0
    full_output_safe_candidate: int = 0


def _as_bool(row: dict[str, str], key: str) -> bool:
    value = row.get(key, "").strip().lower()
    return value not in ("", "0", "false", "no")


def _ratio(num: int, den: int) -> str:
    if den == 0:
        return "nan"
    return f"{num / den:.6f}"


def _read_taxonomy(path: Path) -> tuple[int, Counter[str], dict[str, BucketSummary], dict[str, int]]:
    total = 0
    bucket_counts: Counter[str] = Counter()
    summaries: dict[str, BucketSummary] = {}
    scalar_counts = {
        "pre_traceback_decidable_attempts": 0,
        "post_traceback_only_attempts": 0,
        "top5_only_safe_candidate_attempts": 0,
        "full_output_safe_candidate_attempts": 0,
        "emitted_attempts": 0,
        "final_attempts": 0,
    }

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"empty taxonomy TSV: {path}")
        missing = sorted(REQUIRED_COLUMNS.difference(reader.fieldnames))
        if missing:
            raise SystemExit(
                f"taxonomy TSV missing required columns: {', '.join(missing)}"
            )
        for row in reader:
            bucket = row.get("decision_bucket", "").strip() or "unknown"
            total += 1
            bucket_counts[bucket] += 1
            summary = summaries.setdefault(bucket, BucketSummary())
            summary.attempts += 1

            if _as_bool(row, "pre_traceback_decidable"):
                scalar_counts["pre_traceback_decidable_attempts"] += 1
                summary.pre_traceback_decidable += 1
            if _as_bool(row, "post_traceback_only"):
                scalar_counts["post_traceback_only_attempts"] += 1
                summary.post_traceback_only += 1
            if _as_bool(row, "top5_only_safe_candidate"):
                scalar_counts["top5_only_safe_candidate_attempts"] += 1
                summary.top5_only_safe_candidate += 1
            if _as_bool(row, "full_output_safe_candidate"):
                scalar_counts["full_output_safe_candidate_attempts"] += 1
                summary.full_output_safe_candidate += 1
            if _as_bool(row, "emitted_row"):
                scalar_counts["emitted_attempts"] += 1
            if _as_bool(row, "final_row"):
                scalar_counts["final_attempts"] += 1

    return total, bucket_counts, summaries, scalar_counts


def _parse_stderr_metrics(path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not key.startswith(PREFIX):
            continue
        metrics[key[len(PREFIX) :]] = value.strip()
    return metrics


def _int_metric(metrics: dict[str, str], key: str) -> int:
    try:
        return int(metrics[key])
    except KeyError as exc:
        raise SystemExit(f"missing required metric: {PREFIX}{key}") from exc
    except ValueError as exc:
        raise SystemExit(f"invalid integer metric {PREFIX}{key}: {metrics[key]}") from exc


def _read_stderr(path: Path) -> tuple[int, Counter[str], dict[str, BucketSummary], dict[str, int]]:
    metrics = _parse_stderr_metrics(path)
    total = _int_metric(metrics, "attempts")
    bucket_counts: Counter[str] = Counter()
    summaries: dict[str, BucketSummary] = {}
    for bucket in BUCKET_ORDER:
        count = int(metrics.get(bucket, "0"))
        if count == 0:
            continue
        bucket_counts[bucket] = count
        summary = summaries.setdefault(bucket, BucketSummary())
        summary.attempts = count

    for bucket in ("filtered_score", "invalid_span_bound"):
        count = bucket_counts[bucket]
        if count:
            summaries[bucket].pre_traceback_decidable = count
            summaries[bucket].top5_only_safe_candidate = count
            summaries[bucket].full_output_safe_candidate = count

    for bucket in (
        "filtered_identity",
        "filtered_stability",
        "filtered_nt",
        "final_sort_dedup_removed",
        "final_nonoverlap_dominated",
        "post_cigar_only",
    ):
        count = bucket_counts[bucket]
        if count:
            summaries[bucket].post_traceback_only = count

    retained = bucket_counts["retained_emitted"]
    if retained:
        summaries["retained_emitted"].full_output_safe_candidate = retained

    emitted_attempts = (
        bucket_counts["retained_emitted"]
        + bucket_counts["final_sort_dedup_removed"]
        + bucket_counts["final_nonoverlap_dominated"]
    )
    scalar_counts = {
        "pre_traceback_decidable_attempts": sum(
            summary.pre_traceback_decidable for summary in summaries.values()
        ),
        "post_traceback_only_attempts": sum(
            summary.post_traceback_only for summary in summaries.values()
        ),
        "top5_only_safe_candidate_attempts": sum(
            summary.top5_only_safe_candidate for summary in summaries.values()
        ),
        "full_output_safe_candidate_attempts": sum(
            summary.full_output_safe_candidate for summary in summaries.values()
        ),
        "emitted_attempts": emitted_attempts,
        "final_attempts": bucket_counts["retained_emitted"],
    }
    return total, bucket_counts, summaries, scalar_counts


def _ordered_buckets(bucket_counts: Counter[str]) -> list[str]:
    known = [bucket for bucket in BUCKET_ORDER if bucket in bucket_counts]
    extra = sorted(bucket for bucket in bucket_counts if bucket not in BUCKET_ORDER)
    return known + extra


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2 traceback rejection taxonomy telemetry."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--taxonomy", type=Path)
    source.add_argument("--stderr", type=Path)
    parser.add_argument("--label", default="run")
    parser.add_argument("--gasal2-requests", type=int, default=0)
    args = parser.parse_args()

    if args.taxonomy is not None:
        total, bucket_counts, summaries, scalar_counts = _read_taxonomy(args.taxonomy)
    else:
        total, bucket_counts, summaries, scalar_counts = _read_stderr(args.stderr)
    unknown = bucket_counts["unknown"]
    known = total - unknown
    final_attempts = scalar_counts["final_attempts"]
    gasal2_requests = args.gasal2_requests if args.gasal2_requests > 0 else total

    print(f"label={args.label}")
    print(f"taxonomy_attempts={total}")
    print(f"taxonomy_known_attempts={known}")
    print(f"taxonomy_unknown_attempts={unknown}")
    for key in (
        "pre_traceback_decidable_attempts",
        "post_traceback_only_attempts",
        "top5_only_safe_candidate_attempts",
        "full_output_safe_candidate_attempts",
        "emitted_attempts",
        "final_attempts",
    ):
        print(f"{key}={scalar_counts[key]}")
    print(f"rejected_attempts={total - final_attempts}")
    print(f"unknown_fraction={_ratio(unknown, total)}")
    print(
        "bucket\tattempts\tfraction_of_traceback_attempts\t"
        "fraction_of_gasal2_requests\tpre_traceback_decidable\t"
        "post_traceback_only\ttop5_only_safe_candidate\t"
        "full_output_safe_candidate\tnotes"
    )

    for bucket in _ordered_buckets(bucket_counts):
        summary = summaries[bucket]
        print(
            f"{bucket}\t"
            f"{summary.attempts}\t"
            f"{_ratio(summary.attempts, total)}\t"
            f"{_ratio(summary.attempts, gasal2_requests)}\t"
            f"{summary.pre_traceback_decidable}\t"
            f"{summary.post_traceback_only}\t"
            f"{summary.top5_only_safe_candidate}\t"
            f"{summary.full_output_safe_candidate}\t"
            f"{BUCKET_NOTES.get(bucket, 'unrecognized diagnostic bucket')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
