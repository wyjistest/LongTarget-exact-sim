#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


LITE_COLUMNS = [
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


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _row_key(row: dict[str, str]) -> str:
    return "\t".join(row.get(column, "") for column in LITE_COLUMNS)


def _as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value == "":
        return float("-inf")
    return float(value)


def _sort_key(row: dict[str, str], mode: str) -> tuple[float, ...]:
    if mode == "score":
        return (_as_float(row, "Score"), _as_float(row, "Nt(bp)"), _as_float(row, "MeanStability"))
    if mode == "stability":
        return (_as_float(row, "MeanStability"), _as_float(row, "Nt(bp)"), _as_float(row, "Score"))
    if mode == "nt_score":
        return (_as_float(row, "Nt(bp)"), _as_float(row, "Score"), _as_float(row, "MeanStability"))
    raise ValueError(f"unknown mode: {mode}")


def _topk_rows(rows: list[dict[str, str]], mode: str, k: int) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: (_sort_key(row, mode), _row_key(row)), reverse=True)[:k]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract deterministic top-k rows from a Fasim lite output.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--mode",
        action="append",
        choices=("score", "stability", "nt_score"),
        help="Ranking mode. May be repeated. Defaults to all supported modes.",
    )
    args = parser.parse_args()

    if args.k <= 0:
        raise SystemExit("--k must be positive")

    modes = args.mode or ["score", "stability", "nt_score"]
    rows = _read_rows(args.input)
    selected: dict[str, dict[str, str]] = {}
    for mode in modes:
        for row in _topk_rows(rows, mode, args.k):
            selected[_row_key(row)] = row

    ordered_rows = sorted(selected.values(), key=lambda row: _row_key(row))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LITE_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered_rows)

    print(f"input={args.input}")
    print(f"output={args.output}")
    print(f"rows={len(rows)}")
    print(f"topk_union_rows={len(ordered_rows)}")
    print(f"k={args.k}")
    print(f"modes={','.join(modes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
