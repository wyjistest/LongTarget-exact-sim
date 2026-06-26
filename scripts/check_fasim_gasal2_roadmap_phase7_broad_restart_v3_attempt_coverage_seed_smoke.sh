#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_strong_seed_smoke.md"
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
    "phase7_broad_restart_v3_attempt_coverage_seed_smoke = attempt_coverage_clean_needs_replay_preflight",
    "phase7_broad_restart_v3_attempt_coverage_seed_status = gate_v3_1_pass_candidate_attempts_high",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V3_ATTEMPT_COVERAGE_SEED_CERTIFICATE",
    "runtime_default = off",
    "runtime_authority = CPU aligner.Align()",
    "phase7_v3_descriptor_source_pre_scoreinfo_source = 1",
    "phase7_v3_descriptor_source_after_cpu_scoreinfo_source = 0",
    "phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1",
    "No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.",
    "Do not add a broad_replacement workload-matrix row from this runtime smoke.",
    "phase7_v3_attempt_coverage_seed_runtime_smoke = attempt_coverage_clean",
    "tasks = 48",
    "reference_scoreinfos = 718",
    "reference_attempts = 2,872",
    "candidate_scoreinfos = 718",
    "raw_seed_hits = 1,051,822",
    "candidate_attempts = 108,694",
    "candidate_min_cover_positions = 463",
    "candidate_attempts_lt_all_column = 1",
    "candidate_attempts_lt_raw_seed_hits = 1",
    "candidate_min_cover_positions_lt_reference_attempts = 1",
    "candidate_certificate_checked = 1",
    "candidate_certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "baseline_cpu_scoreinfo_calls = 718",
    "all_column_replay_attempts = 168,730,848",
    "candidate_attempts_below_reference = 0",
    "candidate_min_cover_positions_below_reference = 1",
    "oracle_min_cover_uses_legacy_attempt_windows = 1",
    "real_pre_scoreinfo_reducer_proven = 0",
    "phase7_broad_restart_v3_gate_v3_1_pass = 1",
    "phase7_broad_restart_v3_gate_v3_2_pass = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "phase7_broad_restart_v3_next_gate = oracle_min_cover_replay_shape_probe_or_non_oracle_candidate_reducer",
    "Do not continue to first64 until first1 replay or replay preflight proves both correctness and Align-side work reduction.",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required attempt-coverage seed phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_strong_seed_smoke = task_coverage_clean_attempt_coverage_missing",
    "phase7_broad_restart_v3_next_gate = attempt_coverage_seed_certificate_or_different_exact_scoreinfo_source",
]:
    if phrase not in prev_flat:
        raise SystemExit(f"missing strong-seed prerequisite phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v3-attempt-coverage-seed-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-attempt-coverage-seed-smoke:",
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
    raise SystemExit("workload matrix must not claim broad_replacement from attempt-coverage seed smoke")

print("phase7_broad_restart_v3_attempt_coverage_seed_smoke=attempt_coverage_clean_needs_replay_preflight")
print("phase7_broad_restart_v3_attempt_coverage_seed_status=gate_v3_1_pass_candidate_attempts_high")
print("phase7_broad_restart_v3_gate_v3_1_pass=1")
print("phase7_broad_restart_v3_gate_v3_2_pass=0")
print("phase7_broad_restart_v3_next_gate=oracle_min_cover_replay_shape_probe_or_non_oracle_candidate_reducer")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
