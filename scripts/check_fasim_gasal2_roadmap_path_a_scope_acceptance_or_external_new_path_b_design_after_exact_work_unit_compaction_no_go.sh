#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go.md"
PREV="$ROOT/docs/fasim_gasal2_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go.md"
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
    "# Fasim GASAL2 Path A Scope Acceptance Or External New Path B Design After Exact Work-Unit Compaction No-Go",
    "path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go = recorded",
    "previous_checkpoint = docs/fasim_gasal2_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go.md",
    "previous_gate = path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go",
    "path_a_user_acceptance_recorded = 0",
    "path_a_scoped_completion_may_close_goal = 0",
    "path_b_external_design_input_received = 0",
    "path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined",
    "path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go = 1",
    "path_b_external_design_input_required_after_exact_work_unit_compaction_no_go = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go = recorded",
    "path_b_docs_spec_allowed_without_new_design_input = 0",
    "path_b_runtime_pr_allowed = 0",
    "path_a_acceptance_document = docs/fasim_gasal2_path_a_scoped_completion_acceptance.md",
    "path_b_external_design_document = none",
    "path_b_external_design_reviewed = 0",
    "path_b_external_design_accepted_for_spec = 0",
    "allowed_input_a = explicit_user_path_a_scope_acceptance",
    "allowed_input_b = external_new_path_b_gpu_design_source",
    "path_a_scope_must_remain_narrow = 1",
    "path_a_must_not_claim_broad_aligner_replacement = 1",
    "path_a_must_not_claim_long_query_broad_replacement = 1",
    "path_a_must_not_grant_gpu_endpoint_cigar_traceback_output_digest_authority = 1",
    "not_post_v5_3_descriptor_stream = 1",
    "not_scoreinfo_certificate_engine = 1",
    "not_gpu_owned_scoreinfo_consumer = 1",
    "not_gasal2_full_align_verifier = 1",
    "not_native_cuda_fasim_dp_engine = 1",
    "not_gpu_upper_bound_reject_certificate = 1",
    "not_gpu_exact_work_unit_compaction = 1",
    "requires_scoreinfo_prealign_reduction_plan = 1",
    "requires_align_side_reduction_plan = 1",
    "requires_full_row_digest_equality_plan = 1",
    "requires_fallback_accounting_plan = 1",
    "next_valid_gate = user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go",
    "current_execution_gate = user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go",
    "current_next_pr = none_until_user_scope_acceptance_or_external_path_b_design_input",
    "no real opt-in",
    "no default behavior change",
    "no runtime work drop",
    "no first64 before first1 passes",
    "no promotion of stopped Path B families",
    "no invented Path B design family",
    "no implicit Path A acceptance",
    "no GPU score authority",
    "no GPU endpoint authority",
    "no GPU CIGAR authority",
    "no GPU traceback authority",
    "no GPU output authority",
    "no GPU digest authority",
    "no completion claim from this checkpoint",
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
        "missing input-required checkpoint phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "path_a_user_acceptance_recorded = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "path_b_external_design_input_received = 1",
    "path_b_external_design_reviewed = 1",
    "path_b_external_design_accepted_for_spec = 1",
    "path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go = 0",
    "path_b_external_design_input_required_after_exact_work_unit_compaction_no_go = 0",
    "path_b_docs_spec_allowed_without_new_design_input = 1",
    "path_b_runtime_pr_allowed = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
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
        raise SystemExit(f"input-required checkpoint doc contains forbidden phrase: {forbidden}")

old_gate = "path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go"
old_pr = "fasim_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go"
next_gate = "user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go"
next_pr = "none_until_user_scope_acceptance_or_external_path_b_design_input"

if f"next_valid_gate = {old_gate}" not in prev_text:
    raise SystemExit("previous spec-or-acceptance checkpoint does not point to this gate")
if f"current_next_pr = {old_pr}" not in prev_text:
    raise SystemExit("previous spec-or-acceptance checkpoint does not name this gate PR")

link = "docs/fasim_gasal2_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go.md"
for label, content in [
    ("roadmap", roadmap_text),
    ("action roadmap", action_text),
]:
    if link not in content:
        raise SystemExit(f"{label} does not link input-required checkpoint")
    if f"current_execution_gate = {next_gate}" not in content:
        raise SystemExit(f"{label} cursor was not advanced to input-required gate")
    if f"current_next_pr = {next_pr}" not in content:
        raise SystemExit(f"{label} next PR was not advanced to input-required state")

for phrase in [
    "path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go",
    "path_b_external_design_input_received",
    "user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go",
    "none_until_user_scope_acceptance_or_external_path_b_design_input",
]:
    if phrase not in current_state_text and phrase not in current_state_check_text:
        raise SystemExit(f"current-state sources missing phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-external-new-path-b-design-after-exact-work-unit-compaction-no-go:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

target_name = "check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-external-new-path-b-design-after-exact-work-unit-compaction-no-go"
if f"check-fasim-gasal2-roadmap-current-state: {target_name}" not in makefile_text:
    raise SystemExit("current-state aggregate does not include input-required checkpoint target")

print("path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go=recorded")
print("path_a_user_acceptance_recorded=0")
print("path_b_external_design_input_received=0")
print("next_valid_gate=user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
