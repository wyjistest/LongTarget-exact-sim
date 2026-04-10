#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LONGTARGET_BIN="${LONGTARGET_BIN:-${TARGET:-$ROOT/longtarget_cuda}}"

if [[ ! -x "$LONGTARGET_BIN" ]]; then
  (cd "$ROOT" && make build-cuda)
fi

WORK="$ROOT/.tmp/check_two_stage_threshold_modes"
rm -rf "$WORK"

(
  cd "$ROOT"
  python3 ./scripts/benchmark_two_stage_threshold_modes.py \
    --work-dir "$WORK" \
    --longtarget "$LONGTARGET_BIN" \
    --compare-output-mode lite \
    --prefilter-topk 64 \
    --peak-suppress-bp 5 \
    --score-floor-delta 0 \
    --refine-pad-bp 64 \
    --refine-merge-gap-bp 32 \
    --run-label legacy \
    --run-label deferred_exact \
    --run-label deferred_exact_minimal_v2 \
    --debug-window-run-label deferred_exact_minimal_v2 >/dev/null
)

python3 - "$WORK/report.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["compare_output_mode"] == "lite"
assert report["prefilter_backend"] == "prealign_cuda"
assert report["prefilter_topk"] == 64
assert report["peak_suppress_bp"] == 5
assert report["score_floor_delta"] == 0
assert report["refine_pad_bp"] == 64
assert report["refine_merge_gap_bp"] == 32

runs = report["runs"]
assert set(runs) == {"legacy", "deferred_exact", "deferred_exact_minimal_v2"}
assert runs["legacy"]["threshold_mode"] == "legacy"
assert runs["legacy"]["reject_mode"] == "off"
assert runs["deferred_exact"]["threshold_mode"] == "deferred_exact"
assert runs["deferred_exact"]["reject_mode"] == "off"
assert runs["deferred_exact_minimal_v2"]["threshold_mode"] == "deferred_exact"
assert runs["deferred_exact_minimal_v2"]["reject_mode"] == "minimal_v2"
assert runs["deferred_exact_minimal_v2"]["debug_windows_csv"].endswith("two_stage_windows.tsv")

for label, run in runs.items():
    if label == "legacy":
        assert run["prefilter_backend"] in {"mixed", "prealign_cuda", "sim"}
    else:
        assert run["prefilter_backend"] == "prealign_cuda"
    assert run["wall_seconds"] >= 0
    assert run["internal_seconds"] >= 0
    assert run["prefilter_hits"] >= 0
    assert run["refine_window_count"] >= 0
    assert run["refine_total_bp"] >= 0
    assert run["tasks_with_any_seed"] >= 0
    assert run["tasks_with_any_refine_window_before_gate"] >= 0
    assert run["tasks_with_any_refine_window_after_gate"] >= 0
    assert run["threshold_invoked"] >= 0
    assert run["threshold_skipped_no_seed"] >= 0
    assert run["threshold_skipped_no_refine_window"] >= 0
    assert run["threshold_skipped_after_gate"] >= 0
    assert run["threshold_batch_count"] >= 0
    assert run["threshold_batch_tasks_total"] >= 0
    assert run["threshold_batch_size_mean"] >= 0
    assert run["threshold_batch_size_max"] >= 0
    assert run["threshold_batched_seconds"] >= 0
    assert run["windows_before_gate"] >= 0
    assert run["windows_after_gate"] >= 0
    assert run["singleton_rescued_windows"] >= 0
    assert run["singleton_rescued_tasks"] >= 0
    assert run["singleton_rescue_bp_total"] >= 0
    assert len(run["output_sha256"]) == 64
    assert len(run["normalized_output_sha256"]) == 64
    if label == "deferred_exact_minimal_v2":
        assert run["debug_windows_csv"]
        assert open(run["debug_windows_csv"], "r", encoding="utf-8").readline().startswith("task_index\t")
    else:
        assert run["debug_windows_csv"] == ""

comparisons = report["comparisons_vs_legacy"]
assert set(comparisons) == {"deferred_exact", "deferred_exact_minimal_v2"}
for comparison in comparisons.values():
    assert "strict" in comparison
    assert "relaxed" in comparison
    assert "top_hit_retention" in comparison
    assert "top5_retention" in comparison
    assert "top10_retention" in comparison
    assert "score_weighted_recall" in comparison
    assert "per_output_comparisons" in comparison
    assert "raw_equal" in comparison
    assert "normalized_equal" in comparison
    assert "tolerant_equal" in comparison
    assert "first_diff_examples" in comparison
    assert set(comparison["first_diff_examples"]) == {
        "missing_in_candidate",
        "missing_in_legacy",
        "score_changed",
    }
    assert comparison["difference_class"] in {"none", "ordering_or_format_only", "content_diff"}
    assert 0.0 <= comparison["top5_retention"] <= 1.0
    assert 0.0 <= comparison["top10_retention"] <= 1.0
    assert 0.0 <= comparison["score_weighted_recall"] <= 1.0
    for per_output in comparison["per_output_comparisons"].values():
        assert "top5_retention" in per_output
        assert "top10_retention" in per_output
        assert "score_weighted_recall" in per_output
PY

echo "ok"
