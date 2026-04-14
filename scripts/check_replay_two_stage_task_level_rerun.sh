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

python3 - "$OUT/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
budgets = {item["budget"]: item for item in summary["budgets"]}
assert sorted(budgets) == [1, 2]

budget1 = budgets[1]["aggregate"]
assert budget1["rerun_task_count"] == 1
assert budget1["rerun_added_window_count"] == 2
assert budget1["rerun_added_bp_total"] == 62
assert math.isclose(budget1["predicted_top_hit_retention"], 1.0)
assert math.isclose(budget1["predicted_top5_retention"], 0.75)
assert math.isclose(budget1["predicted_top10_retention"], 0.75)
assert math.isclose(budget1["predicted_score_weighted_recall"], 285.0 / 370.0)
assert budget1["selected_tasks"][0]["task_key"]["fragment_index"] == 1

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
PY

grep -q "Task-Level Exact Rerun Replay" "$OUT/summary.md"
grep -q "budget 2" "$OUT/summary.md"
