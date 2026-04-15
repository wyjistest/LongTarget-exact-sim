#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import benchmark_sample_vs_fasim as sample_vs_fasim  # noqa: E402


RANKING_ORACLE = "oracle_rescue_gain"
RANKING_SPARSE_GAP = "deployable_sparse_gap_v1"
RANKING_SUPPORT_PRESSURE = "deployable_support_pressure_v1"
RANKING_CHOICES = (
    RANKING_ORACLE,
    RANKING_SPARSE_GAP,
    RANKING_SUPPORT_PRESSURE,
)


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _strict_key_tuple(payload: dict[str, object]) -> tuple[int, int, int, int, str, int]:
    return (
        int(payload["query_start"]),
        int(payload["query_end"]),
        int(payload["start_in_genome"]),
        int(payload["end_in_genome"]),
        str(payload["strand"]),
        int(payload["rule"]),
    )


def _update_strict_scores(dest: dict[tuple, float], source: dict[tuple, float]) -> None:
    for key, score in source.items():
        prev = dest.get(key)
        if prev is None or float(score) > prev:
            dest[key] = float(score)


def _top_hit_retention(ref_scores: dict[tuple, float], cand_keys: set[tuple]) -> float:
    if not ref_scores:
        return 1.0
    top_score = max(ref_scores.values())
    top_keys = {key for key, score in ref_scores.items() if score == top_score}
    if not top_keys:
        return 1.0
    return len(top_keys & cand_keys) / len(top_keys)


def _quality_summary(ref_scores: dict[tuple, float], cand_keys: set[tuple]) -> dict[str, float | int]:
    return {
        "covered_strict_key_count": len(cand_keys),
        "top_hit_retention": _top_hit_retention(ref_scores, cand_keys),
        "top5_retention": sample_vs_fasim._topk_retention(ref_scores, cand_keys, k=5),
        "top10_retention": sample_vs_fasim._topk_retention(ref_scores, cand_keys, k=10),
        "score_weighted_recall": sample_vs_fasim._score_weighted_recall(ref_scores, cand_keys),
    }


def _task_key_tuple(task_key: dict[str, object]) -> tuple[int, int, int, int, int, str, int]:
    return (
        int(task_key["fragment_index"]),
        int(task_key["fragment_start_in_seq"]),
        int(task_key["fragment_end_in_seq"]),
        int(task_key["reverse_mode"]),
        int(task_key["parallel_mode"]),
        str(task_key.get("strand", "")),
        int(task_key.get("rule", 0)),
    )


def _rank_task_oracle(item: dict[str, object]) -> tuple[object, ...]:
    return (
        -int(item["rescue_top5_gain_count"]),
        -int(item["rescue_top10_gain_count"]),
        -float(item["rescue_score_weighted_gain"]),
        int(item["rescue_added_bp_total"]),
        item["tile_key"],
        _task_key_tuple(item["task_key"]),
    )


def _task_identity(item: dict[str, object]) -> tuple[object, ...]:
    return (item["tile_key"],) + _task_key_tuple(item["task_key"])


def _get_deployable_features(item: dict[str, object]) -> dict[str, object]:
    features = item.get("deployable_features")
    if not isinstance(features, dict):
        raise RuntimeError(
            "selected ranking requires deployable_features in analysis summary; rerun analyze_two_stage_task_ambiguity.py"
        )
    return features


def _feature_int(mapping: dict[str, object], key: str) -> int:
    value = mapping.get(key)
    if value is None:
        return 0
    return int(value)


def _feature_nested_int(mapping: dict[str, object], key: str, nested_key: str) -> int:
    nested = mapping.get(key)
    if not isinstance(nested, dict):
        return 0
    value = nested.get(nested_key)
    if value is None:
        return 0
    return int(value)


def _feature_optional_int(mapping: dict[str, object], key: str) -> int | None:
    value = mapping.get(key)
    if value is None:
        return None
    return int(value)


def _rank_task_sparse_gap(item: dict[str, object]) -> tuple[object, ...]:
    features = _get_deployable_features(item)
    best_rejected_score = _feature_optional_int(features, "best_rejected_score")
    best_score_gap = _feature_optional_int(features, "best_score_gap")
    return (
        -(
            _feature_nested_int(features, "score_band_counts", "ge85")
            + _feature_nested_int(features, "score_band_counts", "80_84")
            + _feature_nested_int(features, "score_band_counts", "75_79")
        ),
        10**18 if best_rejected_score is None else -best_rejected_score,
        10**18 if best_score_gap is None else best_score_gap,
        -_feature_int(features, "uncovered_rejected_bp_total"),
        _feature_int(features, "kept_window_count"),
        item["tile_key"],
        _task_key_tuple(item["task_key"]),
    )


def _rank_task_support_pressure(item: dict[str, object]) -> tuple[object, ...]:
    features = _get_deployable_features(item)
    best_rejected_score = _feature_optional_int(features, "best_rejected_score")
    best_score_gap = _feature_optional_int(features, "best_score_gap")
    return (
        -_feature_nested_int(features, "reject_reason_counts", "low_support_or_margin"),
        -(
            _feature_nested_int(features, "support_bin_counts", "support2")
            + _feature_nested_int(features, "support_bin_counts", "support3plus")
        ),
        10**18 if best_rejected_score is None else -best_rejected_score,
        10**18 if best_score_gap is None else best_score_gap,
        -_feature_int(features, "uncovered_rejected_window_count"),
        -_feature_int(features, "uncovered_rejected_bp_total"),
        item["tile_key"],
        _task_key_tuple(item["task_key"]),
    )


def _rank_task(item: dict[str, object], ranking: str) -> tuple[object, ...]:
    if ranking == RANKING_ORACLE:
        return _rank_task_oracle(item)
    if ranking == RANKING_SPARSE_GAP:
        return _rank_task_sparse_gap(item)
    if ranking == RANKING_SUPPORT_PRESSURE:
        return _rank_task_support_pressure(item)
    raise RuntimeError(f"unsupported ranking: {ranking}")


def _overlap_summary(selected_tasks: list[dict[str, object]], oracle_selected_tasks: list[dict[str, object]]) -> dict[str, object]:
    selected_ids = {_task_identity(item) for item in selected_tasks}
    oracle_ids = {_task_identity(item) for item in oracle_selected_tasks}
    overlap = selected_ids & oracle_ids
    precision = float(len(overlap)) / float(len(selected_ids)) if selected_ids else 1.0
    recall = float(len(overlap)) / float(len(oracle_ids)) if oracle_ids else 1.0
    union = selected_ids | oracle_ids
    jaccard = float(len(overlap)) / float(len(union)) if union else 1.0
    return {
        "oracle_selected_task_count": len(oracle_ids),
        "candidate_selected_task_count": len(selected_ids),
        "overlap_task_count": len(overlap),
        "precision": precision,
        "recall": recall,
        "jaccard": jaccard,
    }


def _render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Task-Level Exact Rerun Replay",
        "",
        f"- analysis_summary: {summary['analysis_summary']}",
        f"- ranking: {summary['ranking']}",
        "",
    ]
    for budget_payload in summary["budgets"]:
        aggregate = budget_payload["aggregate"]
        lines.extend(
            [
                f"## budget {budget_payload['budget']}",
                "",
                f"- rerun_task_count: {aggregate['rerun_task_count']}",
                f"- rerun_added_window_count: {aggregate['rerun_added_window_count']}",
                f"- rerun_added_bp_total: {aggregate['rerun_added_bp_total']}",
                f"- predicted_top5_retention: {aggregate['predicted_top5_retention']:.12g}",
                f"- predicted_top10_retention: {aggregate['predicted_top10_retention']:.12g}",
                f"- predicted_score_weighted_recall: {aggregate['predicted_score_weighted_recall']:.12g}",
                f"- oracle_overlap_jaccard: {aggregate['oracle_overlap']['jaccard']:.12g}",
                "",
                "| tile | fragment_index | fragment_start | rescue_top5_gain | rescue_top10_gain | added_bp |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in aggregate["selected_tasks"]:
            task_key = item["task_key"]
            lines.append(
                f"| {item['anchor_label']} | {task_key['fragment_index']} | {task_key['fragment_start_in_seq']} | "
                f"{item['rescue_top5_gain_count']} | {item['rescue_top10_gain_count']} | {item['rescue_added_bp_total']} |"
            )
        if not aggregate["selected_tasks"]:
            lines.append("| none | 0 | 0 | 0 | 0 | 0 |")
        lines.append("")
    return "\n".join(lines)


def replay_task_level_rerun(
    analysis_summary_path: Path | str,
    *,
    budgets: list[int],
    ranking: str = RANKING_ORACLE,
) -> dict[str, object]:
    analysis_summary_path = Path(analysis_summary_path).resolve()
    analysis_summary = _load_json(analysis_summary_path)

    tiles = list(analysis_summary.get("tiles", []))
    tile_baselines: dict[str, dict[str, object]] = {}
    candidate_tasks: list[dict[str, object]] = []
    ref_scores_global: dict[tuple, float] = {}
    baseline_keys_global: set[tuple] = set()
    baseline_threshold_skipped_total = 0
    baseline_windows_after_gate_total = 0
    baseline_refine_total_bp_total = 0

    for tile in tiles:
        tile_key = str(tile["tile_key"])
        ref_scores = {
            _strict_key_tuple(item): float(item["score"]) for item in tile.get("legacy_strict_hits", [])
        }
        baseline_keys = {
            _strict_key_tuple(item) for item in tile.get("baseline_covered_strict_keys", [])
        }
        tile_baselines[tile_key] = {
            "tile": tile,
            "ref_scores": ref_scores,
            "baseline_keys": baseline_keys,
        }
        _update_strict_scores(ref_scores_global, ref_scores)
        baseline_keys_global.update(baseline_keys)
        baseline_threshold_skipped_total += int(tile.get("baseline_threshold_skipped_after_gate", 0))
        baseline_windows_after_gate_total += int(tile.get("baseline_windows_after_gate", 0))
        baseline_refine_total_bp_total += int(tile.get("baseline_refine_total_bp", 0))

        for task in tile.get("tasks", []):
            payload = dict(task)
            payload["tile_key"] = tile_key
            payload["anchor_label"] = str(tile.get("anchor_label", ""))
            payload["rescue_gain_key_tuples"] = [
                _strict_key_tuple(item) for item in task.get("rescue_gain_strict_keys", [])
            ]
            candidate_tasks.append(payload)

    ranked_tasks = sorted(candidate_tasks, key=lambda item: _rank_task(item, ranking))
    oracle_ranked_tasks = sorted(candidate_tasks, key=_rank_task_oracle)
    baseline_quality = _quality_summary(ref_scores_global, baseline_keys_global)
    normalized_budgets = sorted({int(value) for value in budgets if int(value) >= 0})
    budget_payloads: list[dict[str, object]] = []

    for budget in normalized_budgets:
        selected_tasks = ranked_tasks[:budget]
        oracle_selected_tasks = oracle_ranked_tasks[:budget]
        predicted_keys_global = set(baseline_keys_global)
        rerun_added_window_count = 0
        rerun_added_bp_total = 0
        predicted_windows_after_gate_total = baseline_windows_after_gate_total
        predicted_refine_total_bp_total = baseline_refine_total_bp_total

        selected_by_tile: dict[str, list[dict[str, object]]] = {}
        for task in selected_tasks:
            selected_by_tile.setdefault(task["tile_key"], []).append(task)
            predicted_keys_global.update(task["rescue_gain_key_tuples"])
            rerun_added_window_count += int(task["rescue_added_window_count"])
            rerun_added_bp_total += int(task["rescue_added_bp_total"])
            predicted_windows_after_gate_total += int(task["rescue_added_window_count"])
            predicted_refine_total_bp_total += int(task["rescue_added_bp_total"])

        predicted_quality = _quality_summary(ref_scores_global, predicted_keys_global)
        per_tile: list[dict[str, object]] = []
        for tile_key, baseline in sorted(tile_baselines.items()):
            tile_selected = selected_by_tile.get(tile_key, [])
            predicted_keys = set(baseline["baseline_keys"])
            for task in tile_selected:
                predicted_keys.update(task["rescue_gain_key_tuples"])
            tile_quality = _quality_summary(dict(baseline["ref_scores"]), predicted_keys)
            per_tile.append(
                {
                    "tile_key": tile_key,
                    "anchor_label": str(baseline["tile"].get("anchor_label", "")),
                    "selected_task_count": len(tile_selected),
                    "rerun_added_window_count": sum(int(task["rescue_added_window_count"]) for task in tile_selected),
                    "rerun_added_bp_total": sum(int(task["rescue_added_bp_total"]) for task in tile_selected),
                    "predicted": tile_quality,
                }
            )

        aggregate = {
            "budget": budget,
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
            "rerun_task_count": len(selected_tasks),
            "rerun_added_window_count": rerun_added_window_count,
            "rerun_added_bp_total": rerun_added_bp_total,
            "baseline_threshold_skipped_after_gate_total": baseline_threshold_skipped_total,
            "predicted_threshold_skipped_after_gate_total": baseline_threshold_skipped_total,
            "baseline_windows_after_gate_total": baseline_windows_after_gate_total,
            "predicted_windows_after_gate_total": predicted_windows_after_gate_total,
            "baseline_refine_total_bp_total": baseline_refine_total_bp_total,
            "predicted_refine_total_bp_total": predicted_refine_total_bp_total,
            "delta_refine_total_bp_total": predicted_refine_total_bp_total - baseline_refine_total_bp_total,
            "oracle_overlap": _overlap_summary(selected_tasks, oracle_selected_tasks),
            "selected_tasks": [
                {
                    "tile_key": task["tile_key"],
                    "anchor_label": task["anchor_label"],
                    "task_key": task["task_key"],
                    "rescue_top5_gain_count": int(task["rescue_top5_gain_count"]),
                    "rescue_top10_gain_count": int(task["rescue_top10_gain_count"]),
                    "rescue_score_weighted_gain": float(task["rescue_score_weighted_gain"]),
                    "rescue_added_window_count": int(task["rescue_added_window_count"]),
                    "rescue_added_bp_total": int(task["rescue_added_bp_total"]),
                }
                for task in selected_tasks
            ],
        }
        budget_payloads.append(
            {
                "budget": budget,
                "aggregate": aggregate,
                "per_tile": per_tile,
            }
        )

    return {
        "analysis_summary": str(analysis_summary_path),
        "ranking": ranking,
        "budgets": budget_payloads,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline replay for task-level ambiguity-triggered exact rerun budgets.",
    )
    parser.add_argument("--analysis-summary", required=True, help="task ambiguity summary.json")
    parser.add_argument(
        "--budget",
        action="append",
        type=int,
        required=True,
        help="global task rerun budget to evaluate (repeatable)",
    )
    parser.add_argument(
        "--ranking",
        choices=RANKING_CHOICES,
        default=RANKING_ORACLE,
        help="task ranking to replay (default: oracle_rescue_gain)",
    )
    parser.add_argument("--output-dir", required=True, help="output directory for summary.json/summary.md")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = replay_task_level_rerun(
        args.analysis_summary,
        budgets=list(args.budget),
        ranking=str(args.ranking),
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
