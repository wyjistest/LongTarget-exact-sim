#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LONGTARGET_BIN="${LONGTARGET_BIN:-${TARGET:-$ROOT/longtarget_cuda}}"

if [[ ! -x "$LONGTARGET_BIN" ]]; then
  (cd "$ROOT" && make build-cuda)
fi

WORK="$ROOT/.tmp/check_two_stage_frontier_sweep"
WORK_STRICT="$ROOT/.tmp/check_two_stage_frontier_sweep_strict"
rm -rf "$WORK" "$WORK_STRICT"

(
  cd "$ROOT"
  python3 ./scripts/benchmark_two_stage_frontier_sweep.py \
    --work-dir "$WORK" \
    --longtarget "$LONGTARGET_BIN" \
    --prefilter-topk-values 64,128 \
    --peak-suppress-bp-values 0,5 \
    --score-floor-delta-values 0 \
    --refine-pad-values 64 \
    --refine-merge-gap-values 32 \
    --min-relaxed-recall 0.0 \
    --min-top-hit-retention 0.0 >/dev/null
)

(
  cd "$ROOT"
  python3 ./scripts/benchmark_two_stage_frontier_sweep.py \
    --work-dir "$WORK_STRICT" \
    --longtarget "$LONGTARGET_BIN" \
    --prefilter-topk-values 64 \
    --peak-suppress-bp-values 5 \
    --score-floor-delta-values 0 \
    --refine-pad-values 64 \
    --refine-merge-gap-values 32 \
    --min-relaxed-recall 2.0 \
    --min-top-hit-retention 2.0 >/dev/null
)

python3 - "$WORK/report.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["compare_output_mode"] == "lite"
assert report["prefilter_backend"] == "prealign_cuda"
assert report["prefilter_topk_values"] == [64, 128]
assert report["peak_suppress_bp_values"] == [0, 5]
assert report["score_floor_delta_values"] == [0]
assert report["refine_pad_bp_values"] == [64]
assert report["refine_merge_gap_bp_values"] == [32]
assert report["quality_gate"] == {
    "min_relaxed_recall": 0.0,
    "min_top_hit_retention": 0.0,
    "require_qualifying_run": False,
}

exact = report["exact"]
assert exact["output_mode"] == "lite"
assert exact["line_count"] >= 0

runs = report["runs"]
assert len(runs) == 4
for run in runs:
    assert run["prefilter_backend"] == "prealign_cuda"
    assert run["prefilter_topk"] in (64, 128)
    assert run["peak_suppress_bp"] in (0, 5)
    assert run["score_floor_delta"] == 0
    assert run["refine_pad_bp"] == 64
    assert run["refine_merge_gap_bp"] == 32
    assert run["wall_seconds"] >= 0
    assert run["internal_seconds"] >= 0
    assert run["prefilter_hits"] >= 0
    assert run["refine_window_count"] >= 0
    assert run["refine_total_bp"] >= 0
    assert run["output_mode"] == "lite"
    assert "strict" in run["comparison"]
    assert "relaxed" in run["comparison"]
    assert "top_hit_retention" in run["comparison"]
    assert "per_output_comparisons" in run["comparison"]
    assert run["comparison"]["per_output_comparisons"]

assert report["best"] == report["best_overall"]
assert report["best_overall"]["prefilter_topk"] in (64, 128)
assert report["best_qualifying"]["prefilter_topk"] in (64, 128)
PY

python3 - "$WORK_STRICT/report.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["quality_gate"] == {
    "min_relaxed_recall": 2.0,
    "min_top_hit_retention": 2.0,
    "require_qualifying_run": False,
}
assert report["best"] == report["best_overall"]
assert report["best_qualifying"] is None
PY

echo "ok"
