#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_next_source_smoke.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_next_source_design.md"
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
    "phase7_broad_restart_v3_next_source_smoke = seed_certificate_fail_closed",
    "phase7_broad_restart_v3_next_source_status = runtime_smoke_no_go",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V3_SEED_CERTIFICATE_SOURCE",
    "phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1",
    "phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1",
    "phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1",
    "phase7_v3_descriptor_source_candidate_certificate_checked = 1",
    "phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1",
    "phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1",
    "phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
    "phase7_broad_restart_v3_gate_v3_2_pass = 0",
    "CPU aligner.Align() output authority",
    "no GPU endpoint/CIGAR/traceback/output authority",
    "Do not add a broad_replacement workload-matrix row from this runtime smoke.",
    "phase7_broad_restart_v3_next_gate = stronger_seed_certificate_or_different_exact_scoreinfo_source",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required next-source smoke phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_next_source_design = defined",
    "phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate_smoke",
    "allowed_source_2 = seed_or_index_certificate",
]:
    if phrase not in design_flat:
        raise SystemExit(f"missing next-source design prerequisite phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v3-next-source-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-next-source-smoke:",
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
    raise SystemExit("workload matrix must not claim broad_replacement from next-source smoke")

print("phase7_broad_restart_v3_next_source_smoke=seed_certificate_fail_closed")
print("phase7_broad_restart_v3_next_source_status=runtime_smoke_no_go")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("phase7_broad_restart_v3_gate_v3_2_pass=0")
print("phase7_broad_restart_v3_next_gate=stronger_seed_certificate_or_different_exact_scoreinfo_source")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
