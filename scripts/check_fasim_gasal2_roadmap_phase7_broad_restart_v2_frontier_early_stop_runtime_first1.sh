#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v2_design.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

texts = [Path(path).read_text(encoding="utf-8") for path in sys.argv[1:]]
flat = " ".join("\n".join(texts).split())

required = [
    "phase7_broad_restart_v2_frontier_early_stop_runtime_first1 = correctness_no_go",
    "make characterize-fasim-gasal2-phase7-frontier-early-stop-runtime",
    "make check-fasim-gasal2-phase7-frontier-early-stop-runtime-result",
    "digest_match = 0",
    "full_rows_equal = 0",
    "missing_rows = 7",
    "extra_rows = 5",
    "triplex_mismatches = 12",
    "candidate_align_attempts = 1,309",
    "reference_align_attempts = 2,872",
    "align_attempt_reduction = 1,563",
    "decision = phase7_frontier_early_stop_runtime_first1_no_go",
    "decision_reasons = output_rows_differ,missing_rows,extra_rows",
    "this candidate must not continue to NEAT1 first64 broad gate",
    "next gate = new reducer or architecture",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

print("phase7_broad_restart_v2_frontier_early_stop_runtime_first1=correctness_no_go")
print("phase7_frontier_early_stop_runtime_first1_digest_match=0")
print("phase7_frontier_early_stop_runtime_first1_full_rows_equal=0")
print("phase7_frontier_early_stop_runtime_first1_candidate_align_attempts=1309")
print("phase7_frontier_early_stop_runtime_first1_reference_align_attempts=2872")
print("phase7_frontier_early_stop_runtime_first1_broad_gate_pass=0")
print("next_gate=new_reducer_or_architecture")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
