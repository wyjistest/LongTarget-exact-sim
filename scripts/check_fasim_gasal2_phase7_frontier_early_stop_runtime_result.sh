#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_early_stop_runtime/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 early-stop runtime report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
by_workload = {row.get("workload"): row for row in rows}
row = by_workload.get("neat1_first1")
if row is None:
    raise SystemExit("missing neat1_first1 early-stop runtime row")

required_columns = [
    "digest_match",
    "full_rows_equal",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "candidate_align_attempts",
    "reference_align_attempts",
    "align_attempt_reduction",
    "early_stop_requested",
    "early_stop_active",
    "early_stop_skipped_attempts",
    "decision",
]
missing = [key for key in required_columns if key not in row]
if missing:
    raise SystemExit("missing columns: " + ",".join(missing))

if row["attempted"] != "1":
    raise SystemExit("neat1_first1 was not attempted")
if row["early_stop_requested"] != "1":
    raise SystemExit("early-stop was not requested")
if row["early_stop_active"] != "1":
    raise SystemExit("early-stop was not active")

candidate = int(row["candidate_align_attempts"])
reference = int(row["reference_align_attempts"])
reduction = int(row["align_attempt_reduction"])
skipped = int(row["early_stop_skipped_attempts"])
if reference <= 0 or candidate <= 0:
    raise SystemExit("expected positive align attempt counts")
if candidate >= reference:
    raise SystemExit(f"expected align reduction, got {candidate}/{reference}")
if reduction != reference - candidate:
    raise SystemExit("align_attempt_reduction does not match reference-candidate")
if skipped != reduction:
    raise SystemExit("early_stop_skipped_attempts does not match reduction")

allowed = {
    "phase7_frontier_early_stop_runtime_first1_go",
    "phase7_frontier_early_stop_runtime_first1_no_go",
}
if row["decision"] not in allowed:
    raise SystemExit("unexpected decision: " + row["decision"])

if row["decision"] == "phase7_frontier_early_stop_runtime_first1_go":
    if row["digest_match"] != "1" and row["full_rows_equal"] != "1":
        raise SystemExit("go decision requires digest or row equality")
    if row["missing_rows"] != "0" or row["extra_rows"] != "0":
        raise SystemExit("go decision requires no row diff")
    if row["triplex_mismatches"] != "0":
        raise SystemExit("go decision requires no triplex mismatches")

print("phase7_frontier_early_stop_runtime_result=pass")
print("phase7_frontier_early_stop_runtime_first1_decision=" + row["decision"])
print("phase7_frontier_early_stop_runtime_first1_digest_match=" + row["digest_match"])
print("phase7_frontier_early_stop_runtime_first1_full_rows_equal=" + row["full_rows_equal"])
print("phase7_frontier_early_stop_runtime_first1_candidate_align_attempts=" + row["candidate_align_attempts"])
print("phase7_frontier_early_stop_runtime_first1_reference_align_attempts=" + row["reference_align_attempts"])
print("phase7_frontier_early_stop_runtime_first1_align_attempt_reduction=" + row["align_attempt_reduction"])
print("phase7_frontier_early_stop_runtime_first1_broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
