#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import analyze_two_stage_task_ambiguity as task_ambiguity  # noqa: E402
import replay_two_stage_task_level_rerun as task_rerun  # noqa: E402

try:  # noqa: E402
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
except ImportError as exc:  # pragma: no cover - environment issue
    raise RuntimeError("search_two_stage_task_trigger_rankings.py requires scikit-learn") from exc


RULE_SCORE_MASS_GAP_V2 = "rule_score_mass_gap_v2"
RULE_SUPPORT_REASON_PRESSURE_V2 = "rule_support_reason_pressure_v2"
LR_BUDGET16_RANK_V1 = "lr_budget16_rank_v1"
HGB_BUDGET16_RANK_V1 = "hgb_budget16_rank_v1"
ORACLE_REFERENCE = task_rerun.RANKING_ORACLE

RULE_CANDIDATES = (
    RULE_SCORE_MASS_GAP_V2,
    RULE_SUPPORT_REASON_PRESSURE_V2,
)
LEARNED_CANDIDATES = (
    LR_BUDGET16_RANK_V1,
    HGB_BUDGET16_RANK_V1,
)
CANDIDATE_ORDER = RULE_CANDIDATES + LEARNED_CANDIDATES


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _task_identity(item: dict[str, object]) -> tuple[object, ...]:
    return task_rerun._task_identity(item)


def _feature_int(mapping: dict[str, object], key: str) -> int:
    value = mapping.get(key)
    if value is None:
        return 0
    return int(value)


def _feature_float(mapping: dict[str, object], key: str) -> float:
    value = mapping.get(key)
    if value is None:
        return 0.0
    return float(value)


def _feature_optional_int(mapping: dict[str, object], key: str) -> int | None:
    value = mapping.get(key)
    if value is None:
        return None
    return int(value)


def _feature_nested_int(mapping: dict[str, object], key: str, nested_key: str) -> int:
    nested = mapping.get(key)
    if not isinstance(nested, dict):
        return 0
    value = nested.get(nested_key)
    if value is None:
        return 0
    return int(value)


def _all_reject_reason_keys(tasks: list[dict[str, object]]) -> list[str]:
    keys: set[str] = set()
    for item in tasks:
        features = task_rerun._get_deployable_features(item)
        for bucket_name in ("reject_reason_counts", "reject_reason_bp_totals"):
            bucket = features.get(bucket_name)
            if isinstance(bucket, dict):
                keys.update(str(key) for key in bucket)
    return sorted(keys)


def _feature_schema(tasks: list[dict[str, object]]) -> tuple[list[str], list[str]]:
    reject_reason_keys = _all_reject_reason_keys(tasks)
    feature_names = [
        "kept_window_count",
        "uncovered_rejected_window_count",
        "uncovered_rejected_bp_total",
        "max_uncovered_rejected_window_bp",
        "has_best_kept_score",
        "best_kept_score",
        "has_best_rejected_score",
        "best_rejected_score",
        "has_best_score_gap",
        "best_score_gap",
        "rejected_score_sum",
        "rejected_score_mean",
        "rejected_score_top3_sum",
        "rejected_score_x_bp_sum",
        "rejected_score_x_support_sum",
        "rule_diversity_count",
        "strand_diversity_count",
        "rule_strand_object_count",
        "rule_strand_entropy",
        "selective_fallback_selected_window_count",
        "tile_rank_by_best_rejected_score",
        "tile_rank_by_rejected_score_x_bp_sum",
    ]
    feature_names.extend(f"score_band_count__{name}" for name in task_ambiguity.DEPLOYABLE_SCORE_BANDS)
    feature_names.extend(f"score_band_bp__{name}" for name in task_ambiguity.DEPLOYABLE_SCORE_BANDS)
    feature_names.extend(f"support_bin_count__{name}" for name in task_ambiguity.DEPLOYABLE_SUPPORT_BINS)
    feature_names.extend(f"reject_reason_count__{name}" for name in reject_reason_keys)
    feature_names.extend(f"reject_reason_bp__{name}" for name in reject_reason_keys)
    return feature_names, reject_reason_keys


def _feature_vector(
    item: dict[str, object],
    *,
    reject_reason_keys: list[str],
) -> list[float]:
    features = task_rerun._get_deployable_features(item)
    best_kept_score = _feature_optional_int(features, "best_kept_score")
    best_rejected_score = _feature_optional_int(features, "best_rejected_score")
    best_score_gap = _feature_optional_int(features, "best_score_gap")
    vector = [
        float(_feature_int(features, "kept_window_count")),
        float(_feature_int(features, "uncovered_rejected_window_count")),
        float(_feature_int(features, "uncovered_rejected_bp_total")),
        float(_feature_int(features, "max_uncovered_rejected_window_bp")),
        0.0 if best_kept_score is None else 1.0,
        0.0 if best_kept_score is None else float(best_kept_score),
        0.0 if best_rejected_score is None else 1.0,
        0.0 if best_rejected_score is None else float(best_rejected_score),
        0.0 if best_score_gap is None else 1.0,
        999.0 if best_score_gap is None else float(best_score_gap),
        float(_feature_int(features, "rejected_score_sum")),
        float(_feature_float(features, "rejected_score_mean")),
        float(_feature_int(features, "rejected_score_top3_sum")),
        float(_feature_int(features, "rejected_score_x_bp_sum")),
        float(_feature_int(features, "rejected_score_x_support_sum")),
        float(_feature_int(features, "rule_diversity_count")),
        float(_feature_int(features, "strand_diversity_count")),
        float(_feature_int(features, "rule_strand_object_count")),
        float(_feature_float(features, "rule_strand_entropy")),
        float(_feature_int(features, "selective_fallback_selected_window_count")),
        float(_feature_int(features, "tile_rank_by_best_rejected_score")),
        float(_feature_int(features, "tile_rank_by_rejected_score_x_bp_sum")),
    ]
    vector.extend(
        float(_feature_nested_int(features, "score_band_counts", name))
        for name in task_ambiguity.DEPLOYABLE_SCORE_BANDS
    )
    vector.extend(
        float(_feature_nested_int(features, "score_band_bp_totals", name))
        for name in task_ambiguity.DEPLOYABLE_SCORE_BANDS
    )
    vector.extend(
        float(_feature_nested_int(features, "support_bin_counts", name))
        for name in task_ambiguity.DEPLOYABLE_SUPPORT_BINS
    )
    vector.extend(
        float(_feature_nested_int(features, "reject_reason_counts", name))
        for name in reject_reason_keys
    )
    vector.extend(
        float(_feature_nested_int(features, "reject_reason_bp_totals", name))
        for name in reject_reason_keys
    )
    return vector


def _oracle_priority_target(item: dict[str, object]) -> float:
    return (
        100000.0 * float(item["rescue_top5_gain_count"])
        + 1000.0 * float(item["rescue_top10_gain_count"])
        + float(item["rescue_score_weighted_gain"])
        - 0.001 * float(item["rescue_added_bp_total"])
    )


def _prepare_replay_context(analysis_summary_path: Path | str) -> dict[str, object]:
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
            task_rerun._strict_key_tuple(item): float(item["score"])
            for item in tile.get("legacy_strict_hits", [])
        }
        baseline_keys = {
            task_rerun._strict_key_tuple(item)
            for item in tile.get("baseline_covered_strict_keys", [])
        }
        tile_baselines[tile_key] = {
            "tile": tile,
            "ref_scores": ref_scores,
            "baseline_keys": baseline_keys,
        }
        task_rerun._update_strict_scores(ref_scores_global, ref_scores)
        baseline_keys_global.update(baseline_keys)
        baseline_threshold_skipped_total += int(tile.get("baseline_threshold_skipped_after_gate", 0))
        baseline_windows_after_gate_total += int(tile.get("baseline_windows_after_gate", 0))
        baseline_refine_total_bp_total += int(tile.get("baseline_refine_total_bp", 0))

        for task in tile.get("tasks", []):
            payload = dict(task)
            payload["tile_key"] = tile_key
            payload["anchor_label"] = str(tile.get("anchor_label", ""))
            payload["rescue_gain_key_tuples"] = [
                task_rerun._strict_key_tuple(item) for item in task.get("rescue_gain_strict_keys", [])
            ]
            candidate_tasks.append(payload)

    baseline_quality = task_rerun._quality_summary(ref_scores_global, baseline_keys_global)
    oracle_ranked_tasks = sorted(candidate_tasks, key=task_rerun._rank_task_oracle)
    feature_names, reject_reason_keys = _feature_schema(candidate_tasks)
    feature_matrix = np.asarray(
        [_feature_vector(task, reject_reason_keys=reject_reason_keys) for task in candidate_tasks],
        dtype=float,
    )
    target_vector = np.asarray([_oracle_priority_target(task) for task in candidate_tasks], dtype=float)
    anchor_labels = [str(task["anchor_label"]) for task in candidate_tasks]
    return {
        "analysis_summary_path": str(analysis_summary_path),
        "analysis_summary": analysis_summary,
        "tiles": tiles,
        "tile_baselines": tile_baselines,
        "candidate_tasks": candidate_tasks,
        "ref_scores_global": ref_scores_global,
        "baseline_keys_global": baseline_keys_global,
        "baseline_quality": baseline_quality,
        "baseline_threshold_skipped_total": baseline_threshold_skipped_total,
        "baseline_windows_after_gate_total": baseline_windows_after_gate_total,
        "baseline_refine_total_bp_total": baseline_refine_total_bp_total,
        "oracle_ranked_tasks": oracle_ranked_tasks,
        "feature_names": feature_names,
        "feature_matrix": feature_matrix,
        "target_vector": target_vector,
        "anchor_labels": anchor_labels,
    }


def _evaluate_ranked_tasks(
    context: dict[str, object],
    ranked_tasks: list[dict[str, object]],
    *,
    budgets: list[int],
) -> list[dict[str, object]]:
    tile_baselines = context["tile_baselines"]
    baseline_quality = context["baseline_quality"]
    baseline_keys_global = context["baseline_keys_global"]
    baseline_threshold_skipped_total = int(context["baseline_threshold_skipped_total"])
    baseline_windows_after_gate_total = int(context["baseline_windows_after_gate_total"])
    baseline_refine_total_bp_total = int(context["baseline_refine_total_bp_total"])
    oracle_ranked_tasks = context["oracle_ranked_tasks"]
    ref_scores_global = context["ref_scores_global"]

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

        predicted_quality = task_rerun._quality_summary(ref_scores_global, predicted_keys_global)
        per_tile: list[dict[str, object]] = []
        for tile_key, baseline in sorted(tile_baselines.items()):
            tile_selected = selected_by_tile.get(tile_key, [])
            predicted_keys = set(baseline["baseline_keys"])
            for task in tile_selected:
                predicted_keys.update(task["rescue_gain_key_tuples"])
            tile_quality = task_rerun._quality_summary(dict(baseline["ref_scores"]), predicted_keys)
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
            "oracle_overlap": task_rerun._overlap_summary(selected_tasks, oracle_selected_tasks),
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
    return budget_payloads


def _target_budget_payload(budget_payloads: list[dict[str, object]], target_budget: int) -> dict[str, object]:
    for payload in budget_payloads:
        if int(payload["budget"]) == int(target_budget):
            return payload
    raise RuntimeError(f"target budget {target_budget} is not present in evaluated budgets")


def _rank_rule_score_mass_gap_v2(item: dict[str, object]) -> tuple[object, ...]:
    features = task_rerun._get_deployable_features(item)
    best_score_gap = _feature_optional_int(features, "best_score_gap")
    best_rejected_score = _feature_optional_int(features, "best_rejected_score")
    return (
        -_feature_int(features, "rejected_score_top3_sum"),
        -_feature_int(features, "rejected_score_x_bp_sum"),
        10**18 if best_score_gap is None else best_score_gap,
        10**18 if best_rejected_score is None else -best_rejected_score,
        _feature_int(features, "tile_rank_by_best_rejected_score"),
        _feature_int(features, "tile_rank_by_rejected_score_x_bp_sum"),
        item["tile_key"],
        task_rerun._task_key_tuple(item["task_key"]),
    )


def _rank_rule_support_reason_pressure_v2(item: dict[str, object]) -> tuple[object, ...]:
    features = task_rerun._get_deployable_features(item)
    best_score_gap = _feature_optional_int(features, "best_score_gap")
    return (
        -(
            2 * _feature_nested_int(features, "support_bin_counts", "support3plus")
            + _feature_nested_int(features, "support_bin_counts", "support2")
        ),
        -_feature_nested_int(features, "reject_reason_bp_totals", "low_support_or_margin"),
        -_feature_int(features, "rejected_score_x_support_sum"),
        -int(round(1000.0 * _feature_float(features, "rule_strand_entropy"))),
        10**18 if best_score_gap is None else best_score_gap,
        _feature_int(features, "tile_rank_by_rejected_score_x_bp_sum"),
        item["tile_key"],
        task_rerun._task_key_tuple(item["task_key"]),
    )


def _ranked_rule_tasks(context: dict[str, object], candidate_name: str) -> list[dict[str, object]]:
    tasks = list(context["candidate_tasks"])
    if candidate_name == RULE_SCORE_MASS_GAP_V2:
        return sorted(tasks, key=_rank_rule_score_mass_gap_v2)
    if candidate_name == RULE_SUPPORT_REASON_PRESSURE_V2:
        return sorted(tasks, key=_rank_rule_support_reason_pressure_v2)
    raise RuntimeError(f"unsupported rule candidate: {candidate_name}")


def _new_model(candidate_name: str):
    if candidate_name == LR_BUDGET16_RANK_V1:
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    if candidate_name == HGB_BUDGET16_RANK_V1:
        return HistGradientBoostingRegressor(
            loss="squared_error",
            learning_rate=0.05,
            max_depth=3,
            max_iter=200,
            min_samples_leaf=1,
            random_state=0,
        )
    raise RuntimeError(f"unsupported learned candidate: {candidate_name}")


def _ranked_learned_tasks(
    context: dict[str, object],
    candidate_name: str,
    *,
    target_budget: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    feature_matrix = np.asarray(context["feature_matrix"], dtype=float)
    target_vector = np.asarray(context["target_vector"], dtype=float)
    anchor_labels = list(context["anchor_labels"])
    candidate_tasks = list(context["candidate_tasks"])
    unique_anchors = sorted(set(anchor_labels))
    oof_predictions = np.zeros(len(candidate_tasks), dtype=float)
    fold_summaries: list[dict[str, object]] = []

    for anchor_label in unique_anchors:
        train_idx = [index for index, value in enumerate(anchor_labels) if value != anchor_label]
        test_idx = [index for index, value in enumerate(anchor_labels) if value == anchor_label]
        if not test_idx:
            continue
        model = _new_model(candidate_name)
        if train_idx:
            model.fit(feature_matrix[train_idx], target_vector[train_idx])
            predictions = model.predict(feature_matrix[test_idx])
        else:
            predictions = np.zeros(len(test_idx), dtype=float)
        oof_predictions[test_idx] = np.asarray(predictions, dtype=float)
        fold_summaries.append(
            {
                "heldout_anchor": anchor_label,
                "train_task_count": len(train_idx),
                "test_task_count": len(test_idx),
            }
        )

    score_map = {
        _task_identity(task): float(oof_predictions[index])
        for index, task in enumerate(candidate_tasks)
    }
    ranked_tasks = sorted(
        candidate_tasks,
        key=lambda item: (
            -score_map[_task_identity(item)],
            int(item["rescue_added_bp_total"]),
            item["tile_key"],
            task_rerun._task_key_tuple(item["task_key"]),
        ),
    )
    training = {
        "strategy": "leave_anchor_out_regression",
        "target_budget": int(target_budget),
        "fold_count": len(unique_anchors),
        "folds": fold_summaries,
        "target_name": "oracle_priority_v1",
        "model": candidate_name,
    }
    return ranked_tasks, training


def _promotion_gate_result(
    aggregate: dict[str, object],
    *,
    min_delta_top10: float,
    min_delta_score_weighted_recall: float,
    max_delta_refine_total_bp: float,
) -> dict[str, object]:
    top_hit_ok = abs(float(aggregate["delta_top_hit_retention"])) <= 1e-12
    top10_ok = float(aggregate["delta_top10_retention"]) >= float(min_delta_top10)
    score_weighted_ok = float(aggregate["delta_score_weighted_recall"]) >= float(min_delta_score_weighted_recall)
    refine_bp_ok = float(aggregate["delta_refine_total_bp_total"]) <= float(max_delta_refine_total_bp)
    return {
        "top_hit_ok": top_hit_ok,
        "top10_ok": top10_ok,
        "score_weighted_ok": score_weighted_ok,
        "refine_bp_ok": refine_bp_ok,
        "passes": top_hit_ok and top10_ok and score_weighted_ok and refine_bp_ok,
    }


def _candidate_priority_key(candidate: dict[str, object]) -> tuple[object, ...]:
    aggregate = candidate["target_budget_summary"]
    gate = candidate["promotion_gate"]
    return (
        0 if gate["passes"] else 1,
        -float(aggregate["delta_top10_retention"]),
        -float(aggregate["delta_score_weighted_recall"]),
        float(aggregate["delta_refine_total_bp_total"]),
        -float(aggregate["oracle_overlap"]["jaccard"]),
        candidate["name"],
    )


def search_task_trigger_rankings(
    analysis_summary_path: Path | str,
    *,
    budgets: list[int],
    target_budget: int,
    min_delta_top10: float,
    min_delta_score_weighted_recall: float,
    max_delta_refine_total_bp: float,
) -> dict[str, object]:
    context = _prepare_replay_context(analysis_summary_path)
    normalized_budgets = sorted({int(value) for value in budgets if int(value) >= 0})
    if target_budget not in normalized_budgets:
        raise RuntimeError("target budget must also be included in --budget")

    oracle_budget_payloads = _evaluate_ranked_tasks(
        context,
        list(context["oracle_ranked_tasks"]),
        budgets=normalized_budgets,
    )
    oracle_target_budget_payload = _target_budget_payload(oracle_budget_payloads, target_budget)
    oracle_target_budget_summary = dict(oracle_target_budget_payload["aggregate"])

    candidates: list[dict[str, object]] = []
    for candidate_name in CANDIDATE_ORDER:
        if candidate_name in RULE_CANDIDATES:
            ranked_tasks = _ranked_rule_tasks(context, candidate_name)
            training = {"strategy": "rule_based"}
        else:
            ranked_tasks, training = _ranked_learned_tasks(
                context,
                candidate_name,
                target_budget=target_budget,
            )
        budget_payloads = _evaluate_ranked_tasks(context, ranked_tasks, budgets=normalized_budgets)
        target_budget_payload = _target_budget_payload(budget_payloads, target_budget)
        target_budget_summary = dict(target_budget_payload["aggregate"])
        gate_result = _promotion_gate_result(
            target_budget_summary,
            min_delta_top10=min_delta_top10,
            min_delta_score_weighted_recall=min_delta_score_weighted_recall,
            max_delta_refine_total_bp=max_delta_refine_total_bp,
        )
        candidates.append(
            {
                "name": candidate_name,
                "kind": "rule" if candidate_name in RULE_CANDIDATES else "learned",
                "feature_names": list(context["feature_names"]),
                "training": training,
                "budgets": budget_payloads,
                "target_budget_summary": target_budget_summary,
                "promotion_gate": gate_result,
                "passes_promotion_gate": bool(gate_result["passes"]),
            }
        )

    candidates.sort(key=_candidate_priority_key)
    passing_candidates = [item["name"] for item in candidates if item["passes_promotion_gate"]]
    best_candidate = candidates[0]["name"] if candidates else None
    recommended_candidate = passing_candidates[0] if passing_candidates else None
    recommended_runtime_confirm = recommended_candidate is not None

    return {
        "analysis_summary": str(Path(analysis_summary_path).resolve()),
        "budgets": normalized_budgets,
        "target_budget": int(target_budget),
        "promotion_gate": {
            "min_delta_top10": float(min_delta_top10),
            "min_delta_score_weighted_recall": float(min_delta_score_weighted_recall),
            "max_delta_refine_total_bp_total": float(max_delta_refine_total_bp),
        },
        "oracle_reference": {
            "ranking": ORACLE_REFERENCE,
            "budgets": oracle_budget_payloads,
            "target_budget_summary": oracle_target_budget_summary,
        },
        "feature_names": list(context["feature_names"]),
        "candidates": candidates,
        "passing_candidates": passing_candidates,
        "best_candidate": best_candidate,
        "recommended_candidate": recommended_candidate,
        "recommended_runtime_confirm": recommended_runtime_confirm,
    }


def _render_markdown(summary: dict[str, object]) -> str:
    oracle = summary["oracle_reference"]["target_budget_summary"]
    lines = [
        "# Task Trigger Ranking Search",
        "",
        f"- analysis_summary: {summary['analysis_summary']}",
        f"- budgets: {', '.join(str(value) for value in summary['budgets'])}",
        f"- target_budget: {summary['target_budget']}",
        f"- promotion_min_delta_top10: {summary['promotion_gate']['min_delta_top10']}",
        f"- promotion_min_delta_score_weighted_recall: {summary['promotion_gate']['min_delta_score_weighted_recall']}",
        f"- promotion_max_delta_refine_total_bp_total: {summary['promotion_gate']['max_delta_refine_total_bp_total']}",
        f"- oracle_budget_delta_top10_retention: {oracle['delta_top10_retention']:.12g}",
        f"- oracle_budget_delta_score_weighted_recall: {oracle['delta_score_weighted_recall']:.12g}",
        f"- oracle_budget_delta_refine_total_bp_total: {oracle['delta_refine_total_bp_total']}",
        f"- passing_candidates: {', '.join(summary['passing_candidates']) if summary['passing_candidates'] else 'none'}",
        f"- best_candidate: {summary.get('best_candidate') or 'none'}",
        f"- recommended_candidate: {summary['recommended_candidate'] or 'none'}",
        f"- recommended_runtime_confirm: {summary['recommended_runtime_confirm']}",
        "",
        "| candidate | kind | passes | delta_top10 | delta_weighted | delta_refine_bp | oracle_jaccard | strategy |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for candidate in summary["candidates"]:
        aggregate = candidate["target_budget_summary"]
        lines.append(
            f"| {candidate['name']} | {candidate['kind']} | {candidate['passes_promotion_gate']} | "
            f"{aggregate['delta_top10_retention']:.12g} | "
            f"{aggregate['delta_score_weighted_recall']:.12g} | "
            f"{aggregate['delta_refine_total_bp_total']} | "
            f"{aggregate['oracle_overlap']['jaccard']:.12g} | "
            f"{candidate['training']['strategy']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search calibrated oracle-free task trigger rankings against oracle budgeted rerun baselines.",
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
        "--target-budget",
        type=int,
        default=16,
        help="budget used for promotion gate and recommendation (default: 16)",
    )
    parser.add_argument(
        "--promotion-min-delta-top10",
        type=float,
        default=0.08,
        help="minimum delta_top10_retention required to pass the promotion gate",
    )
    parser.add_argument(
        "--promotion-min-delta-score-weighted-recall",
        type=float,
        default=0.006,
        help="minimum delta_score_weighted_recall required to pass the promotion gate",
    )
    parser.add_argument(
        "--promotion-max-delta-refine-total-bp",
        type=float,
        default=10121.25,
        help="maximum delta_refine_total_bp_total allowed to pass the promotion gate",
    )
    parser.add_argument("--output-dir", required=True, help="output directory for summary.json/summary.md")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = search_task_trigger_rankings(
        args.analysis_summary,
        budgets=list(args.budget),
        target_budget=int(args.target_budget),
        min_delta_top10=float(args.promotion_min_delta_top10),
        min_delta_score_weighted_recall=float(args.promotion_min_delta_score_weighted_recall),
        max_delta_refine_total_bp=float(args.promotion_max_delta_refine_total_bp),
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
