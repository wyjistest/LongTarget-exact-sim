#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$DESIGN" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
design = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, design, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
design_flat = " ".join(design.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source",
    "phase7_broad_restart_v3_current_status = scaffold_no_go",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "make check-fasim-gasal2-phase7-v3-descriptor-source-env",
    "make check-fasim-gasal2-phase7-v3-descriptor-source-runtime-smoke",
    "phase7_v3_descriptor_source_runtime_smoke = current_no_pre_scoreinfo_source",
    "phase7_v3_descriptor_source_requested = 1",
    "phase7_v3_descriptor_source_active = 0",
    "phase7_v3_descriptor_source_candidate_attempts = 0",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0",
    "The current code does not yet have a pre-scoreInfo GPU/native descriptor source.",
    "The current code does not produce candidate descriptors.",
    "The current code does not reduce CPU scoreInfo/preAlign calls.",
    "gpu_candidate_scoreinfos = 0",
    "gpu_candidate_attempts = 0",
    "cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls",
    "pre_scoreinfo_source = 0",
    "after_cpu_scoreinfo_source = 1",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
    "phase7_broad_restart_v3_may_continue_to_first64 = 0",
    "phase7_broad_restart_v3_next_gate = real_pre_scoreinfo_descriptor_source",
    "claiming broad_replacement from this smoke",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required smoke phrase: {phrase}")

design_required = [
    "phase7_broad_restart_v3_candidate_certificate_design = defined",
    "Gate v3.1: NEAT1 first1 descriptor-source smoke",
    "gpu_candidate_scoreinfos > 0",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
]
for phrase in design_required:
    if phrase not in design_flat:
        raise SystemExit(f"missing v3 design phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v3-descriptor-source-env:",
    "check-fasim-gasal2-phase7-v3-descriptor-source-runtime-smoke:",
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
    raise SystemExit("workload matrix must not claim broad_replacement from v3 smoke")

print("phase7_broad_restart_v3_descriptor_source_smoke=current_no_pre_scoreinfo_source")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("phase7_broad_restart_v3_may_continue_to_first64=0")
print("phase7_broad_restart_v3_next_gate=real_pre_scoreinfo_descriptor_source")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
