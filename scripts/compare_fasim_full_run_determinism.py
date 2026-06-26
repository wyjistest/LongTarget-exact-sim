#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
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

TFOSORTED_COLUMNS = [
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "MeanStability",
    "MeanIdentity(%)",
    "Strand",
    "Rule",
    "Score",
    "Nt(bp)",
    "Class",
    "MidPoint",
    "Center",
    "TFO sequence",
    "TTS sequence",
]

SCHEMAS = {
    "lite": LITE_COLUMNS,
    "tfosorted": TFOSORTED_COLUMNS,
}

TOPK_MODES = ("score", "stability", "nt_score")


def _sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_text(values: list[str]) -> str:
    return hashlib.sha256(("\n".join(values) + "\n").encode("utf-8")).hexdigest()


def _read_rows(path: Path) -> tuple[str, list[str], list[dict[str, str]]]:
    with path.open("rt", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        header = reader.fieldnames or []
        schema = next((name for name, columns in SCHEMAS.items() if columns == header), None)
        if schema is None:
            raise SystemExit(f"unsupported schema for {path}: {header}")
        rows: list[dict[str, str]] = []
        for row_number, row in enumerate(reader, 2):
            if None in row:
                raise SystemExit(f"bad row width in {path} row {row_number}")
            rows.append(row)
        return schema, header, rows


def _row_key(row: dict[str, str], columns: list[str]) -> str:
    return "\t".join(row.get(column, "") for column in columns)


def _float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, ""))
    except ValueError:
        return float("-inf")


def _topk_sort_key(row: dict[str, str], columns: list[str], mode: str) -> tuple[tuple[float, ...], str]:
    if mode == "score":
        metric = (_float(row, "Score"), _float(row, "Nt(bp)"), _float(row, "MeanStability"))
    elif mode == "stability":
        metric = (_float(row, "MeanStability"), _float(row, "Nt(bp)"), _float(row, "Score"))
    elif mode == "nt_score":
        metric = (_float(row, "Nt(bp)"), _float(row, "Score"), _float(row, "MeanStability"))
    else:
        raise ValueError(mode)
    return metric, _row_key(row, columns)


def _topk_digest(rows: list[dict[str, str]], columns: list[str], mode: str, k: int) -> str:
    ranked = sorted(rows, key=lambda row: _topk_sort_key(row, columns, mode), reverse=True)
    keys = [_row_key(row, columns) for row in ranked[:k]]
    return _digest_text(keys)


def _counter_delta(a: Counter[str], b: Counter[str]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    extra: list[str] = []
    for key in sorted(set(a) | set(b)):
        if a[key] > b[key]:
            missing.extend([key] * (a[key] - b[key]))
        elif b[key] > a[key]:
            extra.extend([key] * (b[key] - a[key]))
    return missing, extra


def _first(values: list[str] | set[str]) -> str:
    if not values:
        return "none"
    return sorted(values)[0]


def _classification(byte_stable: bool, set_stable: bool, multiset_stable: bool, topk_stable: bool) -> str:
    if byte_stable and set_stable and multiset_stable and topk_stable:
        return "fully_deterministic"
    if set_stable and not multiset_stable:
        return "order_or_duplicate_count_nondeterminism"
    if set_stable:
        return "order_only_nondeterminism"
    if topk_stable:
        return "row_set_nondeterminism_topk_stable"
    return "row_set_nondeterminism_topk_risk"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare repeated Fasim full-run outputs for byte, set, multiset and top-k determinism."
    )
    parser.add_argument("--run", action="append", required=True, type=Path)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output-summary", required=True, type=Path)
    parser.add_argument("--output-pairs", required=True, type=Path)
    args = parser.parse_args()

    if len(args.run) < 2:
        raise SystemExit("at least two --run files are required")
    if args.k <= 0:
        raise SystemExit("--k must be positive")

    runs = []
    schema0: str | None = None
    columns0: list[str] | None = None
    for index, path in enumerate(args.run, 1):
        schema, columns, rows = _read_rows(path)
        if schema0 is None:
            schema0 = schema
            columns0 = columns
        elif schema != schema0 or columns != columns0:
            raise SystemExit(f"schema mismatch at run {index}: {path}")
        assert columns0 is not None
        keys = [_row_key(row, columns0) for row in rows]
        unique_keys = sorted(set(keys))
        counter = Counter(keys)
        topk = {mode: _topk_digest(rows, columns0, mode, args.k) for mode in TOPK_MODES}
        runs.append(
            {
                "index": index,
                "path": path,
                "rows": rows,
                "row_count": len(rows),
                "unique_count": len(unique_keys),
                "byte_digest": _sha256_bytes(path),
                "set_digest": _digest_text(unique_keys),
                "multiset_digest": _digest_text(sorted(counter.elements())),
                "set": set(unique_keys),
                "counter": counter,
                "topk": topk,
            }
        )

    pair_rows = []
    max_set_missing = 0
    max_set_extra = 0
    max_multi_missing = 0
    max_multi_extra = 0
    first_missing_set = "none"
    first_extra_set = "none"
    first_missing_multi = "none"
    first_extra_multi = "none"
    for left_pos in range(len(runs)):
        for right_pos in range(left_pos + 1, len(runs)):
            left = runs[left_pos]
            right = runs[right_pos]
            left_set = left["set"]
            right_set = right["set"]
            assert isinstance(left_set, set)
            assert isinstance(right_set, set)
            set_missing = sorted(left_set - right_set)
            set_extra = sorted(right_set - left_set)
            left_counter = left["counter"]
            right_counter = right["counter"]
            assert isinstance(left_counter, Counter)
            assert isinstance(right_counter, Counter)
            multi_missing, multi_extra = _counter_delta(left_counter, right_counter)
            topk_equal_by_mode = {
                mode: left["topk"][mode] == right["topk"][mode]  # type: ignore[index]
                for mode in TOPK_MODES
            }
            pair_rows.append(
                {
                    "left": str(left["index"]),
                    "right": str(right["index"]),
                    "byte_equal": str(left["byte_digest"] == right["byte_digest"]).lower(),
                    "set_equal": str(not set_missing and not set_extra).lower(),
                    "multiset_equal": str(not multi_missing and not multi_extra).lower(),
                    "set_missing": str(len(set_missing)),
                    "set_extra": str(len(set_extra)),
                    "multiset_missing": str(len(multi_missing)),
                    "multiset_extra": str(len(multi_extra)),
                    "top_score_equal": str(topk_equal_by_mode["score"]).lower(),
                    "top_stability_equal": str(topk_equal_by_mode["stability"]).lower(),
                    "top_nt_score_equal": str(topk_equal_by_mode["nt_score"]).lower(),
                    "first_missing_set": _first(set_missing),
                    "first_extra_set": _first(set_extra),
                    "first_missing_multiset": _first(multi_missing),
                    "first_extra_multiset": _first(multi_extra),
                }
            )
            max_set_missing = max(max_set_missing, len(set_missing))
            max_set_extra = max(max_set_extra, len(set_extra))
            max_multi_missing = max(max_multi_missing, len(multi_missing))
            max_multi_extra = max(max_multi_extra, len(multi_extra))
            if first_missing_set == "none":
                first_missing_set = _first(set_missing)
            if first_extra_set == "none":
                first_extra_set = _first(set_extra)
            if first_missing_multi == "none":
                first_missing_multi = _first(multi_missing)
            if first_extra_multi == "none":
                first_extra_multi = _first(multi_extra)

    byte_stable = len({str(run["byte_digest"]) for run in runs}) == 1
    set_stable = len({str(run["set_digest"]) for run in runs}) == 1
    multiset_stable = len({str(run["multiset_digest"]) for run in runs}) == 1
    topk_stable = {
        mode: len({str(run["topk"][mode]) for run in runs}) == 1  # type: ignore[index]
        for mode in TOPK_MODES
    }
    all_topk_stable = all(topk_stable.values())

    summary = [
        ("runs", str(len(runs))),
        ("schema", schema0 or "unknown"),
        ("k", str(args.k)),
        ("byte_stable", str(byte_stable).lower()),
        ("set_stable", str(set_stable).lower()),
        ("multiset_stable", str(multiset_stable).lower()),
        (f"top{args.k}_score_stable", str(topk_stable["score"]).lower()),
        (f"top{args.k}_stability_stable", str(topk_stable["stability"]).lower()),
        (f"top{args.k}_nt_score_stable", str(topk_stable["nt_score"]).lower()),
        ("min_rows", str(min(int(run["row_count"]) for run in runs))),
        ("max_rows", str(max(int(run["row_count"]) for run in runs))),
        ("min_unique_rows", str(min(int(run["unique_count"]) for run in runs))),
        ("max_unique_rows", str(max(int(run["unique_count"]) for run in runs))),
        ("max_pair_set_missing", str(max_set_missing)),
        ("max_pair_set_extra", str(max_set_extra)),
        ("max_pair_multiset_missing", str(max_multi_missing)),
        ("max_pair_multiset_extra", str(max_multi_extra)),
        ("first_missing_set", first_missing_set),
        ("first_extra_set", first_extra_set),
        ("first_missing_multiset", first_missing_multi),
        ("first_extra_multiset", first_extra_multi),
        ("classification", _classification(byte_stable, set_stable, multiset_stable, all_topk_stable)),
    ]

    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary.write_text("\n".join(f"{k}={v}" for k, v in summary) + "\n")

    args.output_pairs.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "left",
        "right",
        "byte_equal",
        "set_equal",
        "multiset_equal",
        "set_missing",
        "set_extra",
        "multiset_missing",
        "multiset_extra",
        "top_score_equal",
        "top_stability_equal",
        "top_nt_score_equal",
        "first_missing_set",
        "first_extra_set",
        "first_missing_multiset",
        "first_extra_multiset",
    ]
    with args.output_pairs.open("wt", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        writer.writerows(pair_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
