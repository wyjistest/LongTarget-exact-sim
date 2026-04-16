#!/usr/bin/env python3
import argparse
import csv
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


def choose_cases(rows, limit):
    if not rows or limit <= 0:
        return []

    enriched_rows = enrich_rows(rows)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()

    rows = load_rows(Path(args.manifest))
    selected = choose_cases(rows, args.limit)
    write_selected(Path(args.output), selected)


if __name__ == "__main__":
    main()
