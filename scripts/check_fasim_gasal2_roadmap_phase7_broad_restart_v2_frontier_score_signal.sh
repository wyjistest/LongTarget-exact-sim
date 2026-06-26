#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_score_signal/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 v2 frontier score-signal report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
by_key = {(row.get("workload"), row.get("signal")): row for row in rows}

summary = by_key.get(("summary", "best_post_align_score_signal"))
if summary is None:
    raise SystemExit("missing score-signal summary row")
if summary.get("decision") != "phase7_frontier_score_signal_no_go":
    raise SystemExit(f"unexpected summary decision: {summary.get('decision')}")
if summary.get("signal_gate_pass") != "0":
    raise SystemExit("score-signal gate must not pass")

oracle = by_key.get(("neat1_first64", "oracle_selected"))
if oracle is None:
    raise SystemExit("missing first64 oracle row")
if oracle.get("feature_scope") != "oracle_post_align_selected":
    raise SystemExit("oracle row must be marked oracle_post_align_selected")
if oracle.get("align_attempt_reduction") != "158982":
    raise SystemExit("unexpected first64 oracle reduction")
if oracle.get("signal_gate_pass") != "0":
    raise SystemExit("oracle selected cannot pass score-signal gate")

score_top3 = by_key.get(("neat1_first64", "align_sw_score_desc_top_3"))
if score_top3 is None:
    raise SystemExit("missing first64 align_sw_score_desc_top_3 row")
if score_top3.get("false_negative_selected_rows") != "14670":
    raise SystemExit("unexpected align_sw_score_desc_top_3 false negatives")
if score_top3.get("align_attempt_reduction") != "52994":
    raise SystemExit("unexpected align_sw_score_desc_top_3 reduction")

threshold = by_key.get(("neat1_first64", "align_sw_score_ge_best_zero_fn"))
if threshold is None:
    raise SystemExit("missing first64 align_sw_score_ge_best_zero_fn row")
if threshold.get("false_negative_selected_rows") != "0":
    raise SystemExit("best zero-FN score threshold must have zero false negatives")
if threshold.get("align_attempt_reduction") != "0":
    raise SystemExit("best zero-FN score threshold must not reduce attempts")

post_align_rows = [
    row for row in rows
    if row.get("workload") == "neat1_first64"
    and row.get("feature_scope") == "post_align_score_or_endpoint"
]
if not post_align_rows:
    raise SystemExit("missing first64 post-align rows")
if any(
    int(row.get("false_negative_selected_rows", "0")) == 0
    and int(row.get("align_attempt_reduction", "0")) > 0
    for row in post_align_rows
):
    raise SystemExit("unexpected reducing zero-FN post-align score/end signal")

print("phase7_broad_restart_v2_frontier_score_signal=no_go")
print("phase7_frontier_score_signal_first64_oracle_reduction=158982")
print("phase7_frontier_score_signal_first64_score_top3_false_negatives=14670")
print("phase7_frontier_score_signal_first64_score_threshold_reduction=0")
print("phase7_frontier_score_signal_gate_pass=0")
print("next_gate = new non-score signal or measured runtime reducer design")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
