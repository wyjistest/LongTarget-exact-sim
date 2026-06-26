#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


PREFIX = "benchmark.fasim_top5_gasal2_phase_"


def _metrics(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.startswith(PREFIX):
            key = key[len(PREFIX) :]
        elif key.startswith("benchmark."):
            key = key[len("benchmark.") :]
        else:
            continue
        values[key] = value.strip()
    return values


def _int(values: dict[str, str], key: str) -> int:
    try:
        return int(values[key])
    except KeyError as exc:
        raise SystemExit(f"missing required metric: {key}") from exc
    except ValueError as exc:
        raise SystemExit(f"invalid integer metric {key}: {values[key]}") from exc


def _float(values: dict[str, str], key: str) -> float:
    try:
        return float(values[key])
    except KeyError as exc:
        raise SystemExit(f"missing required metric: {key}") from exc
    except ValueError as exc:
        raise SystemExit(f"invalid float metric {key}: {values[key]}") from exc


def _ratio(num: float, den: float) -> str:
    if den == 0.0:
        return "nan"
    return f"{num / den:.6f}"


def _dominant_stage(
    triplex_seconds: float,
    sort_filter_seconds: float,
    span_check_seconds: float,
    rank_map_seconds: float,
    selected_scan_minus_children_seconds: float,
) -> str:
    stages = [
        ("triplex_materialization", triplex_seconds),
        ("sort_filter", sort_filter_seconds),
        ("span_check", span_check_seconds),
        ("rank_map", rank_map_seconds),
        ("selected_scan_other", selected_scan_minus_children_seconds),
    ]
    return max(stages, key=lambda item: item[1])[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2 convert sort/filter top-N breakdown."
    )
    parser.add_argument("--stderr", required=True, type=Path)
    parser.add_argument("--label", default="run")
    args = parser.parse_args()

    values = _metrics(args.stderr)
    raw_triplexes = _int(values, "gasal2_convert_triplexes_raw")
    emit_candidates = _int(values, "gasal2_emit_candidates")
    emit_rows = (
        int(values.get("gasal2_emit_rows_lite", "0"))
        + int(values.get("gasal2_emit_rows_full", "0"))
    )
    convert_wall = _float(values, "gasal2_convert_wall_seconds")
    selected_scan_seconds = _float(values, "gasal2_convert_selected_scan_seconds")
    span_check_seconds = _float(values, "gasal2_convert_span_check_seconds")
    triplex_seconds = _float(values, "gasal2_convert_triplex_seconds")
    alignment_seconds = _float(values, "gasal2_convert_alignment_seconds")
    sort_seconds = _float(values, "gasal2_convert_sort_seconds")
    filter_seconds = _float(values, "gasal2_convert_filter_seconds")
    rank_map_seconds = _float(values, "gasal2_convert_rank_map_seconds")
    sort_filter_seconds = sort_seconds + filter_seconds
    selected_scan_minus_children_seconds = (
        selected_scan_seconds - span_check_seconds - triplex_seconds - rank_map_seconds
    )
    convert_accounted_seconds = selected_scan_seconds + sort_filter_seconds
    convert_unattributed_seconds = convert_wall - convert_accounted_seconds
    dominant_stage = _dominant_stage(
        triplex_seconds,
        sort_filter_seconds,
        span_check_seconds,
        rank_map_seconds,
        selected_scan_minus_children_seconds,
    )
    sort_topn_first_priority = (
        dominant_stage == "sort_filter" and sort_filter_seconds >= triplex_seconds
    )
    cpu_breakdown_decision = (
        "sort_topn_candidate"
        if sort_topn_first_priority
        else "triplex_materialization_or_preconvert_frontier_first"
    )

    output = {
        "label": args.label,
        "convert_triplexes_raw": str(raw_triplexes),
        "emit_candidates": str(emit_candidates),
        "emit_rows": str(emit_rows),
        "selected_scan_seconds": f"{selected_scan_seconds:.6f}",
        "span_check_seconds": f"{span_check_seconds:.6f}",
        "triplex_seconds": f"{triplex_seconds:.6f}",
        "alignment_seconds": f"{alignment_seconds:.6f}",
        "sort_seconds": f"{sort_seconds:.6f}",
        "filter_seconds": f"{filter_seconds:.6f}",
        "rank_map_seconds": f"{rank_map_seconds:.6f}",
        "sort_filter_seconds": f"{sort_filter_seconds:.6f}",
        "selected_scan_minus_children_seconds": (
            f"{selected_scan_minus_children_seconds:.6f}"
        ),
        "convert_accounted_seconds": f"{convert_accounted_seconds:.6f}",
        "convert_unattributed_seconds": f"{convert_unattributed_seconds:.6f}",
        "selected_scan_share": _ratio(selected_scan_seconds, convert_wall),
        "span_check_share": _ratio(span_check_seconds, convert_wall),
        "triplex_share": _ratio(triplex_seconds, convert_wall),
        "alignment_share": _ratio(alignment_seconds, convert_wall),
        "selected_scan_minus_children_share": _ratio(
            selected_scan_minus_children_seconds, convert_wall
        ),
        "convert_unattributed_share": _ratio(
            convert_unattributed_seconds, convert_wall
        ),
        "sort_share": _ratio(sort_seconds, convert_wall),
        "filter_share": _ratio(filter_seconds, convert_wall),
        "rank_map_share": _ratio(rank_map_seconds, convert_wall),
        "sort_filter_share": _ratio(sort_filter_seconds, convert_wall),
        "triplex_to_sort_filter_ratio": _ratio(
            triplex_seconds, sort_filter_seconds
        ),
        "dominant_convert_stage": dominant_stage,
        "sort_topn_first_priority": "1" if sort_topn_first_priority else "0",
        "cpu_breakdown_decision": cpu_breakdown_decision,
        "rows_per_raw_triplex": _ratio(emit_rows, raw_triplexes),
        "candidates_per_raw_triplex": _ratio(emit_candidates, raw_triplexes),
        "raw_triplexes_per_output_row": _ratio(raw_triplexes, emit_rows),
    }
    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
