#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.md"
HOST_DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$HOST_DOC" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
host_doc = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, host_doc, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
host_flat = " ".join(host_doc.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke = gpu_contract_clean_first1",
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_status = first1_gpu_rows_equal_not_broad",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SHADOW",
    "runtime_default = off",
    "runtime_authority = CPU aligner.Align()",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_broad_restart_v4_gate_v4_1_pass = 1",
    "phase7_broad_restart_v4_gate_v4_2_pass = 0",
    "phase7_broad_restart_v4_gate_v4_3_pass = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "CPU `aligner.Align()` remains the score/endpoint/traceback/CIGAR/output and digest authority.",
    "make check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-shadow-runtime-smoke",
    "phase7_v4_gpu_legacy_byte_scoreinfo_shadow_runtime_smoke = gpu_contract_clean",
    "phase7_v4_gpu_legacy_byte_scoreinfo_shadow_active = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_shadow_host_contract_pass = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows_gt_zero = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 1",
    "phase7_v4_legacy_byte_scoreinfo_shadow_tasks = 48",
    "phase7_v4_legacy_byte_scoreinfo_shadow_cpu_scoreinfo_rows = 718",
    "phase7_v4_legacy_byte_scoreinfo_shadow_host_scoreinfo_rows = 718",
    "phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718",
    "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_mismatches = 0",
    "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_false_negatives = 0",
    "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_extra_required_attempts = 0",
    "phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 1",
    "source = gpu_legacy_byte_scoreinfo",
    "Gate v4.1:",
    "GPU legacy-byte scoreInfo shadow equality on NEAT1 first1",
    "gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay",
    "Do not add a `broad_replacement` workload-matrix row from this smoke.",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required v4 GPU shadow phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke = host_contract_clean_needs_gpu",
    "phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 0",
    "phase7_broad_restart_v4_next_gate = gpu_legacy_byte_scoreinfo_shadow_first1",
]:
    if phrase not in host_flat:
        raise SystemExit(f"missing host checkpoint prerequisite phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-shadow-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-shadow-smoke:",
]:
    if target not in makefile_text:
        raise SystemExit(f"missing Makefile target: {target}")

aggregate = "check-fasim-gasal2-roadmap-current-state:"
aggregate_index = makefile_text.find(aggregate)
if aggregate_index < 0:
    raise SystemExit("missing Makefile roadmap current-state target")
aggregate_line = makefile_text[aggregate_index:].splitlines()[0]
if "check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-shadow-smoke" not in aggregate_line:
    raise SystemExit("roadmap current-state target missing v4 GPU shadow dependency")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from v4 GPU first1 smoke")

print("phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke=gpu_contract_clean_first1")
print("phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_status=first1_gpu_rows_equal_not_broad")
print("phase7_broad_restart_v4_gpu_scoreinfo_rows=718")
print("phase7_broad_restart_v4_gate_v4_1_pass=1")
print("phase7_broad_restart_v4_runtime_next_gate=gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
