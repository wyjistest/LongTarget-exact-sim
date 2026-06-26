#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_predictor/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 frontier predictor report: $REPORT" >&2
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
    "predictor",
    "feature_scope",
    "reference_attempts",
    "kept_attempts",
    "selected_rows",
    "false_negative_selected_rows",
    "align_attempt_reduction",
    "reduction_fraction",
    "predictor_gate_pass",
    "decision",
]
for row in rows:
    missing = [key for key in required if key not in row]
    if missing:
        raise SystemExit(f"{row.get('workload', '<unknown>')}/{row.get('predictor', '<unknown>')}: missing columns {missing}")

for workload in ["neat1_first1", "neat1_first64"]:
    workload_rows = [row for row in rows if row["workload"] == workload]
    if not workload_rows:
        raise SystemExit(f"missing {workload} rows")

    oracle = [row for row in workload_rows if row["predictor"] == "oracle_selected"]
    if len(oracle) != 1:
        raise SystemExit(f"{workload}: expected one oracle_selected row")
    oracle_row = oracle[0]
    if oracle_row["feature_scope"] != "oracle_post_align":
        raise SystemExit(f"{workload}: oracle row must be marked oracle_post_align")
    if int(oracle_row["false_negative_selected_rows"]) != 0:
        raise SystemExit(f"{workload}: oracle must have zero false negatives")
    if int(oracle_row["kept_attempts"]) >= int(oracle_row["reference_attempts"]):
        raise SystemExit(f"{workload}: oracle must reduce attempts")
    if oracle_row["predictor_gate_pass"] != "0":
        raise SystemExit(f"{workload}: oracle cannot pass predictor gate")

    keep_all = [row for row in workload_rows if row["predictor"] == "keep_all"]
    if len(keep_all) != 1:
        raise SystemExit(f"{workload}: expected one keep_all row")
    keep_all_row = keep_all[0]
    if int(keep_all_row["false_negative_selected_rows"]) != 0:
        raise SystemExit(f"{workload}: keep_all must have zero false negatives")
    if int(keep_all_row["align_attempt_reduction"]) != 0:
        raise SystemExit(f"{workload}: keep_all cannot reduce attempts")

    prealign_rows = [row for row in workload_rows if row["feature_scope"] == "pre_align_frontier_fields"]
    if not prealign_rows:
        raise SystemExit(f"{workload}: missing pre-align predictor rows")
    passing = [
        row for row in prealign_rows
        if int(row["false_negative_selected_rows"]) == 0
        and int(row["align_attempt_reduction"]) > 0
        and row["predictor_gate_pass"] == "1"
    ]
    if passing:
        names = ", ".join(row["predictor"] for row in passing)
        raise SystemExit(f"{workload}: unexpected passing pre-align predictor(s): {names}")

    reducing_zero_fn = [
        row for row in prealign_rows
        if int(row["false_negative_selected_rows"]) == 0
        and int(row["align_attempt_reduction"]) > 0
    ]
    if reducing_zero_fn:
        names = ", ".join(row["predictor"] for row in reducing_zero_fn)
        raise SystemExit(f"{workload}: reducing zero-FN pre-align predictors must not exist: {names}")

    if not any(int(row["false_negative_selected_rows"]) > 0 and int(row["align_attempt_reduction"]) > 0 for row in prealign_rows):
        raise SystemExit(f"{workload}: expected at least one reducing pre-align predictor with false negatives")

summary_rows = [row for row in rows if row["workload"] == "summary"]
if len(summary_rows) != 1:
    raise SystemExit("expected one summary row")
summary = summary_rows[0]
if summary["decision"] != "phase7_frontier_predictor_no_go_current_features":
    raise SystemExit(f"unexpected summary decision: {summary['decision']}")
if summary["predictor_gate_pass"] != "0":
    raise SystemExit("summary predictor gate must not pass")

print("phase7_frontier_predictor_result=pass")
print("phase7_frontier_predictor_decision=" + summary["decision"])
print("phase7_frontier_predictor_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
