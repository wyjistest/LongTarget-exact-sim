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
by_workload = {row.get("workload"): row for row in rows}
first1 = by_workload.get("neat1_first1")
first64 = by_workload.get("neat1_first64")
if first1 is None or first64 is None:
    raise SystemExit("expected neat1_first1 and neat1_first64 rows")

if first1.get("attempted") != "1":
    raise SystemExit("neat1_first1 must be attempted")
if first1.get("decision") != "phase7_next_reducer_broad_gate_correctness_no_go":
    raise SystemExit(f"expected first1 correctness no-go, got {first1.get('decision')}")
if first1.get("digest_match") != "0" or first1.get("full_rows_equal") != "0":
    raise SystemExit("first1 no-go must record output inequality")
if int(first1.get("baseline_only_rows", "0")) <= 0:
    raise SystemExit("first1 no-go must record baseline-only rows")
if int(first1.get("candidate_only_rows", "0")) <= 0:
    raise SystemExit("first1 no-go must record candidate-only rows")
if first1.get("false_negative_scoreinfos") != "0":
    raise SystemExit("first1 should not have scoreInfo false negatives in this result")
if first1.get("triplex_mismatches") != "0":
    raise SystemExit("first1 should not have recorded triplex mismatches in this result")
candidate = int(first1.get("candidate_align_attempts", "0"))
reference = int(first1.get("reference_align_attempts", "0"))
if candidate <= 0 or reference <= 0 or candidate >= reference:
    raise SystemExit("first1 should show bounded align-attempt reduction before correctness stop")
reasons = set(first1.get("decision_reasons", "").split(","))
required_reasons = {
    "output_rows_differ",
    "top5_score_differs",
    "top5_stability_differs",
    "top5_nt_score_differs",
}
if not required_reasons.issubset(reasons):
    raise SystemExit(f"missing required no-go reasons: {required_reasons - reasons}")
if first64.get("attempted") != "0":
    raise SystemExit("first64 should be skipped after first1 correctness no-go")
if first64.get("decision") != "phase7_next_reducer_broad_gate_skipped_first1_no_go":
    raise SystemExit(f"unexpected first64 decision: {first64.get('decision')}")

print("phase7_next_reducer_broad_gate=correctness_no_go")
print("phase7_next_reducer_broad_first1_attempted=1")
print("phase7_next_reducer_broad_first1_decision=phase7_next_reducer_broad_gate_correctness_no_go")
print("phase7_next_reducer_broad_first1_digest_match=0")
print("phase7_next_reducer_broad_first1_full_rows_equal=0")
print("phase7_next_reducer_broad_first1_baseline_only_rows=" + first1["baseline_only_rows"])
print("phase7_next_reducer_broad_first1_candidate_only_rows=" + first1["candidate_only_rows"])
print("phase7_next_reducer_broad_first1_candidate_align_attempts=" + str(candidate))
print("phase7_next_reducer_broad_first1_reference_align_attempts=" + str(reference))
print("phase7_next_reducer_broad_first64_attempted=0")
print("phase7_next_reducer_broad_first64_decision=phase7_next_reducer_broad_gate_skipped_first1_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
