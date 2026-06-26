#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md"
CERT="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$CERT" "$DESIGN" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
cert = Path(sys.argv[2])
design = Path(sys.argv[3])
matrix = Path(sys.argv[4])
makefile = Path(sys.argv[5])
for path in [doc, cert, design, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
cert_flat = " ".join(cert.read_text(encoding="utf-8").split())
design_flat = " ".join(design.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_all_column_certificate_smoke = scoreinfo_reducing_all_column_certificate",
    "phase7_broad_restart_v3_current_status = gate_v3_1_pass_attempt_overgenerate",
    "phase7_broad_restart_v3_gate_v3_1_pass = 1",
    "phase7_broad_restart_v3_gate_v3_2_pass = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "make check-fasim-gasal2-phase7-v3-all-column-certificate-env",
    "make check-fasim-gasal2-phase7-v3-all-column-certificate-runtime-smoke",
    "phase7_v3_all_column_certificate_runtime_smoke = scoreinfo_reducing_all_column_certificate",
    "phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1",
    "phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1",
    "phase7_v3_descriptor_source_candidate_certificate_checked = 1",
    "phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0",
    "phase7_v3_descriptor_source_missing_required_attempts = 0",
    "phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1",
    "The certificate covers every target end column.",
    "The attempt descriptor set covers every target window.",
    "This is intentionally overgenerating and is not a performance candidate.",
    "Do not add a broad_replacement workload-matrix row from this smoke.",
    "phase7_broad_restart_v3_next_gate = all_column_certificate_cpu_replay_first1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required all-column certificate phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_certificate_smoke = certificate_checked_no_scoreinfo_reduction",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
]:
    if phrase not in cert_flat:
        raise SystemExit(f"missing prior certificate phrase: {phrase}")

for phrase in [
    "Gate v3.1: NEAT1 first1 descriptor-source smoke",
    "Gate v3.2: NEAT1 first1 CPU-authority replay",
]:
    if phrase not in design_flat:
        raise SystemExit(f"missing v3 design phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v3-all-column-certificate-env:",
    "check-fasim-gasal2-phase7-v3-all-column-certificate-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-certificate-smoke:",
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
    raise SystemExit("workload matrix must not claim broad_replacement from v3 all-column smoke")

print("phase7_broad_restart_v3_all_column_certificate_smoke=scoreinfo_reducing_all_column_certificate")
print("phase7_broad_restart_v3_current_status=gate_v3_1_pass_attempt_overgenerate")
print("phase7_broad_restart_v3_gate_v3_1_pass=1")
print("phase7_broad_restart_v3_gate_v3_2_pass=0")
print("phase7_broad_restart_v3_next_gate=all_column_certificate_cpu_replay_first1")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
