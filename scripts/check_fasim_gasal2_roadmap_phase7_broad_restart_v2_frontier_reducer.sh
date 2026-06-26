#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_reducer/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 v2 frontier reducer report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
by_workload = {row.get("workload"): row for row in rows}
first1 = by_workload.get("neat1_first1")
first64 = by_workload.get("neat1_first64")
if first1 is None or first64 is None:
    raise SystemExit("expected neat1_first1 and neat1_first64 reducer rows")

for label, row in [("first1", first1), ("first64", first64)]:
    if row.get("decision") != "phase7_frontier_reducer_exact_reduction_projected":
        raise SystemExit(f"{label}: expected projected exact reduction")
    if row.get("wall_time_basis") != "oracle_projected":
        raise SystemExit(f"{label}: expected oracle_projected wall basis")
    if row.get("broad_gate_pass") != "0":
        raise SystemExit(f"{label}: projected reducer must not pass broad gate")
    if row.get("digest_match") != "1" and row.get("full_rows_equal") != "1":
        raise SystemExit(f"{label}: reducer projection must preserve replay equality")
    if int(row.get("candidate_align_attempts", "0")) >= int(row.get("reference_align_attempts", "0")):
        raise SystemExit(f"{label}: expected projected Align attempt reduction")
    reasons = set(row.get("decision_reasons", "").split(","))
    for reason in [
        "oracle_selected_rows_require_future_predictor",
        "no_measured_runtime_reducer",
    ]:
        if reason not in reasons:
            raise SystemExit(f"{label}: missing decision reason {reason}")

print("phase7_broad_restart_v2_frontier_reducer=oracle_reduction_projected_not_broad")
print("phase7_frontier_reducer_first1_candidate_align_attempts=" + first1["candidate_align_attempts"])
print("phase7_frontier_reducer_first1_reference_align_attempts=" + first1["reference_align_attempts"])
print("phase7_frontier_reducer_first64_candidate_align_attempts=" + first64["candidate_align_attempts"])
print("phase7_frontier_reducer_first64_reference_align_attempts=" + first64["reference_align_attempts"])
print("phase7_frontier_reducer_broad_gate_pass=0")
print("next_gate = measured runtime reducer or predictor")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
