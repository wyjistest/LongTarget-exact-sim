#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_seed_path_stop.md"
ATTEMPT="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md"
ORACLE="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$ATTEMPT" "$ORACLE" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
attempt = Path(sys.argv[2])
oracle = Path(sys.argv[3])
matrix = Path(sys.argv[4])
makefile = Path(sys.argv[5])
for path in [doc, attempt, oracle, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
attempt_flat = " ".join(attempt.read_text(encoding="utf-8").split())
oracle_flat = " ".join(oracle.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped",
    "phase7_broad_restart_v3_seed_path_status = stopped_no_output_clean_non_oracle_reducer",
    "runtime_authority = CPU aligner.Align()",
    "runtime_default = off",
    "No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.",
    "Do not add a broad_replacement workload-matrix row from this stop checkpoint.",
    "phase7_broad_restart_v3_attempt_coverage_seed_smoke = attempt_coverage_clean_needs_replay_preflight",
    "phase7_broad_restart_v3_gate_v3_1_pass = 1",
    "candidate_certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "cpu_scoreinfo_calls = 0",
    "cpu_scoreinfo_reduced = 1",
    "reference_attempts = 2,872",
    "raw_seed_hits = 1,051,822",
    "candidate_attempts = 108,694",
    "candidate_attempts_below_reference = 0",
    "phase7_broad_restart_v3_oracle_min_cover_replay_smoke = output_no_go",
    "reference_align_attempts = 2,872",
    "candidate_min_cover_positions = 463",
    "candidate_align_attempts = 463",
    "candidate_align_attempts_lt_reference = 1",
    "digest_match = 0",
    "full_rows_equal = 0",
    "missing_rows = 11",
    "extra_rows = 9",
    "phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0",
    "oracle_min_cover_uses_legacy_attempt_windows = 1",
    "real_pre_scoreinfo_reducer_proven = 0",
    "phase7_broad_restart_v3_gate_v3_2_pass = 0",
    "phase7_broad_restart_v3_may_continue_to_first64 = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "Do not continue the current seed/index path to first64.",
    "phase7_broad_restart_v3_next_gate = different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision",
    "full_rows_equal = true",
    "digest_match = true",
    "candidate_align_attempts < reference_align_attempts",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
    "real_pre_scoreinfo_reducer_proven = 1",
    "CPU aligner.Align() remains authority",
    "GPU endpoint/CIGAR/traceback/output authority = false",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required seed path stop phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_attempt_coverage_seed_smoke = attempt_coverage_clean_needs_replay_preflight",
    "candidate_certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "candidate_attempts_below_reference = 0",
    "real_pre_scoreinfo_reducer_proven = 0",
]:
    if phrase not in attempt_flat:
        raise SystemExit(f"missing attempt-coverage prerequisite phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_oracle_min_cover_replay_smoke = output_no_go",
    "candidate_align_attempts = 463",
    "digest_match = 0",
    "full_rows_equal = 0",
    "missing_rows = 11",
    "extra_rows = 9",
    "phase7_broad_restart_v3_next_gate = non_oracle_candidate_reducer_or_stop_seed_path",
]:
    if phrase not in oracle_flat:
        raise SystemExit(f"missing oracle replay prerequisite phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-seed-path-stop:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

aggregate = "check-fasim-gasal2-roadmap-current-state:"
aggregate_index = makefile_text.find(aggregate)
if aggregate_index < 0:
    raise SystemExit("missing Makefile roadmap current-state target")
aggregate_line = makefile_text[aggregate_index:].splitlines()[0]
for dependency in [
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-attempt-coverage-seed-smoke",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-oracle-min-cover-replay-smoke",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-seed-path-stop",
]:
    if dependency not in aggregate_line:
        raise SystemExit(f"roadmap current-state target missing dependency: {dependency}")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("workload matrix must not claim broad_replacement from seed path stop")

print("phase7_broad_restart_v3_seed_path_stop=current_seed_index_path_stopped")
print("phase7_broad_restart_v3_seed_path_status=stopped_no_output_clean_non_oracle_reducer")
print("phase7_broad_restart_v3_gate_v3_1_pass=1")
print("phase7_broad_restart_v3_gate_v3_2_pass=0")
print("phase7_broad_restart_v3_may_continue_to_first64=0")
print("phase7_broad_restart_v3_next_gate=different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
