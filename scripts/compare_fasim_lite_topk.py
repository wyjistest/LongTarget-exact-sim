#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _row_key(row: dict[str, str]) -> str:
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


def _topk_digest(rows: list[dict[str, str]], mode: str, k: int) -> tuple[str, list[str]]:
    top_rows = sorted(rows, key=lambda row: (_sort_key(row, mode), _row_key(row)), reverse=True)[:k]
    keys = [_row_key(row) for row in top_rows]
    digest = hashlib.sha256(("\n".join(keys) + "\n").encode()).hexdigest()
    return digest, keys


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare top-k rows from Fasim lite outputs.")
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument(
        "--mode",
        action="append",
        choices=("score", "stability", "nt_score"),
        help="Ranking mode. May be repeated. Defaults to all supported modes.",
    )
    args = parser.parse_args()

    modes = args.mode or ["score", "stability", "nt_score"]
    baseline_rows = _read_rows(args.baseline)
    candidate_rows = _read_rows(args.candidate)
    baseline_set = {_row_key(row) for row in baseline_rows}
    candidate_set = {_row_key(row) for row in candidate_rows}

    print(f"baseline={args.baseline}")
    print(f"candidate={args.candidate}")
    print(f"baseline_rows={len(baseline_rows)}")
    print(f"candidate_rows={len(candidate_rows)}")
    print(f"baseline_unique_rows={len(baseline_set)}")
    print(f"candidate_unique_rows={len(candidate_set)}")
    print(f"missing_rows={len(baseline_set - candidate_set)}")
    print(f"extra_rows={len(candidate_set - baseline_set)}")

    all_equal = True
    for mode in modes:
        baseline_digest, baseline_top = _topk_digest(baseline_rows, mode, args.k)
        candidate_digest, candidate_top = _topk_digest(candidate_rows, mode, args.k)
        equal = baseline_top == candidate_top
        all_equal = all_equal and equal
        print(f"top{args.k}_{mode}_equal={str(equal).lower()}")
        print(f"top{args.k}_{mode}_baseline_digest={baseline_digest}")
        print(f"top{args.k}_{mode}_candidate_digest={candidate_digest}")

    return 0 if all_equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
