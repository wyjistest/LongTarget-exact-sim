#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_predictor/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 v2 frontier predictor report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
by_key = {(row.get("workload"), row.get("predictor")): row for row in rows}
summary = by_key.get(("summary", "best_pre_align_frontier_fields"))
if summary is None:
    raise SystemExit("missing predictor summary row")
if summary.get("decision") != "phase7_frontier_predictor_no_go_current_features":
    raise SystemExit(f"unexpected summary decision: {summary.get('decision')}")
if summary.get("predictor_gate_pass") != "0":
    raise SystemExit("predictor gate must not pass")

first64_oracle = by_key.get(("neat1_first64", "oracle_selected"))
if first64_oracle is None:
    raise SystemExit("missing neat1_first64 oracle row")
if first64_oracle.get("feature_scope") != "oracle_post_align":
    raise SystemExit("first64 oracle must be post-Align")
if first64_oracle.get("false_negative_selected_rows") != "0":
    raise SystemExit("first64 oracle must have zero false negatives")
if first64_oracle.get("align_attempt_reduction") != "158982":
    raise SystemExit("unexpected first64 oracle reduction")
if first64_oracle.get("predictor_gate_pass") != "0":
    raise SystemExit("oracle cannot pass predictor gate")

first64_keep_all = by_key.get(("neat1_first64", "keep_all"))
if first64_keep_all is None:
    raise SystemExit("missing neat1_first64 keep_all row")
if first64_keep_all.get("false_negative_selected_rows") != "0":
    raise SystemExit("keep_all must have zero false negatives")
if first64_keep_all.get("align_attempt_reduction") != "0":
    raise SystemExit("keep_all must not reduce attempts")

prealign_first64 = [
    row for row in rows
    if row.get("workload") == "neat1_first64"
    and row.get("feature_scope") == "pre_align_frontier_fields"
]
if not prealign_first64:
    raise SystemExit("missing first64 pre-align predictor rows")
if not any(
    int(row.get("false_negative_selected_rows", "0")) > 0
    and int(row.get("align_attempt_reduction", "0")) > 0
    for row in prealign_first64
):
    raise SystemExit("expected reducing first64 pre-align rows with false negatives")
if any(
    int(row.get("false_negative_selected_rows", "0")) == 0
    and int(row.get("align_attempt_reduction", "0")) > 0
    for row in prealign_first64
):
    raise SystemExit("unexpected reducing zero-FN first64 pre-align predictor")

print("phase7_broad_restart_v2_frontier_predictor=no_go_current_features")
print("phase7_frontier_predictor_first64_oracle_reduction=158982")
print("phase7_frontier_predictor_first64_selected_rank_set=" + first64_oracle["selected_rank_set"])
print("phase7_frontier_predictor_first64_group_size_set=" + first64_oracle["group_size_set"])
print("phase7_frontier_predictor_gate_pass=0")
print("next_gate = new pre-Align signal or measured runtime reducer design")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
