#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_rerun_two_stage_panel_with_candidate_env"
rm -rf "$WORK"
mkdir -p "$WORK/panel" "$WORK/data"

printf '>anchor_a\nACGTACGTACGT\n' >"$WORK/data/anchor_a.fa"
printf '>rna\nUGCAUGCA\n' >"$WORK/data/rna.fa"

cat >"$WORK/panel/report.json" <<EOF
{
  "compare_output_mode": "lite",
  "inputs": {
    "rule": 0,
    "strand": ""
  },
  "prefilter_topk": 64,
  "peak_suppress_bp": 5,
  "score_floor_delta": 0,
  "refine_pad_bp": 64,
  "refine_merge_gap_bp": 32,
  "reject_defaults": {
    "min_peak_score": 80,
    "min_support": 2,
    "min_margin": 6,
    "strong_score_override": 100,
    "max_windows_per_task": 8,
    "max_bp_per_task": 32768
  },
  "runs": {
    "deferred_exact_minimal_v2_selective_fallback": {
      "debug_windows_csv": ""
    }
  }
}
EOF

cat >"$WORK/panel/summary.json" <<EOF
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
      "shard_path": "$WORK/data/anchor_a.fa",
      "report_path": "$WORK/panel/report.json"
    }
  ]
}
EOF

python3 "$ROOT/scripts/rerun_two_stage_panel_with_candidate_env.py" \
  --panel-summary "$WORK/panel/summary.json" \
  --output-dir "$WORK/out" \
  --longtarget "$ROOT/longtarget_cuda" \
  --candidate-env LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_MAX_KEPT_WINDOWS=2 \
  --candidate-env LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_GAP=10 \
  --dry-run >/dev/null

python3 - "$WORK/out/dry_run.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["selected_tile_count"] == 1
assert report["candidate_run_label"] == "deferred_exact_minimal_v2_selective_fallback"
assert report["candidate_env_overrides"] == {
    "LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_MAX_KEPT_WINDOWS": "2",
    "LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_GAP": "10",
}
cmd = report["commands"][0]
assert "--run-env" in cmd
assert (
    "deferred_exact_minimal_v2_selective_fallback:LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_MAX_KEPT_WINDOWS=2"
    in cmd
)
assert (
    "deferred_exact_minimal_v2_selective_fallback:LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_GAP=10"
    in cmd
)
PY

grep -q "candidate_env_overrides" "$WORK/out/dry_run.md"
grep -q "deferred_exact_minimal_v2_selective_fallback" "$WORK/out/dry_run.md"

echo "ok"
