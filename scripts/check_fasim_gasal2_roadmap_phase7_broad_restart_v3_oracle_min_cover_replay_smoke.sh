#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
prev = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, prev, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
prev_flat = " ".join(prev.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_oracle_min_cover_replay_smoke = output_no_go",
    "phase7_broad_restart_v3_oracle_min_cover_replay_status = oracle_shape_probe_no_go",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V3_ORACLE_MIN_COVER_REPLAY",
    "runtime_default = off",
    "runtime_authority = CPU aligner.Align()",
    "No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.",
    "Do not add a broad_replacement workload-matrix row from this runtime smoke.",
    "reference_align_attempts = 2,872",
    "candidate_min_cover_positions = 463",
    "candidate_align_attempts = 463",
    "skipped_attempts = 2,409",
    "candidate_align_attempts_lt_reference = 1",
    "digest_match = 0",
    "full_rows_equal = 0",
    "missing_rows = 11",
    "extra_rows = 9",
    "phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "phase7_broad_restart_v3_next_gate = non_oracle_candidate_reducer_or_stop_seed_path",
    "Do not continue this oracle min-cover replay shape to first64.",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required oracle min-cover replay phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_attempt_coverage_seed_smoke = attempt_coverage_clean_needs_replay_preflight",
    "candidate_min_cover_positions = 463",
    "oracle_min_cover_uses_legacy_attempt_windows = 1",
]:
    if phrase not in prev_flat:
        raise SystemExit(f"missing attempt-coverage prerequisite phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v3-oracle-min-cover-replay-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-oracle-min-cover-replay-smoke:",
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
    raise SystemExit("workload matrix must not claim broad_replacement from oracle min-cover replay smoke")

print("phase7_broad_restart_v3_oracle_min_cover_replay_smoke=output_no_go")
print("phase7_broad_restart_v3_oracle_min_cover_replay_status=oracle_shape_probe_no_go")
print("phase7_broad_restart_v3_gate_v3_2_shape_probe_pass=0")
print("phase7_broad_restart_v3_next_gate=non_oracle_candidate_reducer_or_stop_seed_path")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
