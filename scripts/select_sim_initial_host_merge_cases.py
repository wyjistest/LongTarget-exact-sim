#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

SELECTED_FIELDNAMES = [
    "case_id",
    "bucket_key",
    "summary_bin",
    "materialized_bin",
    "prune_bin",
    "logical_event_count",
    "summary_count",
    "store_materialized_count",
    "store_pruned_count",
    "prune_ratio",
    "selection_rank",
    "selection_reason",
]


def quantize_tertiles(rows, field):
    ordered = sorted(
        ((float(row[field]), row["case_id"]) for row in rows),
        key=lambda item: (item[0], item[1]),
    )
    total = len(ordered)
    bins = {}
    for rank, (_, case_id) in enumerate(ordered):
        bins[case_id] = (rank * 3) // total
    return bins


def build_bucket_key(summary_bin, materialized_bin, prune_bin):
    return f"s{summary_bin}|m{materialized_bin}|p{prune_bin}"


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def enrich_rows(rows):
    if not rows:
        return []

    summary_bins = quantize_tertiles(rows, "summary_count")
    materialized_bins = quantize_tertiles(rows, "store_materialized_count")
    prune_bins = quantize_tertiles(rows, "prune_ratio")

    enriched = []
    for row in rows:
        summary_bin = summary_bins[row["case_id"]]
        materialized_bin = materialized_bins[row["case_id"]]
        prune_bin = prune_bins[row["case_id"]]
        enriched_row = dict(row)
        enriched_row["summary_bin"] = str(summary_bin)
        enriched_row["materialized_bin"] = str(materialized_bin)
        enriched_row["prune_bin"] = str(prune_bin)
        enriched_row["bucket_key"] = build_bucket_key(
            summary_bin, materialized_bin, prune_bin
        )
        enriched.append(enriched_row)
    return enriched


def bucket_sort_key(bucket_key):
    summary_token, materialized_token, prune_token = bucket_key.split("|")
    return (int(summary_token[1:]), int(materialized_token[1:]), int(prune_token[1:]))


def bucket_case_totals(enriched_rows):
    buckets = {}
    total_logical_event_count = 0
    total_store_materialized_count = 0
    for row in enriched_rows:
        logical_event_count = int(row["logical_event_count"])
        store_materialized_count = int(row["store_materialized_count"])
        bucket = buckets.setdefault(
            row["bucket_key"],
            {
                "bucket_key": row["bucket_key"],
                "summary_bin": row["summary_bin"],
                "materialized_bin": row["materialized_bin"],
                "prune_bin": row["prune_bin"],
                "bucket_logical_event_count": 0,
                "bucket_store_materialized_count": 0,
                "rows": [],
            },
        )
        bucket["bucket_logical_event_count"] += logical_event_count
        bucket["bucket_store_materialized_count"] += store_materialized_count
        bucket["rows"].append(row)
        total_logical_event_count += logical_event_count
        total_store_materialized_count += store_materialized_count
    return buckets, total_logical_event_count, total_store_materialized_count


def normalized_weighted_score(logical_count, materialized_count, total_logical, total_materialized, logical_weight, materialized_weight):
    logical_component = (
        logical_weight * (float(logical_count) / float(total_logical))
        if total_logical > 0
        else 0.0
    )
    materialized_component = (
        materialized_weight * (float(materialized_count) / float(total_materialized))
        if total_materialized > 0
        else 0.0
    )
    return logical_component + materialized_component


def choose_legacy_cases(enriched_rows, limit):
    if not enriched_rows or limit <= 0:
        return []

    buckets = {}
    for row in enriched_rows:
        buckets.setdefault(row["bucket_key"], []).append(row)

    representatives = []
    for bucket_key, bucket_rows in buckets.items():
        chosen = max(
            bucket_rows,
            key=lambda row: (int(row["logical_event_count"]), row["case_id"]),
        )
        representatives.append((bucket_key, chosen))

    representatives.sort(
        key=lambda item: (-int(item[1]["logical_event_count"]), item[1]["case_id"])
    )

    selected = []
    selected_ids = set()
    for _, row in representatives:
        if len(selected) >= limit:
            break
        selected.append({**row, "selection_reason": "bucket_representative"})
        selected_ids.add(row["case_id"])

    if len(selected) < limit:
        remaining = sorted(
            (row for row in enriched_rows if row["case_id"] not in selected_ids),
            key=lambda row: (-int(row["logical_event_count"]), row["case_id"]),
        )
        for row in remaining:
            if len(selected) >= limit:
                break
            selected.append({**row, "selection_reason": "logical_event_backfill"})
            selected_ids.add(row["case_id"])

    for rank, row in enumerate(selected, start=1):
        row["selection_rank"] = str(rank)

    return selected


def choose_coverage_weighted_cases(
    enriched_rows, limit, logical_weight, materialized_weight
):
    if not enriched_rows or limit <= 0:
        return []

    buckets, total_logical_event_count, total_store_materialized_count = (
        bucket_case_totals(enriched_rows)
    )
    ordered_buckets = []
    for bucket_key, bucket in buckets.items():
        bucket_score = normalized_weighted_score(
            bucket["bucket_logical_event_count"],
            bucket["bucket_store_materialized_count"],
            total_logical_event_count,
            total_store_materialized_count,
            logical_weight,
            materialized_weight,
        )
        ordered_buckets.append((bucket_key, bucket, bucket_score))

    ordered_buckets.sort(
        key=lambda item: (
            -item[2],
            -item[1]["bucket_store_materialized_count"],
            -item[1]["bucket_logical_event_count"],
            bucket_sort_key(item[0]),
        )
    )

    selected = []
    selected_ids = set()
    for bucket_key, bucket, _ in ordered_buckets:
        if len(selected) >= limit:
            break
        representative = max(
            bucket["rows"],
            key=lambda row: (
                normalized_weighted_score(
                    int(row["logical_event_count"]),
                    int(row["store_materialized_count"]),
                    total_logical_event_count,
                    total_store_materialized_count,
                    logical_weight,
                    materialized_weight,
                ),
                int(row["store_materialized_count"]),
                int(row["logical_event_count"]),
                row["case_id"],
            ),
        )
        selected.append({**representative, "selection_reason": "bucket_representative"})
        selected_ids.add(representative["case_id"])

    if len(selected) < limit:
        remaining = sorted(
            (row for row in enriched_rows if row["case_id"] not in selected_ids),
            key=lambda row: (
                -normalized_weighted_score(
                    int(row["logical_event_count"]),
                    int(row["store_materialized_count"]),
                    total_logical_event_count,
                    total_store_materialized_count,
                    logical_weight,
                    materialized_weight,
                ),
                -int(row["store_materialized_count"]),
                -int(row["logical_event_count"]),
                row["case_id"],
            ),
        )
        for row in remaining:
            if len(selected) >= limit:
                break
            selected.append({**row, "selection_reason": "coverage_weighted_backfill"})
            selected_ids.add(row["case_id"])

    for rank, row in enumerate(selected, start=1):
        row["selection_rank"] = str(rank)

    return selected


def choose_cases(rows, limit, strategy, logical_weight, materialized_weight):
    enriched_rows = enrich_rows(rows)
    if strategy == "legacy":
        return choose_legacy_cases(enriched_rows, limit)
    if strategy == "coverage_weighted":
        return choose_coverage_weighted_cases(
            enriched_rows, limit, logical_weight, materialized_weight
        )
    raise ValueError(f"unknown strategy: {strategy}")


def write_selected(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=SELECTED_FIELDNAMES,
            delimiter="\t",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_coverage_report(rows, selected_rows, strategy, logical_weight, materialized_weight, limit):
    enriched_rows = enrich_rows(rows)
    bucket_totals, total_logical_event_count, total_store_materialized_count = (
        bucket_case_totals(enriched_rows)
    )
    selected_bucket_keys = []
    seen_bucket_keys = set()
    covered_logical_event_count = 0
    covered_store_materialized_count = 0
    for row in selected_rows:
        bucket_key = row["bucket_key"]
        if bucket_key in seen_bucket_keys:
            continue
        seen_bucket_keys.add(bucket_key)
        selected_bucket_keys.append(bucket_key)
        covered_logical_event_count += bucket_totals[bucket_key]["bucket_logical_event_count"]
        covered_store_materialized_count += bucket_totals[bucket_key]["bucket_store_materialized_count"]

    covered_bucket_count = len(selected_bucket_keys)
    total_bucket_count = len(bucket_totals)
    return {
        "strategy": strategy,
        "logical_weight": logical_weight,
        "materialized_weight": materialized_weight,
        "limit": limit,
        "selected_case_count": len(selected_rows),
        "covered_bucket_count": covered_bucket_count,
        "total_bucket_count": total_bucket_count,
        "predicted_covered_bucket_share": (
            float(covered_bucket_count) / float(total_bucket_count)
            if total_bucket_count > 0
            else 0.0
        ),
        "predicted_covered_logical_event_share": (
            float(covered_logical_event_count) / float(total_logical_event_count)
            if total_logical_event_count > 0
            else 0.0
        ),
        "predicted_covered_store_materialized_share": (
            float(covered_store_materialized_count) / float(total_store_materialized_count)
            if total_store_materialized_count > 0
            else 0.0
        ),
        "selected_case_ids": [row["case_id"] for row in selected_rows],
        "selected_bucket_keys": selected_bucket_keys,
    }


def write_coverage_report(path: Path, report):
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument(
        "--strategy",
        choices=["legacy", "coverage_weighted"],
        default="legacy",
    )
    parser.add_argument("--logical-weight", type=float, default=1.0)
    parser.add_argument("--materialized-weight", type=float, default=2.0)
    parser.add_argument("--coverage-report")
    args = parser.parse_args()

    rows = load_rows(Path(args.manifest))
    selected = choose_cases(
        rows,
        args.limit,
        args.strategy,
        args.logical_weight,
        args.materialized_weight,
    )
    write_selected(Path(args.output), selected)
    if args.coverage_report:
        write_coverage_report(
            Path(args.coverage_report),
            build_coverage_report(
                rows,
                selected,
                args.strategy,
                args.logical_weight,
                args.materialized_weight,
                args.limit,
            ),
        )


if __name__ == "__main__":
    main()
