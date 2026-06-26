#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_gate_c_first1/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Gate C first1 report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
row = next((r for r in rows if r.get("workload") == "neat1_first1"), None)
if row is None:
    raise SystemExit("missing neat1_first1 row")

required = [
    "attempted",
    "digest_match",
    "full_rows_equal",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "false_negative_scoreinfos",
    "candidate_align_attempts",
    "gate_b_candidate_align_attempts",
    "scoreinfo_reduced",
    "oracle_scoreinfos",
    "oracle_attempts",
    "gpu_candidate_scoreinfos",
    "gpu_candidate_attempts",
    "missing_required_attempts",
    "extra_candidate_attempts",
    "gate_c_requested",
    "gate_c_active",
    "decision",
    "decision_reasons",
]
missing = [key for key in required if key not in row]
if missing:
    raise SystemExit("missing columns: " + ",".join(missing))

if row["attempted"] != "1":
    raise SystemExit("first1 was not attempted")
if row["gate_c_requested"] != "1":
    raise SystemExit("Gate C was not requested")

allowed = {
    "phase7_gate_c_first1_go",
    "phase7_gate_c_first1_no_go",
}
if row["decision"] not in allowed:
    raise SystemExit("unexpected decision: " + row["decision"])

candidate = int(row["candidate_align_attempts"])
gate_b = int(row["gate_b_candidate_align_attempts"])
if candidate < 0 or gate_b <= 0:
    raise SystemExit("invalid candidate or Gate B attempt counts")

if row["decision"] == "phase7_gate_c_first1_go":
    if row["digest_match"] != "1" and row["full_rows_equal"] != "1":
        raise SystemExit("go requires digest or row equality")
    for key in [
        "missing_rows",
        "extra_rows",
        "triplex_mismatches",
        "false_negative_scoreinfos",
        "missing_required_attempts",
    ]:
        if row[key] != "0":
            raise SystemExit(f"go requires {key}=0")
    if candidate > gate_b:
        raise SystemExit("go requires candidate attempts <= Gate B")
    if row["scoreinfo_reduced"] != "1":
        raise SystemExit("go requires scoreInfo/preAlign reduction")
    if int(row["gpu_candidate_attempts"]) <= 0:
        raise SystemExit("go requires GPU candidate descriptors")

print("phase7_gate_c_first1_result=pass")
print("phase7_gate_c_first1_decision=" + row["decision"])
print("phase7_gate_c_first1_digest_match=" + row["digest_match"])
print("phase7_gate_c_first1_full_rows_equal=" + row["full_rows_equal"])
print("phase7_gate_c_first1_candidate_align_attempts=" + row["candidate_align_attempts"])
print("phase7_gate_c_first1_gate_b_candidate_align_attempts=" + row["gate_b_candidate_align_attempts"])
print("phase7_gate_c_first1_scoreinfo_reduced=" + row["scoreinfo_reduced"])
print("phase7_gate_c_first1_gpu_candidate_attempts=" + row["gpu_candidate_attempts"])
print("phase7_gate_c_first1_broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
