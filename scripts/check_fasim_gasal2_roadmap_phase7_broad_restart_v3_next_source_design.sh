#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_next_source_design.md"
REAL_NARROW="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$REAL_NARROW" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
real_narrow = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, real_narrow, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
real_narrow_flat = " ".join(real_narrow.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_next_source_design = defined",
    "phase7_broad_restart_v3_next_source_status = design_only",
    "phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate_smoke",
    "previous_exact_column_candidate_status = no_go",
    "do_not_continue_all_column_replay = 1",
    "do_not_continue_bounded_narrow_probe = 1",
    "do_not_continue_existing_exact_column_gpu_scoreinfo = 1",
    "allowed_source_1 = different_exact_scoreinfo_compatible_gpu_execution",
    "allowed_source_2 = seed_or_index_certificate",
    "descriptor_source_before_cpu_scoreinfo = 1",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
    "candidate_certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "candidate_attempts < 168,730,848",
    "candidate_attempts < reference_align_attempts required before v3.2",
    "first1_descriptor_smoke_before_replay = 1",
    "first64_broad_gate_only_after_first1_replay = 1",
    "CPU aligner.Align() output authority",
    "no GPU endpoint/CIGAR/traceback/output authority",
    "no broad_replacement workload-matrix row",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required next-source design phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_real_narrow_certificate_coverage_proof = exact_column_candidate_no_go",
    "phase7_broad_restart_v3_exact_column_candidate_status = no_go",
    "phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate",
]:
    if phrase not in real_narrow_flat:
        raise SystemExit(f"missing real-narrow prerequisite phrase: {phrase}")

if "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-next-source-design:" not in makefile_text:
    raise SystemExit("missing Makefile next-source design target")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from next-source design")

print("phase7_broad_restart_v3_next_source_design=defined")
print("phase7_broad_restart_v3_next_source_status=design_only")
print("phase7_broad_restart_v3_next_gate=different_exact_scoreinfo_source_or_seed_certificate_smoke")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("phase7_broad_restart_v3_gate_v3_2_pass=0")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
