#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_summarize_two_stage_panel_decision"
rm -rf "$WORK"
mkdir -p "$WORK/case_inside" "$WORK/case_near"

cat >"$WORK/case_inside/compare.json" <<'EOF'
{
  "baseline_run_label": "deferred_exact_minimal_v2",
  "candidate_run_label": "deferred_exact_minimal_v2_selective_fallback",
  "shared_tile_count": 12,
  "aggregate": {
    "top5_retention": {"baseline_mean": 0.83, "candidate_mean": 0.83, "delta_mean": 0.0},
    "top10_retention": {"baseline_mean": 0.83, "candidate_mean": 0.83, "delta_mean": 0.0},
    "score_weighted_recall": {"baseline_mean": 0.80, "candidate_mean": 0.80, "delta_mean": 0.0},
    "threshold_skipped_after_gate": {"baseline_mean": 62.0, "candidate_mean": 62.0, "delta_mean": 0.0},
    "threshold_batch_size_mean": {"baseline_mean": 200.0, "candidate_mean": 200.0, "delta_mean": 0.0},
    "threshold_batched_seconds": {"baseline_mean": 13.0, "candidate_mean": 16.0, "delta_mean": 3.0},
    "refine_total_bp": {"baseline_mean": 275000.0, "candidate_mean": 275000.0, "delta_mean": 0.0},
    "candidate_selective_fallback_totals": {
      "selective_fallback_triggered_tasks": 0,
      "selective_fallback_non_empty_triggered_tasks": 0,
      "selective_fallback_selected_windows": 0,
      "selective_fallback_selected_bp_total": 0
    }
  }
}
EOF

cat >"$WORK/case_inside/attribution.json" <<'EOF'
{
  "candidate_label": "deferred_exact_minimal_v2_selective_fallback",
  "aggregate": {
    "overall": {
      "share_by_class": {
        "inside_kept_window": 0.05,
        "inside_rejected_window": 0.66,
        "outside_kept_but_near_kept": 0.01,
        "far_outside_all_kept": 0.28
      }
    },
    "top5_missing": {
      "share_by_class": {
        "inside_kept_window": 0.10,
        "inside_rejected_window": 0.70,
        "outside_kept_but_near_kept": 0.00,
        "far_outside_all_kept": 0.20
      }
    },
    "top10_missing": {
      "share_by_class": {
        "inside_kept_window": 0.10,
        "inside_rejected_window": 0.55,
        "outside_kept_but_near_kept": 0.00,
        "far_outside_all_kept": 0.35
      }
    },
    "score_weighted_missing": {
      "share_of_missing_weight_by_class": {
        "inside_kept_window": 0.04,
        "inside_rejected_window": 0.67,
        "outside_kept_but_near_kept": 0.01,
        "far_outside_all_kept": 0.28
      }
    }
  }
}
EOF

cat >"$WORK/case_near/compare.json" <<'EOF'
{
  "baseline_run_label": "deferred_exact_minimal_v2",
  "candidate_run_label": "deferred_exact_minimal_v2_selective_fallback",
  "shared_tile_count": 12,
  "aggregate": {
    "top5_retention": {"baseline_mean": 0.83, "candidate_mean": 0.86, "delta_mean": 0.03},
    "top10_retention": {"baseline_mean": 0.83, "candidate_mean": 0.87, "delta_mean": 0.04},
    "score_weighted_recall": {"baseline_mean": 0.80, "candidate_mean": 0.83, "delta_mean": 0.03},
    "threshold_skipped_after_gate": {"baseline_mean": 62.0, "candidate_mean": 60.0, "delta_mean": -2.0},
    "threshold_batch_size_mean": {"baseline_mean": 200.0, "candidate_mean": 205.0, "delta_mean": 5.0},
    "threshold_batched_seconds": {"baseline_mean": 13.0, "candidate_mean": 14.0, "delta_mean": 1.0},
    "refine_total_bp": {"baseline_mean": 275000.0, "candidate_mean": 280000.0, "delta_mean": 5000.0},
    "candidate_selective_fallback_totals": {
      "selective_fallback_triggered_tasks": 8,
      "selective_fallback_non_empty_triggered_tasks": 5,
      "selective_fallback_selected_windows": 8,
      "selective_fallback_selected_bp_total": 960
    }
  }
}
EOF

cat >"$WORK/case_near/attribution.json" <<'EOF'
{
  "candidate_label": "deferred_exact_minimal_v2_selective_fallback",
  "aggregate": {
    "overall": {
      "share_by_class": {
        "inside_kept_window": 0.12,
        "inside_rejected_window": 0.21,
        "outside_kept_but_near_kept": 0.48,
        "far_outside_all_kept": 0.19
      }
    },
    "top5_missing": {
      "share_by_class": {
        "inside_kept_window": 0.10,
        "inside_rejected_window": 0.20,
        "outside_kept_but_near_kept": 0.50,
        "far_outside_all_kept": 0.20
      }
    },
    "top10_missing": {
      "share_by_class": {
        "inside_kept_window": 0.11,
        "inside_rejected_window": 0.20,
        "outside_kept_but_near_kept": 0.49,
        "far_outside_all_kept": 0.20
      }
    },
    "score_weighted_missing": {
      "share_of_missing_weight_by_class": {
        "inside_kept_window": 0.13,
        "inside_rejected_window": 0.22,
        "outside_kept_but_near_kept": 0.46,
        "far_outside_all_kept": 0.19
      }
    }
  }
}
EOF

python3 "$ROOT/scripts/summarize_two_stage_panel_decision.py" \
  --compare-summary "$WORK/case_inside/compare.json" \
  --attribution-summary "$WORK/case_inside/attribution.json" \
  --output-dir "$WORK/case_inside/out" >/dev/null

python3 - "$WORK/case_inside/out/summary.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["recommended_next_step"] == "non_empty_ambiguity_triggered_selective_fallback"
assert report["residual_primary_class"]["score_weighted_missing"] == "inside_rejected_window"
assert report["fallback_effective"] is False
assert report["fallback_triggered"] is False
assert report["candidate_selective_fallback_totals"]["selective_fallback_non_empty_triggered_tasks"] == 0
PY

python3 "$ROOT/scripts/summarize_two_stage_panel_decision.py" \
  --compare-summary "$WORK/case_near/compare.json" \
  --attribution-summary "$WORK/case_near/attribution.json" \
  --output-dir "$WORK/case_near/out" >/dev/null

python3 - "$WORK/case_near/out/summary.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["recommended_next_step"] == "refine_pad_merge_sweep"
assert report["residual_primary_class"]["score_weighted_missing"] == "outside_kept_but_near_kept"
assert report["fallback_effective"] is True
assert report["fallback_triggered"] is True
assert report["candidate_selective_fallback_totals"]["selective_fallback_non_empty_triggered_tasks"] == 5
PY

grep -q "Two-Stage Panel Decision Summary" "$WORK/case_inside/out/summary.md"
grep -q "recommended_next_step" "$WORK/case_inside/out/summary.md"
grep -q "inside_rejected_window" "$WORK/case_inside/out/summary.md"

echo "ok"
