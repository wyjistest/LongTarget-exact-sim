#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md"
ALL_COLUMN="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$ALL_COLUMN" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
all_column = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, all_column, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
all_column_flat = " ".join(all_column.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_all_column_replay_stop = candidate_attempt_explosion_no_go",
    "phase7_broad_restart_v3_gate_v3_1_pass = 1",
    "phase7_broad_restart_v3_gate_v3_2_pass = 0",
    "candidate_attempts = 168,730,848",
    "reference_align_attempts = 2,872",
    "candidate_attempt_ratio = 58,750.30x",
    "candidate_align_attempts < reference_align_attempts cannot pass",
    "do_not_run_all_column_cpu_replay = 1",
    "phase7_broad_restart_v3_may_continue_to_first64 = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Do not add a broad_replacement workload-matrix row from this stop checkpoint.",
    "phase7_broad_restart_v3_next_gate = narrower_scoreinfo_reducing_certificate",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required all-column replay stop phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_all_column_certificate_smoke = scoreinfo_reducing_all_column_certificate",
    "phase7_broad_restart_v3_gate_v3_1_pass = 1",
    "phase7_broad_restart_v3_gate_v3_2_pass = 0",
]:
    if phrase not in all_column_flat:
        raise SystemExit(f"missing all-column certificate phrase: {phrase}")

if "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-replay-stop:" not in makefile_text:
    raise SystemExit("missing Makefile all-column replay stop target")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from v3 all-column stop")

print("phase7_broad_restart_v3_all_column_replay_stop=candidate_attempt_explosion_no_go")
print("phase7_broad_restart_v3_gate_v3_1_pass=1")
print("phase7_broad_restart_v3_gate_v3_2_pass=0")
print("phase7_broad_restart_v3_may_continue_to_first64=0")
print("phase7_broad_restart_v3_next_gate=narrower_scoreinfo_reducing_certificate")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
