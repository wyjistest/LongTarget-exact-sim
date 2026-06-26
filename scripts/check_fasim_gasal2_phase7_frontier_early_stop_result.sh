#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_early_stop/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 frontier early-stop report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if not rows:
    raise SystemExit("empty report")

required = [
    "workload",
    "groups",
    "reference_attempts",
    "candidate_align_attempts",
    "align_attempt_reduction",
    "reduction_fraction",
    "selected_rows",
    "multi_selected_groups",
    "no_selected_groups",
    "skipped_after_selected_rows",
    "unsafe_skipped_rows",
    "false_negative_selected_rows",
    "selected_rank_counts",
    "runtime_candidate",
    "measured_runtime",
    "broad_gate_pass",
    "decision",
]
for row in rows:
    missing = [key for key in required if key not in row]
    if missing:
        raise SystemExit(f"{row.get('workload', '<unknown>')}: missing columns {missing}")

by_workload = {row["workload"]: row for row in rows}
for workload in ["neat1_first1", "neat1_first64"]:
    if workload not in by_workload:
        raise SystemExit(f"missing {workload} row")
    row = by_workload[workload]
    if int(row["groups"]) <= 0:
        raise SystemExit(f"{workload}: expected groups")
    if int(row["reference_attempts"]) <= 0:
        raise SystemExit(f"{workload}: expected reference attempts")
    if int(row["candidate_align_attempts"]) <= 0:
        raise SystemExit(f"{workload}: expected candidate attempts")
    if int(row["candidate_align_attempts"]) >= int(row["reference_attempts"]):
        raise SystemExit(f"{workload}: expected Align attempt reduction")
    if int(row["align_attempt_reduction"]) != int(row["reference_attempts"]) - int(row["candidate_align_attempts"]):
        raise SystemExit(f"{workload}: reduction mismatch")
    if int(row["selected_rows"]) != int(row["groups"]):
        raise SystemExit(f"{workload}: expected one selected row per group")
    if int(row["multi_selected_groups"]) != 0:
        raise SystemExit(f"{workload}: multi-selected groups must be zero")
    if int(row["no_selected_groups"]) != 0:
        raise SystemExit(f"{workload}: no-selected groups must be zero")
    if int(row["skipped_after_selected_rows"]) != int(row["align_attempt_reduction"]):
        raise SystemExit(f"{workload}: skipped rows must match reduction")
    if int(row["unsafe_skipped_rows"]) != 0:
        raise SystemExit(f"{workload}: unsafe skipped rows must be zero")
    if int(row["false_negative_selected_rows"]) != 0:
        raise SystemExit(f"{workload}: false-negative selected rows must be zero")
    if row["runtime_candidate"] != "1":
        raise SystemExit(f"{workload}: expected runtime_candidate=1")
    if row["measured_runtime"] != "0":
        raise SystemExit(f"{workload}: this checkpoint must remain unmeasured")
    if row["broad_gate_pass"] != "0":
        raise SystemExit(f"{workload}: unmeasured checkpoint cannot pass broad gate")
    if row["decision"] != "phase7_frontier_early_stop_candidate_not_measured":
        raise SystemExit(f"{workload}: unexpected decision {row['decision']}")

first64 = by_workload["neat1_first64"]
if first64["candidate_align_attempts"] != "103953":
    raise SystemExit("neat1_first64: unexpected candidate attempt count")
if first64["align_attempt_reduction"] != "108023":
    raise SystemExit("neat1_first64: unexpected reduction count")
if first64["selected_rank_counts"] != "0:33615,1:2469,2:2240,3:14670":
    raise SystemExit("neat1_first64: unexpected selected rank counts")

print("phase7_frontier_early_stop_result=pass")
print("phase7_frontier_early_stop_first64_candidate_align_attempts=" + first64["candidate_align_attempts"])
print("phase7_frontier_early_stop_first64_reference_align_attempts=" + first64["reference_attempts"])
print("phase7_frontier_early_stop_first64_align_attempt_reduction=" + first64["align_attempt_reduction"])
print("phase7_frontier_early_stop_broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
