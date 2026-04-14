#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LONGTARGET_BIN="${LONGTARGET_BIN:-${TARGET:-$ROOT/longtarget_cuda}}"

if [[ ! -x "$LONGTARGET_BIN" ]]; then
  (cd "$ROOT" && make build-cuda)
fi

WORK="$ROOT/.tmp/check_two_stage_task_rerun_runtime"
rm -rf "$WORK"
mkdir -p "$WORK"

BASELINE_WORK="$WORK/baseline"
GOOD_WORK="$WORK/good"
BAD_WORK="$WORK/bad"
GOOD_TASKS="$WORK/selected_tasks_good.tsv"
BAD_TASKS="$WORK/selected_tasks_bad_strand.tsv"

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
    --run-label legacy \
    --run-label deferred_exact_minimal_v3_scoreband_75_79 \
    --debug-window-run-label deferred_exact_minimal_v3_scoreband_75_79 >/dev/null
)

python3 - "$BASELINE_WORK/deferred_exact_minimal_v3_scoreband_75_79/two_stage_windows.tsv" "$GOOD_TASKS" "$BAD_TASKS" <<'PY'
import csv
import sys
from collections import defaultdict
from pathlib import Path

debug_path = Path(sys.argv[1])
good_path = Path(sys.argv[2])
bad_path = Path(sys.argv[3])

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

header = "\t".join(
    [
        "fragment_index",
        "fragment_start_in_seq",
        "fragment_end_in_seq",
        "reverse_mode",
        "parallel_mode",
        "strand",
        "rule",
    ]
)

good_row = "\t".join(str(value) for value in selected)
bad_selected = list(selected)
bad_selected[5] = "__WRONG_STRAND__"
bad_row = "\t".join(str(value) for value in bad_selected)

good_path.write_text(header + "\n" + good_row + "\n", encoding="utf-8")
bad_path.write_text(header + "\n" + bad_row + "\n", encoding="utf-8")
PY

(
  cd "$ROOT"
  python3 ./scripts/benchmark_two_stage_threshold_modes.py \
    --work-dir "$GOOD_WORK" \
    --longtarget "$LONGTARGET_BIN" \
    --compare-output-mode lite \
    --prefilter-topk 64 \
    --peak-suppress-bp 5 \
    --score-floor-delta 0 \
    --refine-pad-bp 64 \
    --refine-merge-gap-bp 32 \
    --run-label legacy \
    --run-label deferred_exact_minimal_v3_task_rerun_budget8 \
    --run-env deferred_exact_minimal_v3_task_rerun_budget8:LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH="$GOOD_TASKS" >/dev/null
)

(
  cd "$ROOT"
  python3 ./scripts/benchmark_two_stage_threshold_modes.py \
    --work-dir "$BAD_WORK" \
    --longtarget "$LONGTARGET_BIN" \
    --compare-output-mode lite \
    --prefilter-topk 64 \
    --peak-suppress-bp 5 \
    --score-floor-delta 0 \
    --refine-pad-bp 64 \
    --refine-merge-gap-bp 32 \
    --run-label legacy \
    --run-label deferred_exact_minimal_v3_task_rerun_budget16 \
    --run-env deferred_exact_minimal_v3_task_rerun_budget16:LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH="$BAD_TASKS" >/dev/null
)

python3 - "$BASELINE_WORK/report.json" "$GOOD_WORK/report.json" "$BAD_WORK/report.json" <<'PY'
import json
import sys

baseline = json.load(open(sys.argv[1], "r", encoding="utf-8"))
good = json.load(open(sys.argv[2], "r", encoding="utf-8"))
bad = json.load(open(sys.argv[3], "r", encoding="utf-8"))

baseline_run = baseline["runs"]["deferred_exact_minimal_v3_scoreband_75_79"]
good_run = good["runs"]["deferred_exact_minimal_v3_task_rerun_budget8"]
bad_run = bad["runs"]["deferred_exact_minimal_v3_task_rerun_budget16"]

assert good_run["task_rerun_enabled"] == 1
assert good_run["task_rerun_budget"] == 8
assert good_run["task_rerun_selected_tasks"] == 1
assert good_run["task_rerun_effective_tasks"] == 1
assert good_run["task_rerun_added_windows"] > 0
assert good_run["task_rerun_refine_bp_total"] > 0
assert good_run["task_rerun_selected_tasks_path"].endswith("selected_tasks_good.tsv")
assert good_run["refine_total_bp"] > baseline_run["refine_total_bp"]

assert bad_run["task_rerun_enabled"] == 1
assert bad_run["task_rerun_budget"] == 16
assert bad_run["task_rerun_effective_tasks"] == 0
assert bad_run["task_rerun_added_windows"] == 0
assert bad_run["task_rerun_refine_bp_total"] == 0
assert bad_run["task_rerun_selected_tasks_path"].endswith("selected_tasks_bad_strand.tsv")
PY

echo "ok"
