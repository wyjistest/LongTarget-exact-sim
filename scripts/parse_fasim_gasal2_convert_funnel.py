#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


PREFIX = "benchmark.fasim_top5_gasal2_phase_"


def _parse_metrics(path: Path) -> dict[str, str]:
    metrics: dict[str, str] = {}
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
        metrics[key] = value.strip()
    return metrics


def _int_metric(metrics: dict[str, str], key: str) -> int:
    try:
        return int(metrics[key])
    except KeyError as exc:
        raise SystemExit(f"missing required metric: {key}") from exc
    except ValueError as exc:
        raise SystemExit(f"invalid integer metric {key}: {metrics[key]}") from exc


def _float_metric(metrics: dict[str, str], key: str) -> float:
    try:
        return float(metrics[key])
    except KeyError as exc:
        raise SystemExit(f"missing required metric: {key}") from exc
    except ValueError as exc:
        raise SystemExit(f"invalid float metric {key}: {metrics[key]}") from exc


def _ratio(num: float, den: float) -> str:
    if den == 0.0:
        return "nan"
    return f"{num / den:.6f}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize GASAL2 convert funnel telemetry from Fasim stderr."
    )
    parser.add_argument("--stderr", required=True, type=Path)
    parser.add_argument("--label", default="run")
    args = parser.parse_args()

    metrics = _parse_metrics(args.stderr)

    input_alignments = _int_metric(metrics, "gasal2_convert_input_alignments")
    raw_triplexes = _int_metric(metrics, "gasal2_convert_triplexes_raw")
    emit_candidates = _int_metric(metrics, "gasal2_emit_candidates")
    emit_rows_lite = int(metrics.get("gasal2_emit_rows_lite", "0"))
    emit_rows_full = int(metrics.get("gasal2_emit_rows_full", "0"))
    emit_rows = emit_rows_lite + emit_rows_full

    filtered_score = _int_metric(metrics, "gasal2_emit_filtered_score")
    filtered_identity = _int_metric(metrics, "gasal2_emit_filtered_identity")
    filtered_stability = _int_metric(metrics, "gasal2_emit_filtered_stability")
    filtered_nt = _int_metric(metrics, "gasal2_emit_filtered_nt")
    filtered_total = (
        filtered_score + filtered_identity + filtered_stability + filtered_nt
    )

    convert_wall = _float_metric(metrics, "gasal2_convert_wall_seconds")
    selected_scan = _float_metric(metrics, "gasal2_convert_selected_scan_seconds")
    triplex = _float_metric(metrics, "gasal2_convert_triplex_seconds")
    sort = _float_metric(metrics, "gasal2_convert_sort_seconds")
    filter_seconds = _float_metric(metrics, "gasal2_convert_filter_seconds")

    output = {
        "label": args.label,
        "convert_input_alignments": str(input_alignments),
        "convert_triplexes_raw": str(raw_triplexes),
        "emit_candidates": str(emit_candidates),
        "emit_rows": str(emit_rows),
        "emit_filtered_score": str(filtered_score),
        "emit_filtered_identity": str(filtered_identity),
        "emit_filtered_stability": str(filtered_stability),
        "emit_filtered_nt": str(filtered_nt),
        "post_convert_filtered_total": str(filtered_total),
        "triplexes_per_input_alignment": _ratio(raw_triplexes, input_alignments),
        "rows_per_input_alignment": _ratio(emit_rows, input_alignments),
        "post_convert_filtered_per_candidate": _ratio(filtered_total, emit_candidates),
        "selected_scan_share": _ratio(selected_scan, convert_wall),
        "triplex_share": _ratio(triplex, convert_wall),
        "sort_share": _ratio(sort, convert_wall),
        "filter_share": _ratio(filter_seconds, convert_wall),
    }

    shadow_requested = metrics.get("gasal2_preconvert_prune_shadow_requested")
    shadow_active = metrics.get("gasal2_preconvert_prune_shadow_active")
    shadow_attempts = metrics.get("gasal2_preconvert_prune_shadow_attempts")
    shadow_false_negatives = metrics.get(
        "gasal2_preconvert_prune_shadow_false_negatives"
    )
    if (
        shadow_requested is not None
        and shadow_active is not None
        and shadow_attempts is not None
        and shadow_false_negatives is not None
    ):
        shadow_attempt_count = int(shadow_attempts)
        shadow_false_negative_count = int(shadow_false_negatives)
        output.update(
            {
                "preconvert_prune_shadow_requested": shadow_requested,
                "preconvert_prune_shadow_active": shadow_active,
                "preconvert_prune_shadow_attempts": shadow_attempts,
                "preconvert_prune_shadow_false_negatives": shadow_false_negatives,
                "preconvert_prune_shadow_attempts_per_input_alignment": _ratio(
                    shadow_attempt_count, input_alignments
                ),
                "preconvert_prune_shadow_false_negative_rate": _ratio(
                    shadow_false_negative_count, shadow_attempt_count
                ),
            }
        )

    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
