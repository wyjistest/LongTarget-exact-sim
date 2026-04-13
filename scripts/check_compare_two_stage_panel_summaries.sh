#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_compare_two_stage_panel_summaries"
rm -rf "$WORK"
mkdir -p "$WORK/base" "$WORK/candidate" "$WORK/mismatch"

cat >"$WORK/base/summary.json" <<'EOF'
{
  "gated_run_label": "deferred_exact_minimal_v2",
  "selected_microanchors": [
    {
      "anchor_label": "anchor_a",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 1,
      "start_bp": 1001,
      "length_bp": 25000,
      "end_bp": 26000,
      "report_path": "/tmp/base_anchor_a.json",
      "runs": {
        "deferred_exact_minimal_v2": {
          "threshold_skipped_after_gate": 10,
          "threshold_batch_size_mean": 20.0,
          "threshold_batched_seconds": 1.5,
          "refine_total_bp": 4000,
          "selective_fallback_non_empty_candidate_tasks": 0,
          "selective_fallback_non_empty_rejected_by_max_kept_windows_tasks": 0,
          "selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks": 0,
          "selective_fallback_non_empty_rejected_by_singleton_override_tasks": 0,
          "selective_fallback_non_empty_rejected_as_covered_by_kept_tasks": 0,
          "selective_fallback_non_empty_rejected_by_score_gap_tasks": 0,
          "selective_fallback_triggered_tasks": 0,
          "selective_fallback_non_empty_triggered_tasks": 0,
          "selective_fallback_selected_windows": 0,
          "selective_fallback_selected_bp_total": 0
        }
      },
      "comparisons_vs_legacy": {
        "deferred_exact_minimal_v2": {
          "top5_retention": 0.4,
          "top10_retention": 0.5,
          "score_weighted_recall": 0.6,
          "difference_class": "content_diff"
        }
      }
    },
    {
      "anchor_label": "anchor_b",
      "selection_bucket_length_bp": 50000,
      "selection_kind": "medium_shrink",
      "selection_rank": 2,
      "start_bp": 50001,
      "length_bp": 50000,
      "end_bp": 100000,
      "report_path": "/tmp/base_anchor_b.json",
      "runs": {
        "deferred_exact_minimal_v2": {
          "threshold_skipped_after_gate": 6,
          "threshold_batch_size_mean": 12.0,
          "threshold_batched_seconds": 0.7,
          "refine_total_bp": 2800,
          "selective_fallback_non_empty_candidate_tasks": 0,
          "selective_fallback_non_empty_rejected_by_max_kept_windows_tasks": 0,
          "selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks": 0,
          "selective_fallback_non_empty_rejected_by_singleton_override_tasks": 0,
          "selective_fallback_non_empty_rejected_as_covered_by_kept_tasks": 0,
          "selective_fallback_non_empty_rejected_by_score_gap_tasks": 0,
          "selective_fallback_triggered_tasks": 0,
          "selective_fallback_non_empty_triggered_tasks": 0,
          "selective_fallback_selected_windows": 0,
          "selective_fallback_selected_bp_total": 0
        }
      },
      "comparisons_vs_legacy": {
        "deferred_exact_minimal_v2": {
          "top5_retention": 0.7,
          "top10_retention": 0.8,
          "score_weighted_recall": 0.9,
          "difference_class": "ordering_or_format_only"
        }
      }
    }
  ]
}
EOF

cat >"$WORK/candidate/summary.json" <<'EOF'
{
  "gated_run_label": "deferred_exact_minimal_v2_selective_fallback",
  "selected_microanchors": [
    {
      "anchor_label": "anchor_a",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 1,
      "start_bp": 1001,
      "length_bp": 25000,
      "end_bp": 26000,
      "report_path": "/tmp/candidate_anchor_a.json",
      "runs": {
        "deferred_exact_minimal_v2_selective_fallback": {
          "threshold_skipped_after_gate": 5,
          "threshold_batch_size_mean": 22.0,
          "threshold_batched_seconds": 1.8,
          "refine_total_bp": 4300,
          "selective_fallback_non_empty_candidate_tasks": 4,
          "selective_fallback_non_empty_rejected_by_max_kept_windows_tasks": 1,
          "selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks": 0,
          "selective_fallback_non_empty_rejected_by_singleton_override_tasks": 1,
          "selective_fallback_non_empty_rejected_as_covered_by_kept_tasks": 0,
          "selective_fallback_non_empty_rejected_by_score_gap_tasks": 1,
          "selective_fallback_triggered_tasks": 2,
          "selective_fallback_non_empty_triggered_tasks": 1,
          "selective_fallback_selected_windows": 2,
          "selective_fallback_selected_bp_total": 120
        }
      },
      "comparisons_vs_legacy": {
        "deferred_exact_minimal_v2_selective_fallback": {
          "top5_retention": 0.6,
          "top10_retention": 0.7,
          "score_weighted_recall": 0.75,
          "difference_class": "content_diff"
        }
      }
    },
    {
      "anchor_label": "anchor_b",
      "selection_bucket_length_bp": 50000,
      "selection_kind": "medium_shrink",
      "selection_rank": 2,
      "start_bp": 50001,
      "length_bp": 50000,
      "end_bp": 100000,
      "report_path": "/tmp/candidate_anchor_b.json",
      "runs": {
        "deferred_exact_minimal_v2_selective_fallback": {
          "threshold_skipped_after_gate": 2,
          "threshold_batch_size_mean": 15.0,
          "threshold_batched_seconds": 0.8,
          "refine_total_bp": 3200,
          "selective_fallback_non_empty_candidate_tasks": 3,
          "selective_fallback_non_empty_rejected_by_max_kept_windows_tasks": 0,
          "selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks": 1,
          "selective_fallback_non_empty_rejected_by_singleton_override_tasks": 0,
          "selective_fallback_non_empty_rejected_as_covered_by_kept_tasks": 0,
          "selective_fallback_non_empty_rejected_by_score_gap_tasks": 1,
          "selective_fallback_triggered_tasks": 1,
          "selective_fallback_non_empty_triggered_tasks": 1,
          "selective_fallback_selected_windows": 1,
          "selective_fallback_selected_bp_total": 80
        }
      },
      "comparisons_vs_legacy": {
        "deferred_exact_minimal_v2_selective_fallback": {
          "top5_retention": 0.8,
          "top10_retention": 0.9,
          "score_weighted_recall": 0.95,
          "difference_class": "none"
        }
      }
    }
  ]
}
EOF

cat >"$WORK/mismatch/summary.json" <<'EOF'
{
  "gated_run_label": "deferred_exact_minimal_v2_selective_fallback",
  "selected_microanchors": [
    {
      "anchor_label": "anchor_a",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 1,
      "start_bp": 1002,
      "length_bp": 25000,
      "end_bp": 26001,
      "report_path": "/tmp/candidate_anchor_a_shifted.json",
      "runs": {
        "deferred_exact_minimal_v2_selective_fallback": {
          "threshold_skipped_after_gate": 5,
          "threshold_batch_size_mean": 22.0,
          "threshold_batched_seconds": 1.8,
          "refine_total_bp": 4300,
          "selective_fallback_non_empty_candidate_tasks": 4,
          "selective_fallback_non_empty_rejected_by_max_kept_windows_tasks": 1,
          "selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks": 0,
          "selective_fallback_non_empty_rejected_by_singleton_override_tasks": 1,
          "selective_fallback_non_empty_rejected_as_covered_by_kept_tasks": 0,
          "selective_fallback_non_empty_rejected_by_score_gap_tasks": 1,
          "selective_fallback_triggered_tasks": 2,
          "selective_fallback_non_empty_triggered_tasks": 1,
          "selective_fallback_selected_windows": 2,
          "selective_fallback_selected_bp_total": 120
        }
      },
      "comparisons_vs_legacy": {
        "deferred_exact_minimal_v2_selective_fallback": {
          "top5_retention": 0.6,
          "top10_retention": 0.7,
          "score_weighted_recall": 0.75,
          "difference_class": "content_diff"
        }
      }
    }
  ]
}
EOF

python3 "$ROOT/scripts/compare_two_stage_panel_summaries.py" \
  --baseline-panel-summary "$WORK/base/summary.json" \
  --candidate-panel-summary "$WORK/candidate/summary.json" \
  --output-dir "$WORK/out" >/dev/null

python3 - "$WORK/out/summary.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["baseline_run_label"] == "deferred_exact_minimal_v2"
assert report["candidate_run_label"] == "deferred_exact_minimal_v2_selective_fallback"
assert report["shared_tile_count"] == 2

agg = report["aggregate"]
assert agg["top5_retention"]["baseline_mean"] == 0.55
assert agg["top5_retention"]["candidate_mean"] == 0.7
assert agg["top5_retention"]["delta_mean"] == 0.15
assert agg["top10_retention"]["baseline_mean"] == 0.65
assert agg["top10_retention"]["candidate_mean"] == 0.8
assert agg["top10_retention"]["delta_mean"] == 0.15
assert agg["score_weighted_recall"]["baseline_mean"] == 0.75
assert agg["score_weighted_recall"]["candidate_mean"] == 0.85
assert agg["score_weighted_recall"]["delta_mean"] == 0.1
assert agg["threshold_skipped_after_gate"]["baseline_mean"] == 8.0
assert agg["threshold_skipped_after_gate"]["candidate_mean"] == 3.5
assert agg["threshold_skipped_after_gate"]["delta_mean"] == -4.5
assert agg["threshold_batch_size_mean"]["baseline_mean"] == 16.0
assert agg["threshold_batch_size_mean"]["candidate_mean"] == 18.5
assert agg["threshold_batch_size_mean"]["delta_mean"] == 2.5
assert agg["threshold_batched_seconds"]["baseline_mean"] == 1.1
assert agg["threshold_batched_seconds"]["candidate_mean"] == 1.3
assert agg["threshold_batched_seconds"]["delta_mean"] == 0.2
assert agg["refine_total_bp"]["baseline_mean"] == 3400.0
assert agg["refine_total_bp"]["candidate_mean"] == 3750.0
assert agg["refine_total_bp"]["delta_mean"] == 350.0

assert agg["difference_class_counts"]["baseline"] == {
    "content_diff": 1,
    "none": 0,
    "ordering_or_format_only": 1
}
assert agg["difference_class_counts"]["candidate"] == {
    "content_diff": 1,
    "none": 1,
    "ordering_or_format_only": 0
}
assert agg["difference_class_transitions"] == {
    "content_diff->content_diff": 1,
    "ordering_or_format_only->none": 1
}
assert agg["candidate_selective_fallback_totals"] == {
    "selective_fallback_non_empty_candidate_tasks": 7,
    "selective_fallback_non_empty_rejected_by_max_kept_windows_tasks": 1,
    "selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks": 1,
    "selective_fallback_non_empty_rejected_by_singleton_override_tasks": 1,
    "selective_fallback_non_empty_rejected_as_covered_by_kept_tasks": 0,
    "selective_fallback_non_empty_rejected_by_score_gap_tasks": 2,
    "selective_fallback_triggered_tasks": 3,
    "selective_fallback_non_empty_triggered_tasks": 2,
    "selective_fallback_selected_windows": 3,
    "selective_fallback_selected_bp_total": 200
}

tiles = report["per_tile"]
assert [tile["anchor_label"] for tile in tiles] == ["anchor_a", "anchor_b"]
assert tiles[0]["delta"]["top5_retention"] == 0.2
assert tiles[0]["delta"]["threshold_skipped_after_gate"] == -5.0
assert tiles[1]["delta"]["difference_class"] == "ordering_or_format_only->none"
PY

grep -q "Two-Stage Panel Summary Comparison" "$WORK/out/summary.md"
grep -q "candidate_selective_fallback_totals" "$WORK/out/summary.md"
grep -q "difference_class" "$WORK/out/summary.md"
grep -q "anchor_a" "$WORK/out/summary.md"

if python3 "$ROOT/scripts/compare_two_stage_panel_summaries.py" \
  --baseline-panel-summary "$WORK/base/summary.json" \
  --candidate-panel-summary "$WORK/mismatch/summary.json" \
  --output-dir "$WORK/mismatch_out" >"$WORK/mismatch.stdout" 2>"$WORK/mismatch.stderr"; then
  echo "expected mismatch comparison to fail" >&2
  exit 1
fi

grep -q "tile set mismatch" "$WORK/mismatch.stderr"

echo "ok"
