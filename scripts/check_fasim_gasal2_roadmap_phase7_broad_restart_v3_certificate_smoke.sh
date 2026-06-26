#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md"
PRE="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PRE" "$DESIGN" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
pre = Path(sys.argv[2])
design = Path(sys.argv[3])
matrix = Path(sys.argv[4])
makefile = Path(sys.argv[5])
for path in [doc, pre, design, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
pre_flat = " ".join(pre.read_text(encoding="utf-8").split())
design_flat = " ".join(design.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_certificate_smoke = certificate_checked_no_scoreinfo_reduction",
    "phase7_broad_restart_v3_current_status = certificate_scaffold_no_go",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "make check-fasim-gasal2-phase7-v3-certificate-env",
    "make check-fasim-gasal2-phase7-v3-certificate-runtime-smoke",
    "phase7_v3_certificate_runtime_smoke = certificate_checked_no_scoreinfo_reduction",
    "phase7_v3_descriptor_source_active = 1",
    "phase7_v3_descriptor_source_pre_scoreinfo_source = 1",
    "phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1",
    "phase7_v3_descriptor_source_candidate_certificate_checked = 1",
    "phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0",
    "phase7_v3_descriptor_source_missing_required_attempts = 0",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0",
    "cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls",
    "This is a task-level scaffold certificate.",
    "It does not prove full legacy scoreInfo/attempt coverage.",
    "It does not reduce CPU scoreInfo/preAlign work.",
    "It does not pass Gate v3.1.",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
    "phase7_broad_restart_v3_may_continue_to_first64 = 0",
    "phase7_broad_restart_v3_next_gate = scoreinfo_reducing_candidate_certificate",
    "Do not add a broad_replacement workload-matrix row from this smoke.",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required certificate smoke phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke = pre_scoreinfo_descriptors_no_reduction",
    "phase7_v3_descriptor_source_candidate_certificate_checked = 0",
]:
    if phrase not in pre_flat:
        raise SystemExit(f"missing prior pre-scoreInfo phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_candidate_certificate_design = defined",
    "Gate v3.1: NEAT1 first1 descriptor-source smoke",
    "candidate_certificate_false_negatives = 0",
]:
    if phrase not in design_flat:
        raise SystemExit(f"missing v3 design phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v3-certificate-env:",
    "check-fasim-gasal2-phase7-v3-certificate-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-certificate-smoke:",
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
    raise SystemExit("workload matrix must not claim broad_replacement from v3 certificate smoke")

print("phase7_broad_restart_v3_certificate_smoke=certificate_checked_no_scoreinfo_reduction")
print("phase7_broad_restart_v3_current_status=certificate_scaffold_no_go")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("phase7_broad_restart_v3_may_continue_to_first64=0")
print("phase7_broad_restart_v3_next_gate=scoreinfo_reducing_candidate_certificate")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
