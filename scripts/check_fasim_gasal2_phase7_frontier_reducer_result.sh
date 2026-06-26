#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_reducer/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 frontier reducer report: $REPORT" >&2
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
    "record_limit",
    "attempted",
    "digest_match",
    "full_rows_equal",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "false_negative_scoreinfos",
    "candidate_align_attempts",
    "reference_align_attempts",
    "align_attempt_reduction",
    "frontier_log_rows",
    "frontier_selected_rows",
    "selected_rows",
    "candidate_wall_seconds",
    "baseline_wall_seconds",
    "candidate_vs_baseline",
    "wall_time_basis",
    "broad_gate_pass",
    "decision",
]

by_workload: dict[str, dict[str, str]] = {}
for row in rows:
    missing = [key for key in required if key not in row]
    if missing:
        raise SystemExit(f"{row.get('workload', '<unknown>')}: missing columns {missing}")
    workload = row["workload"]
    if workload not in {"neat1_first1", "neat1_first64"}:
        raise SystemExit(f"unexpected workload {workload}")
    by_workload[workload] = row

for workload in ["neat1_first1", "neat1_first64"]:
    if workload not in by_workload:
        raise SystemExit(f"missing {workload} row")
    row = by_workload[workload]
    if row["attempted"] != "1":
        raise SystemExit(f"{workload}: reducer proof must be attempted")
    if int(row["missing_rows"]) != 0:
        raise SystemExit(f"{workload}: missing_rows != 0")
    if int(row["extra_rows"]) != 0:
        raise SystemExit(f"{workload}: extra_rows != 0")
    if int(row["triplex_mismatches"]) != 0:
        raise SystemExit(f"{workload}: triplex_mismatches != 0")
    if int(row["false_negative_scoreinfos"]) != 0:
        raise SystemExit(f"{workload}: false_negative_scoreinfos != 0")
    if int(row["digest_match"]) != 1 and int(row["full_rows_equal"]) != 1:
        raise SystemExit(f"{workload}: reducer output not equal")
    candidate_attempts = int(row["candidate_align_attempts"])
    reference_attempts = int(row["reference_align_attempts"])
    if candidate_attempts >= reference_attempts:
        raise SystemExit(f"{workload}: reducer did not reduce Align attempts")
    if int(row["align_attempt_reduction"]) != reference_attempts - candidate_attempts:
        raise SystemExit(f"{workload}: align_attempt_reduction mismatch")
    if int(row["frontier_log_rows"]) <= 0:
        raise SystemExit(f"{workload}: frontier log must contain rows")
    if int(row["frontier_selected_rows"]) <= 0:
        raise SystemExit(f"{workload}: frontier log must contain selected rows")
    if int(row["selected_rows"]) != int(row["frontier_selected_rows"]):
        raise SystemExit(f"{workload}: selected_rows must match frontier_selected_rows")
    if row["decision"] not in {
        "phase7_frontier_reducer_exact_reduction",
        "phase7_frontier_reducer_exact_reduction_projected",
    }:
        raise SystemExit(f"{workload}: unexpected decision {row['decision']}")

first64 = by_workload["neat1_first64"]
if first64["decision"] == "phase7_frontier_reducer_exact_reduction":
    if first64["wall_time_basis"] != "measured":
        raise SystemExit("neat1_first64: exact reduction requires measured wall time")
    if first64["broad_gate_pass"] != "1":
        raise SystemExit("neat1_first64: measured exact reduction must pass broad gate")
    if float(first64["candidate_wall_seconds"]) <= 0.0:
        raise SystemExit("neat1_first64: candidate wall must be measured")
    if float(first64["baseline_wall_seconds"]) <= 0.0:
        raise SystemExit("neat1_first64: baseline wall must be measured")
    if float(first64["candidate_vs_baseline"]) <= 1.0:
        raise SystemExit("neat1_first64: candidate_vs_baseline must be > 1.0")
else:
    if first64["wall_time_basis"] != "oracle_projected":
        raise SystemExit("neat1_first64: projected reduction must be labelled oracle_projected")
    if first64["broad_gate_pass"] != "0":
        raise SystemExit("neat1_first64: projected reduction cannot pass broad gate")

print("phase7_frontier_reducer_result=pass")
print("phase7_frontier_reducer_first1_decision=" + by_workload["neat1_first1"]["decision"])
print("phase7_frontier_reducer_first64_decision=" + by_workload["neat1_first64"]["decision"])
print("phase7_frontier_reducer_first64_broad_gate_pass=" + first64["broad_gate_pass"])
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
