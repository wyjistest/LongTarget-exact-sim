#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_replay/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing frontier replay report: $REPORT" >&2
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
    "frontier_log_rows",
    "frontier_selected_rows",
    "frontier_positive_align_rows",
    "frontier_log_path",
    "decision",
]

by_workload = {}
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
        raise SystemExit(f"{workload}: replay proof must be attempted")
    if int(row["missing_rows"]) != 0:
        raise SystemExit(f"{workload}: missing_rows != 0")
    if int(row["extra_rows"]) != 0:
        raise SystemExit(f"{workload}: extra_rows != 0")
    if int(row["triplex_mismatches"]) != 0:
        raise SystemExit(f"{workload}: triplex_mismatches != 0")
    if int(row["false_negative_scoreinfos"]) != 0:
        raise SystemExit(f"{workload}: false_negative_scoreinfos != 0")
    if int(row["digest_match"]) != 1 and int(row["full_rows_equal"]) != 1:
        raise SystemExit(f"{workload}: replay output not equal")
    if int(row["candidate_align_attempts"]) != int(row["reference_align_attempts"]):
        raise SystemExit(f"{workload}: replay proof must not reduce Align attempts")
    if int(row["frontier_log_rows"]) <= 0:
        raise SystemExit(f"{workload}: frontier log must contain rows")
    if int(row["frontier_selected_rows"]) <= 0:
        raise SystemExit(f"{workload}: frontier log must contain selected rows")
    if int(row["frontier_positive_align_rows"]) <= 0:
        raise SystemExit(f"{workload}: frontier log must contain positive Align rows")
    if not row["frontier_log_path"]:
        raise SystemExit(f"{workload}: frontier log path is empty")
    if row["decision"] != "phase7_frontier_replay_exact":
        raise SystemExit(f"{workload}: unexpected decision {row['decision']}")

print("phase7_frontier_replay_result=pass")
print("phase7_frontier_replay_first1_decision=" + by_workload["neat1_first1"]["decision"])
print("phase7_frontier_replay_first64_decision=" + by_workload["neat1_first64"]["decision"])
print("ok")
PY
