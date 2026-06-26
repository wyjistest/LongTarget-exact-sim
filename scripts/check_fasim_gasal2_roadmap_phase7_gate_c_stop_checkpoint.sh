#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gate_c_stop_checkpoint.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md"

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" "$DESIGN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

paths = [Path(path) for path in sys.argv[1:]]
for path in paths:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")
flat = " ".join("\n".join(path.read_text(encoding="utf-8") for path in paths).split())

required = [
    "phase7_gate_c_stop_checkpoint = current_source_no_go",
    "phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors",
    "digest_match = 1",
    "full_rows_equal = 1",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "false_negative_scoreinfos = 0",
    "candidate_align_attempts = 2,008",
    "gate_b_candidate_align_attempts = 2,008",
    "scoreinfo_reduced = 0",
    "gpu_candidate_scoreinfos = 0",
    "gpu_candidate_attempts = 0",
    "decision = phase7_gate_c_first1_no_go",
    "decision_reasons = no_gpu_candidate_descriptors,scoreinfo_not_reduced",
    "current_gate_c_source_status = stopped_no_gpu_candidate_descriptors",
    "gate_c_first64_allowed = 0",
    "No broad_replacement workload-matrix row may be added from this evidence.",
    "gpu_candidate_scoreinfos > 0",
    "gpu_candidate_attempts > 0",
    "scoreinfo_reduced = 1",
    "candidate_align_attempts <= 2,008",
    "CPU aligner.Align() remains authority",
    "GASAL2 output authority = 0",
    "no GPU endpoint authority",
    "no GPU CIGAR or traceback authority",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

print("phase7_gate_c_stop_checkpoint=current_source_no_go")
print("current_gate_c_source_status=stopped_no_gpu_candidate_descriptors")
print("gate_c_first64_allowed=0")
print("phase7_gate_c_broad_gate_pass=0")
print("next_gate=new_gpu_candidate_descriptor_source_or_stop_broad_gasal2")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
