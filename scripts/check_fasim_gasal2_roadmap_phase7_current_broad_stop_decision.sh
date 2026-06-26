#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_current_broad_stop_decision.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
BROAD_GATE="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
GATE_C_STOP="$ROOT/docs/fasim_gasal2_phase7_gate_c_stop_checkpoint.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"

python3 - "$DOC" "$ROADMAP" "$BROAD_GATE" "$GATE_C_STOP" "$MATRIX" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
broad_gate = Path(sys.argv[3])
gate_c_stop = Path(sys.argv[4])
matrix = Path(sys.argv[5])
for path in [doc, roadmap, broad_gate, gate_c_stop, matrix]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(
    "\n".join(
        path.read_text(encoding="utf-8")
        for path in [doc, roadmap, broad_gate, gate_c_stop]
    ).split()
)

required = [
    "phase7_current_broad_stop_decision = current_broad_sources_no_go",
    "CPU aligner.Align() remains score/endpoint/traceback/CIGAR/output authority.",
    "GASAL2 output authority = 0",
    "no GPU endpoint authority",
    "no GPU CIGAR or traceback authority",
    "no broad_replacement workload-matrix row may be added from current evidence.",
    "decision = broad_path_current_architecture_no_go",
    "candidate_vs_baseline = 0.301413x",
    "attempt_consumer_shadow_no_cpu_align_reduction_no_go",
    "emission_only_consumer_shadow_correctness_no_go",
    "phase7_frontier_early_stop_runtime_first1_no_go",
    "phase7_all_attempt_early_stop_runtime_first64 = correctness_go_near_parity_not_broad",
    "scoreInfo/preAlign work is still CPU work",
    "phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors",
    "gpu_candidate_attempts = 0",
    "current_gate_c_source_status = stopped_no_gpu_candidate_descriptors",
    "current_broad_sources_status = stopped",
    "phase7_current_broad_sources_may_continue = 0",
    "phase7_new_architecture_required = 1",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Path A requires explicit user acceptance of the scoped product contract.",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement")

print("phase7_current_broad_stop_decision=current_broad_sources_no_go")
print("current_broad_sources_status=stopped")
print("phase7_current_broad_sources_may_continue=0")
print("phase7_new_architecture_required=1")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
