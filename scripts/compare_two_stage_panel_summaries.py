#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


DIFFERENCE_CLASSES = ("none", "ordering_or_format_only", "content_diff")
TILE_KEY_FIELDS = (
    "anchor_label",
    "selection_bucket_length_bp",
    "selection_kind",
    "selection_rank",
    "start_bp",
    "length_bp",
)
NUMERIC_METRICS = (
    "top5_retention",
    "top10_retention",
    "score_weighted_recall",
    "threshold_skipped_after_gate",
    "threshold_batch_size_mean",
    "threshold_batched_seconds",
    "refine_total_bp",
)
FALLBACK_COUNTERS = (
    "selective_fallback_triggered_tasks",
    "selective_fallback_non_empty_triggered_tasks",
    "selective_fallback_selected_windows",
    "selective_fallback_selected_bp_total",
)
COMPARISON_METRICS = {"top5_retention", "top10_retention", "score_weighted_recall"}
RUN_METRICS = {
    "threshold_skipped_after_gate",
    "threshold_batch_size_mean",
    "threshold_batched_seconds",
    "refine_total_bp",
}


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _round(value: float) -> float:
    return round(float(value), 12)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return _round(sum(values) / len(values))


def _tile_key(item: dict[str, object]) -> tuple[object, ...]:
    return tuple(item[field] for field in TILE_KEY_FIELDS)


def _tile_identity(item: dict[str, object]) -> dict[str, object]:
    return {field: item[field] for field in TILE_KEY_FIELDS}


def _tile_map(summary: dict[str, object]) -> dict[tuple[object, ...], dict[str, object]]:
    items = summary.get("selected_microanchors", [])
    if not isinstance(items, list):
        raise RuntimeError("selected_microanchors must be a list")
    tile_map: dict[tuple[object, ...], dict[str, object]] = {}
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("selected_microanchors items must be objects")
        key = _tile_key(item)
        if key in tile_map:
            raise RuntimeError(f"duplicate tile key: {key}")
        tile_map[key] = item
    return tile_map


def _run_payload(item: dict[str, object], run_label: str) -> dict[str, object]:
    runs = item.get("runs", {})
    if not isinstance(runs, dict) or run_label not in runs:
        raise RuntimeError(f"missing runs[{run_label}] for tile {_tile_identity(item)}")
    payload = runs[run_label]
    if not isinstance(payload, dict):
        raise RuntimeError(f"runs[{run_label}] must be an object for tile {_tile_identity(item)}")
    return payload


def _comparison_payload(item: dict[str, object], run_label: str) -> dict[str, object]:
    payload = item.get("comparisons_vs_legacy", {})
    if not isinstance(payload, dict) or run_label not in payload:
        raise RuntimeError(f"missing comparisons_vs_legacy[{run_label}] for tile {_tile_identity(item)}")
    comparison = payload[run_label]
    if not isinstance(comparison, dict):
        raise RuntimeError(f"comparisons_vs_legacy[{run_label}] must be an object for tile {_tile_identity(item)}")
    return comparison


def _numeric_value(item: dict[str, object], run_label: str, metric: str) -> float:
    if metric in COMPARISON_METRICS:
        payload = _comparison_payload(item, run_label)
    elif metric in RUN_METRICS:
        payload = _run_payload(item, run_label)
    else:
        raise RuntimeError(f"unsupported metric: {metric}")
    if metric not in payload:
        raise RuntimeError(f"missing {metric} for tile {_tile_identity(item)} in run {run_label}")
    return float(payload[metric])


def _difference_class(item: dict[str, object], run_label: str) -> str:
    comparison = _comparison_payload(item, run_label)
    value = str(comparison.get("difference_class", ""))
    if value not in DIFFERENCE_CLASSES:
        raise RuntimeError(f"invalid difference_class {value!r} for tile {_tile_identity(item)} in run {run_label}")
    return value


def _mismatch_examples(
    baseline_keys: set[tuple[object, ...]],
    candidate_keys: set[tuple[object, ...]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    missing_in_candidate = [
        dict(zip(TILE_KEY_FIELDS, key)) for key in sorted(baseline_keys - candidate_keys)[:5]
    ]
    missing_in_baseline = [
        dict(zip(TILE_KEY_FIELDS, key)) for key in sorted(candidate_keys - baseline_keys)[:5]
    ]
    return missing_in_candidate, missing_in_baseline


def _render_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Panel Summary Comparison",
        "",
        f"- baseline_panel_summary: {summary['baseline_panel_summary']}",
        f"- candidate_panel_summary: {summary['candidate_panel_summary']}",
        f"- baseline_run_label: {summary['baseline_run_label']}",
        f"- candidate_run_label: {summary['candidate_run_label']}",
        f"- shared_tile_count: {summary['shared_tile_count']}",
        "",
        "## Aggregate Delta",
        "",
        "| metric | baseline_mean | candidate_mean | delta_mean |",
        "| --- | ---: | ---: | ---: |",
    ]
    for metric in NUMERIC_METRICS:
        payload = summary["aggregate"][metric]
        lines.append(
            f"| {metric} | {payload['baseline_mean']:.12g} | {payload['candidate_mean']:.12g} | {payload['delta_mean']:.12g} |"
        )
    lines.extend(
        [
            "",
            "## difference_class Counts",
            "",
            "| lane | none | ordering_or_format_only | content_diff |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for lane in ("baseline", "candidate"):
        counts = summary["aggregate"]["difference_class_counts"][lane]
        lines.append(
            f"| {lane} | {counts['none']} | {counts['ordering_or_format_only']} | {counts['content_diff']} |"
        )
    lines.extend(["", "## difference_class Transitions", "", "| transition | count |", "| --- | ---: |"])
    for transition, count in sorted(summary["aggregate"]["difference_class_transitions"].items()):
        lines.append(f"| {transition} | {count} |")
    lines.extend(
        [
            "",
            "## candidate_selective_fallback_totals",
            "",
            "| metric | total |",
            "| --- | ---: |",
        ]
    )
    for key, value in summary["aggregate"]["candidate_selective_fallback_totals"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Per Tile",
            "",
            "| anchor | bucket_bp | selection_kind | selection_rank | start_bp | length_bp | baseline_top5 | candidate_top5 | delta_top5 | baseline_diff | candidate_diff |",
            "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for tile in summary["per_tile"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(tile["anchor_label"]),
                    str(tile["selection_bucket_length_bp"]),
                    str(tile["selection_kind"]),
                    str(tile["selection_rank"]),
                    str(tile["start_bp"]),
                    str(tile["length_bp"]),
                    f"{tile['baseline']['top5_retention']:.12g}",
                    f"{tile['candidate']['top5_retention']:.12g}",
                    f"{tile['delta']['top5_retention']:.12g}",
                    str(tile["baseline"]["difference_class"]),
                    str(tile["candidate"]["difference_class"]),
                ]
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two heavy micro-anchor panel summaries on an identical selected-tile set.",
    )
    parser.add_argument("--baseline-panel-summary", required=True, help="baseline heavy micro-anchor summary.json")
    parser.add_argument("--candidate-panel-summary", required=True, help="candidate heavy micro-anchor summary.json")
    parser.add_argument("--output-dir", required=True, help="output directory for summary.json and summary.md")
    args = parser.parse_args()

    baseline_path = Path(args.baseline_panel_summary).resolve()
    candidate_path = Path(args.candidate_panel_summary).resolve()
    output_dir = Path(args.output_dir).resolve()

    baseline_summary = _load_json(baseline_path)
    candidate_summary = _load_json(candidate_path)
    baseline_run_label = str(baseline_summary.get("gated_run_label", ""))
    candidate_run_label = str(candidate_summary.get("gated_run_label", ""))
    if not baseline_run_label:
        raise RuntimeError(f"missing gated_run_label in {baseline_path}")
    if not candidate_run_label:
        raise RuntimeError(f"missing gated_run_label in {candidate_path}")

    baseline_compare_mode = baseline_summary.get("compare_output_mode")
    candidate_compare_mode = candidate_summary.get("compare_output_mode")
    if (
        baseline_compare_mode is not None
        and candidate_compare_mode is not None
        and baseline_compare_mode != candidate_compare_mode
    ):
        raise RuntimeError(
            f"compare_output_mode mismatch: {baseline_compare_mode!r} vs {candidate_compare_mode!r}"
        )

    baseline_tiles = _tile_map(baseline_summary)
    candidate_tiles = _tile_map(candidate_summary)
    baseline_keys = set(baseline_tiles)
    candidate_keys = set(candidate_tiles)
    if baseline_keys != candidate_keys:
        missing_in_candidate, missing_in_baseline = _mismatch_examples(baseline_keys, candidate_keys)
        raise RuntimeError(
            "tile set mismatch between baseline and candidate panel summaries: "
            f"missing_in_candidate={missing_in_candidate} missing_in_baseline={missing_in_baseline}"
        )

    metric_values: dict[str, dict[str, list[float]]] = {
        metric: {"baseline": [], "candidate": [], "delta": []} for metric in NUMERIC_METRICS
    }
    difference_class_counts = {
        "baseline": {name: 0 for name in DIFFERENCE_CLASSES},
        "candidate": {name: 0 for name in DIFFERENCE_CLASSES},
    }
    difference_class_transitions: dict[str, int] = {}
    candidate_fallback_totals = {name: 0 for name in FALLBACK_COUNTERS}
    per_tile: list[dict[str, object]] = []

    for key in sorted(baseline_keys):
        baseline_item = baseline_tiles[key]
        candidate_item = candidate_tiles[key]
        baseline_metrics: dict[str, object] = {}
        candidate_metrics: dict[str, object] = {}
        delta_metrics: dict[str, object] = {}

        for metric in NUMERIC_METRICS:
            baseline_value = _round(_numeric_value(baseline_item, baseline_run_label, metric))
            candidate_value = _round(_numeric_value(candidate_item, candidate_run_label, metric))
            delta_value = _round(candidate_value - baseline_value)
            baseline_metrics[metric] = baseline_value
            candidate_metrics[metric] = candidate_value
            delta_metrics[metric] = delta_value
            metric_values[metric]["baseline"].append(baseline_value)
            metric_values[metric]["candidate"].append(candidate_value)
            metric_values[metric]["delta"].append(delta_value)

        baseline_diff = _difference_class(baseline_item, baseline_run_label)
        candidate_diff = _difference_class(candidate_item, candidate_run_label)
        baseline_metrics["difference_class"] = baseline_diff
        candidate_metrics["difference_class"] = candidate_diff
        transition_key = f"{baseline_diff}->{candidate_diff}"
        delta_metrics["difference_class"] = transition_key
        difference_class_counts["baseline"][baseline_diff] += 1
        difference_class_counts["candidate"][candidate_diff] += 1
        difference_class_transitions[transition_key] = difference_class_transitions.get(transition_key, 0) + 1

        candidate_run = _run_payload(candidate_item, candidate_run_label)
        for counter in FALLBACK_COUNTERS:
            candidate_fallback_totals[counter] += int(candidate_run.get(counter, 0) or 0)

        per_tile.append(
            {
                **_tile_identity(baseline_item),
                "baseline_report_path": str(baseline_item.get("report_path", "")),
                "candidate_report_path": str(candidate_item.get("report_path", "")),
                "baseline": baseline_metrics,
                "candidate": candidate_metrics,
                "delta": delta_metrics,
            }
        )

    aggregate = {
        metric: {
            "baseline_mean": _mean(metric_values[metric]["baseline"]),
            "candidate_mean": _mean(metric_values[metric]["candidate"]),
            "delta_mean": _mean(metric_values[metric]["delta"]),
        }
        for metric in NUMERIC_METRICS
    }
    aggregate["difference_class_counts"] = difference_class_counts
    aggregate["difference_class_transitions"] = dict(sorted(difference_class_transitions.items()))
    aggregate["candidate_selective_fallback_totals"] = candidate_fallback_totals

    summary = {
        "baseline_panel_summary": str(baseline_path),
        "candidate_panel_summary": str(candidate_path),
        "baseline_run_label": baseline_run_label,
        "candidate_run_label": candidate_run_label,
        "tile_key_fields": list(TILE_KEY_FIELDS),
        "shared_tile_count": len(per_tile),
        "aggregate": aggregate,
        "per_tile": per_tile,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
