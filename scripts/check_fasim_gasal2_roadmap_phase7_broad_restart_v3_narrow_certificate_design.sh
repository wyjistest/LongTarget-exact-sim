#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_design.md"
STOP="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$STOP" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
stop = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, stop, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
stop_flat = " ".join(stop.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_narrow_certificate_design = defined",
    "phase7_broad_restart_v3_narrow_certificate_status = design_only",
    "phase7_broad_restart_v3_next_gate = narrow_certificate_runtime_smoke",
    "phase7_broad_restart_v3_gate_v3_1_pass = 0",
    "phase7_broad_restart_v3_gate_v3_2_pass = 0",
    "must_be_narrower_than_all_column = 1",
    "do_not_use_all_column_or_all_window_certificate = 1",
    "candidate_attempts < 168,730,848",
    "candidate_attempts < reference_align_attempts required for v3.2",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
    "candidate_certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "CPU aligner.Align() output authority",
    "no GPU endpoint/CIGAR/traceback/output authority",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE",
    "no broad_replacement workload-matrix row",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required narrow-certificate design phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_all_column_replay_stop = candidate_attempt_explosion_no_go",
    "phase7_broad_restart_v3_next_gate = narrower_scoreinfo_reducing_certificate",
    "do_not_run_all_column_cpu_replay = 1",
]:
    if phrase not in stop_flat:
        raise SystemExit(f"missing all-column stop prerequisite phrase: {phrase}")

if "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-narrow-certificate-design:" not in makefile_text:
    raise SystemExit("missing Makefile narrow-certificate design target")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from narrow-certificate design")

print("phase7_broad_restart_v3_narrow_certificate_design=defined")
print("phase7_broad_restart_v3_narrow_certificate_status=design_only")
print("phase7_broad_restart_v3_next_gate=narrow_certificate_runtime_smoke")
print("phase7_broad_restart_v3_gate_v3_1_pass=0")
print("phase7_broad_restart_v3_gate_v3_2_pass=0")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
