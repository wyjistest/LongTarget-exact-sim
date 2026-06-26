#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md"
STOP="$ROOT/docs/fasim_gasal2_phase7_current_broad_stop_decision.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"

python3 - "$DOC" "$STOP" "$MATRIX" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
stop = Path(sys.argv[2])
matrix = Path(sys.argv[3])
for path in [doc, stop, matrix]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
stop_flat = " ".join(stop.read_text(encoding="utf-8").split())

required = [
    "phase7_broad_restart_v3_candidate_certificate_design = defined",
    "phase7_broad_restart_v3_status = design_only",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "current broad sources are stopped",
    "new descriptor source before CPU scoreInfo/preAlign has already done the broad work",
    "GPU/native descriptor source",
    "candidate certificate",
    "CPU-authority replay",
    "full-output comparison",
    "not current replacement-consumer",
    "not current attempt-consumer",
    "not current emission-only consumer",
    "not current frontier early-stop",
    "not all-attempt early-stop by itself",
    "not current Gate C oracle-metric scaffold",
    "not a descriptor list derived only after CPU frontier logging",
    "not GASAL2 endpoint/CIGAR/traceback/output authority",
    "CPU `aligner.Align()` remains the authority",
    "requires_gpu_or_native_descriptor_source = 1",
    "requires_candidate_certificate = 1",
    "requires_cpu_authority_replay = 1",
    "requires_scoreinfo_prealign_reduction = 1",
    "requires_align_side_reduction = 1",
    "requires_full_output_equality = 1",
    "Gate v3.1: NEAT1 first1 descriptor-source smoke",
    "gpu_candidate_scoreinfos > 0",
    "gpu_candidate_attempts > 0",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
    "candidate_certificate_false_negatives = 0",
    "Gate v3.2: NEAT1 first1 CPU-authority replay",
    "digest_match = 1",
    "full_rows_equal = 1",
    "candidate_align_attempts < reference_align_attempts",
    "Gate v3.3: NEAT1 first64 broad gate",
    "candidate_vs_baseline > 1.0x",
    "Only Gate v3.3 can create a `contract=broad_replacement` workload-matrix row.",
    "phase7_broad_restart_v3_current_status = design_only",
    "phase7_broad_restart_v3_next_gate = descriptor_source_smoke",
    "phase7_broad_restart_v3_may_claim_completion = 0",
    "broad_gate_pass = 0",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

stop_required = [
    "phase7_current_broad_stop_decision = current_broad_sources_no_go",
    "current_broad_sources_status = stopped",
    "phase7_new_architecture_required = 1",
]
for phrase in stop_required:
    if phrase not in stop_flat:
        raise SystemExit(f"missing stop checkpoint phrase: {phrase}")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from v3 design")

print("phase7_broad_restart_v3_candidate_certificate_design=defined")
print("phase7_broad_restart_v3_current_status=design_only")
print("phase7_broad_restart_v3_next_gate=descriptor_source_smoke")
print("phase7_broad_restart_v3_may_claim_completion=0")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
