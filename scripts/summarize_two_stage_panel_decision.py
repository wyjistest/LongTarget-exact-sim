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
SELECTOR_BLOCKER_ORDER = (
    "max_kept_windows",
    "no_singleton_missing_margin",
    "singleton_override",
    "covered_by_kept",
    "score_gap",
)
SELECTOR_BLOCKER_COUNTER_KEYS = {
    "max_kept_windows": "selective_fallback_non_empty_rejected_by_max_kept_windows_tasks",
    "no_singleton_missing_margin": "selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks",
    "singleton_override": "selective_fallback_non_empty_rejected_by_singleton_override_tasks",
    "covered_by_kept": "selective_fallback_non_empty_rejected_as_covered_by_kept_tasks",
    "score_gap": "selective_fallback_non_empty_rejected_by_score_gap_tasks",
}
SELECTOR_ABLATION_BY_BLOCKER = {
    "max_kept_windows": "raise_non_empty_max_kept_windows",
    "no_singleton_missing_margin": "expand_rescue_object_beyond_singleton_missing_margin",
    "singleton_override": "lower_singleton_override",
    "covered_by_kept": "audit_window_coverage_and_rescue_semantics",
    "score_gap": "raise_non_empty_score_gap",
}


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


def _dominant_selector_blocker(blocker_totals: dict[str, int]) -> str:
    if not any(blocker_totals.values()):
        return ""
    return max(
        SELECTOR_BLOCKER_ORDER,
        key=lambda name: (int(blocker_totals.get(name, 0)), -SELECTOR_BLOCKER_ORDER.index(name)),
    )


def _render_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Two-Stage Panel Decision Summary",
        "",
        f"- compare_summary: {summary['compare_summary']}",
        f"- attribution_summary: {summary['attribution_summary']}",
        f"- candidate_run_label: {summary['candidate_run_label']}",
        f"- recommended_next_step: {summary['recommended_next_step']}",
        f"- dominant_selector_blocker: {summary['dominant_selector_blocker'] or 'n/a'}",
        f"- recommended_selector_ablation: {summary['recommended_selector_ablation']}",
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
            "## Selector Blockers",
            "",
            f"- selector_candidate_tasks: {summary['selector_candidate_tasks']}",
            f"- dominant_selector_blocker: {summary['dominant_selector_blocker'] or 'n/a'}",
            f"- recommended_selector_ablation: {summary['recommended_selector_ablation']}",
            "",
            "| blocker | tasks |",
            "| --- | ---: |",
        ]
    )
    for blocker in SELECTOR_BLOCKER_ORDER:
        lines.append(f"| {blocker} | {summary['selector_blocker_totals'][blocker]} |")
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
    selector_candidate_tasks = int(fallback_totals.get("selective_fallback_non_empty_candidate_tasks", 0))
    selector_blocker_totals = {
        blocker: int(fallback_totals.get(counter_key, 0))
        for blocker, counter_key in SELECTOR_BLOCKER_COUNTER_KEYS.items()
    }
    dominant_selector_blocker = _dominant_selector_blocker(selector_blocker_totals)
    recommended_selector_ablation = (
        SELECTOR_ABLATION_BY_BLOCKER[dominant_selector_blocker]
        if dominant_selector_blocker
        else "observe_quality_only"
    )

    summary = {
        "compare_summary": str(compare_path),
        "attribution_summary": str(attribution_path),
        "candidate_run_label": str(compare.get("candidate_run_label", attribution.get("candidate_label", ""))),
        "fallback_triggered": fallback_triggered,
        "fallback_effective": fallback_effective,
        "candidate_selective_fallback_totals": fallback_totals,
        "selector_candidate_tasks": selector_candidate_tasks,
        "selector_blocker_totals": selector_blocker_totals,
        "dominant_selector_blocker": dominant_selector_blocker,
        "recommended_selector_ablation": recommended_selector_ablation,
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
