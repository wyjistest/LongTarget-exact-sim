#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_summarize_two_stage_frontier"
rm -rf "$WORK"
mkdir -p "$WORK/r1" "$WORK/r2"

cat >"$WORK/r1/report.json" <<'EOF'
{
  "inputs": {"dna_basename": "anchor_a.fa"},
  "quality_gate": {
    "min_relaxed_recall": 0.7,
    "min_top_hit_retention": 0.5,
    "require_qualifying_run": false
  },
  "runs": [
    {
      "prefilter_backend": "prealign_cuda",
      "prefilter_topk": 64,
      "peak_suppress_bp": 0,
      "score_floor_delta": 0,
      "refine_pad_bp": 64,
      "refine_merge_gap_bp": 32,
      "wall_seconds": 10.0,
      "internal_seconds": 9.5,
      "prefilter_hits": 12,
      "refine_window_count": 3,
      "refine_total_bp": 1200,
      "comparison": {
        "relaxed": {"recall": 0.6},
        "top_hit_retention": 0.0,
        "top5_retention": 0.2,
        "top10_retention": 0.3,
        "score_weighted_recall": 0.4,
        "per_output_comparisons": {
          "anchor_a-TFOsorted.lite": {
            "relaxed": {"recall": 0.6},
            "top_hit_retention": 0.0,
            "top5_retention": 0.2,
            "top10_retention": 0.3,
            "score_weighted_recall": 0.4
          }
        }
      }
    },
    {
      "prefilter_backend": "prealign_cuda",
      "prefilter_topk": 128,
      "peak_suppress_bp": 5,
      "score_floor_delta": 0,
      "refine_pad_bp": 64,
      "refine_merge_gap_bp": 32,
      "wall_seconds": 12.0,
      "internal_seconds": 11.0,
      "prefilter_hits": 18,
      "refine_window_count": 2,
      "refine_total_bp": 900,
      "comparison": {
        "relaxed": {"recall": 0.9},
        "top_hit_retention": 0.8,
        "top5_retention": 0.9,
        "top10_retention": 0.95,
        "score_weighted_recall": 0.85,
        "per_output_comparisons": {
          "anchor_a-TFOsorted.lite": {
            "relaxed": {"recall": 0.85},
            "top_hit_retention": 0.8,
            "top5_retention": 0.9,
            "top10_retention": 0.95,
            "score_weighted_recall": 0.85
          }
        }
      }
    }
  ]
}
EOF

cat >"$WORK/r2/report.json" <<'EOF'
{
  "inputs": {"dna_basename": "anchor_b.fa"},
  "quality_gate": {
    "min_relaxed_recall": 0.7,
    "min_top_hit_retention": 0.5,
    "require_qualifying_run": false
  },
  "runs": [
    {
      "prefilter_backend": "prealign_cuda",
      "prefilter_topk": 64,
      "peak_suppress_bp": 0,
      "score_floor_delta": 0,
      "refine_pad_bp": 64,
      "refine_merge_gap_bp": 32,
      "wall_seconds": 9.0,
      "internal_seconds": 8.5,
      "prefilter_hits": 14,
      "refine_window_count": 4,
      "refine_total_bp": 1400,
      "comparison": {
        "relaxed": {"recall": 0.72},
        "top_hit_retention": 0.4,
        "top5_retention": 0.5,
        "top10_retention": 0.55,
        "score_weighted_recall": 0.45,
        "per_output_comparisons": {
          "anchor_b-TFOsorted.lite": {
            "relaxed": {"recall": 0.72},
            "top_hit_retention": 0.4,
            "top5_retention": 0.5,
            "top10_retention": 0.55,
            "score_weighted_recall": 0.45
          }
        }
      }
    },
    {
      "prefilter_backend": "prealign_cuda",
      "prefilter_topk": 128,
      "peak_suppress_bp": 5,
      "score_floor_delta": 0,
      "refine_pad_bp": 64,
      "refine_merge_gap_bp": 32,
      "wall_seconds": 13.0,
      "internal_seconds": 12.0,
      "prefilter_hits": 16,
      "refine_window_count": 2,
      "refine_total_bp": 950,
      "comparison": {
        "relaxed": {"recall": 0.82},
        "top_hit_retention": 0.75,
        "top5_retention": 0.8,
        "top10_retention": 0.9,
        "score_weighted_recall": 0.78,
        "per_output_comparisons": {
          "anchor_b-TFOsorted.lite": {
            "relaxed": {"recall": 0.8},
            "top_hit_retention": 0.75,
            "top5_retention": 0.8,
            "top10_retention": 0.9,
            "score_weighted_recall": 0.78
          }
        }
      }
    }
  ]
}
EOF

python3 "$ROOT/scripts/summarize_two_stage_frontier.py" \
  --format json \
  "$WORK/r1/report.json" \
  "$WORK/r2/report.json" >"$WORK/summary.json"

python3 - "$WORK/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert summary["report_count"] == 2
assert len(summary["rows"]) == 2

rows = {
    (
        row["prefilter_topk"],
        row["peak_suppress_bp"],
        row["score_floor_delta"],
        row["refine_pad_bp"],
        row["refine_merge_gap_bp"],
    ): row
    for row in summary["rows"]
}

fast_bad = rows[(64, 0, 0, 64, 32)]
assert fast_bad["report_count"] == 2
assert fast_bad["zero_top_hit_reports"] == 1
assert fast_bad["all_top_hit_nonzero"] is False
assert fast_bad["qualifying_reports"] == 0
assert fast_bad["mean_prefilter_hits"] == 13.0
assert fast_bad["mean_refine_window_count"] == 3.5
assert fast_bad["mean_refine_total_bp"] == 1300.0
assert fast_bad["mean_top5_retention"] == 0.35
assert fast_bad["min_top10_retention"] == 0.3
assert fast_bad["mean_score_weighted_recall"] == 0.425

slower_good = rows[(128, 5, 0, 64, 32)]
assert slower_good["report_count"] == 2
assert slower_good["zero_top_hit_reports"] == 0
assert slower_good["all_top_hit_nonzero"] is True
assert slower_good["qualifying_reports"] == 2
assert slower_good["min_worst_output_relaxed_recall"] == 0.8
assert slower_good["min_worst_output_top_hit_retention"] == 0.75
assert slower_good["mean_prefilter_hits"] == 17.0
assert slower_good["mean_refine_window_count"] == 2.0
assert slower_good["mean_refine_total_bp"] == 925.0
assert slower_good["mean_top5_retention"] == 0.85
assert slower_good["min_top10_retention"] == 0.9
assert slower_good["min_score_weighted_recall"] == 0.78
assert slower_good["pareto_optimal"] is True
PY

python3 "$ROOT/scripts/summarize_two_stage_frontier.py" \
  "$WORK/r1/report.json" \
  "$WORK/r2/report.json" >"$WORK/summary.md"

grep -q "prefilter_topk" "$WORK/summary.md"
grep -q "mean_prefilter_hits" "$WORK/summary.md"
grep -q "mean_top5_retention" "$WORK/summary.md"
grep -q "min_score_weighted_recall" "$WORK/summary.md"
grep -q "pareto_optimal" "$WORK/summary.md"
grep -q "128" "$WORK/summary.md"

echo "ok"
