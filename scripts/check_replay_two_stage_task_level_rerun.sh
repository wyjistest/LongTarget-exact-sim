#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cat >"$WORK/analysis_summary.json" <<'EOF'
{
  "baseline_label": "deferred_exact_minimal_v3_scoreband_75_79",
  "rescue_label": "deferred_exact",
  "aggregate": {
    "tile_count": 1,
    "eligible_task_count": 4
  },
  "tiles": [
    {
      "tile_key": "anchorReplay|25000|strongest_shrink|1|25000",
      "anchor_label": "anchorReplay",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "baseline_threshold_skipped_after_gate": 0,
      "baseline_windows_after_gate": 4,
      "baseline_refine_total_bp": 144,
      "legacy_strict_hits": [
        {"query_start": 1, "query_end": 20, "start_in_genome": 1000, "end_in_genome": 1020, "strand": "ParaPlus", "rule": 1, "score": 100.0},
        {"query_start": 21, "query_end": 40, "start_in_genome": 2000, "end_in_genome": 2020, "strand": "ParaPlus", "rule": 1, "score": 95.0},
        {"query_start": 41, "query_end": 60, "start_in_genome": 3000, "end_in_genome": 3020, "strand": "ParaPlus", "rule": 1, "score": 90.0},
        {"query_start": 61, "query_end": 80, "start_in_genome": 4000, "end_in_genome": 4020, "strand": "ParaPlus", "rule": 1, "score": 85.0}
      ],
      "baseline_covered_strict_keys": [
        {"query_start": 1, "query_end": 20, "start_in_genome": 1000, "end_in_genome": 1020, "strand": "ParaPlus", "rule": 1}
      ],
      "tasks": [
        {
          "task_key": {"fragment_index": 1, "fragment_start_in_seq": 5001, "fragment_end_in_seq": 10000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 2,
          "baseline_inside_rejected_missing_count_top5": 2,
          "baseline_inside_rejected_missing_count_top10": 2,
          "baseline_inside_rejected_missing_weight": 185.0,
          "baseline_uncovered_rejected_window_count": 2,
          "best_score_gap": 5,
          "rescue_gain_strict_key_count": 2,
          "rescue_top5_gain_count": 2,
          "rescue_top10_gain_count": 2,
          "rescue_score_weighted_gain": 185.0,
          "rescue_added_window_count": 2,
          "rescue_added_bp_total": 62,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 2,
            "uncovered_rejected_bp_total": 62,
            "max_uncovered_rejected_window_bp": 31,
            "best_kept_score": 100,
            "best_rejected_score": 95,
            "best_score_gap": 5,
            "score_band_counts": {"ge85": 2, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 62, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 2, "support3plus": 0},
            "reject_reason_counts": {"low_support_or_margin": 2},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "selective_fallback_selected_window_count": 0
          },
          "rescue_gain_strict_keys": [
            {"query_start": 21, "query_end": 40, "start_in_genome": 2000, "end_in_genome": 2020, "strand": "ParaPlus", "rule": 1},
            {"query_start": 41, "query_end": 60, "start_in_genome": 3000, "end_in_genome": 3020, "strand": "ParaPlus", "rule": 1}
          ]
        },
        {
          "task_key": {"fragment_index": 2, "fragment_start_in_seq": 10001, "fragment_end_in_seq": 15000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 1,
          "baseline_inside_rejected_missing_count_top5": 1,
          "baseline_inside_rejected_missing_count_top10": 1,
          "baseline_inside_rejected_missing_weight": 85.0,
          "baseline_uncovered_rejected_window_count": 1,
          "best_score_gap": 15,
          "rescue_gain_strict_key_count": 1,
          "rescue_top5_gain_count": 1,
          "rescue_top10_gain_count": 1,
          "rescue_score_weighted_gain": 85.0,
          "rescue_added_window_count": 1,
          "rescue_added_bp_total": 10,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 1,
            "uncovered_rejected_bp_total": 10,
            "max_uncovered_rejected_window_bp": 10,
            "best_kept_score": 100,
            "best_rejected_score": 85,
            "best_score_gap": 15,
            "score_band_counts": {"ge85": 1, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 10, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 1, "support3plus": 0},
            "reject_reason_counts": {"low_support_or_margin": 1},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "selective_fallback_selected_window_count": 0
          },
          "rescue_gain_strict_keys": [
            {"query_start": 61, "query_end": 80, "start_in_genome": 4000, "end_in_genome": 4020, "strand": "ParaPlus", "rule": 1}
          ]
        },
        {
          "task_key": {"fragment_index": 3, "fragment_start_in_seq": 15001, "fragment_end_in_seq": 20000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 1,
          "baseline_inside_rejected_missing_count_top5": 1,
          "baseline_inside_rejected_missing_count_top10": 1,
          "baseline_inside_rejected_missing_weight": 85.0,
          "baseline_uncovered_rejected_window_count": 1,
          "best_score_gap": 15,
          "rescue_gain_strict_key_count": 1,
          "rescue_top5_gain_count": 1,
          "rescue_top10_gain_count": 1,
          "rescue_score_weighted_gain": 85.0,
          "rescue_added_window_count": 1,
          "rescue_added_bp_total": 20,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 3,
            "uncovered_rejected_bp_total": 60,
            "max_uncovered_rejected_window_bp": 25,
            "best_kept_score": 100,
            "best_rejected_score": 92,
            "best_score_gap": 8,
            "score_band_counts": {"ge85": 1, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 20, "80_84": 0, "75_79": 0, "70_74": 40, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 0, "support3plus": 3},
            "reject_reason_counts": {"low_support_or_margin": 3},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "selective_fallback_selected_window_count": 0
          },
          "rescue_gain_strict_keys": [
            {"query_start": 61, "query_end": 80, "start_in_genome": 4000, "end_in_genome": 4020, "strand": "ParaPlus", "rule": 1}
          ]
        },
        {
          "task_key": {"fragment_index": 4, "fragment_start_in_seq": 20001, "fragment_end_in_seq": 25000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 1,
          "baseline_inside_rejected_missing_count_top5": 1,
          "baseline_inside_rejected_missing_count_top10": 1,
          "baseline_inside_rejected_missing_weight": 80.0,
          "baseline_uncovered_rejected_window_count": 1,
          "best_score_gap": 20,
          "rescue_gain_strict_key_count": 0,
          "rescue_top5_gain_count": 0,
          "rescue_top10_gain_count": 0,
          "rescue_score_weighted_gain": 0.0,
          "rescue_added_window_count": 0,
          "rescue_added_bp_total": 0,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 1,
            "uncovered_rejected_bp_total": 30,
            "max_uncovered_rejected_window_bp": 30,
            "best_kept_score": 100,
            "best_rejected_score": 82,
            "best_score_gap": 18,
            "score_band_counts": {"ge85": 0, "80_84": 1, "75_79": 0, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 0, "80_84": 30, "75_79": 0, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 1, "support3plus": 0},
            "reject_reason_counts": {"low_support_or_margin": 1},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "selective_fallback_selected_window_count": 0
          },
          "rescue_gain_strict_keys": []
        }
      ]
    }
  ]
}
EOF

OUT="$WORK/out"
python3 "$ROOT/scripts/replay_two_stage_task_level_rerun.py" \
  --analysis-summary "$WORK/analysis_summary.json" \
  --budget 1 \
  --budget 2 \
  --output-dir "$OUT" >/dev/null

OUT_SPARSE="$WORK/out_sparse"
python3 "$ROOT/scripts/replay_two_stage_task_level_rerun.py" \
  --analysis-summary "$WORK/analysis_summary.json" \
  --ranking deployable_sparse_gap_v1 \
  --budget 1 \
  --budget 2 \
  --output-dir "$OUT_SPARSE" >/dev/null

OUT_SUPPORT="$WORK/out_support"
python3 "$ROOT/scripts/replay_two_stage_task_level_rerun.py" \
  --analysis-summary "$WORK/analysis_summary.json" \
  --ranking deployable_support_pressure_v1 \
  --budget 1 \
  --budget 2 \
  --output-dir "$OUT_SUPPORT" >/dev/null

python3 - "$OUT/summary.json" "$OUT_SPARSE/summary.json" "$OUT_SUPPORT/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
summary_sparse = json.load(open(sys.argv[2], "r", encoding="utf-8"))
summary_support = json.load(open(sys.argv[3], "r", encoding="utf-8"))
budgets = {item["budget"]: item for item in summary["budgets"]}
assert sorted(budgets) == [1, 2]
assert summary["ranking"] == "oracle_rescue_gain"

budget1 = budgets[1]["aggregate"]
assert budget1["rerun_task_count"] == 1
assert budget1["rerun_added_window_count"] == 2
assert budget1["rerun_added_bp_total"] == 62
assert math.isclose(budget1["predicted_top_hit_retention"], 1.0)
assert math.isclose(budget1["predicted_top5_retention"], 0.75)
assert math.isclose(budget1["predicted_top10_retention"], 0.75)
assert math.isclose(budget1["predicted_score_weighted_recall"], 285.0 / 370.0)
assert budget1["selected_tasks"][0]["task_key"]["fragment_index"] == 1
assert budget1["oracle_overlap"]["oracle_selected_task_count"] == 1
assert budget1["oracle_overlap"]["candidate_selected_task_count"] == 1
assert budget1["oracle_overlap"]["overlap_task_count"] == 1
assert math.isclose(budget1["oracle_overlap"]["precision"], 1.0)
assert math.isclose(budget1["oracle_overlap"]["recall"], 1.0)
assert math.isclose(budget1["oracle_overlap"]["jaccard"], 1.0)

budget2 = budgets[2]["aggregate"]
assert budget2["rerun_task_count"] == 2
assert budget2["rerun_added_window_count"] == 3
assert budget2["rerun_added_bp_total"] == 72
assert math.isclose(budget2["predicted_top_hit_retention"], 1.0)
assert math.isclose(budget2["predicted_top5_retention"], 1.0)
assert math.isclose(budget2["predicted_top10_retention"], 1.0)
assert math.isclose(budget2["predicted_score_weighted_recall"], 1.0)
assert [item["task_key"]["fragment_index"] for item in budget2["selected_tasks"]] == [1, 2]
assert budget2["delta_refine_total_bp_total"] == 72
assert math.isclose(budget2["oracle_overlap"]["precision"], 1.0)
assert math.isclose(budget2["oracle_overlap"]["recall"], 1.0)
assert math.isclose(budget2["oracle_overlap"]["jaccard"], 1.0)

budgets_sparse = {item["budget"]: item for item in summary_sparse["budgets"]}
assert summary_sparse["ranking"] == "deployable_sparse_gap_v1"
budget1_sparse = budgets_sparse[1]["aggregate"]
assert [item["task_key"]["fragment_index"] for item in budget1_sparse["selected_tasks"]] == [1]
assert math.isclose(budget1_sparse["oracle_overlap"]["jaccard"], 1.0)
budget2_sparse = budgets_sparse[2]["aggregate"]
assert [item["task_key"]["fragment_index"] for item in budget2_sparse["selected_tasks"]] == [1, 3]
assert budget2_sparse["delta_refine_total_bp_total"] == 82
assert budget2_sparse["oracle_overlap"]["oracle_selected_task_count"] == 2
assert budget2_sparse["oracle_overlap"]["candidate_selected_task_count"] == 2
assert budget2_sparse["oracle_overlap"]["overlap_task_count"] == 1
assert math.isclose(budget2_sparse["oracle_overlap"]["precision"], 0.5)
assert math.isclose(budget2_sparse["oracle_overlap"]["recall"], 0.5)
assert math.isclose(budget2_sparse["oracle_overlap"]["jaccard"], 1.0 / 3.0)

budgets_support = {item["budget"]: item for item in summary_support["budgets"]}
assert summary_support["ranking"] == "deployable_support_pressure_v1"
budget1_support = budgets_support[1]["aggregate"]
assert [item["task_key"]["fragment_index"] for item in budget1_support["selected_tasks"]] == [3]
assert budget1_support["oracle_overlap"]["overlap_task_count"] == 0
assert math.isclose(budget1_support["oracle_overlap"]["precision"], 0.0)
assert math.isclose(budget1_support["oracle_overlap"]["recall"], 0.0)
assert math.isclose(budget1_support["oracle_overlap"]["jaccard"], 0.0)
budget2_support = budgets_support[2]["aggregate"]
assert [item["task_key"]["fragment_index"] for item in budget2_support["selected_tasks"]] == [3, 1]
assert budget2_support["delta_refine_total_bp_total"] == 82
assert budget2_support["oracle_overlap"]["overlap_task_count"] == 1
assert math.isclose(budget2_support["oracle_overlap"]["precision"], 0.5)
assert math.isclose(budget2_support["oracle_overlap"]["recall"], 0.5)
assert math.isclose(budget2_support["oracle_overlap"]["jaccard"], 1.0 / 3.0)
PY

grep -q "Task-Level Exact Rerun Replay" "$OUT/summary.md"
grep -q "budget 2" "$OUT/summary.md"
