#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md"
PRIOR="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PRIOR" "$DESIGN" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
prior = Path(sys.argv[2])
design = Path(sys.argv[3])
matrix = Path(sys.argv[4])
makefile = Path(sys.argv[5])
for path in [doc, prior, design, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
prior_flat = " ".join(prior.read_text(encoding="utf-8").split())
design_flat = " ".join(design.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke = pre_scoreinfo_descriptors_no_reduction",
    "phase7_broad_restart_v3_current_status = pre_scoreinfo_scaffold_no_go",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "make check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-env",
    "make check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-runtime-smoke",
    "phase7_v3_pre_scoreinfo_descriptor_source_runtime_smoke = pre_scoreinfo_descriptors_no_reduction",
    "phase7_v3_descriptor_source_requested = 1",
    "phase7_v3_descriptor_source_active = 1",
    "phase7_v3_descriptor_source_pre_scoreinfo_source = 1",
    "phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0",
    "phase7_v3_descriptor_source_candidate_certificate_checked = 0",
    "The v3 source is now positioned before CPU scoreInfo/preAlign.",
    "The source can produce diagnostic candidate descriptors.",
    "The source does not reduce CPU scoreInfo/preAlign work.",
    "The source does not prove candidate-certificate coverage.",
    "gpu_candidate_scoreinfos > 0",
    "gpu_candidate_attempts > 0",
    "pre_scoreinfo_source = 1",
    "after_cpu_scoreinfo_source = 0",
    "cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls",
    "cpu_scoreinfo_reduced = 0",
    "candidate_certificate_checked = 0",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
    "phase7_broad_restart_v3_may_continue_to_first64 = 0",
    "phase7_broad_restart_v3_next_gate = certificate_checked_scoreinfo_reducing_descriptor_source",
    "continuing to first64 while cpu_scoreinfo_reduced = 0",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required pre-scoreInfo smoke phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
]:
    if phrase not in prior_flat:
        raise SystemExit(f"missing prior v3 smoke phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_candidate_certificate_design = defined",
    "Gate v3.1: NEAT1 first1 descriptor-source smoke",
    "candidate_certificate_false_negatives = 0",
]:
    if phrase not in design_flat:
        raise SystemExit(f"missing v3 design phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-env:",
    "check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-runtime-smoke:",
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
    raise SystemExit("workload matrix must not claim broad_replacement from v3 pre-scoreInfo smoke")

print("phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke=pre_scoreinfo_descriptors_no_reduction")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("phase7_broad_restart_v3_may_continue_to_first64=0")
print("phase7_broad_restart_v3_next_gate=certificate_checked_scoreinfo_reducing_descriptor_source")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
