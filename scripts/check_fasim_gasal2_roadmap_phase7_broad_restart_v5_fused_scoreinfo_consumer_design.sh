#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_design.md"
V4_DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$V4_DOC" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
v4_doc = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, v4_doc, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
v4_flat = " ".join(v4_doc.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined",
    "phase7_broad_restart_v5_status = design_only",
    "phase7_broad_restart_v5_design_family = fused_gpu_scoreinfo_to_candidate_attempt_descriptors",
    "phase7_broad_restart_v5_differs_from_v4_source_replay = 1",
    "phase7_broad_restart_v5_may_claim_completion = 0",
    "phase7_broad_restart_v5_gate_v5_1_pass = 0",
    "phase7_broad_restart_v5_gate_v5_2_pass = 0",
    "phase7_broad_restart_v5_gate_v5_3_pass = 0",
    "phase7_broad_restart_v5_next_gate = fused_scoreinfo_consumer_descriptor_contract_first1",
    "Do not materialize the full legacy scoreInfo row stream as a host-visible intermediate.",
    "Compute legacy byte scoreInfo and consume the row stream in the same GPU execution design.",
    "Emit compact candidate attempt descriptors, not endpoint, CIGAR, traceback, output, or digest authority.",
    "CPU aligner.Align() remains the only endpoint, CIGAR, traceback, output, and digest authority.",
    "scoreInfo/preAlign work reduced or replaced = required",
    "Align-side work reduced or replaced = required",
    "candidate_wall_seconds < baseline_wall_seconds = required",
    "fallbacks = 0 for the claimed GPU path = required",
    "full row-set/digest equality = required",
    "no broad_replacement workload-matrix row before Gate v5.3 passes",
    "current v4 source replay must not continue as the broad path",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required v5 design phrase: {phrase}")

for stale in [
    "FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SOURCE_REPLAY is the next runtime path",
    "GPU endpoint authority",
    "GPU CIGAR authority",
    "GPU traceback authority",
]:
    if stale in flat:
        raise SystemExit(f"v5 design contains forbidden stale phrase: {stale}")

for phrase in [
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate = correctness_clean_performance_no_go",
    "phase7_broad_restart_v4_runtime_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "This is a no-go checkpoint for the current v4 source replay implementation.",
]:
    if phrase not in v4_flat:
        raise SystemExit(f"missing v4 no-go predecessor phrase: {phrase}")

target = (
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-"
    "scoreinfo-consumer-design:"
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
    raise SystemExit("roadmap current-state target missing v5 design dependency")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from v5 design-only checkpoint")

print("phase7_broad_restart_v5_fused_scoreinfo_consumer_design=defined")
print("phase7_broad_restart_v5_status=design_only")
print("phase7_broad_restart_v5_design_family=fused_gpu_scoreinfo_to_candidate_attempt_descriptors")
print("phase7_broad_restart_v5_differs_from_v4_source_replay=1")
print("phase7_broad_restart_v5_gate_v5_1_pass=0")
print("phase7_broad_restart_v5_gate_v5_2_pass=0")
print("phase7_broad_restart_v5_gate_v5_3_pass=0")
print("phase7_broad_restart_v5_next_gate=fused_scoreinfo_consumer_descriptor_contract_first1")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
