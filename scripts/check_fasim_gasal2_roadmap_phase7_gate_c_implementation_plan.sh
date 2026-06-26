#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-gate-c-gpu-candidate-generator.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md"

python3 - "$PLAN" "$ROADMAP" "$PHASE_PLAN" "$DESIGN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

paths = [Path(path) for path in sys.argv[1:]]
texts: list[str] = []
for path in paths:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")
    texts.append(path.read_text(encoding="utf-8"))
flat = " ".join("\n".join(texts).split())

required = [
    "# Fasim GASAL2 Phase 7 Gate C GPU Candidate Generator Implementation Plan",
    "phase7_gate_c_gpu_candidate_generator_implementation_plan = defined",
    "FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1",
    "default-off shadow path",
    "CPU aligner.Align() remains authority",
    "GASAL2 output authority = 0",
    "no GPU endpoint authority",
    "no GPU CIGAR or traceback authority",
    "no real opt-in",
    "Task 1: Gate C Env And Telemetry",
    "Task 2: Oracle Frontier Export Reuse",
    "Task 3: GPU Candidate Descriptor Shadow",
    "Task 4: Coverage Comparison Gate",
    "Task 5: CPU-Authority Replay Gate",
    "Task 6: NEAT1 first64 Broad Characterization",
    "Task 7: Roadmap And Matrix Decision",
    "NEAT1 first1 coverage gate",
    "NEAT1 first64 broad gate",
    "false_negative_scoreinfos = 0",
    "missing_rows = 0",
    "extra_rows = 0",
    "triplex_mismatches = 0",
    "candidate_align_attempts <= Gate B candidate_align_attempts",
    "scoreInfo/preAlign work reduced or replaced",
    "workload matrix broad_replacement row is forbidden until Gate C first64 passes",
    "phase7_gate_c_runtime_smoke = pass",
    "Gate C env, telemetry, and runtime hook are wired",
    "this is an oracle-metric scaffold smoke, not GPU candidate generation",
    "no first1 or first64 coverage proof has passed yet",
    "next gate = Gate C GPU Candidate Descriptor Shadow",
    "phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors",
    "current Gate C does not generate GPU candidate descriptors",
    "current Gate C does not reduce or replace scoreInfo/preAlign work",
    "this candidate must not continue to Gate C first64 broad gate",
    "next gate = new GPU candidate descriptor source or stop broad GASAL2 path",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

print("phase7_gate_c_gpu_candidate_generator_implementation_plan=defined")
print("phase7_gate_c_runtime_smoke=oracle_metric_scaffold_clean")
print("phase7_gate_c_first1=no_go_no_gpu_candidate_descriptors")
print("phase7_gate_c_broad_gate_pass=0")
print("next_gate=new_gpu_candidate_descriptor_source_or_stop")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
