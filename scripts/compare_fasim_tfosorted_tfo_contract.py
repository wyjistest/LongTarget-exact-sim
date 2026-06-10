#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


TOPK_MODES = ("score", "stability", "nt_score")


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = reader.fieldnames or []
        if "TFO sequence" not in header:
            raise SystemExit(f"path={path} missing_column=TFO sequence")
        return header, list(reader)


def _digest(values: list[str] | set[str]) -> str:
    ordered = sorted(values)
    return hashlib.sha256(("\n".join(ordered) + "\n").encode("utf-8")).hexdigest()


def _row_key(row: dict[str, str], header: list[str]) -> str:
    return "\t".join(row.get(column, "") for column in header)


def _as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value == "":
        return float("-inf")
    try:
        return float(value)
    except ValueError:
        return float("-inf")


def _sort_key(row: dict[str, str], header: list[str], mode: str) -> tuple[float, ...] | tuple[tuple[float, ...], str]:
    if mode == "score":
        metric = (
            _as_float(row, "Score"),
            _as_float(row, "Nt(bp)"),
            _as_float(row, "MeanStability"),
        )
    elif mode == "stability":
        metric = (
            _as_float(row, "MeanStability"),
            _as_float(row, "Nt(bp)"),
            _as_float(row, "Score"),
        )
    elif mode == "nt_score":
        metric = (
            _as_float(row, "Nt(bp)"),
            _as_float(row, "Score"),
            _as_float(row, "MeanStability"),
        )
    else:
        raise ValueError(f"unknown mode: {mode}")
    return metric, _row_key(row, header)


def _topk(rows: list[dict[str, str]], header: list[str], mode: str, k: int) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: _sort_key(row, header, mode), reverse=True)[:k]


def _norm_gapless_tfo(value: str) -> str:
    return value.replace("-", "").upper()


def _multiset_delta(
    baseline: Counter[str], candidate: Counter[str]
) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    extra: list[str] = []
    for key in sorted(set(baseline) | set(candidate)):
        if baseline[key] > candidate[key]:
            missing.extend([key] * (baseline[key] - candidate[key]))
        elif candidate[key] > baseline[key]:
            extra.extend([key] * (candidate[key] - baseline[key]))
    return missing, extra


def _print_optional(label: str, values: set[str] | list[str]) -> None:
    if values:
        print(f"{label}={sorted(values)[0]}")
    else:
        print(f"{label}=none")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Fasim TFOsorted outputs at TFO-sequence and top-k TFO levels."
    )
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--require-topk-equal", action="store_true")
    parser.add_argument("--require-tfo-set-equal", action="store_true")
    args = parser.parse_args()

    if args.k <= 0:
        raise SystemExit("--k must be positive")

    baseline_header, baseline_rows = _read_rows(args.baseline)
    candidate_header, candidate_rows = _read_rows(args.candidate)
    if baseline_header != candidate_header:
        print(f"header_equal=false")
        print(f"baseline_header={json.dumps(baseline_header, ensure_ascii=True)}")
        print(f"candidate_header={json.dumps(candidate_header, ensure_ascii=True)}")
    else:
        print("header_equal=true")

    print(f"baseline={args.baseline}")
    print(f"candidate={args.candidate}")
    print(f"baseline_rows={len(baseline_rows)}")
    print(f"candidate_rows={len(candidate_rows)}")

    baseline_full = {_row_key(row, baseline_header) for row in baseline_rows}
    candidate_full = {_row_key(row, candidate_header) for row in candidate_rows}
    print(f"full_missing_rows={len(baseline_full - candidate_full)}")
    print(f"full_extra_rows={len(candidate_full - baseline_full)}")
    print(f"full_rows_equal={str(baseline_full == candidate_full).lower()}")

    baseline_tfo = {row["TFO sequence"] for row in baseline_rows if row.get("TFO sequence")}
    candidate_tfo = {row["TFO sequence"] for row in candidate_rows if row.get("TFO sequence")}
    missing_tfo = baseline_tfo - candidate_tfo
    extra_tfo = candidate_tfo - baseline_tfo
    print(f"tfo_baseline_unique={len(baseline_tfo)}")
    print(f"tfo_candidate_unique={len(candidate_tfo)}")
    print(f"tfo_missing={len(missing_tfo)}")
    print(f"tfo_extra={len(extra_tfo)}")
    print(f"tfo_equal={str(baseline_tfo == candidate_tfo).lower()}")
    print(f"tfo_baseline_digest={_digest(baseline_tfo)}")
    print(f"tfo_candidate_digest={_digest(candidate_tfo)}")
    _print_optional("first_missing_tfo", missing_tfo)
    _print_optional("first_extra_tfo", extra_tfo)

    baseline_tfo_counts = Counter(
        row["TFO sequence"] for row in baseline_rows if row.get("TFO sequence")
    )
    candidate_tfo_counts = Counter(
        row["TFO sequence"] for row in candidate_rows if row.get("TFO sequence")
    )
    missing_multi, extra_multi = _multiset_delta(baseline_tfo_counts, candidate_tfo_counts)
    print(f"tfo_multiset_missing={len(missing_multi)}")
    print(f"tfo_multiset_extra={len(extra_multi)}")
    print(f"tfo_multiset_equal={str(baseline_tfo_counts == candidate_tfo_counts).lower()}")
    _print_optional("first_missing_tfo_multiset", missing_multi)
    _print_optional("first_extra_tfo_multiset", extra_multi)

    baseline_gapless = {
        _norm_gapless_tfo(row["TFO sequence"])
        for row in baseline_rows
        if row.get("TFO sequence")
    }
    candidate_gapless = {
        _norm_gapless_tfo(row["TFO sequence"])
        for row in candidate_rows
        if row.get("TFO sequence")
    }
    missing_gapless = baseline_gapless - candidate_gapless
    extra_gapless = candidate_gapless - baseline_gapless
    print(f"gapless_tfo_baseline_unique={len(baseline_gapless)}")
    print(f"gapless_tfo_candidate_unique={len(candidate_gapless)}")
    print(f"gapless_tfo_missing={len(missing_gapless)}")
    print(f"gapless_tfo_extra={len(extra_gapless)}")
    print(f"gapless_tfo_equal={str(baseline_gapless == candidate_gapless).lower()}")
    print(f"gapless_tfo_baseline_digest={_digest(baseline_gapless)}")
    print(f"gapless_tfo_candidate_digest={_digest(candidate_gapless)}")
    _print_optional("first_missing_gapless_tfo", missing_gapless)
    _print_optional("first_extra_gapless_tfo", extra_gapless)

    all_topk_equal = True
    for mode in TOPK_MODES:
        baseline_top = _topk(baseline_rows, baseline_header, mode, args.k)
        candidate_top = _topk(candidate_rows, candidate_header, mode, args.k)
        baseline_top_tfo = [row.get("TFO sequence", "") for row in baseline_top]
        candidate_top_tfo = [row.get("TFO sequence", "") for row in candidate_top]
        baseline_top_full = [_row_key(row, baseline_header) for row in baseline_top]
        candidate_top_full = [_row_key(row, candidate_header) for row in candidate_top]
        tfo_equal = baseline_top_tfo == candidate_top_tfo
        full_equal = baseline_top_full == candidate_top_full
        all_topk_equal = all_topk_equal and tfo_equal
        print(f"top{args.k}_tfo_{mode}_equal={str(tfo_equal).lower()}")
        print(f"top{args.k}_full_{mode}_equal={str(full_equal).lower()}")
        print(f"top{args.k}_tfo_{mode}_baseline_digest={_digest(baseline_top_tfo)}")
        print(f"top{args.k}_tfo_{mode}_candidate_digest={_digest(candidate_top_tfo)}")
        print(
            f"top{args.k}_tfo_{mode}_baseline="
            f"{json.dumps(baseline_top_tfo, ensure_ascii=True)}"
        )
        print(
            f"top{args.k}_tfo_{mode}_candidate="
            f"{json.dumps(candidate_top_tfo, ensure_ascii=True)}"
        )

    if args.require_tfo_set_equal and baseline_tfo != candidate_tfo:
        return 1
    if args.require_topk_equal and not all_topk_equal:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
