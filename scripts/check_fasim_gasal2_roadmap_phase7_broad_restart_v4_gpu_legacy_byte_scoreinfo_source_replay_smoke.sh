#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.md"
PREV_DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.md"
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
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke = cpu_authority_replay_clean_first1",
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_status = first1_replay_clean_needs_first64_broad_gate",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SOURCE_REPLAY",
    "runtime_default = off",
    "runtime_authority = CPU aligner.Align()",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_broad_restart_v4_gate_v4_1_pass = 1",
    "phase7_broad_restart_v4_gate_v4_2_pass = 1",
    "phase7_broad_restart_v4_gate_v4_3_pass = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "make check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-source-replay-runtime-smoke",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_runtime_smoke = cpu_authority_replay_first1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_active = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_rows_equal = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_order_equal = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_attempt_windows_equal = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gpu_scoreinfo_rows_gt_zero = 1",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts = 2008",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts = 2872",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction = 864",
    "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gate_v4_2_pass = 1",
    "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_requested = 1",
    "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_active = 1",
    "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_streaming_ready = 1",
    "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_scoreinfo_rows = 718",
    "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_cpu_authority = 1",
    "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_2_pass = 1",
    "source = gpu_legacy_byte_scoreinfo_source_replay",
    "realpath_requested = 1",
    "realpath_fallbacks = 0",
    "realpath_extend_scoreinfo_groups = 718",
    "realpath_extend_align_attempts = 2008",
    "reference_align_attempts = 2872",
    "align_attempt_reduction = 864",
    "Gate v4.2:",
    "gpu_legacy_byte_scoreinfo_source_first64_broad_gate",
    "Do not add a `broad_replacement` workload-matrix row from this smoke.",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required v4 source replay phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke = gpu_contract_clean_first1",
    "phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718",
    "phase7_broad_restart_v4_runtime_next_gate = gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay",
]:
    if phrase not in prev_flat:
        raise SystemExit(f"missing predecessor checkpoint phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-source-replay-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-source-replay-smoke:",
]:
    if target not in makefile_text:
        raise SystemExit(f"missing Makefile target: {target}")

aggregate = "check-fasim-gasal2-roadmap-current-state:"
aggregate_index = makefile_text.find(aggregate)
if aggregate_index < 0:
    raise SystemExit("missing Makefile roadmap current-state target")
aggregate_line = makefile_text[aggregate_index:].splitlines()[0]
dependency = (
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-"
    "scoreinfo-source-replay-smoke"
)
if dependency not in aggregate_line:
    raise SystemExit("roadmap current-state target missing v4 source replay dependency")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from v4 source replay first1 smoke")

print("phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke=cpu_authority_replay_clean_first1")
print("phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_status=first1_replay_clean_needs_first64_broad_gate")
print("phase7_broad_restart_v4_source_replay_align_attempts=2008")
print("phase7_broad_restart_v4_source_replay_reference_align_attempts=2872")
print("phase7_broad_restart_v4_source_replay_align_attempt_reduction=864")
print("phase7_broad_restart_v4_gate_v4_2_pass=1")
print("phase7_broad_restart_v4_runtime_next_gate=gpu_legacy_byte_scoreinfo_source_first64_broad_gate")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
