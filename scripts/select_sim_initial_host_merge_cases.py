#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path


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


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def choose_cases(rows, limit):
    if not rows or limit <= 0:
        return []

    summary_bins = quantize_tertiles(rows, "summary_count")
    materialized_bins = quantize_tertiles(rows, "store_materialized_count")
    prune_bins = quantize_tertiles(rows, "prune_ratio")

    buckets = {}
    for row in rows:
        key = (
            summary_bins[row["case_id"]],
            materialized_bins[row["case_id"]],
            prune_bins[row["case_id"]],
        )
        buckets.setdefault(key, []).append(row)

    representatives = []
    for key, bucket_rows in buckets.items():
        chosen = max(
            bucket_rows,
            key=lambda row: (int(row["logical_event_count"]), row["case_id"]),
        )
        representatives.append((key, chosen))

    representatives.sort(
        key=lambda item: (-int(item[1]["logical_event_count"]), item[1]["case_id"])
    )

    selected = []
    selected_ids = set()
    for _, row in representatives:
        if len(selected) >= limit:
            break
        selected.append(row)
        selected_ids.add(row["case_id"])

    if len(selected) < limit:
        remaining = sorted(
            (row for row in rows if row["case_id"] not in selected_ids),
            key=lambda row: (-int(row["logical_event_count"]), row["case_id"]),
        )
        for row in remaining:
            if len(selected) >= limit:
                break
            selected.append(row)
            selected_ids.add(row["case_id"])

    return selected


def write_selected(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id"], delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({"case_id": row["case_id"]})


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
