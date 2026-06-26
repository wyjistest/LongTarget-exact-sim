#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.md"
PREV_DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV_DOC" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
prev_doc = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, prev_doc, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
prev_flat = " ".join(prev_doc.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate = correctness_clean_performance_no_go",
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_status = first64_correctness_clean_performance_no_go",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SOURCE_REPLAY",
    "runtime_default = off",
    "runtime_authority = CPU aligner.Align()",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "baseline_wall_seconds = 86.358386",
    "candidate_wall_seconds = 134.744406",
    "candidate_vs_baseline = 0.640905",
    "digest_match = 1",
    "candidate_gate_v4_2_pass = 1",
    "candidate_gpu_scoreinfo_rows = 52994",
    "candidate_source_replay_scoreinfo_rows = 52994",
    "candidate_realpath_requested = 1",
    "candidate_realpath_fallbacks = 0",
    "candidate_realpath_extend_scoreinfo_groups = 52994",
    "candidate_realpath_extend_align_attempts = 140087",
    "candidate_realpath_extend_seconds = 52.1721",
    "candidate_realpath_extend_align_seconds = 52.0788",
    "reference_align_attempts = 211976",
    "align_attempt_reduction = 71889",
    "performance_gate_pass = 0",
    "phase7_broad_restart_v4_gate_v4_1_pass = 1",
    "phase7_broad_restart_v4_gate_v4_2_pass = 1",
    "phase7_broad_restart_v4_gate_v4_3_pass = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "phase7_broad_restart_v4_runtime_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "Do not add a `broad_replacement` workload-matrix row from this first64 result.",
    "This is a no-go checkpoint for the current v4 source replay implementation.",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required v4 source first64 phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke = cpu_authority_replay_clean_first1",
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_status = first1_replay_clean_needs_first64_broad_gate",
    "phase7_broad_restart_v4_runtime_next_gate = gpu_legacy_byte_scoreinfo_source_first64_broad_gate",
]:
    if phrase not in prev_flat:
        raise SystemExit(f"missing predecessor source replay phrase: {phrase}")

target = (
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-"
    "scoreinfo-source-first64-broad-gate:"
)
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

aggregate = "check-fasim-gasal2-roadmap-current-state:"
aggregate_index = makefile_text.find(aggregate)
if aggregate_index < 0:
    raise SystemExit("missing Makefile roadmap current-state target")
aggregate_line = makefile_text[aggregate_index:].splitlines()[0]
dependency = target[:-1]
if dependency not in aggregate_line:
    raise SystemExit("roadmap current-state target missing v4 source first64 dependency")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from v4 source first64 no-go")

print("phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate=correctness_clean_performance_no_go")
print("phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_status=first64_correctness_clean_performance_no_go")
print("phase7_broad_restart_v4_source_first64_baseline_wall_seconds=86.358386")
print("phase7_broad_restart_v4_source_first64_candidate_wall_seconds=134.744406")
print("phase7_broad_restart_v4_source_first64_candidate_vs_baseline=0.640905")
print("phase7_broad_restart_v4_source_first64_digest_match=1")
print("phase7_broad_restart_v4_source_first64_align_attempts=140087")
print("phase7_broad_restart_v4_source_first64_reference_align_attempts=211976")
print("phase7_broad_restart_v4_source_first64_align_attempt_reduction=71889")
print("phase7_broad_restart_v4_gate_v4_3_pass=0")
print("phase7_broad_restart_v4_runtime_next_gate=different_gpu_execution_design_or_path_a_scope_decision")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
