#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
matrix = Path(sys.argv[2])
makefile = Path(sys.argv[3])
for path in [doc, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate = correctness_clean_performance_no_go",
    "phase7_broad_restart_v5_cpu_authority_replay_first64_status = first64_correctness_clean_performance_no_go",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY",
    "runtime_default = off",
    "runtime_authority = CPU aligner.Align()",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_broad_restart_v5_gate_v5_1_pass = 1",
    "phase7_broad_restart_v5_gate_v5_2_pass = 1",
    "phase7_broad_restart_v5_gate_v5_3_pass = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "workload = neat1_first64",
    "digest_match = 1",
    "full_rows_equal = 1",
    "candidate_align_attempts = 115561",
    "reference_align_attempts = 211976",
    "align_attempt_reduction = 96415",
    "candidate_wall_seconds = 124.399845",
    "baseline_wall_seconds = 87.827405",
    "candidate_vs_baseline = 0.706009",
    "source_is_pre_scoreinfo = 1",
    "scoreinfo_prealign_reduced = 1",
    "gpu_descriptor_scoreinfos = 52994",
    "gpu_descriptor_attempts = 211976",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 624",
    "fallback_accounting_clean = 0",
    "performance_gate_pass = 0",
    "phase7_broad_restart_v5_runtime_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "Do not add a `broad_replacement` workload-matrix row from this first64 result.",
    "This is a no-go checkpoint for the current v5 CPU-authority descriptor replay implementation.",
]

missing = [phrase for phrase in required if phrase not in flat]
if missing:
    raise SystemExit("missing v5 first64 checkpoint phrase(s):\n" + "\n".join(missing))

for target in [
    "characterize-fasim-gasal2-phase7-v5-cpu-authority-replay-first64:",
    "check-fasim-gasal2-phase7-v5-cpu-authority-replay-first64-result:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-first64-broad-gate:",
]:
    if target not in makefile_text:
        raise SystemExit(f"missing Makefile target: {target}")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from v5 first64 no-go")

print("phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate=correctness_clean_performance_no_go")
print("phase7_broad_restart_v5_cpu_authority_replay_first64_status=first64_correctness_clean_performance_no_go")
print("phase7_broad_restart_v5_first64_baseline_wall_seconds=87.827405")
print("phase7_broad_restart_v5_first64_candidate_wall_seconds=124.399845")
print("phase7_broad_restart_v5_first64_candidate_vs_baseline=0.706009")
print("phase7_broad_restart_v5_first64_digest_match=1")
print("phase7_broad_restart_v5_first64_full_rows_equal=1")
print("phase7_broad_restart_v5_first64_candidate_align_attempts=115561")
print("phase7_broad_restart_v5_first64_reference_align_attempts=211976")
print("phase7_broad_restart_v5_first64_align_attempt_reduction=96415")
print("phase7_broad_restart_v5_first64_missing_required_attempts=624")
print("phase7_broad_restart_v5_first64_fallback_accounting_clean=0")
print("phase7_broad_restart_v5_gate_v5_3_pass=0")
print("phase7_broad_restart_v5_runtime_next_gate=different_gpu_execution_design_or_path_a_scope_decision")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
