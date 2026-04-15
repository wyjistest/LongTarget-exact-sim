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
    "tile_count": 3,
    "eligible_task_count": 6
  },
  "tiles": [
    {
      "tile_key": "anchorA|25000|strongest_shrink|1|25000",
      "anchor_label": "anchorA",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "baseline_threshold_skipped_after_gate": 0,
      "baseline_windows_after_gate": 2,
      "baseline_refine_total_bp": 50,
      "legacy_strict_hits": [
        {"query_start": 1, "query_end": 20, "start_in_genome": 1000, "end_in_genome": 1020, "strand": "ParaPlus", "rule": 1, "score": 100.0},
        {"query_start": 21, "query_end": 40, "start_in_genome": 2000, "end_in_genome": 2020, "strand": "ParaPlus", "rule": 1, "score": 95.0}
      ],
      "baseline_covered_strict_keys": [
        {"query_start": 1, "query_end": 20, "start_in_genome": 1000, "end_in_genome": 1020, "strand": "ParaPlus", "rule": 1}
      ],
      "tasks": [
        {
          "task_key": {"fragment_index": 1, "fragment_start_in_seq": 5001, "fragment_end_in_seq": 10000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 1,
          "baseline_inside_rejected_missing_count_top5": 1,
          "baseline_inside_rejected_missing_count_top10": 1,
          "baseline_inside_rejected_missing_weight": 95.0,
          "baseline_uncovered_rejected_window_count": 2,
          "best_score_gap": 4,
          "rescue_gain_strict_key_count": 1,
          "rescue_top5_gain_count": 1,
          "rescue_top10_gain_count": 1,
          "rescue_score_weighted_gain": 95.0,
          "rescue_added_window_count": 1,
          "rescue_added_bp_total": 20,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 2,
            "uncovered_rejected_bp_total": 40,
            "max_uncovered_rejected_window_bp": 20,
            "best_kept_score": 100,
            "best_rejected_score": 96,
            "best_score_gap": 4,
            "rejected_score_sum": 191,
            "rejected_score_mean": 95.5,
            "rejected_score_top3_sum": 191,
            "rejected_score_x_bp_sum": 3820,
            "rejected_score_x_support_sum": 574,
            "score_band_counts": {"ge85": 2, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 40, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 1, "support3plus": 1},
            "reject_reason_counts": {"low_support_or_margin": 2},
            "reject_reason_bp_totals": {"low_support_or_margin": 40},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "rule_strand_object_count": 1,
            "rule_strand_entropy": 0.0,
            "selective_fallback_selected_window_count": 0,
            "tile_rank_by_best_rejected_score": 1,
            "tile_rank_by_rejected_score_x_bp_sum": 1
          },
          "rescue_gain_strict_keys": [
            {"query_start": 21, "query_end": 40, "start_in_genome": 2000, "end_in_genome": 2020, "strand": "ParaPlus", "rule": 1}
          ]
        },
        {
          "task_key": {"fragment_index": 2, "fragment_start_in_seq": 10001, "fragment_end_in_seq": 15000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 0,
          "baseline_inside_rejected_missing_count_top5": 0,
          "baseline_inside_rejected_missing_count_top10": 0,
          "baseline_inside_rejected_missing_weight": 0.0,
          "baseline_uncovered_rejected_window_count": 1,
          "best_score_gap": 18,
          "rescue_gain_strict_key_count": 0,
          "rescue_top5_gain_count": 0,
          "rescue_top10_gain_count": 0,
          "rescue_score_weighted_gain": 0.0,
          "rescue_added_window_count": 0,
          "rescue_added_bp_total": 0,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 1,
            "uncovered_rejected_bp_total": 18,
            "max_uncovered_rejected_window_bp": 18,
            "best_kept_score": 100,
            "best_rejected_score": 79,
            "best_score_gap": 21,
            "rejected_score_sum": 79,
            "rejected_score_mean": 79.0,
            "rejected_score_top3_sum": 79,
            "rejected_score_x_bp_sum": 1422,
            "rejected_score_x_support_sum": 158,
            "score_band_counts": {"ge85": 0, "80_84": 0, "75_79": 1, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 0, "80_84": 0, "75_79": 18, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 1, "support3plus": 0},
            "reject_reason_counts": {"low_support_or_margin": 1},
            "reject_reason_bp_totals": {"low_support_or_margin": 18},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "rule_strand_object_count": 1,
            "rule_strand_entropy": 0.0,
            "selective_fallback_selected_window_count": 0,
            "tile_rank_by_best_rejected_score": 2,
            "tile_rank_by_rejected_score_x_bp_sum": 2
          },
          "rescue_gain_strict_keys": []
        }
      ]
    },
    {
      "tile_key": "anchorB|25000|strongest_shrink|1|25000",
      "anchor_label": "anchorB",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "baseline_threshold_skipped_after_gate": 0,
      "baseline_windows_after_gate": 2,
      "baseline_refine_total_bp": 48,
      "legacy_strict_hits": [
        {"query_start": 101, "query_end": 120, "start_in_genome": 3000, "end_in_genome": 3020, "strand": "ParaPlus", "rule": 1, "score": 100.0},
        {"query_start": 121, "query_end": 140, "start_in_genome": 4000, "end_in_genome": 4020, "strand": "ParaPlus", "rule": 1, "score": 90.0}
      ],
      "baseline_covered_strict_keys": [
        {"query_start": 101, "query_end": 120, "start_in_genome": 3000, "end_in_genome": 3020, "strand": "ParaPlus", "rule": 1}
      ],
      "tasks": [
        {
          "task_key": {"fragment_index": 3, "fragment_start_in_seq": 15001, "fragment_end_in_seq": 20000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 1,
          "baseline_inside_rejected_missing_count_top5": 1,
          "baseline_inside_rejected_missing_count_top10": 1,
          "baseline_inside_rejected_missing_weight": 90.0,
          "baseline_uncovered_rejected_window_count": 2,
          "best_score_gap": 6,
          "rescue_gain_strict_key_count": 1,
          "rescue_top5_gain_count": 1,
          "rescue_top10_gain_count": 1,
          "rescue_score_weighted_gain": 90.0,
          "rescue_added_window_count": 1,
          "rescue_added_bp_total": 18,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 2,
            "uncovered_rejected_bp_total": 38,
            "max_uncovered_rejected_window_bp": 20,
            "best_kept_score": 100,
            "best_rejected_score": 94,
            "best_score_gap": 6,
            "rejected_score_sum": 186,
            "rejected_score_mean": 93.0,
            "rejected_score_top3_sum": 186,
            "rejected_score_x_bp_sum": 3534,
            "rejected_score_x_support_sum": 560,
            "score_band_counts": {"ge85": 2, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 38, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 1, "support3plus": 1},
            "reject_reason_counts": {"low_support_or_margin": 2},
            "reject_reason_bp_totals": {"low_support_or_margin": 38},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "rule_strand_object_count": 1,
            "rule_strand_entropy": 0.0,
            "selective_fallback_selected_window_count": 0,
            "tile_rank_by_best_rejected_score": 1,
            "tile_rank_by_rejected_score_x_bp_sum": 1
          },
          "rescue_gain_strict_keys": [
            {"query_start": 121, "query_end": 140, "start_in_genome": 4000, "end_in_genome": 4020, "strand": "ParaPlus", "rule": 1}
          ]
        },
        {
          "task_key": {"fragment_index": 4, "fragment_start_in_seq": 20001, "fragment_end_in_seq": 25000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 0,
          "baseline_inside_rejected_missing_count_top5": 0,
          "baseline_inside_rejected_missing_count_top10": 0,
          "baseline_inside_rejected_missing_weight": 0.0,
          "baseline_uncovered_rejected_window_count": 1,
          "best_score_gap": 17,
          "rescue_gain_strict_key_count": 0,
          "rescue_top5_gain_count": 0,
          "rescue_top10_gain_count": 0,
          "rescue_score_weighted_gain": 0.0,
          "rescue_added_window_count": 0,
          "rescue_added_bp_total": 0,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 1,
            "uncovered_rejected_bp_total": 16,
            "max_uncovered_rejected_window_bp": 16,
            "best_kept_score": 100,
            "best_rejected_score": 78,
            "best_score_gap": 22,
            "rejected_score_sum": 78,
            "rejected_score_mean": 78.0,
            "rejected_score_top3_sum": 78,
            "rejected_score_x_bp_sum": 1248,
            "rejected_score_x_support_sum": 156,
            "score_band_counts": {"ge85": 0, "80_84": 0, "75_79": 1, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 0, "80_84": 0, "75_79": 16, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 1, "support3plus": 0},
            "reject_reason_counts": {"low_support_or_margin": 1},
            "reject_reason_bp_totals": {"low_support_or_margin": 16},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "rule_strand_object_count": 1,
            "rule_strand_entropy": 0.0,
            "selective_fallback_selected_window_count": 0,
            "tile_rank_by_best_rejected_score": 2,
            "tile_rank_by_rejected_score_x_bp_sum": 2
          },
          "rescue_gain_strict_keys": []
        }
      ]
    },
    {
      "tile_key": "anchorC|25000|strongest_shrink|1|25000",
      "anchor_label": "anchorC",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "baseline_threshold_skipped_after_gate": 0,
      "baseline_windows_after_gate": 2,
      "baseline_refine_total_bp": 46,
      "legacy_strict_hits": [
        {"query_start": 201, "query_end": 220, "start_in_genome": 5000, "end_in_genome": 5020, "strand": "ParaPlus", "rule": 1, "score": 100.0},
        {"query_start": 221, "query_end": 240, "start_in_genome": 6000, "end_in_genome": 6020, "strand": "ParaPlus", "rule": 1, "score": 88.0}
      ],
      "baseline_covered_strict_keys": [
        {"query_start": 201, "query_end": 220, "start_in_genome": 5000, "end_in_genome": 5020, "strand": "ParaPlus", "rule": 1}
      ],
      "tasks": [
        {
          "task_key": {"fragment_index": 5, "fragment_start_in_seq": 25001, "fragment_end_in_seq": 30000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 1,
          "baseline_inside_rejected_missing_count_top5": 1,
          "baseline_inside_rejected_missing_count_top10": 1,
          "baseline_inside_rejected_missing_weight": 88.0,
          "baseline_uncovered_rejected_window_count": 2,
          "best_score_gap": 8,
          "rescue_gain_strict_key_count": 1,
          "rescue_top5_gain_count": 1,
          "rescue_top10_gain_count": 1,
          "rescue_score_weighted_gain": 88.0,
          "rescue_added_window_count": 1,
          "rescue_added_bp_total": 22,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 2,
            "uncovered_rejected_bp_total": 44,
            "max_uncovered_rejected_window_bp": 22,
            "best_kept_score": 100,
            "best_rejected_score": 92,
            "best_score_gap": 8,
            "rejected_score_sum": 182,
            "rejected_score_mean": 91.0,
            "rejected_score_top3_sum": 182,
            "rejected_score_x_bp_sum": 4004,
            "rejected_score_x_support_sum": 548,
            "score_band_counts": {"ge85": 2, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 44, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 1, "support3plus": 1},
            "reject_reason_counts": {"low_support_or_margin": 2},
            "reject_reason_bp_totals": {"low_support_or_margin": 44},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "rule_strand_object_count": 1,
            "rule_strand_entropy": 0.0,
            "selective_fallback_selected_window_count": 0,
            "tile_rank_by_best_rejected_score": 1,
            "tile_rank_by_rejected_score_x_bp_sum": 1
          },
          "rescue_gain_strict_keys": [
            {"query_start": 221, "query_end": 240, "start_in_genome": 6000, "end_in_genome": 6020, "strand": "ParaPlus", "rule": 1}
          ]
        },
        {
          "task_key": {"fragment_index": 6, "fragment_start_in_seq": 30001, "fragment_end_in_seq": 35000, "reverse_mode": 0, "parallel_mode": 1, "strand": "ParaPlus", "rule": 1},
          "baseline_inside_rejected_missing_count_overall": 0,
          "baseline_inside_rejected_missing_count_top5": 0,
          "baseline_inside_rejected_missing_count_top10": 0,
          "baseline_inside_rejected_missing_weight": 0.0,
          "baseline_uncovered_rejected_window_count": 1,
          "best_score_gap": 16,
          "rescue_gain_strict_key_count": 0,
          "rescue_top5_gain_count": 0,
          "rescue_top10_gain_count": 0,
          "rescue_score_weighted_gain": 0.0,
          "rescue_added_window_count": 0,
          "rescue_added_bp_total": 0,
          "deployable_features": {
            "kept_window_count": 1,
            "uncovered_rejected_window_count": 1,
            "uncovered_rejected_bp_total": 15,
            "max_uncovered_rejected_window_bp": 15,
            "best_kept_score": 100,
            "best_rejected_score": 77,
            "best_score_gap": 23,
            "rejected_score_sum": 77,
            "rejected_score_mean": 77.0,
            "rejected_score_top3_sum": 77,
            "rejected_score_x_bp_sum": 1155,
            "rejected_score_x_support_sum": 154,
            "score_band_counts": {"ge85": 0, "80_84": 0, "75_79": 1, "70_74": 0, "lt70": 0},
            "score_band_bp_totals": {"ge85": 0, "80_84": 0, "75_79": 15, "70_74": 0, "lt70": 0},
            "support_bin_counts": {"support1": 0, "support2": 1, "support3plus": 0},
            "reject_reason_counts": {"low_support_or_margin": 1},
            "reject_reason_bp_totals": {"low_support_or_margin": 15},
            "rule_diversity_count": 1,
            "strand_diversity_count": 1,
            "rule_strand_object_count": 1,
            "rule_strand_entropy": 0.0,
            "selective_fallback_selected_window_count": 0,
            "tile_rank_by_best_rejected_score": 2,
            "tile_rank_by_rejected_score_x_bp_sum": 2
          },
          "rescue_gain_strict_keys": []
        }
      ]
    }
  ]
}
EOF

OUT="$WORK/out"
python3 "$ROOT/scripts/search_two_stage_task_trigger_rankings.py" \
  --analysis-summary "$WORK/analysis_summary.json" \
  --budget 1 \
  --budget 2 \
  --target-budget 2 \
  --promotion-min-delta-top10 0.3 \
  --promotion-min-delta-score-weighted-recall 0.25 \
  --promotion-max-delta-refine-total-bp 45 \
  --output-dir "$OUT" >/dev/null

python3 - "$OUT/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert summary["target_budget"] == 2
assert summary["budgets"] == [1, 2]
assert summary["oracle_reference"]["ranking"] == "oracle_rescue_gain"
oracle_budget2 = summary["oracle_reference"]["target_budget_summary"]
assert math.isclose(oracle_budget2["delta_top_hit_retention"], 0.0)
assert math.isclose(oracle_budget2["delta_top10_retention"], 2.0 / 6.0)
assert math.isclose(oracle_budget2["delta_score_weighted_recall"], 185.0 / 573.0)
assert oracle_budget2["delta_refine_total_bp_total"] == 38

candidates = {item["name"]: item for item in summary["candidates"]}
assert set(candidates) == {
    "rule_score_mass_gap_v2",
    "rule_support_reason_pressure_v2",
    "lr_budget16_rank_v1",
    "hgb_budget16_rank_v1",
}

for name, item in candidates.items():
    assert item["target_budget_summary"]["budget"] == 2
    assert item["passes_promotion_gate"] is True
    assert item["promotion_gate"]["top_hit_ok"] is True
    assert item["promotion_gate"]["top10_ok"] is True
    assert item["promotion_gate"]["score_weighted_ok"] is True
    assert item["promotion_gate"]["refine_bp_ok"] is True
    assert math.isclose(item["target_budget_summary"]["delta_top_hit_retention"], 0.0)
    assert math.isclose(item["target_budget_summary"]["delta_top10_retention"], 2.0 / 6.0)
    assert item["target_budget_summary"]["delta_score_weighted_recall"] > 0.25
    assert item["target_budget_summary"]["delta_refine_total_bp_total"] <= 45

rule_item = candidates["rule_score_mass_gap_v2"]
assert rule_item["kind"] == "rule"
assert rule_item["training"]["strategy"] == "rule_based"
assert [row["task_key"]["fragment_index"] for row in rule_item["target_budget_summary"]["selected_tasks"]] == [1, 3]
assert math.isclose(rule_item["target_budget_summary"]["delta_score_weighted_recall"], 185.0 / 573.0)
assert rule_item["target_budget_summary"]["delta_refine_total_bp_total"] == 38

learned_lr = candidates["lr_budget16_rank_v1"]
assert learned_lr["kind"] == "learned"
assert learned_lr["training"]["strategy"] == "leave_anchor_out_regression"
assert learned_lr["training"]["target_budget"] == 2
assert learned_lr["training"]["fold_count"] == 3
assert len(learned_lr["feature_names"]) >= 10
assert learned_lr["target_budget_summary"]["oracle_overlap"]["overlap_task_count"] >= 1

learned_hgb = candidates["hgb_budget16_rank_v1"]
assert learned_hgb["kind"] == "learned"
assert learned_hgb["training"]["strategy"] == "leave_anchor_out_regression"
assert learned_hgb["training"]["fold_count"] == 3

assert summary["recommended_candidate"] in candidates
assert "rule_score_mass_gap_v2" in summary["passing_candidates"]
assert "lr_budget16_rank_v1" in summary["passing_candidates"]
PY

grep -q "Task Trigger Ranking Search" "$OUT/summary.md"
grep -q "rule_score_mass_gap_v2" "$OUT/summary.md"
grep -q "lr_budget16_rank_v1" "$OUT/summary.md"

echo "ok"
