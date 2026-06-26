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
    "phase7_all_attempt_early_stop_runtime_first64 = correctness_go_near_parity_not_broad",
    "make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64",
    "make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64-result",
    "FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1",
    "digest_match = 1",
    "full_rows_equal = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "false_negative_scoreinfos = 0",
    "candidate_align_attempts = 140,087",
    "reference_align_attempts = 211,976",
    "align_attempt_reduction = 71,889",
    "candidate_vs_baseline = near_parity_across_reruns",
    "decision = phase7_all_attempt_early_stop_runtime_first64_go",
    "scoreInfo/preAlign work is still CPU work",
    "wall time is near parity across reruns, not a material broad performance win",
    "broad_gate_pass = 0",
    "next gate = coverage-preserving GPU candidate generator",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

print("phase7_all_attempt_early_stop_runtime_first64=correctness_go_near_parity_not_broad")
print("phase7_all_attempt_early_stop_runtime_first64_broad_gate_pass=0")
print("next_gate=coverage_preserving_gpu_candidate_generator")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
