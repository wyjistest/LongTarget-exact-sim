#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_early_stop/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 v2 frontier early-stop report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
by_workload = {row.get("workload"): row for row in rows}
first64 = by_workload.get("neat1_first64")
if first64 is None:
    raise SystemExit("missing neat1_first64 early-stop row")

required = {
    "reference_attempts": "211976",
    "candidate_align_attempts": "103953",
    "align_attempt_reduction": "108023",
    "selected_rows": "52994",
    "multi_selected_groups": "0",
    "no_selected_groups": "0",
    "skipped_after_selected_rows": "108023",
    "unsafe_skipped_rows": "0",
    "false_negative_selected_rows": "0",
    "selected_rank_counts": "0:33615,1:2469,2:2240,3:14670",
    "runtime_candidate": "1",
    "measured_runtime": "0",
    "broad_gate_pass": "0",
    "decision": "phase7_frontier_early_stop_candidate_not_measured",
}
for key, expected in required.items():
    if first64.get(key) != expected:
        raise SystemExit(f"neat1_first64 {key}: expected {expected}, got {first64.get(key)}")

print("phase7_broad_restart_v2_frontier_early_stop=candidate_not_measured")
print("phase7_frontier_early_stop_first64_candidate_align_attempts=103953")
print("phase7_frontier_early_stop_first64_reference_align_attempts=211976")
print("phase7_frontier_early_stop_first64_align_attempt_reduction=108023")
print("phase7_frontier_early_stop_first64_unsafe_skipped_rows=0")
print("phase7_frontier_early_stop_broad_gate_pass=0")
print("next_gate = measured runtime early-stop reducer")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
