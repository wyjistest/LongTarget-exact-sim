#!/usr/bin/env python3
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import analyze_two_stage_coverage_attribution as coverage_attr  # noqa: E402
import analyze_two_stage_selector_candidate_classes as selector_classes  # noqa: E402
import benchmark_sample_vs_fasim as sample_vs_fasim  # noqa: E402


DEFAULT_STRATEGIES = (
    "score_band_dominant",
    "score_band_75_79",
    "score_band_lt_75",
)
RULE_STRAND_OBJECT_STRATEGIES = (
    "rule_strand_strongest",
    "rule_strand_dominant",
)
ALL_STRATEGIES = (
    "support1_margin_present",
    "support2",
    "strongest_low_support_or_margin",
    "support3plus_low_support_or_margin",
    "score_band_80_84",
    "score_band_75_79",
    "score_band_lt_75",
    "score_band_70_74",
    "score_band_65_69",
    "score_band_lt_65",
    "score_band_lt_75_dominant",
    "score_band_dominant",
    "rule_strand_strongest",
    "rule_strand_dominant",
)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _update_strict_scores(dest: dict[tuple, float], source: dict[tuple, float]) -> None:
    for key, score in source.items():
        prev = dest.get(key)
        if prev is None or score > prev:
            dest[key] = float(score)


def _top_hit_retention(ref_scores: dict[tuple, float], cand_keys: set[tuple]) -> float:
    if not ref_scores:
        return 1.0
    top_score = max(ref_scores.values())
    top_hit_keys = {key for key, score in ref_scores.items() if score == top_score}
    if not top_hit_keys:
        return 1.0
    return len(top_hit_keys & cand_keys) / len(top_hit_keys)


def _quality_summary(ref_scores: dict[tuple, float], cand_keys: set[tuple]) -> dict[str, float | int]:
    return {
        "covered_strict_key_count": len(cand_keys),
        "top_hit_retention": _top_hit_retention(ref_scores, cand_keys),
        "top5_retention": sample_vs_fasim._topk_retention(ref_scores, cand_keys, k=5),
        "top10_retention": sample_vs_fasim._topk_retention(ref_scores, cand_keys, k=10),
        "score_weighted_recall": sample_vs_fasim._score_weighted_recall(ref_scores, cand_keys),
    }


def _hit_covered(hit: dict[str, object], windows: list[dict[str, object]]) -> bool:
    return bool(coverage_attr._matching_windows(hit, windows))


def _covered_keys(
    legacy_rows: dict[tuple, dict[str, object]],
    windows: list[dict[str, object]],
) -> set[tuple]:
    if not windows:
        return set()
    covered: set[tuple] = set()
    for key, hit in legacy_rows.items():
        if _hit_covered(hit, windows):
            covered.add(key)
    return covered


def _window_identity(row: dict[str, object]) -> dict[str, object]:
    return {
        "task_index": int(row["task_index"]),
        "window_id": int(row["window_id"]),
        "strand": row["strand"],
        "rule": int(row["rule"]),
        "window_start_in_seq": int(row["window_start_in_seq"]),
        "window_end_in_seq": int(row["window_end_in_seq"]),
        "best_seed_score": int(row["best_seed_score"]),
        "second_best_seed_score": row["second_best_seed_score"],
        "margin": row["margin"],
        "support_count": int(row["support_count"]),
        "window_bp": int(row["window_bp"]),
        "reject_reason": str(row.get("reject_reason", "")),
    }


def _resolved_score_band(strategy: str, dominant_score_band: str, dominant_lt75_band: str) -> str:
    if strategy == "score_band_80_84":
        return "80_84"
    if strategy == "score_band_75_79":
        return "75_79"
    if strategy == "score_band_lt_75":
        return "lt_75"
    if strategy == "score_band_70_74":
        return "70_74"
    if strategy == "score_band_65_69":
        return "65_69"
    if strategy == "score_band_lt_65":
        return "lt_65"
    if strategy == "score_band_lt_75_dominant":
        return dominant_lt75_band
    if strategy == "score_band_dominant":
        return dominant_score_band
    return ""


def _resolved_candidate_object(strategy: str) -> str:
    if strategy in RULE_STRAND_OBJECT_STRATEGIES:
        return strategy
    return ""


def _choose_rule_strand_object(
    task_info: dict[str, object],
    *,
    strategy: str,
    task_rule_strand_stats: dict[tuple[int, str], dict[str, object]] | None,
) -> dict[str, object] | None:
    objects = list(task_info.get("rule_strand_objects", []))
    if not objects:
        return None
    if strategy == "rule_strand_strongest":
        return objects[0]
    if strategy != "rule_strand_dominant":
        return None

    stats = task_rule_strand_stats or {}
    return min(
        objects,
        key=lambda item: (
            -int(stats.get((int(item["rule"]), str(item["strand"])), {}).get("top10_missing_count", 0)),
            -float(stats.get((int(item["rule"]), str(item["strand"])), {}).get("score_weighted_missing", 0.0)),
            -int(stats.get((int(item["rule"]), str(item["strand"])), {}).get("overall_missing_count", 0)),
            selector_classes._window_sort_key(item["representative_row"]),
        ),
    )


def _choose_candidate_row(
    task_info: dict[str, object],
    *,
    strategy: str,
    singleton_override: int,
    resolved_score_band: str,
    task_rule_strand_stats: dict[tuple[int, str], dict[str, object]] | None,
) -> dict[str, object] | None:
    uncovered_rows = list(task_info.get("uncovered_rejected_rows", []))
    if not uncovered_rows:
        return None
    if strategy in RULE_STRAND_OBJECT_STRATEGIES:
        selected_object = _choose_rule_strand_object(
            task_info,
            strategy=strategy,
            task_rule_strand_stats=task_rule_strand_stats,
        )
        if selected_object is None:
            return None
        return selected_object["representative_row"]

    if strategy == "strongest_low_support_or_margin":
        candidates = [
            row for row in uncovered_rows if str(row.get("reject_reason", "")) == "low_support_or_margin"
        ]
    elif resolved_score_band in selector_classes.SCORE_LT_75_BANDS:
        candidates = [
            row
            for row in uncovered_rows
            if selector_classes._intrinsic_window_class(
                row,
                singleton_override=singleton_override,
            )
            == "score_lt_85"
            and selector_classes._score_lt_85_band(row) == "lt_75"
            and selector_classes._score_lt_75_band(row) == resolved_score_band
        ]
    elif resolved_score_band:
        candidates = [
            row
            for row in uncovered_rows
            if selector_classes._intrinsic_window_class(
                row,
                singleton_override=singleton_override,
            )
            == "score_lt_85"
            and selector_classes._score_lt_85_band(row) == resolved_score_band
        ]
    else:
        candidates = [
            row
            for row in uncovered_rows
            if selector_classes._intrinsic_window_class(
                row,
                singleton_override=singleton_override,
            )
            == strategy
        ]
    if not candidates:
        return None
    return min(candidates, key=selector_classes._window_sort_key)


def _render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Non-Empty Candidate-Class Replay",
        "",
        f"- panel_summary: {summary['panel_summary']}",
        f"- candidate_label: {summary['candidate_label']}",
        "- metrics: predicted_* values are offline coverage proxies, not runtime-measured outputs",
        "",
    ]
    for strategy_payload in summary["strategies"]:
        aggregate = strategy_payload["aggregate"]
        lines.extend(
            [
                f"## {strategy_payload['strategy']}",
                "",
                f"- resolved_score_band: {strategy_payload['resolved_score_band'] or 'n/a'}",
                f"- resolved_candidate_object: {strategy_payload['resolved_candidate_object'] or 'n/a'}",
                f"- eligible_task_count: {aggregate['eligible_task_count']}",
                f"- predicted_rescued_task_count: {aggregate['predicted_rescued_task_count']}",
                f"- predicted_rescued_window_count: {aggregate['predicted_rescued_window_count']}",
                f"- baseline_top5_retention: {aggregate['baseline_top5_retention']:.12g}",
                f"- predicted_top5_retention: {aggregate['predicted_top5_retention']:.12g}",
                f"- baseline_score_weighted_recall: {aggregate['baseline_score_weighted_recall']:.12g}",
                f"- predicted_score_weighted_recall: {aggregate['predicted_score_weighted_recall']:.12g}",
                "",
                "| anchor | eligible_tasks | rescued_tasks | rescued_windows | predicted_top5 | predicted_score_weighted |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for tile in strategy_payload["per_tile"]:
            lines.append(
                f"| {tile['anchor_label']} | {tile['eligible_task_count']} | {tile['predicted_rescued_task_count']} | "
                f"{tile['predicted_rescued_window_count']} | {tile['predicted']['top5_retention']:.12g} | "
                f"{tile['predicted']['score_weighted_recall']:.12g} |"
            )
        lines.append("")
    return "\n".join(lines)


def replay_panel_candidate_classes(
    panel_summary_path: Path | str,
    *,
    candidate_label: str,
    max_kept_windows: int,
    non_empty_score_gap: int,
    singleton_override: int,
    strategies: list[str],
) -> dict[str, object]:
    panel_summary_path = Path(panel_summary_path).resolve()
    panel_summary = _load_json(panel_summary_path)
    selected_microanchors = list(panel_summary.get("selected_microanchors", []))
    selector_summary = selector_classes.analyze_panel_candidate_classes(
        panel_summary_path,
        candidate_label=candidate_label,
        max_kept_windows=max_kept_windows,
        non_empty_score_gap=non_empty_score_gap,
        singleton_override=singleton_override,
    )
    dominant_score_band = str(selector_summary.get("recommended_score_lt_85_band", ""))
    dominant_lt75_band = str(selector_summary.get("recommended_score_lt_75_band", ""))

    strategy_state: dict[str, dict[str, object]] = {}
    for strategy in strategies:
        strategy_state[strategy] = {
            "resolved_score_band": _resolved_score_band(
                strategy,
                dominant_score_band,
                dominant_lt75_band,
            ),
            "resolved_candidate_object": _resolved_candidate_object(strategy),
            "ref_scores": {},
            "baseline_keys": set(),
            "predicted_keys": set(),
            "eligible_task_count": 0,
            "predicted_rescued_task_count": 0,
            "predicted_rescued_window_count": 0,
            "predicted_rescued_bp_total": 0,
            "baseline_threshold_skipped_after_gate_total": 0,
            "predicted_threshold_skipped_after_gate_total": 0,
            "baseline_windows_after_gate_total": 0,
            "predicted_windows_after_gate_total": 0,
            "baseline_refine_total_bp_total": 0,
            "predicted_refine_total_bp_total": 0,
            "per_tile": [],
        }

    for panel_item in selected_microanchors:
        context = selector_classes._load_tile_context(panel_item, candidate_label=candidate_label)
        candidate_run = dict(context["report"]["runs"][candidate_label])
        by_task: dict[int, list[dict[str, object]]] = defaultdict(list)
        for row in context["debug_rows"]:
            by_task[int(row["task_index"])].append(row)

        task_infos: dict[int, dict[str, object]] = {}
        for task_index, task_rows in sorted(by_task.items()):
            task_infos[task_index] = selector_classes._classify_task(
                task_index,
                task_rows,
                max_kept_windows=max_kept_windows,
                non_empty_score_gap=non_empty_score_gap,
                singleton_override=singleton_override,
            )
        ranked_keys = sample_vs_fasim._sorted_strict_score_keys(context["legacy_summary"].strict_scores)
        missing_keys = [
            key for key in ranked_keys if key not in context["candidate_summary"].strict_keys
        ]
        rule_strand_missing_payload = selector_classes._collect_rule_strand_missing_items(
            context,
            task_infos,
            ranked_keys=ranked_keys,
            missing_keys=missing_keys,
        )
        rule_strand_stats_by_task = rule_strand_missing_payload["stats_by_task"]

        base_kept_rows = [
            row for row in context["debug_rows"] if int(row["after_gate"]) == 1
        ]
        base_covered_keys = _covered_keys(context["legacy_rows"], base_kept_rows)
        baseline_quality = _quality_summary(context["legacy_summary"].strict_scores, base_covered_keys)
        baseline_threshold_skipped_after_gate = int(candidate_run.get("threshold_skipped_after_gate", 0))
        baseline_windows_after_gate = int(candidate_run.get("windows_after_gate", len(base_kept_rows)))
        baseline_refine_total_bp = int(
            candidate_run.get(
                "refine_total_bp",
                sum(int(row["window_bp"]) for row in base_kept_rows),
            )
        )
        eligible_task_count = sum(
            1 for info in task_infos.values() if info["blocker"] == "no_singleton_missing_margin"
        )

        for strategy in strategies:
            resolved_score_band = str(strategy_state[strategy]["resolved_score_band"])
            rescued_rows: list[dict[str, object]] = []
            for task_index in sorted(task_infos):
                info = task_infos[task_index]
                if info["blocker"] != "no_singleton_missing_margin":
                    continue
                selected_row = _choose_candidate_row(
                    info,
                    strategy=strategy,
                    singleton_override=singleton_override,
                    resolved_score_band=resolved_score_band,
                    task_rule_strand_stats=rule_strand_stats_by_task.get(task_index),
                )
                if selected_row is not None:
                    rescued_rows.append(selected_row)

            predicted_rows = list(base_kept_rows) + rescued_rows
            predicted_covered_keys = _covered_keys(context["legacy_rows"], predicted_rows)
            predicted_quality = _quality_summary(context["legacy_summary"].strict_scores, predicted_covered_keys)
            rescued_bp_total = sum(int(row["window_bp"]) for row in rescued_rows)
            predicted_threshold_skipped_after_gate = baseline_threshold_skipped_after_gate
            predicted_windows_after_gate = baseline_windows_after_gate + len(rescued_rows)
            predicted_refine_total_bp = baseline_refine_total_bp + rescued_bp_total
            tile_payload = {
                "anchor_label": panel_item.get("anchor_label", ""),
                "selection_bucket_length_bp": int(panel_item.get("selection_bucket_length_bp", 0)),
                "selection_kind": panel_item.get("selection_kind", ""),
                "selection_rank": int(panel_item.get("selection_rank", 0)),
                "start_bp": int(panel_item.get("start_bp", 0)),
                "length_bp": int(panel_item.get("length_bp", 0)),
                "report_path": str(context["report_path"]),
                "eligible_task_count": eligible_task_count,
                "predicted_rescued_task_count": len({int(row["task_index"]) for row in rescued_rows}),
                "predicted_rescued_window_count": len(rescued_rows),
                "predicted_rescued_bp_total": rescued_bp_total,
                "baseline": {
                    **baseline_quality,
                    "threshold_skipped_after_gate": baseline_threshold_skipped_after_gate,
                    "windows_after_gate": baseline_windows_after_gate,
                    "refine_total_bp": baseline_refine_total_bp,
                },
                "predicted": {
                    **predicted_quality,
                    "threshold_skipped_after_gate": predicted_threshold_skipped_after_gate,
                    "windows_after_gate": predicted_windows_after_gate,
                    "refine_total_bp": predicted_refine_total_bp,
                },
                "delta": {
                    "top_hit_retention": float(predicted_quality["top_hit_retention"])
                    - float(baseline_quality["top_hit_retention"]),
                    "top5_retention": float(predicted_quality["top5_retention"])
                    - float(baseline_quality["top5_retention"]),
                    "top10_retention": float(predicted_quality["top10_retention"])
                    - float(baseline_quality["top10_retention"]),
                    "score_weighted_recall": float(predicted_quality["score_weighted_recall"])
                    - float(baseline_quality["score_weighted_recall"]),
                    "threshold_skipped_after_gate": predicted_threshold_skipped_after_gate
                    - baseline_threshold_skipped_after_gate,
                    "windows_after_gate": predicted_windows_after_gate - baseline_windows_after_gate,
                    "refine_total_bp": predicted_refine_total_bp - baseline_refine_total_bp,
                },
                "rescued_windows": [_window_identity(row) for row in rescued_rows],
            }
            state = strategy_state[strategy]
            _update_strict_scores(state["ref_scores"], context["legacy_summary"].strict_scores)
            state["baseline_keys"].update(base_covered_keys)
            state["predicted_keys"].update(predicted_covered_keys)
            state["eligible_task_count"] += eligible_task_count
            state["predicted_rescued_task_count"] += tile_payload["predicted_rescued_task_count"]
            state["predicted_rescued_window_count"] += tile_payload["predicted_rescued_window_count"]
            state["predicted_rescued_bp_total"] += rescued_bp_total
            state["baseline_threshold_skipped_after_gate_total"] += baseline_threshold_skipped_after_gate
            state["predicted_threshold_skipped_after_gate_total"] += predicted_threshold_skipped_after_gate
            state["baseline_windows_after_gate_total"] += baseline_windows_after_gate
            state["predicted_windows_after_gate_total"] += predicted_windows_after_gate
            state["baseline_refine_total_bp_total"] += baseline_refine_total_bp
            state["predicted_refine_total_bp_total"] += predicted_refine_total_bp
            state["per_tile"].append(tile_payload)

    strategy_payloads: list[dict[str, object]] = []
    for strategy in strategies:
        state = strategy_state[strategy]
        ref_scores = dict(state["ref_scores"])
        baseline_quality = _quality_summary(ref_scores, set(state["baseline_keys"]))
        predicted_quality = _quality_summary(ref_scores, set(state["predicted_keys"]))
        aggregate = {
            "tile_count": len(selected_microanchors),
            "eligible_task_count": int(state["eligible_task_count"]),
            "predicted_rescued_task_count": int(state["predicted_rescued_task_count"]),
            "predicted_rescued_window_count": int(state["predicted_rescued_window_count"]),
            "predicted_rescued_bp_total": int(state["predicted_rescued_bp_total"]),
            "baseline_covered_strict_key_count": int(baseline_quality["covered_strict_key_count"]),
            "predicted_covered_strict_key_count": int(predicted_quality["covered_strict_key_count"]),
            "baseline_top_hit_retention": float(baseline_quality["top_hit_retention"]),
            "predicted_top_hit_retention": float(predicted_quality["top_hit_retention"]),
            "baseline_top5_retention": float(baseline_quality["top5_retention"]),
            "predicted_top5_retention": float(predicted_quality["top5_retention"]),
            "baseline_top10_retention": float(baseline_quality["top10_retention"]),
            "predicted_top10_retention": float(predicted_quality["top10_retention"]),
            "baseline_score_weighted_recall": float(baseline_quality["score_weighted_recall"]),
            "predicted_score_weighted_recall": float(predicted_quality["score_weighted_recall"]),
            "delta_top_hit_retention": float(predicted_quality["top_hit_retention"])
            - float(baseline_quality["top_hit_retention"]),
            "delta_top5_retention": float(predicted_quality["top5_retention"])
            - float(baseline_quality["top5_retention"]),
            "delta_top10_retention": float(predicted_quality["top10_retention"])
            - float(baseline_quality["top10_retention"]),
            "delta_score_weighted_recall": float(predicted_quality["score_weighted_recall"])
            - float(baseline_quality["score_weighted_recall"]),
            "baseline_threshold_skipped_after_gate_total": int(
                state["baseline_threshold_skipped_after_gate_total"]
            ),
            "predicted_threshold_skipped_after_gate_total": int(
                state["predicted_threshold_skipped_after_gate_total"]
            ),
            "baseline_windows_after_gate_total": int(state["baseline_windows_after_gate_total"]),
            "predicted_windows_after_gate_total": int(state["predicted_windows_after_gate_total"]),
            "baseline_refine_total_bp_total": int(state["baseline_refine_total_bp_total"]),
            "predicted_refine_total_bp_total": int(state["predicted_refine_total_bp_total"]),
            "delta_threshold_skipped_after_gate_total": int(
                state["predicted_threshold_skipped_after_gate_total"]
            )
            - int(state["baseline_threshold_skipped_after_gate_total"]),
            "delta_windows_after_gate_total": int(state["predicted_windows_after_gate_total"])
            - int(state["baseline_windows_after_gate_total"]),
            "delta_refine_total_bp_total": int(state["predicted_refine_total_bp_total"])
            - int(state["baseline_refine_total_bp_total"]),
        }
        strategy_payloads.append(
            {
                "strategy": strategy,
                "resolved_score_band": str(state["resolved_score_band"]),
                "resolved_candidate_object": str(state["resolved_candidate_object"]),
                "aggregate": aggregate,
                "per_tile": state["per_tile"],
            }
        )

    return {
        "panel_summary": str(panel_summary_path),
        "candidate_label": candidate_label,
        "selector_config": {
            "max_kept_windows": max_kept_windows,
            "non_empty_score_gap": non_empty_score_gap,
            "singleton_override": singleton_override,
        },
        "strategies": strategy_payloads,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline replay of non-empty selector candidate-class rescues on a fixed panel tile set.",
    )
    parser.add_argument("--panel-summary", required=True, help="panel summary.json containing selected_microanchors")
    parser.add_argument(
        "--candidate-label",
        default="",
        help="candidate run label (defaults to panel gated_run_label)",
    )
    parser.add_argument("--max-kept-windows", required=True, type=int, help="selector max kept windows")
    parser.add_argument("--non-empty-score-gap", required=True, type=int, help="selector non-empty score gap")
    parser.add_argument("--singleton-override", required=True, type=int, help="selector singleton override floor")
    parser.add_argument(
        "--strategy",
        action="append",
        default=None,
        choices=ALL_STRATEGIES,
        help="candidate-class replay strategy (repeatable)",
    )
    parser.add_argument("--output-dir", required=True, help="output directory for summary.json and summary.md")
    args = parser.parse_args()

    panel_summary_path = Path(args.panel_summary).resolve()
    panel_summary = _load_json(panel_summary_path)
    candidate_label = args.candidate_label or str(panel_summary.get("gated_run_label", ""))
    if not candidate_label:
        raise RuntimeError(
            "missing candidate run label; pass --candidate-label or set gated_run_label in panel summary"
        )
    strategies = list(args.strategy or DEFAULT_STRATEGIES)
    output_dir = Path(args.output_dir).resolve()

    summary = replay_panel_candidate_classes(
        panel_summary_path,
        candidate_label=candidate_label,
        max_kept_windows=args.max_kept_windows,
        non_empty_score_gap=args.non_empty_score_gap,
        singleton_override=args.singleton_override,
        strategies=strategies,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
