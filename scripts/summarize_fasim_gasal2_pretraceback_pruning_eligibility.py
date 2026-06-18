#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


PREFIX = "benchmark.fasim_gasal2_pretraceback_pruning_eligibility_"

BUCKET_ORDER = [
    "exact_request_duplicate",
    "exact_descriptor_duplicate",
    "same_final_row_different_descriptor",
    "cross_flush_exact_duplicate",
    "cigar_dependent_duplicate",
    "representative_selection_dependent",
    "sort_or_dominance_removed",
    "pretraceback_span_provable",
    "reverse_start_dependent_span",
    "cigar_dependent_span",
    "unknown",
]

BUCKET_NOTES = {
    "exact_request_duplicate": "same pre-traceback request as representative",
    "exact_descriptor_duplicate": "same normalized descriptor as representative",
    "same_final_row_different_descriptor": "same final row, different descriptor",
    "cross_flush_exact_duplicate": "same request across flush boundary",
    "cigar_dependent_duplicate": "requires CIGAR or converted alignment fields",
    "representative_selection_dependent": "requires final representative selection",
    "sort_or_dominance_removed": "requires final sort/non-overlap/dominance",
    "pretraceback_span_provable": "span rejection provable before traceback",
    "reverse_start_dependent_span": "span rejection depends on reverse-start convention",
    "cigar_dependent_span": "span rejection depends on traceback endpoints/CIGAR",
    "unknown": "unclassified eligibility bucket",
}

REQUIRED_COLUMNS = {
    "attempt_id",
    "flush_id",
    "task_id",
    "scoreinfo_index",
    "prealign_score",
    "query_len",
    "target_size",
    "target_start",
    "cutlength",
    "request_key_hash",
    "descriptor_key_hash",
    "final_row_hash",
    "representative_attempt_id",
    "representative_flush_id",
    "representative_request_key_hash",
    "representative_descriptor_key_hash",
    "same_flush",
    "cross_flush",
    "score",
    "query_begin",
    "query_end",
    "ref_begin",
    "ref_end",
    "output_global_start",
    "output_global_end",
    "nt",
    "identity",
    "stability",
    "cigar_hash",
    "final_rejection_bucket",
    "eligibility_bucket",
    "pre_traceback_decidable",
    "post_traceback_only",
    "top5_only_safe_candidate",
    "full_output_safe_candidate",
    "notes",
}


@dataclass
class BucketSummary:
    attempts: int = 0
    representative_mapped: int = 0
    pre_traceback_decidable: int = 0
    post_traceback_only: int = 0
    top5_only_safe_candidate: int = 0
    full_output_safe_candidate: int = 0


def _as_bool(row: dict[str, str], key: str) -> bool:
    value = row.get(key, "").strip().lower()
    return value not in ("", "0", "false", "no")


def _as_int(text: str, default: int = 0) -> int:
    try:
        return int(text)
    except (TypeError, ValueError):
        return default


def _ratio(num: int, den: int) -> str:
    if den == 0:
        return "nan"
    return f"{num / den:.6f}"


def _parse_stderr_metrics(path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.startswith(PREFIX):
            metrics[key[len(PREFIX) :]] = value.strip()
    return metrics


def _int_metric(metrics: dict[str, str], key: str) -> int:
    try:
        return int(metrics[key])
    except KeyError as exc:
        raise SystemExit(f"missing required metric: {PREFIX}{key}") from exc
    except ValueError as exc:
        raise SystemExit(f"invalid integer metric {PREFIX}{key}: {metrics[key]}") from exc


def _read_stderr(path: Path) -> tuple[int, int, int, Counter[str], dict[str, BucketSummary], dict[str, int]]:
    metrics = _parse_stderr_metrics(path)
    attempts = _int_metric(metrics, "attempts")
    removed = _int_metric(metrics, "removed_attempts")
    retained = _int_metric(metrics, "retained_final_rows")
    bucket_counts: Counter[str] = Counter()
    summaries: dict[str, BucketSummary] = {}

    for bucket in BUCKET_ORDER:
        count = int(metrics.get(bucket, "0"))
        if count == 0:
            continue
        bucket_counts[bucket] = count
        summary = summaries.setdefault(bucket, BucketSummary())
        summary.attempts = count

    mapped = _int_metric(metrics, "mapped_removed_attempts")
    unmapped = _int_metric(metrics, "unmapped_removed_attempts")

    for bucket in (
        "exact_request_duplicate",
        "exact_descriptor_duplicate",
        "same_final_row_different_descriptor",
        "cross_flush_exact_duplicate",
    ):
        if bucket_counts[bucket]:
            summaries[bucket].representative_mapped = bucket_counts[bucket]

    for bucket in (
        "exact_request_duplicate",
        "exact_descriptor_duplicate",
        "cross_flush_exact_duplicate",
        "pretraceback_span_provable",
    ):
        if bucket_counts[bucket]:
            summaries[bucket].pre_traceback_decidable = bucket_counts[bucket]
            summaries[bucket].top5_only_safe_candidate = bucket_counts[bucket]

    for bucket in (
        "same_final_row_different_descriptor",
        "cigar_dependent_duplicate",
        "representative_selection_dependent",
        "sort_or_dominance_removed",
        "reverse_start_dependent_span",
        "cigar_dependent_span",
    ):
        if bucket_counts[bucket]:
            summaries[bucket].post_traceback_only = bucket_counts[bucket]

    scalar_counts = {
        "removed_attempts": removed,
        "mapped_removed_attempts": mapped,
        "unmapped_removed_attempts": unmapped,
        "known_eligibility_attempts": removed - bucket_counts["unknown"],
        "unknown_eligibility_attempts": bucket_counts["unknown"],
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
        "false_prune_shadow": _int_metric(metrics, "false_prune_shadow"),
        "missing_rows_shadow": _int_metric(metrics, "missing_rows_shadow"),
        "extra_rows_shadow": _int_metric(metrics, "extra_rows_shadow"),
    }
    return attempts, removed, retained, bucket_counts, summaries, scalar_counts


def _read_tsv(path: Path) -> tuple[int, int, int, Counter[str], dict[str, BucketSummary], dict[str, int]]:
    attempts = 0
    retained = 0
    removed = 0
    bucket_counts: Counter[str] = Counter()
    summaries: dict[str, BucketSummary] = {}

    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"empty eligibility TSV: {path}")
        missing = sorted(REQUIRED_COLUMNS.difference(reader.fieldnames))
        if missing:
            raise SystemExit(
                f"eligibility TSV missing required columns: {', '.join(missing)}"
            )
        for row in reader:
            attempts += 1
            final_bucket = row.get("final_rejection_bucket", "").strip()
            bucket = row.get("eligibility_bucket", "").strip() or "unknown"
            if final_bucket == "retained_emitted":
                retained += 1
                continue
            removed += 1
            bucket_counts[bucket] += 1
            summary = summaries.setdefault(bucket, BucketSummary())
            summary.attempts += 1
            if _as_int(row.get("representative_attempt_id", "0")) > 0:
                summary.representative_mapped += 1
            if _as_bool(row, "pre_traceback_decidable"):
                summary.pre_traceback_decidable += 1
            if _as_bool(row, "post_traceback_only"):
                summary.post_traceback_only += 1
            if _as_bool(row, "top5_only_safe_candidate"):
                summary.top5_only_safe_candidate += 1
            if _as_bool(row, "full_output_safe_candidate"):
                summary.full_output_safe_candidate += 1

    mapped = sum(summary.representative_mapped for summary in summaries.values())
    scalar_counts = {
        "removed_attempts": removed,
        "mapped_removed_attempts": mapped,
        "unmapped_removed_attempts": removed - mapped,
        "known_eligibility_attempts": removed - bucket_counts["unknown"],
        "unknown_eligibility_attempts": bucket_counts["unknown"],
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
        "false_prune_shadow": 0,
        "missing_rows_shadow": 0,
        "extra_rows_shadow": 0,
    }
    return attempts, removed, retained, bucket_counts, summaries, scalar_counts


def _ordered_buckets(bucket_counts: Counter[str]) -> list[str]:
    known = [bucket for bucket in BUCKET_ORDER if bucket in bucket_counts]
    extra = sorted(bucket for bucket in bucket_counts if bucket not in BUCKET_ORDER)
    return known + extra


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2 pre-traceback pruning eligibility telemetry."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--stderr", type=Path)
    source.add_argument("--eligibility", type=Path)
    parser.add_argument("--label", default="run")
    args = parser.parse_args()

    if args.stderr is not None:
        (
            attempts,
            removed,
            retained,
            bucket_counts,
            summaries,
            scalar_counts,
        ) = _read_stderr(args.stderr)
    else:
        (
            attempts,
            removed,
            retained,
            bucket_counts,
            summaries,
            scalar_counts,
        ) = _read_tsv(args.eligibility)

    print(f"label={args.label}")
    print(f"eligibility_attempts={attempts}")
    print(f"retained_final_rows={retained}")
    for key in (
        "removed_attempts",
        "mapped_removed_attempts",
        "unmapped_removed_attempts",
        "known_eligibility_attempts",
        "unknown_eligibility_attempts",
        "pre_traceback_decidable_attempts",
        "post_traceback_only_attempts",
        "top5_only_safe_candidate_attempts",
        "full_output_safe_candidate_attempts",
        "false_prune_shadow",
        "missing_rows_shadow",
        "extra_rows_shadow",
    ):
        print(f"{key}={scalar_counts[key]}")
    print(f"unknown_fraction={_ratio(bucket_counts['unknown'], removed)}")
    print(
        "eligibility_bucket\tattempts\tfraction_of_traceback_attempts\t"
        "fraction_of_removed_attempts\trepresentative_mapped\t"
        "pre_traceback_decidable\tpost_traceback_only\t"
        "top5_only_safe_candidate\tfull_output_safe_candidate\t"
        "false_prune_shadow\tmissing_rows_shadow\textra_rows_shadow\tnotes"
    )

    for bucket in _ordered_buckets(bucket_counts):
        summary = summaries[bucket]
        print(
            f"{bucket}\t"
            f"{summary.attempts}\t"
            f"{_ratio(summary.attempts, attempts)}\t"
            f"{_ratio(summary.attempts, removed)}\t"
            f"{summary.representative_mapped}\t"
            f"{summary.pre_traceback_decidable}\t"
            f"{summary.post_traceback_only}\t"
            f"{summary.top5_only_safe_candidate}\t"
            f"{summary.full_output_safe_candidate}\t"
            f"{scalar_counts['false_prune_shadow']}\t"
            f"{scalar_counts['missing_rows_shadow']}\t"
            f"{scalar_counts['extra_rows_shadow']}\t"
            f"{BUCKET_NOTES.get(bucket, '')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
