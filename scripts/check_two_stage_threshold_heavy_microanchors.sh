#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LONGTARGET_BIN="${LONGTARGET_BIN:-${TARGET:-$ROOT/longtarget_cuda}}"

if [[ ! -x "$LONGTARGET_BIN" ]]; then
  (cd "$ROOT" && make build-cuda)
fi

WORK="$ROOT/.tmp/check_two_stage_threshold_heavy_microanchors"
rm -rf "$WORK"

(
  cd "$ROOT"
  python3 ./scripts/benchmark_two_stage_threshold_heavy_microanchors.py \
    --work-dir "$WORK" \
    --longtarget "$LONGTARGET_BIN" \
    --compare-output-mode lite \
    --rna H19.fa \
    --heavy-anchor testDNA.fa \
    --tile-spec 1000:1000:2 \
    --tile-spec 2000:2000:1 \
    --gated-run-label deferred_exact_minimal_v2_selective_fallback >/dev/null
)

python3 - "$WORK/summary.json" "$WORK/discovery_report.json" <<'PY'
import json
import sys
from pathlib import Path

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
discovery = json.load(open(sys.argv[2], "r", encoding="utf-8"))

assert summary["compare_output_mode"] == "lite"
assert summary["prefilter_backend"] == "prealign_cuda"
assert summary["gated_run_label"] == "deferred_exact_minimal_v2_selective_fallback"
assert len(summary["tile_specs"]) == 2
assert len(summary["selected_microanchors"]) == 4
assert summary["decision_flags"].keys() == {
    "needs_stronger_gate",
    "needs_relaxation",
    "ready_for_broader_anchor_sweep",
}
assert summary["aggregate"]["selected_microanchor_count"] == 4
assert "mean_top5_retention" in summary["aggregate"]
assert "mean_top10_retention" in summary["aggregate"]
assert "mean_score_weighted_recall" in summary["aggregate"]
assert "min_top5_retention" in summary["aggregate"]
assert "min_top10_retention" in summary["aggregate"]
assert "min_score_weighted_recall" in summary["aggregate"]

for item in summary["selected_microanchors"]:
    assert item["length_bp"] in {1000, 2000}
    assert item["selection_rank"] in {1, 2}
    assert item["selection_kind"] in {"strongest_shrink", "medium_shrink"}
    assert Path(item["shard_path"]).exists()
    assert Path(item["report_path"]).exists()
    assert set(item["runs"]) == {"legacy", "deferred_exact", "deferred_exact_minimal_v2_selective_fallback"}
    assert set(item["comparisons_vs_legacy"]) == {"deferred_exact", "deferred_exact_minimal_v2_selective_fallback"}
    assert "top5_retention" in item["comparisons_vs_legacy"]["deferred_exact_minimal_v2_selective_fallback"]
    assert "top10_retention" in item["comparisons_vs_legacy"]["deferred_exact_minimal_v2_selective_fallback"]
    assert "score_weighted_recall" in item["comparisons_vs_legacy"]["deferred_exact_minimal_v2_selective_fallback"]

assert discovery["report_count"] >= 3
assert len(discovery["candidates"]) >= 3
assert discovery["discovery_mode"] == "prefilter_only"
for candidate in discovery["candidates"][:3]:
    assert candidate["status"] in {"ok", "empty", "prefilter_failed", "hard_failed", "unsupported"}
    assert Path(candidate["shard_path"]).exists()
    assert Path(candidate["discovery_stderr_path"]).exists()
    payload = candidate["discovery"]
    assert payload["mode"] == "prefilter_only"
    assert payload["status"] == candidate["status"]
    assert payload["prefilter_backend"] == "prealign_cuda"
    assert payload["prefilter_hits"] >= 0
    assert payload["tasks_with_any_seed"] >= 0
    assert payload["tasks_with_any_refine_window_before_gate"] >= 0
    assert payload["tasks_with_any_refine_window_after_gate"] >= 0
    assert payload["windows_before_gate"] >= 0
    assert payload["windows_after_gate"] >= 0
    assert payload["prefilter_failed_tasks"] >= 0
    assert payload["prefilter_only_seconds"] >= 0.0
    assert payload["gate_seconds"] >= 0.0
    assert isinstance(payload["predicted_skip"], bool)
PY

grep -q "Two-Stage Threshold Heavy Micro-Anchor Summary" "$WORK/summary.md"
grep -q "top5_retention" "$WORK/summary.md"
grep -q "score_weighted_recall" "$WORK/summary.md"

echo "ok"
