#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


SCORE_BINS = [
    ("<60", None, 60),
    ("60-79", 60, 80),
    ("80-99", 80, 100),
    ("100-119", 100, 120),
    ("120-139", 120, 140),
    ("140-159", 140, 160),
    ("160-199", 160, 200),
    (">=200", 200, None),
]

SIZE_BINS = [
    ("<55", None, 55),
    ("55-64", 55, 65),
    ("65-79", 65, 80),
    ("80-119", 80, 120),
    (">=120", 120, None),
]


def bin_value(value: int, bins: list[tuple[str, int | None, int | None]]) -> str:
    for label, lower, upper in bins:
        if lower is not None and value < lower:
            continue
        if upper is not None and value >= upper:
            continue
        return label
    raise ValueError(f"value did not match any bin: {value}")


def as_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    if value == "":
        return 0
    return int(float(value))


def emit_counter(title: str, counter: Counter[tuple[str, str]], limit: int = 0) -> None:
    print(title)
    print("bin\tkeep\tskip\ttotal\tskip_fraction")
    labels = sorted({label for label, _decision in counter})
    if limit > 0:
        labels = sorted(
            labels,
            key=lambda label: (
                0.0 if counter[(label, "keep")] + counter[(label, "skip")] == 0
                else counter[(label, "skip")] / (counter[(label, "keep")] + counter[(label, "skip")]),
                counter[(label, "skip")] + counter[(label, "keep")],
                label,
            ),
            reverse=True,
        )[:limit]
    for label in labels:
        keep = counter[(label, "keep")]
        skip = counter[(label, "skip")]
        total = keep + skip
        fraction = 0.0 if total == 0 else skip / total
        print(f"{label}\t{keep}\t{skip}\t{total}\t{fraction:.6f}")


def emit_ordered_counter(
    title: str,
    counter: Counter[tuple[str, str]],
    labels: list[str],
) -> None:
    print(title)
    print("bin\tkeep\tskip\ttotal\tskip_fraction")
    for label in labels:
        keep = counter[(label, "keep")]
        skip = counter[(label, "skip")]
        total = keep + skip
        if total == 0:
            continue
        fraction = skip / total
        print(f"{label}\t{keep}\t{skip}\t{total}\t{fraction:.6f}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize a GASAL2 limited-traceback attempt export TSV."
    )
    parser.add_argument("attempt_export", type=Path)
    parser.add_argument("--scoreinfo-limit", type=int, default=20)
    args = parser.parse_args()

    total = 0
    decision_counts: Counter[str] = Counter()
    score_bins: Counter[tuple[str, str]] = Counter()
    target_size_bins: Counter[tuple[str, str]] = Counter()
    nt_min_bins: Counter[tuple[str, str]] = Counter()
    rule_like_bins: Counter[tuple[str, str]] = Counter()

    with args.attempt_export.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            decision = row.get("decision", "")
            if decision not in ("keep", "skip"):
                continue
            total += 1
            decision_counts[decision] += 1
            score_bins[(bin_value(as_int(row, "prealign_score"), SCORE_BINS), decision)] += 1
            target_size_bins[(bin_value(as_int(row, "target_size"), SIZE_BINS), decision)] += 1
            nt_min_bins[(bin_value(as_int(row, "nt_min_length"), SIZE_BINS), decision)] += 1
            rule_like_bins[(row.get("scoreinfo_index", ""), decision)] += 1

    keep = decision_counts["keep"]
    skip = decision_counts["skip"]
    print(f"rows={total}")
    print(f"keep_rows={keep}")
    print(f"skip_rows={skip}")
    print(f"skip_fraction={0.0 if total == 0 else skip / total:.6f}")
    emit_ordered_counter(
        "prealign_score_bin",
        score_bins,
        [label for label, _lower, _upper in SCORE_BINS],
    )
    emit_ordered_counter(
        "target_size_bin",
        target_size_bins,
        [label for label, _lower, _upper in SIZE_BINS],
    )
    emit_ordered_counter(
        "nt_min_length_bin",
        nt_min_bins,
        [label for label, _lower, _upper in SIZE_BINS],
    )
    emit_counter("scoreinfo_index", rule_like_bins, limit=args.scoreinfo_limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
