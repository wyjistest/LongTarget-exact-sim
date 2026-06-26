#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
ACTION="$ROOT/docs/fasim_gasal2_goal_completion_action_roadmap.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
CURRENT_STATE_CHECK="$ROOT/scripts/check_fasim_gasal2_roadmap_current_state.sh"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$ACTION" "$CURRENT_STATE" "$CURRENT_STATE_CHECK" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    prev,
    roadmap,
    action,
    current_state,
    current_state_check,
    makefile,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [
    doc,
    prev,
    roadmap,
    action,
    current_state,
    current_state_check,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
action_text = action.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
current_state_check_text = current_state_check.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 GPU Exact Work-Unit Compaction First1 Shadow Consumer No-Go",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md",
    "previous_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go",
    "requested = 1",
    "active = 1",
    "scoreinfo_key_descriptors > 0",
    "scoreinfo_unique_keys > 0",
    "scoreinfo_duplicate_units = 0",
    "align_key_descriptors > 0",
    "align_unique_keys > 0",
    "align_duplicate_attempts = 0",
    "key_collisions = 0",
    "cpu_key_validation_mismatches = 0",
    "unsupported_key_descriptors = 0",
    "fallback_to_full_cpu_replay = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "gate_first1_shadow_pass = 1",
    "gate_first1_pass = 0",
    "accepted_exact_work_unit_compaction_consumer = 0",
    "accepted_exact_work_unit_compaction_reduction = 0",
    "accepted_scoreinfo_prealign_compaction = 0",
    "accepted_align_side_compaction = 0",
    "consumer_can_reduce_scoreinfo_work = 0",
    "consumer_can_reduce_align_work = 0",
    "consumer_can_reduce_cpu_replay_frontier = 0",
    "consumer_available_before_scoreinfo_prealign_skip = 0",
    "consumer_available_before_align_skip = 0",
    "duplicate_work_units_available = 0",
    "scoreinfo_duplicate_work_units_available = 0",
    "align_duplicate_work_units_available = 0",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_status = no_go_no_duplicate_work",
    "do_not_implement_reducing_runtime_from_this_shadow = 1",
    "do_not_run_first64_from_this_shadow = 1",
    "do_not_promote_broad_replacement_row_from_this_shadow = 1",
    "path_b_gpu_exact_work_unit_compaction_family_stopped = 1",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go",
    "current_execution_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "CPU aligner.Align() authority = 1",
    "GPU score authority = 0",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "default behavior unchanged = 1",
]
missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing exact work-unit consumer no-go phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "accepted_exact_work_unit_compaction_consumer = 1",
    "accepted_exact_work_unit_compaction_reduction = 1",
    "accepted_scoreinfo_prealign_compaction = 1",
    "accepted_align_side_compaction = 1",
    "consumer_can_reduce_scoreinfo_work = 1",
    "consumer_can_reduce_align_work = 1",
    "consumer_can_reduce_cpu_replay_frontier = 1",
    "consumer_available_before_scoreinfo_prealign_skip = 1",
    "consumer_available_before_align_skip = 1",
    "duplicate_work_units_available = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "gate_first1_pass = 1",
    "GPU score authority = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"exact work-unit consumer no-go doc contains forbidden phrase: {forbidden}")

if "next_valid_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go" not in prev_text:
    raise SystemExit("previous exact-work-unit shadow scaffold does not point to consumer/no-go")

doc_link = "docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go.md"
next_gate = "path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go"
next_pr = "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go"
for label, content in [
    ("roadmap", roadmap_text),
    ("action roadmap", action_text),
]:
    if doc_link not in content:
        raise SystemExit(f"{label} does not link exact-work-unit consumer no-go")
    if f"current_execution_gate = {next_gate}" not in content:
        raise SystemExit(f"{label} cursor was not advanced after exact-work-unit no-go")
    if f"current_next_pr = {next_pr}" not in content:
        raise SystemExit(f"{label} next PR was not advanced after exact-work-unit no-go")

for phrase in [
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_status",
    "no_go_no_duplicate_work",
    "accepted_exact_work_unit_compaction_consumer",
    "accepted_exact_work_unit_compaction_reduction",
    "accepted_scoreinfo_prealign_compaction",
    "accepted_align_side_compaction",
    "path_b_gpu_exact_work_unit_compaction_family_stopped",
    "path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go",
]:
    if phrase not in current_state_text and phrase not in current_state_check_text:
        raise SystemExit(f"current-state sources missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-consumer-no-go:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

target_name = "check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-consumer-no-go"
if f"check-fasim-gasal2-roadmap-current-state: {target_name}" not in makefile_text:
    raise SystemExit("current-state aggregate does not include exact work-unit consumer no-go target")

print("phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go=recorded")
print("phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_status=no_go_no_duplicate_work")
print("path_b_gpu_exact_work_unit_compaction_family_stopped=1")
print("next_valid_gate=path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
