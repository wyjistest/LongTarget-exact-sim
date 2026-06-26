#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"
V2_DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v2_design.md"
NEXT_DOC="$ROOT/docs/fasim_gasal2_phase7_next_reducer_after_early_stop_no_go_design.md"

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" "$V2_DOC" "$NEXT_DOC" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

paths = [Path(path) for path in sys.argv[1:]]
texts = []
for path in paths:
    if not path.exists():
        raise SystemExit(f"missing required document: {path}")
    texts.append(path.read_text(encoding="utf-8"))
flat = " ".join("\n".join(texts).split())

required = [
    "phase7_gate_c_gpu_candidate_generator_design = defined",
    "coverage-preserving GPU candidate generator",
    "Gate A first1 is correctness-clean",
    "Gate B first64 is correctness-clean",
    "scoreInfo/preAlign work is still CPU work",
    "CPU aligner.Align() remains authority",
    "GASAL2 output authority = 0",
    "no GPU endpoint authority",
    "no GPU CIGAR or traceback authority",
    "no real opt-in",
    "candidate coverage before candidate reduction",
    "all-attempt early-stop frontier",
    "false_negative_scoreinfos = 0",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "candidate_align_attempts <= Gate B candidate_align_attempts",
    "scoreInfo/preAlign work reduced or replaced",
    "NEAT1 first1 coverage gate",
    "NEAT1 first64 broad gate",
    "workload matrix broad_replacement row is forbidden until Gate C first64 passes",
    "phase7_gate_c_runtime_smoke = pass",
    "oracle-metric scaffold smoke",
    "This is an oracle-metric scaffold smoke, not GPU candidate generation.",
    "No first1/first64 coverage proof has passed yet.",
    "phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors",
    "current Gate C does not generate GPU candidate descriptors",
    "current Gate C does not reduce or replace scoreInfo/preAlign work",
    "It must not continue to first64 broad characterization.",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

print("phase7_gate_c_gpu_candidate_generator_design=defined")
print("phase7_gate_c_runtime_smoke=oracle_metric_scaffold_clean")
print("phase7_gate_c_first1=no_go_no_gpu_candidate_descriptors")
print("phase7_gate_c_broad_gate_pass=0")
print("next_gate=new_gpu_candidate_descriptor_source_or_stop")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
