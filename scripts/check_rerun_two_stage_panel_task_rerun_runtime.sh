#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_rerun_two_stage_panel_task_rerun_runtime"
rm -rf "$WORK"

python3 "$ROOT/scripts/rerun_two_stage_panel_task_rerun_runtime.py" \
  --panel-summary "$ROOT/.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json" \
  --replay-summary "$ROOT/.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact/summary.json" \
  --budget 8 \
  --output-dir "$WORK" \
  --dry-run >/dev/null

python3 - "$WORK/dry_run.json" "$WORK" <<'PY'
import json
import sys
from pathlib import Path

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
work = Path(sys.argv[2]).resolve()

assert report["candidate_run_label"] == "deferred_exact_minimal_v3_task_rerun_budget8"
assert report["task_rerun_budget"] == 8
assert report["selected_tile_count"] > 0
assert report["selected_task_count_total"] > 0
assert report["commands"]

expected_root = work / "task_rerun_selected_tasks"
for command in report["commands"]:
    matched = [
        item
        for item in command
        if "LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH=" in item
    ]
    assert len(matched) == 1
    path = Path(matched[0].split("=", 1)[1]).resolve()
    assert path.exists(), path
    assert str(path).startswith(str(expected_root)), path
PY

echo "ok"
