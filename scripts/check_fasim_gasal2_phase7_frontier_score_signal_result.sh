#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_score_signal/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 frontier score-signal report: $REPORT" >&2
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
    "signal",
    "feature_scope",
    "reference_attempts",
    "kept_attempts",
    "selected_rows",
    "false_negative_selected_rows",
    "align_attempt_reduction",
    "reduction_fraction",
    "signal_gate_pass",
    "decision",
]
for row in rows:
    missing = [key for key in required if key not in row]
    if missing:
        raise SystemExit(f"{row.get('workload', '<unknown>')}/{row.get('signal', '<unknown>')}: missing columns {missing}")

by_key = {(row["workload"], row["signal"]): row for row in rows}
summary = by_key.get(("summary", "best_post_align_score_signal"))
if summary is None:
    raise SystemExit("missing summary row")
if summary["decision"] != "phase7_frontier_score_signal_no_go":
    raise SystemExit(f"unexpected summary decision: {summary['decision']}")
if summary["signal_gate_pass"] != "0":
    raise SystemExit("summary signal gate must not pass")

first64_oracle = by_key.get(("neat1_first64", "oracle_selected"))
if first64_oracle is None:
    raise SystemExit("missing neat1_first64 oracle row")
if first64_oracle["feature_scope"] != "oracle_post_align_selected":
    raise SystemExit("oracle row must be marked oracle_post_align_selected")
if int(first64_oracle["false_negative_selected_rows"]) != 0:
    raise SystemExit("oracle must have zero false negatives")
if int(first64_oracle["align_attempt_reduction"]) != 158982:
    raise SystemExit("unexpected oracle reduction")
if first64_oracle["signal_gate_pass"] != "0":
    raise SystemExit("oracle selected cannot pass score-signal gate")

first64_score_top3 = by_key.get(("neat1_first64", "align_sw_score_desc_top_3"))
if first64_score_top3 is None:
    raise SystemExit("missing neat1_first64 align_sw_score_desc_top_3 row")
if int(first64_score_top3["align_attempt_reduction"]) <= 0:
    raise SystemExit("score top3 should reduce attempts")
if int(first64_score_top3["false_negative_selected_rows"]) != 14670:
    raise SystemExit("unexpected score top3 false negative count")
if first64_score_top3["signal_gate_pass"] != "0":
    raise SystemExit("score top3 cannot pass signal gate")

first64_score_threshold = by_key.get(("neat1_first64", "align_sw_score_ge_best_zero_fn"))
if first64_score_threshold is None:
    raise SystemExit("missing neat1_first64 align_sw_score_ge_best_zero_fn row")
if int(first64_score_threshold["false_negative_selected_rows"]) != 0:
    raise SystemExit("best zero-FN threshold must have zero false negatives")
if int(first64_score_threshold["align_attempt_reduction"]) != 0:
    raise SystemExit("best zero-FN threshold must not reduce attempts")
if first64_score_threshold["signal_gate_pass"] != "0":
    raise SystemExit("best zero-FN threshold cannot pass without reduction")

post_align_rows = [
    row for row in rows
    if row["workload"] == "neat1_first64"
    and row["feature_scope"] == "post_align_score_or_endpoint"
]
if not post_align_rows:
    raise SystemExit("missing post-align signal rows")
if any(
    int(row["false_negative_selected_rows"]) == 0
    and int(row["align_attempt_reduction"]) > 0
    for row in post_align_rows
):
    raise SystemExit("unexpected reducing zero-FN post-align score/endpoint signal")

print("phase7_frontier_score_signal_result=pass")
print("phase7_frontier_score_signal_decision=" + summary["decision"])
print("phase7_frontier_score_signal_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
