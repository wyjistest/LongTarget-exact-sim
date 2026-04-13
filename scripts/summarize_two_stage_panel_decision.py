#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ATTRIBUTION_CLASSES = (
    "inside_kept_window",
    "inside_rejected_window",
    "outside_kept_but_near_kept",
    "far_outside_all_kept",
)
COUNT_VIEWS = ("overall", "top5_missing", "top10_missing")
WEIGHT_VIEW = "score_weighted_missing"
QUALITY_METRICS = ("top5_retention", "top10_retention", "score_weighted_recall")


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _primary_class(shares: dict[str, float]) -> str:
    return max(
        ATTRIBUTION_CLASSES,
        key=lambda name: (float(shares.get(name, 0.0)), -ATTRIBUTION_CLASSES.index(name)),
    )


def _recommended_next_step(primary_weight_class: str) -> str:
    if primary_weight_class == "inside_rejected_window":
        return "non_empty_ambiguity_triggered_selective_fallback"
    if primary_weight_class == "outside_kept_but_near_kept":
        return "refine_pad_merge_sweep"
    if primary_weight_class == "far_outside_all_kept":
        return "prefilter_coverage_expansion"
    return "audit_inside_kept_window_classification"


def _render_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Panel Decision Summary",
        "",
        f"- compare_summary: {summary['compare_summary']}",
        f"- attribution_summary: {summary['attribution_summary']}",
        f"- candidate_run_label: {summary['candidate_run_label']}",
        f"- recommended_next_step: {summary['recommended_next_step']}",
        f"- fallback_triggered: {summary['fallback_triggered']}",
        f"- fallback_effective: {summary['fallback_effective']}",
        "",
        "## Quality Delta",
        "",
        "| metric | delta_mean |",
        "| --- | ---: |",
    ]
    for metric in (
        "top5_retention",
        "top10_retention",
        "score_weighted_recall",
        "threshold_skipped_after_gate",
        "threshold_batch_size_mean",
        "threshold_batched_seconds",
        "refine_total_bp",
    ):
        lines.append(f"| {metric} | {summary['quality_delta'][metric]:.12g} |")
    lines.extend(
        [
            "",
            "## Residual Primary Class",
            "",
            "| view | primary_class |",
            "| --- | --- |",
        ]
    )
    for view, value in summary["residual_primary_class"].items():
        lines.append(f"| {view} | {value} |")
    lines.extend(
        [
            "",
            "## candidate_selective_fallback_totals",
            "",
            "| metric | total |",
            "| --- | ---: |",
        ]
    )
    for key, value in summary["candidate_selective_fallback_totals"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## score_weighted_missing Shares",
            "",
            "| class | share |",
            "| --- | ---: |",
        ]
    )
    weighted = summary["attribution_share_by_class"][WEIGHT_VIEW]
    for class_name in ATTRIBUTION_CLASSES:
        lines.append(f"| {class_name} | {weighted[class_name]:.12g} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Combine panel compare and coverage attribution summaries into one decision report.",
    )
    parser.add_argument("--compare-summary", required=True, help="compare_two_stage_panel_summaries summary.json")
    parser.add_argument("--attribution-summary", required=True, help="coverage attribution panel summary.json")
    parser.add_argument("--output-dir", required=True, help="output directory for summary.json and summary.md")
    args = parser.parse_args()

    compare_path = Path(args.compare_summary).resolve()
    attribution_path = Path(args.attribution_summary).resolve()
    output_dir = Path(args.output_dir).resolve()

    compare = _load_json(compare_path)
    attribution = _load_json(attribution_path)

    aggregate = compare["aggregate"]
    fallback_totals = dict(aggregate.get("candidate_selective_fallback_totals", {}))
    fallback_triggered = int(fallback_totals.get("selective_fallback_triggered_tasks", 0)) > 0
    fallback_effective = fallback_triggered and any(
        float(aggregate[metric]["delta_mean"]) > 0.0 for metric in QUALITY_METRICS
    )

    residual_primary_class: dict[str, str] = {}
    attribution_share_by_class: dict[str, dict[str, float]] = {}
    for view in COUNT_VIEWS:
        shares = {
            class_name: float(attribution["aggregate"][view]["share_by_class"][class_name])
            for class_name in ATTRIBUTION_CLASSES
        }
        attribution_share_by_class[view] = shares
        residual_primary_class[view] = _primary_class(shares)

    weighted_shares = {
        class_name: float(
            attribution["aggregate"][WEIGHT_VIEW]["share_of_missing_weight_by_class"][class_name]
        )
        for class_name in ATTRIBUTION_CLASSES
    }
    attribution_share_by_class[WEIGHT_VIEW] = weighted_shares
    residual_primary_class[WEIGHT_VIEW] = _primary_class(weighted_shares)

    summary = {
        "compare_summary": str(compare_path),
        "attribution_summary": str(attribution_path),
        "candidate_run_label": str(compare.get("candidate_run_label", attribution.get("candidate_label", ""))),
        "fallback_triggered": fallback_triggered,
        "fallback_effective": fallback_effective,
        "candidate_selective_fallback_totals": fallback_totals,
        "quality_delta": {
            metric: float(aggregate[metric]["delta_mean"])
            for metric in (
                "top5_retention",
                "top10_retention",
                "score_weighted_recall",
                "threshold_skipped_after_gate",
                "threshold_batch_size_mean",
                "threshold_batched_seconds",
                "refine_total_bp",
            )
        },
        "residual_primary_class": residual_primary_class,
        "attribution_share_by_class": attribution_share_by_class,
        "recommended_next_step": _recommended_next_step(residual_primary_class[WEIGHT_VIEW]),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_summary_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
