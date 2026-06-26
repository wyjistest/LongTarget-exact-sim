#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value == "":
        return default
    return float(value)


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    if value == "":
        return default
    return int(float(value))


def row_key(row: dict[str, str]) -> str:
    columns = [
        "Chr",
        "StartInGenome",
        "EndInGenome",
        "Strand",
        "Rule",
        "QueryStart",
        "QueryEnd",
        "StartInSeq",
        "EndInSeq",
        "Direction",
        "Score",
        "Nt(bp)",
        "MeanIdentity(%)",
        "MeanStability",
    ]
    return "\t".join(row.get(column, "") for column in columns)


def stability_sort_key(row: dict[str, str]) -> tuple[float, float, float, str]:
    return (
        as_float(row, "MeanStability", float("-inf")),
        as_float(row, "Nt(bp)", float("-inf")),
        as_float(row, "Score", float("-inf")),
        row_key(row),
    )


def interval_distance(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    overlap = min(a_end, b_end) - max(a_start, b_start)
    if overlap >= 0:
        return 0
    return min(abs(a_start - b_end), abs(b_start - a_end))


def attempt_output_interval(row: dict[str, str]) -> tuple[int, int]:
    start = as_int(row, "output_global_start", -1)
    end = as_int(row, "output_global_end", -1)
    if start >= 0 and end >= 0:
        return start, end
    return (
        as_int(row, "target_global_start", -1),
        as_int(row, "target_global_end", -1),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Map top-stability lite rows to GASAL2 pre-traceback attempts."
    )
    parser.add_argument("--baseline-lite", required=True, type=Path)
    parser.add_argument("--attempt-export", required=True, type=Path)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--near-bp", type=int, default=8)
    parser.add_argument("--max-attempts-per-row", type=int, default=8)
    args = parser.parse_args()

    lite_rows = read_tsv(args.baseline_lite)
    attempts = read_tsv(args.attempt_export)
    top_rows = sorted(lite_rows, key=stability_sort_key, reverse=True)[: args.top_k]

    print(
        "rank\trow_start\trow_end\trow_score\trow_nt\trow_stability\t"
        "matched_attempts\tkept_attempts\tskipped_attempts\tbest_prealign_score\t"
        "best_kept_prealign_score\tbest_skipped_prealign_score\tattempts"
    )
    for rank, row in enumerate(top_rows, 1):
        row_start = as_int(row, "StartInGenome")
        row_end = as_int(row, "EndInGenome")
        matched: list[tuple[int, int, int, int, dict[str, str]]] = []
        for attempt in attempts:
            attempt_start, attempt_end = attempt_output_interval(attempt)
            if attempt_start < 0 or attempt_end < 0:
                continue
            distance = interval_distance(row_start, row_end, attempt_start, attempt_end)
            if distance <= args.near_bp:
                overlap = max(0, min(row_end, attempt_end) - max(row_start, attempt_start))
                matched.append((distance, -overlap, attempt_start, attempt_end, attempt))
        matched.sort(
            key=lambda item: (
                item[0],
                item[1],
                -as_int(item[4], "prealign_score"),
                as_int(item[4], "scoreinfo_index"),
                as_int(item[4], "position"),
            )
        )
        kept = [item for item in matched if item[4].get("decision") == "keep"]
        skipped = [item for item in matched if item[4].get("decision") == "skip"]
        best = max((as_int(item[4], "prealign_score") for item in matched), default=0)
        best_kept = max((as_int(item[4], "prealign_score") for item in kept), default=0)
        best_skipped = max((as_int(item[4], "prealign_score") for item in skipped), default=0)
        attempt_text = []
        for distance, neg_overlap, attempt_start, attempt_end, attempt in matched[: args.max_attempts_per_row]:
            attempt_text.append(
                ",".join(
                    [
                        f"d={distance}",
                        f"ov={-neg_overlap}",
                        f"decision={attempt.get('decision', '')}",
                        f"score={attempt.get('prealign_score', '')}",
                        f"size={attempt.get('target_size', '')}",
                        f"global={attempt_start}-{attempt_end}",
                        f"local={attempt.get('start', '')}+{attempt.get('cutlength', '')}",
                        f"si={attempt.get('scoreinfo_index', '')}",
                    ]
                )
            )
        print(
            "\t".join(
                [
                    str(rank),
                    str(row_start),
                    str(row_end),
                    row.get("Score", ""),
                    row.get("Nt(bp)", ""),
                    row.get("MeanStability", ""),
                    str(len(matched)),
                    str(len(kept)),
                    str(len(skipped)),
                    str(best),
                    str(best_kept),
                    str(best_skipped),
                    "; ".join(attempt_text),
                ]
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
