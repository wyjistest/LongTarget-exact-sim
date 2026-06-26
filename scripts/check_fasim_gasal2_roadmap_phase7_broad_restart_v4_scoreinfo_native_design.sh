#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v4_scoreinfo_native_design.md"
SEED_STOP="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v3_seed_path_stop.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$SEED_STOP" "$MATRIX" "$MAKEFILE" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
seed_stop = Path(sys.argv[2])
matrix = Path(sys.argv[3])
makefile = Path(sys.argv[4])
for path in [doc, seed_stop, matrix, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
seed_stop_flat = " ".join(seed_stop.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v4_scoreinfo_native_design = defined",
    "phase7_broad_restart_v4_status = design_only",
    "phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1",
    "phase7_broad_restart_v4_may_claim_completion = 0",
    "broad_gate_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "No GPU endpoint, CIGAR, traceback, output, or digest authority is introduced.",
    "CPU `aligner.Align()` remains the score/endpoint/traceback/CIGAR/output/digest authority",
    "phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped",
    "phase7_broad_restart_v3_next_gate = different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision",
    "selected_next_path = different_scoreinfo_compatible_gpu_execution_design",
    "all-attempt early-stop first1:",
    "candidate_align_attempts = 2,008",
    "reference_align_attempts = 2,872",
    "all-attempt early-stop first64:",
    "candidate_align_attempts = 140,087",
    "reference_align_attempts = 211,976",
    "legacy_ssw_byte_saturation = required",
    "legacy_bias_behavior = required",
    "legacy_word_upgrade_on_saturation = required",
    "legacy_window_of_5_peak_clustering = required",
    "legacy_scoreInfo_order = required",
    "legacy_attempt_window_order = required",
    "legacy_tie_policy = required",
    "scoreinfo_rows_equal = true",
    "scoreinfo_order_equal = true",
    "scoreinfo_attempt_windows_equal = true",
    "scoreinfo_mismatches = 0",
    "scoreinfo_false_negatives = 0",
    "scoreinfo_extra_required_attempts = 0",
    "GPU Legacy ScoreInfo Generator",
    "CPU-Authority All-Attempt Early-Stop Replay",
    "phase7_v4_legacy_byte_scoreinfo_shadow_active = 1",
    "cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
    "real_pre_scoreinfo_reducer_proven = 1",
    "full_rows_equal = true",
    "digest_match = true",
    "candidate_align_attempts < reference_align_attempts",
    "candidate_wall_seconds < baseline_wall_seconds",
    "candidate_vs_baseline > 1.0",
    "scoreInfo/preAlign work reduced or replaced",
    "Align-side work reduced or replaced",
    "contract = broad_replacement",
    "no broad_replacement workload-matrix row",
    "no seed min-cover replay continuation",
    "phase7_broad_restart_v4_gate_v4_1_pass = 0",
    "phase7_broad_restart_v4_gate_v4_2_pass = 0",
    "phase7_broad_restart_v4_gate_v4_3_pass = 0",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required v4 scoreInfo-native design phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped",
    "phase7_broad_restart_v3_seed_path_status = stopped_no_output_clean_non_oracle_reducer",
    "phase7_broad_restart_v3_may_continue_to_first64 = 0",
    "phase7_broad_restart_v3_next_gate = different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision",
]:
    if phrase not in seed_stop_flat:
        raise SystemExit(f"missing seed-path-stop prerequisite phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-broad-restart-v4-scoreinfo-native-design:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

aggregate = "check-fasim-gasal2-roadmap-current-state:"
aggregate_index = makefile_text.find(aggregate)
if aggregate_index < 0:
    raise SystemExit("missing Makefile roadmap current-state target")
aggregate_line = makefile_text[aggregate_index:].splitlines()[0]
for dependency in [
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v3-seed-path-stop",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v4-scoreinfo-native-design",
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
    raise SystemExit("workload matrix must not claim broad_replacement from v4 design")

print("phase7_broad_restart_v4_scoreinfo_native_design=defined")
print("phase7_broad_restart_v4_status=design_only")
print("phase7_broad_restart_v4_next_gate=legacy_byte_scoreinfo_shadow_first1")
print("phase7_broad_restart_v4_gate_v4_1_pass=0")
print("phase7_broad_restart_v4_gate_v4_2_pass=0")
print("phase7_broad_restart_v4_gate_v4_3_pass=0")
print("claimed_broad_replacement_rows=0")
print("broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
