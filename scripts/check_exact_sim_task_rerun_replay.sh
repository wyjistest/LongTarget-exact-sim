#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LONGTARGET_BIN="${LONGTARGET_BIN:-${TARGET:-$ROOT/longtarget_cuda}}"
REPLAY_BIN="${REPLAY_BIN:-$ROOT/exact_sim_task_rerun_replay}"

if [[ ! -x "$LONGTARGET_BIN" ]]; then
  (cd "$ROOT" && make build-cuda)
fi

WORK="$ROOT/.tmp/check_exact_sim_task_rerun_replay"
rm -rf "$WORK"
mkdir -p "$WORK"

BASELINE_WORK="$WORK/baseline"
SELECTED_TASKS="$WORK/selected_tasks.tsv"
PANEL_SUMMARY="$WORK/panel_summary.json"
FEASIBILITY_OUT="$WORK/feasibility"
REPLAY_OUT="$WORK/replay"
COMPARE_OUT="$WORK/compare"

(
  cd "$ROOT"
  python3 ./scripts/benchmark_two_stage_threshold_modes.py \
    --work-dir "$BASELINE_WORK" \
    --longtarget "$LONGTARGET_BIN" \
    --compare-output-mode lite \
    --prefilter-topk 64 \
    --peak-suppress-bp 5 \
    --score-floor-delta 0 \
    --refine-pad-bp 64 \
    --refine-merge-gap-bp 32 \
    --run-label deferred_exact_minimal_v3_scoreband_75_79 \
    --debug-window-run-label deferred_exact_minimal_v3_scoreband_75_79 >/dev/null
)

python3 - "$BASELINE_WORK/deferred_exact_minimal_v3_scoreband_75_79/two_stage_windows.tsv" "$SELECTED_TASKS" "$PANEL_SUMMARY" "$BASELINE_WORK/report.json" <<'PY'
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

debug_path = Path(sys.argv[1])
selected_path = Path(sys.argv[2])
panel_summary_path = Path(sys.argv[3])
report_path = Path(sys.argv[4])

rows = list(csv.DictReader(debug_path.open("r", encoding="utf-8"), delimiter="\t"))
groups = defaultdict(list)
for row in rows:
    key = (
        int(row["fragment_index"]),
        int(row["fragment_start_in_seq"]),
        int(row["fragment_end_in_seq"]),
        int(row["reverse_mode"]),
        int(row["parallel_mode"]),
        row["strand"],
        int(row["rule"]),
    )
    groups[key].append(row)

selected = None
for key, group in groups.items():
    before_gate = sum(int(row["before_gate"]) for row in group)
    after_gate = sum(int(row["after_gate"]) for row in group)
    if before_gate > after_gate and after_gate > 0:
        selected = key
        break

if selected is None:
    raise SystemExit("failed to find a task with rejected-but-runnable windows")

selected_path.write_text(
    "\n".join(
        [
            "fragment_index\tfragment_start_in_seq\tfragment_end_in_seq\treverse_mode\tparallel_mode\tstrand\trule",
            "\t".join(str(value) for value in selected),
            "",
        ]
    ),
    encoding="utf-8",
)

summary = {
    "baseline_run_label": "deferred_exact_minimal_v3_scoreband_75_79",
    "candidate_run_label": "deferred_exact_minimal_v3_task_rerun_budget16",
    "selected_microanchors": [
        {
            "anchor_label": "sample",
            "selection_bucket_length_bp": 25000,
            "selection_kind": "strongest_shrink",
            "selection_rank": 0,
            "start_bp": 1,
            "length_bp": 25000,
            "report_path": str(report_path),
            "task_rerun_selected_tasks_path": str(selected_path),
        }
    ],
}
panel_summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
PY

python3 "$ROOT/scripts/benchmark_two_stage_task_rerun_kernel_feasibility.py" \
  --panel-summary "$PANEL_SUMMARY" \
  --longtarget "$LONGTARGET_BIN" \
  --output-dir "$FEASIBILITY_OUT" >/dev/null

"$REPLAY_BIN" \
  --corpus-manifest "$FEASIBILITY_OUT/task_rerun_corpus_manifest.tsv" \
  --output-dir "$REPLAY_OUT" >/dev/null

python3 "$ROOT/scripts/benchmark_two_stage_task_rerun_kernel_feasibility.py" \
  --panel-summary "$PANEL_SUMMARY" \
  --longtarget "$LONGTARGET_BIN" \
  --output-dir "$COMPARE_OUT" \
  --compare-task-output-root "$REPLAY_OUT" >/dev/null

python3 - "$COMPARE_OUT/summary.json" <<'PY'
import json
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
comparison = summary["candidate_task_output_comparison"]
assert comparison["semantic_equivalent"] is True
assert comparison["mismatched_tile_count"] == 0
assert comparison["compared_tile_count"] == 1
PY

echo "ok"
