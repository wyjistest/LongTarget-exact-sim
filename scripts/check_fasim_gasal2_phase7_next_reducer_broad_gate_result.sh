#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_next_reducer_broad_gate/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 next reducer broad-gate report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
if len(rows) < 2:
    raise SystemExit(f"expected at least first1 and first64 rows, got {len(rows)}")

required = [
    "workload",
    "record_limit",
    "attempted",
    "digest_match",
    "full_rows_equal",
    "baseline_only_rows",
    "candidate_only_rows",
    "top5_score_equal",
    "top5_stability_equal",
    "top5_nt_score_equal",
    "false_negative_scoreinfos",
    "triplex_mismatches",
    "candidate_align_attempts",
    "reference_align_attempts",
    "align_attempt_reduction",
    "candidate_vs_baseline",
    "decision",
    "decision_reasons",
]
for row in rows:
    missing = [key for key in required if key not in row]
    if missing:
        raise SystemExit(f"{row.get('workload', '<unknown>')}: missing columns {missing}")

by_workload = {row["workload"]: row for row in rows}
if "neat1_first1" not in by_workload:
    raise SystemExit("missing neat1_first1 row")
if "neat1_first64" not in by_workload:
    raise SystemExit("missing neat1_first64 row")

first1 = by_workload["neat1_first1"]
if first1["attempted"] != "1":
    raise SystemExit("neat1_first1 must be attempted")
if first1["decision"] not in {
    "phase7_next_reducer_broad_gate_go",
    "phase7_next_reducer_broad_gate_correctness_no_go",
    "phase7_next_reducer_broad_gate_no_reduction_no_go",
    "phase7_next_reducer_broad_gate_performance_no_go",
}:
    raise SystemExit(f"unexpected neat1_first1 decision: {first1['decision']}")

candidate_align = int(first1["candidate_align_attempts"])
reference_align = int(first1["reference_align_attempts"])
if candidate_align <= 0 or reference_align <= 0:
    raise SystemExit("neat1_first1 must report positive align attempts")
if candidate_align >= reference_align and first1["decision"] == "phase7_next_reducer_broad_gate_go":
    raise SystemExit("go row cannot have candidate_align >= reference_align")
if int(first1["false_negative_scoreinfos"]) != 0:
    raise SystemExit("neat1_first1 must keep false_negative_scoreinfos=0 for this gate")

first64 = by_workload["neat1_first64"]
if first64["attempted"] == "0":
    if first1["decision"] == "phase7_next_reducer_broad_gate_go":
        raise SystemExit("neat1_first64 cannot be skipped after a first1 go")
    if not first64["decision"].startswith("phase7_next_reducer_broad_gate_skipped_"):
        raise SystemExit(f"unexpected skipped first64 decision: {first64['decision']}")
else:
    if first64["decision"] == "phase7_next_reducer_broad_gate_go":
        if first64["digest_match"] != "1" and first64["full_rows_equal"] != "1":
            raise SystemExit("first64 go requires digest or row equality")
        if int(first64["candidate_align_attempts"]) >= int(first64["reference_align_attempts"]):
            raise SystemExit("first64 go requires align attempt reduction")
        if float(first64["candidate_vs_baseline"]) <= 1.0:
            raise SystemExit("first64 go requires speedup > 1")

print("phase7_next_reducer_broad_gate_result=pass")
print("phase7_next_reducer_first1_decision=" + first1["decision"])
print("phase7_next_reducer_first1_digest_match=" + first1["digest_match"])
print("phase7_next_reducer_first1_full_rows_equal=" + first1["full_rows_equal"])
print("phase7_next_reducer_first1_baseline_only_rows=" + first1["baseline_only_rows"])
print("phase7_next_reducer_first1_candidate_only_rows=" + first1["candidate_only_rows"])
print("phase7_next_reducer_first1_candidate_align_attempts=" + first1["candidate_align_attempts"])
print("phase7_next_reducer_first1_reference_align_attempts=" + first1["reference_align_attempts"])
print("phase7_next_reducer_first1_decision_reasons=" + first1["decision_reasons"])
print("phase7_next_reducer_first64_attempted=" + first64["attempted"])
print("phase7_next_reducer_first64_decision=" + first64["decision"])
print("ok")
PY
